"""Fleet lái xe — tra cứu, cập nhật, xuất Excel, kiểm tra GPLX."""
import io
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.fleet_models import LaiXe
from app.api.fleet_common import FLEET_WRITE, _lx_to_dict, _validate_patch, _LX_DATES
from app.utils.date_parse import parse_vn_date

router = APIRouter(prefix="/fleet", tags=["Fleet - Lái xe"])

def _build_lx_query(q, ho_ten, hang_gplx, trang_thai, gplx_het_han_truoc,
                    nhiem_vu=None, dong_bhxh_bhyt=None, ksk_ket_qua=None, ksk_het_han_truoc=None):
    stmt = select(LaiXe)
    if q:
        q_like = f"%{q}%"
        stmt = stmt.where(or_(
            LaiXe.ho_ten.ilike(q_like),
            LaiXe.hang_gplx.ilike(q_like),
            LaiXe.tap_huan_don_vi.ilike(q_like),
        ))
    if ho_ten:                stmt = stmt.where(LaiXe.ho_ten.ilike(f"%{ho_ten}%"))
    if hang_gplx:             stmt = stmt.where(LaiXe.hang_gplx == hang_gplx)
    if trang_thai:            stmt = stmt.where(LaiXe.trang_thai == trang_thai)
    if gplx_het_han_truoc:    stmt = stmt.where(LaiXe.han_gplx <= gplx_het_han_truoc)
    if nhiem_vu == "lai_xe":  stmt = stmt.where(LaiXe.nhiem_vu_lai_xe != None)
    if nhiem_vu == "nv_phuc_vu": stmt = stmt.where(LaiXe.nhiem_vu_nv_phuc_vu != None)
    if dong_bhxh_bhyt:        stmt = stmt.where(LaiXe.dong_bhxh_bhyt.ilike(f"%{dong_bhxh_bhyt}%"))
    if ksk_ket_qua:           stmt = stmt.where(LaiXe.ksk_ket_qua.ilike(f"%{ksk_ket_qua}%"))
    if ksk_het_han_truoc:     stmt = stmt.where(LaiXe.ksk_ngay_kham <= ksk_het_han_truoc)
    return stmt

@router.get("/lai-xe", summary="Danh sách lái xe với filter linh hoạt")
async def list_lai_xe(
    q:              Optional[str] = Query(None),
    ho_ten:         Optional[str] = Query(None),
    hang_gplx:      Optional[str] = Query(None),
    trang_thai:     Optional[str] = Query(None),
    gplx_het_han_truoc: Optional[str] = Query(None),
    nhiem_vu:       Optional[str] = Query(None, description="lai_xe | nv_phuc_vu"),
    dong_bhxh_bhyt: Optional[str] = Query(None, description="Có | Không"),
    ksk_ket_qua:    Optional[str] = Query(None, description="Đủ sức khỏe | Không đủ"),
    ksk_het_han_truoc: Optional[str] = Query(None),
    page:  int = Query(default=1, ge=1),
    size:  int = Query(default=20, ge=1, le=500),
    sort_by: str = Query(default="ho_ten"),
    order:   str = Query(default="asc", pattern="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db),
):
    stmt = _build_lx_query(q, ho_ten, hang_gplx, trang_thai, gplx_het_han_truoc,
                           nhiem_vu, dong_bhxh_bhyt, ksk_ket_qua, ksk_het_han_truoc)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar()

    sort_col = getattr(LaiXe, sort_by, LaiXe.ho_ten)
    stmt = stmt.order_by(sort_col.asc() if order == "asc" else sort_col.desc())
    stmt = stmt.offset((page - 1) * size).limit(size)
    rows = (await db.execute(stmt)).scalars().all()

    return {
        "total": total,
        "page": page,
        "size": size,
        "pages": (total + size - 1) // size,
        "data": [_lx_to_dict(r) for r in rows],
    }

@router.get("/lai-xe/export", summary="Xuất Excel danh sách lái xe (theo filter)")
async def export_lai_xe(
    q:              Optional[str] = Query(None),
    ho_ten:         Optional[str] = Query(None),
    hang_gplx:      Optional[str] = Query(None),
    trang_thai:     Optional[str] = Query(None),
    gplx_het_han_truoc: Optional[str] = Query(None),
    nhiem_vu:       Optional[str] = Query(None),
    dong_bhxh_bhyt: Optional[str] = Query(None),
    ksk_ket_qua:    Optional[str] = Query(None),
    ksk_het_han_truoc: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    stmt = _build_lx_query(q, ho_ten, hang_gplx, trang_thai, gplx_het_han_truoc,
                           nhiem_vu, dong_bhxh_bhyt, ksk_ket_qua, ksk_het_han_truoc)
    stmt = stmt.order_by(LaiXe.ho_ten)
    rows = (await db.execute(stmt)).scalars().all()

    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Lái xe"

    headers = [
        "Họ tên", "Nhiệm vụ lái xe", "NV phục vụ",
        "Hạng GPLX", "Hạn GPLX",
        "Ngày ký HĐ", "Loại HĐ", "BHXH/BHYT",
        "Ngày khám SK", "Kết quả SK",
        "Ngày tập huấn", "Đơn vị TH", "Số GCN TH",
        "Trạng thái", "Ghi chú",
    ]
    header_fill = PatternFill("solid", fgColor="1E3A5F")
    header_font = Font(bold=True, color="FFFFFF", size=10)
    for ci, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=ci, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[1].height = 30

    for ri, r in enumerate(rows, 2):
        ws.cell(ri, 1, r.ho_ten)
        ws.cell(ri, 2, r.nhiem_vu_lai_xe or "")
        ws.cell(ri, 3, r.nhiem_vu_nv_phuc_vu or "")
        ws.cell(ri, 4, r.hang_gplx)
        ws.cell(ri, 5, r.han_gplx)
        ws.cell(ri, 6, r.hop_dong_ngay_ky)
        ws.cell(ri, 7, r.hop_dong_loai)
        ws.cell(ri, 8, r.dong_bhxh_bhyt)
        ws.cell(ri, 9, r.ksk_ngay_kham)
        ws.cell(ri, 10, r.ksk_ket_qua)
        ws.cell(ri, 11, r.tap_huan_ngay)
        ws.cell(ri, 12, r.tap_huan_don_vi)
        ws.cell(ri, 13, r.tap_huan_so_gcn)
        ws.cell(ri, 14, r.trang_thai)
        ws.cell(ri, 15, r.ghi_chu)

    col_widths = [24, 14, 14, 12, 14, 14, 22, 12, 14, 18, 14, 22, 16, 14, 20]
    for ci, w in enumerate(col_widths, 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(ci)].width = w

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    from datetime import date
    fname = f"lai_xe_{date.today().strftime('%Y%m%d')}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )

@router.get("/lai-xe/{lx_id}", summary="Chi tiết lái xe")
async def get_lai_xe(lx_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LaiXe).where(LaiXe.id == lx_id))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(404, "Lái xe không tồn tại")
    return _lx_to_dict(row)


# ════════════════════════════════════════════════════════════════════════════
# STATS
# ════════════════════════════════════════════════════════════════════════════

@router.patch("/lai-xe/{lx_id}", summary="Cập nhật lái xe (validate + tự sync Date + check GPLX)",
              dependencies=[Depends(FLEET_WRITE)])
async def update_lai_xe(lx_id: str, payload: dict, db: AsyncSession = Depends(get_db)):
    from app.services.audit_service import log_audit as _log
    row = (await db.execute(select(LaiXe).where(LaiXe.id == lx_id))).scalar_one_or_none()
    if not row:
        raise HTTPException(404, "Lái xe không tồn tại")
    payload = _validate_patch(payload, date_fields=_LX_DATES | {"ngay_sinh"},
                              int_fields={}, hang_field="hang_gplx")
    if payload.get("sdt") and len(str(payload["sdt"])) > 20:
        raise HTTPException(422, "SĐT quá dài")
    if payload.get("cccd") and not str(payload["cccd"]).replace(" ", "").isdigit():
        raise HTTPException(422, "CCCD phải là số")
    allowed = {"ho_ten", "sdt", "cccd", "dia_chi", "nhiem_vu_lai_xe", "nhiem_vu_nv_phuc_vu",
               "hang_gplx", "han_gplx", "so_gplx", "hop_dong_ngay_ky", "hop_dong_loai",
               "dong_bhxh_bhyt", "ksk_ngay_kham", "ksk_ket_qua", "tap_huan_ngay",
               "tap_huan_don_vi", "tap_huan_so_gcn", "trang_thai", "ghi_chu"}
    for k, v in payload.items():
        if k in allowed and hasattr(row, k):
            setattr(row, k, v)
    if "ngay_sinh" in payload and hasattr(row, "ngay_sinh"):
        row.ngay_sinh = parse_vn_date(payload["ngay_sinh"])
    for s_key, d_key in [("han_gplx", "han_gplx_date"),
                         ("hop_dong_ngay_ky", "hop_dong_ngay_ky_date"),
                         ("ksk_ngay_kham", "ksk_ngay_kham_date"),
                         ("tap_huan_ngay", "tap_huan_ngay_date")]:
        if s_key in payload and hasattr(row, d_key):
            setattr(row, d_key, parse_vn_date(payload[s_key]))
    await _log(db, action="update", entity="lai_xe", entity_id=lx_id, detail=row.ho_ten)
    return _lx_to_dict(row)

@router.get("/lai-xe/{lx_id}/gplx-check", summary="Kiểm tra GPLX có đủ lái xe bao nhiêu chỗ")
async def gplx_check(lx_id: str, so_cho: int = Query(..., ge=1, le=100),
                     db: AsyncSession = Depends(get_db)):
    from app.services.gplx_service import validate_gplx_for_so_cho
    row = (await db.execute(select(LaiXe).where(LaiXe.id == lx_id))).scalar_one_or_none()
    if not row:
        raise HTTPException(404, "Lái xe không tồn tại")
    ok, msg = validate_gplx_for_so_cho(row.hang_gplx, so_cho)
    return {"ho_ten": row.ho_ten, "hang_gplx": row.hang_gplx, "so_cho": so_cho,
            "dat": ok, "chi_tiet": msg}


# ════════════════════════════════════════════════════════════════════════════
# QUERY PHƯƠNG TIỆN — Filter linh hoạt
# ════════════════════════════════════════════════════════════════════════════
