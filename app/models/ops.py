"""Models điều hành vận tải (tuyến, phân công, lệnh, bảo trì, hồ sơ pháp lý)."""

from sqlalchemy import Column, String, Date, DateTime, Text, Integer, Float, Boolean, Index
from sqlalchemy.sql import func
import uuid
from app.core.database import Base


def _uid() -> str:
    return str(uuid.uuid4())


class Tuyen(Base):
    """Tuyến khai thác: Hà Nội - Hải Phòng..."""
    __tablename__ = "tuyen"

    id = Column(String(36), primary_key=True, default=_uid)
    ma_tuyen = Column(String(50), nullable=False, unique=True, index=True)
    ten_tuyen = Column(String(255), nullable=False)
    diem_di = Column(String(200), nullable=True)
    diem_den = Column(String(200), nullable=True)
    cu_ly_km = Column(Float, nullable=True)
    trang_thai = Column(String(50), nullable=True, default="hoat_dong", index=True)
    ghi_chu = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class PhanCong(Base):
    """Phân công lái xe <-> phương tiện theo thời gian + tuyến."""
    __tablename__ = "phan_cong"

    id = Column(String(36), primary_key=True, default=_uid)
    phuong_tien_id = Column(String(36), nullable=False, index=True)
    bien_so = Column(String(20), nullable=True, index=True)
    lai_xe_id = Column(String(36), nullable=False, index=True)
    ho_ten = Column(String(200), nullable=True)
    tuyen_id = Column(String(36), nullable=True, index=True)
    tu_ngay = Column(Date, nullable=True, index=True)
    den_ngay = Column(Date, nullable=True, index=True)
    ca = Column(String(50), nullable=True)  # sang/chieu/dem
    trang_thai = Column(String(50), nullable=True, default="hieu_luc", index=True)
    ghi_chu = Column(Text, nullable=True)
    created_by = Column(String(36), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_pc_xe_ngay", "phuong_tien_id", "tu_ngay"),
        Index("ix_pc_lx_ngay", "lai_xe_id", "tu_ngay"),
    )

class LenhVanChuyen(Base):
    """Lệnh vận chuyển / lệnh xuất bến — sinh từ Tạo hợp đồng, có verify_code."""
    __tablename__ = "lenh_van_chuyen"

    id = Column(String(36), primary_key=True, default=_uid)
    so_lenh = Column(String(50), nullable=False, unique=True, index=True)
    phuong_tien_id = Column(String(36), nullable=True, index=True)
    bien_so = Column(String(20), nullable=True, index=True)
    lai_xe_id = Column(String(36), nullable=True, index=True)
    tuyen_id = Column(String(36), nullable=True, index=True)
    ngay_xuat_ben = Column(Date, nullable=True, index=True)
    gio_xuat_ben = Column(String(10), nullable=True)
    render_job_id = Column(String(36), nullable=True, index=True)
    verify_code = Column(String(20), nullable=True, unique=True, index=True)
    trang_thai = Column(String(50), nullable=True, default="da_cap", index=True)
    ghi_chu = Column(Text, nullable=True)
    created_by = Column(String(36), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class HoSoPhapLy(Base):
    """Lịch sử đăng kiểm/phù hiệu/bảo hiểm qua các kỳ (kèm file scan)."""
    __tablename__ = "ho_so_phap_ly"

    id = Column(String(36), primary_key=True, default=_uid)
    phuong_tien_id = Column(String(36), nullable=False, index=True)
    bien_so = Column(String(20), nullable=True, index=True)
    loai = Column(String(50), nullable=False, index=True)  # dang_kiem|phu_hieu|bao_hiem|gsht
    ngay_cap = Column(Date, nullable=True)
    ngay_het_han = Column(Date, nullable=True, index=True)
    so_giay = Column(String(100), nullable=True)
    don_vi_cap = Column(String(200), nullable=True)
    file_scan = Column(String(500), nullable=True)
    ghi_chu = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class BaoTri(Base):
    """Sửa chữa / bảo dưỡng / nhiên liệu / chi phí theo xe."""
    __tablename__ = "bao_tri"

    id = Column(String(36), primary_key=True, default=_uid)
    phuong_tien_id = Column(String(36), nullable=False, index=True)
    bien_so = Column(String(20), nullable=True, index=True)
    ngay = Column(Date, nullable=False, index=True)
    loai = Column(String(50), nullable=False, index=True)  # sua_chua|bao_duong|nhien_lieu|lop|dang_kiem_phi...
    noi_dung = Column(Text, nullable=True)
    km_hien_tai = Column(Integer, nullable=True)
    chi_phi = Column(Float, nullable=True, default=0)
    nha_cung_cap = Column(String(200), nullable=True)
    hoa_don = Column(String(100), nullable=True)
    created_by = Column(String(36), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
