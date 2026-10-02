"""Dashboard API — số liệu tổng hợp cho trang chỉ huy HTX."""
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.fleet_models import PhuongTien, LaiXe
from app.models.coop_models import Tuyen, XaVien, LenhVanChuyen, DoanhThu
from app.services.expiry_service import expiry_report

router = APIRouter(prefix="/dashboard", tags=["Dashboard - Chỉ huy"])


@router.get("/summary", summary="Tổng hợp chỉ huy: xe, lệnh hôm nay, hết hạn, doanh thu tháng")
async def summary(db: AsyncSession = Depends(get_db)):
    today = date.today()
    thang = today.strftime("%Y-%m")

    total_xe = (await db.execute(select(func.count(PhuongTien.id)))).scalar() or 0
    total_lx = (await db.execute(select(func.count(LaiXe.id)))).scalar() or 0
    total_tuyen = (await db.execute(select(func.count(Tuyen.id)))).scalar() or 0
    total_xv = (await db.execute(select(func.count(XaVien.id)))).scalar() or 0
    lenh_homnay = (await db.execute(
        select(func.count(LenhVanChuyen.id)).where(LenhVanChuyen.ngay_xuat_ben == today)
    )).scalar() or 0

    exp = await expiry_report(db, 30)
    muc_count: dict[str, int] = {}
    for x in exp["phuong_tien"] + exp["lai_xe"]:
        muc_count[x["muc"]] = muc_count.get(x["muc"], 0) + 1

    dt = (await db.execute(select(DoanhThu).where(DoanhThu.thang == thang))).scalars().all()
    tong_dt = sum(r.doanh_thu or 0 for r in dt)
    tong_cp = sum(r.chi_phi or 0 for r in dt)

    lenh_moi = (await db.execute(
        select(LenhVanChuyen).order_by(LenhVanChuyen.created_at.desc()).limit(5)
    )).scalars().all()

    return {
        "today": today.isoformat(),
        "thang": thang,
        "xe": {"tong": total_xe},
        "lai_xe": {"tong": total_lx},
        "tuyen": {"tong": total_tuyen},
        "xa_vien": {"tong": total_xv},
        "lenh_homnay": lenh_homnay,
        "het_han": {
            "tong_30_ngay": exp["tong"],
            "da_het_han": exp["het_han"],
            "theo_muc": muc_count,
            "gap_nhat": (exp["phuong_tien"] + exp["lai_xe"])[:5],
        },
        "doanh_thu_thang": {
            "thang": thang, "tong_doanh_thu": tong_dt,
            "tong_chi_phi": tong_cp, "loi_nhuan": tong_dt - tong_cp,
        },
        "lenh_moi": [
            {"so_lenh": r.so_lenh, "bien_so": r.bien_so,
             "ngay_xuat_ben": str(r.ngay_xuat_ben) if r.ngay_xuat_ben else None,
             "verify_code": r.verify_code}
            for r in lenh_moi
        ],
    }
