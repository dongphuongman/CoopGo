"""Schemas render tài liệu."""
from pydantic import BaseModel, Field
from typing import Any, Optional
from datetime import datetime
from enum import Enum


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
