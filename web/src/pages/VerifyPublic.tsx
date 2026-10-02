import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ShieldCheck, ShieldX, Loader2, Download, Printer } from "lucide-react";
import { Button } from "@/components/ui/button";

interface VerifyResult {
  hop_le: boolean;
  verify_code: string;
  template: string | null;
  bien_so: string | null;
  created_at: string | null;
  download_url: string | null;
}

async function verifyPublic(code: string): Promise<VerifyResult> {
  // Không cần đăng nhập — CSGT/khách quét QR
  const res = await fetch(`/api/verify/${code}`);
  if (!res.ok) throw new Error("Mã xác thực không tồn tại");
  return res.json();
}

export default function VerifyPublic() {
  const { code = "" } = useParams();
  const { data, isLoading, isError } = useQuery({
    queryKey: ["verify-public", code],
    queryFn: () => verifyPublic(code.toUpperCase()),
    retry: false,
  });

  return (
    <div className="min-h-screen bg-muted/40 flex items-center justify-center p-4">
      <div className="bg-card rounded-2xl border shadow-lg p-8 max-w-md w-full text-center space-y-4">
        <p className="text-xs text-muted-foreground tracking-wide">XÁC THỰC VĂN BẢN — CoopGo</p>
        {isLoading && (
          <div className="flex flex-col items-center gap-2 py-6">
            <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
            <p className="text-sm text-muted-foreground">Đang kiểm tra mã {code}…</p>
          </div>
        )}
        {isError && (
          <>
            <ShieldX className="w-14 h-14 text-destructive mx-auto" />
            <h1 className="text-xl font-bold text-destructive">Không hợp lệ</h1>
            <p className="text-sm text-muted-foreground">
              Mã <code className="font-mono">{code}</code> không tồn tại trong hệ thống.
              Văn bản này có thể là giả — hãy liên hệ HTX để xác minh.
            </p>
          </>
        )}
        {data && (
          <>
            <ShieldCheck className="w-14 h-14 text-green-600 mx-auto" />
            <h1 className="text-xl font-bold text-green-700">Văn bản hợp lệ</h1>
            <div className="text-sm text-left bg-muted rounded-lg p-4 space-y-1.5">
              <p><span className="text-muted-foreground">Loại văn bản:</span> <b>{data.template ?? "—"}</b></p>
              <p><span className="text-muted-foreground">Biển số:</span> <b>{data.bien_so ?? "—"}</b></p>
              <p><span className="text-muted-foreground">Mã xác thực:</span> <code className="font-mono">{data.verify_code}</code></p>
              <p><span className="text-muted-foreground">Ngày cấp:</span> {data.created_at ? new Date(data.created_at).toLocaleString("vi-VN") : "—"}</p>
            </div>
            <div className="flex gap-2 justify-center print:hidden">
              {data.download_url && (
                <a href={`/api${data.download_url}`} download>
                  <Button size="sm"><Download className="w-4 h-4 mr-1.5" /> Tải bản gốc</Button>
                </a>
              )}
              <Button size="sm" variant="outline" onClick={() => window.print()}>
                <Printer className="w-4 h-4 mr-1.5" /> In
              </Button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
