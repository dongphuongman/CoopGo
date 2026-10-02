"""Fleet phương tiện — tra cứu, cập nhật, xuất Excel."""
import io
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.fleet_models import PhuongTien
from app.api.fleet_common import FLEET_WRITE, _pt_to_dict, _validate_patch, _PT_DATES, _PT_INTS
from app.utils.date_parse import parse_vn_date

router = APIRouter(prefix="/fleet", tags=["Fleet - Phương tiện"])

def _build_pt_query(q, bien_so, hang_xe, loai_hinh, trang_thai, so_cho, so_cho_min, so_cho_max,
                    loai_so_huu=None, loai_di_thue=None,
                    han_dang_kiem_truoc=None, han_bao_hiem_truoc=None):
    from app.utils.date_parse import parse_vn_date as _pd
    stmt = select(PhuongTien)
    if q:
        q_like = f"%{q}%"
        stmt = stmt.where(or_(
            PhuongTien.bien_so.ilike(q_like),
            PhuongTien.hang_xe.ilike(q_like),
            PhuongTien.loai_hinh_hoat_dong.ilike(q_like),
            PhuongTien.tuyen_khai_thac.ilike(q_like),
        ))
    if bien_so:     stmt = stmt.where(PhuongTien.bien_so.ilike(f"%{bien_so}%"))
    if hang_xe:     stmt = stmt.where(PhuongTien.hang_xe.ilike(f"%{hang_xe}%"))
    if loai_hinh:   stmt = stmt.where(PhuongTien.loai_hinh_hoat_dong.ilike(f"%{loai_hinh}%"))
    if trang_thai:  stmt = stmt.where(PhuongTien.trang_thai == trang_thai)
    if so_cho:      stmt = stmt.where(PhuongTien.so_cho == so_cho)
    if so_cho_min:  stmt = stmt.where(PhuongTien.so_cho >= so_cho_min)
    if so_cho_max:  stmt = stmt.where(PhuongTien.so_cho <= so_cho_max)
    if loai_so_huu == "X":  stmt = stmt.where(PhuongTien.loai_so_huu != None)
    if loai_so_huu == "khong":  stmt = stmt.where(PhuongTien.loai_so_huu == None)
    if loai_di_thue == "X":  stmt = stmt.where(PhuongTien.loai_di_thue != None)
    if loai_di_thue == "khong":  stmt = stmt.where(PhuongTien.loai_di_thue == None)
    if han_dang_kiem_truoc:
        _d = _pd(han_dang_kiem_truoc)
        if _d and hasattr(PhuongTien, "han_dang_kiem_date"):
            stmt = stmt.where(or_(PhuongTien.han_dang_kiem_date <= _d,
                                  PhuongTien.han_dang_kiem <= han_dang_kiem_truoc))
        else:
            stmt = stmt.where(PhuongTien.han_dang_kiem <= han_dang_kiem_truoc)
    if han_bao_hiem_truoc:
        _d2 = _pd(han_bao_hiem_truoc)
        if _d2 and hasattr(PhuongTien, "han_bao_hiem_date"):
            stmt = stmt.where(or_(PhuongTien.han_bao_hiem_date <= _d2,
                                  PhuongTien.han_bao_hiem <= han_bao_hiem_truoc))
        else:
            stmt = stmt.where(PhuongTien.han_bao_hiem <= han_bao_hiem_truoc)
    return stmt

@router.get("/phuong-tien", summary="Danh sách phương tiện với filter linh hoạt")
async def list_phuong_tien(
    q:            Optional[str] = Query(None),
    bien_so:      Optional[str] = Query(None),
    hang_xe:      Optional[str] = Query(None),
    loai_hinh:    Optional[str] = Query(None),
    trang_thai:   Optional[str] = Query(None),
    so_cho:       Optional[int] = Query(None),
    so_cho_min:   Optional[int] = Query(None),
    so_cho_max:   Optional[int] = Query(None),
    loai_so_huu:  Optional[str] = Query(None),
    loai_di_thue: Optional[str] = Query(None),
    han_dang_kiem_truoc: Optional[str] = Query(None),
    han_bao_hiem_truoc:  Optional[str] = Query(None),
    page:    int = Query(default=1, ge=1),
    size:    int = Query(default=20, ge=1, le=500),
    sort_by: str = Query(default="bien_so"),
    order:   str = Query(default="asc", pattern="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db),
):
    stmt = _build_pt_query(q, bien_so, hang_xe, loai_hinh, trang_thai, so_cho, so_cho_min, so_cho_max,
                           loai_so_huu, loai_di_thue, han_dang_kiem_truoc, han_bao_hiem_truoc)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar()

    sort_col = getattr(PhuongTien, sort_by, PhuongTien.bien_so)
    stmt = stmt.order_by(sort_col.asc() if order == "asc" else sort_col.desc())
    stmt = stmt.offset((page - 1) * size).limit(size)
    rows = (await db.execute(stmt)).scalars().all()

    return {
        "total": total,
        "page": page,
        "size": size,
        "pages": (total + size - 1) // size,
        "data": [_pt_to_dict(r) for r in rows],
    }

@router.get("/phuong-tien/export", summary="Xuất Excel danh sách phương tiện (theo filter)")
async def export_phuong_tien(
    q:            Optional[str] = Query(None),
    bien_so:      Optional[str] = Query(None),
    hang_xe:      Optional[str] = Query(None),
    loai_hinh:    Optional[str] = Query(None),
    trang_thai:   Optional[str] = Query(None),
    so_cho:       Optional[int] = Query(None),
    so_cho_min:   Optional[int] = Query(None),
    so_cho_max:   Optional[int] = Query(None),
    loai_so_huu:  Optional[str] = Query(None),
    loai_di_thue: Optional[str] = Query(None),
    han_dang_kiem_truoc: Optional[str] = Query(None),
    han_bao_hiem_truoc:  Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    stmt = _build_pt_query(q, bien_so, hang_xe, loai_hinh, trang_thai, so_cho, so_cho_min, so_cho_max,
                           loai_so_huu, loai_di_thue, han_dang_kiem_truoc, han_bao_hiem_truoc)
    stmt = stmt.order_by(PhuongTien.bien_so)
    rows = (await db.execute(stmt)).scalars().all()

    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Phương tiện"

    headers = [
        "Biển số", "Hãng xe", "Năm SX", "Số chỗ", "Màu xe",
        "Loại hình HĐ", "Tuyến khai thác",
        "Hạn đăng kiểm", "Hạn phù hiệu", "Hạn BH TNDS",
        "GSHT tên", "GSHT đơn vị",
        "Sở hữu", "Đi thuê", "Trạng thái", "Ghi chú",
    ]
    # Header style
    header_fill = PatternFill("solid", fgColor="1E3A5F")
    header_font = Font(bold=True, color="FFFFFF", size=10)
    for ci, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=ci, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    ws.row_dimensions[1].height = 30

    for ri, r in enumerate(rows, 2):
        ws.cell(ri, 1, r.bien_so)
        ws.cell(ri, 2, r.hang_xe)
        ws.cell(ri, 3, r.nam_san_xuat)
        ws.cell(ri, 4, r.so_cho)
        ws.cell(ri, 5, r.mau_xe)
        ws.cell(ri, 6, r.loai_hinh_hoat_dong)
        ws.cell(ri, 7, r.tuyen_khai_thac)
        ws.cell(ri, 8, r.han_dang_kiem)
        ws.cell(ri, 9, r.han_phu_hieu)
        ws.cell(ri, 10, r.han_bao_hiem)
        ws.cell(ri, 11, r.gsht_ten)
        ws.cell(ri, 12, r.gsht_don_vi)
        ws.cell(ri, 13, r.loai_so_huu)
        ws.cell(ri, 14, r.loai_di_thue)
        ws.cell(ri, 15, r.trang_thai)
        ws.cell(ri, 16, r.ghi_chu)

    col_widths = [14, 18, 8, 8, 10, 22, 26, 14, 14, 14, 20, 20, 10, 10, 14, 20]
    for ci, w in enumerate(col_widths, 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(ci)].width = w

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    from datetime import date
    fname = f"phuong_tien_{date.today().strftime('%Y%m%d')}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )

@router.get("/phuong-tien/{pt_id}", summary="Chi tiết phương tiện")
async def get_phuong_tien(pt_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PhuongTien).where(PhuongTien.id == pt_id))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(404, "Phương tiện không tồn tại")
    return _pt_to_dict(row)


# ════════════════════════════════════════════════════════════════════════════
# QUERY LÁI XE — Filter linh hoạt
# ════════════════════════════════════════════════════════════════════════════

@router.patch("/phuong-tien/{pt_id}", summary="Cập nhật phương tiện (validate + tự sync Date)",
              dependencies=[Depends(FLEET_WRITE)])
async def update_phuong_tien(pt_id: str, payload: dict, db: AsyncSession = Depends(get_db)):
    from app.services.audit_service import log_audit as _log
    row = (await db.execute(select(PhuongTien).where(PhuongTien.id == pt_id))).scalar_one_or_none()
    if not row:
        raise HTTPException(404, "Phương tiện không tồn tại")
    payload = _validate_patch(payload, date_fields=_PT_DATES, int_fields=_PT_INTS)
    allowed = {"hang_xe", "nam_san_xuat", "so_cho", "mau_xe", "loai_hinh_hoat_dong",
               "tuyen_khai_thac", "han_dang_kiem", "han_phu_hieu", "han_bao_hiem",
               "gsht_ten", "gsht_don_vi", "gsht_dia_chi", "gsht_mat_khau",
               "so_khung", "so_may", "trong_tai_kg", "so_ghe",
               "loai_so_huu", "loai_di_thue", "trang_thai", "ghi_chu"}
    for k, v in payload.items():
        if k in allowed and hasattr(row, k):
            setattr(row, k, v)
    # sync Date
    for s_key, d_key in [("han_dang_kiem", "han_dang_kiem_date"),
                         ("han_phu_hieu", "han_phu_hieu_date"),
                         ("han_bao_hiem", "han_bao_hiem_date")]:
        if s_key in payload and hasattr(row, d_key):
            d = parse_vn_date(payload[s_key])
            setattr(row, d_key, d)
    await _log(db, action="update", entity="phuong_tien", entity_id=pt_id, detail=row.bien_so)
    return _pt_to_dict(row)
