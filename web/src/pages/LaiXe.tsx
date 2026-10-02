import { useState, useRef, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Upload, Search, Download, RefreshCw, Users, FileSpreadsheet,
  Loader2, AlertCircle, ChevronLeft, ChevronRight, X, SlidersHorizontal,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { toast } from "sonner";
import {
  getLaiXe, importLaiXe, exportLaiXeBlob, getImportJob,
  LaiXeFilter,
} from "@/lib/api";

const PAGE_SIZES = [20, 50, 100];
const HANG_GPLX = ["B1", "B2", "C", "D", "E", "FC", "D, E"];

function hanBadge(date: string | null) {
  if (!date) return <span className="text-muted-foreground text-xs">—</span>;
  const d = new Date(date.includes("-") ? date : date.split("/").reverse().join("-"));
  const now = new Date();
  const diff = (d.getTime() - now.getTime()) / (1000 * 60 * 60 * 24);
  if (diff < 0) return <span className="text-xs text-destructive font-medium">{date} ⚠</span>;
  if (diff < 60) return <span className="text-xs text-warning font-medium">{date} !</span>;
  return <span className="text-xs">{date}</span>;
}

function nhiemVuBadge(laiXe: string | null, nvPv: string | null) {
  const parts: string[] = [];
  if (laiXe && laiXe.trim()) parts.push("Lái xe");
  if (nvPv && nvPv.trim()) parts.push("NV phục vụ");
  if (!parts.length) return <span className="text-muted-foreground text-xs">—</span>;
  return (
    <div className="flex flex-wrap gap-1">
      {parts.map(p => <Badge key={p} variant="outline" className="text-xs">{p}</Badge>)}
    </div>
  );
}

export default function LaiXe() {
  const qc = useQueryClient();

  // ── Filter state ──────────────────────────────────────────────────────────
  const [q, setQ] = useState("");
  const [hangGplx, setHangGplx] = useState("");
  const [trangThai, setTrangThai] = useState("");
  const [gplxHetHan, setGplxHetHan] = useState("");
  const [nhiemVu, setNhiemVu] = useState("");
  const [dongBhxhBhyt, setDongBhxhBhyt] = useState("");
  const [kskKetQua, setKskKetQua] = useState("");
  const [kskHetHanTruoc, setKskHetHanTruoc] = useState("");
  const [showFilters, setShowFilters] = useState(false);
  const [page, setPage] = useState(1);
  const [size, setSize] = useState(20);

  // ── Upload state ─────────────────────────────────────────────────────────
  const [uploadOpen, setUploadOpen] = useState(false);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [headerRow, setHeaderRow] = useState("4");
  const [dataStartRow, setDataStartRow] = useState("6");
  const [jobId, setJobId] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const filter: LaiXeFilter = {
    q: q || undefined,
    hang_gplx: hangGplx || undefined,
    trang_thai: trangThai || undefined,
    gplx_het_han_truoc: gplxHetHan || undefined,
    nhiem_vu: nhiemVu || undefined,
    dong_bhxh_bhyt: dongBhxhBhyt || undefined,
    ksk_ket_qua: kskKetQua || undefined,
    ksk_het_han_truoc: kskHetHanTruoc || undefined,
    page,
    size,
  };

  const { data, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ["lai-xe", filter],
    queryFn: () => getLaiXe(filter),
    placeholderData: (prev) => prev,
  });

  // Poll import job
  const { data: jobData } = useQuery({
    queryKey: ["import-job-lx", jobId],
    queryFn: () => getImportJob(jobId!),
    enabled: !!jobId,
    refetchInterval: (q) => {
      const s = q.state.data?.status;
      return s === "pending" || s === "processing" ? 2000 : false;
    },
  });

  const importMutation = useMutation({
    mutationFn: () => importLaiXe(uploadFile!, Number(headerRow), Number(dataStartRow)),
    onSuccess: (res) => {
      setJobId(res.job_id);
      toast.success("Đang import dữ liệu lái xe…");
    },
    onError: (err: Error) => toast.error(err.message),
  });

  if (jobData?.status === "done" && jobId) {
    setJobId(null);
    setUploadOpen(false);
    setUploadFile(null);
    qc.invalidateQueries({ queryKey: ["lai-xe"] });
    toast.success(`Import thành công ${jobData.success_rows ?? 0} dòng` +
      (jobData.error_rows ? ` (${jobData.error_rows} lỗi)` : ""));
  }

  const handleExport = useCallback(async () => {
    try {
      const { blob, filename } = await exportLaiXeBlob({
        q: q || undefined,
        hang_gplx: hangGplx || undefined,
        trang_thai: trangThai || undefined,
        gplx_het_han_truoc: gplxHetHan || undefined,
        nhiem_vu: nhiemVu || undefined,
        dong_bhxh_bhyt: dongBhxhBhyt || undefined,
        ksk_ket_qua: kskKetQua || undefined,
        ksk_het_han_truoc: kskHetHanTruoc || undefined,
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = filename;
      document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(url);
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Xuất Excel thất bại");
    }
  }, [q, hangGplx, trangThai, gplxHetHan, nhiemVu, dongBhxhBhyt, kskKetQua, kskHetHanTruoc]);

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    const f = e.dataTransfer.files[0];
    if (f?.name.match(/\.(xlsx|xls)$/i)) setUploadFile(f);
  }

  function resetPage() { setPage(1); }

  const rows = data?.data ?? [];
  const total = data?.total ?? 0;
  const pages = data?.pages ?? 1;

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-display font-bold flex items-center gap-2">
            <Users className="w-6 h-6 text-primary" /> Danh sách Lái xe
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            {total > 0 ? `${total} lái xe / nhân viên` : "Chưa có dữ liệu"}
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isFetching}>
            <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${isFetching ? "animate-spin" : ""}`} /> Refresh
          </Button>
          <Button variant="outline" size="sm" onClick={handleExport} disabled={total === 0}>
            <Download className="w-3.5 h-3.5 mr-1.5" /> Xuất Excel
          </Button>
          <Dialog open={uploadOpen} onOpenChange={setUploadOpen}>
            <DialogTrigger asChild>
              <Button size="sm">
                <Upload className="w-3.5 h-3.5 mr-1.5" /> Import Excel
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-md">
              <DialogHeader>
                <DialogTitle className="font-display">Import Excel Lái xe</DialogTitle>
              </DialogHeader>
              <div className="space-y-4 pt-2">
                <div
                  className="border-2 border-dashed border-border rounded-lg p-8 text-center cursor-pointer hover:border-primary/50 transition-colors"
                  onDrop={handleDrop}
                  onDragOver={(e) => e.preventDefault()}
                  onClick={() => fileRef.current?.click()}
                >
                  {uploadFile ? (
                    <div className="flex items-center justify-center gap-2">
                      <FileSpreadsheet className="w-5 h-5 text-success" />
                      <span className="text-sm font-medium">{uploadFile.name}</span>
                      <button onClick={(e) => { e.stopPropagation(); setUploadFile(null); }}>
                        <X className="w-4 h-4 text-muted-foreground hover:text-destructive" />
                      </button>
                    </div>
                  ) : (
                    <>
                      <FileSpreadsheet className="w-8 h-8 text-muted-foreground mx-auto mb-2" />
                      <p className="text-sm text-muted-foreground">
                        Kéo thả hoặc <span className="text-primary font-medium">chọn file</span>
                      </p>
                      <p className="text-xs text-muted-foreground mt-1">.xlsx hoặc .xls</p>
                    </>
                  )}
                  <input ref={fileRef} type="file" accept=".xlsx,.xls" className="hidden"
                    onChange={(e) => setUploadFile(e.target.files?.[0] ?? null)} />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label className="text-xs">Dòng header</Label>
                    <Input className="mt-1" type="number" min={1} value={headerRow}
                      onChange={(e) => setHeaderRow(e.target.value)} />
                  </div>
                  <div>
                    <Label className="text-xs">Dòng bắt đầu data</Label>
                    <Input className="mt-1" type="number" min={1} value={dataStartRow}
                      onChange={(e) => setDataStartRow(e.target.value)} />
                  </div>
                </div>

                {jobData && (
                  <div className={`rounded-lg px-4 py-3 text-sm ${jobData.status === "done" ? "bg-success/10 text-success" : jobData.status === "failed" ? "bg-destructive/10 text-destructive" : "bg-muted"}`}>
                    {jobData.status === "processing" || jobData.status === "pending" ? (
                      <div className="flex items-center gap-2">
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Đang import… {jobData.progress_percent}%
                      </div>
                    ) : jobData.status === "done" ? (
                      `✓ Thành công ${jobData.success_rows} dòng${jobData.error_rows ? ` | ${jobData.error_rows} lỗi` : ""}`
                    ) : `✕ Import thất bại`}
                  </div>
                )}

                <Button
                  className="w-full"
                  disabled={!uploadFile || importMutation.isPending || !!jobId}
                  onClick={() => importMutation.mutate()}
                >
                  {importMutation.isPending || jobId ? (
                    <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Đang xử lý…</>
                  ) : "Import dữ liệu"}
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Filter bar */}
      <div className="bg-card border border-border rounded-xl p-4 space-y-3 animate-fade-in">
        <div className="flex items-center gap-3">
          <div className="relative flex-1 max-w-sm">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <Input placeholder="Tìm tên, đơn vị…" value={q}
              onChange={(e) => { setQ(e.target.value); resetPage(); }}
              className="pl-10" />
          </div>
          <Button variant="outline" size="sm" onClick={() => setShowFilters(!showFilters)}>
            <SlidersHorizontal className="w-3.5 h-3.5 mr-1.5" />
            Lọc nâng cao
            {(hangGplx || trangThai || gplxHetHan || nhiemVu || dongBhxhBhyt || kskKetQua || kskHetHanTruoc) && (
              <Badge className="ml-2 h-4 px-1.5 text-[10px]" variant="secondary">
                {[hangGplx, trangThai, gplxHetHan, nhiemVu, dongBhxhBhyt, kskKetQua, kskHetHanTruoc].filter(Boolean).length}
              </Badge>
            )}
          </Button>
          {(q || hangGplx || trangThai || gplxHetHan || nhiemVu || dongBhxhBhyt || kskKetQua || kskHetHanTruoc) && (
            <Button variant="ghost" size="sm" onClick={() => {
              setQ(""); setHangGplx(""); setTrangThai(""); setGplxHetHan("");
              setNhiemVu(""); setDongBhxhBhyt(""); setKskKetQua(""); setKskHetHanTruoc("");
              resetPage();
            }}>
              <X className="w-3.5 h-3.5 mr-1" /> Xóa lọc
            </Button>
          )}
        </div>

        {showFilters && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2 border-t border-border">
            {/* Row 1 */}
            <div>
              <Label className="text-xs text-muted-foreground">Hạng GPLX</Label>
              <Select value={hangGplx} onValueChange={(v) => { setHangGplx(v === "_all" ? "" : v); resetPage(); }}>
                <SelectTrigger className="mt-1 h-8 text-xs"><SelectValue placeholder="Tất cả" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="_all">Tất cả</SelectItem>
                  {HANG_GPLX.map(h => <SelectItem key={h} value={h}>{h}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs text-muted-foreground">Trạng thái</Label>
              <Select value={trangThai} onValueChange={(v) => { setTrangThai(v === "_all" ? "" : v); resetPage(); }}>
                <SelectTrigger className="mt-1 h-8 text-xs"><SelectValue placeholder="Tất cả" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="_all">Tất cả</SelectItem>
                  <SelectItem value="Đang làm việc">Đang làm việc</SelectItem>
                  <SelectItem value="Nghỉ phép">Nghỉ phép</SelectItem>
                  <SelectItem value="Đã nghỉ việc">Đã nghỉ việc</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs text-muted-foreground">Nhiệm vụ</Label>
              <Select value={nhiemVu} onValueChange={(v) => { setNhiemVu(v === "_all" ? "" : v); resetPage(); }}>
                <SelectTrigger className="mt-1 h-8 text-xs"><SelectValue placeholder="Tất cả" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="_all">Tất cả</SelectItem>
                  <SelectItem value="lai_xe">Lái xe</SelectItem>
                  <SelectItem value="nv_phuc_vu">NV phục vụ</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs text-muted-foreground">Đóng BHXH/BHYT</Label>
              <Select value={dongBhxhBhyt} onValueChange={(v) => { setDongBhxhBhyt(v === "_all" ? "" : v); resetPage(); }}>
                <SelectTrigger className="mt-1 h-8 text-xs"><SelectValue placeholder="Tất cả" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="_all">Tất cả</SelectItem>
                  <SelectItem value="Có">Có</SelectItem>
                  <SelectItem value="Không">Không</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {/* Row 2 */}
            <div>
              <Label className="text-xs text-muted-foreground">Kết quả KSK</Label>
              <Select value={kskKetQua} onValueChange={(v) => { setKskKetQua(v === "_all" ? "" : v); resetPage(); }}>
                <SelectTrigger className="mt-1 h-8 text-xs"><SelectValue placeholder="Tất cả" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="_all">Tất cả</SelectItem>
                  <SelectItem value="Đủ sức khỏe">Đủ sức khỏe</SelectItem>
                  <SelectItem value="Không đủ">Không đủ</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs text-muted-foreground">KSK hết hạn trước</Label>
              <Input className="mt-1 h-8 text-xs" type="date"
                value={kskHetHanTruoc} onChange={(e) => { setKskHetHanTruoc(e.target.value); resetPage(); }} />
            </div>
            <div>
              <Label className="text-xs text-muted-foreground">GPLX hết hạn trước</Label>
              <Input className="mt-1 h-8 text-xs" type="date"
                value={gplxHetHan} onChange={(e) => { setGplxHetHan(e.target.value); resetPage(); }} />
            </div>
            <div className="flex items-end">
              <Select value={String(size)} onValueChange={(v) => { setSize(Number(v)); resetPage(); }}>
                <SelectTrigger className="h-8 text-xs w-full"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {PAGE_SIZES.map(s => <SelectItem key={s} value={String(s)}>{s} / trang</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
          </div>
        )}
      </div>

      {/* Table */}
      {isLoading && (
        <div className="flex items-center justify-center h-40">
          <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
        </div>
      )}
      {isError && (
        <div className="flex items-center gap-2 text-destructive text-sm py-4">
          <AlertCircle className="w-4 h-4" /> Không thể tải dữ liệu
        </div>
      )}
      {!isLoading && !isError && (
        <div className={`bg-card rounded-xl border border-border overflow-hidden animate-fade-in ${isFetching ? "opacity-70" : ""}`}>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-muted/50">
                  {["Họ tên", "Nhiệm vụ", "Hạng GPLX", "Hạn GPLX", "Kết quả KSK", "Ngày TH NV", "Trạng thái"].map(h => (
                    <th key={h} className="text-left px-4 py-3 font-medium text-muted-foreground text-xs whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.length === 0 ? (
                  <tr><td colSpan={7} className="text-center py-12 text-muted-foreground text-sm">
                    Không có dữ liệu lái xe
                  </td></tr>
                ) : rows.map(r => (
                  <tr key={r.id} className="border-b border-border/50 hover:bg-muted/30 transition-colors">
                    <td className="px-4 py-2.5 font-medium">{r.ho_ten}</td>
                    <td className="px-4 py-2.5">{nhiemVuBadge(r.nhiem_vu_lai_xe, r.nhiem_vu_nv_phuc_vu)}</td>
                    <td className="px-4 py-2.5 text-center">
                      {r.hang_gplx ? <Badge variant="secondary" className="text-xs font-mono">{r.hang_gplx}</Badge> : "—"}
                    </td>
                    <td className="px-4 py-2.5">{hanBadge(r.han_gplx)}</td>
                    <td className="px-4 py-2.5">
                      {r.ksk_ket_qua ? (
                        <span className={`text-xs ${r.ksk_ket_qua.includes("Đủ") ? "text-success" : "text-warning"}`}>
                          {r.ksk_ket_qua}
                        </span>
                      ) : "—"}
                    </td>
                    <td className="px-4 py-2.5 text-xs text-muted-foreground">{r.tap_huan_ngay ?? "—"}</td>
                    <td className="px-4 py-2.5">
                      {r.trang_thai ? (
                        <Badge variant={r.trang_thai === "Đang làm việc" ? "default" : "secondary"} className="text-xs">
                          {r.trang_thai}
                        </Badge>
                      ) : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between px-4 py-3 border-t border-border text-sm text-muted-foreground">
            <span>
              {total === 0 ? "0 kết quả" : `${(page - 1) * size + 1}–${Math.min(page * size, total)} / ${total}`}
            </span>
            <div className="flex items-center gap-1">
              <Button variant="ghost" size="icon" className="h-7 w-7"
                disabled={page <= 1} onClick={() => setPage(p => p - 1)}>
                <ChevronLeft className="w-4 h-4" />
              </Button>
              <span className="px-2 text-xs">Trang {page} / {pages}</span>
              <Button variant="ghost" size="icon" className="h-7 w-7"
                disabled={page >= pages} onClick={() => setPage(p => p + 1)}>
                <ChevronRight className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
