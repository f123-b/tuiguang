"use client";

import { Badge, Button, Card, EmptyState, StatusBadge } from "@xuliu/ui";
import {
  ArrowLeft,
  ArrowRight,
  CalendarDays,
  CheckCheck,
  LockKeyhole,
  RefreshCw,
  Settings2,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { api, post, type EditorialEntry } from "../../lib/api";
import { Field, money, PageHeader, type PageProps } from "../page-shared";

const angles = [
  "功能速览",
  "开始使用",
  "使用前检查",
  "操作笔记",
  "场景说明",
  "常见问题",
  "一周回顾",
  "功能清单",
  "资料准备",
  "版本核对",
  "入门指引",
  "真实体验记录",
  "工作流整理",
  "下周计划",
];

export function CalendarPage({ store, action, busy }: PageProps) {
  const creator = store.creators[0];
  const [days, setDays] = useState<EditorialEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<string[]>([]);
  const [confirmed, setConfirmed] = useState(false);
  const runStates = store.runs.map((r) => `${r.id}:${r.status}`).join(",");
  useEffect(() => {
    let cancelled = false;
    if (!creator) {
      setLoading(false);
      return;
    }
    api<EditorialEntry[]>(`/creators/${creator.id}/calendar`)
      .then((result) => {
        if (!cancelled) {
          setDays(result);
          setError("");
          setLoading(false);
        }
      })
      .catch((e) => {
        if (!cancelled) {
          setError(e.message);
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [creator?.id, runStates]);
  const eligible = days.filter(
    (d) => d.status === "approved" && !d.run_id && !d.facts_stale,
  );
  const chosen = eligible.filter((d) => selected.includes(d.id));
  return (
    <>
      <PageHeader
        eyebrow="EDITORIAL CALENDAR"
        title="把未来的创作，安排妥当"
        description="未来 14 天的真实制作计划。修改后重新确认，已确认的选题将按时准备，发布由你完成。"
      >
        <Link className="button secondary" href="/creator/edit">
          <Settings2 size={15} />
          调整创作频率
        </Link>
      </PageHeader>
      {error && (
        <div role="alert" className="alert danger">
          {error}
        </div>
      )}
      {!creator ? (
        <EmptyState
          title="先设定创作节奏"
          description="创建创作者后，在这里管理选题和制作日程。"
          action={
            <Link className="button primary" href="/creator">
              创建创作者
            </Link>
          }
        />
      ) : (
        <>
          <div className="info-strip">
            <CalendarDays size={18} />
            <span>
              {creator.timezone} · {creator.hour}:00 开始准备
            </span>
            <Badge tone={creator.status === "active" ? "success" : "warning"}>
              {creator.status === "active" ? "持续创作已开启" : "创作者已暂停"}
            </Badge>
          </div>
          <div className="editorial-toolbar">
            <p>
              规则选题依据已核实事实轮换，未进行热度或语义去重分析。锁定的选题会保留。
            </p>
            <Button
              variant="secondary"
              disabled={busy}
              onClick={() =>
                action(async () => {
                  const result = await api<EditorialEntry[]>(
                    `/creators/${creator.id}/plan`,
                    post(),
                  );
                  setDays(result);
                  setError("");
                  setLoading(false);
                }, "计划已补齐，已有选题已保留")
              }
            >
              <RefreshCw size={15} />
              补齐 14 天计划
            </Button>
          </div>
          {loading ? (
            <p role="status">正在读取选题计划…</p>
          ) : !days.length ? (
            <EmptyState
              title="尚未建立选题计划"
              description="点击上方按钮补齐未来 14 天的计划，计划本身不调用模型。"
            />
          ) : (
            <div className="editorial-grid">
              {days.map((day, index) => {
                const canSelect = eligible.some((d) => d.id === day.id);
                return (
                  <Card
                    key={day.id}
                    className={`editorial-day ${["rest", "skipped", "expired"].includes(day.status) ? "editorial-off" : ""}`}
                  >
                    <div className="editorial-date">
                      <span>
                        <strong>{day.date.slice(8)}</strong>{" "}
                        {new Date(day.date + "T12:00:00").toLocaleDateString(
                          "zh-CN",
                          { weekday: "short" },
                        )}
                      </span>
                      {index === 0 && <Badge tone="blue">今天</Badge>}
                    </div>
                    <small>{day.date.slice(0, 7)}</small>
                    <StatusBadge status={day.status} />
                    <Link
                      className="editorial-title"
                      href={`/topics/${day.id}`}
                    >
                      {day.title}
                    </Link>
                    <div className="editorial-meta">
                      <span>
                        {day.angle} · v{day.revision}
                      </span>
                      {day.locked && (
                        <span>
                          <LockKeyhole size={12} />
                          已锁定
                        </span>
                      )}
                    </div>
                    {day.facts_stale && (
                      <p className="error-text">事实版本变化，需要复核</p>
                    )}
                    <div className="editorial-day-actions">
                      {canSelect && (
                        <label className="checkline">
                          <input
                            type="checkbox"
                            aria-label={`提前准备：${day.title}`}
                            checked={selected.includes(day.id)}
                            disabled={
                              busy ||
                              (chosen.length >= 7 && !selected.includes(day.id))
                            }
                            onChange={(e) => {
                              setSelected((prev) =>
                                e.target.checked
                                  ? [...prev, day.id]
                                  : prev.filter((id) => id !== day.id),
                              );
                              setConfirmed(false);
                            }}
                          />
                          提前准备
                        </label>
                      )}
                      <Link className="text-link" href={`/topics/${day.id}`}>
                        查看选题
                        <ArrowRight size={13} />
                      </Link>
                    </div>
                  </Card>
                );
              })}
            </div>
          )}
          {chosen.length > 0 && (
            <Card className="editorial-batch">
              <h2>提前准备 {chosen.length} 篇内容</h2>
              <p>
                {chosen.map((d) => d.date).join("、")}{" "}
                的选题会立即排入后台。每次最多 7 篇，不会自动发布。
              </p>
              <p>
                模型预算按实际执行日计算：每日{" "}
                {money(creator.daily_budget_cents)}，每月{" "}
                {money(creator.monthly_budget_cents)}。
                {store.dashboard.generation_mode === "template"
                  ? "当前使用本地规则草稿，无模型费用。"
                  : "真实模型执行前会逐篇检查授权和预算，达到上限会暂停。"}
              </p>
              <label className="checkline">
                <input
                  type="checkbox"
                  checked={confirmed}
                  onChange={(e) => setConfirmed(e.target.checked)}
                />
                我已核对所选选题，同意现在开始准备
              </label>
              <Button
                disabled={busy || !confirmed || creator.status !== "active"}
                onClick={() =>
                  action(async () => {
                    await api(
                      `/creators/${creator.id}/prepare`,
                      post({
                        entry_ids: chosen.map((d) => d.id),
                        expected_revisions: Object.fromEntries(
                          chosen.map((d) => [d.id, d.revision]),
                        ),
                        confirmed: true,
                      }),
                    );
                    setSelected([]);
                    setConfirmed(false);
                    setDays(
                      await api<EditorialEntry[]>(
                        `/creators/${creator.id}/calendar`,
                      ),
                    );
                  }, "所选选题已排入后台，可在创作活动查看进度")
                }
              >
                <CheckCheck size={16} />
                确认并开始准备
              </Button>
              {creator.status !== "active" && (
                <Link className="text-link" href="/creator">
                  请先恢复创作者
                </Link>
              )}
            </Card>
          )}
        </>
      )}
    </>
  );
}

export function TopicPage({ store, path, action, busy }: PageProps) {
  const id = path.split("/").at(-1);
  const creator = store.creators[0];
  const [entry, setEntry] = useState<EditorialEntry | null>(null);
  const [days, setDays] = useState<EditorialEntry[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [approval, setApproval] = useState(false);
  const [prepareConsent, setPrepareConsent] = useState(false);
  const [target, setTarget] = useState("");
  const [dirty, setDirty] = useState(false);
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setEntry(null);
    setError("");
    if (!creator) {
      setLoading(false);
      return;
    }
    Promise.all([
      api<EditorialEntry>(`/topics/${id}`),
      api<EditorialEntry[]>(`/creators/${creator.id}/calendar`),
    ])
      .then(([topic, calendar]) => {
        if (!cancelled) {
          setEntry(topic);
          setDays(calendar);
          setLoading(false);
          setTarget(topic.date);
          setDirty(false);
          setApproval(false);
          setPrepareConsent(false);
        }
      })
      .catch((e) => {
        if (!cancelled) {
          setError(e.message);
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [id, creator?.id]);
  const update = async (operation: string, data: unknown, method = "POST") => {
    const result = await api<EditorialEntry>(`/topics/${id}${operation}`, {
      method,
      body: JSON.stringify(data),
    });
    setEntry(result);
    setDirty(false);
    setApproval(false);
    setPrepareConsent(false);
    if (creator)
      setDays(await api<EditorialEntry[]>(`/creators/${creator.id}/calendar`));
  };
  if (loading) return <p role="status">正在读取选题…</p>;
  if (!entry || !creator)
    return (
      <EmptyState
        title="无法读取这个选题"
        description={error || "请先创建创作者，或回到日历选择有效选题。"}
        action={
          <Link className="button secondary" href="/calendar">
            返回日历
          </Link>
        }
      />
    );
  const editable =
    !entry.run_id &&
    [
      "approved",
      "planned",
      "rest",
      "skipped",
      "needs_review",
      "expired",
    ].includes(entry.status);
  const payload = { expected_revision: entry.revision };
  return (
    <>
      <Link className="text-link" href="/calendar">
        <ArrowLeft size={15} />
        返回选题日历
      </Link>
      <PageHeader
        eyebrow="EDITORIAL TOPIC"
        title={entry.title}
        description={`${entry.date} · ${creator.timezone} ${creator.hour}:00 制作 · 选题版本 ${entry.revision}`}
      >
        <StatusBadge status={entry.status} />
        {entry.locked && <Badge>已锁定</Badge>}
      </PageHeader>
      {entry.facts_stale && (
        <div role="alert" className="alert warning">
          {entry.run_id
            ? "品牌事实已变化，原执行依据保持冻结。请在日历中选择尚未执行的日期，依据最新事实安排新选题。"
            : "品牌事实已变化。重新选择当前事实并保存后，才能确认和执行。"}
        </div>
      )}
      {entry.run_id && (
        <div className="info-strip">
          <CheckCheck size={18} />
          <span>执行依据已冻结，不能改写这个选题。</span>
          <Link className="text-link" href="/creator/activity">
            查看创作活动
          </Link>
        </div>
      )}
      <div className="editorial-detail-grid">
        <Card>
          <h2>选题与依据</h2>
          <form
            key={`${entry.id}:${entry.revision}`}
            className="form-stack"
            onChange={() => {
              setDirty(true);
              setApproval(false);
              setPrepareConsent(false);
            }}
            onSubmit={(e) => {
              e.preventDefault();
              const form = new FormData(e.currentTarget);
              action(
                () =>
                  update(
                    "",
                    {
                      ...payload,
                      title: form.get("title"),
                      angle: form.get("angle"),
                      fact_refs: form.getAll("fact"),
                      locked: form.get("locked") === "on",
                    },
                    "PATCH",
                  ),
                "选题已保存，请重新确认后再执行",
              );
            }}
          >
            <Field label="内容标题">
              <input
                name="title"
                required
                maxLength={180}
                defaultValue={entry.title}
                disabled={!editable || busy}
              />
            </Field>
            <Field label="创作角度">
              <select
                name="angle"
                defaultValue={entry.angle}
                disabled={!editable || busy}
              >
                {angles.map((angle) => (
                  <option key={angle}>{angle}</option>
                ))}
              </select>
            </Field>
            <fieldset className="editorial-facts" disabled={!editable || busy}>
              <legend>引用已核实事实</legend>
              {entry.available_facts.length ? (
                entry.available_facts.map((fact) => (
                  <label className="editorial-fact" key={fact.id}>
                    <input
                      type="checkbox"
                      name="fact"
                      value={fact.id}
                      defaultChecked={entry.fact_refs.includes(fact.id)}
                    />
                    <span>
                      <strong>{fact.claim}</strong>
                      <small>来源：{fact.source}</small>
                    </span>
                  </label>
                ))
              ) : (
                <p>没有已核实的事实，请先在品牌资料补充来源。</p>
              )}
            </fieldset>
            <label className="checkline">
              <input
                type="checkbox"
                name="locked"
                defaultChecked={entry.locked}
                disabled={!editable || busy}
              />
              锁定选题，补齐计划时保留当前安排
            </label>
            <p className="muted">
              保存修改后会回到“待确认选题”。已确认规则选题按创作者设置执行，手动改题需要你重新确认。
            </p>
            {editable && (
              <Button type="submit" disabled={busy}>
                保存选题
              </Button>
            )}
          </form>
        </Card>
        <div className="form-stack">
          {dirty && (
            <div role="status" className="alert warning">
              有未保存的修改。请先保存，再确认、改期或提前准备。
            </div>
          )}
          <Card>
            <h2>确认制作安排</h2>
            <p>{entry.rationale}</p>
            <p className="muted">
              来源：{entry.source === "user" ? "用户编辑" : "本地规则计划"} ·
              品牌事实版本 {entry.brand_revision}
            </p>
            {editable && (
              <>
                <label className="checkline">
                  <input
                    type="checkbox"
                    checked={approval}
                    onChange={(e) => setApproval(e.target.checked)}
                  />
                  我已核对已保存的选题与事实来源
                </label>
                <Button
                  disabled={busy || dirty || !approval || entry.facts_stale}
                  onClick={() =>
                    action(
                      () => update("/approve", { ...payload, confirmed: true }),
                      "选题已确认，将依照安排准备",
                    )
                  }
                >
                  确认这个选题
                </Button>
                <div className="editorial-divider" />
                <Field
                  label="调整制作日期"
                  hint="目标日期已有选题时，两条选题交换日期，交换后都需要重新确认。"
                >
                  <select
                    value={target}
                    onChange={(e) => setTarget(e.target.value)}
                    disabled={busy}
                  >
                    {days.map((day) => (
                      <option value={day.date} key={day.id}>
                        {day.date}
                        {day.run_id ? " · 已创建任务" : ""}
                      </option>
                    ))}
                  </select>
                </Field>
                <div className="row">
                  <Button
                    variant="secondary"
                    disabled={
                      busy ||
                      dirty ||
                      target === entry.date ||
                      !!days.find((d) => d.date === target)?.run_id
                    }
                    onClick={() =>
                      action(
                        () =>
                          update("/reschedule", {
                            ...payload,
                            date: target,
                            swap_revision: days.find((d) => d.date === target)
                              ?.revision,
                          }),
                        "选题日期已交换，请重新确认两条选题",
                      )
                    }
                  >
                    交换日期
                  </Button>
                  <Button
                    variant="quiet"
                    disabled={busy || dirty || entry.status === "skipped"}
                    onClick={() =>
                      action(
                        () => update("/skip", payload),
                        "已跳过这一天的创作",
                      )
                    }
                  >
                    跳过这一天
                  </Button>
                </div>
              </>
            )}
          </Card>
          {entry.status === "approved" && !entry.run_id && (
            <Card>
              <h2>现在提前准备</h2>
              <p>
                立即执行本选题，费用计入实际执行日预算，生成后仍需人工审核。
                {store.dashboard.generation_mode === "template"
                  ? "当前是本地规则草稿。"
                  : "当前使用真实模型。"}
              </p>
              <label className="checkline">
                <input
                  type="checkbox"
                  checked={prepareConsent}
                  onChange={(e) => setPrepareConsent(e.target.checked)}
                />
                同意现在开始准备
              </label>
              <Button
                disabled={
                  busy ||
                  dirty ||
                  !prepareConsent ||
                  entry.facts_stale ||
                  creator.status !== "active"
                }
                onClick={() =>
                  action(async () => {
                    await api(
                      `/creators/${creator.id}/prepare`,
                      post({
                        entry_ids: [entry.id],
                        expected_revisions: { [entry.id]: entry.revision },
                        confirmed: true,
                      }),
                    );
                    setEntry(await api<EditorialEntry>(`/topics/${id}`));
                    setPrepareConsent(false);
                  }, "选题已排入后台")
                }
              >
                准备这篇内容
              </Button>
              {creator.status !== "active" && (
                <p>创作者已暂停，请先在创作者页面恢复。</p>
              )}
            </Card>
          )}
        </div>
      </div>
    </>
  );
}
