"use client";
import { Badge, Button, Card, EmptyState } from "@xuliu/ui";
import {
  ArrowDownToLine,
  ArrowRight,
  Gauge,
  Search,
  Upload,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { api, post } from "../../lib/api";

import {
  dateText,
  Field,
  PageHeader,
  platformName,
  type PageProps,
} from "../page-shared";
export function AnalyticsPage({ store, action, busy, path }: PageProps) {
  const [preview, setPreview] = useState<{
    id: string;
    rows: Record<string, unknown>[];
    data_source: string;
  } | null>(null);
  const importing = path.endsWith("/import");
  return (
    <>
      <PageHeader
        eyebrow="REAL DATA, REAL LEARNING"
        title={
          importing ? "让真实的反馈，回到创作里" : "用事实看效果，让数据有出处"
        }
        description="指标来自你上传的报表；缺失值保持未知，不混加不同平台与统计窗口。"
      >
        <Link
          className="button secondary"
          href={importing ? "/analytics" : "/analytics/import"}
        >
          {importing ? <Gauge size={16} /> : <Upload size={16} />}
          {importing ? "查看数据" : "导入数据"}
        </Link>
      </PageHeader>
      {importing && (
        <Card>
          <div className="section-heading">
            <h2>上传 → 校验预览 → 确认入库</h2>
            <a className="text-link" href="/api/v1/analytics/import/template">
              <ArrowDownToLine size={14} />
              下载 CSV 模板
            </a>
          </div>
          <form
            className="form-stack max-form"
            onSubmit={(e) => {
              e.preventDefault();
              const data = new FormData(e.currentTarget);
              action(async () => {
                const result = await api<NonNullable<typeof preview>>(
                  "/analytics/import/preview",
                  { method: "POST", body: data },
                );
                setPreview(result);
              }, "报表校验通过，请核对后确认导入");
            }}
          >
            <Field
              label="数据文件"
              hint="CSV / XLSX，最大 5 MB、5000 行。先下载模板；作品 ID 可从下方复制。"
            >
              <input name="file" type="file" accept=".csv,.xlsx" required />
            </Field>
            <Field label="数据来源说明">
              <input
                name="data_source"
                required
                maxLength={180}
                placeholder="例如：本人从官方后台导出的 11 月第 1 周报表"
              />
            </Field>
            <Button type="submit" disabled={busy}>
              <Search size={15} />
              校验并预览
            </Button>
          </form>
          {preview && (
            <div className="import-preview">
              <h3>待确认 · {preview.rows.length} 行</h3>
              <p>{preview.data_source}</p>
              <pre>{JSON.stringify(preview.rows.slice(0, 5), null, 2)}</pre>
              <Button
                disabled={busy}
                onClick={() =>
                  action(async () => {
                    await api(
                      "/analytics/import/commit",
                      post({ preview_id: preview.id }),
                    );
                    setPreview(null);
                  }, "指标已持久保存；相同记录不会重复导入")
                }
              >
                确认导入 {preview.rows.length} 行
              </Button>
            </div>
          )}
          <details className="content-ids">
            <summary>查看当前内容 ID（填入报表的 content_id）</summary>
            {store.contents.map((c) => (
              <p key={c.id}>
                {c.title}
                <br />
                <code>{c.id}</code>
              </p>
            ))}
          </details>
        </Card>
      )}
      <div className="info-strip">
        <Gauge size={18} />
        <span>{store.analytics.conclusion}</span>
        <Badge>{store.analytics.snapshot_count} 条快照</Badge>
      </div>
      {!store.analytics.groups.length ? (
        <Card>
          <EmptyState
            title="没有数据，也是一种明确的状态"
            description="尚未导入真实指标。添加报表后，按平台、来源与统计窗口查看观察值。"
            action={
              !importing && (
                <Link className="button secondary" href="/analytics/import">
                  导入第一份报表
                  <ArrowRight size={14} />
                </Link>
              )
            }
          />
        </Card>
      ) : (
        store.analytics.groups.map((g, i) => (
          <Card key={i}>
            <div className="section-heading">
              <h2>
                {platformName[g.platform]} · {g.period_start} — {g.period_end}
              </h2>
              <Badge tone="blue">用户提供</Badge>
            </div>
            <p className="muted">来源：{g.data_source}</p>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>内容</th>
                    <th>阅读 / 播放</th>
                    <th>点赞</th>
                    <th>收藏</th>
                    <th>观察时间</th>
                  </tr>
                </thead>
                <tbody>
                  {g.snapshots.map((m) => (
                    <tr key={m.id}>
                      <td>
                        {store.contents.find((c) => c.id === m.content_id)
                          ?.title || m.content_id.slice(0, 8)}
                      </td>
                      <td>{m.values.views?.toLocaleString() ?? "未知"}</td>
                      <td>{m.values.likes?.toLocaleString() ?? "未知"}</td>
                      <td>{m.values.saves?.toLocaleString() ?? "未知"}</td>
                      <td>{dateText(m.observed_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        ))
      )}
    </>
  );
}
