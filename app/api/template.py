"""
Template API:
  POST /templates/          - Upload template .docx → parse + AI label
  GET  /templates/          - List tất cả templates
  GET  /templates/{id}      - Chi tiết template
  PATCH /templates/{id}/labels - Override labels
  DELETE /templates/{id}    - Xóa template
"""
import uuid
import copy
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm.attributes import flag_modified
from app.core.config import get_settings
from app.core.database import get_db, Template
from app.core.template_parser import parse_template
from app.services.ai_service import generate_labels_with_ai, rule_based_hints
from app.api.auth import require_roles
from app.utils.uploads import save_upload_limited
from app.schemas.template import (
    TemplateCreateResponse, TemplateDetailResponse,
    LabelConfigUpdate, TemplateMeta, FieldMeta, TableMeta
)

TPL_WRITE = require_roles("admin", "dieu_hanh", "van_phong")
TPL_DELETE = require_roles("admin", "dieu_hanh")

router = APIRouter(prefix="/templates", tags=["Templates"])
settings = get_settings()


@router.post("/", response_model=TemplateCreateResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(TPL_WRITE)])
async def upload_template(
    file: UploadFile = File(..., description="File .docx template (Jinja2 syntax)"),
    name: str = Form(..., description="Tên template"),
    description: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload template .docx → tự động parse placeholder + AI generate labels tiếng Việt.
    """
    # Lưu file (giới hạn dung lượng + đúng .docx)
    template_id = str(uuid.uuid4())
    safe_filename = f"{template_id}_{file.filename}"
    filepath = settings.UPLOAD_DIR / safe_filename
    await save_upload_limited(file, filepath,
                              allowed_exts=(".docx",),
                              max_mb=settings.MAX_UPLOAD_MB)

    # Parse template
    try:
        parsed = parse_template(filepath)
    except Exception as e:
        filepath.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail=f"Không thể parse template: {e}")

    # AI generate labels cho tất cả keys
    all_keys = [f["key"] for f in parsed["fields"]]
    for table in parsed["tables"]:
        all_keys.extend(table["columns"])

    ai_labels = await generate_labels_with_ai(all_keys) if all_keys else {}
    hints = rule_based_hints(all_keys)

    # Build metadata với labels
    fields = [
        FieldMeta(
            key=f["key"],
            label=ai_labels.get(f["key"], f["key"]),
            type=f["type"],
            description=hints.get(f["key"]),
        )
        for f in parsed["fields"]
    ]

    tables = [
        TableMeta(
            key=t["key"],
            loop_var=t["loop_var"],
            columns=t["columns"],
            column_labels={col: ai_labels.get(col, col) for col in t["columns"]},
            column_hints={col: hints[col] for col in t["columns"] if col in hints},
            access=t.get("access", "loop"),
        )
        for t in parsed["tables"]
    ]

    metadata = TemplateMeta(fields=fields, tables=tables)

    # Lưu vào DB
    template = Template(
        id=template_id,
        name=name,
        description=description,
        filename=file.filename,
        filepath=str(filepath),
        field_metadata=metadata.model_dump(),
        label_config={},
    )
    db.add(template)
    await db.flush()
    await db.refresh(template)  # load server-default values (created_at, etc.)

    return TemplateCreateResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        filename=template.filename,
        metadata=metadata,
        created_at=template.created_at,
    )


@router.get("/", response_model=list[TemplateDetailResponse])
async def list_templates(db: AsyncSession = Depends(get_db)):
    """Lấy danh sách tất cả templates."""
    result = await db.execute(select(Template).order_by(Template.created_at.desc()))
    templates = result.scalars().all()
    return [_to_response(t) for t in templates]


@router.get("/{template_id}", response_model=TemplateDetailResponse)
async def get_template(template_id: str, db: AsyncSession = Depends(get_db)):
    """Lấy chi tiết một template."""
    template = await _get_or_404(template_id, db)
    return _to_response(template)


@router.patch("/{template_id}/labels", response_model=TemplateDetailResponse,
             dependencies=[Depends(TPL_WRITE)])
async def update_labels(
    template_id: str,
    payload: LabelConfigUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Override labels tiếng Việt cho template.
    Cho phép user chỉnh sửa label nếu AI generate chưa đúng.
    """
    template = await _get_or_404(template_id, db)

    # Ghi đè bằng dict MỚI để SQLAlchemy phát hiện thay đổi JSON column
    template.label_config = {**(template.label_config or {}), **payload.labels}
    flag_modified(template, "label_config")

    # Cập nhật labels trong metadata — deep copy để tạo object mới
    if template.field_metadata:
        meta = copy.deepcopy(template.field_metadata)
        for field in meta.get("fields", []):
            if field["key"] in payload.labels:
                field["label"] = payload.labels[field["key"]]
        for table in meta.get("tables", []):
            for col in table.get("columns", []):
                col_key = f"{table['key']}.{col}"
                if col_key in payload.labels:
                    table["column_labels"][col] = payload.labels[col_key]
                elif col in payload.labels:
                    table["column_labels"][col] = payload.labels[col]
        template.field_metadata = meta
        flag_modified(template, "field_metadata")

    await db.flush()
    return _to_response(template)


@router.post("/{template_id}/relabel", response_model=TemplateDetailResponse,
             summary="Chuẩn hóa lại nhãn tiếng Việt có dấu (giữ nhãn user đã sửa)",
             dependencies=[Depends(TPL_WRITE)])
async def relabel_template(template_id: str, db: AsyncSession = Depends(get_db)):
    """
    Sinh lại nhãn tiếng Việt có dấu + hint cho template đã upload trước đây.
    Các nhãn user đã chỉnh tay (label_config) được giữ nguyên.
    """
    template = await _get_or_404(template_id, db)
    meta = copy.deepcopy(template.field_metadata or {"fields": [], "tables": []})
    manual = template.label_config or {}

    keys = [f["key"] for f in meta.get("fields", [])]
    for t in meta.get("tables", []):
        keys.extend(t.get("columns", []))

    fresh_labels = await generate_labels_with_ai(keys) if keys else {}
    fresh_hints = rule_based_hints(keys)

    for f in meta.get("fields", []):
        k = f["key"]
        if k not in manual:  # giữ nhãn user đã sửa
            f["label"] = fresh_labels.get(k, f.get("label", k))
        f["description"] = fresh_hints.get(k)
    for t in meta.get("tables", []):
        hints = {}
        for col in t.get("columns", []):
            col_key = f"{t['key']}.{col}"
            if col not in manual and col_key not in manual:
                t["column_labels"][col] = fresh_labels.get(col, t["column_labels"].get(col, col))
            if col in fresh_hints:
                hints[col] = fresh_hints[col]
        t["column_hints"] = hints

    template.field_metadata = meta
    flag_modified(template, "field_metadata")
    await db.flush()
    return _to_response(template)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT,
             dependencies=[Depends(TPL_DELETE)])
async def delete_template(template_id: str, db: AsyncSession = Depends(get_db)):
    """Xóa template và file liên quan."""
    template = await _get_or_404(template_id, db)

    # Xóa file
    Path(template.filepath).unlink(missing_ok=True)

    await db.execute(delete(Template).where(Template.id == template_id))


# ─── Helpers ────────────────────────────────────────────────────────────────────

async def _get_or_404(template_id: str, db: AsyncSession) -> Template:
    result = await db.execute(select(Template).where(Template.id == template_id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template không tồn tại")
    return template


def _to_response(t: Template) -> TemplateDetailResponse:
    meta_raw = t.field_metadata or {"fields": [], "tables": []}
    return TemplateDetailResponse(
        id=t.id,
        name=t.name,
        description=t.description,
        filename=t.filename,
        metadata=TemplateMeta(**meta_raw),
        label_config=t.label_config or {},
        created_at=t.created_at,
    )
