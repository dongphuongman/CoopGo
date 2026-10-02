import { NavLink, useLocation, useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  FileText,
  ListChecks,
  Settings,
  ChevronLeft,
  FileCode2,
  LogOut,
  User,
  Truck,
  Users,
  BellRing,
  CalendarClock,
  Wrench,
  QrCode,
  FileSignature,
} from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/contexts/AuthContext";
import { canAccess, normalizeRole, roleLabel } from "@/lib/permissions";

const navItems = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/canh-bao", icon: BellRing, label: "Cảnh báo" },
  { to: "/templates", icon: FileText, label: "Templates" },
  { to: "/render", icon: FileSignature, label: "Tạo hợp đồng" },
  { to: "/bulk", icon: QrCode, label: "Bulk + Verify" },
  { to: "/jobs", icon: ListChecks, label: "Jobs" },
  { to: "/phuong-tien", icon: Truck, label: "Phương tiện" },
  { to: "/lai-xe", icon: Users, label: "Lái xe" },
  { to: "/dieu-hanh", icon: CalendarClock, label: "Điều hành" },
  { to: "/bao-tri", icon: Wrench, label: "Bảo trì" },
  // Tạm ẩn: Xã viên (chức năng tài chính HTX chưa hoàn thiện, sẽ mở lại sau)
  // { to: "/xa-vien", icon: HandCoins, label: "Xã viên" },
  { to: "/settings", icon: Settings, label: "Cấu hình" },
];

export function AppSidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const role = normalizeRole(user?.role, user?.is_admin);
  const visibleItems = navItems.filter((item) => canAccess(role, item.to));

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <aside
      className={cn(
        "flex flex-col h-screen bg-sidebar text-sidebar-foreground border-r border-sidebar-border transition-all duration-300 shrink-0",
        collapsed ? "w-[68px]" : "w-[240px]"
      )}
    >
      {/* Logo */}
      <div className="flex items-center gap-3 px-4 h-16 border-b border-sidebar-border">
        <div className="w-8 h-8 rounded-lg bg-sidebar-primary flex items-center justify-center shrink-0">
          <FileCode2 className="w-4 h-4 text-sidebar-primary-foreground" />
        </div>
        {!collapsed && (
          <div className="animate-slide-in">
            <h1 className="font-display text-base font-bold text-sidebar-primary-foreground tracking-tight">
              CoopGo
            </h1>
            <p className="text-[10px] text-sidebar-foreground/60 leading-none">HTX Vận tải</p>
          </div>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 py-4 px-2 space-y-1">
        {visibleItems.map((item) => {
          const isActive = location.pathname === item.to;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
                isActive
                  ? "bg-sidebar-accent text-sidebar-primary"
                  : "text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground"
              )}
            >
              <item.icon className="w-[18px] h-[18px] shrink-0" />
              {!collapsed && <span className="animate-slide-in">{item.label}</span>}
            </NavLink>
          );
        })}
      </nav>

      {/* User info + logout */}
      {user && (
        <div className="border-t border-sidebar-border px-2 py-3 space-y-1">
          <div
            className={cn(
              "flex items-center gap-3 px-3 py-2 rounded-lg",
              collapsed ? "justify-center" : ""
            )}
          >
            <div className="w-7 h-7 rounded-full bg-sidebar-accent flex items-center justify-center shrink-0">
              <User className="w-3.5 h-3.5 text-sidebar-foreground/60" />
            </div>
            {!collapsed && (
              <div className="animate-slide-in min-w-0">
                <p className="text-xs font-medium truncate">{user.full_name ?? user.username}</p>
                <p className="text-[10px] text-sidebar-foreground/50 truncate">
                  {roleLabel(user.role, user.is_admin)} • {user.email}
                </p>
              </div>
            )}
          </div>
          <button
            onClick={handleLogout}
            className={cn(
              "w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-destructive transition-colors",
              collapsed ? "justify-center" : ""
            )}
            title="Đăng xuất"
          >
            <LogOut className="w-[18px] h-[18px] shrink-0" />
            {!collapsed && <span className="animate-slide-in">Đăng xuất</span>}
          </button>
        </div>
      )}

      {/* Collapse toggle */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="flex items-center justify-center h-12 border-t border-sidebar-border text-sidebar-foreground/50 hover:text-sidebar-foreground transition-colors"
      >
        <ChevronLeft
          className={cn("w-4 h-4 transition-transform", collapsed && "rotate-180")}
        />
      </button>
    </aside>
  );
}
