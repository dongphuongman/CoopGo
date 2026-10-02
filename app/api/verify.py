"""Tra cứu công khai — KHÔNG cần đăng nhập (CSGT quét QR)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db, RenderJob, RenderStatus
from app.models.system import VanBanVerify
from app.models.ops import LenhVanChuyen

public_router = APIRouter(tags=["Public - Tra cứu công khai"])
settings = get_settings()


@public_router.get("/verify/{code}", summary="Tra cứu văn bản bằng mã QR (công khai, không cần đăng nhập)")
async def verify_doc(code: str, db: AsyncSession = Depends(get_db)):
    code = code.upper()
    v = (await db.execute(select(VanBanVerify).where(VanBanVerify.verify_code == code))).scalar_one_or_none()
    if v:
        job = (await db.execute(select(RenderJob).where(RenderJob.id == v.render_job_id))).scalar_one_or_none()
        return {"hop_le": True, "verify_code": v.verify_code, "template": v.template_name,
                "bien_so": v.bien_so, "created_at": v.created_at,
                "download_url": f"/render/jobs/{v.render_job_id}/download" if job and job.status == RenderStatus.DONE else None}
    # Lệnh vận chuyển (có verify_code riêng, không qua render)
    lenh = (await db.execute(select(LenhVanChuyen).where(LenhVanChuyen.verify_code == code))).scalar_one_or_none()
    if lenh:
        return {"hop_le": True, "verify_code": lenh.verify_code,
                "template": "Lệnh vận chuyển",
                "so_lenh": lenh.so_lenh, "bien_so": lenh.bien_so,
                "created_at": lenh.created_at, "download_url": None}
    # fallback: tìm trong render job input (job cũ chưa có VanBanVerify)
    jobs = (await db.execute(select(RenderJob).where(RenderJob.status == RenderStatus.DONE)
                             .order_by(RenderJob.created_at.desc()).limit(200))).scalars().all()
    for j in jobs:
        if (j.input_data or {}).get("verify_code") == code:
            return {"hop_le": True, "verify_code": code,
                    "template": None, "bien_so": (j.input_data or {}).get("bien_so"),
                    "created_at": j.created_at, "download_url": f"/render/jobs/{j.id}/download"}
    raise HTTPException(404, "Mã xác thực không tồn tại (văn bản giả?)")


@public_router.get("/lenh-qr/{code}", summary="Ảnh QR tra cứu lệnh (PNG, công khai)")
async def lenh_qr(code: str):
    """QR trỏ tới trang xác thực công khai /verify/{code} trên web."""
    import io
    import qrcode
    from fastapi.responses import StreamingResponse
    url = f"{settings.PUBLIC_WEB_URL.rstrip('/')}/verify/{code.upper()}"
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")
