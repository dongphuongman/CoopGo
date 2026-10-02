import { BASE, authHeaders, handleResponse, buildQs } from "./client";

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
