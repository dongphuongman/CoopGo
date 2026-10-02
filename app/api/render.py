"""
Render API:
  POST /render/{template_id}          - Render sync (nhỏ, nhanh)
  POST /render/{template_id}/async    - Render async → job_id
  GET  /render/jobs/{job_id}          - Check job status
  GET  /render/jobs/{job_id}/download - Download kết quả
"""
import uuid
import hashlib
import json as _json
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import get_db, Template, RenderJob, RenderStatus
from app.services.docx_service import render_docx
from app.services.pdf_service import convert_to_pdf
from app.schemas.render import RenderRequest, RenderJobResponse, RenderJobStatus, RenderJobListItem

router = APIRouter(prefix="/render", tags=["Render"])
settings = get_settings()


def _compute_hash(template_id: str, data: dict, output_format: str) -> str:
    """SHA-256 của (template_id + sorted JSON data + output_format) để detect duplicate renders."""
    payload = _json.dumps(
        {"template_id": template_id, "data": data, "fmt": output_format},
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


async def _find_cached_job(h: str, db: AsyncSession) -> RenderJob | None:
    """Tìm job DONE có cùng hash và file output còn tồn tại."""
    result = await db.execute(
        select(RenderJob)
        .where(RenderJob.payload_hash == h, RenderJob.status == RenderStatus.DONE)
        .order_by(RenderJob.created_at.desc())
        .limit(1)
    )
    job = result.scalar_one_or_none()
    if job and job.output_path and Path(job.output_path).exists():
        return job
    return None


@router.post("/{template_id}", summary="Render sync – trả về file ngay")
async def render_sync(
    template_id: str,
    payload: RenderRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Render template với dữ liệu → trả về file PDF/DOCX ngay.
    Nếu cùng hash (template + data + format) đã được render trước đó, trả về file cache.
    """
    template = await _get_template_or_404(template_id, db)

    h = _compute_hash(template_id, payload.data, payload.output_format)
    cached = await _find_cached_job(h, db)
    if cached:
        output_path = Path(cached.output_path)
        media_type = "application/pdf" if output_path.suffix == ".pdf" else \
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        return FileResponse(path=str(output_path), media_type=media_type, filename=output_path.name)

    output_path = await _do_render(template, payload)

    # Lưu job DONE để cache cho lần sau
    job = RenderJob(
        id=str(uuid.uuid4()),
        template_id=template_id,
        status=RenderStatus.DONE,
        input_data={"data": payload.data, "output_format": payload.output_format},
        output_path=str(output_path),
        payload_hash=h,
        completed_at=datetime.now(timezone.utc),
    )
    db.add(job)

    media_type = "application/pdf" if payload.output_format == "pdf" else \
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    return FileResponse(
        path=str(output_path),
        media_type=media_type,
        filename=output_path.name,
    )


@router.post("/{template_id}/async", response_model=RenderJobResponse, status_code=202,
             summary="Render async – nhận job_id, poll để lấy kết quả")
async def render_async(
    template_id: str,
    payload: RenderRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Tạo render job chạy background. Phù hợp cho file lớn, batch processing.
    Poll GET /render/jobs/{job_id} để kiểm tra status.
    Nếu cùng hash đã render xong, trả về job cũ ngay (cached=True).
    """
    await _get_template_or_404(template_id, db)

    h = _compute_hash(template_id, payload.data, payload.output_format)
    cached = await _find_cached_job(h, db)
    if cached:
        return RenderJobResponse(
            job_id=cached.id,
            template_id=cached.template_id,
            status=RenderJobStatus.DONE,
            download_url=f"/render/jobs/{cached.id}/download",
            created_at=cached.created_at,
            completed_at=cached.completed_at,
            payload_hash=h,
            cached=True,
        )

    job = RenderJob(
        id=str(uuid.uuid4()),
        template_id=template_id,
        status=RenderStatus.PENDING,
        input_data={"data": payload.data, "output_format": payload.output_format},
        payload_hash=h,
    )
    db.add(job)
    await db.flush()

    # Chạy background (production nên dùng Celery worker)
    background_tasks.add_task(_background_render, job.id, template_id, payload)

    return RenderJobResponse(
        job_id=job.id,
        template_id=template_id,
        status=RenderJobStatus.PENDING,
        created_at=job.created_at,
        payload_hash=h,
    )


@router.get("/jobs/", response_model=list[RenderJobListItem], summary="List render jobs gần đây")
async def list_jobs(
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """Lấy danh sách render jobs, mới nhất trước, kèm tên template."""
    stmt = (
        select(RenderJob, Template.name.label("template_name"))
        .join(Template, RenderJob.template_id == Template.id, isouter=True)
        .order_by(RenderJob.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.all()
    return [
        RenderJobListItem(
            job_id=row[0].id,
            template_id=row[0].template_id,
            template_name=row[1],
            status=RenderJobStatus(row[0].status),
            output_format=(row[0].input_data or {}).get("output_format", "pdf"),
            error_message=row[0].error_message,
            created_at=row[0].created_at,
            completed_at=row[0].completed_at,
            download_url=f"/render/jobs/{row[0].id}/download" if row[0].status == RenderStatus.DONE else None,
            payload_hash=row[0].payload_hash,
        )
        for row in rows
    ]


@router.get("/jobs/{job_id}", response_model=RenderJobResponse)
async def get_job_status(job_id: str, db: AsyncSession = Depends(get_db)):
    """Kiểm tra trạng thái render job."""
    job = await _get_job_or_404(job_id, db)

    download_url = None
    if job.status == RenderStatus.DONE and job.output_path:
        download_url = f"/render/jobs/{job_id}/download"

    return RenderJobResponse(
        job_id=job.id,
        template_id=job.template_id,
        status=RenderJobStatus(job.status),
        download_url=download_url,
        error_message=job.error_message,
        created_at=job.created_at,
        completed_at=job.completed_at,
    )


@router.get("/jobs/{job_id}/download", summary="Download kết quả render")
async def download_job_result(
    job_id: str,
    inline: bool = Query(False, description="True = xem trong trình duyệt (PDF)"),
    db: AsyncSession = Depends(get_db)
):
    """Download file output của render job."""
    job = await _get_job_or_404(job_id, db)

    if job.status != RenderStatus.DONE:
        raise HTTPException(status_code=400, detail=f"Job chưa hoàn thành: {job.status}")

    output_path = Path(job.output_path)
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="File output không tồn tại")

    media_type = "application/pdf" if output_path.suffix == ".pdf" else \
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    if inline and output_path.suffix == ".pdf":
        return FileResponse(
            path=str(output_path),
            media_type=media_type,
            headers={"Content-Disposition": "inline"},
        )
    return FileResponse(path=str(output_path), media_type=media_type, filename=output_path.name)


# ─── Background task ────────────────────────────────────────────────────────────

async def _background_render(job_id: str, template_id: str, payload: RenderRequest):
    """Chạy render trong background, cập nhật job status."""
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(select(RenderJob).where(RenderJob.id == job_id))
            job = result.scalar_one()
            job.status = RenderStatus.PROCESSING

            template_result = await db.execute(select(Template).where(Template.id == template_id))
            template = template_result.scalar_one()

            output_path = await _do_render(template, payload)

            job.status = RenderStatus.DONE
            job.output_path = str(output_path)
            job.completed_at = datetime.now(timezone.utc)
            await db.commit()

        except Exception as e:
            job.status = RenderStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.now(timezone.utc)
            await db.commit()


# ─── Core render logic ──────────────────────────────────────────────────────────

async def _do_render(template: Template, payload: RenderRequest) -> Path:
    job_id = uuid.uuid4().hex
    temp_docx = settings.TEMP_DIR / f"{job_id}.docx"

    try:
        # Normalize data trước khi render — fix lỗi paired list không đều
        context = _normalize_context(payload.data)

        await render_docx(template.filepath, context, temp_docx)

        if payload.output_format == "pdf":
            output_path = await convert_to_pdf(temp_docx, settings.OUTPUT_DIR)
        else:
            output_path = settings.OUTPUT_DIR / f"{job_id}.docx"
            temp_docx.rename(output_path)

        return output_path

    finally:
        temp_docx.unlink(missing_ok=True)


def _normalize_context(data: dict) -> dict:
    """
    Tự động detect và pad các cặp list song song (dạng *_trai / *_phai)
    để đảm bảo cùng độ dài — tránh lỗi 'list object has no element Undefined'.

    Ví dụ: hanh_khach_trai + hanh_khach_phai → pad list ngắn hơn bằng dict rỗng.
    """
    result = dict(data)

    # Tìm tất cả cặp key có suffix _trai / _phai
    trai_keys = [k for k in result if k.endswith("_trai") and isinstance(result[k], list)]

    for trai_key in trai_keys:
        base   = trai_key[:-5]          # "hanh_khach"
        phai_key = base + "_phai"

        if phai_key not in result or not isinstance(result[phai_key], list):
            continue

        list_trai = result[trai_key]
        list_phai = result[phai_key]
        target_len = max(len(list_trai), len(list_phai))

        if len(list_trai) == len(list_phai):
            continue  # Đã bằng nhau, không cần xử lý

        # Tạo empty record dựa theo keys của phần tử đầu tiên
        sample = (list_trai or list_phai)[0] if (list_trai or list_phai) else {}
        empty  = {k: "" for k in sample.keys()}

        result[trai_key] = list_trai + [empty] * (target_len - len(list_trai))
        result[phai_key] = list_phai + [empty] * (target_len - len(list_phai))

    return result


# ─── Helpers ────────────────────────────────────────────────────────────────────

async def _get_template_or_404(template_id: str, db: AsyncSession) -> Template:
    result = await db.execute(select(Template).where(Template.id == template_id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template không tồn tại")
    return template


async def _get_job_or_404(job_id: str, db: AsyncSession) -> RenderJob:
    result = await db.execute(select(RenderJob).where(RenderJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job không tồn tại")
    return job