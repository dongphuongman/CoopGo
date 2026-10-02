"""Notify service — nhắc hết hạn đăng kiểm/phù hiệu/BH/GPLX/KSK.

Kênh gửi (bật theo cấu hình, thiếu cấu hình = bỏ qua kênh đó):
- log: luôn ghi (để debug + lịch sử)
- email: SMTP (SMTP_HOST/USER/PASS + NOTIFY_EMAILS)
- zalo: Zalo OA API (ZALO_OA_TOKEN + ZALO_USER_IDS)

Chống gửi trùng: unique (kenh, ref_loai, ref_id, ngay) — nhiều worker
cùng chạy cũng chỉ 1 bản ghi được ghi nhận.
"""
from __future__ import annotations

import smtplib
from datetime import date
from email.message import EmailMessage

import httpx
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import logger
from app.models.system import ThongBao
from app.services.expiry_service import expiry_report

settings = get_settings()

LOAI_LABEL = {
    "dang_kiem": "đăng kiểm",
    "phu_hieu": "phù hiệu",
    "bao_hiem": "bảo hiểm TNDS",
    "gplx": "giấy phép lái xe",
    "ksk": "khám sức khỏe",
}


async def build_notifications(db: AsyncSession, within_days: int) -> list[dict]:
    """Dựng danh sách nhắc từ báo cáo hết hạn (chưa gửi)."""
    rep = await expiry_report(db, within_days)
    items: list[dict] = []
    for x in rep["phuong_tien"]:
        loai = x["loai"]
        muc = "ĐÃ HẾT HẠN" if x["muc"] == "expired" else f"còn {x['con_lai_ngay']} ngày"
        items.append({
            "ref_loai": loai,
            "ref_id": x["bien_so"],
            "tieu_de": f"Xe {x['bien_so']} {LOAI_LABEL.get(loai, loai)} {muc}",
            "noi_dung": (f"Phương tiện {x['bien_so']} ({x.get('extra') or ''}) "
                         f"{LOAI_LABEL.get(loai, loai)} hết hạn ngày {x['het_han']} ({muc})."),
        })
    for x in rep["lai_xe"]:
        loai = x["loai"]
        muc = "ĐÃ HẾT HẠN" if x["muc"] == "expired" else f"còn {x['con_lai_ngay']} ngày"
        items.append({
            "ref_loai": loai,
            "ref_id": x["doi_tuong"],
            "tieu_de": f"{x['doi_tuong']} {LOAI_LABEL.get(loai, loai)} {muc}",
            "noi_dung": (f"Lái xe {x['doi_tuong']} {LOAI_LABEL.get(loai, loai)} "
                         f"hết hạn ngày {x['het_han']} ({muc})."),
        })
    return items


def _channels(eff: dict) -> list[str]:
    ch = ["log"]
    if eff.get("SMTP_HOST") and eff.get("NOTIFY_EMAILS"):
        ch.append("email")
    if eff.get("ZALO_OA_TOKEN") and eff.get("ZALO_USER_IDS"):
        ch.append("zalo")
    return ch


def _send_email(eff: dict, subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["Subject"] = f"[CoopGo] {subject}"
    msg["From"] = eff.get("SMTP_FROM") or eff.get("SMTP_USER")
    msg["To"] = eff.get("NOTIFY_EMAILS")
    msg.set_content(body)
    with smtplib.SMTP(eff.get("SMTP_HOST"), int(eff.get("SMTP_PORT") or 587), timeout=20) as s:
        s.starttls()
        if eff.get("SMTP_USER"):
            s.login(eff.get("SMTP_USER"), eff.get("SMTP_PASS") or "")
        s.send_message(msg)


async def _send_zalo(eff: dict, text: str) -> None:
    async with httpx.AsyncClient(timeout=20.0) as client:
        for uid in [u.strip() for u in str(eff.get("ZALO_USER_IDS") or "").split(",") if u.strip()]:
            r = await client.post(
                "https://openapi.zalo.me/v3.0/oa/message/cs",
                headers={"access_token": eff.get("ZALO_OA_TOKEN"),
                         "Content-Type": "application/json"},
                json={"recipient": {"user_id": uid},
                      "message": {"text": text[:1000]}},
            )
            if r.status_code != 200 or r.json().get("error") not in (None, 0):
                raise RuntimeError(f"Zalo OA lỗi: {r.text[:200]}")


async def send_notifications(db: AsyncSession, within_days: int | None = None,
                             dry_run: bool = False) -> dict:
    """Gửi nhắc + ghi log chống trùng. Đọc cấu hình hiệu lực (DB ghi đè .env)."""
    from app.services import settings_service as svc
    eff = await svc.get_effective_map(db)
    if within_days is None:
        within_days = int(eff.get("NOTIFY_WITHIN_DAYS") or 30)
    items = await build_notifications(db, within_days)
    today = date.today()
    stats = {"total": len(items), "sent": 0, "skipped": 0, "failed": 0,
             "channels": _channels(eff), "within_days": within_days}

    for it in items:
        for kenh in stats["channels"]:
            # Bỏ qua nếu hôm nay đã gửi (kênh, ref) này
            exists = (await db.execute(select(ThongBao.id).where(
                ThongBao.kenh == kenh, ThongBao.ref_loai == it["ref_loai"],
                ThongBao.ref_id == it["ref_id"], ThongBao.ngay == today,
            ))).scalar_one_or_none()
            if exists:
                stats["skipped"] += 1
                continue
            if dry_run:
                stats["skipped"] += 1
                continue
            try:
                if kenh == "log":
                    logger.warning("nhac_het_han", tieu_de=it["tieu_de"])
                elif kenh == "email":
                    _send_email(eff, it["tieu_de"], it["noi_dung"])
                elif kenh == "zalo":
                    await _send_zalo(eff, f"[CoopGo] {it['tieu_de']}\n{it['noi_dung']}")
                db.add(ThongBao(kenh=kenh, loai="het_han", tieu_de=it["tieu_de"],
                                noi_dung=it["noi_dung"], ref_loai=it["ref_loai"],
                                ref_id=it["ref_id"], ngay=today, trang_thai="sent"))
                try:
                    await db.flush()
                except IntegrityError:
                    # worker khác gửi trước — bỏ qua
                    await db.rollback()
                    stats["skipped"] += 1
                    continue
                stats["sent"] += 1
            except Exception as e:
                stats["failed"] += 1
                try:
                    db.add(ThongBao(kenh=kenh, loai="het_han", tieu_de=it["tieu_de"],
                                    noi_dung=it["noi_dung"], ref_loai=it["ref_loai"],
                                    ref_id=it["ref_id"], ngay=today,
                                    trang_thai="failed", loi=str(e)[:500]))
                    await db.flush()
                except Exception:
                    await db.rollback()
    return stats
