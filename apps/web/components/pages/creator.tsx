"use client";
import { Badge, Button, Card, EmptyState, StatusBadge } from "@xuliu/ui";
import {
  ArrowRight,
  ChevronRight,
  Pause,
  Play,
  Settings2,
  Sparkles,
  WandSparkles,
} from "lucide-react";
import Link from "next/link";
import { api, post } from "../../lib/api";

import {
  Field,
  money,
  PageHeader,
  platformName,
  type PageProps,
} from "../page-shared";
export function CreatorPage({ store, action, busy, path }: PageProps) {
  const creator = store.creators[0];
  const editing =
    !creator || path.endsWith("/edit") || path.startsWith("/onboarding");
  if (!store.brands.length)
    return (
      <EmptyState
        title="先让创作者认识你的产品"
        description="添加品牌信息和已核实的功能事实，然后安排创作。"
        action={
          <Link className="button primary" href="/brand">
            添加品牌资料
          </Link>
        }
      />
    );
  return (
    <>
      <PageHeader
        eyebrow="YOUR AI CREATOR"
        title={editing ? "为创作设定一个好节奏" : creator.name}
        description="设定人设、创作频率与预算，内容会持续准备，发布始终由你完成。"
      >
        {creator && <StatusBadge status={creator.status} />}
        {creator && !editing && (
          <Link className="button secondary" href="/creator/edit">
            <Settings2 size={15} />
            编辑设置
          </Link>
        )}
      </PageHeader>
      {editing ? (
        <Card>
          <form
            className="form-stack max-form"
            key={creator?.id || "new"}
            onSubmit={(e) => {
              e.preventDefault();
              const f = new FormData(e.currentTarget);
              const data = {
                brand_id: store.brands[0].id,
                name: f.get("name"),
                style: f.get("style"),
                platform: f.get("platform"),
                timezone: f.get("timezone"),
                hour: Number(f.get("hour")),
                weekdays: f.getAll("weekday").map(Number),
                daily_budget_cents: Math.round(Number(f.get("daily")) * 100),
                monthly_budget_cents: Math.round(
                  Number(f.get("monthly")) * 100,
                ),
                model_consent: f.get("consent") === "on",
                render_options: {
                  graphics: f.get("auto_graphics") === "on",
                  review_preview_before_final: f.get("preview_review") === "on",
                  video: f.get("auto_video") === "on",
                  duration_sec: Number(f.get("video_duration")),
                  video_mode: f.get("video_mode"),
                  size: f.get("render_size"),
                  asset_id: String(f.get("source_asset") || "") || null,
                },
              };
              action(
                () =>
                  api(creator ? `/creators/${creator.id}` : "/creators", {
                    method: creator ? "PATCH" : "POST",
                    body: JSON.stringify(data),
                  }),
                "创作者设置已保存",
              );
            }}
          >
            <Field label="创作者名称">
              <input
                name="name"
                required
                maxLength={120}
                defaultValue={creator?.name || `${store.brands[0].name}内容官`}
              />
            </Field>
            <Field label="内容风格">
              <textarea
                name="style"
                rows={2}
                maxLength={1000}
                defaultValue={
                  creator?.style ||
                  "理性、简洁、可信。关注真实功能，不夸张承诺。"
                }
              />
            </Field>
            <div className="form-grid">
              <Field label="平台内容规格">
                <select
                  name="platform"
                  defaultValue={creator?.platform || "xiaohongshu"}
                >
                  {Object.entries(platformName).map(([k, v]) => (
                    <option value={k} key={k}>
                      {v}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="运营时区">
                <input
                  name="timezone"
                  defaultValue={creator?.timezone || "Asia/Shanghai"}
                  required
                />
              </Field>
            </div>
            <div className="form-grid">
              <Field label="本地时间 · 每日开始制作">
                <input
                  name="hour"
                  type="number"
                  min={0}
                  max={23}
                  defaultValue={creator?.hour ?? 9}
                  required
                />
              </Field>
              <div className="field">
                <span>每周创作日</span>
                <div className="weekday-picker">
                  {["一", "二", "三", "四", "五", "六", "日"].map((d, i) => (
                    <label key={d}>
                      <input
                        name="weekday"
                        value={i}
                        type="checkbox"
                        defaultChecked={
                          !creator || creator.weekdays.includes(i)
                        }
                      />
                      <span>{d}</span>
                    </label>
                  ))}
                </div>
              </div>
            </div>
            <div className="form-grid">
              <Field label="每日模型预算（元）">
                <input
                  name="daily"
                  type="number"
                  min={0}
                  max={10000}
                  step="0.01"
                  required
                  defaultValue={(creator?.daily_budget_cents ?? 500) / 100}
                />
              </Field>
              <Field label="每月模型预算（元）">
                <input
                  name="monthly"
                  type="number"
                  min={0}
                  max={100000}
                  step="0.01"
                  required
                  defaultValue={(creator?.monthly_budget_cents ?? 10000) / 100}
                />
              </Field>
            </div>
            <details className="subtle-note">
              <summary>日任务同时制作图文与视频（可选）</summary>
              <p>
                原有设置默认关闭。开启后按已确认日程制作真实本地媒体，仍需你审核和手动发布；字幕和音频可在工作室补充。暂停会阻止新自动媒体任务，已开始的制作可能完成。
              </p>
              <label className="checkline">
                <input
                  name="auto_graphics"
                  type="checkbox"
                  defaultChecked={creator?.render_options?.graphics || false}
                />
                同时制作封面和事实图文卡
              </label>
              <label className="checkline">
                <input
                  name="auto_video"
                  type="checkbox"
                  defaultChecked={creator?.render_options?.video || false}
                />
                同时制作本地宣传视频（默认静音）
              </label>
              <label className="checkline">
                <input
                  name="preview_review"
                  type="checkbox"
                  defaultChecked={
                    creator?.render_options?.review_preview_before_final ?? true
                  }
                />
                先生成低清预览，经我确认后再生成高清
              </label>
              <div className="form-grid">
                <Field label="自动视频形式">
                  <select
                    name="video_mode"
                    defaultValue={creator?.render_options?.video_mode || "mg"}
                  >
                    <option value="mg">MG 动态图文</option>
                    <option value="mixed">MG 与授权素材混合</option>
                    <option value="screen_demo">真实截图 / 录屏讲解</option>
                    <option value="montage">授权视频素材混剪</option>
                  </select>
                </Field>
                <Field label="媒体尺寸">
                  <select
                    name="render_size"
                    defaultValue={creator?.render_options?.size || "wide"}
                  >
                    <option value="wide">16:9 · 横版</option>
                    <option value="portrait">9:16 · 竖版</option>
                    <option value="square">1:1 · 方形</option>
                  </select>
                </Field>
                <Field label="自动视频时长">
                  <select
                    name="video_duration"
                    defaultValue={creator?.render_options?.duration_sec || 30}
                  >
                    <option value={15}>15 秒</option>
                    <option value={20}>20 秒</option>
                    <option value={30}>30 秒</option>
                  </select>
                </Field>
                <Field label="真实素材（MG 可不选）">
                  <select
                    name="source_asset"
                    defaultValue={creator?.render_options?.asset_id || ""}
                  >
                    <option value="">不选择素材</option>
                    {store.assets
                      .filter((a) => a.verified && a.kind !== "audio")
                      .map((a) => (
                        <option key={a.id} value={a.id}>
                          {a.name}
                        </option>
                      ))}
                  </select>
                </Field>
              </div>
              <p className="muted">
                素材必须由你核实授权。缺少素材、源版本变化或制作失败会明确暂停该任务，不用其他引擎暗中替代，也不重做已计费草稿。
              </p>
            </details>
            <label className="checkline">
              <input
                name="consent"
                type="checkbox"
                defaultChecked={creator?.model_consent}
              />
              配置真实模型后，允许发送已核实品牌事实用于创作
            </label>
            <p className="muted">
              当前模式：
              {store.dashboard.generation_mode === "template"
                ? "本地规则草稿，不调用付费模型。预算不包含本地渲染的算力成本。"
                : "真实模型。每次调用先检查授权与预算。"}
            </p>
            <Button type="submit" disabled={busy}>
              <Sparkles size={16} />
              {creator ? "保存设置" : "保存并开启创作"}
            </Button>
          </form>
        </Card>
      ) : (
        <>
          <div className="creator-hero card">
            <div className="creator-avatar">
              <Sparkles size={40} />
            </div>
            <div>
              <Badge tone="success">持续内容伙伴</Badge>
              <h2>{creator.name}</h2>
              <p>{creator.style}</p>
              <div className="row">
                <Badge>{platformName[creator.platform]}</Badge>
                <span className="muted">
                  {creator.timezone} · {creator.hour}:00
                </span>
              </div>
            </div>
            <Button
              variant="secondary"
              disabled={busy}
              onClick={() =>
                action(
                  () =>
                    api(
                      `/creators/${creator.id}/${creator.status === "active" ? "pause" : "resume"}`,
                      post(),
                    ),
                  creator.status === "active" ? "创作者已暂停" : "创作者已恢复",
                )
              }
            >
              {creator.status === "active" ? (
                <Pause size={16} />
              ) : (
                <Play size={16} />
              )}
              {creator.status === "active" ? "暂停创作者" : "恢复创作者"}
            </Button>
          </div>
          <div className="three-grid">
            <Card>
              <span className="muted">每日模型预算</span>
              <h2 className="large-number">
                {money(creator.daily_budget_cents)}
              </h2>
              <p>达到上限后停止新的模型调用</p>
            </Card>
            <Card>
              <span className="muted">每月模型预算</span>
              <h2 className="large-number">
                {money(creator.monthly_budget_cents)}
              </h2>
              <p>费用预留与实际用量可追溯</p>
            </Card>
            <Card>
              <span className="muted">创作频率</span>
              <h2 className="large-number">
                每周 {creator.weekdays.length} 天
              </h2>
              <Link className="text-link" href="/calendar">
                查看未来 14 天<ArrowRight size={14} />
              </Link>
            </Card>
          </div>
          <Card>
            <div className="section-heading">
              <h2>下一次制作</h2>
              <Link href="/calendar">
                管理已确认选题
                <ChevronRight size={15} />
              </Link>
            </div>
            <p>
              {creator.next_run_at
                ? new Date(creator.next_run_at).toLocaleString("zh-CN", {
                    timeZone: creator.timezone,
                    hour12: false,
                  }) + `（${creator.timezone}）`
                : creator.status !== "active"
                  ? "创作者已暂停，恢复后按照已确认计划继续。"
                  : "暂无可执行选题，请在日历补齐并确认计划。"}
            </p>
          </Card>
          <Card>
            <div className="section-heading">
              <h2>开始一次真实创作</h2>
              <Link href="/creator/activity">
                查看运行日志
                <ChevronRight size={15} />
              </Link>
            </div>
            <p>
              按照日历中已确认的今日选题准备草稿，任务会持久保存，重启后可以继续处理。选题已跳过或待确认时，请先在日历调整。
            </p>
            <Button
              disabled={busy || creator.status !== "active"}
              onClick={() =>
                action(
                  () =>
                    api(`/creators/${creator.id}/run-today`, {
                      ...post(),
                      headers: { "Idempotency-Key": crypto.randomUUID() },
                    }),
                  "日任务已排入后台",
                )
              }
            >
              <WandSparkles size={16} />
              准备今日内容
            </Button>
          </Card>
        </>
      )}
    </>
  );
}

export function ActivityPage({ store, action, busy }: PageProps) {
  return (
    <>
      <PageHeader
        title="每一步创作，都有迹可循"
        description="这里展示真实的持久化任务状态与诊断编号。"
      />
      <Card>
        {store.runs.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>运营日期</th>
                  <th>任务状态</th>
                  <th>当前阶段</th>
                  <th>诊断编号 / 错误</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {store.runs.map((r) => (
                  <tr key={r.id}>
                    <td>{r.operational_date}</td>
                    <td>
                      <StatusBadge status={r.status} />
                    </td>
                    <td>
                      {r.stage === "awaiting_user_review"
                        ? "等待人工审阅"
                        : r.stage === "asset_rendering"
                          ? "制作图文与视频"
                          : r.stage === "media_failed"
                            ? "媒体制作需处理"
                            : r.stage}
                    </td>
                    <td>
                      <code>{r.trace_id.slice(0, 16)}</code>
                      {r.error_code && (
                        <p className="error-text">{r.error_code}</p>
                      )}
                    </td>
                    <td>
                      {r.status === "queued" && (
                        <Button
                          variant="secondary"
                          disabled={busy}
                          onClick={() =>
                            action(
                              () => api(`/creator-runs/${r.id}/skip`, post()),
                              "已跳过该日任务",
                            )
                          }
                        >
                          跳过
                        </Button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            title="还没有创作活动"
            description="开启创作者后，后台执行记录会保存在这里。"
          />
        )}
      </Card>
    </>
  );
}
