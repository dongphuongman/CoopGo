"""Models mở rộng CoopGo: tuyến/phân công/lệnh, bảo trì, xã viên, audit, verify.

Tất cả bảng mới -> create_all tự tạo. Không sửa bảng cũ ở đây.
Xem fleet_models.py cho PhuongTien/LaiXe (đã thêm cột Date + hồ sơ).
"""
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
