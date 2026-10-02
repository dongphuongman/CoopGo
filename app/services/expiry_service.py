"""Expiry service — tính danh sách sắp hết hạn đăng kiểm/phù hiệu/BH/GPLX/KSK.

Dùng cột Date mới; fallback parse String cũ để tương thích dữ liệu import trước đây.
"""
from __future__ import annotations

from datetime import date
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fleet_models import PhuongTien, LaiXe
from app.utils.date_parse import parse_vn_date, days_until, expiry_level, as_iso

LOAI_LABEL = {
    "dang_kiem": "Đăng kiểm",
    "phu_hieu": "Phù hiệu",
    "bao_hiem": "Bảo hiểm TNDS",
    "gplx": "GPLX",
    "ksk": "Khám sức khỏe",
}


def _eff_date(date_col, str_val):
    d = date_col if hasattr(date_col, "year") else None
    if d:
        return d
    return parse_vn_date(str_val)


async def expiry_report(db: AsyncSession, within_days: int = 30) -> dict:
    today = date.today()
    pts = (await db.execute(select(PhuongTien))).scalars().all()
    lxs = (await db.execute(select(LaiXe))).scalars().all()

    def item(bien_so, loai, het_han, extra=""):
        days = days_until(het_han, today)
        return {
            "bien_so": bien_so, "doi_tuong": bien_so,
            "loai": loai, "loai_label": LOAI_LABEL.get(loai, loai),
            "het_han": as_iso(het_han),
            "con_lai_ngay": days, "muc": expiry_level(days),
            "extra": extra,
        }

    def item_lx(ho_ten, loai, het_han):
        days = days_until(het_han, today)
        return {
            "doi_tuong": ho_ten, "loai": loai, "loai_label": LOAI_LABEL.get(loai, loai),
            "het_han": as_iso(het_han),
            "con_lai_ngay": days, "muc": expiry_level(days),
        }

    pt_alerts, lx_alerts = [], []
    for r in pts:
        for loai, dc, sv in [
            ("dang_kiem", r.han_dang_kiem_date, r.han_dang_kiem),
            ("phu_hieu", r.han_phu_hieu_date, r.han_phu_hieu),
            ("bao_hiem", r.han_bao_hiem_date, r.han_bao_hiem),
        ]:
            het = dc if dc else parse_vn_date(sv)
            days = days_until(het, today)
            if het and (days is not None and days <= within_days):
                pt_alerts.append(item(r.bien_so, loai, het, r.hang_xe or ""))
    for r in lxs:
        het_gplx = r.han_gplx_date if r.han_gplx_date else parse_vn_date(r.han_gplx)
        days = days_until(het_gplx, today)
        if het_gplx and days is not None and days <= within_days:
            lx_alerts.append(item_lx(r.ho_ten, "gplx", het_gplx))
        het_ksk = r.ksk_ngay_kham_date if getattr(r, "ksk_ngay_kham_date", None) else parse_vn_date(r.ksk_ngay_kham)
        # KSK hiệu lực ~6 tháng: hết hạn = ngày khám + 180 ngày (ước lượng)
        if het_ksk and not (r.ksk_ket_qua and "không" in str(r.ksk_ket_qua).lower()):
            from datetime import timedelta
            het_ksk_exp = het_ksk + timedelta(days=180)
            days2 = days_until(het_ksk_exp, today)
            if days2 is not None and days2 <= within_days:
                lx_alerts.append(item_lx(r.ho_ten, "ksk", het_ksk_exp))

    rank = {"expired": 0, "critical": 1, "warning": 2, "notice": 3, "ok": 4, "unknown": 5}
    pt_alerts.sort(key=lambda x: (rank.get(x["muc"], 9), x["con_lai_ngay"] or 9999))
    lx_alerts.sort(key=lambda x: (rank.get(x["muc"], 9), x["con_lai_ngay"] or 9999))

    return {
        "today": today.isoformat(),
        "within_days": within_days,
        "phuong_tien": pt_alerts,
        "lai_xe": lx_alerts,
        "tong": len(pt_alerts) + len(lx_alerts),
        "het_han": sum(1 for x in pt_alerts + lx_alerts if x["muc"] == "expired"),
    }
