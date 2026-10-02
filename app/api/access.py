"""Audit + phân quyền — nhật ký ai làm gì, ma trận role, gán role (admin)."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, User
from app.models.system import AuditLog
from app.services.audit_service import log_audit
from app.api.auth import require_roles

router = APIRouter(tags=["Audit & Phân quyền"])
AUDIT_READ = require_roles("admin", "dieu_hanh")


@router.get("/audit/logs", summary="Nhật ký ai làm gì",
            dependencies=[Depends(AUDIT_READ)])
async def list_audit(entity: Optional[str] = None, action: Optional[str] = None,
                     limit: int = Query(100, ge=1, le=500), db: AsyncSession = Depends(get_db)):
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    if entity:
        stmt = stmt.where(AuditLog.entity == entity)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    rows = (await db.execute(stmt)).scalars().all()
    return [{"id": r.id, "actor": r.actor_name, "action": r.action, "entity": r.entity,
             "entity_id": r.entity_id, "detail": r.detail,
             "created_at": r.created_at.isoformat() if r.created_at else None} for r in rows]


@router.get("/roles/matrix", summary="Ma trận phân quyền chuẩn HTX (đồng bộ menu frontend)")
async def roles_matrix():
    all_roles = ["admin", "dieu_hanh", "ke_toan", "van_phong", "lai_xe"]
    office = ["admin", "dieu_hanh", "van_phong"]
    return {
        "roles": all_roles,
        "role_labels": {
            "admin": "Quản trị", "dieu_hanh": "Điều hành", "ke_toan": "Kế toán",
            "van_phong": "Văn phòng", "lai_xe": "Lái xe",
        },
        "menus": {
            "/": all_roles,
            "/canh-bao": ["admin", "dieu_hanh", "ke_toan", "van_phong"],
            "/templates": office,
            "/render": office,
            "/bulk": office,
            "/jobs": office,
            "/phuong-tien": all_roles,
            "/lai-xe": all_roles,
            "/dieu-hanh": ["admin", "dieu_hanh"],
            "/bao-tri": ["admin", "dieu_hanh", "ke_toan"],
            "/xa-vien": ["admin", "dieu_hanh", "ke_toan"],
            "/settings": ["admin"],
        },
        "matrix": {
            "fleet.xem": all_roles,
            "fleet.sua": ["admin", "dieu_hanh"],
            "fleet.import": ["admin", "dieu_hanh"],
            "lenh.cap": ["admin", "dieu_hanh"],
            "taichinh.xem": ["admin", "dieu_hanh", "ke_toan"],
            "taichinh.sua": ["admin", "ke_toan"],
            "template.render": office,
            "cautruc.xem": all_roles,
            "config.sua": ["admin"],
        },
        "luu_y": "Admin luôn có mọi quyền. Menu frontend ẩn theo ma trận này; API chặn bằng require_roles.",
    }


@router.patch("/users/{user_id}/role", summary="Gán role cho user (admin)",
             dependencies=[Depends(require_roles("admin"))])
async def set_role(user_id: str, payload: dict, db: AsyncSession = Depends(get_db)):
    role = str(payload.get("role") or "").strip()
    if role not in ("admin", "dieu_hanh", "ke_toan", "van_phong", "lai_xe"):
        raise HTTPException(400, "role không hợp lệ")
    u = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not u:
        raise HTTPException(404, "User không tồn tại")
    if hasattr(u, "role"):
        u.role = role
    u.is_admin = (role == "admin")
    await log_audit(db, action="set_role", entity="user", entity_id=user_id, detail=role)
    return {"ok": True, "role": role}
