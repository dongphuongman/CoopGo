import { BASE, authHeaders, handleResponse, buildQs } from "./client";

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
