// ─── HTTP client dùng chung (base URL, token, lỗi) ────────────────────────────
export const BASE = "/api";

export function getToken(): string | null {
  return localStorage.getItem("admin_token");
}

export function authHeaders(): HeadersInit {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const msg = (body as { detail?: string }).detail ?? res.statusText;
    throw new Error(msg);
  }
  return res.json() as Promise<T>;
}

export function buildQs(params: Record<string, unknown>): string {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v != null && v !== "") p.append(k, String(v));
  }
  return p.toString();
}
