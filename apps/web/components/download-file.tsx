"use client";
import { Button } from "@xuliu/ui";
import { useState } from "react";

export function DownloadFile({
  href,
  filename,
  children,
}: {
  href: string;
  filename: string;
  children: React.ReactNode;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  return (
    <>
      <Button
        variant="secondary"
        disabled={busy}
        onClick={async () => {
          setBusy(true);
          setError("");
          try {
            const response = await fetch(href, {
              credentials: "same-origin",
              cache: "no-store",
            });
            if (!response.ok) {
              const body = await response.json().catch(() => null);
              throw new Error(
                body?.error?.message || "文件暂不可下载，请刷新作品状态后重试",
              );
            }
            const blob = await response.blob();
            if (!blob.size)
              throw new Error("没有收到有效文件，请重新生成后再下载");
            const url = URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = url;
            link.download = filename;
            document.body.appendChild(link);
            link.click();
            link.remove();
            setTimeout(() => URL.revokeObjectURL(url), 60000);
          } catch (e) {
            setError((e as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        {busy ? "正在准备文件…" : children}
      </Button>
      {error && (
        <p className="alert warning" role="alert">
          {error}
        </p>
      )}
    </>
  );
}
