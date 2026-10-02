import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getTuyen, createTuyen, getPhanCong, createPhanCong, getLenh, createLenh, getPhuongTien, getLaiXe } from "@/lib/api";
import { viLabel, TRANG_THAI_LABELS } from "@/lib/labels";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function DieuHanh() {
  const qc = useQueryClient();
  const { data: tuyen } = useQuery({ queryKey: ["tuyen"], queryFn: () => getTuyen() });
  const { data: pc } = useQuery({ queryKey: ["phan-cong"], queryFn: () => getPhanCong() });
  const { data: lenh } = useQuery({ queryKey: ["lenh"], queryFn: () => getLenh() });
  const { data: pts } = useQuery({ queryKey: ["pts-mini"], queryFn: () => getPhuongTien({ size: 200 }) });
  const { data: lxs } = useQuery({ queryKey: ["lxs-mini"], queryFn: () => getLaiXe({ size: 200 }) });

  const [maTuyen, setMaTuyen] = useState(""); const [tenTuyen, setTenTuyen] = useState("");
  const [pcXe, setPcXe] = useState(""); const [pcLx, setPcLx] = useState(""); const [pcTu, setPcTu] = useState("");
  const [lenhXe, setLenhXe] = useState("");

  const mTuyen = useMutation({ mutationFn: () => createTuyen({ ma_tuyen: maTuyen, ten_tuyen: tenTuyen }), onSuccess: () => { qc.invalidateQueries({ queryKey: ["tuyen"] }); setMaTuyen(""); setTenTuyen(""); } });
  const mPc = useMutation({ mutationFn: () => createPhanCong({ phuong_tien_id: pcXe, lai_xe_id: pcLx, tu_ngay: pcTu || undefined }), onSuccess: () => qc.invalidateQueries({ queryKey: ["phan-cong"] }) });
  const mLenh = useMutation({ mutationFn: () => createLenh({ bien_so: lenhXe || undefined }), onSuccess: () => qc.invalidateQueries({ queryKey: ["lenh"] }) });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Điều hành: tuyến • phân công • lệnh</h1>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="rounded-xl border p-4 space-y-3">
          <h2 className="font-semibold">Tuyến ({tuyen?.length ?? 0})</h2>
          <div className="flex gap-2"><Input placeholder="Mã tuyến" value={maTuyen} onChange={(e) => setMaTuyen(e.target.value)} /><Input placeholder="Tên tuyến" value={tenTuyen} onChange={(e) => setTenTuyen(e.target.value)} /></div>
          <Button size="sm" onClick={() => mTuyen.mutate()} disabled={!maTuyen || !tenTuyen}>Thêm tuyến</Button>
          <div className="divide-y text-sm max-h-64 overflow-auto">{(tuyen ?? []).map((t) => <div key={t.id} className="py-1.5"><span className="font-medium">{t.ma_tuyen}</span> — {t.ten_tuyen}</div>)}</div>
        </div>
        <div className="rounded-xl border p-4 space-y-3">
          <h2 className="font-semibold">Phân công xe ↔ lái xe (check GPLX + trùng)</h2>
          <select className="w-full border rounded px-2 py-1.5 text-sm" value={pcXe} onChange={(e) => setPcXe(e.target.value)}><option value="">-- Xe --</option>{(pts?.data ?? []).map((p) => <option key={p.id} value={p.id}>{p.bien_so} ({p.so_cho} chỗ)</option>)}</select>
          <select className="w-full border rounded px-2 py-1.5 text-sm" value={pcLx} onChange={(e) => setPcLx(e.target.value)}><option value="">-- Lái xe --</option>{(lxs?.data ?? []).map((l) => <option key={l.id} value={l.id}>{l.ho_ten} ({l.hang_gplx})</option>)}</select>
          <Input type="date" value={pcTu} onChange={(e) => setPcTu(e.target.value)} />
          <Button size="sm" onClick={() => mPc.mutate()} disabled={!pcXe || !pcLx}>Phân công</Button>
          {mPc.isError && <p className="text-xs text-destructive">{(mPc.error as Error).message}</p>}
          {mPc.isSuccess && <p className="text-xs text-green-600">Phân công OK (đã check GPLX + trùng lịch)</p>}
          <div className="divide-y text-sm max-h-64 overflow-auto">{(pc?.data ?? []).map((r) => <div key={r.id} className="py-1.5">{r.bien_so} × {r.ho_ten} <span className="text-muted-foreground">({r.tu_ngay} • {viLabel(TRANG_THAI_LABELS, r.trang_thai)})</span></div>)}</div>
        </div>
        <div className="rounded-xl border p-4 space-y-3">
          <h2 className="font-semibold">Lệnh vận chuyển (có QR verify)</h2>
          <Input placeholder="Biển số (vd 29B-12345)" value={lenhXe} onChange={(e) => setLenhXe(e.target.value)} />
          <Button size="sm" onClick={() => mLenh.mutate()}>Cấp lệnh</Button>
          <div className="divide-y text-sm max-h-64 overflow-auto">{(lenh ?? []).map((l) => (
            <div key={l.id} className="py-1.5 flex items-center gap-2">
              <img src={`/api/lenh-qr/${l.verify_code}`} alt="QR" className="w-12 h-12 border rounded" loading="lazy" />
              <div>
                <span className="font-medium">{l.so_lenh}</span> • {l.bien_so}
                <div className="text-xs text-muted-foreground">QR: <span className="text-primary font-mono">{l.verify_code}</span> — quét để xác thực</div>
              </div>
            </div>
          ))}</div>
        </div>
      </div>
    </div>
  );
}
