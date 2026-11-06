"use client";

import { Badge, Button, Card, EmptyState, StatusBadge } from "@xuliu/ui";
import {
  ArrowDown,
  ArrowDownToLine,
  ArrowLeft,
  ArrowRight,
  ArrowUp,
  CheckCheck,
  ImagePlus,
  Layers,
  Plus,
  RefreshCw,
  Save,
  Trash2,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import {
  api,
  post,
  type Content,
  type GraphicDocument,
  type GraphicPage,
} from "../../lib/api";
import { Field, PageHeader, type PageProps } from "../page-shared";

const templates = {
  editorial: "产品笔记",
  checklist: "事实清单",
  screenshot: "真实截图",
};
const sizes = {
  portrait: "竖版 · 1080 × 1440",
  square: "方形 · 1080 × 1080",
  landscape: "横版 · 1920 × 1080",
};
const themes = { midnight: "午夜科技", paper: "纸感笔记", sage: "青绿色调" };
const previewUrl = (content: Content, index: number) =>
  `/api/v1/content/packages/${content.id}/graphics/pages/${index}/preview?revision=${content.revision}`;
const initialDocument = (content: Content): GraphicDocument =>
  content.graphics || {
    schema_version: "1.0",
    renderer_version: "graphic_cards@1",
    size: "portrait",
    theme: "midnight",
    pages: [
      {
        page_id: "cover",
        template: "editorial",
        heading: content.title,
        text: "",
        asset_id: null,
      },
    ],
  };

export function GraphicsLibrary({ store }: PageProps) {
  const [selected, setSelected] = useState(
    store.contents.find((c) => c.status !== "user_reported_published")?.id ||
      "",
  );
  return (
    <>
      <PageHeader
        eyebrow="GRAPHIC STUDIO"
        title="把真实的内容，排成好看的图文"
        description="从一张封面到六页图文，使用你的事实与授权图片，生成可以实际下载的 PNG / JPG。"
      />
      <div className="graphics-template-grid">
        {Object.entries(templates).map(([key, name]) => (
          <Card key={key}>
            <div className={`graphic-template-demo demo-${key}`}>
              <small>版式示意</small>
              <span>{name}</span>
              {key === "editorial" ? (
                <h2>
                  一份产品笔记
                  <br />
                  讲清一个价值
                </h2>
              ) : key === "checklist" ? (
                <div>
                  01 已核实事实
                  <br />
                  02 有依据的说明
                  <br />
                  03 清楚的来源
                </div>
              ) : (
                <div className="graphic-image-placeholder">
                  <ImagePlus size={32} />
                  <span>放入你的授权截图</span>
                </div>
              )}
            </div>
            <h2>{name}</h2>
            <p>
              {key === "editorial"
                ? "标题、说明与品牌页脚，自动调整文字大小。"
                : key === "checklist"
                  ? "直接引用当前内容的已核实事实，来源随发布包保存。"
                  : "完整适配真实图片，保留比例，不裁切或虚构产品界面。"}
            </p>
          </Card>
        ))}
      </div>
      {store.contents.length ? (
        <Card className="graphics-entry">
          <div>
            <h2>从一份内容开始</h2>
            <p>编辑器内选择版式、尺寸、配色与页序。修改会取消之前的审核。</p>
          </div>
          <Field label="选择内容">
            <select
              value={selected}
              onChange={(e) => setSelected(e.target.value)}
            >
              <option value="">请选择内容</option>
              {store.contents.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.title}
                  {c.status === "user_reported_published"
                    ? " · 已登记，只读"
                    : ""}
                </option>
              ))}
            </select>
          </Field>
          {selected && (
            <Link
              className="button primary"
              href={`/studio/article/${selected}/graphics`}
            >
              打开图文编辑器
              <ArrowRight size={15} />
            </Link>
          )}
        </Card>
      ) : (
        <EmptyState
          title="先准备一份内容"
          description="创作者准备的草稿会出现在这里，之后可以制作封面和图文卡。"
          action={
            <Link className="button primary" href="/campaigns">
              前往内容工作室
            </Link>
          }
        />
      )}
    </>
  );
}

export function GraphicsPage(props: PageProps) {
  const content = props.store.contents.find(
    (c) => c.id === props.path.split("/")[3],
  );
  return content ? (
    <GraphicsEditor key={content.id} {...props} content={content} />
  ) : (
    <EmptyState
      title="未找到这份内容"
      description="从内容工作室选择已有草稿，再开始制作图文。"
      action={
        <Link className="button secondary" href="/campaigns">
          返回内容库
        </Link>
      }
    />
  );
}

function GraphicsEditor({
  store,
  action,
  busy,
  content,
}: PageProps & { content: Content }) {
  const [document, setDocument] = useState<GraphicDocument>(() =>
    initialDocument(content),
  );
  const [baseRevision, setBaseRevision] = useState(content.revision);
  const [selected, setSelected] = useState(0);
  const [dirty, setDirty] = useState(!content.graphics);
  const [confirmed, setConfirmed] = useState(false);
  const [viewed, setViewed] = useState<string[]>([]);
  const [imageError, setImageError] = useState(false);
  const [previewNonce, setPreviewNonce] = useState(0);
  const creator = store.creators.find((c) => c.id === content.creator_id);
  const brand = store.brands.find((b) => b.id === creator?.brand_id);
  const assets = store.assets.filter(
    (a) => a.brand_id === brand?.id && a.kind === "image" && a.verified,
  );
  const facts =
    brand?.facts.filter((f) => content.fact_refs.includes(f.id)) || [];
  const readonly = content.status === "user_reported_published";
  const conflict = content.revision !== baseRevision;
  const receipt =
    content.graphics_render?.content_revision === content.revision
      ? content.graphics_render
      : null;
  const page = document.pages[selected] || document.pages[0];
  const canReview =
    !!receipt &&
    !dirty &&
    !conflict &&
    viewed.length === document.pages.length &&
    !imageError;
  const approved = content.approved_revision === content.revision;
  useEffect(() => {
    if (!dirty && content.revision !== baseRevision) {
      setDocument(initialDocument(content));
      setBaseRevision(content.revision);
      setConfirmed(false);
    }
  }, [content, baseRevision, dirty]);
  useEffect(() => {
    setViewed([]);
    setConfirmed(false);
    setImageError(false);
  }, [content.revision, receipt?.cache_key, previewNonce]);
  function change(next: GraphicDocument) {
    setDocument(next);
    setDirty(true);
    setConfirmed(false);
  }
  function patchPage(patch: Partial<GraphicPage>) {
    change({
      ...document,
      pages: document.pages.map((p, i) =>
        i === selected ? { ...p, ...patch } : p,
      ),
    });
  }
  function movePage(direction: number) {
    const pages = [...document.pages];
    const target = selected + direction;
    [pages[selected], pages[target]] = [pages[target], pages[selected]];
    change({ ...document, pages });
    setSelected(target);
  }
  function reload() {
    setDocument(initialDocument(content));
    setBaseRevision(content.revision);
    setDirty(!content.graphics);
    setSelected(0);
    setConfirmed(false);
  }
  return (
    <>
      <Link className="text-link" href={`/studio/article/${content.id}`}>
        <ArrowLeft size={15} />
        返回文案与事实审核
      </Link>
      <PageHeader
        eyebrow="GRAPHIC EDITOR"
        title="让每一页，都讲清楚一点"
        description={`${content.title} · 内容版本 ${content.revision} · 图文修改后需要重新审核。`}
      >
        <StatusBadge status={content.status} />
        <Link className="button secondary" href="/studio/covers">
          查看版式
        </Link>
      </PageHeader>
      {conflict && (
        <div role="alert" className="alert warning">
          内容已在其他操作中更新。当前编辑保留，请核对后重新载入已保存版本。
          <Button variant="quiet" onClick={reload}>
            重新载入
          </Button>
        </div>
      )}
      {dirty && (
        <div role="status" className="info-strip">
          <Save size={16} />
          <span>
            当前有未保存的图文。先保存，再生成真实预览；审核与下载使用已保存版本。
          </span>
        </div>
      )}
      <div className="graphics-workbench">
        <Card className="graphics-pages">
          <div className="section-heading">
            <h2>图文页</h2>
            <Badge>{document.pages.length} / 6</Badge>
          </div>
          <div className="graphic-page-list">
            {document.pages.map((p, index) => (
              <button
                className={`graphic-page-select ${index === selected ? "selected" : ""}`}
                key={p.page_id}
                onClick={() => {
                  setSelected(index);
                  setImageError(false);
                }}
                aria-label={`查看第 ${index + 1} 页：${p.heading || content.title}`}
              >
                <span className="graphic-page-number">
                  {String(index + 1).padStart(2, "0")}
                </span>
                <span>
                  <strong>{p.heading || content.title}</strong>
                  <small>
                    {templates[p.template]}
                    {viewed.includes(p.page_id) ? " · 已查看预览" : ""}
                  </small>
                </span>
              </button>
            ))}
          </div>
          <Button
            variant="secondary"
            disabled={
              busy || readonly || document.pages.length >= 6 || conflict
            }
            onClick={() => {
              change({
                ...document,
                pages: [
                  ...document.pages,
                  {
                    page_id: crypto.randomUUID(),
                    template: "editorial",
                    heading: "",
                    text: "",
                    asset_id: null,
                  },
                ],
              });
              setSelected(document.pages.length);
            }}
          >
            <Plus size={15} />
            添加一页
          </Button>
          <div className="graphic-page-operations">
            <Button
              variant="quiet"
              aria-label="上移当前页"
              disabled={busy || readonly || selected === 0 || conflict}
              onClick={() => movePage(-1)}
            >
              <ArrowUp size={16} />
            </Button>
            <Button
              variant="quiet"
              aria-label="下移当前页"
              disabled={
                busy ||
                readonly ||
                selected === document.pages.length - 1 ||
                conflict
              }
              onClick={() => movePage(1)}
            >
              <ArrowDown size={16} />
            </Button>
            <Button
              variant="quiet"
              aria-label="删除当前页"
              disabled={
                busy || readonly || document.pages.length === 1 || conflict
              }
              onClick={() => {
                change({
                  ...document,
                  pages: document.pages.filter(
                    (p) => p.page_id !== page.page_id,
                  ),
                });
                setSelected(Math.max(0, selected - 1));
              }}
            >
              <Trash2 size={16} />
            </Button>
          </div>
          <p className="muted">
            第一张图作为封面，所有图文页随发布包一起导出。
          </p>
        </Card>
        <div className="graphics-canvas-column">
          <div className="graphic-preview-label">
            <span>第 {selected + 1} 页 · 已保存的真实图片</span>
            <Badge>{receipt && !dirty ? "真实 PNG 预览" : "等待生成"}</Badge>
          </div>
          <div className={`graphic-canvas canvas-${document.size}`}>
            {receipt && receipt.pages[selected] && !imageError ? (
              <img
                key={`${content.revision}:${selected}:${previewNonce}`}
                src={`${previewUrl(content, selected)}&preview=${previewNonce}`}
                alt={`第 ${selected + 1} 页真实图文预览：${receipt.pages[selected]?.heading || content.title}`}
                onLoad={() => {
                  const id = receipt.pages[selected]?.page_id;
                  if (id)
                    setViewed((prev) =>
                      prev.includes(id) ? prev : [...prev, id],
                    );
                }}
                onError={() => setImageError(true)}
              />
            ) : (
              <div className="graphic-preview-empty">
                <Layers size={42} />
                <h3>
                  {imageError ? "预览不可用" : "这里将展示实际导出的图片"}
                </h3>
                <p>
                  {imageError
                    ? "请核对素材与事实，再生成当前版本预览。"
                    : "保存右侧设置后，点击“生成真实预览”。"}
                </p>
              </div>
            )}
          </div>
          {dirty && receipt && (
            <p className="alert warning">
              此处显示的是上次保存的版本，尚未包含当前修改。
            </p>
          )}
          {receipt && (
            <div className="graphic-render-meta">
              <span>
                {receipt.pages[selected]?.width} ×{" "}
                {receipt.pages[selected]?.height} · PNG / JPG
              </span>
              <span>
                已查看 {viewed.length} / {document.pages.length} 页
              </span>
            </div>
          )}
        </div>
        <Card className="graphics-properties">
          <h2>当前页与全局样式</h2>
          <fieldset
            className="graphic-property-fields"
            disabled={busy || readonly || conflict}
          >
            <Field label="版式">
              <select
                value={page.template}
                onChange={(e) =>
                  patchPage({
                    template: e.target.value as GraphicPage["template"],
                    asset_id:
                      e.target.value === "screenshot"
                        ? assets[0]?.id || null
                        : null,
                  })
                }
              >
                {Object.entries(templates).map(([id, name]) => (
                  <option key={id} value={id}>
                    {name}
                  </option>
                ))}
              </select>
            </Field>
            <Field
              label="本页标题"
              hint="留空使用内容标题。文字过多时会提示调整，不静默裁断。"
            >
              <textarea
                rows={2}
                maxLength={180}
                value={page.heading}
                onChange={(e) => patchPage({ heading: e.target.value })}
              />
            </Field>
            <Field label="本页补充说明">
              <textarea
                rows={3}
                maxLength={600}
                value={page.text}
                onChange={(e) => patchPage({ text: e.target.value })}
              />
            </Field>
            {page.template === "screenshot" && (
              <Field label="已核实授权图片">
                <select
                  value={page.asset_id || ""}
                  onChange={(e) =>
                    patchPage({ asset_id: e.target.value || null })
                  }
                >
                  <option value="">请选择授权图片</option>
                  {assets.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.name}
                    </option>
                  ))}
                </select>
              </Field>
            )}
            {page.template === "screenshot" && (
              <div className="form-stack">
                <p className="muted">
                  {assets.length
                    ? "新上传的图片可刷新后选择。"
                    : "暂无可用图片，请先在素材库上传并核实来源、授权。"}
                </p>
                <div className="row">
                  <Link
                    className="text-link"
                    href="/studio/assets"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    打开素材库
                  </Link>
                  <Button
                    variant="quiet"
                    type="button"
                    disabled={busy}
                    onClick={() => action(async () => {}, "授权素材列表已刷新")}
                  >
                    刷新素材列表
                  </Button>
                </div>
              </div>
            )}
            {page.template === "checklist" && (
              <p className="muted">
                事实清单直接引用当前内容的事实，来源见下方和发布包。
              </p>
            )}
            <div className="graphic-property-divider" />
            <Field label="全部页面尺寸">
              <select
                value={document.size}
                onChange={(e) =>
                  change({
                    ...document,
                    size: e.target.value as GraphicDocument["size"],
                  })
                }
              >
                {Object.entries(sizes).map(([id, name]) => (
                  <option key={id} value={id}>
                    {name}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="全部页面配色">
              <select
                value={document.theme}
                onChange={(e) =>
                  change({
                    ...document,
                    theme: e.target.value as GraphicDocument["theme"],
                  })
                }
              >
                {Object.entries(themes).map(([id, name]) => (
                  <option key={id} value={id}>
                    {name}
                  </option>
                ))}
              </select>
            </Field>
          </fieldset>
          <div className="form-stack">
            <Button
              disabled={
                busy ||
                readonly ||
                !dirty ||
                conflict ||
                document.pages.some(
                  (p) => p.template === "screenshot" && !p.asset_id,
                )
              }
              onClick={() =>
                action(async () => {
                  await api(`/content/packages/${content.id}/graphics`, {
                    method: "PUT",
                    body: JSON.stringify({
                      expected_revision: baseRevision,
                      document,
                    }),
                  });
                  setDirty(false);
                  setConfirmed(false);
                }, "图文工程已保存，请生成真实预览并重新审核")
              }
            >
              <Save size={16} />
              保存图文工程
            </Button>
            <Button
              variant="secondary"
              disabled={busy || readonly || dirty || conflict || !content.graphics}
              onClick={() =>
                action(async () => {
                  await api(
                    `/content/packages/${content.id}/graphics/render`,
                    post({ expected_revision: content.revision }),
                  );
                  setPreviewNonce((n) => n + 1);
                }, "真实 PNG / JPG 已生成")
              }
            >
              <RefreshCw size={16} />
              生成真实预览
            </Button>
            {!dirty && content.graphics && (
              <a
                className="text-link"
                href={`/api/v1/content/packages/${content.id}/graphics/project`}
              >
                <ArrowDownToLine size={14} />
                下载已保存工程 JSON
              </a>
            )}
          </div>
        </Card>
      </div>
      <div className="graphic-review-grid">
        <Card>
          <h2>事实与素材依据</h2>
          <div className="graphic-evidence-list">
            {facts.map((f) => (
              <div key={f.id}>
                <strong>{f.claim}</strong>
                <small>
                  来源：{f.source} · {f.verified ? "用户已核实" : "尚未核实"}
                </small>
              </div>
            ))}
            {page.asset_id &&
              store.assets
                .filter((a) => a.id === page.asset_id)
                .map((a) => (
                  <div key={a.id}>
                    <strong>{a.name}</strong>
                    <small>来源：{a.source}</small>
                    <small>
                      授权：{a.license_note} ·{" "}
                      {a.verified ? "用户已核实" : "尚未核实"}
                    </small>
                  </div>
                ))}
          </div>
          <Link
            className="text-link"
            href="/studio/assets"
            target="_blank"
            rel="noopener noreferrer"
          >
            管理授权素材
            <ArrowRight size={14} />
          </Link>
        </Card>
        <Card className="graphic-review">
          <h2>查看每一页，再交给发布中心</h2>
          <p>
            内部预审提供风险提示。请复核文字、真实图片、素材授权、AI
            标识及平台当前要求。
          </p>
          <div className="review-list">
            {content.compliance.issues.map((issue, index) => (
              <p
                className={issue.level === "blocked" ? "error-text" : "muted"}
                key={index}
              >
                {issue.message}
              </p>
            ))}
          </div>
          {!readonly && (
            <>
              <label className="checkline">
                <input
                  type="checkbox"
                  checked={confirmed}
                  disabled={!canReview || busy}
                  onChange={(e) => setConfirmed(e.target.checked)}
                />
                我已查看全部真实预览并复核事实、授权和标识
              </label>
              <div className="form-actions">
                <Button
                  disabled={
                    busy ||
                    !canReview ||
                    !confirmed ||
                    content.compliance.status === "blocked"
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
                      "图文已人工审核",
                    )
                  }
                >
                  <CheckCheck size={16} />
                  确认审核
                </Button>
                <Button
                  variant="secondary"
                  disabled={busy || dirty || conflict || !approved || !receipt}
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
                      "完整图文发布包已生成",
                    )
                  }
                >
                  准备全部图文发布包
                </Button>
              </div>
            </>
          )}
          {approved && receipt && !dirty && (
            <div className="row">
              <a
                className="button secondary"
                href={`/api/v1/content/packages/${content.id}/graphics/pages/${selected}/download?revision=${content.revision}&format=png`}
              >
                下载本页 PNG
              </a>
              <a
                className="button secondary"
                href={`/api/v1/content/packages/${content.id}/graphics/pages/${selected}/download?revision=${content.revision}&format=jpg`}
              >
                下载本页 JPG
              </a>
            </div>
          )}
          <Link className="text-link" href="/publish">
            前往人工发布中心
            <ArrowRight size={14} />
          </Link>
        </Card>
      </div>
    </>
  );
}
