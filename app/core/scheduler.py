"""Scheduler chạy đêm: quét hết hạn + gửi nhắc (7h sáng hằng ngày).

Chống chạy trùng nhiều worker bằng unique (kenh, ref_loai, ref_id, ngay)
trong bảng thong_bao — worker nào insert trước thắng.
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.core.logging import logger
from app.services.notify_service import send_notifications

settings = get_settings()
_scheduler: AsyncIOScheduler | None = None


async def _job_nhac_het_han():
    try:
        async with AsyncSessionLocal() as db:
            from app.services import settings_service as svc
            enabled = await svc.get_effective(db, "SCHEDULER_ENABLED")
            if not enabled:
                logger.info("scheduler_skipped", reason="SCHEDULER_ENABLED=false")
                return
            stats = await send_notifications(db, None)
            await db.commit()
        logger.info("scheduler_nhac_het_han", **stats)
    except Exception as e:
        logger.error("scheduler_failed", error=str(e))


def start_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        return
    # Luôn đăng ký job; mỗi lần chạy kiểm tra SCHEDULER_ENABLED trong DB
    # nên bật/tắt trên màn hình Settings có hiệu lực ngay, không cần restart.
    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(_job_nhac_het_han, CronTrigger(hour=7, minute=0),
                       id="nhac_het_han", replace_existing=True)
    _scheduler.start()
    logger.info("scheduler_started", job="nhac_het_han 07:00 hằng ngày")


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("scheduler_stopped")
