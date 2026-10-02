import { useState, useRef, ChangeEvent } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  FileText,
  Upload,
  Search,
  MoreVertical,
  Tag,
  Calendar,
  Eye,
  Trash2,
  Loader2,
  AlertCircle,
  Pencil,
  Save,
  Sparkles,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import { getTemplates, uploadTemplate, deleteTemplate, updateLabels, relabelTemplate, Template } from "@/lib/api";

const Templates = () => {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [uploadName, setUploadName] = useState("");
  const [uploadDesc, setUploadDesc] = useState("");
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Label editing state
  const [editLabelsTemplate, setEditLabelsTemplate] = useState<Template | null>(null);
  const [labelEdits, setLabelEdits] = useState<Record<string, string>>({});

  const { data: templates = [], isLoading, isError } = useQuery({
    queryKey: ["templates"],
    queryFn: getTemplates,
  });

  const uploadMutation = useMutation({
    mutationFn: () => uploadTemplate(uploadFile!, uploadName, uploadDesc || undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["templates"] });
      toast.success("Template đã được upload và phân tích thành công");
      setUploadOpen(false);
      setUploadName("");
      setUploadDesc("");
      setUploadFile(null);
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteTemplate(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["templates"] });
      toast.success("Đã xóa template");
      setSelectedTemplate(null);
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const labelsMutation = useMutation({
    mutationFn: ({ id, labels }: { id: string; labels: Record<string, string> }) =>
      updateLabels(id, labels),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["templates"] });
      toast.success("Đã cập nhật labels");
      setEditLabelsTemplate(null);
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const relabelMutation = useMutation({
    mutationFn: (id: string) => relabelTemplate(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["templates"] });
      queryClient.invalidateQueries({ queryKey: ["template"] });
      toast.success("Đã chuẩn hóa nhãn tiếng Việt (giữ nguyên nhãn bạn đã sửa tay)");
    },
    onError: (err: Error) => toast.error(err.message),
  });

  function openLabelEditor(tpl: Template, e: React.MouseEvent) {
    e.stopPropagation();
    const initial: Record<string, string> = {};
    (tpl.metadata?.fields ?? []).forEach((f) => {
      initial[f.key] = tpl.label_config?.[f.key] ?? f.label ?? "";
    });
    (tpl.metadata?.tables ?? []).forEach((t) => {
      t.columns.forEach((col) => {
        const colKey = `${t.key}.${col}`;
        initial[colKey] = tpl.label_config?.[colKey] ?? t.column_labels[col] ?? "";
      });
    });
    setLabelEdits(initial);
    setEditLabelsTemplate(tpl);
  }

  const filtered = templates.filter(
    (t) =>
      t.name.toLowerCase().includes(search.toLowerCase()) ||
      (t.description ?? "").toLowerCase().includes(search.toLowerCase())
  );

  function handleFileChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0] ?? null;
    setUploadFile(file);
    if (file && !uploadName) setUploadName(file.name.replace(/\.docx$/i, ""));
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file?.name.endsWith(".docx")) {
      setUploadFile(file);
      if (!uploadName) setUploadName(file.name.replace(/\.docx$/i, ""));
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-display font-bold">Templates</h1>
          <p className="text-muted-foreground text-sm mt-1">Quản lý mẫu tài liệu Word</p>
        </div>

        <Dialog open={uploadOpen} onOpenChange={setUploadOpen}>
          <DialogTrigger asChild>
            <Button>
              <Upload className="w-4 h-4 mr-2" /> Upload Template
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle className="font-display">Upload Template mới</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 pt-2">
              <div>
                <Label>Tên template</Label>
                <Input
                  placeholder="VD: Hợp đồng lao động"
                  className="mt-1.5"
                  value={uploadName}
                  onChange={(e) => setUploadName(e.target.value)}
                />
              </div>
              <div>
                <Label>Mô tả</Label>
                <Textarea
                  placeholder="Mô tả ngắn về template..."
                  className="mt-1.5"
                  value={uploadDesc}
                  onChange={(e) => setUploadDesc(e.target.value)}
                />
              </div>
              <div>
                <Label>File Word (.docx)</Label>
                <div
                  className="mt-1.5 border-2 border-dashed border-border rounded-lg p-8 text-center cursor-pointer hover:border-primary/50 transition-colors"
                  onDrop={handleDrop}
                  onDragOver={(e) => e.preventDefault()}
                  onClick={() => fileInputRef.current?.click()}
                >
                  {uploadFile ? (
                    <p className="text-sm font-medium text-primary">{uploadFile.name}</p>
                  ) : (
                    <>
                      <Upload className="w-8 h-8 text-muted-foreground mx-auto mb-2" />
                      <p className="text-sm text-muted-foreground">
                        Kéo thả file hoặc{" "}
                        <span className="text-primary font-medium">chọn file</span>
                      </p>
                      <p className="text-xs text-muted-foreground mt-1">
                        Chỉ chấp nhận .docx, tối đa 10MB
                      </p>
                    </>
                  )}
                </div>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".docx"
                  className="hidden"
                  onChange={handleFileChange}
                />
              </div>
              <Button
                className="w-full"
                disabled={!uploadFile || !uploadName || uploadMutation.isPending}
                onClick={() => uploadMutation.mutate()}
              >
                {uploadMutation.isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" /> Đang xử lý…
                  </>
                ) : (
                  "Upload & Phân tích"
                )}
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="Tìm template..."
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
          <AlertCircle className="w-4 h-4" /> Không thể tải templates
        </div>
      )}
      {!isLoading && !isError && filtered.length === 0 && (
        <p className="text-sm text-muted-foreground">
          Không có template nào{search ? " khớp tìm kiếm" : ""}.
        </p>
      )}

      {/* Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {filtered.map((template) => (
          <div
            key={template.id}
            className="bg-card rounded-xl border border-border p-5 hover:shadow-md transition-shadow animate-fade-in cursor-pointer"
            onClick={() => setSelectedTemplate(template)}
          >
            <div className="flex items-start justify-between">
              <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                <FileText className="w-5 h-5 text-primary" />
              </div>
              <DropdownMenu>
                <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                  <button className="text-muted-foreground hover:text-foreground p-1">
                    <MoreVertical className="w-4 h-4" />
                  </button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem onClick={(e) => openLabelEditor(template, e)}>
                    <Pencil className="w-3.5 h-3.5 mr-2" /> Chỉnh sửa Labels
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    onClick={(e) => {
                      e.stopPropagation();
                      relabelMutation.mutate(template.id);
                    }}
                  >
                    <Sparkles className="w-3.5 h-3.5 mr-2" /> Chuẩn hóa nhãn TV
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    className="text-destructive focus:text-destructive"
                    onClick={(e) => {
                      e.stopPropagation();
                      deleteMutation.mutate(template.id);
                    }}
                  >
                    <Trash2 className="w-3.5 h-3.5 mr-2" /> Xóa template
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>

            <h3 className="font-display font-semibold mt-3">{template.name}</h3>
            <p className="text-sm text-muted-foreground mt-1 line-clamp-2">
              {template.description ?? "Chưa có mô tả"}
            </p>

            <div className="flex flex-wrap gap-1.5 mt-3">
              {(template.metadata?.fields ?? []).slice(0, 3).map((f) => (
                <Badge key={f.key} variant="secondary" className="text-xs font-normal">
                  <Tag className="w-3 h-3 mr-1" /> {f.label ?? f.key}
                </Badge>
              ))}
              {(template.metadata?.fields?.length ?? 0) > 3 && (
                <Badge variant="secondary" className="text-xs font-normal">
                  +{template.metadata.fields.length - 3}
                </Badge>
              )}
            </div>

            <div className="flex items-center gap-4 mt-4 pt-3 border-t border-border text-xs text-muted-foreground">
              <span className="flex items-center gap-1">
                <Calendar className="w-3 h-3" />{" "}
                {new Date(template.created_at).toLocaleDateString("vi-VN")}
              </span>
              <span className="flex items-center gap-1">
                <Eye className="w-3 h-3" />
                {template.metadata?.fields?.length ?? 0} fields,&nbsp;
                {template.metadata?.tables?.length ?? 0} tables
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Detail dialog */}
      <Dialog open={!!selectedTemplate} onOpenChange={() => setSelectedTemplate(null)}>
        <DialogContent className="max-w-lg max-h-[85vh] overflow-y-auto">
          {selectedTemplate && (
            <>
              <DialogHeader>
                <DialogTitle className="font-display">{selectedTemplate.name}</DialogTitle>
              </DialogHeader>
              <p className="text-sm text-muted-foreground">
                {selectedTemplate.description ?? "Chưa có mô tả"}
              </p>

              <div className="space-y-3 mt-2">
                <h4 className="text-sm font-semibold">
                  Fields ({selectedTemplate.metadata?.fields?.length ?? 0})
                </h4>
                <div className="space-y-2">
                  {(selectedTemplate.metadata?.fields ?? []).map((f) => (
                    <div
                      key={f.key}
                      className="flex items-center justify-between bg-muted rounded-lg px-3 py-2"
                    >
                      <div>
                        <code className="text-xs text-primary font-mono">{`{{ ${f.key} }}`}</code>
                        <p className="text-sm mt-0.5">{f.label ?? f.key}</p>
                      </div>
                      <Badge variant="outline" className="text-xs">
                        {f.type}
                      </Badge>
                    </div>
                  ))}
                  {(selectedTemplate.metadata?.fields?.length ?? 0) === 0 && (
                    <p className="text-xs text-muted-foreground">Không có field nào</p>
                  )}
                </div>

                {(selectedTemplate.metadata?.tables?.length ?? 0) > 0 && (
                  <>
                    <h4 className="text-sm font-semibold mt-4">
                      Tables ({selectedTemplate.metadata.tables.length})
                    </h4>
                    {selectedTemplate.metadata.tables.map((t) => (
                      <div key={t.key} className="bg-muted rounded-lg px-3 py-2">
                        <code className="text-xs text-primary font-mono">
                          {t.access === "index"
                            ? `{{ ${t.key}[0].${t.columns[0] ?? "…"} }}`
                            : `{% for ${t.loop_var} in ${t.key} %}`}
                        </code>
                        <div className="flex flex-wrap gap-1.5 mt-1.5">
                          {t.columns.map((col) => (
                            <Badge key={col} variant="secondary" className="text-xs">
                              {t.column_labels[col] ?? col}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    ))}
                  </>
                )}
              </div>

              <div className="flex gap-2 mt-4">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={(e) => { setSelectedTemplate(null); openLabelEditor(selectedTemplate, e); }}
                >
                  <Pencil className="w-3.5 h-3.5 mr-1.5" /> Chỉnh sửa Labels
                </Button>
                <Button
                  variant="destructive"
                  size="sm"
                  disabled={deleteMutation.isPending}
                  onClick={() => deleteMutation.mutate(selectedTemplate.id)}
                >
                  {deleteMutation.isPending ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Trash2 className="w-3.5 h-3.5 mr-1.5" />
                  )}
                  Xóa template
                </Button>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
      {/* Label edit dialog */}
      <Dialog open={!!editLabelsTemplate} onOpenChange={(open) => { if (!open) setEditLabelsTemplate(null); }}>
        <DialogContent className="max-w-lg max-h-[85vh] overflow-y-auto">
          {editLabelsTemplate && (
            <>
              <DialogHeader>
                <DialogTitle className="font-display">
                  Chỉnh sửa Labels — {editLabelsTemplate.name}
                </DialogTitle>
              </DialogHeader>
              <p className="text-xs text-muted-foreground mt-1">
                Đặt tên hiển thị cho từng trường. Để trống = dùng tên gốc.
              </p>

              <div className="space-y-3 mt-3">
                {/* Fields */}
                {(editLabelsTemplate.metadata?.fields?.length ?? 0) > 0 && (
                  <>
                    <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Fields</p>
                    {editLabelsTemplate.metadata.fields.map((f) => (
                      <div key={f.key} className="flex items-center gap-3">
                        <code className="text-xs text-primary font-mono w-36 shrink-0">{`{{ ${f.key} }}`}</code>
                        <Input
                          placeholder={f.key}
                          value={labelEdits[f.key] ?? ""}
                          onChange={(e) =>
                            setLabelEdits((prev) => ({ ...prev, [f.key]: e.target.value }))
                          }
                          className="flex-1"
                        />
                      </div>
                    ))}
                  </>
                )}

                {/* Table columns */}
                {(editLabelsTemplate.metadata?.tables ?? []).map((t) => (
                  <div key={t.key}>
                    <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mt-2">
                      Table: {t.key}
                    </p>
                    {t.columns.map((col) => {
                      const colKey = `${t.key}.${col}`;
                      return (
                        <div key={colKey} className="flex items-center gap-3 mt-2">
                          <code className="text-xs text-primary font-mono w-36 shrink-0">{col}</code>
                          <Input
                            placeholder={col}
                            value={labelEdits[colKey] ?? ""}
                            onChange={(e) =>
                              setLabelEdits((prev) => ({ ...prev, [colKey]: e.target.value }))
                            }
                            className="flex-1"
                          />
                        </div>
                      );
                    })}
                  </div>
                ))}
              </div>

              <Button
                className="w-full mt-4"
                disabled={labelsMutation.isPending}
                onClick={() => {
                  // Only send non-empty labels
                  const clean = Object.fromEntries(
                    Object.entries(labelEdits).filter(([, v]) => v.trim() !== "")
                  );
                  labelsMutation.mutate({ id: editLabelsTemplate.id, labels: clean });
                }}
              >
                {labelsMutation.isPending ? (
                  <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Đang lưu…</>
                ) : (
                  <><Save className="w-4 h-4 mr-2" /> Lưu Labels</>
                )}
              </Button>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Templates;
