"""Bulk render API — render hàng loạt + render kèm mã QR verify."""
import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, Template, RenderJob, RenderStatus
from app.models.system import VanBanVerify
from app.models.fleet_models import PhuongTien
from app.services.qr_verify_service import new_verify_code, verify_url
from app.services.audit_service import log_audit
from app.api.auth import require_roles
from app.api.render import _do_render

router = APIRouter(tags=["Bulk render"])
OPS_WRITE = require_roles("admin", "dieu_hanh", "van_phong")


class BulkFleetIn(BaseModel):
    template_id: str
    bien_so_list: list[str] = []
    phuong_tien_ids: list[str] = []
    output_format: str = "pdf"
    extra_data: dict = {}
    gan_verify: bool = True


@router.post("/bulk/render-fleet", summary="Render hàng loạt từ danh sách xe",
             dependencies=[Depends(OPS_WRITE)])
async def bulk_render_fleet(payload: BulkFleetIn, background_tasks: BackgroundTasks,
                            db: AsyncSession = Depends(get_db)):
    tpl = (await db.execute(select(Template).where(Template.id == payload.template_id))).scalar_one_or_none()
    if not tpl:
        raise HTTPException(404, "Template không tồn tại")
    # Lấy xe theo ids hoặc biển số
    pts: list[PhuongTien] = []
    if payload.phuong_tien_ids:
        pts = (await db.execute(select(PhuongTien).where(PhuongTien.id.in_(payload.phuong_tien_ids)))).scalars().all()
    elif payload.bien_so_list:
        pts = (await db.execute(select(PhuongTien).where(PhuongTien.bien_so.in_(payload.bien_so_list)))).scalars().all()
    else:
        raise HTTPException(400, "Cần bien_so_list hoặc phuong_tien_ids")
    if not pts:
        raise HTTPException(404, "Không tìm thấy xe nào")

    jobs = []
    for pt in pts:
        job_id = str(uuid.uuid4())
        data = {"bien_so": pt.bien_so, "hang_xe": pt.hang_xe, "so_cho": pt.so_cho,
                "tuyen_khai_thac": pt.tuyen_khai_thac, "han_dang_kiem": pt.han_dang_kiem,
                "han_phu_hieu": pt.han_phu_hieu, "han_bao_hiem": pt.han_bao_hiem,
                **(payload.extra_data or {})}
        code = new_verify_code(job_id, tpl.id) if payload.gan_verify else None
        if code:
            data["verify_code"] = code
            data["verify_url"] = verify_url(code)
            data["qr_text"] = data["verify_url"]
        job = RenderJob(id=job_id, template_id=tpl.id, status=RenderStatus.PENDING,
                        input_data={"data": data, "output_format": payload.output_format,
                                    "bien_so": pt.bien_so, "verify_code": code})
        db.add(job)
        jobs.append((job_id, pt.bien_so, code))
        background_tasks.add_task(_bulk_one, job_id, tpl.id, data, payload.output_format, code,
                                  tpl.name, pt.bien_so)
    await db.flush()
    await log_audit(db, action="bulk_render", entity="template", entity_id=tpl.id,
                    detail=f"{len(jobs)} xe")
    return {"template": tpl.name, "total": len(jobs),
            "jobs": [{"job_id": j, "bien_so": b,
                      "download_url": f"/render/jobs/{j}/download",
                      "verify_code": c,
                      "verify_url": verify_url(c) if c else None} for j, b, c in jobs]}


async def _bulk_one(job_id: str, template_id: str, data: dict, fmt: str,
                    code: Optional[str], tpl_name: str, bien_so: str):
    from app.core.database import AsyncSessionLocal
    from app.api.render import RenderRequest
    async with AsyncSessionLocal() as db:
        try:
            r = await db.execute(select(RenderJob).where(RenderJob.id == job_id))
            job = r.scalar_one()
            job.status = RenderStatus.PROCESSING
            t = (await db.execute(select(Template).where(Template.id == template_id))).scalar_one()
            out = await _do_render(t, RenderRequest(data=data, output_format=fmt))
            job.status = RenderStatus.DONE
            job.output_path = str(out)
            job.completed_at = datetime.now(timezone.utc)
            if code:
                db.add(VanBanVerify(verify_code=code, render_job_id=job_id,
                                    template_id=template_id, template_name=tpl_name,
                                    bien_so=bien_so,
                                    payload_summary=json.dumps({"bien_so": bien_so}, ensure_ascii=False)))
            await db.commit()
        except Exception as e:
            r = await db.execute(select(RenderJob).where(RenderJob.id == job_id))
            job = r.scalar_one_or_none()
            if job:
                job.status = RenderStatus.FAILED
                job.error_message = str(e)
                job.completed_at = datetime.now(timezone.utc)
                await db.commit()


@router.post("/render/{template_id}/with-verify", summary="Render 1 văn bản kèm mã QR verify",
             dependencies=[Depends(OPS_WRITE)])
async def render_with_verify(template_id: str, payload: dict, background_tasks: BackgroundTasks,
                              db: AsyncSession = Depends(get_db)):
    from app.api.render import RenderRequest
    tpl = (await db.execute(select(Template).where(Template.id == template_id))).scalar_one_or_none()
    if not tpl:
        raise HTTPException(404, "Template không tồn tại")
    data = dict(payload.get("data") or {})
    fmt = payload.get("output_format", "pdf")
    job_id = str(uuid.uuid4())
    code = new_verify_code(job_id, template_id)
    data.update({"verify_code": code, "verify_url": verify_url(code), "qr_text": verify_url(code)})
    job = RenderJob(id=job_id, template_id=template_id, status=RenderStatus.PENDING,
                    input_data={"data": data, "output_format": fmt,
                                "verify_code": code,
                                "bien_so": data.get("bien_so")})
    db.add(job)
    await db.flush()
    background_tasks.add_task(_bulk_one, job_id, template_id, data, fmt, code, tpl.name,
                              str(data.get("bien_so") or ""))
    return {"job_id": job_id, "status": "pending", "verify_code": code,
            "verify_url": verify_url(code),
            "download_url": f"/render/jobs/{job_id}/download"}
