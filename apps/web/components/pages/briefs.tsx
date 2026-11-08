"use client";
import { PresentationControls, defaultPresentation } from "./film-design";
import { Button, Card, StatusBadge } from "@xuliu/ui";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, post, type Run } from "../../lib/api";
import { Field, PageHeader, type PageProps } from "../page-shared";
import {
  VoiceControls,
  defaultVoiceSettings,
  type VoiceSettings,
} from "./narration";

type BriefDocument = {
  brand_id: string;
  topic: string;
  content: string;
  audience: string;
  tone: string;
  narrative_mode?: string;
  verbatim_script: string;
  required_phrases: string[];
  forbidden_phrases: string[];
  call_to_action: string;
  duration_sec: number;
  size: string;
  visual_mode: string;
  fact_refs: string[];
  asset_ids: string[];
};
type Brief = {
  id: string;
  topic: string;
  revision: number;
  document: BriefDocument;
};
type ScriptShot = {
  duration_frames: number;
  caption: string;
  narration: string;
  visual_note: string;
  asset_id: string | null;
};
type Script = {
  title: string;
  fact_refs: string[];
  shots: ScriptShot[];
  uncertainties: string[];
};
type Plan = {
  id: string;
  method: string;
  brief_revision: number;
  document: Script;
  stale?: boolean;
  video_id: string | null;
  review: {
    status: string;
    issues: string[];
    uncertainties: string[];
    creative_review?: {
      questions: string[];
      same_caption_and_narration: number;
      distinct_shot_durations: number;
    };
    model_usage?: { prompt_tokens: number; completion_tokens: number };
  };
};
type Detail = { brief: Brief; plans: Plan[]; runs: Run[] };
const lines = (value: FormDataEntryValue | null) =>
  String(value || "")
    .split(/\r?\n/)
    .map((x) => x.trim())
    .filter(Boolean);

export function BriefsPage(props: PageProps) {
  const { store, action, busy, path } = props;
  const router = useRouter();
  const id = path.split("/")[3];
  const selectedId = /^[a-f0-9]{32}$/.test(id || "") ? id : "";
  const [list, setList] = useState<Brief[]>([]);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [tick, setTick] = useState(0);
  const [dirty, setDirty] = useState(false);
  const [error, setError] = useState("");
  const [selectedPlanId, setSelectedPlanId] = useState("");
  const [consent, setConsent] = useState(false);
  const [cap, setCap] = useState("0.10");
  const runState = store.runs.map((r) => r.id + r.status + r.stage).join("|");
  useEffect(() => {
    let cancelled = false;
    Promise.all([
      api<Brief[]>("/creation-briefs"),
      selectedId
        ? api<Detail>(`/creation-briefs/${selectedId}`)
        : Promise.resolve(null),
    ])
      .then(([rows, data]) => {
        if (!cancelled) {
          setList(rows);
          setDetail(data);
          setError("");
        }
      })
      .catch((e) => {
        if (!cancelled) setError(e.message);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedId, tick, runState]);
  useEffect(() => {
    setDirty(false);
    setSelectedPlanId("");
    setConsent(false);
  }, [selectedId, detail?.brief.revision]);
  const brief = detail?.brief.id === selectedId ? detail.brief : undefined;
  const plan =
    detail?.plans.find((p) => p.id === selectedPlanId) || detail?.plans[0];
  const brand = store.brands[0];
  const creator = store.creators.find((c) => c.brand_id === brand?.id);
  const pending = detail?.runs.some((r) =>
    ["queued", "running"].includes(r.status),
  );
  const run = (fn: () => Promise<unknown>, message: string) =>
    action(async () => {
      await fn();
      setTick((t) => t + 1);
    }, message);
  if (!brand)
    return (
      <Card>
        <h1>先告诉我，这条视频要介绍什么</h1>
        <p>
          填写产品或项目名称，即可在这里规定内容、制作分镜和配音视频。手工制作不需要开启自动创作者。
        </p>
        <form
          className="form-stack"
          onSubmit={(e) => {
            e.preventDefault();
            const form = new FormData(e.currentTarget);
            action(
              () =>
                api(
                  "/brands",
                  post({
                    name: form.get("name"),
                    description: form.get("description"),
                    audience: form.get("audience"),
                    website: "",
                    facts: [],
                  }),
                ),
              "资料已保存，可以开始规定视频内容",
            );
          }}
        >
          <Field label="产品或项目名称">
            <input
              name="name"
              required
              maxLength={100}
              placeholder="例如：我的文件整理工具"
            />
          </Field>
          <Field label="这是什么产品或项目">
            <textarea
              name="description"
              maxLength={2000}
              rows={3}
              placeholder="用自己的话简单介绍，用于组织你的创作资料"
            />
          </Field>
          <Field label="给谁看">
            <input
              name="audience"
              maxLength={500}
              placeholder="例如：第一次使用软件的人"
            />
          </Field>
          <Button type="submit" disabled={busy}>
            保存资料并开始创作
          </Button>
        </form>
        <p className="muted">
          以上介绍不会自动成为已核实事实。使用 AI 写产品脚本前，请在
          <Link href="/brand">品牌与素材</Link>添加有来源的事实。
        </p>
      </Card>
    );
  return (
    <>
      <PageHeader
        eyebrow="YOUR CREATIVE BRIEF"
        title="你来定主题，作品按你的要求创作"
        description="规定内容、原文与表达方式，先检查脚本，再制作视频。"
      >
        <Button
          variant="secondary"
          disabled={busy}
          onClick={() => router.push("/studio/briefs/new")}
        >
          新建创作要求
        </Button>
        <Link href="/settings/models" className="button quiet">
          模型设置
        </Link>
      </PageHeader>
      <Card>
        <h2>这里能做什么视频？</h2>
        <p>
          DeepSeek
          编写脚本、分镜和旁白文字；本地引擎制作动态文字解说、实录讲解及素材混合短片。人物表演、任意新场景等生成式画面需要另接视频生成服务。
        </p>
        <p className="muted">
          确认脚本后可选择本机中文配音，自动合成音轨、字幕和视频；实录镜头使用你选择的真实素材。画面说明是制作建议。
        </p>
      </Card>
      {error && (
        <p className="alert warning" role="alert">
          {error}
        </p>
      )}
      <Field label="已保存的创作要求">
        <select
          value={selectedId}
          onChange={(e) =>
            router.push(
              e.target.value
                ? `/studio/briefs/${e.target.value}`
                : "/studio/briefs/new",
            )
          }
        >
          <option value="">新建一份</option>
          {list.map((b) => (
            <option key={b.id} value={b.id}>
              {b.topic} · V{b.revision}
            </option>
          ))}
        </select>
      </Field>
      {selectedId && !brief ? (
        <p>正在读取创作要求…</p>
      ) : (
        <Card>
          <h2>1. 规定你要讲什么{brief ? ` · V${brief.revision}` : ""}</h2>
          <form
            key={brief ? brief.id + brief.revision : "new"}
            className="form-stack"
            onChange={() => setDirty(true)}
            onSubmit={(e) => {
              e.preventDefault();
              const f = new FormData(e.currentTarget);
              const document = {
                brand_id: brand.id,
                topic: String(f.get("topic")),
                content: String(f.get("content")),
                audience: String(f.get("audience")),
                tone: String(f.get("tone")),
                narrative_mode: String(f.get("narrative_mode")),
                verbatim_script: String(f.get("verbatim_script")),
                required_phrases: lines(f.get("required")),
                forbidden_phrases: lines(f.get("forbidden")),
                call_to_action: String(f.get("cta")),
                duration_sec: Number(f.get("duration")),
                size: String(f.get("size")),
                visual_mode: String(f.get("mode")),
                fact_refs: f.getAll("fact_refs").map(String),
                asset_ids: f.getAll("asset_ids").map(String),
              };
              run(async () => {
                const result = await api<Brief>(
                  brief ? `/creation-briefs/${brief.id}` : "/creation-briefs",
                  {
                    method: brief ? "PUT" : "POST",
                    body: JSON.stringify(
                      brief
                        ? { expected_revision: brief.revision, document }
                        : document,
                    ),
                  },
                );
                setDirty(false);
                router.push(`/studio/briefs/${result.id}`);
              }, "创作要求已保存，尚未调用模型");
            }}
          >
            <Field label="视频主题">
              <input
                name="topic"
                required
                maxLength={180}
                defaultValue={brief?.document.topic || ""}
                placeholder="例如：用 30 秒讲清楚软件如何整理文件"
              />
            </Field>
            <Field label="这条视频怎样讲">
              <select
                name="narrative_mode"
                defaultValue={brief?.document.narrative_mode || "story"}
              >
                <option value="story">轻剧情：处境、追问、转折、解决</option>
                <option value="contrast">
                  反差幽默：前后对比，一个具体例子
                </option>
                <option value="documentary">真实故事：细节、过程与回看</option>
                <option value="overview">功能概览：直接介绍产品</option>
              </select>
              <span className="muted">
                用于 AI
                分镜；原文模式仍逐行保留你的文字。人物表演、实拍和音色需要相应素材。
              </span>
            </Field>
            <Field label="视频内容与结构要求">
              <textarea
                name="content"
                required
                rows={4}
                maxLength={6000}
                defaultValue={brief?.document.content || ""}
                placeholder="想解决什么问题、讲哪些内容、怎样开场和结尾。产品能力请关联下面已核实的事实。"
              />
            </Field>
            <div className="form-grid">
              <Field label="目标受众">
                <input
                  name="audience"
                  maxLength={1000}
                  defaultValue={brief?.document.audience ?? brand.audience}
                />
              </Field>
              <Field label="表达语气">
                <input
                  name="tone"
                  maxLength={500}
                  defaultValue={brief?.document.tone || "清楚、克制、不夸张"}
                />
              </Field>
            </div>
            <Field label="逐镜头原文（原文模式必填）">
              <textarea
                name="verbatim_script"
                rows={5}
                maxLength={2400}
                defaultValue={brief?.document.verbatim_script || ""}
                placeholder={
                  "每个非空行作为一个镜头，1–12 行，每行最多 180 字。\n原文模式保留每行文字，仅去除行首行尾空白。"
                }
              />
            </Field>
            <div className="form-grid">
              <Field label="画面必须出现的原文（每行一项，最多 8 项）">
                <textarea
                  name="required"
                  rows={3}
                  maxLength={1000}
                  defaultValue={
                    brief?.document.required_phrases.join("\n") || ""
                  }
                />
              </Field>
              <Field label="标题、画面和旁白禁用词（每行一项，最多 8 项）">
                <textarea
                  name="forbidden"
                  rows={3}
                  maxLength={1000}
                  defaultValue={
                    brief?.document.forbidden_phrases.join("\n") || ""
                  }
                />
              </Field>
            </div>
            <Field label="行动引导（原样出现在画面文字中）">
              <input
                name="cta"
                maxLength={120}
                defaultValue={brief?.document.call_to_action || ""}
                placeholder="例如：了解详情后，结合实际版本体验"
              />
            </Field>
            <div className="form-grid">
              <Field label="视频总时长（秒）">
                <input
                  type="number"
                  name="duration"
                  min={3}
                  max={60}
                  required
                  defaultValue={brief?.document.duration_sec || 30}
                />
              </Field>
              <Field label="视频比例">
                <select
                  name="size"
                  defaultValue={brief?.document.size || "wide"}
                >
                  <option value="wide">横屏 16:9</option>
                  <option value="portrait">竖屏 9:16</option>
                  <option value="square">方形 1:1</option>
                </select>
              </Field>
              <Field label="画面制作形式">
                <select
                  name="mode"
                  defaultValue={brief?.document.visual_mode || "mg"}
                >
                  <option value="mg">MG 动态文字</option>
                  <option value="screen_demo">
                    素材分镜（实录 / 实拍 / 插画）
                  </option>
                  <option value="mixed">MG 与真实素材混合</option>
                </select>
              </Field>
            </div>
            <fieldset>
              <legend>本次可以引用的已核实事实（AI 脚本至少选择一条）</legend>
              {brand.facts
                .filter((f) => f.verified)
                .map((f, i) => (
                  <label key={f.id} className="checkline">
                    <input
                      type="checkbox"
                      name="fact_refs"
                      value={f.id}
                      defaultChecked={
                        brief ? brief.document.fact_refs.includes(f.id) : i < 3
                      }
                    />
                    {f.claim}
                  </label>
                ))}
              <p className="muted">
                创作要求不会自动成为产品事实。
                <Link href="/brand">核实新功能声明</Link>
              </p>
            </fieldset>
            <fieldset>
              <legend>允许用于本次视频的真实素材</legend>
              {store.assets
                .filter(
                  (a) =>
                    a.brand_id === brand.id &&
                    a.verified &&
                    a.kind !== "audio" &&
                    a.applicability_status !== "needs_review",
                )
                .map((a) => (
                  <label key={a.id} className="checkline">
                    <input
                      type="checkbox"
                      name="asset_ids"
                      value={a.id}
                      defaultChecked={
                        brief?.document.asset_ids.includes(a.id) || false
                      }
                    />
                    {a.name}
                  </label>
                ))}
              <Link href="/studio/assets" className="text-link">
                上传录屏、图片或核实素材授权
              </Link>
            </fieldset>
            <Button type="submit" disabled={busy}>
              保存创作要求
            </Button>
            {dirty && (
              <p className="alert warning">
                有未保存的要求。先保存，再准备脚本；修改要求后旧脚本需重新准备。
              </p>
            )}
          </form>
        </Card>
      )}
      {brief && (
        <Card>
          <h2>2. 准备脚本</h2>
          <p>先把内容整理成可编辑分镜。保存要求与原文模式均不调用模型。</p>
          <Button
            variant="secondary"
            disabled={busy || dirty || !brief.document.verbatim_script.trim()}
            onClick={() =>
              run(async () => {
                const prepared = await api<Plan>(
                  `/creation-briefs/${brief.id}/plans/manual`,
                  post({
                    expected_revision: brief.revision,
                    confirmed: true,
                  }),
                );
                setSelectedPlanId(prepared.id);
              }, "原文脚本已保存，请检查分镜")
            }
          >
            按原文准备分镜（无模型费用）
          </Button>
          <details>
            <summary>让 AI 按要求编写脚本</summary>
            <p>
              将本次要求、原文、受众、选定事实和素材名称/类型发给你配置的模型，不发送素材文件。模型脚本先保存供你检查，不自动制作或发布。
            </p>
            <Field label="本次模型费用上限（元，按配置单价估算）">
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
                checked={consent}
                onChange={(e) => setConsent(e.target.checked)}
              />
              同意本次发送上述资料，并承担预算内费用
            </label>
            <Button
              disabled={
                busy ||
                dirty ||
                pending ||
                !consent ||
                !creator ||
                creator.status !== "active" ||
                !creator.model_consent ||
                !brief.document.fact_refs.length ||
                !Number.isFinite(Number(cap)) ||
                Number(cap) < 0.01 ||
                Number(cap) > 100 ||
                !["owner", "admin"].includes(store.user.role)
              }
              onClick={() =>
                run(async () => {
                  await api(`/creation-briefs/${brief.id}/plans/ai`, {
                    ...post({
                      expected_revision: brief.revision,
                      confirmed: true,
                      creator_id: creator?.id,
                      max_cost_cents: Math.round(Number(cap) * 100),
                    }),
                    headers: { "Idempotency-Key": crypto.randomUUID() },
                  });
                  setConsent(false);
                  setSelectedPlanId("");
                }, "AI 脚本已排队，完成后在下方检查")
              }
            >
              提交一次 AI 脚本创作
            </Button>
            <p className="muted">
              需同品牌创作者处于运行状态并启用模型授权，费用计入其日/月预算。超时或格式未知不会自动重试。
              <Link href="/creator/edit">创作者设置</Link>
            </p>
          </details>
          {detail?.runs.map((r) => (
            <p key={r.id}>
              <StatusBadge status={r.status} /> {r.stage}{" "}
              {r.error_code && `· ${r.error_code}`} ·{" "}
              <Link href="/creator/activity">查看任务与费用</Link>
            </p>
          ))}
        </Card>
      )}
      {brief && plan && (
        <>
          <Field label="脚本历史（修改会另存一份）">
            <select
              value={plan.id}
              onChange={(e) => setSelectedPlanId(e.target.value)}
            >
              {detail?.plans.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.method === "user_text"
                    ? "原文脚本"
                    : p.method === "user_edit"
                      ? "人工修订"
                      : "模型建议"}{" "}
                  · 要求 V{p.brief_revision} · {p.id.slice(0, 8)}
                  {p.stale ? " · 依据已变化" : ""}
                </option>
              ))}
            </select>
          </Field>
          <BriefScriptEditor
            key={plan.id}
            {...props}
            brief={brief}
            plan={plan}
            locked={dirty}
            onSaved={(id) => {
              setSelectedPlanId(id);
              setTick((t) => t + 1);
            }}
          />
        </>
      )}
    </>
  );
}

function BriefScriptEditor({
  store,
  action,
  busy,
  brief,
  plan,
  locked,
  onSaved,
}: PageProps & {
  brief: Brief;
  plan: Plan;
  locked: boolean;
  onSaved: (id: string) => void;
}) {
  const router = useRouter();
  const [draft, setDraft] = useState<Script>(structuredClone(plan.document));
  const [dirty, setDirty] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const [withVoice, setWithVoice] = useState(true);
  const [presentation, setPresentation] = useState(defaultPresentation);
  const [productionMode, setProductionMode] = useState("auto");
  const [voiceSettings, setVoiceSettings] =
    useState<VoiceSettings>(defaultVoiceSettings);
  const [error, setError] = useState("");
  const update = (doc: Script) => {
    setDraft(doc);
    setDirty(true);
    setConfirmed(false);
  };
  const changeShot = (index: number, patch: Partial<ScriptShot>) =>
    update({
      ...draft,
      shots: draft.shots.map((s, i) => (i === index ? { ...s, ...patch } : s)),
    });
  const total = draft.shots.reduce((sum, s) => sum + s.duration_frames, 0);
  const hasMedia = draft.shots.some((s) => !!s.asset_id);
  const allMedia = draft.shots.every((s) => !!s.asset_id);
  const recommendedMode = allMedia ? "screen_demo" : hasMedia ? "mixed" : "mg";
  return (
    <Card>
      <h2>3. 检查脚本与分镜，再制作预览</h2>
      <p className="muted">
        {plan.method === "model_suggestion"
          ? "模型脚本建议，待人工核对"
          : "用户提供或修订的脚本"}
        。画面说明供你核对；下方选择声音并确认后，可将旁白合成为真实音轨。
      </p>
      {plan.stale && (
        <p className="alert warning">
          要求或依据已变化，旧脚本仅供参考。请回到第 2 步准备当前版本的脚本。
        </p>
      )}
      {locked && (
        <p className="alert warning">上方创作要求尚未保存，请先处理。</p>
      )}
      {error && (
        <p className="alert warning" role="alert">
          {error}
        </p>
      )}
      {plan.review.issues.map((x, i) => (
        <p className="alert warning" key={i}>
          {x}
        </p>
      ))}
      {plan.review.uncertainties?.length > 0 && (
        <p className="alert warning">
          待补充或核实：{plan.review.uncertainties.join("；")}
        </p>
      )}
      {plan.review.creative_review && (
        <details>
          <summary>创作复看：这段内容有吸引力吗？</summary>
          <p className="muted">
            以下供你复看画面与听感，不是质量评分。修改脚本后请保存，再查看更新后的提示。
          </p>
          <ul>
            {plan.review.creative_review.questions.map((question) => (
              <li key={question}>{question}</li>
            ))}
          </ul>
        </details>
      )}
      <Field label="脚本标题 / 工程名称">
        <input
          maxLength={180}
          value={draft.title}
          onChange={(e) => update({ ...draft, title: e.target.value })}
        />
      </Field>
      <fieldset>
        <legend>脚本实际引用的事实</legend>
        {store.brands
          .find((b) => b.id === brief.document.brand_id)
          ?.facts.filter((f) => brief.document.fact_refs.includes(f.id))
          .map((f) => (
            <label key={f.id} className="checkline">
              <input
                type="checkbox"
                checked={draft.fact_refs.includes(f.id)}
                onChange={(e) =>
                  update({
                    ...draft,
                    fact_refs: e.target.checked
                      ? [...draft.fact_refs, f.id]
                      : draft.fact_refs.filter((id) => id !== f.id),
                  })
                }
              />
              {f.claim}
            </label>
          ))}
        {draft.fact_refs.some(
          (id) => !brief.document.fact_refs.includes(id),
        ) && (
          <Button
            variant="quiet"
            onClick={() =>
              update({
                ...draft,
                fact_refs: draft.fact_refs.filter((id) =>
                  brief.document.fact_refs.includes(id),
                ),
              })
            }
          >
            移除未被授权给本次创作的事实引用
          </Button>
        )}
      </fieldset>
      <Field label="待核实事项（每行一项，最多 8 项）">
        <textarea
          rows={3}
          maxLength={4000}
          value={draft.uncertainties.join("\n")}
          onChange={(e) =>
            update({ ...draft, uncertainties: e.target.value.split("\n") })
          }
          onBlur={() => {
            const cleaned = draft.uncertainties
              .map((x) => x.trim())
              .filter(Boolean);
            if (cleaned.join("\n") !== draft.uncertainties.join("\n"))
              update({ ...draft, uncertainties: cleaned });
          }}
        />
      </Field>
      <p>
        分镜总时长 {(total / 30).toFixed(2)} 秒 / 目标{" "}
        {brief.document.duration_sec} 秒
      </p>
      <Button
        variant="quiet"
        disabled={busy || locked || plan.stale}
        onClick={() => {
          const frames = brief.document.duration_sec * 30;
          if (frames / draft.shots.length < 15) {
            setError("镜头过多，每镜至少半秒；请减少镜头。");
            return;
          }
          update({
            ...draft,
            shots: draft.shots.map((s, i) => ({
              ...s,
              duration_frames:
                Math.floor(frames / draft.shots.length) +
                (i < frames % draft.shots.length ? 1 : 0),
            })),
          });
        }}
      >
        按指定总时长均分
      </Button>
      {draft.shots.map((shot, i) => (
        <section className="subtle-note form-stack" key={i}>
          <h3>镜头 {i + 1}</h3>
          <Field label={`镜头 ${i + 1} 时长（秒）`}>
            <input
              type="number"
              min={0.5}
              max={60}
              step={0.5}
              value={shot.duration_frames / 30}
              onChange={(e) =>
                changeShot(i, {
                  duration_frames: Math.round(Number(e.target.value) * 30),
                })
              }
            />
          </Field>
          <Field label={`镜头 ${i + 1} 画面文字`}>
            <textarea
              rows={2}
              maxLength={180}
              value={shot.caption}
              onChange={(e) => changeShot(i, { caption: e.target.value })}
            />
          </Field>
          <Field label={`镜头 ${i + 1} 旁白文字脚本`}>
            <textarea
              rows={2}
              maxLength={600}
              value={shot.narration}
              onChange={(e) => changeShot(i, { narration: e.target.value })}
            />
          </Field>
          <Field label={`镜头 ${i + 1} 画面说明（制作建议）`}>
            <textarea
              rows={2}
              maxLength={500}
              value={shot.visual_note}
              onChange={(e) => changeShot(i, { visual_note: e.target.value })}
            />
          </Field>
          <Field label={`镜头 ${i + 1} 使用的素材`}>
            <select
              value={shot.asset_id || ""}
              onChange={(e) =>
                changeShot(i, { asset_id: e.target.value || null })
              }
            >
              <option value="">MG 文字与图形</option>
              {store.assets
                .filter((a) => brief.document.asset_ids.includes(a.id))
                .map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name}
                  </option>
                ))}
            </select>
          </Field>
          <div className="form-actions">
            <Button
              variant="quiet"
              disabled={i === 0}
              onClick={() => {
                const shots = [...draft.shots];
                [shots[i - 1], shots[i]] = [shots[i], shots[i - 1]];
                update({ ...draft, shots });
              }}
            >
              上移
            </Button>
            <Button
              variant="quiet"
              disabled={i === draft.shots.length - 1}
              onClick={() => {
                const shots = [...draft.shots];
                [shots[i + 1], shots[i]] = [shots[i], shots[i + 1]];
                update({ ...draft, shots });
              }}
            >
              下移
            </Button>
            <Button
              variant="quiet"
              disabled={draft.shots.length <= 1}
              onClick={() =>
                update({
                  ...draft,
                  shots: draft.shots.filter((_, n) => n !== i),
                })
              }
            >
              删除此镜头
            </Button>
          </div>
        </section>
      ))}
      <div className="form-actions">
        <Button
          variant="secondary"
          disabled={draft.shots.length >= 12}
          onClick={() =>
            update({
              ...draft,
              shots: [
                ...draft.shots,
                {
                  caption: "新的镜头",
                  duration_frames: 90,
                  narration: "",
                  visual_note: "",
                  asset_id: null,
                },
              ],
            })
          }
        >
          增加镜头
        </Button>
        <Button
          disabled={busy || locked || plan.stale || !dirty}
          onClick={() =>
            action(async () => {
              const next = await api<Plan>(
                `/creation-briefs/${brief.id}/plans/${plan.id}/revisions`,
                post({ expected_revision: brief.revision, document: draft }),
              );
              onSaved(next.id);
            }, "修订已另存，原脚本保留")
          }
        >
          保存脚本修订
        </Button>
      </div>
      <label className="checkline">
        <input
          type="checkbox"
          checked={withVoice}
          disabled={busy || locked || dirty || !!plan.stale}
          onChange={(e) => setWithVoice(e.target.checked)}
        />
        为这份脚本制作配音、同步字幕和视频
      </label>
      {!plan.video_id && (
        <Field label="成片画面形式">
          <select
            value={productionMode}
            disabled={busy || locked || dirty || !!plan.stale}
            onChange={(e) => setProductionMode(e.target.value)}
          >
            <option value="auto">按当前分镜推荐</option>
            {!hasMedia && <option value="mg">MG 图解与动态文字</option>}
            {allMedia && (
              <>
                <option value="screen_demo">保留界面比例的录屏教程</option>
                <option value="montage">全画幅素材混剪</option>
                <option value="illustrated">插画故事（每镜需要图片）</option>
              </>
            )}
            {hasMedia && !allMedia && (
              <option value="mixed">图解与素材混合制作</option>
            )}
            <option value="legacy">原产品发布片版式</option>
          </select>
        </Field>
      )}
      {!plan.video_id && (
        <PresentationControls
          fixedStudio={productionMode !== "legacy"}
          value={presentation}
          onChange={setPresentation}
          disabled={busy || locked || dirty || !!plan.stale}
        />
      )}
      {withVoice && (
        <VoiceControls
          value={voiceSettings}
          onChange={setVoiceSettings}
          disabled={busy || locked || dirty || !!plan.stale}
        />
      )}
      <label className="checkline">
        <input
          type="checkbox"
          checked={confirmed}
          disabled={dirty || locked || !!plan.stale}
          onChange={(e) => setConfirmed(e.target.checked)}
        />
        我已核对脚本、事实、素材和不确定项，同意按这份已保存脚本建立工程并制作低清预览
      </label>
      <Button
        disabled={
          busy ||
          locked ||
          dirty ||
          !!plan.stale ||
          !confirmed ||
          (withVoice &&
            (!voiceSettings.voice_id || !voiceSettings.usage_confirmed)) ||
          plan.review.status === "needs_revision"
        }
        onClick={() =>
          action(
            async () => {
              const result = await api<{ video_id: string }>(
                `/creation-briefs/${brief.id}/plans/${plan.id}/build`,
                post({
                  expected_revision: brief.revision,
                  confirmed: true,
                  ...(withVoice ? { narration: voiceSettings } : {}),
                  ...(!plan.video_id ? { presentation } : {}),
                  ...(!plan.video_id && productionMode !== "legacy"
                    ? {
                        production_mode:
                          productionMode === "auto"
                            ? recommendedMode
                            : productionMode,
                        recipe_id:
                          brief.document.narrative_mode === "story"
                            ? "story"
                            : brief.document.narrative_mode === "documentary"
                              ? "tutorial"
                              : brief.document.narrative_mode === "contrast"
                                ? "qa"
                                : "feature",
                      }
                    : {}),
                }),
              );
              router.push(`/studio/video/${result.video_id}`);
            },
            withVoice
              ? "配音、字幕与视频预览已排队"
              : "视频工程已建立，低清预览已排队",
          )
        }
      >
        {withVoice ? "制作带配音的视频预览" : "建立工程并制作无配音预览"}
      </Button>
      {plan.video_id && (
        <p>
          <Link href={`/studio/video/${plan.video_id}`} className="text-link">
            打开已建立的视频工程
          </Link>{" "}
          · 后续编辑以视频工作室保存的工程版本为准。
        </p>
      )}
    </Card>
  );
}
