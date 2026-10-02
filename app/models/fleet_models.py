"""
Models cho phương tiện và lái xe — cấu trúc theo file thực tế Trường Phát
"""
from sqlalchemy import Column, String, DateTime, Date, Text, Integer, Float, Boolean, Index, UniqueConstraint, Enum
from sqlalchemy.sql import func
import uuid, enum
from app.core.database import Base


class ImportStatus(str, enum.Enum):
    PENDING    = "pending"
    PROCESSING = "processing"
    DONE       = "done"
    FAILED     = "failed"


class PhuongTien(Base):
    """Phụ lục 1 — Danh sách phương tiện"""
    __tablename__ = "phuong_tien"

    id                   = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # ── Định danh chính ──────────────────────────────────────────
    bien_so              = Column(String(20),  nullable=False, index=True)   # Biển kiểm soát

    # ── Thông số xe ──────────────────────────────────────────────
    nam_san_xuat         = Column(Integer,     nullable=True)
    so_cho               = Column(Integer,     nullable=True,  index=True)   # Sức chứa (người)
    mau_xe               = Column(String(50),  nullable=True)                # Màu sơn
    hang_xe              = Column(String(100), nullable=True)                # Nhãn hiệu xe
    loai_hinh_hoat_dong  = Column(String(100), nullable=True)                # Loại hình hoạt động
    tuyen_khai_thac      = Column(String(200), nullable=True)                # Tuyến khai thác

    # ── Giấy tờ / Pháp lý ────────────────────────────────────────
    han_dang_kiem        = Column(String(20),  nullable=True,  index=True)   # Ngày hết hạn Đăng kiểm (giữ tương thích Excel cũ)
    han_phu_hieu         = Column(String(20),  nullable=True,  index=True)   # Ngày hết hạn Phù hiệu
    han_bao_hiem         = Column(String(20),  nullable=True,  index=True)   # Ngày hết hạn Bảo hiểm TNDS
    # Cột Date chuẩn để cảnh báo hết hạn (tự sync từ String khi import/save)
    han_dang_kiem_date   = Column(Date,        nullable=True,  index=True)
    han_phu_hieu_date    = Column(Date,        nullable=True,  index=True)
    han_bao_hiem_date    = Column(Date,        nullable=True,  index=True)

    # ── Thông số bổ sung ───────────────────────────────────────────
    so_khung             = Column(String(100), nullable=True)
    so_may               = Column(String(100), nullable=True)
    trong_tai_kg         = Column(Integer,     nullable=True)
    so_ghe               = Column(Integer,     nullable=True)

    # ── Thiết bị GSHT ─────────────────────────────────────────────
    gsht_ten             = Column(String(100), nullable=True)   # Tên thiết bị
    gsht_don_vi          = Column(String(100), nullable=True)   # Đơn vị cung cấp
    gsht_dia_chi         = Column(String(200), nullable=True)   # Địa chỉ truy cập
    gsht_mat_khau        = Column(String(100), nullable=True)   # Mật khẩu truy cập

    # ── Loại phương tiện ──────────────────────────────────────────
    loai_so_huu          = Column(String(10),  nullable=True)   # Thuộc sở hữu đơn vị (X hoặc rỗng)
    loai_di_thue         = Column(String(10),  nullable=True)   # Phương tiện đi thuê (X hoặc rỗng)

    # ── Misc ───────────────────────────────────────────────────────
    ghi_chu              = Column(Text,        nullable=True)
    trang_thai           = Column(String(50),  nullable=True,  index=True)

    # ── Audit ──────────────────────────────────────────────────────
    import_job_id        = Column(String(36),     nullable=True,  index=True)
    created_at           = Column(DateTime(timezone=True), server_default=func.now())
    updated_at           = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("bien_so", name="uq_phuong_tien_bien_so"),
        Index("ix_pt_so_cho", "so_cho"),
        Index("ix_pt_han_dang_kiem", "han_dang_kiem"),
    )


class LaiXe(Base):
    """Phụ lục 2 — Danh sách lái xe, nhân viên phục vụ"""
    __tablename__ = "lai_xe"

    id                   = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # ── Thông tin cá nhân ────────────────────────────────────────
    ho_ten               = Column(String(200), nullable=False, index=True)
    sdt                  = Column(String(20),  nullable=True,  index=True)
    cccd                 = Column(String(20),  nullable=True,  index=True)
    dia_chi              = Column(String(300), nullable=True)
    ngay_sinh            = Column(Date,        nullable=True)
    anh_dai_dien         = Column(String(500), nullable=True)  # path/URL ảnh
    anh_gplx             = Column(String(500), nullable=True)  # path/URL scan GPLX

    # ── Nhiệm vụ ─────────────────────────────────────────────────
    nhiem_vu_lai_xe      = Column(String(10),  nullable=True)   # X nếu là lái xe
    nhiem_vu_nv_phuc_vu  = Column(String(10),  nullable=True)   # X nếu là NV phục vụ trên xe

    # ── GPLX ─────────────────────────────────────────────────────
    hang_gplx            = Column(String(10),  nullable=True,  index=True)   # Hạng: B2, C, D, E
    han_gplx             = Column(String(20),  nullable=True,  index=True)   # Ngày hết hạn GPLX (tương thích cũ)
    han_gplx_date        = Column(Date,        nullable=True,  index=True)
    so_gplx              = Column(String(50),  nullable=True,  index=True)

    # ── Hợp đồng lao động ────────────────────────────────────────
    hop_dong_ngay_ky     = Column(String(20),  nullable=True)
    hop_dong_ngay_ky_date = Column(Date,      nullable=True)
    hop_dong_loai        = Column(String(100), nullable=True)   # xác định thời hạn / 1 năm...

    # ── Bảo hiểm ─────────────────────────────────────────────────
    dong_bhxh_bhyt       = Column(String(10),  nullable=True)   # Có / Không

    # ── Khám sức khỏe định kỳ ────────────────────────────────────
    ksk_ngay_kham        = Column(String(20),  nullable=True)
    ksk_ngay_kham_date   = Column(Date,        nullable=True)
    ksk_ket_qua          = Column(String(100), nullable=True)   # Đủ sức khỏe / Không đủ

    # ── Tập huấn nghiệp vụ ───────────────────────────────────────
    tap_huan_ngay        = Column(String(20),  nullable=True)
    tap_huan_ngay_date   = Column(Date,        nullable=True)
    tap_huan_don_vi      = Column(String(100), nullable=True)   # Sở GTVT / Công ty...
    tap_huan_so_gcn      = Column(String(50),  nullable=True)   # Số GCN tập huấn

    # ── Misc ──────────────────────────────────────────────────────
    ghi_chu              = Column(Text,        nullable=True)
    trang_thai           = Column(String(50),  nullable=True,  index=True)

    # ── Audit ─────────────────────────────────────────────────────
    import_job_id        = Column(String(36),     nullable=True,  index=True)
    created_at           = Column(DateTime(timezone=True), server_default=func.now())
    updated_at           = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("ho_ten", "han_gplx", name="uq_lai_xe_hoten_gplx"),
        Index("ix_lx_hang_gplx_han", "hang_gplx", "han_gplx"),
    )


class ImportJob(Base):
    """Track tiến trình import file Excel"""
    __tablename__ = "import_jobs"

    id              = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    target_table    = Column(String(50),  nullable=False)
    filename        = Column(String(255), nullable=False)
    status          = Column(String(20),  default=ImportStatus.PENDING, index=True)
    total_rows      = Column(Integer,     default=0)
    processed_rows  = Column(Integer,     default=0)
    success_rows    = Column(Integer,     default=0)
    error_rows      = Column(Integer,     default=0)
    preview_mode    = Column(Boolean,     default=False)
    error_details   = Column(Text,        nullable=True)   # JSON array
    header_row      = Column(Integer,     default=4)
    data_start_row  = Column(Integer,     default=6)
    # Nâng cao import: chế độ upsert + mapping cột do user gửi
    upsert_mode     = Column(String(20),  default="upsert")
    column_mapping  = Column(Text,        nullable=True)  # JSON {excel_col: db_field}
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    completed_at    = Column(DateTime(timezone=True), nullable=True)
