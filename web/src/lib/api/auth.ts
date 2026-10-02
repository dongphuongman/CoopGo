import { BASE, authHeaders, handleResponse, buildQs } from "./client";

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
