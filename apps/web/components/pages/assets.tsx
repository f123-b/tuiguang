"use client";
import { Badge, Button, Card, EmptyState } from "@xuliu/ui";
import { ArrowDownToLine, Clapperboard, FileText, Upload } from "lucide-react";
import Link from "next/link";
import { api } from "../../lib/api";

import { Field, PageHeader, type PageProps } from "../page-shared";
export function AssetsPage({ store, action, busy }: PageProps) {
  const brand = store.brands[0];
  return (
    <>
      <PageHeader
        title="让每一份素材，都有清楚的来处"
        description="支持 PNG、JPG、WebP、MP4、MOV，单个文件最大 50 MB。上传后保存在当前工作区。"
      />
      <div className="form-columns">
        <Card>
          <h2>上传品牌素材</h2>
          {brand ? (
            <form
              className="form-stack"
              onSubmit={(e) => {
                e.preventDefault();
                const data = new FormData(e.currentTarget);
                action(
                  () =>
                    api(`/brands/${brand.id}/assets`, {
                      method: "POST",
                      body: data,
                    }),
                  "素材与授权信息已保存",
                );
              }}
            >
              <Field label="选择截图、录屏或授权素材">
                <input
                  name="file"
                  type="file"
                  accept=".png,.jpg,.jpeg,.webp,.mp4,.mov"
                  required
                />
              </Field>
              <Field label="素材来源">
                <input
                  name="source"
                  required
                  placeholder="例如：本人录制的 1.0 版软件演示"
                />
              </Field>
              <Field label="授权说明">
                <textarea
                  name="license_note"
                  required
                  rows={3}
                  placeholder="说明素材的使用权与适用范围"
                />
              </Field>
              <label className="checkline">
                <input name="verified" type="checkbox" value="true" />
                我确认有权使用这份素材
              </label>
              <Button disabled={busy} type="submit">
                <Upload size={16} />
                上传并保存
              </Button>
            </form>
          ) : (
            <EmptyState
              title="请先建立品牌"
              description="素材需要归属于一个真实产品。"
              action={
                <Link className="button primary" href="/brand">
                  添加品牌
                </Link>
              }
            />
          )}
        </Card>
        <Card>
          <h2>
            素材库 <span className="muted">{store.assets.length}</span>
          </h2>
          {store.assets.length ? (
            <div className="asset-list">
              {store.assets.map((a) => (
                <div key={a.id}>
                  <div className="asset-icon">
                    {a.kind === "image" ? (
                      <FileText size={21} />
                    ) : (
                      <Clapperboard size={21} />
                    )}
                  </div>
                  <div>
                    <strong>{a.name}</strong>
                    <p>{a.source}</p>
                    <Badge tone={a.verified ? "success" : "warning"}>
                      {a.verified ? "用户确认授权" : "授权待核实"}
                    </Badge>
                  </div>
                  <Button
                    variant="quiet"
                    disabled={busy}
                    onClick={() =>
                      action(
                        () =>
                          api(`/assets/${a.id}`, {
                            method: "PATCH",
                            body: JSON.stringify({
                              verified: !a.verified,
                              reason: a.verified
                                ? "用户撤销授权或标记版本过期"
                                : "用户重新核实来源和使用授权",
                            }),
                          }),
                        a.verified
                          ? "素材已停用，相关待发布稿需重新审核"
                          : "已重新记录用户核实结果",
                      )
                    }
                  >
                    {a.verified ? "停用 / 标记过期" : "我已重新核实授权"}
                  </Button>
                  <a
                    className="icon-button"
                    aria-label={`下载 ${a.name}`}
                    href={`/api/v1/assets/${a.id}/download`}
                  >
                    <ArrowDownToLine size={17} />
                  </a>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              title="素材库等待你的第一份资料"
              description="真实软件截图和录屏，是产品内容最好的起点。"
            />
          )}
        </Card>
      </div>
    </>
  );
}
