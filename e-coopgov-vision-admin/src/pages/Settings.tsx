import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Save, Loader2, RotateCcw, BellRing, Cpu, Server } from "lucide-react";
import { toast } from "sonner";
import { getAppConfig, updateAppConfig, ConfigSetting } from "@/lib/api";

const GROUP_ICONS: Record<string, typeof BellRing> = {
  notify: BellRing,
  ai: Cpu,
  render: Server,
};

function FieldInput({ s, value, onChange }: { s: ConfigSetting; value: unknown; onChange: (v: unknown) => void }) {
  if (s.type === "bool") {
    return (
      <div className="flex items-center justify-between">
        <div>
          <Label>{s.label}</Label>
          <p className="text-xs text-muted-foreground mt-0.5">{s.hint}</p>
        </div>
        <Switch checked={!!value} onCheckedChange={onChange} />
      </div>
    );
  }
  if (s.type === "text") {
    return (
      <div>
        <Label>{s.label}</Label>
        <Textarea
          className="mt-1.5 font-mono text-xs"
          rows={2}
          placeholder={s.hint}
          value={(value as string) ?? ""}
          onChange={(e) => onChange(e.target.value)}
        />
        <p className="text-xs text-muted-foreground mt-1">{s.hint}</p>
      </div>
    );
  }
  return (
    <div>
      <Label>{s.label}</Label>
      <Input
        className="mt-1.5 font-mono text-sm"
        type={s.type === "password" ? "password" : s.type === "int" || s.type === "float" ? "number" : "text"}
        placeholder={s.type === "password" && s.has_value ? "•••••••• (đã lưu — để trống = giữ nguyên)" : s.hint}
        value={s.type === "password" ? ((value as string) ?? "") : ((value as string | number) ?? "")}
        onChange={(e) => onChange(e.target.value)}
      />
      <p className="text-xs text-muted-foreground mt-1">{s.hint}</p>
    </div>
  );
}

const SettingsPage = () => {
  const qc = useQueryClient();
  const { data, isLoading, isError } = useQuery({ queryKey: ["app-config"], queryFn: getAppConfig });
  const [draft, setDraft] = useState<Record<string, unknown>>({});
  const [dirty, setDirty] = useState<Set<string>>(new Set());

  function setVal(key: string, v: unknown) {
    setDraft((p) => ({ ...p, [key]: v }));
    setDirty((p) => new Set(p).add(key));
  }

  const saveMutation = useMutation({
    mutationFn: () => updateAppConfig(draft),
    onSuccess: (r) => {
      qc.invalidateQueries({ queryKey: ["app-config"] });
      setDraft({});
      setDirty(new Set());
      toast.success(`Đã lưu ${r.updated.length} mục`);
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const resetMutation = useMutation({
    mutationFn: (key: string) => updateAppConfig({ [key]: null }),
    onSuccess: (_data, key) => {
      qc.invalidateQueries({ queryKey: ["app-config"] });
      setDraft((p) => {
        const n = { ...p };
        delete n[key];
        return n;
      });
      toast.success("Đã về mặc định");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  function valOf(s: ConfigSetting): unknown {
    if (s.key in draft) return draft[s.key];
    if (s.type === "password") return ""; // không hiện mật khẩu thật, rỗng = giữ nguyên
    return s.value;
  }

  return (
    <div className="space-y-6 max-w-3xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-display font-bold">Cấu hình hệ thống</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Sửa trực tiếp tại đây, lưu vào database — không cần đụng file .env, không mất khi restart
          </p>
        </div>
        <Button onClick={() => saveMutation.mutate()} disabled={dirty.size === 0 || saveMutation.isPending}>
          {saveMutation.isPending ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
          Lưu ({dirty.size})
        </Button>
      </div>

      {isLoading && (
        <div className="flex items-center justify-center h-40">
          <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
        </div>
      )}
      {isError && <p className="text-sm text-destructive">Không tải được cấu hình (cần quyền admin)</p>}

      {(data?.groups ?? []).map((g) => {
        const Icon = GROUP_ICONS[g.id] ?? Server;
        return (
          <div key={g.id} className="bg-card rounded-xl border border-border p-6">
            <div className="flex items-center gap-3 mb-5">
              <div className="w-9 h-9 rounded-lg bg-primary/10 flex items-center justify-center">
                <Icon className="w-4 h-4 text-primary" />
              </div>
              <div>
                <h2 className="font-display font-semibold">{g.title}</h2>
                <p className="text-xs text-muted-foreground">{g.hint}</p>
              </div>
            </div>
            <div className="space-y-5">
              {g.settings.map((s) => (
                <div key={s.key} className="border-t border-border pt-4 first:border-0 first:pt-0">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <FieldInput s={s} value={valOf(s)} onChange={(v) => setVal(s.key, v)} />
                    </div>
                  </div>
                  <div className="flex items-center gap-2 mt-1.5">
                    <Badge variant="outline" className="text-[11px]">
                      {s.key in draft ? "chưa lưu" : s.source === "db" ? "đã sửa" : "mặc định"}
                    </Badge>
                    {s.restart && <Badge variant="secondary" className="text-[11px]">cần restart API</Badge>}
                    {s.source === "db" && !(s.key in draft) && (
                      <button
                        className="text-[11px] text-muted-foreground hover:text-foreground flex items-center gap-1"
                        onClick={() => resetMutation.mutate(s.key)}
                      >
                        <RotateCcw className="w-3 h-3" /> Về mặc định
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default SettingsPage;
