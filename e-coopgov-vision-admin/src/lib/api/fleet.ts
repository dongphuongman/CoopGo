import { BASE, authHeaders, handleResponse, buildQs } from "./client";

// ─── Fleet API ────────────────────────────────────────────────────────────────

export interface PhuongTienItem {
  id: string;
  bien_so: string;
  hang_xe: string | null;
  nam_san_xuat: number | null;
  so_cho: number | null;
  mau_xe: string | null;
  loai_hinh_hoat_dong: string | null;
  tuyen_khai_thac: string | null;
  han_dang_kiem: string | null;
  han_phu_hieu: string | null;
  han_bao_hiem: string | null;
  gsht_ten: string | null;
  gsht_don_vi: string | null;
  loai_so_huu: string | null;
  loai_di_thue: string | null;
  trang_thai: string | null;
  ghi_chu: string | null;
  created_at: string | null;
}

export interface LaiXeItem {
  id: string;
  ho_ten: string;
  nhiem_vu_lai_xe: string | null;
  nhiem_vu_nv_phuc_vu: string | null;
  hang_gplx: string | null;
  han_gplx: string | null;
  hop_dong_ngay_ky: string | null;
  hop_dong_loai: string | null;
  dong_bhxh_bhyt: string | null;
  ksk_ngay_kham: string | null;
  ksk_ket_qua: string | null;
  tap_huan_ngay: string | null;
  tap_huan_don_vi: string | null;
  tap_huan_so_gcn: string | null;
  trang_thai: string | null;
  ghi_chu: string | null;
  created_at: string | null;
}

export interface FleetListResponse<T> {
  total: number;
  page: number;
  size: number;
  pages: number;
  data: T[];
}

export interface ImportJobResult {
  job_id: string;
  status: string;
  progress_percent: number;
  total_rows: number | null;
  success_rows: number | null;
  error_rows: number | null;
  error_details: { row?: number; error: string }[];
  completed_at: string | null;
}

export interface PhuongTienFilter {
  q?: string; bien_so?: string; hang_xe?: string; loai_hinh?: string;
  trang_thai?: string; so_cho_min?: number; so_cho_max?: number;
  loai_so_huu?: string; loai_di_thue?: string;
  han_dang_kiem_truoc?: string; han_bao_hiem_truoc?: string;
  page?: number; size?: number;
}

export interface LaiXeFilter {
  q?: string; ho_ten?: string; hang_gplx?: string; trang_thai?: string;
  gplx_het_han_truoc?: string; nhiem_vu?: string;
  dong_bhxh_bhyt?: string; ksk_ket_qua?: string;
  ksk_het_han_truoc?: string;
  page?: number; size?: number;
}

export async function getPhuongTien(filter: PhuongTienFilter = {}): Promise<FleetListResponse<PhuongTienItem>> {
  const qs = buildQs(filter as Record<string, unknown>);
  const res = await fetch(`${BASE}/fleet/phuong-tien${qs ? "?" + qs : ""}`, { headers: authHeaders() });
  return handleResponse<FleetListResponse<PhuongTienItem>>(res);
}

export async function getLaiXe(filter: LaiXeFilter = {}): Promise<FleetListResponse<LaiXeItem>> {
  const qs = buildQs(filter as Record<string, unknown>);
  const res = await fetch(`${BASE}/fleet/lai-xe${qs ? "?" + qs : ""}`, { headers: authHeaders() });
  return handleResponse<FleetListResponse<LaiXeItem>>(res);
}

export async function importPhuongTien(file: File, headerRow = 4, dataStartRow = 6): Promise<{ job_id: string }> {
  const form = new FormData();
  form.append("file", file);
  form.append("header_row", String(headerRow));
  form.append("data_start_row", String(dataStartRow));
  const res = await fetch(`${BASE}/fleet/phuong-tien/import`, {
    method: "POST", headers: authHeaders(), body: form,
  });
  return handleResponse(res);
}

export async function importLaiXe(file: File, headerRow = 4, dataStartRow = 6): Promise<{ job_id: string }> {
  const form = new FormData();
  form.append("file", file);
  form.append("header_row", String(headerRow));
  form.append("data_start_row", String(dataStartRow));
  const res = await fetch(`${BASE}/fleet/lai-xe/import`, {
    method: "POST", headers: authHeaders(), body: form,
  });
  return handleResponse(res);
}

export async function getImportJob(jobId: string): Promise<ImportJobResult> {
  const res = await fetch(`${BASE}/fleet/import-jobs/${jobId}`, { headers: authHeaders() });
  return handleResponse<ImportJobResult>(res);
}

export async function exportPhuongTienBlob(filter: PhuongTienFilter = {}): Promise<{ blob: Blob; filename: string }> {
  const qs = buildQs(filter as Record<string, unknown>);
  const res = await fetch(`${BASE}/fleet/phuong-tien/export${qs ? "?" + qs : ""}`, { headers: authHeaders() });
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail ?? res.statusText);
  const blob = await res.blob();
  const disposition = res.headers.get("content-disposition") ?? "";
  const m = disposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
  return { blob, filename: m?.[1]?.replace(/['"]/g, "") ?? "phuong_tien.xlsx" };
}

export async function exportLaiXeBlob(filter: LaiXeFilter = {}): Promise<{ blob: Blob; filename: string }> {
  const qs = buildQs(filter as Record<string, unknown>);
  const res = await fetch(`${BASE}/fleet/lai-xe/export${qs ? "?" + qs : ""}`, { headers: authHeaders() });
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail ?? res.statusText);
  const blob = await res.blob();
  const disposition = res.headers.get("content-disposition") ?? "";
  const m = disposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
  return { blob, filename: m?.[1]?.replace(/['"]/g, "") ?? "lai_xe.xlsx" };
}
