"""Ops API — Tuyến / Phân công / Lệnh vận chuyển / Bảo trì / Hồ sơ pháp lý.

- CRUD tuyến
- Phân công xe-lái xe (check trùng thời gian + validate GPLX vs số chỗ)
- Lệnh vận chuyển (auto số lệnh + verify_code để in QR)
- Bảo trì / chi phí theo xe + tổng hợp tháng
- Hồ sơ pháp lý các kỳ (tự sync hạn mới nhất về PhuongTien)
"""
import uuid
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.ops import Tuyen, PhanCong, LenhVanChuyen, BaoTri, HoSoPhapLy
from app.models.fleet_models import PhuongTien, LaiXe
from app.services.gplx_service import validate_gplx_for_so_cho
from app.services.qr_verify_service import new_verify_code
from app.services.audit_service import log_audit
from app.utils.date_parse import parse_vn_date
from app.utils import labels as vi
from app.api.auth import require_roles

router = APIRouter(tags=["Ops - Điều hành vận tải"])

OPS_WRITE = require_roles("admin", "dieu_hanh")


# ─── Schemas ──────────────────────────────────────────────────────────
class TuyenIn(BaseModel):
    ma_tuyen: str
    ten_tuyen: str
    diem_di: Optional[str] = None
    diem_den: Optional[str] = None
    cu_ly_km: Optional[float] = None
    trang_thai: Optional[str] = "hoat_dong"
    ghi_chu: Optional[str] = None


class PhanCongIn(BaseModel):
    phuong_tien_id: str
    lai_xe_id: str
    tuyen_id: Optional[str] = None
    tu_ngay: Optional[str] = None  # YYYY-MM-DD hoặc DD/MM/YYYY
    den_ngay: Optional[str] = None
    ca: Optional[str] = None
    ghi_chu: Optional[str] = None


class LenhIn(BaseModel):
    phuong_tien_id: Optional[str] = None
    bien_so: Optional[str] = None
    lai_xe_id: Optional[str] = None
    tuyen_id: Optional[str] = None
    ngay_xuat_ben: Optional[str] = None
    gio_xuat_ben: Optional[str] = None
    ghi_chu: Optional[str] = None


class BaoTriIn(BaseModel):
    phuong_tien_id: str
    ngay: str
    loai: str = Field(description="sua_chua|bao_duong|nhien_lieu|lop|khac")
    noi_dung: Optional[str] = None
    km_hien_tai: Optional[int] = None
    chi_phi: Optional[float] = 0
    nha_cung_cap: Optional[str] = None
    hoa_don: Optional[str] = None


class HoSoIn(BaseModel):
    phuong_tien_id: str
    loai: str = Field(description="dang_kiem|phu_hieu|bao_hiem|gsht")
    ngay_cap: Optional[str] = None
    ngay_het_han: Optional[str] = None
    so_giay: Optional[str] = None
    don_vi_cap: Optional[str] = None
    file_scan: Optional[str] = None
    ghi_chu: Optional[str] = None


def _d(s: Optional[str]):
    return parse_vn_date(s) if s else None


# ─── Tuyến ────────────────────────────────────────────────────────────
@router.get("/tuyen", summary="Danh sách tuyến")
async def list_tuyen(q: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    stmt = select(Tuyen).order_by(Tuyen.ma_tuyen)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Tuyen.ma_tuyen.ilike(like), Tuyen.ten_tuyen.ilike(like)))
    rows = (await db.execute(stmt)).scalars().all()
    return [{"id": t.id, "ma_tuyen": t.ma_tuyen, "ten_tuyen": t.ten_tuyen,
             "diem_di": t.diem_di, "diem_den": t.diem_den, "cu_ly_km": t.cu_ly_km,
             "trang_thai": t.trang_thai, "ghi_chu": t.ghi_chu} for t in rows]


@router.post("/tuyen", summary="Tạo tuyến", status_code=201,
             dependencies=[Depends(OPS_WRITE)])
async def create_tuyen(payload: TuyenIn, db: AsyncSession = Depends(get_db)):
    exists = (await db.execute(select(Tuyen).where(Tuyen.ma_tuyen == payload.ma_tuyen))).scalar_one_or_none()
    if exists:
        raise HTTPException(400, f"Mã tuyến {payload.ma_tuyen} đã tồn tại")
    t = Tuyen(**payload.model_dump())
    db.add(t)
    await db.flush()
    await log_audit(db, action="create", entity="tuyen", entity_id=t.id, detail=t.ma_tuyen)
    return {"id": t.id, "ma_tuyen": t.ma_tuyen}


@router.delete("/tuyen/{tuyen_id}", summary="Xóa tuyến",
             dependencies=[Depends(OPS_WRITE)])
async def delete_tuyen(tuyen_id: str, db: AsyncSession = Depends(get_db)):
    t = (await db.execute(select(Tuyen).where(Tuyen.id == tuyen_id))).scalar_one_or_none()
    if not t:
        raise HTTPException(404, "Tuyến không tồn tại")
    await db.delete(t)
    await log_audit(db, action="delete", entity="tuyen", entity_id=tuyen_id)
    return {"ok": True}


# ─── Phân công ────────────────────────────────────────────────────────
@router.get("/phan-cong", summary="Danh sách phân công")
async def list_phan_cong(
    bien_so: Optional[str] = None, ngay: Optional[str] = None,
    page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(PhanCong).order_by(PhanCong.tu_ngay.desc())
    if bien_so:
        stmt = stmt.where(PhanCong.bien_so.ilike(f"%{bien_so}%"))
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar()
    rows = (await db.execute(stmt.offset((page - 1) * size).limit(size))).scalars().all()
    return {"total": total, "page": page, "size": size,
            "data": [{"id": r.id, "bien_so": r.bien_so, "ho_ten": r.ho_ten,
                      "phuong_tien_id": r.phuong_tien_id, "lai_xe_id": r.lai_xe_id,
                      "tuyen_id": r.tuyen_id, "tu_ngay": str(r.tu_ngay) if r.tu_ngay else None,
                      "den_ngay": str(r.den_ngay) if r.den_ngay else None,
                      "ca": r.ca, "trang_thai": r.trang_thai, "ghi_chu": r.ghi_chu} for r in rows]}


@router.post("/phan-cong", summary="Phân công xe - lái xe (có check GPLX + trùng)", status_code=201,
             dependencies=[Depends(OPS_WRITE)])
async def create_phan_cong(payload: PhanCongIn, db: AsyncSession = Depends(get_db)):
    pt = (await db.execute(select(PhuongTien).where(PhuongTien.id == payload.phuong_tien_id))).scalar_one_or_none()
    if not pt:
        raise HTTPException(404, "Phương tiện không tồn tại")
    lx = (await db.execute(select(LaiXe).where(LaiXe.id == payload.lai_xe_id))).scalar_one_or_none()
    if not lx:
        raise HTTPException(404, "Lái xe không tồn tại")

    ok, msg = validate_gplx_for_so_cho(lx.hang_gplx, pt.so_cho)
    if not ok:
        raise HTTPException(400, f"Không phù hợp GPLX: {lx.ho_ten} ({lx.hang_gplx}) — {msg}")

    tu = _d(payload.tu_ngay) or date.today()
    den = _d(payload.den_ngay)
    # Check trùng: cùng xe hoặc cùng lái xe giao nhau thời gian & đang hiệu lực
    overlap = (await db.execute(select(PhanCong).where(
        or_(PhanCong.phuong_tien_id == pt.id, PhanCong.lai_xe_id == lx.id),
        PhanCong.trang_thai == "hieu_luc",
        or_(PhanCong.den_ngay.is_(None), PhanCong.den_ngay >= tu),
    ))).scalars().all()
    for o in overlap:
        o_den = o.den_ngay or date(2099, 12, 31)
        o_tu = o.tu_ngay or date(2000, 1, 1)
        end = den or date(2099, 12, 31)
        if o_tu <= end and tu <= o_den:
            raise HTTPException(400, f"Trùng phân công (xe {o.bien_so} / {o.ho_ten} từ {o.tu_ngay} đến {o.den_ngay})")

    pc = PhanCong(phuong_tien_id=pt.id, bien_so=pt.bien_so, lai_xe_id=lx.id,
                  ho_ten=lx.ho_ten, tuyen_id=payload.tuyen_id, tu_ngay=tu,
                  den_ngay=den, ca=payload.ca, ghi_chu=payload.ghi_chu)
    db.add(pc)
    await db.flush()
    await log_audit(db, action="create", entity="phan_cong", entity_id=pc.id,
                    detail=f"{pt.bien_so} x {lx.ho_ten}")
    return {"id": pc.id, "bien_so": pt.bien_so, "ho_ten": lx.ho_ten, "gplx_check": msg}


@router.post("/phan-cong/{pc_id}/ket-thuc", summary="Kết thúc phân công",
             dependencies=[Depends(OPS_WRITE)])
async def end_phan_cong(pc_id: str, db: AsyncSession = Depends(get_db)):
    pc = (await db.execute(select(PhanCong).where(PhanCong.id == pc_id))).scalar_one_or_none()
    if not pc:
        raise HTTPException(404, "Phân công không tồn tại")
    pc.trang_thai = "ket_thuc"
    pc.den_ngay = date.today()
    await log_audit(db, action="update", entity="phan_cong", entity_id=pc_id,
                    detail=vi.label(vi.TRANG_THAI, "ket_thuc"))
    return {"ok": True}


# ─── Lệnh vận chuyển ──────────────────────────────────────────────────
@router.get("/lenh", summary="Danh sách lệnh vận chuyển")
async def list_lenh(bien_so: Optional[str] = None, limit: int = Query(50, ge=1, le=200),
                    db: AsyncSession = Depends(get_db)):
    stmt = select(LenhVanChuyen).order_by(LenhVanChuyen.created_at.desc()).limit(limit)
    if bien_so:
        stmt = stmt.where(LenhVanChuyen.bien_so.ilike(f"%{bien_so}%"))
    rows = (await db.execute(stmt)).scalars().all()
    return [{"id": r.id, "so_lenh": r.so_lenh, "bien_so": r.bien_so,
             "ngay_xuat_ben": str(r.ngay_xuat_ben) if r.ngay_xuat_ben else None,
             "verify_code": r.verify_code, "trang_thai": r.trang_thai,
             "render_job_id": r.render_job_id} for r in rows]


@router.post("/lenh", summary="Cấp lệnh vận chuyển (auto số + verify_code)", status_code=201,
             dependencies=[Depends(OPS_WRITE)])
async def create_lenh(payload: LenhIn, db: AsyncSession = Depends(get_db)):
    bien_so = payload.bien_so
    if payload.phuong_tien_id and not bien_so:
        pt = (await db.execute(select(PhuongTien).where(PhuongTien.id == payload.phuong_tien_id))).scalar_one_or_none()
        bien_so = pt.bien_so if pt else None
    so_lenh = f"LVC-{date.today().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    code = new_verify_code(so_lenh)
    r = LenhVanChuyen(so_lenh=so_lenh, phuong_tien_id=payload.phuong_tien_id,
                      bien_so=bien_so, lai_xe_id=payload.lai_xe_id,
                      tuyen_id=payload.tuyen_id,
                      ngay_xuat_ben=_d(payload.ngay_xuat_ben) or date.today(),
                      gio_xuat_ben=payload.gio_xuat_ben, verify_code=code,
                      ghi_chu=payload.ghi_chu)
    db.add(r)
    await db.flush()
    await log_audit(db, action="create", entity="lenh", entity_id=r.id, detail=so_lenh)
    return {"id": r.id, "so_lenh": so_lenh, "verify_code": code,
            "qr_text": f"/verify/{code}"}


# ─── Bảo trì ─────────────────────────────────────────────────────────
@router.post("/bao-tri", summary="Ghi bảo trì / chi phí", status_code=201,
             dependencies=[Depends(OPS_WRITE)])
async def create_baotri(payload: BaoTriIn, db: AsyncSession = Depends(get_db)):
    pt = (await db.execute(select(PhuongTien).where(PhuongTien.id == payload.phuong_tien_id))).scalar_one_or_none()
    if not pt:
        raise HTTPException(404, "Phương tiện không tồn tại")
    ngay = _d(payload.ngay)
    if not ngay:
        raise HTTPException(400, "Ngày không hợp lệ (dùng YYYY-MM-DD hoặc DD/MM/YYYY)")
    b = BaoTri(phuong_tien_id=pt.id, bien_so=pt.bien_so, ngay=ngay, loai=payload.loai,
               noi_dung=payload.noi_dung, km_hien_tai=payload.km_hien_tai,
               chi_phi=payload.chi_phi or 0, nha_cung_cap=payload.nha_cung_cap,
               hoa_don=payload.hoa_don)
    db.add(b)
    await db.flush()
    await log_audit(db, action="create", entity="bao_tri", entity_id=b.id,
                    detail=f"{pt.bien_so} {vi.label(vi.BAO_TRI_LOAI, payload.loai)} {vi.fmt_money(payload.chi_phi)}")
    return {"id": b.id}


@router.get("/bao-tri", summary="Lịch sử bảo trì theo xe")
async def list_baotri(bien_so: Optional[str] = None, loai: Optional[str] = None,
                      limit: int = Query(100, ge=1, le=500), db: AsyncSession = Depends(get_db)):
    stmt = select(BaoTri).order_by(BaoTri.ngay.desc()).limit(limit)
    if bien_so:
        stmt = stmt.where(BaoTri.bien_so.ilike(f"%{bien_so}%"))
    if loai:
        stmt = stmt.where(BaoTri.loai == loai)
    rows = (await db.execute(stmt)).scalars().all()
    tong = sum(r.chi_phi or 0 for r in rows)
    return {"tong_chi_phi": tong,
            "data": [{"id": r.id, "bien_so": r.bien_so, "ngay": str(r.ngay),
                      "loai": r.loai, "noi_dung": r.noi_dung, "km": r.km_hien_tai,
                      "chi_phi": r.chi_phi} for r in rows]}


# ─── Hồ sơ pháp lý ───────────────────────────────────────────────────
@router.post("/ho-so", summary="Lưu giấy tờ 1 kỳ (tự sync hạn mới nhất về xe)", status_code=201,
             dependencies=[Depends(OPS_WRITE)])
async def create_hoso(payload: HoSoIn, db: AsyncSession = Depends(get_db)):
    pt = (await db.execute(select(PhuongTien).where(PhuongTien.id == payload.phuong_tien_id))).scalar_one_or_none()
    if not pt:
        raise HTTPException(404, "Phương tiện không tồn tại")
    het = _d(payload.ngay_het_han)
    h = HoSoPhapLy(phuong_tien_id=pt.id, bien_so=pt.bien_so, loai=payload.loai,
                   ngay_cap=_d(payload.ngay_cap), ngay_het_han=het,
                   so_giay=payload.so_giay, don_vi_cap=payload.don_vi_cap,
                   file_scan=payload.file_scan, ghi_chu=payload.ghi_chu)
    db.add(h)
    await db.flush()
    # Sync hạn mới nhất về PhuongTien (cả String + Date)
    if het:
        iso = het.isoformat()
        if payload.loai == "dang_kiem":
            pt.han_dang_kiem, pt.han_dang_kiem_date = iso, het
        elif payload.loai == "phu_hieu":
            pt.han_phu_hieu, pt.han_phu_hieu_date = iso, het
        elif payload.loai == "bao_hieu" or payload.loai == "bao_hiem":
            pt.han_bao_hiem, pt.han_bao_hiem_date = iso, het
    await log_audit(db, action="create", entity="ho_so", entity_id=h.id,
                    detail=f"{pt.bien_so} {vi.label(vi.HOSO_LOAI, payload.loai)}")
    return {"id": h.id}


@router.get("/ho-so/{phuong_tien_id}", summary="Lịch sử giấy tờ của 1 xe")
async def list_hoso(phuong_tien_id: str, db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(HoSoPhapLy).where(
        HoSoPhapLy.phuong_tien_id == phuong_tien_id).order_by(HoSoPhapLy.ngay_het_han.desc()))
    ).scalars().all()
    return [{"id": r.id, "loai": r.loai, "ngay_cap": str(r.ngay_cap) if r.ngay_cap else None,
             "ngay_het_han": str(r.ngay_het_han) if r.ngay_het_han else None,
             "so_giay": r.so_giay, "don_vi_cap": r.don_vi_cap} for r in rows]
