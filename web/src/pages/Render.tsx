import { useState, useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { FileText, Plus, Trash2, Download, Loader2, CircleHelp } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { getTemplates, getTemplate, renderSync, renderAsync } from "@/lib/api";

const Render = () => {
  const qc = useQueryClient();
  const [selectedId, setSelectedId] = useState("");
  const [outputFormat, setOutputFormat] = useState<"pdf" | "docx">("pdf");
  const [renderMode, setRenderMode] = useState<"sync" | "async">("sync");
  const [fieldValues, setFieldValues] = useState<Record<string, string>>({});
  const [tableValues, setTableValues] = useState<Record<string, Record<string, string>[]>>({});
  const [rendering, setRendering] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);

  const { data: templates = [], isLoading: templatesLoading } = useQuery({
    queryKey: ["templates"],
    queryFn: getTemplates,
  });

  const { data: template, isLoading: templateLoading } = useQuery({
    queryKey: ["template", selectedId],
    queryFn: () => getTemplate(selectedId),
    enabled: !!selectedId,
  });

  // Reset form when template changes
  useEffect(() => {
    if (!template) return;
    const fields: Record<string, string> = {};
    (template.metadata?.fields ?? []).forEach((f) => {
      fields[f.key] = "";
    });
    setFieldValues(fields);
    const tables: Record<string, Record<string, string>[]> = {};
    (template.metadata?.tables ?? []).forEach((t) => {
      tables[t.key] = [Object.fromEntries(t.columns.map((c) => [c, ""]))];
    });
    setTableValues(tables);
    setJobId(null);
  }, [template?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  function buildPayload(): Record<string, unknown> {
    const data: Record<string, unknown> = { ...fieldValues };
    (template?.metadata?.tables ?? []).forEach((t) => {
      data[t.key] = (tableValues[t.key] ?? []).filter((row) =>
        Object.values(row).some((v) => v.trim() !== "")
      );
    });
    return data;
  }

  async function handleRender() {
    if (!selectedId) return;
    setRendering(true);
    setJobId(null);
    try {
      const data = buildPayload();
      if (renderMode === "sync") {
        const { blob, filename } = await renderSync(selectedId, data, outputFormat);
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
        toast.success("Tạo hợp đồng thành công, file đang được tải xuống");
      } else {
        const job = await renderAsync(selectedId, data, outputFormat);
        setJobId(job.job_id);
        qc.invalidateQueries({ queryKey: ["render-jobs"] });
        toast.success(`Job đã tạo: ${job.job_id.split("-")[0]}…`);
      }
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Tạo hợp đồng thất bại");
    } finally {
      setRendering(false);
    }
  }

  function addRow(tableKey: string, columns: string[]) {
    setTableValues((prev) => ({
      ...prev,
      [tableKey]: [
        ...(prev[tableKey] ?? []),
        Object.fromEntries(columns.map((c) => [c, ""])),
      ],
    }));
  }

  function removeRow(tableKey: string, idx: number) {
    setTableValues((prev) => ({
      ...prev,
      [tableKey]: (prev[tableKey] ?? []).filter((_, i) => i !== idx),
    }));
  }

  function setCell(tableKey: string, rowIdx: number, col: string, value: string) {
    setTableValues((prev) => {
      const rows = [...(prev[tableKey] ?? [])];
      rows[rowIdx] = { ...rows[rowIdx], [col]: value };
      return { ...prev, [tableKey]: rows };
    });
  }

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="text-2xl font-display font-bold">Tạo hợp đồng</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Chọn mẫu hợp đồng, điền thông tin và xuất file
        </p>
      </div>

      <div className="bg-card rounded-xl border border-border p-6 space-y-5 animate-fade-in">
        {/* Template selector + options */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <Label>Chọn Template</Label>
            <Select value={selectedId} onValueChange={setSelectedId}>
              <SelectTrigger className="mt-1.5">
                <SelectValue
                  placeholder={templatesLoading ? "Đang tải…" : "Chọn template..."}
                />
              </SelectTrigger>
              <SelectContent>
                {templates.map((t) => (
                  <SelectItem key={t.id} value={t.id}>
                    <span className="flex items-center gap-2">
                      <FileText className="w-3.5 h-3.5" /> {t.name}
                    </span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>Định dạng</Label>
              <Select
                value={outputFormat}
                onValueChange={(v) => setOutputFormat(v as "pdf" | "docx")}
              >
                <SelectTrigger className="mt-1.5">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="pdf">PDF</SelectItem>
                  <SelectItem value="docx">DOCX</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Chế độ</Label>
              <Select
                value={renderMode}
                onValueChange={(v) => setRenderMode(v as "sync" | "async")}
              >
                <SelectTrigger className="mt-1.5">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="sync">Sync</SelectItem>
                  <SelectItem value="async">Async</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </div>

        {/* Loading template fields */}
        {selectedId && templateLoading && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground pt-2">
            <Loader2 className="w-4 h-4 animate-spin" /> Đang tải fields…
          </div>
        )}

        {/* Dynamic form */}
        {template && !templateLoading && (
          <>
            {/* Fields */}
            {(template.metadata?.fields?.length ?? 0) > 0 && (
              <div className="border-t border-border pt-5">
                <h3 className="font-display font-semibold text-sm mb-3 flex items-center gap-2">
                  Dữ liệu Fields
                  <Badge variant="secondary" className="text-xs font-normal">
                    {template.metadata.fields.length} fields
                  </Badge>
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {template.metadata.fields.map((f) => (
                    <div key={f.key}>
                      <Label className="text-xs flex items-center gap-1.5">
                        <span>{f.label ?? f.key}</span>
                        {f.description && (
                          <span title={f.description} className="cursor-help inline-flex">
                            <CircleHelp className="w-3.5 h-3.5 text-muted-foreground" />
                          </span>
                        )}
                        <code className="text-primary ml-1 font-mono text-[11px]">
                          {`{{ ${f.key} }}`}
                        </code>
                      </Label>
                      <Input
                        placeholder={f.description ? `${f.label ?? f.key} (${f.description})` : (f.label ?? f.key)}
                        title={f.description ?? undefined}
                        className="mt-1"
                        value={fieldValues[f.key] ?? ""}
                        onChange={(e) =>
                          setFieldValues((prev) => ({ ...prev, [f.key]: e.target.value }))
                        }
                      />
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Tables */}
            {(template.metadata?.tables ?? []).map((tbl) => (
              <div key={tbl.key} className="border-t border-border pt-5">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-display font-semibold text-sm flex items-center gap-2">
                    Table:{" "}
                    <code className="text-primary font-mono">{tbl.key}</code>
                    <Badge variant="secondary" className="text-xs font-normal">
                      {tbl.access === "index" ? "index" : "loop"}
                    </Badge>
                  </h3>
                  {tbl.access !== "index" && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => addRow(tbl.key, tbl.columns)}
                    >
                      <Plus className="w-3.5 h-3.5 mr-1" /> Thêm dòng
                    </Button>
                  )}
                </div>

                <div className="space-y-2">
                  {(tableValues[tbl.key] ?? []).map((row, ri) => (
                    <div key={ri} className="flex items-center gap-2">
                      {tbl.columns.map((col) => (
                        <Input
                          key={col}
                          placeholder={tbl.column_labels[col] ?? col}
                          title={tbl.column_hints?.[col] ?? tbl.column_labels[col] ?? col}
                          value={row[col] ?? ""}
                          onChange={(e) => setCell(tbl.key, ri, col, e.target.value)}
                          className="flex-1 min-w-0"
                        />
                      ))}
                      {tbl.access !== "index" && (
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => removeRow(tbl.key, ri)}
                          className="shrink-0 text-muted-foreground hover:text-destructive"
                          disabled={(tableValues[tbl.key]?.length ?? 0) <= 1}
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ))}

            {/* JSON Preview */}
            <div className="border-t border-border pt-5">
              <Label className="text-xs text-muted-foreground">JSON Preview (chỉ đọc)</Label>
              <Textarea
                readOnly
                className="mt-1.5 font-mono text-xs h-32"
                value={JSON.stringify(buildPayload(), null, 2)}
              />
            </div>

            {/* Async job result */}
            {jobId && (
              <div className="bg-muted rounded-lg px-4 py-3 flex items-center gap-3 text-sm">
                <div className="w-2 h-2 rounded-full bg-warning animate-pulse" />
                <span>
                  Job đang xử lý:{" "}
                  <code className="text-primary font-mono">{jobId}</code>
                  {" — kiểm tra tại trang "}
                  <a href="/jobs" className="text-primary underline">
                    Jobs
                  </a>
                </span>
              </div>
            )}

            <Button
              className="w-full"
              size="lg"
              onClick={handleRender}
              disabled={rendering}
            >
              {rendering ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" /> Đang tạo hợp đồng…
                </>
              ) : (
                <>
                  <Download className="w-4 h-4 mr-2" />
                  {renderMode === "sync" ? "Tạo hợp đồng & Tải ngay" : "Tạo job Async"}
                </>
              )}
            </Button>
          </>
        )}
      </div>
    </div>
  );
};

export default Render;
