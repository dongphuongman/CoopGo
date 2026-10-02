// ─── Phân quyền menu theo role ──────────────────────────────────────────────
// Đồng bộ với GET /roles/matrix ở backend. Admin luôn thấy tất cả.

export type Role = "admin" | "dieu_hanh" | "ke_toan" | "van_phong" | "lai_xe";

export const ROLE_LABELS: Record<Role, string> = {
  admin: "Quản trị",
  dieu_hanh: "Điều hành",
  ke_toan: "Kế toán",
  van_phong: "Văn phòng",
  lai_xe: "Lái xe",
};

function all(): Role[] {
  return ["admin", "dieu_hanh", "ke_toan", "van_phong", "lai_xe"];
}

/** path → roles được thấy menu (admin luôn được qua) */
export const MENU_PERMISSIONS: Record<string, Role[]> = {
  "/": all(),
  "/canh-bao": ["admin", "dieu_hanh", "ke_toan", "van_phong"],
  "/templates": ["admin", "dieu_hanh", "van_phong"],
  "/render": ["admin", "dieu_hanh", "van_phong"],
  "/bulk": ["admin", "dieu_hanh", "van_phong"],
  "/jobs": ["admin", "dieu_hanh", "van_phong"],
  "/phuong-tien": all(), // xem; sửa/xóa do backend chặn theo role
  "/lai-xe": all(), // xem; sửa do backend chặn theo role
  "/dieu-hanh": ["admin", "dieu_hanh"],
  "/bao-tri": ["admin", "dieu_hanh", "ke_toan"],
  "/xa-vien": ["admin", "dieu_hanh", "ke_toan"],
  "/settings": ["admin"],
};

export function normalizeRole(role?: string | null, isAdmin?: boolean): Role {
  if (role === "admin" || role === "dieu_hanh" || role === "ke_toan" || role === "van_phong" || role === "lai_xe") {
    return role;
  }
  return isAdmin ? "admin" : "van_phong";
}

export function canAccess(role: Role, path: string): boolean {
  if (role === "admin") return true;
  return (MENU_PERMISSIONS[path] ?? []).includes(role);
}

export function roleLabel(role?: string | null, isAdmin?: boolean): string {
  return ROLE_LABELS[normalizeRole(role, isAdmin)];
}
