"""Schemas template Word."""
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
