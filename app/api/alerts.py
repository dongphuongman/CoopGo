"""Alerts API — cảnh báo hết hạn đăng kiểm/phù hiệu/BH/GPLX/KSK.

GET /alerts/expiry?within_days=30 — danh sách sắp hết hạn, sort gấp trước
GET /alerts/summary — số liệu cho Dashboard fleet
GET /alerts/notify-preview — xem trước nội dung sẽ gửi nhắc
POST /alerts/notify — gửi nhắc ngay (chống trùng theo ngày)
GET /alerts/notifications — lịch sử đã gửi
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.coop_models import ThongBao
from app.services.expiry_service import expiry_report
from app.services.notify_service import build_notifications, send_notifications
from app.api.auth import require_roles

router = APIRouter(prefix="/alerts", tags=["Alerts - Cảnh báo hết hạn"])

NOTIFY_WRITE = require_roles("admin", "dieu_hanh")


@router.get("/expiry", summary="Danh sách sắp hết hạn")
async def get_expiry(
    within_days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    return await expiry_report(db, within_days)


@router.get("/summary", summary="Số liệu tổng hợp cho dashboard")
async def get_summary(db: AsyncSession = Depends(get_db)):
    r30 = await expiry_report(db, 30)
    r7 = await expiry_report(db, 7)
    return {
        "today": r30["today"],
        "sap_het_han_30_ngay": r30["tong"],
        "sap_het_han_7_ngay": r7["tong"],
        "da_het_han": r30["het_han"],
        "chi_tiet_7_ngay": {"phuong_tien": r7["phuong_tien"], "lai_xe": r7["lai_xe"]},
    }


@router.get("/notify-preview", summary="Xem trước nội dung sẽ gửi nhắc")
async def notify_preview(within_days: int | None = Query(None, ge=1, le=365),
                         db: AsyncSession = Depends(get_db)):
    from app.services import settings_service as svc
    if within_days is None:
        within_days = int(await svc.get_effective(db, "NOTIFY_WITHIN_DAYS") or 30)
    items = await build_notifications(db, within_days)
    return {"within_days": within_days, "total": len(items), "items": items[:50]}


@router.post("/notify", summary="Gửi nhắc hết hạn ngay (chống gửi trùng trong ngày)",
             dependencies=[Depends(NOTIFY_WRITE)])
async def notify_now(within_days: int | None = Query(None, ge=1, le=365),
                     db: AsyncSession = Depends(get_db)):
    return await send_notifications(db, within_days)


@router.get("/notifications", summary="Lịch sử thông báo đã gửi")
async def notification_history(limit: int = Query(50, ge=1, le=200),
                               db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(ThongBao).order_by(ThongBao.created_at.desc())
                             .limit(limit))).scalars().all()
    return [{"id": r.id, "kenh": r.kenh, "tieu_de": r.tieu_de,
             "ref_loai": r.ref_loai, "ref_id": r.ref_id,
             "trang_thai": r.trang_thai, "ngay": str(r.ngay),
             "created_at": r.created_at.isoformat() if r.created_at else None}
            for r in rows]
