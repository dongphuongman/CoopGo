import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getXaVien, createXaVien, getDoanhThu } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function XaVien() {
  const qc = useQueryClient();
  const { data: xv } = useQuery({ queryKey: ["xavien"], queryFn: () => getXaVien() });
  const { data: dt } = useQuery({ queryKey: ["doanhthu"], queryFn: () => getDoanhThu() });
  const [ma, setMa] = useState(""); const [ten, setTen] = useState(""); const [sdt, setSdt] = useState("");
  const m = useMutation({ mutationFn: () => createXaVien({ ma_xa_vien: ma, ho_ten: ten, sdt }), onSuccess: () => { qc.invalidateQueries({ queryKey: ["xavien"] }); setMa(""); setTen(""); setSdt(""); } });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Xã viên • Vốn góp • Doanh thu</h1>
      <div className="grid grid-cols-3 gap-4">
        <div className="rounded-xl border p-4"><p className="text-xs text-muted-foreground">Tổng doanh thu</p><p className="text-xl font-bold">{(dt?.tong_doanh_thu ?? 0).toLocaleString()}đ</p></div>
        <div className="rounded-xl border p-4"><p className="text-xs text-muted-foreground">Tổng chi phí</p><p className="text-xl font-bold">{(dt?.tong_chi_phi ?? 0).toLocaleString()}đ</p></div>
        <div className="rounded-xl border p-4"><p className="text-xs text-muted-foreground">Lợi nhuận</p><p className="text-xl font-bold text-green-600">{(dt?.tong_loi_nhuan ?? 0).toLocaleString()}đ</p></div>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="rounded-xl border p-4 space-y-3">
          <h2 className="font-semibold">Xã viên ({xv?.length ?? 0})</h2>
          <div className="flex gap-2"><Input placeholder="Mã XV" value={ma} onChange={(e) => setMa(e.target.value)} /><Input placeholder="Họ tên" value={ten} onChange={(e) => setTen(e.target.value)} /><Input placeholder="SĐT" value={sdt} onChange={(e) => setSdt(e.target.value)} /></div>
          <Button size="sm" onClick={() => m.mutate()} disabled={!ma || !ten}>Thêm xã viên</Button>
          <div className="divide-y text-sm max-h-72 overflow-auto">{(xv ?? []).map((x) => <div key={x.id} className="py-1.5"><b>{x.ma_xa_vien}</b> — {x.ho_ten} <span className="text-muted-foreground">• {x.sdt} • vốn: {Number(x.tong_von_gop).toLocaleString()}đ</span></div>)}</div>
        </div>
        <div className="rounded-xl border p-4">
          <h2 className="font-semibold mb-2">Doanh thu theo xe/tháng</h2>
          <div className="divide-y text-sm max-h-96 overflow-auto">{(dt?.data ?? []).map((r, i) => <div key={i} className="py-1.5 flex justify-between"><span>{r.thang} • <b>{r.bien_so}</b></span><span>{Number(r.doanh_thu).toLocaleString()}đ → <b className="text-green-600">+{Number(r.loi_nhuan).toLocaleString()}</b></span></div>)}
            {(dt?.data ?? []).length === 0 && <p className="text-sm text-muted-foreground">Chưa có dữ liệu — ghi qua POST /doanh-thu</p>}</div>
        </div>
      </div>
    </div>
  );
}
