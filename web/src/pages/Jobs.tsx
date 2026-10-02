import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Search, Download, RefreshCw, FileText, Loader2, AlertCircle, Eye } from "lucide-react";
import { useState, useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { getRenderJobs, RenderJobListItem } from "@/lib/api";
import { renderAsync } from "docx-preview";

function statusBadge(status: string) {
  switch (status) {
    case "done":
      return <Badge className="bg-success/15 text-success border-0 text-xs">Hoàn thành</Badge>;
    case "pending":
      return <Badge className="bg-warning/15 text-warning border-0 text-xs">Đang xử lý</Badge>;
    case "processing":
      return <Badge className="bg-blue-500/15 text-blue-600 border-0 text-xs">Đang render</Badge>;
    case "failed":
      return <Badge className="bg-destructive/15 text-destructive border-0 text-xs">Lỗi</Badge>;
    default:
      return null;
  }
}

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleString("vi-VN", { dateStyle: "short", timeStyle: "short" });
}

function completionDuration(created: string, completed?: string | null) {
  if (!completed) return "-";
  const ms = new Date(completed).getTime() - new Date(created).getTime();
  return `${(ms / 1000).toFixed(1)}s`;
}

const Jobs = () => {
  const [search, setSearch] = useState("");
  const [previewJob, setPreviewJob] = useState<RenderJobListItem | null>(null);
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [blobLoading, setBlobLoading] = useState(false);
  const [blobError, setBlobError] = useState<string | null>(null);
  const docxRef = useRef<HTMLDivElement>(null);

  // Fetch file as blob when preview opens (no Content-Disposition: attachment)
  useEffect(() => {
    if (!previewJob?.download_url) { setBlobUrl(null); return; }
    let revoked = false;
    setBlobLoading(true);
    setBlobError(null);
    setBlobUrl(null);

    const token = localStorage.getItem("admin_token");
    fetch(`/api${previewJob.download_url}?inline=1`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.blob();
      })
      .then(blob => {
        if (revoked) return;
        const url = URL.createObjectURL(blob);
        setBlobUrl(url);
        setBlobLoading(false);
      })
      .catch(e => {
        if (!revoked) { setBlobError(e.message); setBlobLoading(false); }
      });

    return () => {
      revoked = true;
      setBlobUrl(prev => { if (prev) URL.revokeObjectURL(prev); return null; });
    };
  }, [previewJob]);

  // Render DOCX into container div once blob is ready
  useEffect(() => {
    if (!blobUrl || !docxRef.current) return;
    const fmt = previewJob?.output_format ?? "";
    if (fmt !== "docx" && fmt !== "doc") return;
    fetch(blobUrl)
      .then(r => r.blob())
      .then(blob => {
        if (docxRef.current) {
          docxRef.current.innerHTML = "";
          renderAsync(blob, docxRef.current, undefined, {
            className: "docx-preview",
            inWrapper: true,
            ignoreWidth: false,
            ignoreHeight: false,
            ignoreFonts: false,
            breakPages: true,
            useBase64URL: true,
          });
        }
      });
  }, [blobUrl, previewJob?.output_format]);

  function closePreview() {
    setPreviewJob(null);
    setBlobUrl(prev => { if (prev) URL.revokeObjectURL(prev); return null; });
    setBlobError(null);
  }

  const { data: jobs = [], isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ["render-jobs"],
    queryFn: () => getRenderJobs(200),
    refetchInterval: (query) => {
      const hasActive = (query.state.data ?? []).some(
        (j) => j.status === "pending" || j.status === "processing"
      );
      return hasActive ? 5000 : false;
    },
  });

  const filtered = jobs.filter(
    (j) =>
      (j.template_name ?? "").toLowerCase().includes(search.toLowerCase()) ||
      j.job_id.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* File Preview Dialog */}
      <Dialog open={!!previewJob} onOpenChange={(o) => !o && closePreview()}>
        <DialogContent className="max-w-5xl w-full h-[92vh] flex flex-col p-0">
          <DialogHeader className="px-5 py-3 border-b border-border flex-row items-center space-y-0 shrink-0">
            <DialogTitle className="font-display text-sm truncate max-w-[500px]">
              {previewJob?.template_name ?? previewJob?.template_id}
              <Badge variant="outline" className="ml-2 text-xs uppercase">{previewJob?.output_format}</Badge>
            </DialogTitle>
          </DialogHeader>

          <div className="flex-1 overflow-hidden relative">
            {/* Loading */}
            {blobLoading && (
              <div className="absolute inset-0 flex items-center justify-center bg-background/80 z-10">
                <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
              </div>
            )}

            {/* Error */}
            {blobError && (
              <div className="flex flex-col items-center justify-center h-full gap-2 text-destructive">
                <AlertCircle className="w-8 h-8" />
                <p className="text-sm">Không thể tải file: {blobError}</p>
              </div>
            )}

            {/* PDF — object tag renders inline, no download prompt */}
            {!blobLoading && !blobError && blobUrl && (previewJob?.output_format === "pdf") && (
              <object
                data={blobUrl}
                type="application/pdf"
                className="w-full h-full"
              >
                <p className="p-6 text-sm text-muted-foreground">Trình duyệt không hỗ trợ xem PDF. Vui lòng dùng Chrome/Edge.</p>
              </object>
            )}

            {/* DOCX — rendered by docx-preview */}
            {!blobLoading && !blobError && blobUrl && (previewJob?.output_format === "docx" || previewJob?.output_format === "doc") && (
              <div className="h-full overflow-y-auto bg-gray-100 p-4">
                <div
                  ref={docxRef}
                  className="mx-auto bg-white shadow-md"
                  style={{ minHeight: "29.7cm" }}
                />
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-display font-bold">Render Jobs</h1>
          <p className="text-muted-foreground text-sm mt-1">Theo dõi trạng thái các tác vụ render</p>
        </div>
        <Button variant="outline" onClick={() => refetch()} disabled={isFetching}>
          <RefreshCw className={`w-4 h-4 mr-2 ${isFetching ? "animate-spin" : ""}`} /> Refresh
        </Button>
      </div>

      <div className="relative max-w-md">
        <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="Tìm theo tên template hoặc job ID..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-10"
        />
      </div>

      {isLoading && (
        <div className="flex items-center justify-center h-40">
          <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
        </div>
      )}
      {isError && (
        <div className="flex items-center gap-2 text-destructive text-sm">
          <AlertCircle className="w-4 h-4" /> Không thể tải danh sách jobs
        </div>
      )}

      {!isLoading && !isError && (
        <div className="bg-card rounded-xl border border-border overflow-hidden animate-fade-in">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-muted/50">
                  <th className="text-left px-5 py-3 font-medium text-muted-foreground">Job ID</th>
                  <th className="text-left px-5 py-3 font-medium text-muted-foreground">Template</th>
                  <th className="text-left px-5 py-3 font-medium text-muted-foreground">Trạng thái</th>
                  <th className="text-left px-5 py-3 font-medium text-muted-foreground">Format</th>
                  <th className="text-left px-5 py-3 font-medium text-muted-foreground">Thời gian</th>
                  <th className="text-left px-5 py-3 font-medium text-muted-foreground">Duration</th>
                  <th className="text-right px-5 py-3 font-medium text-muted-foreground"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {filtered.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="text-center py-12 text-sm text-muted-foreground">
                      {search ? "Không có job khớp tìm kiếm" : "Chưa có render job nào"}
                    </td>
                  </tr>
                ) : (
                  filtered.map((job) => (
                    <tr key={job.job_id} className="hover:bg-muted/30 transition-colors">
                      <td className="px-5 py-3">
                        <code className="text-xs font-mono text-primary">{job.job_id.split("-")[0]}</code>
                      </td>
                      <td className="px-5 py-3">
                        <span className="flex items-center gap-2">
                          <FileText className="w-3.5 h-3.5 shrink-0 text-muted-foreground" />
                          <span className="truncate max-w-[180px]">
                            {job.template_name ?? job.template_id}
                          </span>
                        </span>
                      </td>
                      <td className="px-5 py-3">{statusBadge(job.status)}</td>
                      <td className="px-5 py-3">
                        <Badge variant="outline" className="text-xs uppercase">
                          {job.output_format}
                        </Badge>
                      </td>
                      <td className="px-5 py-3 text-muted-foreground">
                        {formatDate(job.created_at)}
                      </td>
                      <td className="px-5 py-3 text-muted-foreground">
                        {completionDuration(job.created_at, job.completed_at)}
                      </td>
                      <td className="px-5 py-3 text-right">
                        {job.status === "done" && job.download_url && (
                          <div className="flex items-center justify-end gap-1">
                            <Button variant="ghost" size="sm" onClick={() => setPreviewJob(job)}>
                              <Eye className="w-3.5 h-3.5 mr-1" /> Xem
                            </Button>
                            <a href={`/api${job.download_url}`} download>
                              <Button variant="ghost" size="sm">
                                <Download className="w-3.5 h-3.5 mr-1" /> Tải
                              </Button>
                            </a>
                          </div>
                        )}
                        {(job.status === "pending" || job.status === "processing") && (
                          <Button variant="ghost" size="sm" onClick={() => refetch()}>
                            <RefreshCw className="w-3.5 h-3.5 mr-1" /> Poll
                          </Button>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default Jobs;
