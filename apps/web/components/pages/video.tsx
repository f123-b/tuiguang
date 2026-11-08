"use client";
import { Badge, Button, Card, EmptyState, StatusBadge } from "@xuliu/ui";
import { Clapperboard, Plus, Sparkles } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { api, post, type Video } from "../../lib/api";
import { Field, PageHeader, type PageProps } from "../page-shared";
import { VideoEditor } from "./video-editor";
import { PresentationControls, defaultPresentation } from "./film-design";
import { VoiceControls, defaultVoiceSettings } from "./narration";
import { DramaStudio } from "./video-drama";
import { DramaSkillsStudio } from "./video-drama-skills";

type Mode = "mg" | "screen_demo" | "montage" | "illustrated" | "mixed";
type Catalog = {
  version: string;
  recipes: { id: string; name: string; roles: string[] }[];
  modes: {
    id: string;
    name: string;
    description: string;
    available: boolean;
  }[];
};
type Scene = {
  headline: string;
  narration: string;
  supporting: string;
  points: string;
  asset_id: string;
  seconds: number;
  start: number;
  treatment: "auto" | "screen" | "montage" | "comic" | "diagram";
};
const emptyScene = (): Scene => ({
  headline: "",
  narration: "",
  supporting: "",
  points: "",
  asset_id: "",
  seconds: 5,
  start: 0,
  treatment: "auto",
});

export function VideoPage(props: PageProps) {
  if (props.path === "/studio/video/drama")
    return <DramaSkillsStudio {...props} />;
  if (props.path === "/studio/video/ai") return <DramaStudio {...props} />;
  const video = props.store.videos.find(
    (v) => v.id === props.path.split("/")[3],
  );
  return video ? (
    <VideoEditor {...props} video={video} />
  ) : (
    <VideoCreate {...props} />
  );
}

export function VideoCreate({ store, action, busy }: PageProps) {
  const router = useRouter();
  const [catalog, setCatalog] = useState<Catalog>();
  const [error, setError] = useState("");
  const [brandId, setBrandId] = useState(store.brands[0]?.id || "");
  const brand = store.brands.find((b) => b.id === brandId) || store.brands[0];
  const [mode, setMode] = useState<Mode>("mg");
  const [recipeId, setRecipeId] = useState("feature");
  const [scenes, setScenes] = useState<Scene[]>(() =>
    Array.from({ length: 4 }, emptyScene),
  );
  const [presentation, setPresentation] = useState(defaultPresentation);
  const [withVoice, setWithVoice] = useState(true);
  const [voice, setVoice] = useState(defaultVoiceSettings);
  const submission = useRef<{ body: string; key: string } | null>(null);
  useEffect(() => {
    api<Catalog>("/videos/recipes")
      .then(setCatalog)
      .catch((e) => setError(e.message));
  }, []);
  const assets = store.assets.filter(
    (a) =>
      a.verified &&
      a.kind !== "audio" &&
      a.brand_id === brand?.id &&
      a.applicability_status === "current",
  );
  const roles = catalog?.recipes.find((r) => r.id === recipeId)?.roles || [];
  const patch = (index: number, value: Partial<Scene>) =>
    setScenes((old) =>
      old.map((s, i) => (i === index ? { ...s, ...value } : s)),
    );
  const total = scenes.reduce((n, s) => n + s.seconds, 0);
  return (
    <>
      <PageHeader
        eyebrow="VIDEO STUDIO"
        title="选一种形式，讲好这条内容"
        description="从真实内容和逐镜素材开始，制作配音、字幕与可审看的视频。"
      >
        <Link className="button secondary" href="/studio/briefs/new">
          先让 AI 帮我写主题与脚本
        </Link>
        <Link className="button secondary" href="/studio/assets">
          准备授权素材
        </Link>
      </PageHeader>
      {error && <p role="alert">{error}</p>}
      {!catalog && !error && <p role="status">正在读取本机制作能力…</p>}
      <div className="video-mode-grid">
        {catalog?.modes.map((item) => (
          <button
            key={item.id}
            type="button"
            className={`mode-card ${mode === item.id ? "selected" : ""}`}
            disabled={!item.available || busy}
            aria-pressed={mode === item.id}
            onClick={() =>
              item.id === "generative"
                ? router.push("/studio/video/drama")
                : setMode(item.id as Mode)
            }
          >
            <Clapperboard size={24} />
            <strong>{item.name}</strong>
            <p>{item.description}</p>
            <Badge tone={item.available ? "success" : "neutral"}>
              {item.available ? "本地可制作" : "待接入"}
            </Badge>
          </button>
        ))}
      </div>
      <div className="form-columns">
        <Card>
          <h2>内容与分镜</h2>
          {brand ? (
            <form
              className="form-stack"
              onSubmit={(event) => {
                event.preventDefault();
                const fields = new FormData(event.currentTarget);
                const body = JSON.stringify({
                  brand_id: brand.id,
                  name: fields.get("name"),
                  mode,
                  recipe_id: recipeId,
                  size: fields.get("size"),
                  presentation: {
                    ...presentation,
                    style: "studio",
                    brand_label:
                      presentation.brand_label || brand.name.slice(0, 40),
                  },
                  scenes: scenes.map((s) => ({
                    headline: s.headline,
                    narration: s.narration,
                    supporting: s.supporting,
                    points: s.points
                      .split("\n")
                      .map((p) => p.trim())
                      .filter(Boolean),
                    asset_id: mode === "mg" ? null : s.asset_id || null,
                    duration_frames: Math.round(s.seconds * 30),
                    trim_start_frame: Math.round(s.start * 30),
                    treatment: s.treatment,
                  })),
                  ...(withVoice ? { narration: voice } : {}),
                });
                if (submission.current?.body !== body)
                  submission.current = { body, key: crypto.randomUUID() };
                const key = submission.current.key;
                action(
                  async () => {
                    const video = await api<Video>("/videos/from-recipe", {
                      ...post(),
                      body,
                      headers: { "Idempotency-Key": key },
                    });
                    router.push(`/studio/video/${video.id}`);
                  },
                  withVoice
                    ? "工程已创建，正在制作配音和预览"
                    : "工程已创建，正在合成无旁白预览",
                );
              }}
            >
              <div className="form-grid">
                <Field label="品牌">
                  <select
                    value={brand.id}
                    onChange={(e) => {
                      setBrandId(e.target.value);
                      setScenes((old) =>
                        old.map((s) => ({ ...s, asset_id: "" })),
                      );
                    }}
                  >
                    {store.brands.map((b) => (
                      <option key={b.id} value={b.id}>
                        {b.name}
                      </option>
                    ))}
                  </select>
                </Field>
                <Field label="内容结构">
                  <select
                    value={recipeId}
                    onChange={(e) => setRecipeId(e.target.value)}
                  >
                    {catalog?.recipes.map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.name}
                      </option>
                    ))}
                  </select>
                </Field>
              </div>
              <Field label="项目名称">
                <input
                  name="name"
                  required
                  maxLength={120}
                  placeholder={`${brand.name} · 新视频`}
                />
              </Field>
              <div className="form-grid">
                <Field label="画面比例">
                  <select name="size">
                    <option value="wide">横屏 · 16:9</option>
                    <option value="portrait">竖屏 · 9:16</option>
                    <option value="square">方形 · 1:1</option>
                  </select>
                </Field>
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() =>
                    setMode(
                      assets.length >= 2
                        ? "mixed"
                        : assets.length
                          ? "screen_demo"
                          : "mg",
                    )
                  }
                >
                  <Sparkles size={15} />
                  按素材推荐形式
                </Button>
              </div>
              {recipeId === "release" && (
                <p className="muted">
                  请在分镜中注明实际版本与来源；规划中的功能不能当作已上线能力。
                </p>
              )}
              {recipeId === "story" && (
                <p className="muted">
                  虚构情节请在文案中标注“情景演绎”，实际用户经历须有授权和依据。
                </p>
              )}
              {mode === "mixed" && (
                <p className="muted">
                  至少保留一镜图解和一镜素材；逐镜选择实录、全画幅混剪或插画分镜。
                </p>
              )}
              {mode === "illustrated" && (
                <p className="muted">
                  使用你已授权的插画，添加镜头运动与对白。这一形式不会生成角色动作或口型。
                </p>
              )}
              {scenes.map((scene, i) => {
                const textOnly =
                  mode === "mg" || (mode === "mixed" && !scene.asset_id);
                return (
                  <fieldset
                    className="form-stack film-controls"
                    key={i}
                    disabled={busy}
                  >
                    <legend>
                      镜头 {i + 1} ·{" "}
                      {roles[Math.min(i, roles.length - 1)] || "补充镜头"}
                    </legend>
                    <Field label={`镜头 ${i + 1} 画面短句`}>
                      <input
                        required
                        maxLength={80}
                        value={scene.headline}
                        onChange={(e) => patch(i, { headline: e.target.value })}
                        placeholder="这一镜让观众看见什么"
                      />
                    </Field>
                    <Field label={`镜头 ${i + 1} 旁白`}>
                      <textarea
                        rows={2}
                        maxLength={600}
                        value={scene.narration}
                        onChange={(e) =>
                          patch(i, { narration: e.target.value })
                        }
                        placeholder="写自然说话的句子；留空时用画面短句配音"
                      />
                    </Field>
                    <Field label={`镜头 ${i + 1} 补充文字`}>
                      <textarea
                        rows={2}
                        maxLength={240}
                        value={scene.supporting}
                        onChange={(e) =>
                          patch(i, { supporting: e.target.value })
                        }
                      />
                    </Field>
                    {mode !== "mg" && (
                      <Field label={`镜头 ${i + 1} 授权素材`}>
                        <select
                          required={mode !== "mixed"}
                          value={scene.asset_id}
                          onChange={(e) =>
                            patch(i, { asset_id: e.target.value })
                          }
                        >
                          <option value="">
                            {mode === "mixed" ? "图解 / 动态文字" : "选择素材"}
                          </option>
                          {assets
                            .filter(
                              (a) =>
                                mode !== "illustrated" || a.kind === "image",
                            )
                            .map((a) => (
                              <option key={a.id} value={a.id}>
                                {a.name} ·{" "}
                                {a.kind === "video" ? "视频" : "图片"}
                              </option>
                            ))}
                        </select>
                      </Field>
                    )}
                    {mode === "mixed" && scene.asset_id && (
                      <Field label={`镜头 ${i + 1} 素材呈现`}>
                        <select
                          value={scene.treatment}
                          onChange={(e) =>
                            patch(i, {
                              treatment: e.target.value as Scene["treatment"],
                            })
                          }
                        >
                          <option value="auto">全画幅混剪</option>
                          <option value="screen">真实界面讲解</option>
                          <option value="montage">全画幅素材</option>
                          <option value="comic">插画分镜（图片）</option>
                        </select>
                      </Field>
                    )}
                    {textOnly && (
                      <Field
                        label={`镜头 ${i + 1} 图解节点（每行一项，最多三项）`}
                      >
                        <textarea
                          rows={3}
                          value={scene.points}
                          onChange={(e) => patch(i, { points: e.target.value })}
                          placeholder="只写有依据的步骤、关系或信息；没有数据不画假图表"
                        />
                      </Field>
                    )}
                    <div className="form-grid">
                      <Field label={`镜头 ${i + 1} 时长（秒）`}>
                        <input
                          type="number"
                          min={0.5}
                          max={60}
                          step={0.1}
                          required
                          value={scene.seconds}
                          onChange={(e) =>
                            patch(i, { seconds: Number(e.target.value) })
                          }
                        />
                      </Field>
                      {!textOnly && (
                        <Field label={`镜头 ${i + 1} 素材入点（秒）`}>
                          <input
                            type="number"
                            min={0}
                            max={7200}
                            step={0.1}
                            required
                            value={scene.start}
                            onChange={(e) =>
                              patch(i, { start: Number(e.target.value) })
                            }
                          />
                        </Field>
                      )}
                    </div>
                    <div className="inline-actions">
                      <Button
                        type="button"
                        variant="secondary"
                        disabled={i === 0}
                        onClick={() =>
                          setScenes((old) => {
                            const next = [...old];
                            [next[i - 1], next[i]] = [next[i], next[i - 1]];
                            return next;
                          })
                        }
                      >
                        前移
                      </Button>
                      <Button
                        type="button"
                        variant="secondary"
                        disabled={scenes.length <= 2}
                        onClick={() =>
                          setScenes((old) =>
                            old.filter((_, index) => index !== i),
                          )
                        }
                      >
                        删除这一镜
                      </Button>
                    </div>
                  </fieldset>
                );
              })}
              <Button
                type="button"
                variant="secondary"
                disabled={scenes.length >= 12 || busy}
                onClick={() => setScenes((old) => [...old, emptyScene()])}
              >
                <Plus size={16} />
                添加镜头
              </Button>
              <p className="muted">
                当前 {scenes.length} 镜 · {total.toFixed(1)} 秒。制作上限 120
                秒；配音自动延长后仍受此限制。短录屏会提示修改入点或时长。
              </p>
              <PresentationControls
                fixedStudio
                value={{ ...presentation, style: "studio" }}
                onChange={(v) => setPresentation({ ...v, style: "studio" })}
              />
              <label className="checkline">
                <input
                  type="checkbox"
                  checked={withVoice}
                  onChange={(e) => setWithVoice(e.target.checked)}
                />
                同时制作本机配音与同步字幕
              </label>
              {withVoice && (
                <VoiceControls
                  value={voice}
                  onChange={setVoice}
                  disabled={busy}
                />
              )}
              {!withVoice && (
                <p className="muted">
                  本次先生成无旁白预览，可在工程内继续配音和添加授权音乐。
                </p>
              )}
              <p className="muted">
                不调用付费视频接口。素材与声音许可由你核实；先审看带水印预览，再确认高清合成。
              </p>
              <Button
                disabled={
                  busy ||
                  !catalog ||
                  !catalog.modes.find((m) => m.id === mode)?.available ||
                  total > 120 ||
                  (withVoice && (!voice.voice_id || !voice.usage_confirmed))
                }
                type="submit"
              >
                创建并制作预览
              </Button>
            </form>
          ) : (
            <EmptyState
              title="先添加品牌"
              description="视频需要关联你的产品资料。"
              action={
                <Link className="button" href="/brand">
                  添加品牌
                </Link>
              }
            />
          )}
        </Card>
        <Card>
          <h2>我的视频项目</h2>
          {store.videos.length ? (
            <div className="project-list">
              {store.videos.map((v) => (
                <Link href={`/studio/video/${v.id}`} key={v.id}>
                  <span className="project-thumb">
                    <Clapperboard size={22} />
                  </span>
                  <div>
                    <strong>{v.name}</strong>
                    <p>
                      {v.ir.width} × {v.ir.height} · {v.ir.shots.length} 镜
                    </p>
                    <StatusBadge status={v.status} />
                  </div>
                </Link>
              ))}
            </div>
          ) : (
            <EmptyState
              title="第一条视频，从分镜开始"
              description="选择形式，填写内容，生成真实可播放的预览。"
            />
          )}
        </Card>
      </div>
    </>
  );
}
