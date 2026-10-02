import { BASE, authHeaders, handleResponse, buildQs } from "./client";

// ─── Alerts ───────────────────────────────────────────────────────────────
export interface ExpiryItem {
  doi_tuong: string; bien_so?: string; loai: string; loai_label?: string;
  het_han: string | null; con_lai_ngay: number | null; muc: string; extra?: string;
}
export interface ExpiryReport {
  today: string; within_days: number;
  phuong_tien: ExpiryItem[]; lai_xe: ExpiryItem[]; tong: number; het_han: number;
}
export async function getExpiry(withinDays = 30): Promise<ExpiryReport> {
  const res = await fetch(`${BASE}/alerts/expiry?within_days=${withinDays}`, { headers: authHeaders() });
  return handleResponse<ExpiryReport>(res);
}
export async function getAlertSummary(): Promise<{
  today: string; sap_het_han_30_ngay: number; sap_het_han_7_ngay: number; da_het_han: number;
  chi_tiet_7_ngay: { phuong_tien: ExpiryItem[]; lai_xe: ExpiryItem[] };
}> {
  const res = await fetch(`${BASE}/alerts/summary`, { headers: authHeaders() });
  return handleResponse(res);
}
