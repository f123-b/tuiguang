"use client";
import { Badge, Button, Card } from "@xuliu/ui";
import { ArrowRight, Check, FolderOpen, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { api } from "../../lib/api";

import { Field, PageHeader, type PageProps } from "../page-shared";
import { ProductSources } from "./product-sources";
import { BrandChanges } from "./evidence";
export function BrandPage({ store, action, busy }: PageProps) {
  const brand = store.brands[0];
  return (
    <>
      <PageHeader
        eyebrow="BRAND FOUNDATION"
        title="真实的产品，是好内容的起点"
        description="你的创作者只会引用已核实的品牌事实。更新资料后，待发布稿件会重新进入审核。"
      >
        <Link className="button secondary" href="/studio/assets">
          <FolderOpen size={16} />
          管理素材
        </Link>
      </PageHeader>
      {brand && (
        <ProductSources brandId={brand.id} action={action} busy={busy} />
      )}
      {brand && <BrandChanges brand={brand} action={action} busy={busy} />}
      <div className="form-columns">
        <Card>
          <div className="section-heading">
            <h2>{brand ? "编辑品牌资料" : "建立品牌资料"}</h2>
            <Badge tone="blue">
              {brand ? `版本 ${brand.revision}` : "第一步"}
            </Badge>
          </div>
          <form
            className="form-stack"
            key={brand?.id || "new"}
            onSubmit={(e) => {
              e.preventDefault();
              const f = new FormData(e.currentTarget);
              const facts = String(f.get("facts"))
                .split("\n")
                .filter((l) => l.trim())
                .map((l) => {
                  const [claim, ...source] = l.split("|");
                  return {
                    claim: claim.trim(),
                    source: source.join("|").trim(),
                    verified: f.get("verified") === "on",
                  };
                });
              action(
                () =>
                  api(brand ? `/brands/${brand.id}` : "/brands", {
                    method: brand ? "PATCH" : "POST",
                    body: JSON.stringify({
                      name: f.get("name"),
                      description: f.get("description"),
                      website: f.get("website"),
                      audience: f.get("audience"),
                      facts,
                    }),
                  }),
                "品牌事实已保存",
              );
            }}
          >
            <Field label="产品 / 品牌名称">
              <input
                name="name"
                required
                maxLength={120}
                defaultValue={brand?.name}
                placeholder="例如：你的软件名称"
              />
            </Field>
            <Field label="产品简介">
              <textarea
                name="description"
                rows={3}
                maxLength={5000}
                defaultValue={brand?.description}
                placeholder="这个产品为谁，解决什么具体问题？"
              />
            </Field>
            <div className="form-grid">
              <Field label="产品官网（可选）">
                <input
                  type="url"
                  name="website"
                  defaultValue={brand?.website}
                  placeholder="https://"
                />
              </Field>
              <Field label="目标用户">
                <input
                  name="audience"
                  defaultValue={brand?.audience}
                  placeholder="例如：独立开发者、小型团队"
                />
              </Field>
            </div>
            <Field
              label="功能事实与来源"
              hint="每行一条，用 | 分隔：真实功能 | 说明书、版本记录或证据 URL。"
            >
              <textarea
                name="facts"
                rows={6}
                required
                defaultValue={brand?.facts
                  .map((f) => `${f.claim} | ${f.source}`)
                  .join("\n")}
                placeholder="支持本地文件整理 | 1.0 版使用说明第 3 页"
              />
            </Field>
            <label className="checkline">
              <input
                type="checkbox"
                name="verified"
                defaultChecked={brand?.facts.every((f) => f.verified)}
              />
              我已核实上述功能及资料来源，允许用于创作
            </label>
            <div className="form-actions">
              <Button disabled={busy} type="submit">
                <Check size={16} />
                保存品牌资料
              </Button>
              {brand && (
                <Link className="button secondary" href="/creator">
                  设置创作者
                  <ArrowRight size={14} />
                </Link>
              )}
            </div>
          </form>
        </Card>
        <div>
          <Card className="guide-card">
            <span className="guide-icon">
              <ShieldCheck size={24} />
            </span>
            <h2>让每一个卖点都有出处</h2>
            <p>录屏、正式说明书和已经发布的版本记录，都能成为事实依据。</p>
            <div className="guide-list">
              <p>
                <Check size={14} />
                已上线、可验证的真实功能
              </p>
              <p>
                <Check size={14} />
                清楚的来源和适用版本
              </p>
              <p>
                <Check size={14} />
                用户核实后再进入创作
              </p>
            </div>
            <div className="subtle-note">
              规划中的功能请保持未核实，避免被写成已上线。
            </div>
          </Card>
          {brand && (
            <Card>
              <h2>已记录的事实</h2>
              <div className="fact-list">
                {brand.facts.map((f) => (
                  <div key={f.id}>
                    <Badge tone={f.verified ? "success" : "warning"}>
                      {f.verified ? "用户已核实" : "待核实"}
                    </Badge>
                    <strong>{f.claim}</strong>
                    <p>{f.source}</p>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </div>
      </div>
    </>
  );
}
