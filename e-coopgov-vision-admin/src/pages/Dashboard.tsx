import { StatCard } from "@/components/StatCard";
import { Truck, Users, CalendarClock, BellRing, HandCoins, Loader2, QrCode } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/contexts/AuthContext";

interface DashSummary {
  today: string;
  thang: string;
  xe: { tong: number };
  lai_xe: { tong: number };
  tuyen: { tong: number };
  xa_vien: { tong: number };
  lenh_homnay: number;
  het_han: {
    tong_30_ngay: number; da_het_han: number;
    theo_muc: Record<string, number>;
    gap_nhat: { doi_tuong: string; bien_so?: string; loai: string; loai_label?: string; het_han: string | null; con_lai_ngay: number | null; muc: string }[];
  };
  doanh_thu_thang: { thang: string; tong_doanh_thu: number; tong_chi_phi: number; loi_nhuan: number };
  lenh_moi: { so_lenh: string; bien_so: string; ngay_xuat_ben: string | null; verify_code: string }[];
}

async function getDashboardSummary(): Promise<DashSummary> {
  const token = localStorage.getItem("admin_token");
  const res = await fetch("/api/dashboard/summary", {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new Error("Không tải được dashboard");
  return res.json();
}

function mucBadge(muc: string) {
  const map: Record<string, string> = {
    expired: "bg-destructive/15 text-destructive",
    critical: "bg-red-500/15 text-red-600",
    warning: "bg-amber-500/15 text-amber-700",
    notice: "bg-blue-500/15 text-blue-600",
  };
  const label: Record<string, string> = {
    expired: "Hết hạn", critical: "Gấp", warning: "Sắp tới", notice: "Lưu ý",
  };
  return <Badge className={`${map[muc] ?? "bg-muted text-muted-foreground"} border-0 text-xs`}>{label[muc] ?? muc}</Badge>;
}

const fmt = (n: number) => n.toLocaleString("vi-VN");

const Dashboard = () => {
  const { user } = useAuth();
  const { data, isLoading, isError } = useQuery({
    queryKey: ["dashboard-summary"],
    queryFn: getDashboardSummary,
    refetchInterval: 60_000,
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-display font-bold">Dashboard</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Xin chào, {user?.full_name ?? user?.username ?? "Admin"} — Hôm nay {data?.today ?? "…"}
        </p>
      </div>

      {isLoading && (
        <div className="flex items-center justify-center h-40">
          <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
        </div>
      )}
      {isError && <p className="text-sm text-destructive">Không tải được số liệu tổng hợp</p>}

      {data && (
        <>
          {data.het_han.da_het_han > 0 && (
            <a href="/canh-bao" className="block bg-destructive/10 border border-destructive/30 rounded-xl px-5 py-3.5 text-sm hover:bg-destructive/15 transition-colors">
              <b className="text-destructive">⚠ Có {data.het_han.da_het_han} giấy tờ đã hết hạn</b>
              <span className="text-muted-foreground"> — bấm để xem và xử lý ngay →</span>
            </a>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard title="Phương tiện" value={data.xe.tong} subtitle={`${data.tuyen.tong} tuyến`} icon={Truck} />
            <StatCard title="Lái xe" value={data.lai_xe.tong} subtitle={`${data.xa_vien.tong} xã viên`} icon={Users} />
            <StatCard title="Lệnh hôm nay" value={data.lenh_homnay} subtitle="lệnh xuất bến" icon={CalendarClock} />
            <StatCard
              title="Hết hạn 30 ngày"
              value={data.het_han.tong_30_ngay}
              subtitle={data.het_han.da_het_han > 0 ? `${data.het_han.da_het_han} đã quá hạn` : "chưa có quá hạn"}
              icon={BellRing}
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard
              title={`Doanh thu ${data.doanh_thu_thang.thang}`}
              value={`${fmt(data.doanh_thu_thang.tong_doanh_thu)}đ`}
              subtitle={`Lãi ${fmt(data.doanh_thu_thang.loi_nhuan)}đ`}
              icon={HandCoins}
            />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-card rounded-xl border border-border">
              <div className="flex items-center justify-between p-5 border-b border-border">
                <h2 className="font-display font-semibold">Sắp hết hạn gấp nhất</h2>
                <a href="/canh-bao" className="text-sm text-primary hover:underline">Cảnh báo →</a>
              </div>
              {data.het_han.gap_nhat.length === 0 ? (
                <p className="p-5 text-sm text-muted-foreground">Không có giấy tờ nào sắp hết hạn 🎉</p>
              ) : (
                <div className="divide-y divide-border">
                  {data.het_han.gap_nhat.map((x, i) => (
                    <div key={i} className="px-5 py-3 flex items-center justify-between text-sm">
                      <div>
                        <span className="font-medium">{x.bien_so ?? x.doi_tuong}</span>
                        <span className="text-muted-foreground"> • {x.loai_label ?? x.loai}</span>
                        <div className="text-xs text-muted-foreground">
                          Hết hạn: {x.het_han ?? "?"} ({x.con_lai_ngay ?? "?"} ngày)
                        </div>
                      </div>
                      {mucBadge(x.muc)}
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="bg-card rounded-xl border border-border">
              <div className="flex items-center justify-between p-5 border-b border-border">
                <h2 className="font-display font-semibold">Lệnh mới nhất</h2>
                <a href="/dieu-hanh" className="text-sm text-primary hover:underline">Điều hành →</a>
              </div>
              {data.lenh_moi.length === 0 ? (
                <p className="p-5 text-sm text-muted-foreground">Chưa có lệnh nào</p>
              ) : (
                <div className="divide-y divide-border">
                  {data.lenh_moi.map((l) => (
                    <div key={l.so_lenh} className="px-5 py-3 flex items-center gap-3 text-sm">
                      <img src={`/api/lenh-qr/${l.verify_code}`} alt="QR" className="w-10 h-10 border rounded" loading="lazy" />
                      <div>
                        <span className="font-medium">{l.so_lenh}</span> • {l.bien_so}
                        <div className="text-xs text-muted-foreground flex items-center gap-1">
                          <QrCode className="w-3 h-3" /> {l.verify_code}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default Dashboard;
