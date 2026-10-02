import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate, useLocation, Outlet } from "react-router-dom";
import { AppLayout } from "@/components/AppLayout";
import { AuthProvider, useAuth } from "@/contexts/AuthContext";
import Dashboard from "./pages/Dashboard";
import Templates from "./pages/Templates";
import Render from "./pages/Render";
import Jobs from "./pages/Jobs";
import SettingsPage from "./pages/Settings";
import Login from "./pages/Login";
import NotFound from "./pages/NotFound";
import PhuongTien from "./pages/PhuongTien";
import LaiXe from "./pages/LaiXe";
import CanhBao from "./pages/CanhBao";
import DieuHanh from "./pages/DieuHanh";
import BaoTri from "./pages/BaoTri";
// Tạm ẩn: import XaVien from "./pages/XaVien";
import BulkVerify from "./pages/BulkVerify";
import VerifyPublic from "./pages/VerifyPublic";
import { Loader2 } from "lucide-react";
import { canAccess, normalizeRole, Role } from "@/lib/permissions";

const queryClient = new QueryClient();

/** Redirects unauthenticated users to /login, shows spinner while verifying token. */
function RequireAuth() {
  const { user, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }

  return <Outlet />;
}

/** Chặn route theo role — thiếu quyền thì về Dashboard. */
function RequireRole({ path, children }: { path: string; children: JSX.Element }) {
  const { user } = useAuth();
  const role: Role = normalizeRole(user?.role, user?.is_admin);
  if (!canAccess(role, path)) {
    return <Navigate to="/" replace />;
  }
  return children;
}

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            {/* Public */}
            <Route path="/login" element={<Login />} />
            <Route path="/verify/:code" element={<VerifyPublic />} />

            {/* Protected */}
            <Route element={<RequireAuth />}>
              <Route element={<AppLayout />}>
                <Route path="/" element={<Dashboard />} />
                <Route path="/canh-bao" element={<RequireRole path="/canh-bao"><CanhBao /></RequireRole>} />
                <Route path="/templates" element={<RequireRole path="/templates"><Templates /></RequireRole>} />
                <Route path="/render" element={<RequireRole path="/render"><Render /></RequireRole>} />
                <Route path="/bulk" element={<RequireRole path="/bulk"><BulkVerify /></RequireRole>} />
                <Route path="/jobs" element={<RequireRole path="/jobs"><Jobs /></RequireRole>} />
                <Route path="/phuong-tien" element={<PhuongTien />} />
                <Route path="/lai-xe" element={<LaiXe />} />
                <Route path="/dieu-hanh" element={<RequireRole path="/dieu-hanh"><DieuHanh /></RequireRole>} />
                <Route path="/bao-tri" element={<RequireRole path="/bao-tri"><BaoTri /></RequireRole>} />
                {/* Tạm ẩn: /xa-vien (mở lại khi hoàn thiện Tài chính HTX) */}
                <Route path="/xa-vien" element={<Navigate to="/" replace />} />
                <Route path="/settings" element={<RequireRole path="/settings"><SettingsPage /></RequireRole>} />
              </Route>
            </Route>

            <Route path="*" element={<NotFound />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
