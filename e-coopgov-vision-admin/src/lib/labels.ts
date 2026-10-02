// ─── Nhãn tiếng Việt cho mã trạng thái / loại ────────────────────────────────

export const TRANG_THAI_LABELS: Record<string, string> = {
  hieu_luc: "Hiệu lực",
  ket_thuc: "Kết thúc",
  hoat_dong: "Hoạt động",
  tam_ngung: "Tạm ngưng",
  thanh_ly: "Thanh lý",
  da_cap: "Đã cấp",
  da_ban: "Đã bàn giao",
  chinh_thuc: "Chính thức",
  thu_viec: "Thử việc",
  nghi_viec: "Nghỉ việc",
};

export const BAO_TRI_LOAI_LABELS: Record<string, string> = {
  sua_chua: "Sửa chữa",
  bao_duong: "Bảo dưỡng",
  nhien_lieu: "Nhiên liệu",
  lop: "Lốp",
  dang_kiem_phi: "Phí đăng kiểm",
  khac: "Khác",
};

export const HOSO_LOAI_LABELS: Record<string, string> = {
  dang_kiem: "Đăng kiểm",
  phu_hieu: "Phù hiệu",
  bao_hiem: "Bảo hiểm TNDS",
  gsht: "Thiết bị GSHT",
};

export const THONGBAO_TRANGTHAI_LABELS: Record<string, string> = {
  sent: "Đã gửi",
  failed: "Thất bại",
  skipped: "Bỏ qua",
};

export const THONGBAO_KENH_LABELS: Record<string, string> = {
  log: "Nhật ký",
  email: "Email",
  zalo: "Zalo",
};

/** Trả nhãn TV, giữ nguyên nếu không có trong từ điển. */
export function viLabel(map: Record<string, string>, value: string | null | undefined): string {
  if (value == null) return "";
  return map[value] ?? value;
}
