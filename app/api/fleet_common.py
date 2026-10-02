"""Fleet dùng chung: validate PATCH, serializers, thống kê, phân quyền."""
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.core.config import get_settings
from app.core.database import get_db
from app.models.fleet_models import PhuongTien, LaiXe
from app.utils.date_parse import parse_vn_date
from app.api.auth import require_roles

router = APIRouter(prefix="/fleet", tags=["Fleet"])
settings = get_settings()

FLEET_IMPORT = require_roles("admin", "dieu_hanh")
FLEET_WRITE = require_roles("admin", "dieu_hanh")

_PT_DATES = {"han_dang_kiem", "han_phu_hieu", "han_bao_hiem"}
_LX_DATES = {"han_gplx", "hop_dong_ngay_ky", "ksk_ngay_kham", "tap_huan_ngay"}

_PT_INTS = {"nam_san_xuat": (1900, 2100), "so_cho": (1, 100),
            "trong_tai_kg": (0, 100000), "so_ghe": (1, 100)}

def _validate_patch(payload: dict, *, date_fields: set, int_fields: dict,
                    hang_field: str | None = None) -> dict:
    """Trả về payload đã chuẩn hóa; raise 422 nếu sai định dạng."""
    from app.services.gplx_service import normalize_hang
    clean: dict = {}
    for k, v in payload.items():
        if v is None or (isinstance(v, str) and not v.strip()):
            clean[k] = None
            continue
        if k in date_fields:
            d = parse_vn_date(v)
            if d is None:
                raise HTTPException(
                    422, f"Ngày không hợp lệ: '{k}' = '{v}' (dùng YYYY-MM-DD hoặc DD/MM/YYYY)")
            clean[k] = v
        elif k in int_fields:
            lo, hi = int_fields[k]
            try:
                iv = int(float(v))
            except (TypeError, ValueError):
                raise HTTPException(422, f"'{k}' phải là số, nhận được '{v}'")
            if not (lo <= iv <= hi):
                raise HTTPException(422, f"'{k}' phải trong khoảng {lo}..{hi}")
            clean[k] = iv
        elif hang_field and k == hang_field:
            h = normalize_hang(v)
            if not h:
                raise HTTPException(422, f"Hạng GPLX không hợp lệ: '{v}' (vd B2, C, D, E)")
            clean[k] = h
        else:
            clean[k] = v
    return clean

def _pt_to_dict(r: PhuongTien) -> dict:
    from app.utils.date_parse import parse_vn_date as _p
    def _iso(d, s):
        if d:
            return str(d)
        dd = _p(s) if s else None
        return dd.isoformat() if dd else s
    return {
        "id": r.id,
        "bien_so": r.bien_so,
        "hang_xe": r.hang_xe,
        "nam_san_xuat": r.nam_san_xuat,
        "so_cho": r.so_cho,
        "mau_xe": r.mau_xe,
        "loai_hinh_hoat_dong": r.loai_hinh_hoat_dong,
        "tuyen_khai_thac": r.tuyen_khai_thac,
        "han_dang_kiem": r.han_dang_kiem,
        "han_phu_hieu": r.han_phu_hieu,
        "han_bao_hiem": r.han_bao_hiem,
        "han_dang_kiem_date": _iso(getattr(r, "han_dang_kiem_date", None), r.han_dang_kiem),
        "han_phu_hieu_date": _iso(getattr(r, "han_phu_hieu_date", None), r.han_phu_hieu),
        "han_bao_hiem_date": _iso(getattr(r, "han_bao_hiem_date", None), r.han_bao_hiem),
        "gsht_ten": r.gsht_ten,
        "gsht_don_vi": r.gsht_don_vi,
        "so_khung": getattr(r, "so_khung", None),
        "so_may": getattr(r, "so_may", None),
        "trong_tai_kg": getattr(r, "trong_tai_kg", None),
        "loai_so_huu": r.loai_so_huu,
        "loai_di_thue": r.loai_di_thue,
        "trang_thai": r.trang_thai,
        "ghi_chu": r.ghi_chu,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }

def _lx_to_dict(r: LaiXe) -> dict:
    from app.utils.date_parse import parse_vn_date as _p
    def _iso(d, s):
        if d:
            return str(d)
        dd = _p(s) if s else None
        return dd.isoformat() if dd else s
    return {
        "id": r.id,
        "ho_ten": r.ho_ten,
        "sdt": getattr(r, "sdt", None),
        "cccd": getattr(r, "cccd", None),
        "dia_chi": getattr(r, "dia_chi", None),
        "ngay_sinh": str(getattr(r, "ngay_sinh", None)) if getattr(r, "ngay_sinh", None) else None,
        "so_gplx": getattr(r, "so_gplx", None),
        "nhiem_vu_lai_xe": r.nhiem_vu_lai_xe,
        "nhiem_vu_nv_phuc_vu": r.nhiem_vu_nv_phuc_vu,
        "hang_gplx": r.hang_gplx,
        "han_gplx": r.han_gplx,
        "han_gplx_date": _iso(getattr(r, "han_gplx_date", None), r.han_gplx),
        "hop_dong_ngay_ky": r.hop_dong_ngay_ky,
        "hop_dong_loai": r.hop_dong_loai,
        "dong_bhxh_bhyt": r.dong_bhxh_bhyt,
        "ksk_ngay_kham": r.ksk_ngay_kham,
        "ksk_ket_qua": r.ksk_ket_qua,
        "tap_huan_ngay": r.tap_huan_ngay,
        "tap_huan_don_vi": r.tap_huan_don_vi,
        "tap_huan_so_gcn": r.tap_huan_so_gcn,
        "trang_thai": r.trang_thai,
        "ghi_chu": r.ghi_chu,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }

@router.get("/stats", summary="Thống kê tổng hợp phương tiện & lái xe")
async def get_fleet_stats(db: AsyncSession = Depends(get_db)):
    # Phương tiện
    total_pt = (await db.execute(select(func.count(PhuongTien.id)))).scalar()
    pt_by_so_cho = (await db.execute(
        select(PhuongTien.so_cho, func.count().label("count"))
        .group_by(PhuongTien.so_cho)
        .order_by(PhuongTien.so_cho)
    )).all()
    pt_by_trang_thai = (await db.execute(
        select(PhuongTien.trang_thai, func.count().label("count"))
        .group_by(PhuongTien.trang_thai)
    )).all()

    # Lái xe
    total_lx = (await db.execute(select(func.count(LaiXe.id)))).scalar()
    lx_by_hang_gplx = (await db.execute(
        select(LaiXe.hang_gplx, func.count().label("count"))
        .group_by(LaiXe.hang_gplx)
        .order_by(LaiXe.hang_gplx)
    )).all()
    lx_by_trang_thai = (await db.execute(
        select(LaiXe.trang_thai, func.count().label("count"))
        .group_by(LaiXe.trang_thai)
    )).all()

    return {
        "phuong_tien": {
            "total": total_pt,
            "by_so_cho": [{"so_cho": r[0], "count": r[1]} for r in pt_by_so_cho],
            "by_trang_thai": [{"trang_thai": r[0], "count": r[1]} for r in pt_by_trang_thai],
        },
        "lai_xe": {
            "total": total_lx,
            "by_hang_gplx": [{"hang": r[0], "count": r[1]} for r in lx_by_hang_gplx],
            "by_trang_thai": [{"trang_thai": r[0], "count": r[1]} for r in lx_by_trang_thai],
        },
    }


# ════════════════════════════════════════════════════════════════════════════
# BACKGROUND IMPORT TASK
# ════════════════════════════════════════════════════════════════════════════
