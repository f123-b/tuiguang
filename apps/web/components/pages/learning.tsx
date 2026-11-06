"use client";
import { Badge, Button, Card, EmptyState } from "@xuliu/ui";
import Link from "next/link";
import { useEffect, useState } from "react";
import { api, post } from "../../lib/api";
import {
  Field,
  PageHeader,
  platformName,
  type PageProps,
} from "../page-shared";

type Report = {
  id: string;
  version: number;
  period_start: string;
  period_end: string;
  report: {
    metric_sample_count: number;
    feedback_count: number;
    confidence: string;
    facts: string[];
    unknowns: string[];
    next_experiments: string[];
    groups: {
      platform: string;
      period_start: string;
      period_end: string;
      data_source: string;
      sample_count: number;
      metrics: Record<
        string,
        { mean: number | null; known_count: number; missing_count: number }
      >;
    }[];
  };
};
type Strategy = {
  id: string;
  report_id: string;
  parent_id: string | null;
  status: string;
  settings: {
    tone: string;
    concise: boolean;
    preferred_angles: string[];
    basis: unknown;
  };
};
type Feedback = {
  id: string;
  content_id: string;
  content_revision: number;
  reason_tag: string;
  note: string;
  active: boolean;
  created_at: string;
};
const labels: Record<string, string> = {
  proposed: "待审批",
  accepted: "已批准",
  rejected: "已拒绝",
  rolled_back: "已回滚",
  needs_review: "依据撤销，待重审",
  too_advertising: "太像广告",
  shorter: "希望更短",
  inaccurate: "不准确",
  too_fast: "节奏太快",
  more_real: "需要更真实",
  inconsistent: "视觉不统一",
  useful: "内容有用",
  other: "其他",
};

export function GrowthPage({ store, action, busy }: PageProps) {
  const creator = store.creators[0];
  const [reports, setReports] = useState<Report[]>([]),
    [strategies, setStrategies] = useState<Strategy[]>([]),
    [feedback, setFeedback] = useState<Feedback[]>([]);
  const [selected, setSelected] = useState(""),
    [refresh, setRefresh] = useState(0),
    [error, setError] = useState("");
  const [confirmed, setConfirmed] = useState<Record<string, boolean>>({});
  const end = new Date();
  const start = new Date(end);
  start.setUTCDate(start.getUTCDate() - 6);
  useEffect(() => {
    if (!creator) return;
    Promise.all([
      api<Report[]>(`/creators/${creator.id}/learning-reports`),
      api<Strategy[]>(`/creators/${creator.id}/strategy-proposals`),
      api<Feedback[]>("/analytics/feedback"),
    ])
      .then(([r, s, f]) => {
        setReports(r);
        setStrategies(s);
        setFeedback(f);
      })
      .catch((e) => setError(e.message));
  }, [creator?.id, creator?.active_strategy_id, refresh]);
  const report = reports.find((r) => r.id === selected) || reports[0];
  const run = (fn: () => Promise<unknown>, message: string) =>
    action(async () => {
      await fn();
      setRefresh((v) => v + 1);
    }, message);
  return (
    <>
      <PageHeader
        eyebrow="GROW WITH EVIDENCE"
        title="从可追溯的反馈，形成下一轮假设"
        description="本地规则整理真实记录；观察事实、用户偏好和待验证实验分别展示，不预测流量。"
      />
      {error && (
        <p className="alert warning" role="alert">
          {error}
        </p>
      )}
      {!creator ? (
        <EmptyState
          title="请先建立创作者"
          description="复盘需要关联创作者及其内容。"
          action={
            <Link className="button primary" href="/creator">
              建立创作者
            </Link>
          }
        />
      ) : (
        <>
          <Card>
            <form
              className="form-stack"
              onSubmit={(e) => {
                e.preventDefault();
                const f = new FormData(e.currentTarget);
                run(async () => {
                  const r = await api<Report>(
                    `/creators/${creator.id}/learning-reports`,
                    post({
                      period_start: f.get("start"),
                      period_end: f.get("end"),
                    }),
                  );
                  setSelected(r.id);
                }, "证据报告已保存，相同依据不会重复生成");
              }}
            >
              <div className="form-grid">
                <Field label="复盘开始">
                  <input
                    type="date"
                    name="start"
                    defaultValue={start.toISOString().slice(0, 10)}
                    required
                  />
                </Field>
                <Field label="复盘结束">
                  <input
                    type="date"
                    name="end"
                    defaultValue={end.toISOString().slice(0, 10)}
                    required
                  />
                </Field>
              </div>
              <Button type="submit" disabled={busy}>
                生成证据周报
              </Button>
            </form>
            <p className="muted">
              后台也会为启用的创作者整理上一完整周。缺少指标会保留“证据不足”；没有调用付费模型。
            </p>
            {reports.length > 0 && (
              <Field label="报告历史">
                <select
                  value={report?.id || ""}
                  onChange={(e) => setSelected(e.target.value)}
                >
                  {reports.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.period_start} — {r.period_end} · V{r.version}
                    </option>
                  ))}
                </select>
              </Field>
            )}
          </Card>
          {report ? (
            <>
              <div className="three-grid">
                <Card>
                  <h2>观察到的事实</h2>
                  {report.report.facts.map((t, i) => (
                    <p key={i}>{t}</p>
                  ))}
                  <Badge
                    tone={
                      report.report.confidence === "insufficient"
                        ? "warning"
                        : "blue"
                    }
                  >
                    {report.report.confidence === "insufficient"
                      ? "证据不足"
                      : "仅描述性统计"}
                  </Badge>
                </Card>
                <Card>
                  <h2>尚不能确定</h2>
                  {report.report.unknowns.map((t, i) => (
                    <p key={i}>{t}</p>
                  ))}
                </Card>
                <Card>
                  <h2>下一轮待验证实验</h2>
                  {report.report.next_experiments.map((t, i) => (
                    <p key={i}>{t}</p>
                  ))}
                  <Link href="/analytics/import" className="text-link">
                    补充指标来源
                  </Link>
                </Card>
              </div>
              {report.report.groups.map((g, i) => (
                <Card key={i}>
                  <h3>
                    {platformName[g.platform]} · {g.period_start} —{" "}
                    {g.period_end}
                  </h3>
                  <p>
                    来源：{g.data_source} · {g.sample_count} 篇观察
                  </p>
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>指标</th>
                          <th>均值</th>
                          <th>已知 / 缺失</th>
                        </tr>
                      </thead>
                      <tbody>
                        {Object.entries(g.metrics).map(([name, m]) => (
                          <tr key={name}>
                            <td>{name}</td>
                            <td>{m.mean === null ? "未知" : m.mean}</td>
                            <td>
                              {m.known_count} / {m.missing_count}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </Card>
              ))}
              <Card>
                <details>
                  <summary>报告原始证据与版本</summary>
                  <p>
                    这里保留生成时的原始依据。撤销数据后会生成新版，不改写旧报告。
                  </p>
                  <pre className="diagnostic-json">
                    {JSON.stringify(report, null, 2)}
                  </pre>
                </details>
              </Card>
            </>
          ) : (
            <Card>
              <EmptyState
                title="尚无报告"
                description="选择日期生成第一份报告；缺数据时不会补造数字。"
              />
            </Card>
          )}
          <Card>
            <h2>偏好与策略版本</h2>
            <p>
              当前生效：{creator.active_strategy_id || "原始设置"}
              。批准只影响后续新计划；回滚或撤销依据后，引用旧策略的待执行计划需复核。
            </p>
            {!strategies.length && (
              <p className="muted">
                达到 14 篇指标或三次同类反馈后可形成提案，仍需你批准。
              </p>
            )}
            {strategies.map((s) => (
              <section key={s.id} className="subtle-note">
                <Badge
                  tone={
                    s.id === creator.active_strategy_id ? "success" : "neutral"
                  }
                >
                  {labels[s.status] || s.status}
                </Badge>
                <h3>
                  {s.settings.tone === "restrained" ? "更克制" : "保留现有语气"}
                  {s.settings.concise ? "，更简短" : ""}
                </h3>
                <p>建议角度：{s.settings.preferred_angles.join(" / ")}</p>
                <p className="muted">
                  依据报告 {s.report_id} · 上一策略 {s.parent_id || "原始设置"}
                  。这是一项待验证假设。
                </p>
                <details>
                  <summary>策略依据</summary>
                  <pre className="diagnostic-json">
                    {JSON.stringify(s.settings.basis, null, 2)}
                  </pre>
                </details>
                {s.status === "proposed" && (
                  <>
                    <label className="checkline">
                      <input
                        type="checkbox"
                        checked={!!confirmed[s.id]}
                        onChange={(e) =>
                          setConfirmed({
                            ...confirmed,
                            [s.id]: e.target.checked,
                          })
                        }
                      />
                      已检查依据和影响，确认应用到后续计划
                    </label>
                    <div className="form-actions">
                      <Button
                        disabled={busy || !confirmed[s.id]}
                        onClick={() =>
                          run(
                            () =>
                              api(
                                `/creators/${creator.id}/strategy-proposals/${s.id}/decide`,
                                post({
                                  decision: "accept",
                                  confirmed: true,
                                  expected_active_id:
                                    creator.active_strategy_id || null,
                                }),
                              ),
                            "策略已批准",
                          )
                        }
                      >
                        接受策略
                      </Button>
                      <Button
                        variant="quiet"
                        disabled={busy}
                        onClick={() =>
                          run(
                            () =>
                              api(
                                `/creators/${creator.id}/strategy-proposals/${s.id}/decide`,
                                post({
                                  decision: "reject",
                                  confirmed: true,
                                  expected_active_id:
                                    creator.active_strategy_id || null,
                                }),
                              ),
                            "已拒绝提案",
                          )
                        }
                      >
                        拒绝
                      </Button>
                    </div>
                  </>
                )}
                {s.id === creator.active_strategy_id && (
                  <Button
                    variant="secondary"
                    disabled={busy}
                    onClick={() =>
                      run(
                        () =>
                          api(
                            `/creators/${creator.id}/strategy-proposals/${s.id}/rollback`,
                            post({ confirmed: true, expected_active_id: s.id }),
                          ),
                        "偏好已回滚",
                      )
                    }
                  >
                    回滚此策略
                  </Button>
                )}
              </section>
            ))}
          </Card>
          <Card>
            <h2>主动反馈</h2>
            <form
              className="form-stack"
              onSubmit={(e) => {
                e.preventDefault();
                const f = new FormData(e.currentTarget);
                const c = store.contents.find((c) => c.id === f.get("content"));
                if (!c) return;
                run(
                  () =>
                    api(
                      "/analytics/feedback",
                      post({
                        content_id: c.id,
                        expected_revision: c.revision,
                        reason_tag: f.get("reason"),
                        note: f.get("note"),
                      }),
                    ),
                  "反馈已绑定作品版本",
                );
              }}
            >
              <Field label="对应作品">
                <select name="content" required>
                  {store.contents.map((c) => (
                    <option value={c.id} key={c.id}>
                      {c.title} · V{c.revision}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="反馈原因">
                <select name="reason">
                  {[
                    "too_advertising",
                    "shorter",
                    "inaccurate",
                    "too_fast",
                    "more_real",
                    "inconsistent",
                    "useful",
                    "other",
                  ].map((k) => (
                    <option key={k} value={k}>
                      {labels[k]}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="具体说明（可选）">
                <textarea name="note" rows={3} maxLength={2000} />
              </Field>
              <Button type="submit" disabled={busy || !store.contents.length}>
                保存反馈
              </Button>
            </form>
            {feedback.slice(0, 30).map((f) => (
              <section key={f.id} className="subtle-note">
                <Badge>{f.active ? labels[f.reason_tag] : "已停用"}</Badge>
                <p>
                  {f.note || "无补充说明"} · V{f.content_revision}
                </p>
                <Link
                  className="text-link"
                  href={`/studio/article/${f.content_id}`}
                >
                  查看作品
                </Link>
                {f.active && (
                  <Button
                    variant="quiet"
                    disabled={busy}
                    onClick={() =>
                      run(
                        () =>
                          api(
                            `/analytics/feedback/${f.id}/withdraw`,
                            post({ confirmed: true }),
                          ),
                        "反馈及依赖偏好已停用",
                      )
                    }
                  >
                    停用反馈
                  </Button>
                )}
              </section>
            ))}
          </Card>
        </>
      )}
    </>
  );
}

export function ManualMetrics({ store, action, busy }: PageProps) {
  const [batches, setBatches] = useState<
    {
      id: string;
      data_source: string;
      created_at: string;
      committed: boolean;
    withdrawn: boolean;
    }[]
  >([]);
  const [refresh, setRefresh] = useState(0),
    [error, setError] = useState("");
  useEffect(() => {
    api<typeof batches>("/analytics/batches")
      .then(setBatches)
      .catch((e) => setError(e.message));
  }, [refresh, store.analytics.snapshot_count]);
  return (
    <Card>
      <details>
        <summary>手工指标与导入纠正</summary>
        {error && <p role="alert">{error}</p>}
        <p>
          未知指标留空。纠正时先撤销有误批次，再填写正确记录；历史报告保留原依据。
        </p>
        <form
          className="form-stack"
          onSubmit={(e) => {
            e.preventDefault();
            const f = new FormData(e.currentTarget);
            const c = store.contents.find((c) => c.id === f.get("content"));
            if (!c) return;
            const values: Record<string, number | null> = {};
            for (const key of [
              "views",
              "likes",
              "saves",
              "clicks",
              "conversions",
            ])
              values[key] =
                String(f.get(key)) === "" ? null : Number(f.get(key));
            action(async () => {
              await api(
                "/analytics/manual",
                post({
                  content_id: c.id,
                  platform: c.platform,
                  data_source: f.get("source"),
                  period_start: f.get("start"),
                  period_end: f.get("end"),
                  observed_at: new Date(
                    String(f.get("observed")),
                  ).toISOString(),
                  ...values,
                }),
              );
              setRefresh((v) => v + 1);
            }, "手工指标已保存");
          }}
        >
          <Field label="作品">
            <select name="content" required>
              {store.contents.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.title}
                </option>
              ))}
            </select>
          </Field>
          <Field label="真实来源">
            <input name="source" maxLength={180} required />
          </Field>
          <div className="form-grid">
            <Field label="统计开始">
              <input name="start" type="date" required />
            </Field>
            <Field label="统计结束">
              <input name="end" type="date" required />
            </Field>
            <Field label="观察时间（当前设备时区）">
              <input name="observed" type="datetime-local" required />
            </Field>
            {[
              ["views", "阅读/播放"],
              ["likes", "点赞"],
              ["saves", "收藏"],
              ["clicks", "点击"],
              ["conversions", "转化"],
            ].map(([key, label]) => (
              <Field key={key} label={label}>
                <input
                  type="number"
                  name={key}
                  min={0}
                  max={999999999999}
                  placeholder="未知请留空"
                />
              </Field>
            ))}
          </div>
          <Button type="submit" disabled={busy || !store.contents.length}>
            保存手工指标
          </Button>
        </form>
        <h3>导入批次</h3>
        {batches.map((b) => (
          <div key={b.id} className="subtle-note">
            <p>
              {b.data_source} · {b.created_at} ·{" "}
              {b.withdrawn ? "已停用" : b.committed ? "已入库" : "仅预览"}
            </p>
            {b.committed && !b.withdrawn && (
              <Button
                variant="quiet"
                disabled={busy}
                onClick={() =>
                  action(async () => {
                    await api(
                      `/analytics/batches/${b.id}/withdraw`,
                      post({ confirmed: true }),
                    );
                    setRefresh((v) => v + 1);
                  }, "此批次指标及依赖偏好已停用")
                }
              >
                撤销此批次指标
              </Button>
            )}
          </div>
        ))}
      </details>
    </Card>
  );
}
