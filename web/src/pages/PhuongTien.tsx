import { useState, useRef, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Upload, Search, Download, RefreshCw, Truck, FileSpreadsheet,
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
  getPhuongTien, importPhuongTien, exportPhuongTienBlob, getImportJob,
  PhuongTienFilter,
} from "@/lib/api";

const PAGE_SIZES = [20, 50, 100];

function hanBadge(date: string | null) {
  if (!date) return <span className="text-muted-foreground text-xs">—</span>;
  const d = new Date(date.includes("-") ? date : date.split("/").reverse().join("-"));
  const now = new Date();
  const diff = (d.getTime() - now.getTime()) / (1000 * 60 * 60 * 24);
  if (diff < 0) return <span className="text-xs text-destructive font-medium">{date} ⚠ Hết hạn</span>;
  if (diff < 30) return <span className="text-xs text-warning font-medium">{date} ⚠</span>;
  return <span className="text-xs">{date}</span>;
}

export default function PhuongTien() {
  const qc = useQueryClient();

  // ── Filter state ──────────────────────────────────────────────────────────
  const [q, setQ] = useState("");
  const [trangThai, setTrangThai] = useState("");
  const [soChoMin, setSoChoMin] = useState("");
  const [soChoMax, setSoChoMax] = useState("");
  const [hangXe, setHangXe] = useState("");
  const [loaiHinh, setLoaiHinh] = useState("");
  const [loaiSoHuu, setLoaiSoHuu] = useState("");
  const [loaiDiThue, setLoaiDiThue] = useState("");
  const [hanDangKiemTruoc, setHanDangKiemTruoc] = useState("");
  const [hanBaoHiemTruoc, setHanBaoHiemTruoc] = useState("");
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

  const filter: PhuongTienFilter = {
    q: q || undefined,
    trang_thai: trangThai || undefined,
    so_cho_min: soChoMin ? Number(soChoMin) : undefined,
    so_cho_max: soChoMax ? Number(soChoMax) : undefined,
    hang_xe: hangXe || undefined,
    loai_hinh: loaiHinh || undefined,
    loai_so_huu: loaiSoHuu || undefined,
    loai_di_thue: loaiDiThue || undefined,
    han_dang_kiem_truoc: hanDangKiemTruoc || undefined,
    han_bao_hiem_truoc: hanBaoHiemTruoc || undefined,
    page,
    size,
  };

  const { data, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ["phuong-tien", filter],
    queryFn: () => getPhuongTien(filter),
    placeholderData: (prev) => prev,
  });

  // Poll import job
  const { data: jobData } = useQuery({
    queryKey: ["import-job", jobId],
    queryFn: () => getImportJob(jobId!),
    enabled: !!jobId,
    refetchInterval: (q) => {
      const s = q.state.data?.status;
      return s === "pending" || s === "processing" ? 2000 : false;
    },
  });

  const importMutation = useMutation({
    mutationFn: () => importPhuongTien(uploadFile!, Number(headerRow), Number(dataStartRow)),
    onSuccess: (res) => {
      setJobId(res.job_id);
      toast.success("Đang import dữ liệu phương tiện…");
    },
    onError: (err: Error) => toast.error(err.message),
  });

  // Watch job done
  if (jobData?.status === "done" && jobId) {
    setJobId(null);
    setUploadOpen(false);
    setUploadFile(null);
    qc.invalidateQueries({ queryKey: ["phuong-tien"] });
    toast.success(`Import thành công ${jobData.success_rows ?? 0} dòng` +
      (jobData.error_rows ? ` (${jobData.error_rows} lỗi)` : ""));
  }

  const handleExport = useCallback(async () => {
    try {
      const { blob, filename } = await exportPhuongTienBlob({
        q: q || undefined, trang_thai: trangThai || undefined,
        so_cho_min: soChoMin ? Number(soChoMin) : undefined, so_cho_max: soChoMax ? Number(soChoMax) : undefined,
        hang_xe: hangXe || undefined, loai_hinh: loaiHinh || undefined,
        loai_so_huu: loaiSoHuu || undefined, loai_di_thue: loaiDiThue || undefined,
        han_dang_kiem_truoc: hanDangKiemTruoc || undefined, han_bao_hiem_truoc: hanBaoHiemTruoc || undefined,
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = filename;
      document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(url);
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Xuất Excel thất bại");
    }
  }, [q, trangThai, soChoMin, soChoMax, hangXe, loaiHinh, loaiSoHuu, loaiDiThue, hanDangKiemTruoc, hanBaoHiemTruoc]);

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
            <Truck className="w-6 h-6 text-primary" /> Danh sách Phương tiện
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            {total > 0 ? `${total} phương tiện` : "Chưa có dữ liệu"}
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
                <DialogTitle className="font-display">Import Excel Phương tiện</DialogTitle>
              </DialogHeader>
              <div className="space-y-4 pt-2">
                {/* Drop zone */}
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

                {/* Row config */}
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

                {/* Job progress */}
                {jobData && (
                  <div className={`rounded-lg px-4 py-3 text-sm ${jobData.status === "done" ? "bg-success/10 text-success" : jobData.status === "failed" ? "bg-destructive/10 text-destructive" : "bg-muted"}`}>
                    {jobData.status === "processing" || jobData.status === "pending" ? (
                      <div className="flex items-center gap-2">
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Đang import… {jobData.progress_percent}%
                      </div>
                    ) : jobData.status === "done" ? (
                      `✓ Thành công ${jobData.success_rows} dòng${jobData.error_rows ? ` | ${jobData.error_rows} lỗi` : ""}`
                    ) : (
                      `✕ Import thất bại`
                    )}
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
            <Input placeholder="Tìm biển số, hãng xe…" value={q}
              onChange={(e) => { setQ(e.target.value); resetPage(); }}
              className="pl-10" />
          </div>
          <Button variant="outline" size="sm" onClick={() => setShowFilters(!showFilters)}>
            <SlidersHorizontal className="w-3.5 h-3.5 mr-1.5" />
            Lọc nâng cao
            {(trangThai || soChoMin || soChoMax || hangXe || loaiHinh || loaiSoHuu || loaiDiThue || hanDangKiemTruoc || hanBaoHiemTruoc) && (
              <Badge className="ml-2 h-4 px-1.5 text-[10px]" variant="secondary">
                {[trangThai, soChoMin, soChoMax, hangXe, loaiHinh, loaiSoHuu, loaiDiThue, hanDangKiemTruoc, hanBaoHiemTruoc].filter(Boolean).length}
              </Badge>
            )}
          </Button>
          {(q || trangThai || soChoMin || soChoMax || hangXe || loaiHinh || loaiSoHuu || loaiDiThue || hanDangKiemTruoc || hanBaoHiemTruoc) && (
            <Button variant="ghost" size="sm" onClick={() => {
              setQ(""); setTrangThai(""); setSoChoMin(""); setSoChoMax("");
              setHangXe(""); setLoaiHinh(""); setLoaiSoHuu(""); setLoaiDiThue("");
              setHanDangKiemTruoc(""); setHanBaoHiemTruoc(""); resetPage();
            }}>
              <X className="w-3.5 h-3.5 mr-1" /> Xóa lọc
            </Button>
          )}
        </div>

        {showFilters && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2 border-t border-border">
            {/* Row 1 */}
            <div>
              <Label className="text-xs text-muted-foreground">Trạng thái</Label>
              <Select value={trangThai} onValueChange={(v) => { setTrangThai(v === "_all" ? "" : v); resetPage(); }}>
                <SelectTrigger className="mt-1 h-8 text-xs"><SelectValue placeholder="Tất cả" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="_all">Tất cả</SelectItem>
                  <SelectItem value="Hoạt động">Hoạt động</SelectItem>
                  <SelectItem value="Bảo dưỡng">Bảo dưỡng</SelectItem>
                  <SelectItem value="Tạm dừng">Tạm dừng</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs text-muted-foreground">Hãng xe</Label>
              <Input className="mt-1 h-8 text-xs" placeholder="VD: Toyota, Thaco..."
                value={hangXe} onChange={(e) => { setHangXe(e.target.value); resetPage(); }} />
            </div>
            <div>
              <Label className="text-xs text-muted-foreground">Loại hình HĐ</Label>
              <Input className="mt-1 h-8 text-xs" placeholder="VD: Tuyến cố định..."
                value={loaiHinh} onChange={(e) => { setLoaiHinh(e.target.value); resetPage(); }} />
            </div>
            <div>
              <Label className="text-xs text-muted-foreground">Loại sở hữu</Label>
              <Select value={loaiSoHuu} onValueChange={(v) => { setLoaiSoHuu(v === "_all" ? "" : v); resetPage(); }}>
                <SelectTrigger className="mt-1 h-8 text-xs"><SelectValue placeholder="Tất cả" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="_all">Tất cả</SelectItem>
                  <SelectItem value="X">Sở hữu</SelectItem>
                  <SelectItem value="khong">Không sở hữu</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {/* Row 2 */}
            <div>
              <Label className="text-xs text-muted-foreground">Loại đi thuê</Label>
              <Select value={loaiDiThue} onValueChange={(v) => { setLoaiDiThue(v === "_all" ? "" : v); resetPage(); }}>
                <SelectTrigger className="mt-1 h-8 text-xs"><SelectValue placeholder="Tất cả" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="_all">Tất cả</SelectItem>
                  <SelectItem value="X">Đi thuê</SelectItem>
                  <SelectItem value="khong">Không đi thuê</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs text-muted-foreground">Số chỗ tối thiểu</Label>
              <Input className="mt-1 h-8 text-xs" type="number" min={0} placeholder="VD: 16"
                value={soChoMin} onChange={(e) => { setSoChoMin(e.target.value); resetPage(); }} />
            </div>
            <div>
              <Label className="text-xs text-muted-foreground">Số chỗ tối đa</Label>
              <Input className="mt-1 h-8 text-xs" type="number" min={0} placeholder="VD: 45"
                value={soChoMax} onChange={(e) => { setSoChoMax(e.target.value); resetPage(); }} />
            </div>
            <div>
              <Label className="text-xs text-muted-foreground">Hạn đăng kiểm trước</Label>
              <Input className="mt-1 h-8 text-xs" type="date"
                value={hanDangKiemTruoc} onChange={(e) => { setHanDangKiemTruoc(e.target.value); resetPage(); }} />
            </div>
            {/* Row 3 */}
            <div>
              <Label className="text-xs text-muted-foreground">Hạn bảo hiểm trước</Label>
              <Input className="mt-1 h-8 text-xs" type="date"
                value={hanBaoHiemTruoc} onChange={(e) => { setHanBaoHiemTruoc(e.target.value); resetPage(); }} />
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
                  {["Biển số", "Hãng xe", "Số chỗ", "Màu xe", "Loại hình HĐ", "Hạn ĐK", "Hạn BH TNDS", "Trạng thái"].map(h => (
                    <th key={h} className="text-left px-4 py-3 font-medium text-muted-foreground text-xs whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.length === 0 ? (
                  <tr><td colSpan={8} className="text-center py-12 text-muted-foreground text-sm">
                    Không có dữ liệu phương tiện
                  </td></tr>
                ) : rows.map(r => (
                  <tr key={r.id} className="border-b border-border/50 hover:bg-muted/30 transition-colors">
                    <td className="px-4 py-2.5 font-mono font-semibold text-primary text-xs">{r.bien_so}</td>
                    <td className="px-4 py-2.5">{r.hang_xe ?? "—"}</td>
                    <td className="px-4 py-2.5 text-center">
                      {r.so_cho ? <Badge variant="secondary" className="text-xs">{r.so_cho} chỗ</Badge> : "—"}
                    </td>
                    <td className="px-4 py-2.5 text-muted-foreground">{r.mau_xe ?? "—"}</td>
                    <td className="px-4 py-2.5 text-xs text-muted-foreground max-w-[180px] truncate">{r.loai_hinh_hoat_dong ?? "—"}</td>
                    <td className="px-4 py-2.5">{hanBadge(r.han_dang_kiem)}</td>
                    <td className="px-4 py-2.5">{hanBadge(r.han_bao_hiem)}</td>
                    <td className="px-4 py-2.5">
                      {r.trang_thai ? (
                        <Badge variant={r.trang_thai === "Hoạt động" ? "default" : "secondary"} className="text-xs">
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
              <span className="px-2 text-xs">
                Trang {page} / {pages}
              </span>
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
