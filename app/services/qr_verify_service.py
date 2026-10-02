"""Verify code + QR payload cho văn bản render.

Không thêm dep nặng (qrcode): backend sinh verify_code (hash ngắn),
verify_url; frontend tự render QR từ URL (lib có sẵn / api QR).
"""
from __future__ import annotations

import hashlib
import uuid


def new_verify_code(job_id: str, template_id: str = "") -> str:
    raw = f"{job_id}:{template_id}:{uuid.uuid4().hex}".encode()
    return hashlib.sha256(raw).hexdigest()[:12].upper()


def verify_url(code: str, base_url: str = "") -> str:
    base = (base_url or "").rstrip("/") or "https://htx.local/verify"
    return f"{base}/{code}"


def qr_text(code: str, bien_so: str = "", base_url: str = "") -> str:
    """Text nhúng vào template / QR: URL + biển số để CSGT quét nhanh."""
    url = verify_url(code, base_url)
    return f"{url}" if not bien_so else f"{url} | {bien_so}"
