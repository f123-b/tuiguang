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
import { useState, useEffect } from "react";
import { api, post, type Shot, type Video } from "../../lib/api";

import { Field, PageHeader, type PageProps } from "../page-shared";
import { VideoEditor } from "./video-editor";
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
  const [mode, setMode] = useState("auto");
  const brand = store.brands[0];
  const availableAssets = store.assets.filter(
    (a) => a.verified && a.kind !== "audio",
  );
  const effectiveMode =
    mode === "auto" ? (availableAssets.length ? "mixed" : "pillow_mg") : mode;
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
          ["auto", "自动推荐", "按当前真实素材推荐本地方案", Sparkles, true],
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
          [
            "screen_demo",
            "软件录屏讲解",
            "完整呈现已授权界面，支持裁切入点",
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
                  effectiveMode === "mixed"
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
                          provider:
                            effectiveMode === "screen_demo"
                              ? "ffmpeg_media"
                              : effectiveMode,
                          kind:
                            effectiveMode === "pillow_mg"
                              ? "motion_graphics"
                              : effectiveMode === "screen_demo"
                                ? "screen_demo"
                                : "montage",
                          duration_frames: frames,
                          caption,
                          asset_id:
                            effectiveMode === "pillow_mg" ? null : assetId,
                          locked: false,
                        },
                      ];
                action(async () => {
                  const video = await api<Video>(
                    "/videos/projects",
                    post({
                      brand_id: brand.id,
                      name: f.get("name"),
                      width: f.get("ratio") === "16:9" ? 1920 : 1080,
                      height: f.get("ratio") === "9:16" ? 1920 : 1080,
                      fps: 30,
                      preview_required: true,
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
                  <select name="ratio">
                    <option value="16:9">16:9 · 1920 × 1080</option>
                    <option value="9:16">9:16 · 1080 × 1920</option>
                    <option value="1:1">1:1 · 1080 × 1080</option>
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
              {effectiveMode !== "pillow_mg" && (
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
                渲染，不调用付费服务。可在工程中添加授权旁白、配乐和字幕；离线系统语音仅在本机可用时显示。未选择音频时导出静音轨。
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
