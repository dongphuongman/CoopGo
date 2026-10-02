"""
AI Service: Tự động generate label tiếng Việt cho các field key.
Dùng Ollama (local) với model qwen3-coder-next.
"""
import json
import httpx
from typing import Optional
from app.core.config import get_settings
from app.core.logging import logger

settings = get_settings()

SYSTEM_PROMPT = """Bạn là trợ lý giúp tạo nhãn (label) tiếng Việt cho các field trong form tài liệu.
Nhiệm vụ: Nhận danh sách field keys (snake_case, tiếng Anh hoặc tiếng Việt không dấu),
trả về JSON mapping key → label tiếng Việt đẹp, chuyên nghiệp.

Quy tắc BẮT BUỘC:
- Label PHẢI có đầy đủ dấu tiếng Việt (ví dụ "Biển số xe", KHÔNG viết "Bien So Xe")
- Label ngắn gọn, rõ ràng, đúng ngữ cảnh văn phòng/doanh nghiệp
- Viết hoa chữ đầu
- Giữ nguyên dạng viết tắt in hoa quen thuộc: CCCD, GPLX, MST, BHXH, BHYT
- Không có dấu hai chấm ở cuối
- Chỉ trả về JSON thuần, không giải thích

Ví dụ input: ["ho_ten", "ngay_sinh", "so_cmnd", "dia_chi"]
Ví dụ output: {"ho_ten": "Họ và tên", "ngay_sinh": "Ngày sinh", "so_cmnd": "Số CMND/CCCD", "dia_chi": "Địa chỉ"}"""


OLLAMA_BASE_URL = "https://ollama.com"
OLLAMA_MODEL = "qwen3-coder-next"


async def generate_labels_with_ai(keys: list[str]) -> dict[str, str]:
    """
    Gọi Ollama Cloud API để auto-generate label tiếng Việt.
    Chiến lược: từ điển rule-based cho key đã biết (chuẩn, có dấu);
    chỉ gọi AI cho key lạ. Fallback về rule-based nếu API lỗi/tắt.
    """
    rule = _rule_based_labels(keys)
    unknown = [k for k in keys if k not in VI_PHRASE_MAP]

    if not settings.AI_ENABLED or not settings.OLLAMA_API_KEY or not unknown:
        if not settings.AI_ENABLED or not settings.OLLAMA_API_KEY:
            logger.warning("ai_disabled", reason="falling back to rule-based labels")
        return rule

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/chat",
                headers={
                    "Authorization": f"Bearer {settings.OLLAMA_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": OLLAMA_MODEL,
                    "stream": False,
                    "messages": [
                        {
                            "role": "system",
                            "content": SYSTEM_PROMPT,
                        },
                        {
                            "role": "user",
                            "content": f"Tạo label tiếng Việt cho các field sau: {json.dumps(keys, ensure_ascii=False)}"
                        },
                    ],
                },
            )
            response.raise_for_status()
            data = response.json()

            raw_text = data["message"]["content"].strip()

            # Đảm bảo parse JSON sạch (model đôi khi wrap trong ```json```)
            if raw_text.startswith("```"):
                raw_text = raw_text.split("```")[1]
                if raw_text.startswith("json"):
                    raw_text = raw_text[4:]
            raw_text = raw_text.strip()

            labels = json.loads(raw_text)
            logger.info("ai_labels_generated", count=len(labels), model=OLLAMA_MODEL)
            # Từ điển luôn thắng cho key đã biết (chuẩn, có dấu); AI chỉ bổ sung key lạ
            return {**labels, **{k: v for k, v in rule.items() if k in VI_PHRASE_MAP}}

    except Exception as e:
        logger.warning("ai_label_failed", error=str(e), fallback="rule_based")
        return rule


def _rule_based_labels(keys: list[str]) -> dict[str, str]:
    """
    Rule-based label generator không cần AI — LUÔN có dấu tiếng Việt.
    Ưu tiên từ điển cụm từ đầy đủ, fallback ghép từng từ có dấu.
    """
    return {key: _label_for(key) for key in keys}


def rule_based_hints(keys: list[str]) -> dict[str, str]:
    """Giải thích viết tắt cho từng key, vd cccd_ben_a -> 'CCCD: Căn cước công dân'."""
    out = {}
    for key in keys:
        hint = _hint_for(key)
        if hint:
            out[key] = hint
    return out


def _label_for(key: str) -> str:
    if key in VI_PHRASE_MAP:
        return VI_PHRASE_MAP[key]
    return _compose_label(key)


def _hint_for(key: str) -> str:
    parts = []
    seen = set()
    for word in key.lower().split("_"):
        if word in ABBR_HINTS and word not in seen:
            seen.add(word)
            parts.append(f"{ABBR_DISPLAY.get(word, word.upper())}: {ABBR_HINTS[word]}")
    return "; ".join(parts)


def _compose_label(key: str) -> str:
    """Ghép nhãn từ từng từ có dấu; viết tắt giữ in hoa, chữ cái đơn in hoa."""
    words = []
    for word in key.lower().split("_"):
        if word in ABBR_WORDS:
            words.append(ABBR_DISPLAY.get(word, word.upper()))
        elif len(word) == 1 and word.isalpha():
            words.append(word.upper())  # bên a/b
        elif word in VI_WORD_MAP:
            words.append(VI_WORD_MAP[word])
        else:
            words.append(word.capitalize())
    label = " ".join(words)
    return label[0].upper() + label[1:] if label else key


# ─── Từ điển cụm từ đầy đủ (key -> nhãn chuẩn có dấu) ─────────────────────
VI_PHRASE_MAP = {
    # Cá nhân
    "ho_ten": "Họ và tên",
    "ngay_sinh": "Ngày sinh",
    "ngay_cap": "Ngày cấp",
    "ngay_het_han": "Ngày hết hạn",
    "ngay_ky": "Ngày ký",
    "nam_ky": "Năm ký",
    "nam_don": "Năm đón",
    "thang_don": "Tháng đón",
    "ngay_don": "Ngày đón",
    "nam_tra": "Năm trả",
    "thang_tra": "Tháng trả",
    "ngay_tra": "Ngày trả",
    "tra_truoc": "Trả trước",
    "kiem_tra": "Kiểm tra",
    "don_vi": "Đơn vị",
    "so_cmnd": "Số CMND/CCCD",
    "so_cccd": "Số CCCD",
    "so_dien_thoai": "Số điện thoại",
    "dia_chi": "Địa chỉ",
    "dia_chi_thuong_tru": "Địa chỉ thường trú",
    "quoc_tich": "Quốc tịch",
    "gioi_tinh": "Giới tính",
    "tinh": "Tỉnh/Thành phố",
    "quan": "Quận/Huyện",
    "phuong": "Phường/Xã",
    "email": "Email",
    # Công việc
    "chuc_vu": "Chức vụ",
    "phong_ban": "Phòng ban",
    "cong_ty": "Công ty",
    "don_vi": "Đơn vị",
    "ma_nhan_vien": "Mã nhân viên",
    "nguoi_ky": "Người ký",
    "nguoi_dai_dien": "Người đại diện",
    "nguoi_lap": "Người lập",
    "dai_dien_ben_a": "Đại diện bên A",
    "dai_dien_ben_b": "Đại diện bên B",
    "chuc_vu_ben_a": "Chức vụ bên A",
    "chuc_vu_ben_b": "Chức vụ bên B",
    # Hợp đồng
    "so_hop_dong": "Số hợp đồng",
    "noi_dung": "Nội dung",
    "dieu_khoan": "Điều khoản",
    "ghi_chu": "Ghi chú",
    "mo_ta": "Mô tả",
    "ngay_hieu_luc": "Ngày hiệu lực",
    "thoi_han": "Thời hạn",
    "dia_diem": "Địa điểm",
    # Tiền
    "luong": "Lương",
    "tien_luong": "Tiền lương",
    "so_tien": "Số tiền",
    "tong_tien": "Tổng tiền",
    "tong_cuoc_phi": "Tổng cước phí",
    "con_lai": "Còn lại",
    "dat_coc": "Đặt cọc",
    "gia_thue": "Giá thuê",
    "don_gia": "Đơn giá",
    "thanh_tien": "Thành tiền",
    "thue_vat": "Thuế VAT",
    "hinh_thuc_tt": "Hình thức TT",
    "ten_san_pham": "Tên sản phẩm",
    "so_luong": "Số lượng",
    "so_luong_khach": "Số lượng khách",
    "san_luong": "Sản lượng",
    "ma_so": "Mã số",
    # HTX vận tải — phương tiện
    "bien_so_xe": "Biển số xe",
    "hang_xe": "Hãng xe",
    "loai_xe": "Loại xe",
    "mau_xe": "Màu xe",
    "so_cho": "Số chỗ",
    "so_ghe": "Số ghế",
    "nam_san_xuat": "Năm sản xuất",
    "so_khung": "Số khung",
    "so_may": "Số máy",
    "trong_tai": "Trọng tải (kg)",
    # HTX vận tải — tuyến / hành trình
    "tuyen": "Tuyến",
    "tuyen_khai_thac": "Tuyến khai thác",
    "diem_di": "Điểm đi",
    "diem_den": "Điểm đến",
    "gio_di": "Giờ đi",
    "gio_den": "Giờ đến",
    "ngay_di": "Ngày đi",
    "ngay_ve": "Ngày về",
    "cu_ly": "Cự ly (km)",
    "hanh_trinh_di": "Hành trình đi",
    "hanh_trinh_ve": "Hành trình về",
    "don_khach_tai": "Đón khách tại",
    "tra_khach_tai": "Trả khách tại",
    "thoi_gian_thue": "Thời gian thuê",
    # HTX vận tải — lái xe
    "ho_ten_lai_xe": "Họ tên lái xe",
    "so_gplx": "Số GPLX",
    "hang_gplx": "Hạng GPLX",
    "han_gplx": "Hạn GPLX",
    "gplx": "GPLX",
    # Bên A / Bên B
    "ben_a": "Bên A",
    "ben_b": "Bên B",
    "ten_ben_a": "Tên bên A",
    "ten_ben_b": "Tên bên B",
    "dia_chi_ben_a": "Địa chỉ bên A",
    "dia_chi_ben_b": "Địa chỉ bên B",
    "cccd_ben_a": "CCCD bên A",
    "cccd_ben_b": "CCCD bên B",
    "dt_ben_a": "ĐT bên A",
    "dt_ben_b": "ĐT bên B",
    "mst_ben_a": "MST bên A",
    "mst_ben_b": "MST bên B",
    "dt_xe": "ĐT xe",
}

# ─── Từ điển từng từ (viết thường, sẽ viết hoa chữ đầu khi ghép) ───────────
VI_WORD_MAP = {
    "ngay": "ngày", "thang": "tháng", "nam": "năm", "gio": "giờ", "phut": "phút",
    "so": "số", "ho": "họ", "ten": "tên", "dem": "đệm",
    "dia": "địa", "chi": "chỉ", "ben": "bên", "xe": "xe", "lai": "lái",
    "tai": "tại",     "don": "đơn", "ky": "ký", "khach": "khách",
    "tra": "trả", "luong": "lương",
    "thoi": "thời", "gian": "gian",
    "cuoc": "cước", "phi": "phí",
    "truoc": "trước", "sau": "sau",
    "hanh": "hành", "trinh": "trình", "di": "đi", "ve": "về",
    "hinh": "hình", "thuc": "thức", "con": "còn",
    "tuyen": "tuyến", "khai": "khai", "thac": "thác",
    "diem": "điểm", "den": "đến",
    "tien": "tiền", "tong": "tổng", "hop": "hợp", "dong": "đồng",
    "thanh": "thanh", "toan": "toán",
    "nguoi": "người", "dai": "đại", "dien": "diện", "chuc": "chức", "vu": "vụ",
    "cong": "công", "ty": "ty", "vi": "vị",
    "huyen": "huyện", "xa": "xã", "phuong": "phường",
    "quoc": "quốc", "tich": "tịch", "gioi": "giới",
    "san": "sản", "xuat": "xuất", "may": "máy", "trong": "trọng",
    "kham": "khám", "suc": "sức", "khoe": "khỏe", "ket": "kết", "qua": "quả",
    "tap": "tập", "huan": "huấn", "bao": "bảo", "hiem": "hiểm",
    "hieu": "hiệu", "luc": "lực", "han": "hạn", "kiem": "kiểm", "dinh": "định",
    "dang": "đăng", "phu": "phù",
    "dieu": "điều", "khoan": "khoản",
    "mo": "mô", "ta": "tả",
    "nhan": "nhân", "vien": "viên",
    "ly": "ly", "khung": "khung",
}

# ─── Viết tắt giữ in hoa + giải thích hint ─────────────────────────────────
ABBR_WORDS = {
    "cccd", "cmnd", "dt", "gplx", "mst", "tt", "bhxh", "bhyt",
    "ksk", "gcn", "bsx", "vat", "hd", "stt",
}

# Cách hiển thị viết tắt (mặc định = in hoa key)
ABBR_DISPLAY = {
    "dt": "ĐT",
}

ABBR_HINTS = {
    "cccd": "Căn cước công dân",
    "cmnd": "Chứng minh nhân dân",
    "dt": "Điện thoại",
    "gplx": "Giấy phép lái xe",
    "mst": "Mã số thuế",
    "tt": "Thanh toán",
    "bhxh": "Bảo hiểm xã hội",
    "bhyt": "Bảo hiểm y tế",
    "ksk": "Khám sức khỏe",
    "gcn": "Giấy chứng nhận",
    "bsx": "Biển số xe",
    "vat": "Thuế giá trị gia tăng",
    "hd": "Hợp đồng",
    "stt": "Số thứ tự",
}
