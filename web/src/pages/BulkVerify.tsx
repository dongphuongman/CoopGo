import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { getTemplates, bulkRenderFleet, verifyDoc, getAuditLogs } from "@/lib/api";
import { roleLabel } from "@/lib/permissions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const ACTION_LABELS: Record<string, string> = {
  create: "Tạo mới",
  update: "Cập nhật",
  delete: "Xóa",
  import: "Nhập Excel",
  render: "Tạo văn bản",
  bulk_render: "Tạo hàng loạt",
  set_role: "Gán quyền",
  login: "Đăng nhập",
};

const ENTITY_LABELS: Record<string, string> = {
  lenh: "Lệnh vận chuyển",
  phan_cong: "Phân công",
  phuong_tien: "Phương tiện",
  lai_xe: "Lái xe",
  tuyen: "Tuyến",
  bao_tri: "Bảo trì",
  ho_so: "Hồ sơ pháp lý",
  xa_vien: "Xã viên",
  von_gop: "Vốn góp",
  doanh_thu: "Doanh thu",
  template: "Mẫu hợp đồng",
  user: "Người dùng",
};

function actionLabel(a: string): string {
  return ACTION_LABELS[a] ?? a;
}

function entityLabel(e: string | null): string {
  if (!e) return "";
  return ENTITY_LABELS[e] ?? e;
}

function detailLabel(action: string, entity: string | null, detail: string | null): string {
  if (!detail) return "";
  if (action === "set_role") return roleLabel(detail);
  return detail;
}

export default function BulkVerify() {
  const { data: tpls } = useQuery({ queryKey: ["templates"], queryFn: getTemplates });
  const [tpl, setTpl] = useState(""); const [bss, setBss] = useState("");
  const [code, setCode] = useState("");
  const m = useMutation({ mutationFn: () => bulkRenderFleet({ template_id: tpl, bien_so_list: bss.split(/[\n,]+/).map((s) => s.trim()).filter(Boolean) }) });
  const v = useMutation({ mutationFn: () => verifyDoc(code.trim().toUpperCase()) });
  const { data: logs } = useQuery({ queryKey: ["audit"], queryFn: () => getAuditLogs(50) });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Bulk render • Verify QR • Nhật ký</h1>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="rounded-xl border p-4 space-y-3">
          <h2 className="font-semibold">Render hàng loạt từ danh sách xe</h2>
          <select className="w-full border rounded px-2 py-1.5 text-sm" value={tpl} onChange={(e) => setTpl(e.target.value)}><option value="">-- Template --</option>{(tpls ?? []).map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}</select>
          <textarea className="w-full border rounded p-2 text-sm" rows={4} placeholder="29B-12345, 29B-67890 (cách nhau dấu phẩy/xuống dòng)" value={bss} onChange={(e) => setBss(e.target.value)} />
          <Button size="sm" onClick={() => m.mutate()} disabled={!tpl || !bss}>Render {bss.split(/[\n,]+/).filter((s) => s.trim()).length} xe</Button>
          {m.data && <div className="text-sm space-y-1 max-h-56 overflow-auto">{m.data.jobs.map((j) => <div key={j.job_id}>🚗 {j.bien_so} → <a className="text-primary underline" href={`/api/render/jobs/${j.job_id}/download`}>tải</a> • QR: <b>{j.verify_code}</b></div>)}</div>}
          {m.isError && <p className="text-xs text-destructive">{(m.error as Error).message}</p>}
        </div>
        <div className="rounded-xl border p-4 space-y-3">
          <h2 className="font-semibold">Tra cứu văn bản (QR / mã verify)</h2>
          <div className="flex gap-2"><Input placeholder="VD: A1B2C3D4E5F6" value={code} onChange={(e) => setCode(e.target.value)} /><Button size="sm" onClick={() => v.mutate()}>Tra cứu</Button></div>
          {v.data && <div className="text-sm rounded bg-green-50 border border-green-200 p-3">✅ Hợp lệ • Template: {v.data.template} • Xe: {v.data.bien_so} • <a className="underline text-primary" href={`/api${v.data.download_url}`}>Tải bản gốc</a></div>}
          {v.isError && <p className="text-xs text-destructive">❌ {(v.error as Error).message} (văn bản giả?)</p>}
          <h2 className="font-semibold pt-2">Nhật ký hệ thống (50 mới nhất)</h2>
          <div className="divide-y text-xs max-h-64 overflow-auto">{(logs ?? []).map((l) => <div key={l.id} className="py-1.5"><b>{actionLabel(l.action)}</b> {entityLabel(l.entity)} • {detailLabel(l.action, l.entity, l.detail)} <span className="text-muted-foreground">— {l.created_at}</span></div>)}</div>
        </div>
      </div>
    </div>
  );
}
