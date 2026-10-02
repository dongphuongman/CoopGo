"""Models hệ thống (verify, audit, thông báo, cấu hình)."""

from sqlalchemy import Column, String, Date, DateTime, Text, Integer, Float, Boolean, Index
from sqlalchemy.sql import func
import uuid
from app.core.database import Base


def _uid() -> str:
    return str(uuid.uuid4())


class VanBanVerify(Base):
    """Map verify_code -> render job để tra cứu QR."""
    __tablename__ = "van_ban_verify"

    id = Column(String(36), primary_key=True, default=_uid)
    verify_code = Column(String(20), nullable=False, unique=True, index=True)
    render_job_id = Column(String(36), nullable=False, index=True)
    template_id = Column(String(36), nullable=True)
    template_name = Column(String(255), nullable=True)
    bien_so = Column(String(20), nullable=True, index=True)
    payload_summary = Column(Text, nullable=True)  # JSON tóm tắt
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class AuditLog(Base):
    """Ai làm gì, với bản ghi nào, khi nào."""
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=_uid)
    actor_id = Column(String(36), nullable=True, index=True)
    actor_name = Column(String(200), nullable=True)
    action = Column(String(100), nullable=False, index=True)  # create|update|delete|import|render|login...
    entity = Column(String(100), nullable=True, index=True)
    entity_id = Column(String(100), nullable=True, index=True)
    detail = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

class ThongBao(Base):
    """Lịch sử nhắc hết hạn (chống gửi trùng bằng unique kenh/ref/ngay)."""
    __tablename__ = "thong_bao"

    id = Column(String(36), primary_key=True, default=_uid)
    kenh = Column(String(20), nullable=False, index=True)  # log|email|zalo
    loai = Column(String(50), nullable=False, index=True)  # het_han
    tieu_de = Column(String(255), nullable=True)
    noi_dung = Column(Text, nullable=True)
    nguoi_nhan = Column(String(255), nullable=True)
    ref_loai = Column(String(50), nullable=True)  # dang_kiem|phu_hieu|bao_hiem|gplx|ksk
    ref_id = Column(String(200), nullable=True)  # bien_so|ho_ten
    ngay = Column(Date, nullable=False, index=True)
    trang_thai = Column(String(20), nullable=True, default="sent")  # sent|failed|skipped
    loi = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index("uq_tb_kenh_ref_ngay", "kenh", "ref_loai", "ref_id", "ngay", unique=True),)

class AppSetting(Base):
    """Cấu hình hệ thống sửa qua màn hình Settings (ghi đè giá trị .env)."""
    __tablename__ = "app_settings"

    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
