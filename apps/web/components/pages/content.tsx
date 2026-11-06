"use client";
import { Badge, Button, Card, EmptyState, StatusBadge } from "@xuliu/ui";
import {
  ArrowDownToLine,
  ArrowRight,
  Check,
  FileText,
  Layers,
  Plus,
  ShieldCheck,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { api, post, type Content } from "../../lib/api";

import {
  Field,
  PageHeader,
  platformName,
  type PageProps,
} from "../page-shared";
import { ContentEvidence } from "./evidence";
export function ContentCard({ content }: { content: Content }) {
  return (
    <Link href={`/studio/article/${content.id}`} className="content-card">
      <div className={`content-cover variant-${content.id.charCodeAt(0) % 3}`}>
        {content.graphics_render?.content_revision === content.revision ? (
          <img
            className="content-rendered-cover"
            src={`/api/v1/content/packages/${content.id}/graphics/pages/0/preview?revision=${content.revision}`}
            alt={`${content.title} · 实际图文封面`}
          />
        ) : (
          <>
            <span>PRODUCT NOTES</span>
            <h3>{content.title}</h3>
            <span className="cover-footer">
              <FileText size={14} />
              真实产品 · 内容笔记
            </span>
          </>
        )}
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
  const [dirty, setDirty] = useState(false);
  const [variantDirty, setVariantDirty] = useState(false);
  useEffect(() => {
    setConfirmed(false);
    setDirty(false);
    setVariantDirty(false);
  }, [content?.id, content?.revision]);
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
      <ContentEvidence
        content={content}
        onDraftChange={setVariantDirty}
        action={action}
        busy={busy}
        locked={dirty || content.status === "user_reported_published"}
      />
      <Card>
        <details>
          <summary>视频成片与发布包</summary>
          <p className="muted">
            绑定当前已渲染的视频版本；修改视频后须重新绑定并审核。未保存的文案不会被打包。
          </p>
          {content.video_attachment && (
            <p>
              已绑定视频 V{content.video_attachment.revision} ·{" "}
              <Link href={`/studio/video/${content.video_attachment.video_id}`}>
                查看视频工程
              </Link>
            </p>
          )}
          <form
            className="form-stack"
            key={`video-${content.revision}`}
            onSubmit={(e) => {
              e.preventDefault();
              const f = new FormData(e.currentTarget);
              action(
                () =>
                  api(
                    `/content/packages/${content.id}/video`,
                    post({
                      expected_revision: content.revision,
                      confirmed: true,
                      video_id: f.get("video") || null,
                    }),
                  ),
                "视频绑定已保存，请重新审核内容",
              );
            }}
          >
            <select
              aria-label="绑定成片"
              name="video"
              defaultValue={content.video_attachment?.video_id || ""}
              disabled={
                dirty ||
                variantDirty ||
                content.status === "user_reported_published"
              }
            >
              <option value="">不绑定视频</option>
              {store.videos
                .filter((v) => v.rendered_revision === v.revision)
                .map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.name} · V{v.revision}
                  </option>
                ))}
            </select>
            <label className="checkline">
              <input type="checkbox" required />
              我已观看成片并核对产品画面、旁白、字幕和音频使用权
            </label>
            <Button
              type="submit"
              variant="secondary"
              disabled={
                busy ||
                dirty ||
                variantDirty ||
                content.status === "user_reported_published"
              }
            >
              保存视频绑定
            </Button>
          </form>
        </details>
      </Card>
      <div className="editor-columns">
        <Card className="article-preview">
          <span className="eyebrow">COVER PREVIEW</span>
          {content.graphics_render?.content_revision === content.revision ? (
            <img
              className="article-rendered-cover"
              src={`/api/v1/content/packages/${content.id}/graphics/pages/0/preview?revision=${content.revision}`}
              alt="已保存的真实图文封面"
            />
          ) : (
            <div className="graphic-preview-empty">
              <Layers size={40} />
              <h3>制作你的封面与图文卡</h3>
              <p>选择版式、配色和真实素材，生成可以审核与下载的图片。</p>
            </div>
          )}
          <Link
            className="button secondary"
            href={`/studio/article/${content.id}/graphics`}
          >
            编辑封面与图文卡
            <ArrowRight size={15} />
          </Link>
          <p className="muted">
            {content.graphics
              ? `${content.graphics.pages.length} 页图文 · 预览与导出使用同一文件`
              : "尚未建立图文工程，旧流程仍会随发布包生成默认封面。"}
          </p>
        </Card>
        <Card>
          <form
            className="form-stack"
            onChange={() => {
              setDirty(true);
              setConfirmed(false);
            }}
            key={content.id + "-" + content.revision}
            onSubmit={(e) => {
              e.preventDefault();
              const f = new FormData(e.currentTarget);
              action(
                () =>
                  api(`/content/packages/${content.id}`, {
                    method: "PATCH",
                    body: JSON.stringify({
                      expected_revision: content.revision,
                      title: f.get("title"),
                      body: f.get("body"),
                      reason_tag: f.get("reason_tag"),
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
            <Field label="修改原因（可选）">
              <select name="reason_tag" defaultValue="edit">
                <option value="edit">一般修改</option>
                <option value="too_advertising">太像广告</option>
                <option value="inaccurate">不准确</option>
                <option value="more_real">需要更真实</option>
                <option value="shorter">希望更短</option>
                <option value="other">其他</option>
              </select>
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
          {(dirty || variantDirty) && (
            <div className="alert warning">
              有未保存的文案修改，请先保存，再审核或准备发布包。
            </div>
          )}
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
                busy ||
                dirty ||
                variantDirty ||
                !confirmed ||
                content.compliance.status === "blocked" ||
                content.status === "user_reported_published"
              }
              onClick={() =>
                action(
                  () =>
                    api(
                      `/content/packages/${content.id}/approve`,
                      post({
                        confirmed: true,
                        expected_revision: content.revision,
                      }),
                    ),
                  "已保存人工审核结果",
                )
              }
            >
              确认审核
            </Button>
            <Button
              variant="secondary"
              disabled={
                busy ||
                dirty ||
                variantDirty ||
                content.approved_revision !== content.revision
              }
              onClick={() =>
                action(
                  () =>
                    api(
                      "/manual-publication/packages",
                      post({
                        content_id: content.id,
                        expected_revision: content.revision,
                      }),
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
