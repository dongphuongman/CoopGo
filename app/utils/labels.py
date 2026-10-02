"""Nhãn tiếng Việt cho mã trạng thái/loại — dùng khi ghi log, thông báo."""

TRANG_THAI = {
    "hieu_luc": "Hiệu lực",
    "ket_thuc": "Kết thúc",
    "hoat_dong": "Hoạt động",
    "tam_ngung": "Tạm ngưng",
    "da_cap": "Đã cấp",
    "chinh_thuc": "Chính thức",
}

BAO_TRI_LOAI = {
    "sua_chua": "Sửa chữa",
    "bao_duong": "Bảo dưỡng",
    "nhien_lieu": "Nhiên liệu",
    "lop": "Lốp",
    "dang_kiem_phi": "Phí đăng kiểm",
    "khac": "Khác",
}

HOSO_LOAI = {
    "dang_kiem": "Đăng kiểm",
    "phu_hieu": "Phù hiệu",
    "bao_hiem": "Bảo hiểm TNDS",
    "gsht": "Thiết bị GSHT",
}


def label(map_: dict, code: str | None) -> str:
    return map_.get(code or "", code or "")


def fmt_money(v) -> str:
    try:
        return f"{float(v):,.0f}đ".replace(",", ".")
    except (TypeError, ValueError):
        return str(v)
