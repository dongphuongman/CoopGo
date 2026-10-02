"""Audit helper — ghi log mọi thay đổi quan trọng (import/sửa/xóa/render)."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.coop_models import AuditLog


async def log_audit(
    db: AsyncSession,
    *,
    action: str,
    entity: str = "",
    entity_id: str = "",
    actor_id: str | None = None,
    actor_name: str = "",
    detail: str = "",
) -> None:
    try:
        db.add(AuditLog(
            actor_id=actor_id,
            actor_name=actor_name,
            action=action,
            entity=entity,
            entity_id=str(entity_id or ""),
            detail=detail,
        ))
        await db.flush()
    except Exception:
        pass  # audit không được làm fail nghiệp vụ chính
