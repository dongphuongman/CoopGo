import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getExpiry, getAlertSummary, sendNotifyNow, getNotifyHistory } from "@/lib/api";
import { viLabel, THONGBAO_KENH_LABELS, THONGBAO_TRANGTHAI_LABELS } from "@/lib/labels";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { BellRing } from "lucide-react";

function mucBadge(muc: string) {
  const map: Record<string, string> = {
    expired: "bg-destructive/15 text-destructive",
    critical: "bg-red-500/15 text-red-600",
    warning: "bg-amber-500/15 text-amber-700",
    notice: "bg-blue-500/15 text-blue-600",
    ok: "bg-green-500/15 text-green-700",
  };
  return <Badge className={`${map[muc] ?? "bg-muted text-muted-foreground"} border-0 text-xs`}>{muc}</Badge>;
}

export default function CanhBao() {
  const qc = useQueryClient();
  const [days, setDays] = useState(30);
  const { data, isLoading, refetch } = useQuery({
    queryKey: ["expiry", days], queryFn: () => getExpiry(days),
  });
  const { data: summary } = useQuery({ queryKey: ["alert-summary"], queryFn: getAlertSummary });
  const { data: history } = useQuery({ queryKey: ["notify-history"], queryFn: () => getNotifyHistory(20) });
  const notifyMutation = useMutation({
    mutationFn: () => sendNotifyNow(days),
    onSuccess: (r) => {
      qc.invalidateQueries({ queryKey: ["notify-history"] });
      toast.success(`Đã gửi ${r.sent} nhắc (${r.skipped} trùng trong ngày, ${r.failed} lỗi) qua: ${r.channels.join(", ")}`);
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Cảnh báo hết hạn</h1>
          <p className="text-sm text-muted-foreground">Đăng kiểm • Phù hiệu • Bảo hiểm • GPLX • KSK — hôm nay {data?.today}</p>
        </div>
        <div className="flex gap-2">
          {[7, 30, 60].map((d) => (
            <Button key={d} variant={days === d ? "default" : "outline"} size="sm" onClick={() => setDays(d)}>{d} ngày</Button>
          ))}
          <Button size="sm" variant="ghost" onClick={() => refetch()}>Tải lại</Button>
          <Button size="sm" onClick={() => notifyMutation.mutate()} disabled={notifyMutation.isPending}>
            <BellRing className="w-3.5 h-3.5 mr-1.5" />
            {notifyMutation.isPending ? "Đang gửi…" : "Gửi nhắc ngay"}
          </Button>
        </div>
      </div>

      {summary && (
        <div className="grid grid-cols-3 gap-4">
          <div className="rounded-xl border p-4"><p className="text-xs text-muted-foreground">Đã hết hạn</p><p className="text-2xl font-bold text-destructive">{summary.da_het_han}</p></div>
          <div className="rounded-xl border p-4"><p className="text-xs text-muted-foreground">Trong 7 ngày</p><p className="text-2xl font-bold">{summary.sap_het_han_7_ngay}</p></div>
          <div className="rounded-xl border p-4"><p className="text-xs text-muted-foreground">Trong 30 ngày</p><p className="text-2xl font-bold">{summary.sap_het_han_30_ngay}</p></div>
        </div>
      )}

      {isLoading ? <p className="text-sm text-muted-foreground">Đang tải...</p> : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="rounded-xl border">
            <div className="p-4 border-b font-semibold">Phương tiện ({data?.phuong_tien.length ?? 0})</div>
            <div className="divide-y max-h-[520px] overflow-auto">
              {(data?.phuong_tien ?? []).map((x, i) => (
                <div key={i} className="px-4 py-2.5 flex items-center justify-between text-sm">
                  <div><span className="font-medium">{x.bien_so}</span><span className="text-muted-foreground"> • {x.loai_label ?? x.loai}</span><div className="text-xs text-muted-foreground">Hết hạn: {x.het_han} ({x.con_lai_ngay} ngày)</div></div>
                  {mucBadge(x.muc)}
                </div>
              ))}
              {(data?.phuong_tien ?? []).length === 0 && <p className="p-4 text-sm text-muted-foreground">Không có xe nào sắp hết hạn 🎉</p>}
            </div>
          </div>
          <div className="rounded-xl border">
            <div className="p-4 border-b font-semibold">Lái xe ({data?.lai_xe.length ?? 0})</div>
            <div className="divide-y max-h-[520px] overflow-auto">
              {(data?.lai_xe ?? []).map((x, i) => (
                <div key={i} className="px-4 py-2.5 flex items-center justify-between text-sm">
                  <div><span className="font-medium">{x.doi_tuong}</span><span className="text-muted-foreground"> • {x.loai_label ?? x.loai}</span><div className="text-xs text-muted-foreground">Hết hạn: {x.het_han} ({x.con_lai_ngay} ngày)</div></div>
                  {mucBadge(x.muc)}
                </div>
              ))}
              {(data?.lai_xe ?? []).length === 0 && <p className="p-4 text-sm text-muted-foreground">Không có lái xe nào sắp hết hạn 🎉</p>}
            </div>
          </div>
        </div>
      )}

      <div className="rounded-xl border">
        <div className="p-4 border-b font-semibold">Lịch sử đã gửi nhắc ({history?.length ?? 0} gần nhất)</div>
        {(history ?? []).length === 0 ? (
          <p className="p-4 text-sm text-muted-foreground">Chưa gửi nhắc nào. Bấm “Gửi nhắc ngay” để nhắc qua các kênh đã cấu hình (log/email/Zalo).</p>
        ) : (
          <div className="divide-y max-h-56 overflow-auto">
            {(history ?? []).map((h) => (
              <div key={h.id} className="px-4 py-2 text-sm flex items-center justify-between">
                <span>[{viLabel(THONGBAO_KENH_LABELS, h.kenh)}] {h.tieu_de}</span>
                <span className="text-xs text-muted-foreground">{h.ngay} • {viLabel(THONGBAO_TRANGTHAI_LABELS, h.trang_thai)}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
