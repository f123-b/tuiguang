"use client";
import { Badge, Button, Card, EmptyState, StatusBadge } from "@xuliu/ui";
import {
  ArrowDownToLine,
  Check,
  ChevronRight,
  Clapperboard,
  FolderOpen,
  Layers,
  Play,
  Plus,
  Sparkles,
  WandSparkles,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { api, post, type Shot, type Video } from "../../lib/api";

import { Field, PageHeader, type PageProps } from "../page-shared";
export function VideoPage(props: PageProps) {
  const { store, path } = props;
  const id = path.split("/")[3];
  const video = store.videos.find((v) => v.id === id);
  return video ? (
    <VideoEditor {...props} video={video} />
  ) : (
    <VideoCreate {...props} />
  );
}

export function VideoCreate({ store, action, busy }: PageProps) {
  const router = useRouter();
  const [mode, setMode] = useState("pillow_mg");
  const brand = store.brands[0];
  const availableAssets = store.assets.filter((a) => a.verified);
  return (
    <>
      <PageHeader
        eyebrow="VIDEO STUDIO"
        title="一个故事，可以有很多种表达"
        description="从动态图形到真实素材，按镜头选择制作方式。当前可运行 MG 与素材混剪两个本地引擎。"
      >
        <Link className="button secondary" href="/studio/assets">
          <FolderOpen size={15} />
          准备素材
        </Link>
      </PageHeader>
      <div className="video-mode-grid">
        {[
          [
            "pillow_mg",
            "2D / MG 动画",
            "动态文字与图形，参数可编辑",
            Sparkles,
            true,
          ],
          [
            "ffmpeg_media",
            "软件实录 / 混剪",
            "真实截图、录屏与授权视频",
            Clapperboard,
            true,
          ],
          ["mixed", "混合制作", "MG + 真实素材，组合你的故事", Layers, true],
          [
            "ai",
            "AI 创意 / 卡通",
            "生成式镜头，待接入模型",
            WandSparkles,
            false,
          ],
          ["3d", "3D / CG 动画", "高级三维引擎，尚未接入", Clapperboard, false],
        ].map(([value, title, desc, Icon, available]) => (
          <button
            key={String(value)}
            className={`mode-card ${mode === value ? "selected" : ""}`}
            disabled={!available}
            onClick={() => setMode(String(value))}
          >
            {typeof Icon === "function" || typeof Icon === "object" ? (
              <Icon size={24} />
            ) : null}
            <strong>{String(title)}</strong>
            <p>{String(desc)}</p>
            <Badge tone={available ? "success" : "neutral"}>
              {available ? "本地可运行" : "待接入"}
            </Badge>
          </button>
        ))}
      </div>
      <div className="form-columns">
        <Card>
          <h2>建立可编辑的视频工程</h2>
          {brand ? (
            <form
              className="form-stack"
              onSubmit={(e) => {
                e.preventDefault();
                const f = new FormData(e.currentTarget);
                const seconds = Number(f.get("duration"));
                const assetId = String(f.get("asset") || "");
                const caption = String(f.get("caption"));
                const frames = seconds * 30;
                const shots =
                  mode === "mixed"
                    ? [
                        {
                          shot_id: "s1",
                          provider: "pillow_mg",
                          kind: "motion_graphics",
                          duration_frames: Math.round(frames / 3),
                          caption,
                          asset_id: null,
                          locked: false,
                        },
                        {
                          shot_id: "s2",
                          provider: "ffmpeg_media",
                          kind: "montage",
                          duration_frames: frames - 2 * Math.round(frames / 3),
                          caption: "真实产品素材",
                          asset_id: assetId,
                          locked: false,
                        },
                        {
                          shot_id: "s3",
                          provider: "pillow_mg",
                          kind: "motion_graphics",
                          duration_frames: Math.round(frames / 3),
                          caption: "了解产品，亲自体验",
                          asset_id: null,
                          locked: false,
                        },
                      ]
                    : [
                        {
                          shot_id: "s1",
                          provider: mode,
                          kind:
                            mode === "pillow_mg"
                              ? "motion_graphics"
                              : "montage",
                          duration_frames: frames,
                          caption,
                          asset_id: mode === "pillow_mg" ? null : assetId,
                          locked: false,
                        },
                      ];
                action(async () => {
                  const video = await api<Video>(
                    "/videos/projects",
                    post({
                      brand_id: brand.id,
                      name: f.get("name"),
                      width: Number(f.get("width")),
                      height: Number(f.get("width")) === 1920 ? 1080 : 1920,
                      fps: 30,
                      shots,
                    }),
                  );
                  router.push(`/studio/video/${video.id}`);
                }, "视频工程已保存");
              }}
            >
              <Field label="项目名称">
                <input
                  name="name"
                  required
                  maxLength={120}
                  placeholder={`${brand.name} · 产品宣传片`}
                />
              </Field>
              <Field label="开场文案">
                <textarea
                  name="caption"
                  rows={2}
                  required
                  maxLength={180}
                  placeholder="写下你想讲述的真实产品信息"
                />
              </Field>
              <div className="form-grid">
                <Field label="画面比例">
                  <select name="width">
                    <option value="1920">16:9 · 1920 × 1080</option>
                    <option value="1080">9:16 · 1080 × 1920</option>
                  </select>
                </Field>
                <Field label="视频时长">
                  <select name="duration">
                    <option value="20">20 秒</option>
                    <option value="30">30 秒</option>
                    <option value="15">15 秒</option>
                  </select>
                </Field>
              </div>
              {mode !== "pillow_mg" && (
                <Field label="已确认授权的素材">
                  <select name="asset" required>
                    <option value="">选择真实素材</option>
                    {availableAssets.map((a) => (
                      <option value={a.id} key={a.id}>
                        {a.name}
                      </option>
                    ))}
                  </select>
                </Field>
              )}
              <p className="muted">
                本地 CPU
                渲染，不调用付费服务。当前输出含静音音轨，配音、配乐与生成式引擎尚未接入。
              </p>
              <Button disabled={busy} type="submit">
                <Plus size={16} />
                创建视频工程
              </Button>
            </form>
          ) : (
            <EmptyState
              title="先添加你的品牌"
              description="视频工程需要关联真实产品。"
              action={
                <Link href="/brand" className="button primary">
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
                      {v.ir.width} × {v.ir.height} · {v.ir.shots.length} 个镜头
                    </p>
                    <StatusBadge status={v.status} />
                  </div>
                  <ChevronRight size={17} />
                </Link>
              ))}
            </div>
          ) : (
            <EmptyState
              title="第一条宣传片，准备开场"
              description="选择一种表达方式，创建真实的视频工程。"
            />
          )}
        </Card>
      </div>
    </>
  );
}

export function VideoEditor({
  store,
  action,
  busy,
  video,
}: PageProps & { video: Video }) {
  const [selected, setSelected] = useState(0);
  const shot = video.ir.shots[selected] || video.ir.shots[0];
  const total =
    video.ir.shots.reduce((sum, s) => sum + s.duration_frames, 0) / 30;
  const ready = video.rendered_revision === video.revision;
  return (
    <>
      <PageHeader
        title={video.name}
        description={`独立视频工程 · V${video.revision} · ${video.ir.width} × ${video.ir.height} · ${total} 秒`}
      >
        <StatusBadge status={video.status} />
        <Button
          disabled={
            busy || video.status === "queued" || video.status === "running"
          }
          onClick={() =>
            action(
              () => api(`/videos/${video.id}/render`, post()),
              "渲染任务已保存，后台会输出真实 MP4",
            )
          }
        >
          <Play size={15} />
          渲染 MP4
        </Button>
        <a
          className="button secondary"
          href={`/api/v1/videos/${video.id}/project`}
        >
          导出工程
        </a>
        {ready && (
          <a
            className="button secondary"
            href={`/api/v1/videos/${video.id}/download`}
          >
            <ArrowDownToLine size={16} />
            下载成片
          </a>
        )}
      </PageHeader>
      <div className="video-editor">
        <Card className="shot-sidebar">
          <div className="section-heading">
            <h3>分镜列表</h3>
            <Badge>{video.ir.shots.length}</Badge>
          </div>
          {video.ir.shots.map((s, i) => (
            <button
              key={s.shot_id}
              onClick={() => setSelected(i)}
              className={`shot-card ${i === selected ? "selected" : ""}`}
            >
              <div className="shot-thumb">
                {s.provider === "pillow_mg" ? (
                  <Sparkles size={22} />
                ) : (
                  <Clapperboard size={22} />
                )}
                <span>{String(i + 1).padStart(2, "0")}</span>
              </div>
              <strong>{s.caption || "素材镜头"}</strong>
              <small>
                {s.provider === "pillow_mg" ? "本地 MG" : "素材混剪"} ·{" "}
                {s.duration_frames / 30}s
              </small>
            </button>
          ))}
        </Card>
        <div className="video-center">
          <div className="video-stage">
            {ready ? (
              <video
                controls
                preload="metadata"
                src={`/api/v1/videos/${video.id}/download`}
              />
            ) : (
              <div className="unrendered-stage">
                <Clapperboard size={38} />
                <h3>工程已保存，等待真实渲染</h3>
                <p>点击“渲染 MP4”后，由后台生成可播放成片。</p>
                <Badge>当前显示工程信息</Badge>
              </div>
            )}
          </div>
          <div className="player-bar">
            <span>
              00:00{" "}
              <span className="muted">
                / 00:{String(total).padStart(2, "0")}
              </span>
            </span>
            <span>
              {video.ir.width}:{video.ir.height} · 30 fps
            </span>
          </div>
          <Card className="timeline">
            <div className="section-heading">
              <h3>统一时间线</h3>
              <span className="muted">按镜头编辑 · 本地引擎</span>
            </div>
            <div className="timeline-ruler">
              {[0, 1, 2, 3, 4].map((i) => (
                <span key={i}>{Math.round((total * i) / 4)}s</span>
              ))}
            </div>
            <div className="timeline-track">
              <span>画面</span>
              <div>
                {video.ir.shots.map((s, i) => (
                  <button
                    key={s.shot_id}
                    onClick={() => setSelected(i)}
                    style={{ flex: s.duration_frames }}
                    className={selected === i ? "selected" : ""}
                  >
                    {s.caption || `镜头 ${i + 1}`}
                  </button>
                ))}
              </div>
            </div>
            <div className="timeline-track">
              <span>音轨</span>
              <div className="audio-track">静音轨道 · 配音与配乐待接入</div>
            </div>
          </Card>
        </div>
        <Card className="shot-inspector">
          <h3>镜头属性</h3>
          <form
            key={`${shot.shot_id}-${shot.shot_revision}`}
            className="form-stack"
            onSubmit={(e) => {
              e.preventDefault();
              const f = new FormData(e.currentTarget);
              const provider = String(f.get("provider"));
              const updated: Shot = {
                ...shot,
                caption: String(f.get("caption")),
                duration_frames: Math.round(Number(f.get("seconds")) * 30),
                provider,
                kind: provider === "pillow_mg" ? "motion_graphics" : "montage",
                asset_id:
                  provider === "pillow_mg" ? null : String(f.get("asset")),
              };
              action(
                () =>
                  api(`/videos/${video.id}/scenes/${shot.shot_id}`, {
                    method: "PATCH",
                    body: JSON.stringify(updated),
                  }),
                "镜头已保存，其余镜头缓存会保留",
              );
            }}
          >
            <Field label="制作引擎">
              <select name="provider" defaultValue={shot.provider}>
                <option value="pillow_mg">本地 MG 动画</option>
                <option value="ffmpeg_media">真实素材 / 录屏</option>
              </select>
            </Field>
            <Field label="镜头文案">
              <textarea
                name="caption"
                maxLength={180}
                rows={4}
                defaultValue={shot.caption}
              />
            </Field>
            <Field label="镜头时长（秒）">
              <input
                name="seconds"
                type="number"
                step="0.5"
                min="0.5"
                max="60"
                defaultValue={shot.duration_frames / 30}
                required
              />
            </Field>
            <Field label="素材（MG 可留空）">
              <select name="asset" defaultValue={shot.asset_id || ""}>
                <option value="">未选择素材</option>
                {store.assets
                  .filter((a) => a.verified)
                  .map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.name}
                    </option>
                  ))}
              </select>
            </Field>
            <p className="muted">
              {shot.provider === "pillow_mg"
                ? "文字、图形动画可通过参数修改。"
                : "素材按片段编辑；当前版本保持源画面，不叠加字幕。"}
            </p>
            <Button disabled={busy || shot.locked} type="submit">
              <Check size={14} />
              保存此镜头
            </Button>
          </form>
        </Card>
      </div>
    </>
  );
}
