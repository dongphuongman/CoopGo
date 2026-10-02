from pydantic import BaseModel, Field
from typing import Any, Optional
from datetime import datetime
from enum import Enum


# ─── Template Models ───────────────────────────────────────────────────────────

class FieldMeta(BaseModel):
    key: str
    label: Optional[str] = None
    type: str = "text"  # text | date | number | boolean
    required: bool = False
    description: Optional[str] = None


class TableMeta(BaseModel):
    key: str
    loop_var: str = "item"
    columns: list[str] = []
    column_labels: dict[str, str] = {}
    column_hints: dict[str, str] = {}  # giải thích viết tắt, vd {"cccd": "CCCD: Căn cước công dân"}
    access: str = "loop"  # "loop" = {% for %} | "index" = list[0].field


class TemplateMeta(BaseModel):
    fields: list[FieldMeta]
    tables: list[TableMeta]


class TemplateCreateResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    filename: str
    metadata: TemplateMeta
    created_at: datetime


class TemplateDetailResponse(TemplateCreateResponse):
    label_config: dict[str, str] = {}


class LabelConfigUpdate(BaseModel):
    """User override label cho từng field."""
    labels: dict[str, str] = Field(
        ...,
        example={"ho_ten": "Họ và tên đầy đủ", "ngay_sinh": "Ngày tháng năm sinh"}
    )


# ─── Render Models ─────────────────────────────────────────────────────────────

class RenderRequest(BaseModel):
    data: dict[str, Any] = Field(
        ...,
        example={
            "ho_ten": "Nguyễn Văn A",
            "ngay_sinh": "01/01/1990",
            "danh_sach": [
                {"ten": "Sản phẩm A", "so_tien": "1.000.000"},
                {"ten": "Sản phẩm B", "so_tien": "2.000.000"},
            ]
        }
    )
    output_format: str = Field(default="pdf", pattern="^(pdf|docx)$")


class RenderJobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"


class RenderJobResponse(BaseModel):
    job_id: str
    template_id: str
    status: RenderJobStatus
    download_url: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    payload_hash: Optional[str] = None
    cached: bool = False


class RenderJobListItem(BaseModel):
    """Lightweight job entry cho danh sách, kèm tên template."""
    job_id: str
    template_id: str
    template_name: Optional[str] = None
    status: RenderJobStatus
    output_format: str = "pdf"
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    download_url: Optional[str] = None
    payload_hash: Optional[str] = None


# ─── Config Models ─────────────────────────────────────────────────────────────

class AppConfigUpdate(BaseModel):
    """Config hệ thống có thể update qua API."""
    ai_enabled: Optional[bool] = None
    max_concurrent_renders: Optional[int] = Field(default=None, ge=1, le=50)
    render_timeout_seconds: Optional[int] = Field(default=None, ge=10, le=300)


class AppConfigResponse(BaseModel):
    ai_enabled: bool
    ai_model: str
    max_concurrent_renders: int
    render_timeout_seconds: int
    libreoffice_bin: str
