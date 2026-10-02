// ─── Types ──────────────────────────────────────────────────────────────────
export interface UserProfile {
  id: string;
  email: string;
  username: string;
  full_name: string | null;
  is_active: boolean;
  is_admin: boolean;
  role?: string | null;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

/** Matches backend FieldMeta */
export interface TemplateField {
  key: string;
  label: string | null;
  type: string;
  required?: boolean;
  description?: string | null;
}

/** Matches backend TableMeta */
export interface TemplateTable {
  key: string;
  loop_var: string;
  columns: string[];
  column_labels: Record<string, string>;
  column_hints?: Record<string, string>;
  access?: "loop" | "index";
}

export interface TemplateMeta {
  fields: TemplateField[];
  tables: TemplateTable[];
}

/** Matches backend TemplateDetailResponse */
export interface Template {
  id: string;
  name: string;
  description: string | null;
  filename: string;
  metadata: TemplateMeta;
  label_config?: Record<string, string>;
  created_at: string;
}

export interface RenderJobResponse {
  job_id: string;
  template_id: string;
  status: "pending" | "processing" | "done" | "failed";
  download_url?: string;
  error_message?: string | null;
  created_at: string;
  completed_at?: string | null;
}

/** Matches backend RenderJobListItem */
export interface RenderJobListItem {
  job_id: string;
  template_id: string;
  template_name: string | null;
  status: "pending" | "processing" | "done" | "failed";
  output_format: string;
  error_message?: string | null;
  created_at: string;
  completed_at?: string | null;
  download_url?: string | null;
  payload_hash?: string | null;
}

// ─── Auth helpers ─────────────────────────────────────────────────────────────

const BASE = "/api";

function getToken(): string | null {
  return localStorage.getItem("admin_token");
}

function authHeaders(): HeadersInit {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const msg = (body as { detail?: string }).detail ?? res.statusText;
    throw new Error(msg);
  }
  return res.json() as Promise<T>;
}

// ─── Auth API ─────────────────────────────────────────────────────────────────

export async function login(username: string, password: string): Promise<TokenResponse> {
  const form = new URLSearchParams({ username, password });
  const res = await fetch(`${BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: form.toString(),
  });
  return handleResponse<TokenResponse>(res);
}

export async function getMe(): Promise<UserProfile> {
  const res = await fetch(`${BASE}/auth/me`, { headers: authHeaders() });
  return handleResponse<UserProfile>(res);
}

// ─── Templates API ────────────────────────────────────────────────────────────

export async function getTemplates(): Promise<Template[]> {
  const res = await fetch(`${BASE}/templates/`, { headers: authHeaders() });
  return handleResponse<Template[]>(res);
}

export async function getTemplate(id: string): Promise<Template> {
  const res = await fetch(`${BASE}/templates/${id}`, { headers: authHeaders() });
  return handleResponse<Template>(res);
}

export async function deleteTemplate(id: string): Promise<void> {
  const res = await fetch(`${BASE}/templates/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error((body as { detail?: string }).detail ?? res.statusText);
  }
}

export async function uploadTemplate(file: File, name: string, description?: string): Promise<Template> {
  const form = new FormData();
  form.append("file", file);
  form.append("name", name);
  if (description) form.append("description", description);
  const res = await fetch(`${BASE}/templates/`, {
    method: "POST",
    headers: authHeaders(),
    body: form,
  });
  return handleResponse<Template>(res);
}

export async function updateLabels(id: string, labels: Record<string, string>): Promise<Template> {
  const res = await fetch(`${BASE}/templates/${id}/labels`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ labels }),
  });
  return handleResponse<Template>(res);
}

export async function relabelTemplate(id: string): Promise<Template> {
  const res = await fetch(`${BASE}/templates/${id}/relabel`, {
    method: "POST",
    headers: authHeaders(),
  });
  return handleResponse<Template>(res);
}

// ─── Jobs API ─────────────────────────────────────────────────────────────────

export async function getRenderJobs(limit = 100): Promise<RenderJobListItem[]> {
  const res = await fetch(`${BASE}/render/jobs/?limit=${limit}`, { headers: authHeaders() });
  return handleResponse<RenderJobListItem[]>(res);
}

export async function getJobStatus(jobId: string): Promise<RenderJobResponse> {
  const res = await fetch(`${BASE}/render/jobs/${jobId}`, { headers: authHeaders() });
  return handleResponse<RenderJobResponse>(res);
}

// ─── Render API ───────────────────────────────────────────────────────────────

export async function renderSync(
  templateId: string,
  data: Record<string, unknown>,
  outputFormat: "pdf" | "docx" = "pdf"
): Promise<{ blob: Blob; filename: string }> {
  const res = await fetch(`${BASE}/render/${templateId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ data, output_format: outputFormat }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error((body as { detail?: string }).detail ?? res.statusText);
  }
  const blob = await res.blob();
  const disposition = res.headers.get("content-disposition") ?? "";
  const match = disposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
  const filename = match?.[1]?.replace(/['"]/g, "") ?? `output.${outputFormat}`;
  return { blob, filename };
}

export async function renderAsync(
  templateId: string,
  data: Record<string, unknown>,
  outputFormat: "pdf" | "docx" = "pdf"
): Promise<RenderJobResponse> {
  const res = await fetch(`${BASE}/render/${templateId}/async`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ data, output_format: outputFormat }),
  });
  return handleResponse<RenderJobResponse>(res);
}

export function downloadJobUrl(jobId: string): string {
  return `${BASE}/render/jobs/${jobId}/download`;
}

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

function buildQs(params: Record<string, unknown>): string {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v != null && v !== "") p.append(k, String(v));
  }
  return p.toString();
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

// ─── Bulk / Verify / Audit ────────────────────────────────────────────────
export async function bulkRenderFleet(payload: { template_id: string; bien_so_list?: string[]; phuong_tien_ids?: string[]; output_format?: string; extra_data?: Record<string, unknown> }): Promise<{ total: number; jobs: { job_id: string; bien_so: string; verify_code: string; verify_url: string }[] }> {
  const res = await fetch(`${BASE}/bulk/render-fleet`, { method: "POST", headers: { "Content-Type": "application/json", ...authHeaders() }, body: JSON.stringify(payload) });
  return handleResponse(res);
}
export async function verifyDoc(code: string): Promise<{ hop_le: boolean; template: string | null; bien_so: string | null; download_url: string | null }> {
  const res = await fetch(`${BASE}/verify/${code}`, { headers: authHeaders() });
  return handleResponse(res);
}
export async function getAuditLogs(limit = 100): Promise<{ id: string; actor: string | null; action: string; entity: string | null; detail: string | null; created_at: string | null }[]> {
  const res = await fetch(`${BASE}/audit/logs?limit=${limit}`, { headers: authHeaders() });
  return handleResponse(res);
}
export async function previewExcelHeaders(file: File): Promise<{ headers: string[]; goi_y_mapping: Record<string, string> }> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}/fleet/import/preview-headers`, { method: "POST", headers: authHeaders(), body: form });
  return handleResponse(res);
}
export async function gplxCheck(lxId: string, soCho: number): Promise<{ dat: boolean; chi_tiet: string }> {
  const res = await fetch(`${BASE}/fleet/lai-xe/${lxId}/gplx-check?so_cho=${soCho}`, { headers: authHeaders() });
  return handleResponse(res);
}

// ─── Notify ───────────────────────────────────────────────────────────────
export async function sendNotifyNow(withinDays = 30): Promise<{ total: number; sent: number; skipped: number; failed: number; channels: string[] }> {
  const res = await fetch(`${BASE}/alerts/notify?within_days=${withinDays}`, { method: "POST", headers: authHeaders() });
  return handleResponse(res);
}

export async function getNotifyHistory(limit = 20): Promise<{ id: string; kenh: string; tieu_de: string; ref_loai: string | null; ref_id: string | null; trang_thai: string; ngay: string }[]> {
  const res = await fetch(`${BASE}/alerts/notifications?limit=${limit}`, { headers: authHeaders() });
  return handleResponse(res);
}

// ─── App config (màn hình Settings, admin) ──────────────────────────────────
export interface ConfigSetting {
  key: string; label: string; hint: string;
  type: "bool" | "int" | "float" | "string" | "text" | "password";
  value: unknown; source: "env" | "db";
  restart: boolean; min?: number; max?: number;
  has_value?: boolean | null;
}
export interface ConfigGroup {
  id: string; title: string; hint: string; settings: ConfigSetting[];
}
export async function getAppConfig(): Promise<{ groups: ConfigGroup[] }> {
  const res = await fetch(`${BASE}/config/`, { headers: authHeaders() });
  return handleResponse(res);
}
export async function updateAppConfig(settings: Record<string, unknown>): Promise<{ ok: boolean; updated: string[] }> {
  const res = await fetch(`${BASE}/config/`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ settings }),
  });
  return handleResponse(res);
}
