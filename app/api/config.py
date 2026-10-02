"""
Config API: cấu hình hệ thống qua màn hình Settings (lưu DB, không cần .env).
  GET  /config/      - Toàn bộ nhóm + giá trị hiệu lực (admin)
  PATCH /config/     - Lưu nhiều key {settings: {KEY: value}} (admin)
    value null = khôi phục mặc định .env; password rỗng = giữ nguyên
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.auth import require_roles
from app.services import settings_service as svc

router = APIRouter(prefix="/config", tags=["Config"])

ADMIN = require_roles("admin")


class ConfigUpdate(BaseModel):
    settings: dict


@router.get("/", summary="Xem toàn bộ cấu hình (admin)")
async def get_config(db: AsyncSession = Depends(get_db),
                     _: object = Depends(ADMIN)):
    items = await svc.get_all(db)
    by_group: dict[str, list] = {}
    for it in items:
        by_group.setdefault(it["group"], []).append({
            "key": it["key"], "label": it["label"], "hint": it.get("hint", ""),
            "type": it["type"], "value": it["value"], "source": it["source"],
            "restart": bool(it.get("restart", False)),
            "min": it.get("min"), "max": it.get("max"),
            "has_value": bool(it["value"]) if it["type"] == "password" else None,
        })
    groups = [{**g, "settings": by_group.get(g["id"], [])} for g in svc.GROUPS]
    return {"groups": groups}


@router.patch("/", summary="Lưu cấu hình (admin)")
async def update_config(payload: ConfigUpdate, db: AsyncSession = Depends(get_db),
                        _: object = Depends(ADMIN)):
    try:
        items = await svc.update_many(db, payload.settings or {})
    except ValueError as e:
        raise HTTPException(422, str(e))
    return {"ok": True, "updated": list((payload.settings or {}).keys())}
