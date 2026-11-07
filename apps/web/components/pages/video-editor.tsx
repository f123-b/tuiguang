"use client";
import { Badge, Button, Card } from "@xuliu/ui";
import { useEffect, useState } from "react";
import Link from "next/link";
import {
  api,
  post,
  type AudioTrack,
  type Shot,
  type Video,
} from "../../lib/api";
import { QualityPanel } from "./quality";
import { NarrationPanel } from "./narration";
import {
  PresentationControls,
  SceneDesignControls,
  defaultPresentation,
} from "./film-design";
import { DownloadFile } from "../download-file";
import { Field, PageHeader, type PageProps } from "../page-shared";

export function VideoEditor({
  store,
  action,
  busy,
  video,
}: PageProps & { video: Video }) {
  const [draft, setDraft] = useState<Video["ir"]>(structuredClone(video.ir));
  const [dirty, setDirty] = useState(false);
  const [selected, setSelected] = useState(0);
  const [history, setHistory] = useState<{ revision: number }[]>([]);
  const [restore, setRestore] = useState(0);
  const [confirmRestore, setConfirmRestore] = useState(false);
  const [voices, setVoices] = useState<{ id: string; language: string }[]>([]);
  const [error, setError] = useState("");
  const [receipt, setReceipt] = useState<unknown>(null);
  const [exportPath, setExportPath] = useState("");
  useEffect(() => {
    setDraft(structuredClone(video.ir));
    setDirty(false);
    setConfirmRestore(false);
    setExportPath("");
  }, [video.id, video.revision]);
  useEffect(() => {
    api<{ revision: number }[]>(`/videos/${video.id}/history`)
      .then(setHistory)
      .catch((e) => setError(e.message));
    api<{ voices: { id: string; language: string }[] }>("/videos/voices")
      .then((v) => setVoices(v.voices))
      .catch((e) => setError(e.message));
  }, [video.id, video.revision]);
  useEffect(() => {
    api<{ status: string; receipt: unknown; error_code: string }[]>(
      `/videos/${video.id}/render-jobs`,
    )
      .then((j) => setReceipt(j[0] || null))
      .catch((e) => setError(e.message));
  }, [video.id, video.status, video.revision]);
  const update = (next: Video["ir"]) => {
    setDraft(next);
    setDirty(true);
  };
  const index = Math.min(selected, draft.shots.length - 1);
  const shot = draft.shots[index];
  const total = draft.shots.reduce((sum, s) => sum + s.duration_frames, 0);
  const images = store.assets.filter(
    (a) => a.verified && a.kind !== "audio" && a.brand_id === video.brand_id,
  );
  const audio = store.assets.filter(
    (a) => a.verified && a.kind === "audio" && a.brand_id === video.brand_id,
  );
  const changeShot = (patch: Partial<Shot>) =>
    update({
      ...draft,
      shots: draft.shots.map((s, i) => (i === index ? { ...s, ...patch } : s)),
    });
  const changeAudio = (i: number, patch: Partial<AudioTrack>) =>
    update({
      ...draft,
      audio_tracks: (draft.audio_tracks || []).map((t, j) =>
        i === j ? { ...t, ...patch } : t,
      ),
    });
  const move = (delta: number) => {
    const shots = [...draft.shots];
    [shots[index], shots[index + delta]] = [shots[index + delta], shots[index]];
    update({ ...draft, shots });
    setSelected(index + delta);
  };
  const ready = video.rendered_revision === video.revision;
  return (
    <>
      <PageHeader
        title={video.name}
        description={`保存版本 V${video.revision} · ${draft.width} × ${draft.height} · ${(total / 30).toFixed(2)} 秒 · ${dirty ? "有未保存修改" : "工程已保存"}`}
      >
        <Button
          disabled={busy || (!dirty && video.ir.schema_version !== "1.0")}
          onClick={() =>
            action(
              () =>
                api(`/videos/${video.id}/project`, {
                  method: "PUT",
                  body: JSON.stringify({
                    expected_revision: video.revision,
                    document: {
                      brand_id: video.brand_id,
                      name: draft.name || video.name,
                      width: draft.width,
                      height: draft.height,
                      fps: 30,
                      presentation: draft.presentation,
                      shots: draft.shots,
                      audio_tracks: draft.audio_tracks || [],
                      subtitles: draft.subtitles || [],
                    },
                  }),
                }),
              "工程已保存，历史版本可恢复",
            )
          }
        >
          {video.ir.schema_version === "1.0"
            ? "升级并保存工程"
            : "保存整个工程"}
        </Button>
        {!video.preview_required && (
          <Button
            disabled={
              busy ||
              dirty ||
              video.status === "queued" ||
              video.status === "running"
            }
            onClick={() =>
              action(
                () => api(`/videos/${video.id}/render`, post()),
                "真实渲染已排队",
              )
            }
          >
            渲染 MP4
          </Button>
        )}
        <a
          className="button secondary"
          href={`/api/v1/videos/${video.id}/project`}
        >
          导出已保存工程
        </a>
        {ready && !dirty && (
          <DownloadFile
            href={`/api/v1/videos/${video.id}/download`}
            filename={`video-${video.id.slice(0, 8)}-v${video.revision}.mp4`}
          >
            下载成片
          </DownloadFile>
        )}
        {ready && !dirty && (
          <Button
            variant="secondary"
            disabled={busy}
            onClick={() =>
              action(async () => {
                const result = await api<{ path: string }>(
                  `/videos/${video.id}/export-local`,
                  post({ expected_revision: video.revision, confirmed: true }),
                );
                setExportPath(result.path);
              }, "成片、配音、字幕及工程已保存到本机导出文件夹")
            }
          >
            保存到本机文件夹
          </Button>
        )}
      </PageHeader>
      {exportPath && (
        <Card>
          <h2>文件已保存到本机</h2>
          <Field label="成片文件位置">
            <input
              readOnly
              value={exportPath}
              onFocus={(e) => e.currentTarget.select()}
            />
          </Field>
          <p>
            复制此路径，在资源管理器地址栏粘贴即可找到成片；同一文件夹还保存了配音、字幕和工程。
          </p>
        </Card>
      )}
      {error && (
        <p className="alert warning" role="alert">
          {error}
        </p>
      )}
      {dirty && (
        <p className="alert warning">
          修改尚未保存；渲染、导出和版本恢复使用服务器已保存工程。先保存再继续。
        </p>
      )}
      <Card>
        <h2>发布片导演设置</h2>
        <PresentationControls
          value={
            draft.presentation || { ...defaultPresentation, style: "classic" }
          }
          onChange={(presentation) => update({ ...draft, presentation })}
          disabled={busy}
        />
      </Card>
      <NarrationPanel video={video} action={action} busy={busy} dirty={dirty} />
      <QualityPanel
        store={store}
        action={action}
        busy={busy}
        kind="video"
        id={video.id}
        revision={video.revision}
        brandId={video.brand_id}
        video={video}
        dirty={dirty}
      />
      <div className="video-editor">
        <Card className="shot-sidebar">
          <h3>分镜与顺序</h3>
          {draft.shots.map((s, i) => (
            <button
              type="button"
              key={s.shot_id}
              className={`shot-card ${index === i ? "selected" : ""}`}
              onClick={() => setSelected(i)}
            >
              <strong>
                {i + 1}. {s.caption || "素材镜头"}
              </strong>
              <small>
                {(s.duration_frames / 30).toFixed(2)}s ·{" "}
                {s.locked
                  ? "已锁定"
                  : s.provider === "pillow_mg"
                    ? "参数可编辑"
                    : "片段可编辑"}
              </small>
            </button>
          ))}
          <Button
            variant="secondary"
            disabled={busy || draft.shots.length >= 12}
            onClick={() => {
              update({
                ...draft,
                shots: [
                  ...draft.shots,
                  {
                    shot_id: crypto.randomUUID(),
                    shot_revision: 1,
                    provider: "pillow_mg",
                    kind: "motion_graphics",
                    caption: "新的真实产品笔记",
                    duration_frames: 90,
                    asset_id: null,
                    locked: false,
                    trim_start_frame: 0,
                    speed_percent: 100,
                  },
                ],
              });
              setSelected(draft.shots.length);
            }}
          >
            增加镜头
          </Button>
        </Card>
        <div className="video-center">
          <div className="video-stage">
            {ready ? (
              <video
                key={`${video.id}-${video.revision}`}
                controls
                preload="metadata"
                src={`/api/v1/videos/${video.id}/download`}
              />
            ) : (
              <div className="unrendered-stage">
                <h3>当前版本还没有成片</h3>
                <p>保存工程后，先在质量流程中检查并生成低清预览。</p>
              </div>
            )}
          </div>
          <p className="muted">
            播放器显示服务器已保存版本。素材不足或版权未核实会明确阻止渲染。
          </p>
          <Card className="timeline">
            <h3>统一时间线 · {(total / 30).toFixed(2)} 秒</h3>
            <div className="timeline-track">
              <span>画面</span>
              <div>
                {draft.shots.map((s, i) => (
                  <button
                    key={s.shot_id}
                    style={{ flex: s.duration_frames }}
                    onClick={() => setSelected(i)}
                  >
                    {i + 1}
                  </button>
                ))}
              </div>
            </div>
            <div className="timeline-track">
              <span>音轨</span>
              <div className="audio-track">
                {(draft.audio_tracks || [])
                  .map(
                    (t) =>
                      `${t.role === "voiceover" ? "旁白" : "配乐"} ${t.start_frame / 30}–${(t.start_frame + t.duration_frames) / 30}s`,
                  )
                  .join(" / ") || "未添加音频，导出静音轨"}
              </div>
            </div>
            <p className="muted">
              字幕 {(draft.subtitles || []).length} 条 · 仅当前工作区授权素材
            </p>
          </Card>
        </div>
        <Card className="shot-inspector">
          <h3>镜头 {index + 1}</h3>
          <div className="form-stack">
            <div className="form-actions">
              <Button
                variant="quiet"
                disabled={index === 0}
                onClick={() => move(-1)}
              >
                上移
              </Button>
              <Button
                variant="quiet"
                disabled={index === draft.shots.length - 1}
                onClick={() => move(1)}
              >
                下移
              </Button>
              <Button
                variant="quiet"
                disabled={shot.locked || draft.shots.length === 1}
                onClick={() =>
                  update({
                    ...draft,
                    shots: draft.shots.filter((_, i) => i !== index),
                  })
                }
              >
                删除镜头
              </Button>
            </div>
            <Field label="制作引擎">
              <select
                value={shot.provider}
                disabled={shot.locked}
                onChange={(e) =>
                  changeShot({
                    provider: e.target.value,
                    design: { ...shot.design, layout: "auto" },
                    kind:
                      e.target.value === "pillow_mg"
                        ? "motion_graphics"
                        : "montage",
                    asset_id:
                      e.target.value === "pillow_mg"
                        ? null
                        : images[0]?.id || null,
                  })
                }
              >
                <option value="pillow_mg">本地 MG 动画</option>
                <option value="ffmpeg_media">真实素材 / 录屏</option>
              </select>
            </Field>
            <Field label="镜头文案 / 字幕">
              <textarea
                value={shot.caption}
                maxLength={180}
                disabled={shot.locked}
                rows={4}
                onChange={(e) => changeShot({ caption: e.target.value })}
              />
            </Field>
            {draft.presentation?.style === "studio" && (
              <SceneDesignControls
                value={shot.design}
                onChange={(design) => changeShot({ design })}
                media={!!shot.asset_id}
                disabled={shot.locked || busy}
              />
            )}
            <Field label="镜头时长（秒，最多 60）">
              <input
                type="number"
                min={0.5}
                max={60}
                step={0.5}
                value={shot.duration_frames / 30}
                disabled={shot.locked}
                onChange={(e) =>
                  changeShot({
                    duration_frames: Math.round(Number(e.target.value) * 30),
                  })
                }
              />
            </Field>
            {shot.provider === "ffmpeg_media" && (
              <>
                <Field label="授权真实素材">
                  <select
                    value={shot.asset_id || ""}
                    disabled={shot.locked}
                    onChange={(e) => changeShot({ asset_id: e.target.value })}
                  >
                    <option value="">请选择</option>
                    {images.map((a) => (
                      <option key={a.id} value={a.id}>
                        {a.name}
                      </option>
                    ))}
                  </select>
                </Field>
                <Field label="源视频入点（帧，30fps）">
                  <input
                    type="number"
                    min={0}
                    value={shot.trim_start_frame || 0}
                    disabled={shot.locked}
                    onChange={(e) =>
                      changeShot({ trim_start_frame: Number(e.target.value) })
                    }
                  />
                </Field>
                <Field label="播放速度（百分比）">
                  <input
                    type="number"
                    min={25}
                    max={400}
                    value={shot.speed_percent || 100}
                    disabled={shot.locked}
                    onChange={(e) =>
                      changeShot({ speed_percent: Number(e.target.value) })
                    }
                  />
                </Field>
                <Field label="录屏末帧停留（秒）">
                  <input
                    type="number"
                    min={0}
                    step={1 / 30}
                    max={Math.max(0, (shot.duration_frames - 1) / 30)}
                    value={(shot.freeze_end_frames || 0) / 30}
                    disabled={shot.locked}
                    onChange={(e) =>
                      changeShot({
                        freeze_end_frames: Math.round(
                          Number(e.target.value) * 30,
                        ),
                      })
                    }
                  />
                </Field>
              </>
            )}
            <Button
              variant="secondary"
              disabled={busy || dirty}
              onClick={() =>
                action(
                  () =>
                    api(
                      `/videos/${video.id}/shots/${shot.shot_id}/lock`,
                      post({
                        expected_revision: video.revision,
                        locked: !shot.locked,
                      }),
                    ),
                  shot.locked ? "已主动解锁" : "镜头已锁定",
                )
              }
            >
              {shot.locked ? "主动解锁此镜头" : "锁定此镜头"}
            </Button>
          </div>
        </Card>
      </div>
      <div className="form-columns">
        <Card>
          <h2>全片与版本恢复</h2>
          <Field label="项目名称">
            <input
              value={draft.name || video.name}
              maxLength={120}
              onChange={(e) => update({ ...draft, name: e.target.value })}
            />
          </Field>
          <Field label="画面比例">
            <select
              value={
                draft.width === 1920
                  ? "wide"
                  : draft.height === 1920
                    ? "portrait"
                    : "square"
              }
              onChange={(e) =>
                update({
                  ...draft,
                  width: e.target.value === "wide" ? 1920 : 1080,
                  height: e.target.value === "portrait" ? 1920 : 1080,
                })
              }
            >
              <option value="wide">16:9 · 1920×1080</option>
              <option value="portrait">9:16 · 1080×1920</option>
              <option value="square">1:1 · 1080×1080</option>
            </select>
          </Field>
          <Field label="选择服务器历史版本">
            <select
              value={restore}
              onChange={(e) => {
                setRestore(Number(e.target.value));
                setConfirmRestore(false);
              }}
            >
              <option value={0}>请选择版本</option>
              {history.map((h) => (
                <option key={h.revision} value={h.revision}>
                  V{h.revision}
                </option>
              ))}
            </select>
          </Field>
          <label className="checkline">
            <input
              type="checkbox"
              checked={confirmRestore}
              onChange={(e) => setConfirmRestore(e.target.checked)}
            />
            确认将所选工程恢复为新版本（包含锁定镜头）
          </label>
          <Button
            disabled={
              busy ||
              dirty ||
              !confirmRestore ||
              !restore ||
              restore === video.revision
            }
            onClick={() =>
              action(
                () =>
                  api(
                    `/videos/${video.id}/restore/${restore}`,
                    post({
                      expected_revision: video.revision,
                      confirmed: true,
                    }),
                  ),
                "已恢复为新工程版本",
              )
            }
          >
            恢复工程
          </Button>
          <details>
            <summary>最近渲染结果与技术回执</summary>
            <pre className="diagnostic-json">
              {JSON.stringify(receipt, null, 2)}
            </pre>
          </details>
        </Card>
        <Card>
          <h2>授权旁白与配乐</h2>
          <p>
            先在素材库上传并核实音频授权，再加入音轨。所有音轨按 30fps
            帧数对齐；全片最高 120 秒。
          </p>
          <Link href="/studio/assets" className="text-link">
            上传音频或核实授权
          </Link>
          {(draft.audio_tracks || []).map((track, i) => (
            <section key={track.track_id} className="subtle-note">
              <div className="form-grid">
                <Field label="音频素材">
                  <select
                    value={track.asset_id}
                    onChange={(e) =>
                      changeAudio(i, { asset_id: e.target.value })
                    }
                  >
                    {audio.map((a) => (
                      <option value={a.id} key={a.id}>
                        {a.name}
                      </option>
                    ))}
                  </select>
                </Field>
                <Field label="用途">
                  <select
                    value={track.role}
                    onChange={(e) =>
                      changeAudio(i, {
                        role: e.target.value as AudioTrack["role"],
                        loop: false,
                      })
                    }
                  >
                    <option value="voiceover">旁白</option>
                    <option value="music">配乐</option>
                  </select>
                </Field>
                <Field label="全片开始帧">
                  <input
                    type="number"
                    min={0}
                    value={track.start_frame}
                    onChange={(e) =>
                      changeAudio(i, { start_frame: Number(e.target.value) })
                    }
                  />
                </Field>
                <Field label="时长帧">
                  <input
                    type="number"
                    min={1}
                    max={total}
                    value={track.duration_frames}
                    onChange={(e) =>
                      changeAudio(i, {
                        duration_frames: Number(e.target.value),
                      })
                    }
                  />
                </Field>
                <Field label="源音频入点帧">
                  <input
                    type="number"
                    min={0}
                    value={track.source_start_frame}
                    onChange={(e) =>
                      changeAudio(i, {
                        source_start_frame: Number(e.target.value),
                      })
                    }
                  />
                </Field>
                <Field label="音量百分比">
                  <input
                    type="number"
                    min={0}
                    max={200}
                    value={track.volume_percent}
                    onChange={(e) =>
                      changeAudio(i, { volume_percent: Number(e.target.value) })
                    }
                  />
                </Field>
              </div>
              <label className="checkline">
                <input
                  type="checkbox"
                  disabled={track.role !== "music"}
                  checked={track.loop}
                  onChange={(e) => changeAudio(i, { loop: e.target.checked })}
                />
                配乐循环（旁白不循环）
              </label>
              <Button
                variant="quiet"
                onClick={() =>
                  update({
                    ...draft,
                    audio_tracks: draft.audio_tracks?.filter((_, j) => j !== i),
                  })
                }
              >
                移除此音轨
              </Button>
            </section>
          ))}
          <Button
            variant="secondary"
            disabled={!audio.length || (draft.audio_tracks?.length || 0) >= 8}
            onClick={() =>
              update({
                ...draft,
                audio_tracks: [
                  ...(draft.audio_tracks || []),
                  {
                    track_id: crypto.randomUUID(),
                    asset_id: audio[0].id,
                    role: "voiceover",
                    start_frame: 0,
                    duration_frames: Math.min(total, 60),
                    source_start_frame: 0,
                    volume_percent: 100,
                    loop: false,
                  },
                ],
              })
            }
          >
            添加音轨
          </Button>
          <details>
            <summary>单独生成音频素材（高级）</summary>
            {voices.length ? (
              <form
                className="form-stack"
                onSubmit={(e) => {
                  e.preventDefault();
                  const f = new FormData(e.currentTarget);
                  action(
                    () =>
                      api(
                        "/videos/speech",
                        post({
                          brand_id: video.brand_id,
                          text: f.get("text"),
                          voice_id: f.get("voice"),
                          confirmed: true,
                        }),
                      ),
                    "配音已保存到素材库；核实使用权后才可加入成片",
                  );
                }}
              >
                <select aria-label="本机语音" name="voice">
                  {voices.map((v) => (
                    <option key={v.id} value={v.id}>
                      {v.id} · {v.language}
                    </option>
                  ))}
                </select>
                <textarea
                  aria-label="配音文本"
                  name="text"
                  maxLength={4000}
                  rows={3}
                  required
                  placeholder="只输入已经核实、允许由本机语音合成的文本"
                />
                <label className="checkline">
                  <input type="checkbox" required />
                  我同意使用本机语音合成，并会核实语音输出的使用许可
                </label>
                <Button disabled={busy} type="submit">
                  生成离线配音
                </Button>
              </form>
            ) : (
              <p className="muted">
                本机没有可用的离线语音；可自行上传授权配音。不会自动调用付费云端
                TTS。
              </p>
            )}
          </details>
        </Card>
      </div>
      <Card>
        <h2>字幕时间线</h2>
        <p>
          字幕不能重叠或超出全片。素材镜头文案也会烧录到画面；此处用于额外解说字幕。
        </p>
        {(draft.subtitles || []).map((cue, i) => (
          <div className="form-grid subtle-note" key={cue.cue_id}>
            <Field label="起始帧">
              <input
                type="number"
                value={cue.start_frame}
                min={0}
                onChange={(e) =>
                  update({
                    ...draft,
                    subtitles: draft.subtitles?.map((c, j) =>
                      i === j
                        ? { ...c, start_frame: Number(e.target.value) }
                        : c,
                    ),
                  })
                }
              />
            </Field>
            <Field label="结束帧">
              <input
                type="number"
                value={cue.end_frame}
                min={1}
                max={total}
                onChange={(e) =>
                  update({
                    ...draft,
                    subtitles: draft.subtitles?.map((c, j) =>
                      i === j ? { ...c, end_frame: Number(e.target.value) } : c,
                    ),
                  })
                }
              />
            </Field>
            <Field label="字幕文本">
              <textarea
                value={cue.text}
                maxLength={120}
                rows={2}
                onChange={(e) =>
                  update({
                    ...draft,
                    subtitles: draft.subtitles?.map((c, j) =>
                      i === j ? { ...c, text: e.target.value } : c,
                    ),
                  })
                }
              />
            </Field>
            <Button
              variant="quiet"
              onClick={() =>
                update({
                  ...draft,
                  subtitles: draft.subtitles?.filter((_, j) => i !== j),
                })
              }
            >
              删除此字幕
            </Button>
          </div>
        ))}
        <div className="form-actions">
          <Button
            variant="secondary"
            disabled={(draft.subtitles?.length || 0) >= 100}
            onClick={() => {
              const start = draft.subtitles?.at(-1)?.end_frame || 0;
              if (start >= total) {
                setError("全片没有空余字幕时长，请先修改现有字幕");
                return;
              }
              update({
                ...draft,
                subtitles: [
                  ...(draft.subtitles || []),
                  {
                    cue_id: crypto.randomUUID(),
                    start_frame: start,
                    end_frame: Math.min(total, start + 60),
                    text: "新的解说字幕",
                  },
                ],
              });
            }}
          >
            添加字幕
          </Button>
          <a
            className="button quiet"
            href={`/api/v1/videos/${video.id}/subtitles`}
          >
            下载已保存 SRT
          </a>
        </div>
      </Card>
    </>
  );
}
