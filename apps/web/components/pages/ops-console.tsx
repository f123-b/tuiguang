"use client";
import { Badge, Card } from "@xuliu/ui";
import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import { Field, PageHeader, type PageProps } from "../page-shared";

type Event = {
  id: string;
  created_at: string;
  run_id: string | null;
  stage: string;
  status: string;
  error_code: string | null;
  trace_id: string;
  context: Record<string, unknown>;
};
export function OpsConsole({ path }: PageProps) {
  const [data, setData] = useState<unknown>(null),
    [error, setError] = useState(""),
    [filter, setFilter] = useState("");
  const release = path.startsWith("/ops/releases"),
    maintenance = path.startsWith("/ops/maintenance"),
    runId = path.startsWith("/ops/diagnostics/") ? path.split("/")[3] : null;
  useEffect(() => {
    setData(null);
    setError("");
    api(
      maintenance
        ? "/ops/maintenance"
        : release
          ? "/releases/current"
          : runId
            ? `/creator-runs/${runId}/diagnostic`
            : "/ops/diagnostics",
    )
      .then(setData)
      .catch((e) => setError(e.message));
  }, [path]);
  const rows = Array.isArray(data)
    ? (data as Event[]).filter(
        (e) =>
          !filter ||
          `${e.stage} ${e.error_code || ""} ${e.trace_id} ${e.run_id || ""}`.includes(
            filter,
          ),
      )
    : [];
  return (
    <>
      <PageHeader
        title={
          release
            ? "运行版本清单"
            : maintenance
              ? "本机维护状态"
              : runId
                ? "任务执行链与证据"
                : "诊断与维护"
        }
        description="只展示本工作区的脱敏事件。观察到的失败与推测原因分开；没有证据时不生成根因结论。"
      />
      <div className="tabs">
        <Link href="/ops/diagnostics">任务事件</Link>
        <Link href="/ops/releases">版本清单</Link>
        <Link href="/ops/maintenance">维护状态</Link>
      </div>
      <Card>
        {error ? (
          <p role="alert">{error}</p>
        ) : data ? (
          Array.isArray(data) ? (
            <>
              <Field label="在最近 200 条事件中筛选错误码 / Trace / 任务">
                <input
                  value={filter}
                  onChange={(e) => setFilter(e.target.value)}
                />
              </Field>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>时间 / 阶段</th>
                      <th>实际状态</th>
                      <th>错误与证据</th>
                      <th>操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((e) => (
                      <tr key={e.id}>
                        <td>
                          {e.created_at}
                          <br />
                          {e.stage}
                        </td>
                        <td>
                          <Badge
                            tone={e.status === "error" ? "danger" : "neutral"}
                          >
                            {e.status}
                          </Badge>
                        </td>
                        <td>
                          {e.error_code || "无错误码"}
                          <details>
                            <summary>脱敏上下文</summary>
                            <pre className="diagnostic-json">
                              {JSON.stringify(
                                { trace_id: e.trace_id, ...e.context },
                                null,
                                2,
                              )}
                            </pre>
                          </details>
                        </td>
                        <td>
                          {e.run_id ? (
                            <Link
                              href={`/ops/diagnostics/${e.run_id}`}
                              className="text-link"
                            >
                              查看执行链
                            </Link>
                          ) : (
                            "无关联日任务"
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {!rows.length && <p>没有匹配的真实事件。</p>}
            </>
          ) : (
            <pre className="diagnostic-json">
              {JSON.stringify(data, null, 2)}
            </pre>
          )
        ) : (
          <p>正在读取…</p>
        )}
      </Card>
    </>
  );
}
