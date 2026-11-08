"use client";
import { Badge, Button, Card } from "@xuliu/ui";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { api, post } from "../../lib/api";
import { Field, PageHeader, type PageProps } from "../page-shared";
import { VoiceControls, defaultVoiceSettings } from "./narration";

type Character = {
  id: string;
  name: string;
  goal: string;
  flaw: string;
  appearance: string;
  voice_hint: string;
};
type Scene = {
  id: string;
  name: string;
  description: string;
  lighting: string;
  axis: string;
  palette: string;
};
type Beat = {
  id: string;
  cause_id: string | null;
  character_id: string;
  role: string;
  action: string;
  obstacle: string;
  result: string;
};
type Shot = {
  id: string;
  beat_id: string;
  scene_id: string;
  character_ids: string[];
  action: string;
  frame_prompt: string;
  motion_prompt: string;
  framing: string;
  camera: string;
  start_positions: Record<string, string>;
  end_positions: Record<string, string>;
  transition_reason: string;
  narration: string;
  delivery: string;
  frames: number;
  reference_asset_id: string | null;
};
type Plan = {
  title: string;
  logline: string;
  hook: string;
  characters: Character[];
  scenes: Scene[];
  beats: Beat[];
  shots: Shot[];
  uncertainties: string[];
};
type Project = {
  id: string;
  revision: number;
  document: {
    title: string;
    brand_id: string;
    story: string;
    theme: string;
    genre: string;
    duration_sec: number;
    style: string;
    size: string;
  };
  plan: Partial<Plan>;
  report: {
    issues?: { code: string; location: string; message: string }[];
    duration_sec?: number;
    human_checks?: string[];
  };
  confirmation: { revision?: number };
  bindings: Record<string, string>;
  stale: boolean;
  history: { revision: number; plan: Plan }[];
};
type Skill = {
  id: string;
  name: string;
  source: string;
  commit: string;
  license: string;
  mode: string;
  integrity: string;
};
type Job = {
  id: string;
  status: string;
  error_message?: string;
  receipt: { art_review?: string };
};
type Run = { id: string; status: string; error_code: string | null };
const roles: Record<string, string> = {
  hook: "开场钩子",
  setup: "困境推进",
  choice: "人物选择",
  payoff: "行动后果",
  cliff: "结尾悬念",
};
const blankPlan = (title: string): Plan => ({
  title,
  logline: "",
  hook: "",
  characters: [
    { id: "C01", name: "", goal: "", flaw: "", appearance: "", voice_hint: "" },
  ],
  scenes: [
    {
      id: "S01",
      name: "",
      description: "",
      lighting: "",
      axis: "",
      palette: "",
    },
  ],
  beats: [],
  shots: [],
  uncertainties: [],
});
const blankShot = (i: number): Shot => ({
  id: `SH${i}`,
  beat_id: `B${i}`,
  scene_id: "S01",
  character_ids: ["C01"],
  action: "",
  frame_prompt: "",
  motion_prompt: "",
  framing: "medium",
  camera: "固定机位",
  start_positions: { C01: "left" },
  end_positions: { C01: "left" },
  transition_reason: "",
  narration: "",
  delivery: "平静自然",
  frames: 121,
  reference_asset_id: null,
});

export function DramaSkillsStudio({ store, action, busy }: PageProps) {
  const router = useRouter();
  const [skills, setSkills] = useState<Skill[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [project, setProject] = useState<Project>();
  const [plan, setPlan] = useState<Plan>();
  const [runs, setRuns] = useState<Run[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [error, setError] = useState("");
  const [dirty, setDirty] = useState(false);
  const dirtyRef = useRef(false);
  const selected = useRef("");
  const version = useRef(0);
  const [step, setStep] = useState(0);
  const [brandId, setBrandId] = useState(store.brands[0]?.id || "");
  const [creatorId, setCreatorId] = useState("");
  const [note, setNote] = useState("");
  const [request, setRequest] = useState<{
    shot: string;
    body: Record<string, unknown>;
    takeKey: string;
    canRetake: boolean;
  }>();
  const [voice, setVoice] = useState({
    ...defaultVoiceSettings,
    fit_mode: "fixed" as const,
  });
  const [withVoice, setWithVoice] = useState(true);
  const modelKey = useRef<{ body: string; key: string } | undefined>(undefined);
  const change = (next: Plan) => {
    setPlan(next);
    setDirty(true);
    dirtyRef.current = true;
    setRequest(undefined);
  };
  const load = async (id: string) => {
    selected.current = id;
    const result = await api<{ project: Project; runs: Run[] }>(
      `/dramas/${id}`,
    );
    if (selected.current !== id) return;
    setProject(result.project);
    setRuns(result.runs);
    if (!dirtyRef.current || version.current === 0) {
      setPlan(
        result.project.plan.shots ? (result.project.plan as Plan) : undefined,
      );
      version.current = result.project.revision;
    }
    setJobs(await api<Job[]>("/video-generation/jobs"));
  };
  const list = async () => setProjects(await api<Project[]>("/dramas"));
  useEffect(() => {
    Promise.all([
      api<{ skills: Skill[] }>("/dramas/skills").then((r) =>
        setSkills(r.skills),
      ),
      list(),
    ]).catch((e) => setError(e.message));
    const timer = setInterval(() => {
      if (selected.current)
        void load(selected.current).catch((e) => setError(e.message));
    }, 10000);
    return () => clearInterval(timer);
  }, []);
  const choose = async (id: string) => {
    dirtyRef.current = false;
    setDirty(false);
    version.current = 0;
    setRequest(undefined);
    setNote("");
    await load(id);
  };
  const uri = project ? `/dramas/${project.id}` : "";
  const locked = !!project?.confirmation.revision && !dirty && !project.stale;
  const images = store.assets.filter(
    (a) =>
      a.brand_id === project?.document.brand_id &&
      a.kind === "image" &&
      a.verified &&
      a.applicability_status === "current",
  );
  const creators = store.creators.filter(
    (c) => c.brand_id === project?.document.brand_id,
  );
  const editShot = (i: number, value: Partial<Shot>) =>
    plan &&
    change({
      ...plan,
      shots: plan.shots.map((s, n) => (n === i ? { ...s, ...value } : s)),
    });
  const text = (
    label: string,
    value: string,
    onChange: (s: string) => void,
    multi = false,
  ) => (
    <Field label={label}>
      {multi ? (
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          rows={3}
          maxLength={700}
        />
      ) : (
        <input
          value={value}
          onChange={(e) => onChange(e.target.value)}
          maxLength={700}
        />
      )}
    </Field>
  );
  return (
    <>
      <PageHeader
        eyebrow="STORY → SHOTS → FILM"
        title="短剧制作"
        description="先把人物为什么行动、选择带来什么后果讲清楚，再制作动态镜头。支持真人与动漫。"
      >
        <Link className="button secondary" href="/studio/video/ai">
          动态镜头与审看
        </Link>
        <Link className="button secondary" href="/studio/video/new">
          其他视频类型
        </Link>
      </PageHeader>
      {error && <p role="alert">{error}</p>}
      <details className="card">
        <summary>
          已内置 {skills.length} 个制作 Skills · 查看来源与使用方式
        </summary>
        <p>
          七个制作技能提供大纲、人物、首帧参考规范、美术、剧本、走位和分镜方法，另有审片技能。规划读取固定参考片段；保存计划时实际运行剧本检查和软件的连续性规则。角色参考图需在素材库准备，其他原生报告与生图命令未自动执行。
        </p>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>技能</th>
                <th>许可</th>
                <th>固定版本</th>
                <th>接入</th>
              </tr>
            </thead>
            <tbody>
              {skills.map((s) => (
                <tr key={s.id}>
                  <td>
                    <a
                      href={s.source + "/tree/" + s.commit}
                      target="_blank"
                      rel="noreferrer"
                    >
                      {s.name}
                    </a>
                  </td>
                  <td>{s.license}</td>
                  <td>{s.commit.slice(0, 8)}</td>
                  <td>
                    {s.id === "novel-script" ? "参考与实际检查" : "方法参考"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
      <div className="form-columns">
        <Card>
          <h2>新建短剧</h2>
          <form
            className="form-stack"
            onSubmit={(e) => {
              e.preventDefault();
              const f = new FormData(e.currentTarget);
              void action(async () => {
                const created = await api<Project>(
                  "/dramas",
                  post({
                    brand_id: brandId,
                    title: f.get("title"),
                    story: f.get("story"),
                    theme: f.get("theme"),
                    genre: f.get("genre"),
                    duration_sec: Number(f.get("duration")),
                    style: f.get("style"),
                    size: f.get("size"),
                    fact_refs: f.getAll("fact"),
                    rights_confirmed: f.get("rights") === "on",
                  }),
                );
                await list();
                await choose(created.id);
              }, "短剧要求已保存");
            }}
          >
            <Field label="品牌">
              <select
                value={brandId}
                onChange={(e) => setBrandId(e.target.value)}
              >
                {store.brands.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.name}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="片名">
              <input name="title" required maxLength={120} />
            </Field>
            <Field label="故事内容：人物遇到什么问题，做了什么选择，结果怎样">
              <textarea
                name="story"
                required
                minLength={10}
                maxLength={6000}
                rows={4}
              />
            </Field>
            <Field label="主题 / 想让观众感受到什么">
              <input name="theme" required maxLength={400} />
            </Field>
            <div className="form-columns">
              <Field label="题材">
                <input name="genre" defaultValue="职场剧情" maxLength={100} />
              </Field>
              <Field label="时长（10–60秒）">
                <input
                  name="duration"
                  type="number"
                  min={10}
                  max={60}
                  defaultValue={20}
                />
              </Field>
            </div>
            <div className="form-columns">
              <Field label="风格">
                <select name="style">
                  <option value="realistic">真人</option>
                  <option value="anime">动漫</option>
                </select>
              </Field>
              <Field label="画幅">
                <select name="size">
                  <option value="wide">横屏</option>
                  <option value="portrait">竖屏</option>
                </select>
              </Field>
            </div>
            <fieldset>
              <legend>剧情可引用的已核实产品事实</legend>
              {store.brands
                .find((b) => b.id === brandId)
                ?.facts.filter((f) => f.verified)
                .map((f) => (
                  <label className="check-row" key={f.id}>
                    <input name="fact" type="checkbox" value={f.id} />
                    {f.claim}
                  </label>
                ))}
            </fieldset>
            <label className="check-row">
              <input name="rights" type="checkbox" required />
              这是原创故事或我已获得改编及使用授权
            </label>
            <Button disabled={busy || !brandId}>保存故事要求</Button>
          </form>
        </Card>
        <Card>
          <h2>我的短剧</h2>
          <div className="form-stack">
            {projects.length === 0 && (
              <p className="muted">先写故事要求，再让模型规划或自行编写。</p>
            )}
            {projects.map((p) => (
              <button
                className="button secondary"
                key={p.id}
                disabled={busy || dirty}
                onClick={() => void action(() => choose(p.id))}
              >
                {p.document.title} ·{" "}
                {p.document.style === "realistic" ? "真人" : "动漫"} ·{" "}
                {p.document.duration_sec}秒 · 第{p.revision}版
              </button>
            ))}
          </div>
        </Card>
      </div>
      {project && (
        <>
          <Card>
            <h2>{project.document.title}</h2>
            <p>{project.document.story}</p>
            <p className="muted">
              主题：{project.document.theme} · {project.document.duration_sec}秒
              ·{" "}
              {project.document.size === "wide"
                ? "横屏1280×704"
                : "竖屏704×1280"}
            </p>
            <div className="form-columns">
              <Field label="用于规划的创作者（使用其模型授权与预算）">
                <select
                  value={creatorId}
                  onChange={(e) => setCreatorId(e.target.value)}
                >
                  <option value="">请选择</option>
                  {creators.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name} · {c.model_consent ? "已授权模型" : "模型未授权"}{" "}
                      · {c.status}
                    </option>
                  ))}
                </select>
              </Field>
              <form
                className="form-stack"
                onSubmit={(e) => {
                  e.preventDefault();
                  const f = new FormData(e.currentTarget);
                  void action(async () => {
                    const body = {
                      expected_revision: project.revision,
                      confirmed: true,
                      creator_id: creatorId,
                      max_cost_cents: Number(f.get("cap")),
                    };
                    const stamp = JSON.stringify(body) + project.id;
                    if (modelKey.current?.body !== stamp)
                      modelKey.current = {
                        body: stamp,
                        key: crypto.randomUUID(),
                      };
                    await api(uri + "/plan-ai", {
                      ...post(body),
                      headers: { "Idempotency-Key": modelKey.current.key },
                    });
                    await load(project.id);
                  }, "已排队规划；不会自动生成画面");
                }}
              >
                <Field label="本次规划费用上限（分）">
                  <input
                    name="cap"
                    type="number"
                    min={1}
                    max={10000}
                    defaultValue={10}
                  />
                </Field>
                <label className="check-row">
                  <input type="checkbox" required />
                  同意把本次故事和所选事实发送给已配置的模型
                </label>
                <Button
                  disabled={
                    busy ||
                    !creatorId ||
                    dirty ||
                    runs.some((r) => ["queued", "running"].includes(r.status))
                  }
                >
                  用 Skills 规划短剧
                </Button>
              </form>
            </div>
            {runs.map((r) => (
              <p key={r.id}>
                规划任务 {r.id.slice(0, 8)}：{r.status}
                {r.error_code &&
                  ` · ${r.error_code}，请核对后手工修订，不自动重试`}
              </p>
            ))}
            {!plan && (
              <Button
                variant="secondary"
                onClick={() => change(blankPlan(project.document.title))}
              >
                自己编写人物与分镜
              </Button>
            )}
          </Card>
          {plan && (
            <>
              <nav className="toolbar" aria-label="短剧制作阶段">
                {["故事与人物", "场景与剧本", "镜头与首帧", "检查与制作"].map(
                  (s, i) => (
                    <Button
                      key={s}
                      variant={step === i ? "primary" : "secondary"}
                      onClick={() => setStep(i)}
                    >
                      {i + 1}. {s}
                    </Button>
                  ),
                )}
              </nav>
              {dirty && (
                <p role="status">
                  有未保存的修改。保存后重新检查与确认，旧生成镜头保留在历史中。
                  <Button
                    variant="secondary"
                    disabled={busy}
                    onClick={() =>
                      void action(
                        () => choose(project.id),
                        "已重新读取保存版本",
                      )
                    }
                  >
                    放弃未保存的修改
                  </Button>
                </p>
              )}
              {step === 0 && (
                <Card>
                  <h2>故事与人物动机</h2>
                  <div className="form-stack">
                    {text(
                      "一句话故事",
                      plan.logline,
                      (v) => change({ ...plan, logline: v }),
                      true,
                    )}
                    {text(
                      "开场具体钩子",
                      plan.hook,
                      (v) => change({ ...plan, hook: v }),
                      true,
                    )}
                    {plan.characters.map((c, i) => (
                      <fieldset key={i}>
                        <legend>
                          {c.id} · {c.name || "新角色"}
                        </legend>
                        {(
                          [
                            ["name", "姓名"],
                            ["goal", "想得到什么"],
                            ["flaw", "弱点 / 为什么会犹豫"],
                            ["appearance", "身份、服装、发型连续性锁"],
                            ["voice_hint", "声音与表演方向"],
                          ] as const
                        ).map(([k, label]) => (
                          <div key={k}>
                            {text(label, c[k], (v) =>
                              change({
                                ...plan,
                                characters: plan.characters.map((x, n) =>
                                  n === i ? { ...x, [k]: v } : x,
                                ),
                              }),
                            )}
                          </div>
                        ))}
                      </fieldset>
                    ))}
                    <Button
                      variant="secondary"
                      disabled={plan.characters.length >= 3}
                      onClick={() =>
                        change({
                          ...plan,
                          characters: [
                            ...plan.characters,
                            {
                              id: `C0${plan.characters.length + 1}`,
                              name: "",
                              goal: "",
                              flaw: "",
                              appearance: "",
                              voice_hint: "",
                            },
                          ],
                        })
                      }
                    >
                      增加角色
                    </Button>
                  </div>
                </Card>
              )}
              {step === 1 && (
                <Card>
                  <h2>场景与因果节拍</h2>
                  <div className="form-stack">
                    {plan.scenes.map((s, i) => (
                      <fieldset key={i}>
                        <legend>
                          {s.id} · {s.name || "新场景"}
                        </legend>
                        {(
                          [
                            ["name", "场景名"],
                            ["description", "空间与关键道具"],
                            ["lighting", "光照"],
                            ["axis", "轴线与空间关系"],
                            ["palette", "色彩"],
                          ] as const
                        ).map(([k, label]) => (
                          <div key={k}>
                            {text(label, s[k], (v) =>
                              change({
                                ...plan,
                                scenes: plan.scenes.map((x, n) =>
                                  n === i ? { ...x, [k]: v } : x,
                                ),
                              }),
                            )}
                          </div>
                        ))}
                      </fieldset>
                    ))}
                    <Button
                      variant="secondary"
                      disabled={plan.scenes.length >= 4}
                      onClick={() =>
                        change({
                          ...plan,
                          scenes: [
                            ...plan.scenes,
                            {
                              id: `S0${plan.scenes.length + 1}`,
                              name: "",
                              description: "",
                              lighting: "",
                              axis: "",
                              palette: "",
                            },
                          ],
                        })
                      }
                    >
                      增加场景
                    </Button>
                    {plan.beats.map((b, i) => (
                      <fieldset key={i}>
                        <legend>
                          {b.id} · {roles[b.role]}
                        </legend>
                        <div className="form-columns">
                          <Field label="剧情职责">
                            <select
                              value={b.role}
                              onChange={(e) =>
                                change({
                                  ...plan,
                                  beats: plan.beats.map((x, n) =>
                                    n === i
                                      ? { ...x, role: e.target.value }
                                      : x,
                                  ),
                                })
                              }
                            >
                              {Object.entries(roles).map(([v, l]) => (
                                <option key={v} value={v}>
                                  {l}
                                </option>
                              ))}
                            </select>
                          </Field>
                          <Field label="原因来自哪一拍">
                            <select
                              value={b.cause_id || ""}
                              onChange={(e) =>
                                change({
                                  ...plan,
                                  beats: plan.beats.map((x, n) =>
                                    n === i
                                      ? {
                                          ...x,
                                          cause_id: e.target.value || null,
                                        }
                                      : x,
                                  ),
                                })
                              }
                            >
                              <option value="">开场无需前因</option>
                              {plan.beats.slice(0, i).map((x) => (
                                <option key={x.id}>{x.id}</option>
                              ))}
                            </select>
                          </Field>
                          <Field label="行动人物">
                            <select
                              value={b.character_id}
                              onChange={(e) =>
                                change({
                                  ...plan,
                                  beats: plan.beats.map((x, n) =>
                                    n === i
                                      ? { ...x, character_id: e.target.value }
                                      : x,
                                  ),
                                })
                              }
                            >
                              {plan.characters.map((c) => (
                                <option key={c.id} value={c.id}>
                                  {c.name || c.id}
                                </option>
                              ))}
                            </select>
                          </Field>
                        </div>
                        {(
                          [
                            ["action", "这一拍做了什么"],
                            ["obstacle", "具体障碍"],
                            ["result", "后果 / 下一拍为什么发生"],
                          ] as const
                        ).map(([k, label]) => (
                          <div key={k}>
                            {text(label, b[k], (v) =>
                              change({
                                ...plan,
                                beats: plan.beats.map((x, n) =>
                                  n === i ? { ...x, [k]: v } : x,
                                ),
                              }),
                            )}
                          </div>
                        ))}
                      </fieldset>
                    ))}
                    <Button
                      variant="secondary"
                      disabled={plan.beats.length >= 12}
                      onClick={() => {
                        const i = plan.beats.length + 1;
                        change({
                          ...plan,
                          beats: [
                            ...plan.beats,
                            {
                              id: `B${i}`,
                              cause_id: i === 1 ? null : `B${i - 1}`,
                              character_id: plan.characters[0].id,
                              role: i === 1 ? "hook" : "setup",
                              action: "",
                              obstacle: "",
                              result: "",
                            },
                          ],
                          shots: [...plan.shots, blankShot(i)],
                        });
                      }}
                    >
                      增加节拍和对应镜头
                    </Button>
                  </div>
                </Card>
              )}
              {step === 2 && (
                <Card>
                  <h2>镜头覆盖与参考首帧</h2>
                  <p className="muted">
                    单镜2–5秒。先在素材库准备同一角色、同一场景和对应景别的高清首帧；仅换提示词不能保证人物一致。源图横屏至少1280×704，竖屏至少704×1280。
                  </p>
                  <Link href="/studio/assets">打开素材库</Link>
                  <div className="form-stack">
                    {plan.shots.map((s, i) => (
                      <fieldset key={i}>
                        <legend>
                          {s.id} → {s.beat_id} · {s.frames / 24}秒
                        </legend>
                        <Field label="场景">
                          <select
                            value={s.scene_id}
                            onChange={(e) =>
                              editShot(i, { scene_id: e.target.value })
                            }
                          >
                            {plan.scenes.map((x) => (
                              <option value={x.id} key={x.id}>
                                {x.name || x.id}
                              </option>
                            ))}
                          </select>
                        </Field>
                        <div className="form-columns">
                          <Field label="景别">
                            <select
                              value={s.framing}
                              onChange={(e) =>
                                editShot(i, { framing: e.target.value })
                              }
                            >
                              {[
                                ["wide", "全景"],
                                ["medium", "中景"],
                                ["close", "特写"],
                                ["insert", "细节插入"],
                              ].map(([v, l]) => (
                                <option key={v} value={v}>
                                  {l}
                                </option>
                              ))}
                            </select>
                          </Field>
                          <Field label="源片时长">
                            <select
                              value={s.frames}
                              onChange={(e) =>
                                editShot(i, { frames: Number(e.target.value) })
                              }
                            >
                              {[49, 73, 97, 121].map((n) => (
                                <option key={n} value={n}>
                                  {(n / 24).toFixed(2)}秒
                                </option>
                              ))}
                            </select>
                          </Field>
                        </div>
                        {(
                          [
                            ["action", "画面行动"],
                            ["frame_prompt", "首帧构图"],
                            ["motion_prompt", "具体动作"],
                            ["camera", "摄影机运动"],
                            ["narration", "准确画外音（留空则静默）"],
                            ["delivery", "声音表演提示"],
                            [
                              "transition_reason",
                              "走位变化 / 转场理由（有变化必填）",
                            ],
                          ] as const
                        ).map(([k, label]) => (
                          <div key={k}>
                            {text(
                              label,
                              s[k],
                              (v) => editShot(i, { [k]: v }),
                              k === "frame_prompt" || k === "motion_prompt",
                            )}
                          </div>
                        ))}
                        <fieldset>
                          <legend>人物站位（画面坐标）</legend>
                          {plan.characters.map((c) => {
                            const present = s.character_ids.includes(c.id);
                            return (
                              <div key={c.id}>
                                <label className="check-row">
                                  <input
                                    type="checkbox"
                                    checked={present}
                                    onChange={(e) => {
                                      const ids = e.target.checked
                                        ? [...s.character_ids, c.id]
                                        : s.character_ids.filter(
                                            (x) => x !== c.id,
                                          );
                                      editShot(i, {
                                        character_ids: ids,
                                        start_positions: Object.fromEntries(
                                          ids.map((id) => [
                                            id,
                                            s.start_positions[id] || "left",
                                          ]),
                                        ),
                                        end_positions: Object.fromEntries(
                                          ids.map((id) => [
                                            id,
                                            s.end_positions[id] || "left",
                                          ]),
                                        ),
                                      });
                                    }}
                                  />
                                  {c.name || c.id}出镜
                                </label>
                                {present && (
                                  <div className="form-columns">
                                    {(
                                      [
                                        "start_positions",
                                        "end_positions",
                                      ] as const
                                    ).map((k) => (
                                      <Field
                                        label={
                                          k === "start_positions"
                                            ? "起始位置"
                                            : "结束位置"
                                        }
                                        key={k}
                                      >
                                        <select
                                          value={s[k][c.id]}
                                          onChange={(e) =>
                                            editShot(i, {
                                              [k]: {
                                                ...s[k],
                                                [c.id]: e.target.value,
                                              },
                                            })
                                          }
                                        >
                                          {[
                                            ["left", "左"],
                                            ["center", "中"],
                                            ["right", "右"],
                                            ["offscreen", "画外"],
                                          ].map(([v, l]) => (
                                            <option value={v} key={v}>
                                              {l}
                                            </option>
                                          ))}
                                        </select>
                                      </Field>
                                    ))}
                                  </div>
                                )}
                              </div>
                            );
                          })}
                        </fieldset>
                        <Field label="已核实的高清首帧">
                          <select
                            value={s.reference_asset_id || ""}
                            onChange={(e) =>
                              editShot(i, {
                                reference_asset_id: e.target.value || null,
                              })
                            }
                          >
                            <option value="">先准备对应构图的角色参考图</option>
                            {images.map((a) => (
                              <option key={a.id} value={a.id}>
                                {a.name}
                              </option>
                            ))}
                          </select>
                        </Field>
                      </fieldset>
                    ))}
                  </div>
                </Card>
              )}
              <div className="toolbar">
                <Button
                  disabled={busy || !dirty}
                  onClick={() =>
                    void action(async () => {
                      const result = await api<Project>(uri + "/plan", {
                        method: "PUT",
                        body: JSON.stringify({
                          expected_revision: project.revision,
                          document: plan,
                        }),
                      });
                      dirtyRef.current = false;
                      setDirty(false);
                      setProject(result);
                      setPlan(result.plan as Plan);
                      version.current = result.revision;
                      await list();
                    }, "计划已保存并执行检查")
                  }
                >
                  保存并检查全部计划
                </Button>
                <Badge
                  tone={dirty ? "warning" : locked ? "success" : "neutral"}
                >
                  {dirty
                    ? "待保存"
                    : locked
                      ? "已确认当前计划"
                      : "待检查与确认"}
                </Badge>
              </div>
              {step === 3 && (
                <>
                  <Card>
                    <h2>检查与人工确认</h2>
                    {plan.uncertainties.length > 0 && (
                      <>
                        <h3>尚需核对的制作条件</h3>
                        {plan.uncertainties.map((u, i) => (
                          <p key={i}>{u}</p>
                        ))}
                        <p className="muted">
                          这些说明不是已核实事实。真实软件界面需在后续编辑器插入授权录屏，不能由情景生成画面冒充。
                        </p>
                      </>
                    )}
                    {!project.report.issues && (
                      <p>先保存计划，运行结构与剧本检查。</p>
                    )}
                    {project.report.issues?.length === 0 && (
                      <p>
                        结构检查未发现阻断项。剧情是否自然、有趣仍需你审看。
                      </p>
                    )}
                    {project.report.issues?.map((x, i) => (
                      <p role="alert" key={i}>
                        <strong>{x.location}</strong>：{x.message}
                      </p>
                    ))}
                    {project.report.human_checks?.map((x) => (
                      <p key={x}>□ {x}</p>
                    ))}
                    <Field label="核对意见">
                      <textarea
                        value={note}
                        onChange={(e) => setNote(e.target.value)}
                        minLength={5}
                        maxLength={1000}
                      />
                    </Field>
                    <Button
                      disabled={
                        busy ||
                        dirty ||
                        !project.report.issues ||
                        project.report.issues.length > 0 ||
                        note.trim().length < 5
                      }
                      onClick={() =>
                        void action(async () => {
                          await api(
                            uri + "/confirm",
                            post({
                              expected_revision: project.revision,
                              confirmed: true,
                              note,
                            }),
                          );
                          await load(project.id);
                        }, "当前计划已记录人工确认")
                      }
                    >
                      确认故事与分镜
                    </Button>
                    {project.stale && (
                      <p role="alert">
                        来源或技能版本已变化，请重新保存、检查和确认。
                      </p>
                    )}
                  </Card>
                  <Card>
                    <h2>逐镜生成与审看</h2>
                    <p>
                      本机生成单镜约需数十分钟，以实际任务为准。先审看一个镜头再继续；本流程不提供口型同步，旁白在剪辑阶段制作。
                    </p>
                    {plan.shots.map((s) => {
                      const job = jobs.find(
                        (j) => j.id === project.bindings[s.id],
                      );
                      return (
                        <div className="card" key={s.id}>
                          <h3>
                            {s.id} · {s.action}
                          </h3>
                          <p>
                            {job
                              ? `任务状态：${job.status} · ${job.receipt?.art_review === "user_confirmed" ? "用户已审看" : "待画面审看"}`
                              : "尚未生成"}
                          </p>
                          {job?.error_message && (
                            <p role="alert">{job.error_message}</p>
                          )}
                          <Button
                            variant="secondary"
                            disabled={busy || !locked}
                            onClick={() =>
                              void action(async () => {
                                const body = await api<Record<string, unknown>>(
                                  `${uri}/shots/${s.id}/request`,
                                );
                                setRequest({
                                  shot: s.id,
                                  body,
                                  takeKey: crypto.randomUUID(),
                                  canRetake:
                                    !!job &&
                                    [
                                      "completed",
                                      "failed",
                                      "cancelled",
                                    ].includes(job.status),
                                });
                              })
                            }
                          >
                            查看本镜生成参数
                          </Button>
                          {job && (
                            <Link href="/studio/video/ai">
                              打开片段审看与质量确认
                            </Link>
                          )}
                        </div>
                      );
                    })}
                    {request && (
                      <form
                        className="form-stack"
                        onSubmit={(e) => {
                          e.preventDefault();
                          const retake =
                            new FormData(e.currentTarget).get("retake") ===
                            "on";
                          void action(async () => {
                            await api(
                              `${uri}/shots/${request.shot}/generate`,
                              post({
                                expected_revision: project.revision,
                                confirmed: true,
                                take_key: retake ? request.takeKey : null,
                              }),
                            );
                            setRequest(undefined);
                            await load(project.id);
                          }, "此镜头已排队，重复请求复用原任务");
                        }}
                      >
                        <h3>{request.shot} · 本次仅生成1镜</h3>
                        {request.canRetake && (
                          <label className="check-row">
                            <input type="checkbox" name="retake" />
                            重新拍摄本镜头（保留旧片段，仅替换本镜绑定）
                          </label>
                        )}
                        <p>
                          {String(request.body.width)}×
                          {String(request.body.height)} ·{" "}
                          {(Number(request.body.frames) / 24).toFixed(2)}秒 ·
                          本机 Wan 2.2
                        </p>
                        <p
                          style={{
                            whiteSpace: "pre-wrap",
                            overflowWrap: "anywhere",
                          }}
                        >
                          {String(request.body.prompt)}
                        </p>
                        <label className="check-row">
                          <input type="checkbox" required />
                          已核对参考图、动作、站位与以上参数，同意开始本镜生成
                        </label>
                        <Button disabled={busy || !locked}>
                          确认生成这一镜
                        </Button>
                      </form>
                    )}
                  </Card>
                  <Card>
                    <h2>配音、字幕与预览</h2>
                    <p>
                      全部镜头完成并在动态镜头页逐镜确认后，按剧本顺序剪辑。固定时长配音不会用长停帧补足台词；超长需缩短台词后重做。
                    </p>
                    <label className="check-row">
                      <input
                        type="checkbox"
                        checked={withVoice}
                        onChange={(e) => setWithVoice(e.target.checked)}
                      />
                      制作本机画外音与字幕
                    </label>
                    {withVoice && (
                      <VoiceControls
                        value={voice}
                        onChange={(v) => setVoice({ ...v, fit_mode: "fixed" })}
                        disabled={busy}
                      />
                    )}
                    <p className="muted">
                      当前使用一个选定的画外音声音；角色声音方向已保存，逐角色自动配音与人物对口型尚未接入。
                    </p>
                    <Button
                      disabled={
                        busy ||
                        !locked ||
                        (withVoice &&
                          (!voice.voice_id || !voice.usage_confirmed))
                      }
                      onClick={() =>
                        void action(async () => {
                          const result = await api<{ video_id: string }>(
                            uri + "/build",
                            post({
                              expected_revision: project.revision,
                              confirmed: true,
                              narration: withVoice
                                ? { ...voice, fit_mode: "fixed" }
                                : null,
                            }),
                          );
                          router.push(`/studio/video/${result.video_id}`);
                        }, "已建立短剧工程并排队预览")
                      }
                    >
                      按当前剧本制作预览
                    </Button>
                  </Card>
                </>
              )}
              <details className="card">
                <summary>计划 JSON 与历史修订（高级）</summary>
                <p>
                  可复制当前计划备份。载入历史修订后需重新保存、检查和确认。
                </p>
                <textarea
                  aria-label="短剧计划JSON"
                  key={project.revision}
                  value={JSON.stringify(plan, null, 2)}
                  readOnly
                  rows={10}
                  style={{ width: "100%" }}
                />
                {project.history.map((h) => (
                  <p key={h.revision}>
                    第{h.revision}版{" "}
                    <Button
                      variant="secondary"
                      disabled={busy}
                      onClick={() => change(h.plan)}
                    >
                      载入为待保存草稿
                    </Button>
                  </p>
                ))}
              </details>
            </>
          )}
        </>
      )}
    </>
  );
}
