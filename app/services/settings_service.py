"""Cấu hình hệ thống qua màn hình Settings — lưu DB, ghi đè .env.

- GET /config → danh sách nhóm + từng key kèm giá trị hiệu lực + nguồn
- PATCH /config {settings: {KEY: value}} → validate + lưu DB (value null = về mặc định)
- Mật khẩu: gửi rỗng = giữ nguyên, không ghi đè
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.system import AppSetting

_env = get_settings()

TYPES = ("bool", "int", "float", "string", "text", "password")


def _env_default(key: str):
    return getattr(_env, key, None)


def _parse_bool(v) -> bool:
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    if s in ("1", "true", "yes", "on", "y", "có", "bat", "bật"):
        return True
    if s in ("0", "false", "no", "off", "n", "không", "tat", "tắt", ""):
        return False
    raise ValueError(f"Giá trị boolean không hợp lệ: {v!r}")


def coerce(key: str, raw):
    """Ép kiểu + validate theo type của key. Raise ValueError nếu sai."""
    t = DEF_MAP[key]["type"]
    if raw is None:
        return None
    if t == "bool":
        return _parse_bool(raw)
    if t == "int":
        iv = int(float(raw))
        mn, mx = DEF_MAP[key].get("min"), DEF_MAP[key].get("max")
        if (mn is not None and iv < mn) or (mx is not None and iv > mx):
            raise ValueError(f"{key} phải trong khoảng {mn}..{mx}")
        return iv
    if t == "float":
        fv = float(raw)
        mn, mx = DEF_MAP[key].get("min"), DEF_MAP[key].get("max")
        if (mn is not None and fv < mn) or (mx is not None and fv > mx):
            raise ValueError(f"{key} phải trong khoảng {mn}..{mx}")
        return fv
    return str(raw)


def to_str(key: str, v) -> str | None:
    if v is None:
        return None
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v)


def from_str(key: str, s: str | None):
    if s is None:
        return _env_default(key)
    t = DEF_MAP[key]["type"]
    if t == "bool":
        return _parse_bool(s)
    if t == "int":
        return int(s)
    if t == "float":
        return float(s)
    return s


async def get_all(db: AsyncSession) -> list[dict]:
    """Toàn bộ defs kèm giá trị hiệu lực + nguồn (env/db)."""
    rows = (await db.execute(select(AppSetting))).scalars().all()
    over = {r.key: r.value for r in rows}
    out = []
    for d in SETTING_DEFS:
        k = d["key"]
        if k in over:
            out.append({**d, "value": from_str(k, over[k]), "source": "db"})
        else:
            out.append({**d, "value": _env_default(k), "source": "env"})
    return out


async def get_effective(db: AsyncSession, key: str):
    row = (await db.execute(select(AppSetting).where(AppSetting.key == key))).scalar_one_or_none()
    if row is None:
        return _env_default(key)
    return from_str(key, row.value)


async def get_effective_map(db: AsyncSession, keys: list[str] | None = None) -> dict:
    rows = (await db.execute(select(AppSetting))).scalars().all()
    over = {r.key: r.value for r in rows}
    out = {}
    for d in SETTING_DEFS:
        k = d["key"]
        if keys is not None and k not in keys:
            continue
        out[k] = from_str(k, over[k]) if k in over else _env_default(k)
    return out


async def update_many(db: AsyncSession, payload: dict) -> list[dict]:
    """Lưu nhiều key. value None = xóa override (về mặc định .env)."""
    for k in payload:
        if k not in DEF_MAP:
            raise ValueError(f"Key không hỗ trợ sửa qua UI: {k}")
    for k, raw in payload.items():
        t = DEF_MAP[k]["type"]
        if raw is None or (t == "password" and str(raw or "") == ""):
            if raw is None:  # null = khôi phục mặc định
                row = (await db.execute(select(AppSetting).where(AppSetting.key == k))).scalar_one_or_none()
                if row:
                    await db.delete(row)
            continue  # password rỗng = giữ nguyên
        val = coerce(k, raw)
        row = (await db.execute(select(AppSetting).where(AppSetting.key == k))).scalar_one_or_none()
        s = to_str(k, val)
        if row:
            row.value = s
        else:
            db.add(AppSetting(key=k, value=s))
    await db.flush()
    return await get_all(db)


SETTING_DEFS: list[dict] = [
    # ── Nhắc hết hạn ──
    {"key": "SCHEDULER_ENABLED", "group": "notify", "type": "bool",
     "label": "Tự động nhắc hằng đêm",
     "hint": "Bật job quét hết hạn lúc 7h sáng mỗi ngày. Có hiệu lực ngay, không cần restart."},
    {"key": "NOTIFY_WITHIN_DAYS", "group": "notify", "type": "int", "min": 1, "max": 365,
     "label": "Nhắc trước (ngày)",
     "hint": "Nhắc các giấy tờ hết hạn trong vòng X ngày tới."},
    {"key": "NOTIFY_EMAILS", "group": "notify", "type": "text",
     "label": "Email nhận nhắc",
     "hint": "Cách nhau dấu phẩy. Để trống = không gửi mail."},
    {"key": "SMTP_HOST", "group": "notify", "type": "string",
     "label": "SMTP host", "hint": "VD: smtp.gmail.com. Dùng App Password cho Gmail."},
    {"key": "SMTP_PORT", "group": "notify", "type": "int", "min": 1, "max": 65535,
     "label": "SMTP port", "hint": "Thường là 587 (STARTTLS)."},
    {"key": "SMTP_USER", "group": "notify", "type": "string",
     "label": "SMTP user", "hint": "Tài khoản đăng nhập SMTP."},
    {"key": "SMTP_PASS", "group": "notify", "type": "password",
     "label": "SMTP password", "hint": "Để trống = giữ nguyên mật khẩu đã lưu."},
    {"key": "SMTP_FROM", "group": "notify", "type": "string",
     "label": "Email người gửi", "hint": "Để trống = dùng SMTP user."},
    {"key": "ZALO_OA_TOKEN", "group": "notify", "type": "password",
     "label": "Zalo OA access token", "hint": "Lấy ở developers.zalo.me → OA → Access token. Để trống = giữ nguyên."},
    {"key": "ZALO_USER_IDS", "group": "notify", "type": "text",
     "label": "Zalo user IDs nhận nhắc", "hint": "User ID đã follow OA, cách nhau dấu phẩy."},
    # ── AI ──
    {"key": "AI_ENABLED", "group": "ai", "type": "bool",
     "label": "Bật AI gán nhãn",
     "hint": "Tự gán nhãn tiếng Việt khi upload template. Tắt = dùng từ điển có sẵn."},
    {"key": "OLLAMA_API_KEY", "group": "ai", "type": "password",
     "label": "Ollama API key", "hint": "Để trống = giữ nguyên key đã lưu."},
    # ── Render & upload ──
    {"key": "MAX_UPLOAD_MB", "group": "render", "type": "float", "min": 1, "max": 200,
     "label": "Dung lượng upload tối đa (MB)",
     "hint": "Áp dụng cho Excel import và template. Có hiệu lực ngay."},
    {"key": "PUBLIC_WEB_URL", "group": "render", "type": "string",
     "label": "URL web công khai",
     "hint": "QR trên lệnh trỏ về đây + /verify/{mã}. VD: https://htx.example.com"},
    {"key": "MAX_CONCURRENT_RENDERS", "group": "render", "type": "int", "min": 1, "max": 50,
     "label": "Render đồng thời tối đa",
     "hint": "⚠ Cần restart API mới có hiệu lực.", "restart": True},
    {"key": "RENDER_TIMEOUT_SECONDS", "group": "render", "type": "int", "min": 10, "max": 300,
     "label": "Timeout render (giây)",
     "hint": "⚠ Cần restart API mới có hiệu lực.", "restart": True},
]

DEF_MAP = {d["key"]: d for d in SETTING_DEFS}

GROUPS = [
    {"id": "notify", "title": "Nhắc hết hạn", "hint": "Kênh gửi, lịch tự động và người nhận"},
    {"id": "ai", "title": "AI gán nhãn", "hint": "Tự động đặt nhãn tiếng Việt cho template"},
    {"id": "render", "title": "Render & Upload", "hint": "Xuất tài liệu, dung lượng file, QR công khai"},
]
