"use client";
import { Badge, Button, Card, EmptyState, StatusBadge } from "@xuliu/ui";
import {
  ArrowDownToLine,
  ArrowRight,
  Check,
  FileText,
  Plus,
  ShieldCheck,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { api, post, type Content } from "../../lib/api";

import {
  Field,
  PageHeader,
  platformName,
  type PageProps,
} from "../page-shared";
export function ContentCard({ content }: { content: Content }) {
  return (
    <Link href={`/studio/article/${content.id}`} className="content-card">
      <div className={`content-cover variant-${content.id.charCodeAt(0) % 3}`}>
        <span>PRODUCT NOTES</span>
        <h3>{content.title}</h3>
        <span className="cover-footer">
          <FileText size={14} />
          真实产品 · 内容笔记
        </span>
      </div>
      <div className="content-meta">
        <div className="row between">
          <Badge>{platformName[content.platform]}</Badge>
          <StatusBadge status={content.status} />
        </div>
        <h3>{content.title}</h3>
        <p>
          {content.generation_source === "template"
            ? "本地规则草稿"
            : "AI 生成草稿"}{" "}
          · 版本 {content.revision}
        </p>
      </div>
    </Link>
  );
}

export function ContentLibrary({ store, action, busy, path }: PageProps) {
  const [filter, setFilter] = useState("all");
  const creator = store.creators[0];
  const list = store.contents.filter(
    (c) => filter === "all" || c.status === filter,
  );
  return (
    <>
      <PageHeader
        eyebrow="CONTENT STUDIO"
        title={
          path.startsWith("/compliance")
            ? "好内容，经得起再看一眼"
            : "把真实的价值，写成好内容"
        }
        description="从草稿到审核，每一份内容都有清楚的状态和事实依据。"
      >
        <Button
          disabled={busy || !creator || creator.status !== "active"}
          onClick={() =>
            creator &&
            action(
              () =>
                api(`/creators/${creator.id}/run-today`, {
                  ...post(),
                  headers: { "Idempotency-Key": crypto.randomUUID() },
                }),
              "今日内容任务已准备",
            )
          }
        >
          <Plus size={16} />
          准备今日图文
        </Button>
      </PageHeader>
      <div className="tabs">
        {[
          ["all", "全部内容"],
          ["awaiting_user_review", "待审核"],
          ["approved_for_handoff", "已审核"],
          ["awaiting_manual_publication", "待手动发布"],
          ["user_reported_published", "用户已登记"],
        ].map(([value, label]) => (
          <button
            key={value}
            className={filter === value ? "selected" : ""}
            onClick={() => setFilter(value)}
          >
            {label}
          </button>
        ))}
      </div>
      {list.length ? (
        <div className="content-grid">
          {list.map((c) => (
            <ContentCard content={c} key={c.id} />
          ))}
        </div>
      ) : (
        <Card>
          <EmptyState
            title="这里还没有内容"
            description={
              creator
                ? "点击“准备今日图文”，后台将制作真实草稿。每位创作者每天有一条日更任务。"
                : "先完成品牌资料并建立你的创作者。"
            }
            action={
              <Link className="button secondary" href="/creator">
                查看创作者
                <ArrowRight size={14} />
              </Link>
            }
          />
        </Card>
      )}
    </>
  );
}

export function ArticlePage({ store, action, busy, path }: PageProps) {
  const content = store.contents.find((c) => c.id === path.split("/")[3]);
  const [confirmed, setConfirmed] = useState(false);
  if (!content)
    return (
      <EmptyState
        title="未找到这份内容"
        description="请从内容库中选择作品。"
        action={
          <Link className="button secondary" href="/campaigns">
            返回内容库
          </Link>
        }
      />
    );
  return (
    <>
      <PageHeader
        title="把每一句话，调整到恰到好处"
        description="保存修改会取消之前的审核，旧版发布包也会失效。"
      >
        <StatusBadge status={content.status} />
        <Link className="button secondary" href="/campaigns">
          返回内容库
        </Link>
      </PageHeader>
      <div className="editor-columns">
        <Card className="article-preview">
          <span className="eyebrow">COVER PREVIEW</span>
          <div className="article-cover">
            <span>产品创作笔记</span>
            <h2>{content.title}</h2>
            <div />
            <p>{store.brands[0]?.name}</p>
            <small>AI 辅助制作 · 发布前请复核标识</small>
          </div>
          <p className="muted">版式预览 · 实际 PNG 随发布包生成</p>
        </Card>
        <Card>
          <form
            className="form-stack"
            key={content.id + "-" + content.revision}
            onSubmit={(e) => {
              e.preventDefault();
              const f = new FormData(e.currentTarget);
              action(
                () =>
                  api(`/content/packages/${content.id}`, {
                    method: "PATCH",
                    body: JSON.stringify({
                      title: f.get("title"),
                      body: f.get("body"),
                    }),
                  }),
                "内容已保存，请重新审核",
              );
            }}
          >
            <div className="row between">
              <Badge>{platformName[content.platform]}</Badge>
              <span className="muted">
                {content.generation_source === "template"
                  ? "本地规则草稿"
                  : "AI 生成草稿"}{" "}
                · V{content.revision}
              </span>
            </div>
            <Field label="标题">
              <input
                name="title"
                defaultValue={content.title}
                maxLength={180}
                required
                disabled={content.status === "user_reported_published"}
              />
            </Field>
            <Field label="正文">
              <textarea
                name="body"
                defaultValue={content.body}
                rows={11}
                maxLength={12000}
                required
                disabled={content.status === "user_reported_published"}
              />
            </Field>
            <Button
              variant="secondary"
              type="submit"
              disabled={busy || content.status === "user_reported_published"}
            >
              <Check size={15} />
              保存修改
            </Button>
          </form>
          <div className="divider" />
          <h3>内容预审与人工复核</h3>
          <div className="review-list">
            {content.compliance.issues?.map((issue, i) => (
              <p
                key={i}
                className={issue.level === "blocked" ? "error-text" : "muted"}
              >
                <ShieldCheck size={15} />
                {issue.message}
              </p>
            ))}
          </div>
          <label className="checkline">
            <input
              type="checkbox"
              checked={confirmed}
              onChange={(e) => setConfirmed(e.target.checked)}
            />
            我已复核产品事实、素材授权与 AI 标识
          </label>
          <div className="form-actions">
            <Button
              disabled={
                busy || !confirmed || content.compliance.status === "blocked"
              }
              onClick={() =>
                action(
                  () =>
                    api(
                      `/content/packages/${content.id}/approve`,
                      post({ confirmed: true }),
                    ),
                  "已保存人工审核结果",
                )
              }
            >
              确认审核
            </Button>
            <Button
              variant="secondary"
              disabled={busy || content.approved_revision !== content.revision}
              onClick={() =>
                action(
                  () =>
                    api(
                      "/manual-publication/packages",
                      post({ content_id: content.id }),
                    ),
                  "发布资料包已实际生成，可到人工发布中心下载",
                )
              }
            >
              <ArrowDownToLine size={15} />
              准备发布包
            </Button>
            <Link className="text-link" href="/publish">
              前往发布中心
              <ArrowRight size={14} />
            </Link>
          </div>
        </Card>
      </div>
    </>
  );
}
