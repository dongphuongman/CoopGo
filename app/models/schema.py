"""Shim tương thích: re-export schemas đã tách sang app/schemas/.

Code mới nên import trực tiếp:
  from app.schemas.template import FieldMeta, TableMeta, TemplateMeta, ...
  from app.schemas.render import RenderRequest, RenderJobResponse, ...
"""
from app.schemas.template import (
    FieldMeta, TableMeta, TemplateMeta,
    TemplateCreateResponse, TemplateDetailResponse, LabelConfigUpdate,
)
from app.schemas.render import (
    RenderRequest, RenderJobStatus, RenderJobResponse, RenderJobListItem,
)

__all__ = [
    "FieldMeta", "TableMeta", "TemplateMeta",
    "TemplateCreateResponse", "TemplateDetailResponse", "LabelConfigUpdate",
    "RenderRequest", "RenderJobStatus", "RenderJobResponse", "RenderJobListItem",
]
