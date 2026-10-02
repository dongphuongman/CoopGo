import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getBaoTri, createBaoTri, getPhuongTien } from "@/lib/api";
import { viLabel, BAO_TRI_LOAI_LABELS } from "@/lib/labels";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function BaoTri() {
  const qc = useQueryClient();
  const [bienSo, setBienSo] = useState("");
  const { data } = useQuery({ queryKey: ["baotri", bienSo], queryFn: () => getBaoTri(bienSo || undefined) });
  const { data: pts } = useQuery({ queryKey: ["pts-mini2"], queryFn: () => getPhuongTien({ size: 200 }) });
  const [xe, setXe] = useState(""); const [ngay, setNgay] = useState(""); const [loai, setLoai] = useState("bao_duong");
  const [nd, setNd] = useState(""); const [cp, setCp] = useState("");
  const m = useMutation({ mutationFn: () => createBaoTri({ phuong_tien_id: xe, ngay, loai, noi_dung: nd, chi_phi: Number(cp) || 0 }), onSuccess: () => qc.invalidateQueries({ queryKey: ["baotri"] }) });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Bảo trì & chi phí</h1>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="rounded-xl border p-4 space-y-3">
          <h2 className="font-semibold">Ghi bảo trì</h2>
          <select className="w-full border rounded px-2 py-1.5 text-sm" value={xe} onChange={(e) => setXe(e.target.value)}><option value="">-- Xe --</option>{(pts?.data ?? []).map((p) => <option key={p.id} value={p.id}>{p.bien_so}</option>)}</select>
          <Input type="date" value={ngay} onChange={(e) => setNgay(e.target.value)} />
          <select className="w-full border rounded px-2 py-1.5 text-sm" value={loai} onChange={(e) => setLoai(e.target.value)}>
            <option value="bao_duong">Bảo dưỡng</option><option value="sua_chua">Sửa chữa</option><option value="nhien_lieu">Nhiên liệu</option><option value="lop">Lốp</option><option value="khac">Khác</option>
          </select>
          <Input placeholder="Nội dung" value={nd} onChange={(e) => setNd(e.target.value)} />
          <Input placeholder="Chi phí (VND)" value={cp} onChange={(e) => setCp(e.target.value)} />
          <Button size="sm" onClick={() => m.mutate()} disabled={!xe || !ngay}>Lưu</Button>
        </div>
        <div className="lg:col-span-2 rounded-xl border p-4">
          <div className="flex items-center gap-2 mb-3">
            <Input placeholder="Lọc biển số..." value={bienSo} onChange={(e) => setBienSo(e.target.value)} className="max-w-xs" />
            <span className="text-sm text-muted-foreground">Tổng: <b>{(data?.tong_chi_phi ?? 0).toLocaleString()}đ</b></span>
          </div>
          <div className="divide-y text-sm max-h-[480px] overflow-auto">
            {(data?.data ?? []).map((r) => <div key={r.id} className="py-2 flex justify-between"><span>{r.ngay} • <b>{r.bien_so}</b> • {viLabel(BAO_TRI_LOAI_LABELS, r.loai)} • {r.noi_dung}</span><span className="font-medium">{Number(r.chi_phi).toLocaleString()}đ</span></div>)}
          </div>
        </div>
      </div>
    </div>
  );
}
