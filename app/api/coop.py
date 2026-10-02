"""Coop API — Xã viên / Vốn góp / Doanh thu chia lãi."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.coop_models import XaVien, VonGop, DoanhThu
from app.services.audit_service import log_audit
from app.utils.date_parse import parse_vn_date
from app.api.auth import require_roles

router = APIRouter(tags=["Coop - Xã viên & Tài chính"])

COOP_WRITE = require_roles("admin", "dieu_hanh")
FIN_WRITE = require_roles("admin", "ke_toan")


class XaVienIn(BaseModel):
    ma_xa_vien: str
    ho_ten: str
    cccd: Optional[str] = None
    sdt: Optional[str] = None
    dia_chi: Optional[str] = None
    ngay_tham_gia: Optional[str] = None
    ghi_chu: Optional[str] = None


class VonGopIn(BaseModel):
    xa_vien_id: str
    ngay_gop: str
    so_tien: float
    hinh_thuc: Optional[str] = None
    ghi_chu: Optional[str] = None


class DoanhThuIn(BaseModel):
    bien_so: Optional[str] = None
    phuong_tien_id: Optional[str] = None
    tuyen_id: Optional[str] = None
    thang: str  # YYYY-MM
    doanh_thu: float = 0
    chi_phi: float = 0
    ghi_chu: Optional[str] = None


@router.get("/xa-vien", summary="Danh sách xã viên + tổng vốn góp")
async def list_xavien(q: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    stmt = select(XaVien).order_by(XaVien.ma_xa_vien)
    if q:
        stmt = stmt.where(XaVien.ho_ten.ilike(f"%{q}%"))
    rows = (await db.execute(stmt)).scalars().all()
    out = []
    for x in rows:
        tong = (await db.execute(select(func.coalesce(func.sum(VonGop.so_tien), 0))
                                .where(VonGop.xa_vien_id == x.id))).scalar() or 0
        out.append({"id": x.id, "ma_xa_vien": x.ma_xa_vien, "ho_ten": x.ho_ten,
                    "sdt": x.sdt, "cccd": x.cccd, "trang_thai": x.trang_thai,
                    "tong_von_gop": tong})
    return out


@router.post("/xa-vien", status_code=201, summary="Thêm xã viên",
             dependencies=[Depends(COOP_WRITE)])
async def create_xavien(payload: XaVienIn, db: AsyncSession = Depends(get_db)):
    if (await db.execute(select(XaVien).where(XaVien.ma_xa_vien == payload.ma_xa_vien))).scalar_one_or_none():
        raise HTTPException(400, "Mã xã viên đã tồn tại")
    x = XaVien(ma_xa_vien=payload.ma_xa_vien, ho_ten=payload.ho_ten, cccd=payload.cccd,
               sdt=payload.sdt, dia_chi=payload.dia_chi,
               ngay_tham_gia=parse_vn_date(payload.ngay_tham_gia) if payload.ngay_tham_gia else None,
               ghi_chu=payload.ghi_chu)
    db.add(x)
    await db.flush()
    await log_audit(db, action="create", entity="xa_vien", entity_id=x.id, detail=x.ma_xa_vien)
    return {"id": x.id}


@router.post("/von-gop", status_code=201, summary="Ghi vốn góp",
             dependencies=[Depends(FIN_WRITE)])
async def create_vongop(payload: VonGopIn, db: AsyncSession = Depends(get_db)):
    ngay = parse_vn_date(payload.ngay_gop)
    if not ngay:
        raise HTTPException(400, "ngay_gop không hợp lệ")
    v = VonGop(xa_vien_id=payload.xa_vien_id, ngay_gop=ngay, so_tien=payload.so_tien,
               hinh_thuc=payload.hinh_thuc, ghi_chu=payload.ghi_chu)
    db.add(v)
    await db.flush()
    await log_audit(db, action="create", entity="von_gop", entity_id=v.id, detail=str(payload.so_tien))
    return {"id": v.id}


@router.get("/von-gop/{xa_vien_id}", summary="Lịch sử vốn góp 1 xã viên")
async def list_vongop(xa_vien_id: str, db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(VonGop).where(VonGop.xa_vien_id == xa_vien_id)
                             .order_by(VonGop.ngay_gop.desc()))).scalars().all()
    return [{"id": r.id, "ngay_gop": str(r.ngay_gop), "so_tien": r.so_tien,
             "hinh_thuc": r.hinh_thuc} for r in rows]


@router.post("/doanh-thu", status_code=201, summary="Ghi doanh thu tháng (tự tính lợi nhuận)",
             dependencies=[Depends(FIN_WRITE)])
async def create_doanhthu(payload: DoanhThuIn, db: AsyncSession = Depends(get_db)):
    loinhuan = (payload.doanh_thu or 0) - (payload.chi_phi or 0)
    r = DoanhThu(phuong_tien_id=payload.phuong_tien_id, bien_so=payload.bien_so,
                 tuyen_id=payload.tuyen_id, thang=payload.thang,
                 doanh_thu=payload.doanh_thu, chi_phi=payload.chi_phi,
                 loi_nhuan=loinhuan, ghi_chu=payload.ghi_chu)
    db.add(r)
    await db.flush()
    await log_audit(db, action="create", entity="doanh_thu", entity_id=r.id,
                    detail=f"{payload.thang} {payload.bien_so}")
    return {"id": r.id, "loi_nhuan": loinhuan}


@router.get("/doanh-thu", summary="Tổng hợp doanh thu theo tháng")
async def list_doanhthu(thang: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    stmt = select(DoanhThu).order_by(DoanhThu.thang.desc()).limit(200)
    if thang:
        stmt = stmt.where(DoanhThu.thang == thang)
    rows = (await db.execute(stmt)).scalars().all()
    tong_dt = sum(r.doanh_thu or 0 for r in rows)
    tong_cp = sum(r.chi_phi or 0 for r in rows)
    return {"tong_doanh_thu": tong_dt, "tong_chi_phi": tong_cp,
            "tong_loi_nhuan": tong_dt - tong_cp,
            "data": [{"id": r.id, "bien_so": r.bien_so, "thang": r.thang,
                      "doanh_thu": r.doanh_thu, "chi_phi": r.chi_phi,
                      "loi_nhuan": r.loi_nhuan} for r in rows]}
