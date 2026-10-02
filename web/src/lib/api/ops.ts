import { BASE, authHeaders, handleResponse, buildQs } from "./client";

// ─── Ops: tuyến / phân công / lệnh / bảo trì ─────────────────────────────
export async function getTuyen(q?: string): Promise<{ id: string; ma_tuyen: string; ten_tuyen: string; diem_di: string | null; diem_den: string | null }[]> {
  const res = await fetch(`${BASE}/tuyen${q ? "?q=" + encodeURIComponent(q) : ""}`, { headers: authHeaders() });
  return handleResponse(res);
}
export async function createTuyen(payload: { ma_tuyen: string; ten_tuyen: string; diem_di?: string; diem_den?: string }): Promise<{ id: string }> {
  const res = await fetch(`${BASE}/tuyen`, { method: "POST", headers: { "Content-Type": "application/json", ...authHeaders() }, body: JSON.stringify(payload) });
  return handleResponse(res);
}
export async function getPhanCong(params: { bien_so?: string } = {}): Promise<{ total: number; data: { id: string; bien_so: string; ho_ten: string; tu_ngay: string | null; den_ngay: string | null; trang_thai: string }[] }> {
  const qs = buildQs(params as Record<string, unknown>);
  const res = await fetch(`${BASE}/phan-cong${qs ? "?" + qs : ""}`, { headers: authHeaders() });
  return handleResponse(res);
}
export async function createPhanCong(payload: { phuong_tien_id: string; lai_xe_id: string; tuyen_id?: string; tu_ngay?: string; den_ngay?: string; ca?: string }): Promise<{ id: string }> {
  const res = await fetch(`${BASE}/phan-cong`, { method: "POST", headers: { "Content-Type": "application/json", ...authHeaders() }, body: JSON.stringify(payload) });
  return handleResponse(res);
}
export async function getLenh(bien_so?: string): Promise<{ id: string; so_lenh: string; bien_so: string; verify_code: string }[]> {
  const res = await fetch(`${BASE}/lenh${bien_so ? "?bien_so=" + encodeURIComponent(bien_so) : ""}`, { headers: authHeaders() });
  return handleResponse(res);
}
export async function createLenh(payload: { phuong_tien_id?: string; bien_so?: string; lai_xe_id?: string; tuyen_id?: string; ngay_xuat_ben?: string }): Promise<{ so_lenh: string; verify_code: string }> {
  const res = await fetch(`${BASE}/lenh`, { method: "POST", headers: { "Content-Type": "application/json", ...authHeaders() }, body: JSON.stringify(payload) });
  return handleResponse(res);
}
export async function getBaoTri(bien_so?: string): Promise<{ tong_chi_phi: number; data: { id: string; bien_so: string; ngay: string; loai: string; noi_dung: string | null; chi_phi: number }[] }> {
  const res = await fetch(`${BASE}/bao-tri${bien_so ? "?bien_so=" + encodeURIComponent(bien_so) : ""}`, { headers: authHeaders() });
  return handleResponse(res);
}
export async function createBaoTri(payload: { phuong_tien_id: string; ngay: string; loai: string; noi_dung?: string; chi_phi?: number; km_hien_tai?: number }): Promise<{ id: string }> {
  const res = await fetch(`${BASE}/bao-tri`, { method: "POST", headers: { "Content-Type": "application/json", ...authHeaders() }, body: JSON.stringify(payload) });
  return handleResponse(res);
}
