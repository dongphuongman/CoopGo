"""Models HTX (xã viên, vốn góp, doanh thu)."""

from sqlalchemy import Column, String, Date, DateTime, Text, Integer, Float, Boolean, Index
from sqlalchemy.sql import func
import uuid
from app.core.database import Base


def _uid() -> str:
    return str(uuid.uuid4())


class XaVien(Base):
    """Xã viên HTX."""
    __tablename__ = "xa_vien"

    id = Column(String(36), primary_key=True, default=_uid)
    ma_xa_vien = Column(String(50), nullable=False, unique=True, index=True)
    ho_ten = Column(String(200), nullable=False, index=True)
    cccd = Column(String(20), nullable=True, index=True)
    sdt = Column(String(20), nullable=True, index=True)
    dia_chi = Column(String(300), nullable=True)
    ngay_tham_gia = Column(Date, nullable=True)
    trang_thai = Column(String(50), nullable=True, default="chinh_thuc", index=True)
    ghi_chu = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class VonGop(Base):
    """Vốn góp của xã viên."""
    __tablename__ = "von_gop"

    id = Column(String(36), primary_key=True, default=_uid)
    xa_vien_id = Column(String(36), nullable=False, index=True)
    ngay_gop = Column(Date, nullable=False, index=True)
    so_tien = Column(Float, nullable=False, default=0)
    hinh_thuc = Column(String(50), nullable=True)  # tien_mat|chuyen_khoan|xe_quy_doi
    ghi_chu = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class DoanhThu(Base):
    """Doanh thu theo xe/tuyến/tháng để chia lãi."""
    __tablename__ = "doanh_thu"

    id = Column(String(36), primary_key=True, default=_uid)
    phuong_tien_id = Column(String(36), nullable=True, index=True)
    bien_so = Column(String(20), nullable=True, index=True)
    tuyen_id = Column(String(36), nullable=True, index=True)
    thang = Column(String(7), nullable=False, index=True)  # YYYY-MM
    doanh_thu = Column(Float, nullable=False, default=0)
    chi_phi = Column(Float, nullable=False, default=0)
    loi_nhuan = Column(Float, nullable=False, default=0)
    ghi_chu = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index("ix_dt_xe_thang", "bien_so", "thang"),)
