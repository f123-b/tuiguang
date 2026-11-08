"use client";
import { Button, Card, Badge } from "@xuliu/ui";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { api, post, type Asset, type Video } from "../../lib/api";
import { Field, PageHeader, type PageProps } from "../page-shared";
import { VoiceControls, defaultVoiceSettings } from "./narration";

type Capability = {
  available: boolean;
  reason: string | null;
  version: string;
};
type Job = {
  id: string;
  brand_id: string;
  status: string;
  stage: string;
  error_message: string | null;
  provider_request_id: string | null;
  output_asset?: Asset;
  document: { prompt: string; style: string; frames: number; seed: number };
  receipt: { duration_sec?: number; output_sha256?: string };
};
const stateName: Record<string, string> = {
  queued: "排队中",
  submitting: "正在提交",
  running: "正在生成",
  completed: "片段已完成",
  failed: "生成失败",
  unknown: "状态待检查",
  cancelled: "已取消",
};

export function DramaStudio({ store, action, busy }: PageProps) {
  const router = useRouter();
  const [capability, setCapability] = useState<Capability>();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [error, setError] = useState("");
  const [brandId, setBrandId] = useState(store.brands[0]?.id || "");
  const [style, setStyle] = useState("realistic");
  const [reference, setReference] = useState("");
  const [selected, setSelected] = useState<string[]>([]);
  const [lines, setLines] = useState<
    Record<string, { headline: string; narration: string }>
  >({});
  const [withVoice, setWithVoice] = useState(false);
  const [voice, setVoice] = useState(defaultVoiceSettings);
  const submission = useRef<{ body: string; key: string } | null>(null);
  const filmSubmission = useRef<{ body: string; key: string } | null>(null);
  const refresh = useCallback(async () => {
    const result = await api<Job[]>("/video-generation/jobs");
    setJobs(result);
  }, []);
  useEffect(() => {
    let active = true;
    api<Capability>("/video-generation/capabilities")
      .then((value) => {
        if (active) setCapability(value);
      })
      .catch((e) => {
        if (active) setError(e.message);
      });
    const poll = () =>
      refresh().catch((e) => {
        if (active) setError(e.message);
      });
    void poll();
    const timer = setInterval(poll, 10000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [refresh]);
  const images = store.assets.filter(
    (a) =>
      a.brand_id === brandId &&
      a.kind === "image" &&
      a.verified &&
      a.applicability_status === "current",
  );
  const visible = jobs.filter((j) => j.brand_id === brandId);
  return (
    <>
      <PageHeader
        eyebrow="AI SHORT DRAMA"
        title="AI 动态短剧"
        description="先生成角色动作，逐镜检查，再配音剪辑。真人、动漫共用一套分镜流程。"
      >
        <Link className="button secondary" href="/studio/video/drama">
          从故事开始制作短剧
        </Link>
        <Link className="button secondary" href="/studio/video/new">
          其他视频形式
        </Link>
        <Link className="button secondary" href="/studio/assets">
          准备角色参考图
        </Link>
      </PageHeader>
      {error && <p role="alert">{error}</p>}
      <Card>
        <Badge tone={capability?.available ? "success" : "neutral"}>
          {capability?.available ? "本机 Wan 2.2 已连接" : "本机生成服务待就绪"}
        </Badge>
        <p>
          {capability?.reason ||
            "每次生成 2–5 秒无声动态画面；旁白在剪辑阶段制作，当前不提供人物对口型。"}
        </p>
        <p className="muted">
          参考图决定角色与画风。跨镜头人物一致性、动作和细节需逐镜检查。生成画面不能当作真实产品实录；成本为本机算力，无外部付费接口。
        </p>
      </Card>
      <div className="form-columns">
        <Card>
          <h2>1. 编排一个动态镜头</h2>
          <form
            className="form-stack"
            onSubmit={(e) => {
              e.preventDefault();
              const form = new FormData(e.currentTarget);
              const [width, height] = String(form.get("size"))
                .split("x")
                .map(Number);
              const body = JSON.stringify({
                brand_id: brandId,
                reference_asset_id: reference,
                style,
                prompt: form.get("prompt"),
                seed: Number(form.get("seed")),
                width,
                height,
                frames: Number(form.get("frames")),
                usage_confirmed: form.get("consent") === "on",
              });
              if (submission.current?.body !== body)
                submission.current = { body, key: crypto.randomUUID() };
              const key = submission.current.key;
              void action(async () => {
                await api("/video-generation/jobs", {
                  ...post(),
                  body,
                  headers: { "Idempotency-Key": key },
                });
                await refresh();
              }, "镜头已进入本机生成队列");
            }}
          >
            <Field label="品牌">
              <select
                value={brandId}
                onChange={(e) => {
                  setBrandId(e.target.value);
                  setReference("");
                  setSelected([]);
                }}
                required
              >
                {store.brands.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.name}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="角色与画面风格">
              <select value={style} onChange={(e) => setStyle(e.target.value)}>
                <option value="realistic">真人剧情</option>
                <option value="anime">动漫剧情</option>
              </select>
            </Field>
            <Field
              label="角色首帧参考图"
              hint="请先在素材页上传并确认用途；建议同一角色持续复用同组参考图。"
            >
              <select
                value={reference}
                onChange={(e) => setReference(e.target.value)}
                required
              >
                <option value="">选择已核实的图片</option>
                {images.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name}
                  </option>
                ))}
              </select>
            </Field>
            <Field
              label="这一镜发生什么"
              hint="写清人物、动作起点与终点、情绪和机位；单镜只安排一个短动作。中文或英文均可。"
            >
              <textarea
                name="prompt"
                minLength={10}
                maxLength={1600}
                rows={5}
                required
                placeholder="雨夜书桌前，她低头看笔记，轻轻放下笔，再抬眼露出释然的微笑。固定中景，暖台灯，无口播。"
              />
            </Field>
            <div className="form-grid">
              <Field label="画面尺寸">
                <select name="size">
                  <option value="1280x704">横屏 · 1280 × 704（较慢）</option>
                  <option value="704x1280">竖屏 · 704 × 1280（较慢）</option>
                  <option value="896x896">方形 · 896 × 896（较慢）</option>
                  <option value="512x288">
                    低清试算 · 512 × 288（不作出片）
                  </option>
                </select>
              </Field>
              <Field label="时长">
                <select name="frames">
                  <option value="121">约 5 秒</option>
                  <option value="49">约 2 秒</option>
                  <option value="73">约 3 秒</option>
                  <option value="97">约 4 秒</option>
                </select>
              </Field>
            </div>
            <p className="muted">
              本机高分辨率生成可能耗时较长；先验证一个简单动作，检查稳定性后再批量生成。不要用低清试算放大冒充高清。
            </p>
            <Field
              label="随机种子"
              hint="更换种子可制作新版本；种子相同也不保证逐像素复现。"
            >
              <input
                type="number"
                name="seed"
                defaultValue={37}
                min={0}
                max={4294967295}
                required
              />
            </Field>
            <label className="checkbox-row">
              <input type="checkbox" name="consent" required />
              我有权使用参考图及人物形象，且会检查生成内容与用途
            </label>
            <Button
              type="submit"
              disabled={busy || !capability?.available || !reference}
            >
              生成这个镜头
            </Button>
          </form>
        </Card>
        <Card>
          <h2>2. 检查片段与选择顺序</h2>
          {!visible.length && (
            <p>生成后在这里查看片段。多个镜头按勾选顺序进入短剧。</p>
          )}
          {visible.map((job) => (
            <article
              key={job.id}
              className="form-stack"
              style={{
                borderBottom: "1px solid var(--border)",
                padding: "20px 0",
              }}
            >
              <div>
                <Badge>
                  {job.document.style === "anime" ? "动漫" : "真人"}
                </Badge>{" "}
                {stateName[job.status] || job.status} · {job.id.slice(0, 8)}
              </div>
              <p style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>
                {job.document.prompt}
              </p>
              {job.error_message && <p role="alert">{job.error_message}</p>}
              {job.status === "queued" && (
                <Button
                  variant="secondary"
                  disabled={busy}
                  onClick={() =>
                    void action(async () => {
                      await api(
                        `/video-generation/jobs/${job.id}/cancel`,
                        post(),
                      );
                      await refresh();
                    }, "未提交的镜头已取消")
                  }
                >
                  取消排队镜头
                </Button>
              )}
              {job.status === "unknown" && job.provider_request_id && (
                <Button
                  variant="secondary"
                  disabled={busy}
                  onClick={() =>
                    void action(async () => {
                      await api(
                        `/video-generation/jobs/${job.id}/check-existing`,
                        post(),
                      );
                      await refresh();
                    }, "正在检查已有任务，不会重新生成")
                  }
                >
                  读取已有任务结果
                </Button>
              )}
              {job.status === "completed" && (
                <>
                  <video
                    controls
                    preload="metadata"
                    src={`/api/v1/video-generation/jobs/${job.id}/video`}
                    style={{ width: "100%", borderRadius: 12 }}
                  />
                  <small>
                    原生 {job.receipt.duration_sec?.toFixed(2)} 秒 · seed{" "}
                    {job.document.seed} · AI 生成素材
                  </small>
                  {!job.output_asset?.verified ? (
                    <form
                      className="form-stack"
                      onSubmit={(e) => {
                        e.preventDefault();
                        const form = new FormData(e.currentTarget);
                        void action(async () => {
                          await api(
                            `/video-generation/jobs/${job.id}/verify`,
                            post({ confirmed: true, note: form.get("note") }),
                          );
                          await refresh();
                        }, "已记录你的素材检查");
                      }}
                    >
                      <Field
                        label="检查结论"
                        hint="确认脸、手、动作、闪烁及人物使用权；不满意时修改动作或种子生成新镜头。"
                      >
                        <input
                          name="note"
                          minLength={5}
                          maxLength={1000}
                          required
                          placeholder="例如：已检查人物和动作，用于本地内部试片"
                        />
                      </Field>
                      <label className="checkbox-row">
                        <input type="checkbox" required />
                        我已观看并确认该片段可用于本次作品
                      </label>
                      <Button type="submit" variant="secondary" disabled={busy}>
                        确认素材检查
                      </Button>
                    </form>
                  ) : (
                    <>
                      <label className="checkbox-row">
                        <input
                          type="checkbox"
                          checked={selected.includes(job.id)}
                          onChange={(e) =>
                            setSelected((old) =>
                              e.target.checked
                                ? [...old, job.id]
                                : old.filter((id) => id !== job.id),
                            )
                          }
                        />
                        {selected.includes(job.id)
                          ? `第 ${selected.indexOf(job.id) + 1} 镜`
                          : "加入短剧"}
                      </label>
                      <Field label="分镜标题（记录用途，不遮挡人物）">
                        <input
                          maxLength={80}
                          value={lines[job.id]?.headline || ""}
                          placeholder="简短标题，避免挡住人物"
                          onChange={(e) =>
                            setLines((old) => ({
                              ...old,
                              [job.id]: {
                                ...old[job.id],
                                headline: e.target.value,
                              },
                            }))
                          }
                        />
                      </Field>
                      <Field
                        label="旁白或画外音"
                        hint="短镜头适合短句。声音不会驱动人物嘴型。"
                      >
                        <textarea
                          rows={2}
                          maxLength={600}
                          value={lines[job.id]?.narration || ""}
                          onChange={(e) =>
                            setLines((old) => ({
                              ...old,
                              [job.id]: {
                                ...old[job.id],
                                narration: e.target.value,
                              },
                            }))
                          }
                        />
                      </Field>
                    </>
                  )}
                </>
              )}
            </article>
          ))}
        </Card>
      </div>
      <Card>
        <h2>3. 配音与剪辑成片</h2>
        <form
          className="form-stack"
          onSubmit={(e) => {
            e.preventDefault();
            const form = new FormData(e.currentTarget);
            const body = JSON.stringify({
              brand_id: brandId,
              name: form.get("name"),
              mode: "generative",
              recipe_id: "story",
              size: form.get("size"),
              presentation: {
                style: "studio",
                theme: "ink",
                accent: "#B7F56B",
                brand_label: "AI 剧情演绎",
                transition: "clean",
                audio_finish: true,
              },
              scenes: selected.map((id, index) => {
                const job = jobs.find((j) => j.id === id)!;
                return {
                  asset_id: job.output_asset!.id,
                  generation_job_id: id,
                  headline: lines[id]?.headline || `第 ${index + 1} 镜`,
                  narration: lines[id]?.narration || "",
                  duration_frames: Math.floor((job.document.frames / 24) * 30),
                  motion: "still",
                };
              }),
              ...(withVoice ? { narration: voice } : {}),
            });
            if (filmSubmission.current?.body !== body)
              filmSubmission.current = { body, key: crypto.randomUUID() };
            const key = filmSubmission.current.key;
            void action(async () => {
              const video = await api<Video>("/videos/from-recipe", {
                ...post(),
                body,
                headers: { "Idempotency-Key": key },
              });
              router.push(`/studio/video/${video.id}`);
            }, "正在制作短剧预览");
          }}
        >
          <div className="form-grid">
            <Field label="短剧名称">
              <input
                name="name"
                maxLength={120}
                required
                placeholder="那个选择 · AI 短剧试片"
              />
            </Field>
            <Field label="成片画幅">
              <select name="size">
                <option value="wide">横屏</option>
                <option value="portrait">竖屏</option>
                <option value="square">方形</option>
              </select>
            </Field>
          </div>
          <p>
            已选 {selected.length}{" "}
            个镜头。预览通过你的检查后，仍需在视频编辑器确认才能导出高清合成；放大合成不会增加生成画面细节。
          </p>
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={withVoice}
              onChange={(e) => setWithVoice(e.target.checked)}
            />
            制作旁白与字幕
          </label>
          {withVoice && <VoiceControls value={voice} onChange={setVoice} />}
          <Button
            type="submit"
            disabled={busy || selected.length < 1 || selected.length > 12}
          >
            剪辑这 {selected.length} 个镜头
          </Button>
        </form>
      </Card>
    </>
  );
}
