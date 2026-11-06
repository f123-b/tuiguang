"use client";
import { Button, Card } from "@xuliu/ui";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api, post, type Video } from "../../lib/api";
import { Field, type PageProps } from "../page-shared";

type Report = {
  id: string;
  subject_revision: number;
  created_at: string;
  report: {
    method: string;
    decision: string;
    stale?: boolean;
    checks?: {
      key: string;
      label: string;
      status: string;
      evidence: unknown;
    }[];
    critique?: Record<string, unknown>;
    limits: string[];
    actual_cents?: number;
  };
};
type PreviewJob = {
  id: string;
  revision: number;
  status: string;
  purpose: string;
};
const statusText: Record<string, string> = {
  pass: "规则通过",
  blocked: "阻断",
  needs_review: "需复核",
  unknown: "不确定",
};

export function QualityPanel({
  store,
  action,
  busy,
  kind,
  id,
  revision,
  brandId,
  creatorId,
  dirty = false,
  video,
}: Pick<PageProps, "store" | "action" | "busy"> & {
  kind: "content" | "video";
  id: string;
  revision: number;
  brandId: string;
  creatorId?: string;
  dirty?: boolean;
  video?: Video;
}) {
  const root = kind === "video" ? `/videos/${id}` : `/content/packages/${id}`;
  const [reports, setReports] = useState<Report[]>([]);
  const [jobs, setJobs] = useState<PreviewJob[]>([]);
  const [note, setNote] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [modelConsent, setModelConsent] = useState(false);
  const [cap, setCap] = useState("0.10");
  const [error, setError] = useState("");
  const [review, setReview] = useState("");
  const creator = store.creators.find((c) =>
    creatorId ? c.id === creatorId : c.brand_id === brandId,
  );
  const [selectedCreator, setSelectedCreator] = useState(creator?.id || "");
  const refresh = async () => {
    const rows = await api<Report[]>(root + "/quality");
    setReports(rows);
    if (kind === "video") {
      setJobs(await api<PreviewJob[]>(root + "/render-jobs"));
      const reviews = await api<{ revision: number; decision: string }[]>(
        root + "/quality-reviews",
      );
      setReview(reviews.find((r) => r.revision === revision)?.decision || "");
    }
  };
  useEffect(() => {
    refresh().catch((e) => setError(e.message));
    const timer = setInterval(
      () => refresh().catch((e) => setError(e.message)),
      5000,
    );
    return () => clearInterval(timer);
    // Each report and preview remains bound to the server revision.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [root, revision]);
  useEffect(() => {
    setConfirmed(false);
    setNote("");
    setReview("");
  }, [id, revision]);
  const run = (fn: () => Promise<unknown>, message: string) =>
    action(async () => {
      await fn();
      await refresh();
    }, message);
  const current = reports.find(
    (r) => r.subject_revision === revision && r.report.method === "rules",
  );
  const ai = reports.find(
    (r) =>
      r.subject_revision === revision && r.report.method === "model_suggestion",
  );
  const preview = jobs.find(
    (j) =>
      j.purpose === "preview" &&
      j.revision === revision &&
      j.status === "completed",
  );
  const waiting = jobs.some(
    (j) => j.revision === revision && ["queued", "running"].includes(j.status),
  );
  const canModel = store.creators.find((c) => c.id === selectedCreator);
  return (
    <Card>
      <h2>创作质量与人工判断</h2>
      <p>
        检查开场、事实引用、相似标题和镜头结构。单一收益点、受众价值与表达目的需要人工判断；这里不预测流量。
      </p>
      {error && (
        <p className="alert warning" role="alert">
          {error}
        </p>
      )}
      {dirty && <p className="alert warning">有未保存修改，请先保存再检查。</p>}
      <Button
        variant="secondary"
        disabled={busy || dirty}
        onClick={() =>
          run(
            () => api(root + "/quality", post({ confirmed: true })),
            "已保存当前依据的规则检查",
          )
        }
      >
        检查当前作品
      </Button>
      {current ? (
        <>
          <p className="muted">
            检查版本 V{current.subject_revision} ·{" "}
            {new Date(current.created_at).toLocaleString("zh-CN")}
          </p>
          <div className="review-list">
            {current.report.checks?.map((c) => (
              <details key={c.key}>
                <summary>
                  {c.label} · {statusText[c.status] || c.status}
                </summary>
                <pre className="diagnostic-json">
                  {JSON.stringify(c.evidence, null, 2)}
                </pre>
              </details>
            ))}
          </div>
        </>
      ) : (
        <p className="muted">当前版本还没有规则报告。</p>
      )}
      <details>
        <summary>可选：让模型提供语义复核建议</summary>
        <p>
          将当前已保存的标题、正文（含图文卡和分平台文案）或镜头文案、已核实事实、受众及近 30
          条标题发送到你配置的模型。费用计入所选创作者预算。模型建议需人工核对。
        </p>
        <Link href="/settings/models" className="text-link">
          配置模型接口
        </Link>
        <Field label="承担预算的创作者">
          <select
            value={selectedCreator}
            onChange={(e) => {
              setSelectedCreator(e.target.value);
              setModelConsent(false);
            }}
          >
            <option value="">请选择</option>
            {store.creators
              .filter(
                (c) =>
                  c.brand_id === brandId && (!creatorId || c.id === creatorId),
              )
              .map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
          </select>
        </Field>
        <Field label="本次费用上限（元，以你填写的报价估算）">
          <input
            type="number"
            min="0.01"
            max="100"
            step="0.01"
            value={cap}
            onChange={(e) => setCap(e.target.value)}
          />
        </Field>
        <label className="checkline">
          <input
            type="checkbox"
            checked={modelConsent}
            onChange={(e) => setModelConsent(e.target.checked)}
          />
          我同意本次发送上述资料并承担预算内费用
        </label>
        <Button
          disabled={
            busy ||
            dirty ||
            !modelConsent ||
            !canModel?.model_consent ||
            canModel.status !== "active" ||
            !(Number(cap) >= 0.01)
          }
          onClick={() =>
            run(
              () =>
                api(root + "/quality/ai", {
                  ...post({
                    confirmed: true,
                    creator_id: selectedCreator,
                    expected_revision: revision,
                    max_cost_cents: Math.round(Number(cap) * 100),
                  }),
                  headers: {
                    "Content-Type": "application/json",
                    "Idempotency-Key": crypto.randomUUID(),
                  },
                }).then((v) => {
                  setModelConsent(false);
                  return v;
                }),
              "模型复核已排队；请查看任务及费用回执",
            )
          }
        >
          提交模型质量复核
        </Button>
        <p className="muted">
          需在创作者设置中启用模型授权并保持运行；超预算、配置或版本变化会停止请求。
        </p>
        {ai && (
          <>
            <p>
              {ai.report.stale
                ? "依据已变化，旧建议仅供参考"
                : "模型建议 · 待人工核对"}{" "}
              · 记账 ¥{((ai.report.actual_cents || 0) / 100).toFixed(2)}
            </p>
            <pre className="diagnostic-json">
              {JSON.stringify(ai.report.critique, null, 2)}
            </pre>
          </>
        )}
      </details>
      {video && (
        <>
          <h3>低清预览 → 人工确认 → 高清成片</h3>
          <p>
            {video.preview_required
              ? "此工程需要先预览并记录人工确认，才能生成高清成片。"
              : "旧工程保留直接渲染流程，也可主动使用预览检查。"}{" "}
            预览含水印，不能作为发布成片。
          </p>
          <Button
            variant="secondary"
            disabled={busy || dirty || waiting}
            onClick={() =>
              run(
                () =>
                  api(
                    root + "/preview",
                    post({ expected_revision: revision, confirmed: true }),
                  ),
                "低清预览已排队",
              )
            }
          >
            生成低清预览
          </Button>
          {preview && (
            <>
              <video
                controls
                preload="metadata"
                key={preview.id}
                style={{ width: "100%", maxHeight: 420 }}
                src={`/api/v1/videos/${id}/preview/download`}
              />
              <Field label="人工复核记录（至少 4 字）">
                <textarea
                  maxLength={2000}
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  placeholder="核对开场、收益点、受众、事实来源、字幕和声音"
                />
              </Field>
              <label className="checkline">
                <input
                  type="checkbox"
                  checked={confirmed}
                  onChange={(e) => setConfirmed(e.target.checked)}
                />
                我已播放当前预览，并人工核对质量报告中的不确定项
              </label>
              <div className="form-actions">
                {(["needs_rework", "accept"] as const).map((decision) => (
                  <Button
                    key={decision}
                    variant={decision === "accept" ? "primary" : "secondary"}
                    disabled={
                      busy ||
                      dirty ||
                      !confirmed ||
                      note.trim().length < 4 ||
                      !current ||
                      (decision === "accept" &&
                        current.report.decision === "blocked")
                    }
                    onClick={() =>
                      run(
                        () =>
                          api(
                            root + "/quality-review",
                            post({
                              expected_revision: revision,
                              confirmed: true,
                              preview_job_id: preview.id,
                              report_id: current?.id,
                              decision,
                              note,
                            }),
                          ),
                        decision === "accept"
                          ? "已记录人工确认，可以提交高清渲染"
                          : "已记录需要修改",
                      )
                    }
                  >
                    {decision === "accept" ? "确认可生成高清" : "需要修改"}
                  </Button>
                ))}
              </div>
            </>
          )}
          <p className="muted">
            当前人工记录：
            {review === "accept"
              ? "已确认；服务端提交时仍会复查依据和预览字节"
              : review === "needs_rework"
                ? "需要修改后重新预览"
                : "尚未确认"}
          </p>
          <Button
            disabled={
              busy ||
              dirty ||
              waiting ||
              (video.preview_required && review !== "accept")
            }
            onClick={() =>
              run(() => api(root + "/render", post()), "高清成片已排队")
            }
          >
            生成高清成片
          </Button>
        </>
      )}
      <details>
        <summary>历史报告（最近 30 份）</summary>
        <ul>
          {reports.map((r) => (
            <li key={r.id}>
              V{r.subject_revision} ·{" "}
              {r.report.method === "rules" ? "规则检查" : "模型建议"} ·{" "}
              {new Date(r.created_at).toLocaleString("zh-CN")} ·{" "}
              {r.id.slice(0, 8)}
            </li>
          ))}
        </ul>
      </details>
    </Card>
  );
}
