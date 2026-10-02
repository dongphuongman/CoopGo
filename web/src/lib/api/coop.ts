import { BASE, authHeaders, handleResponse, buildQs } from "./client";

// ─── Coop ─────────────────────────────────────────────────────────────────
export async function getXaVien(q?: string): Promise<{ id: string; ma_xa_vien: string; ho_ten: string; sdt: string | null; tong_von_gop: number }[]> {
  const res = await fetch(`${BASE}/xa-vien${q ? "?q=" + encodeURIComponent(q) : ""}`, { headers: authHeaders() });
  return handleResponse(res);
}
export async function createXaVien(payload: { ma_xa_vien: string; ho_ten: string; sdt?: string; cccd?: string }): Promise<{ id: string }> {
  const res = await fetch(`${BASE}/xa-vien`, { method: "POST", headers: { "Content-Type": "application/json", ...authHeaders() }, body: JSON.stringify(payload) });
  return handleResponse(res);
}
export async function getDoanhThu(thang?: string): Promise<{ tong_doanh_thu: number; tong_chi_phi: number; tong_loi_nhuan: number; data: { bien_so: string; thang: string; doanh_thu: number; chi_phi: number; loi_nhuan: number }[] }> {
  const res = await fetch(`${BASE}/doanh-thu${thang ? "?thang=" + thang : ""}`, { headers: authHeaders() });
  return handleResponse(res);
}
