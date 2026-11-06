"use client";
import { Badge, Button, Card } from "@xuliu/ui";
import Link from "next/link";
import { useEffect, useState } from "react";
import { api, post } from "../../lib/api";
import { Field, type PageProps } from "../page-shared";

export function HandoffOutcome({
  packageId,
  readonly,
  action,
  busy,
}: Pick<PageProps, "action" | "busy"> & {
  packageId: string;
  readonly: boolean;
}) {
  const [result, setResult] = useState<{
    package_id: string;
    outcome: string;
    notes: string;
    source: string;
  } | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    setResult(null);
    api<
      { package_id: string; outcome: string; notes: string; source: string }[]
    >("/manual-publication/outcomes")
      .then((rows) =>
        setResult(rows.find((r) => r.package_id === packageId) || null),
      )
      .catch((e) => setError(e.message));
  }, [packageId]);
  return (
    <Card>
      <details>
        <summary>暂缓、拒绝或放弃的用户记录</summary>
        <p>
          这里记录你自己提供的结果，未经平台核验。不会自动重发。真正已发布的作品仍需完成上方人工发布检查表登记。
        </p>
        {error && <p role="alert">{error}</p>}
        {result && (
          <Badge>
            用户自报 ·{" "}
            {
              (
                {
                  pending: "等待手动处理",
                  postponed: "暂缓",
                  platform_rejected: "用户报告被平台拒绝",
                  abandoned: "放弃",
                } as Record<string, string>
              )[result.outcome]
            }
          </Badge>
        )}
        <form
          className="form-stack"
          key={`${packageId}-${result?.outcome || "pending"}`}
          onSubmit={(e) => {
            e.preventDefault();
            const f = new FormData(e.currentTarget);
            action(async () => {
              setResult(
                await api(
                  `/manual-publication/packages/${packageId}/outcome`,
                  post({
                    outcome: f.get("outcome"),
                    notes: f.get("notes"),
                    confirmed: true,
                  }),
                ),
              );
            }, "用户自报结果已保存，未向平台发送请求");
          }}
        >
          <Field label="你提供的处理结果">
            <select
              name="outcome"
              defaultValue={result?.outcome || "pending"}
              disabled={readonly}
            >
              <option value="pending">等待手动处理</option>
              <option value="postponed">暂缓</option>
              <option value="platform_rejected">我报告被平台拒绝</option>
              <option value="abandoned">放弃</option>
            </select>
          </Field>
          <Field label="备注">
            <textarea
              name="notes"
              rows={2}
              maxLength={2000}
              defaultValue={result?.notes || ""}
              disabled={readonly}
            />
          </Field>
          <label className="checkline">
            <input type="checkbox" required disabled={readonly} />
            这是我本人提供的处理结果
          </label>
          <Button variant="secondary" type="submit" disabled={busy || readonly}>
            保存用户自报结果
          </Button>
          <Link href="/notifications" className="text-link">
            设置本软件的发布提醒
          </Link>
        </form>
      </details>
    </Card>
  );
}
