"use client";
import { Button, Card, StatusBadge } from "@xuliu/ui";
import { useEffect, useState } from "react";
import { api, post, type Video } from "../../lib/api";
import { Field, type PageProps } from "../page-shared";
import { DownloadFile } from "../download-file";

export type VoiceSettings = {
  voice_id: string;
  rate: number;
  fit_mode: "extend" | "fixed";
  subtitles: boolean;
  usage_confirmed: boolean;
};
export const defaultVoiceSettings: VoiceSettings = {
  voice_id: "",
  rate: 0,
  fit_mode: "extend",
  subtitles: true,
  usage_confirmed: false,
};

export function VoiceControls({
  value,
  onChange,
  disabled = false,
}: {
  value: VoiceSettings;
  onChange: (v: VoiceSettings) => void;
  disabled?: boolean;
}) {
  const [voices, setVoices] = useState<{ id: string; language: string }[]>([]);
  const [error, setError] = useState("");
  const [loaded, setLoaded] = useState(false);
  useEffect(() => {
    let cancelled = false;
    api<{ voices: { id: string; language: string }[] }>("/videos/voices")
      .then((data) => {
        if (cancelled) return;
        setVoices(data.voices);
        if (!value.voice_id && data.voices.length)
          onChange({
            ...value,
            voice_id: (
              data.voices.find((v) => v.language.startsWith("zh")) ||
              data.voices[0]
            ).id,
          });
      })
      .catch((e) => {
        if (!cancelled) setError(e.message);
      })
      .finally(() => {
        if (!cancelled) setLoaded(true);
      });
    return () => {
      cancelled = true;
    };
    // Installed voices are read once; user choices remain local until submission.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return (
    <fieldset disabled={disabled} className="form-stack">
      <legend>本地配音与视频合成</legend>
      {!loaded && <p>正在读取本机语音…</p>}
      {error && (
        <p role="alert" className="alert warning">
          {error}
        </p>
      )}
      {loaded && !voices.length && (
        <p className="alert warning">
          本机没有可用系统语音。请在 Windows
          安装中文语音后重试，也可在视频工作室上传自己的配音。
        </p>
      )}
      <div className="form-grid">
        <Field label="配音声音">
          <select
            value={value.voice_id}
            onChange={(e) => onChange({ ...value, voice_id: e.target.value })}
          >
            <option value="">请选择本机声音</option>
            {voices.map((v) => (
              <option key={v.id} value={v.id}>
                {v.language.startsWith("zh") ? "中文" : v.language} · {v.id}
              </option>
            ))}
          </select>
        </Field>
        <Field label="配音语速">
          <select
            value={value.rate}
            onChange={(e) =>
              onChange({ ...value, rate: Number(e.target.value) })
            }
          >
            <option value={-2}>较慢</option>
            <option value={0}>正常</option>
            <option value={2}>较快</option>
            <option value={4}>快速</option>
          </select>
        </Field>
        <Field label="旁白时长与画面匹配">
          <select
            value={value.fit_mode}
            onChange={(e) =>
              onChange({
                ...value,
                fit_mode: e.target.value as VoiceSettings["fit_mode"],
              })
            }
          >
            <option value="extend">旁白较长时自动延长镜头</option>
            <option value="fixed">严格保持镜头时长，超长时提示修改</option>
          </select>
        </Field>
      </div>
      <p className="muted">
        逐镜头生成真实声音并自动加入时间线。自动延长可能增加总时长；录屏会在原镜头结束后停留末帧，不截断旁白。已有旁白会替换，配乐保留。
      </p>
      <label className="checkline">
        <input
          type="checkbox"
          checked={value.subtitles}
          onChange={(e) => onChange({ ...value, subtitles: e.target.checked })}
        />
        按旁白自动生成同步字幕（已有字幕请取消，原字幕将保留）
      </label>
      <label className="checkline">
        <input
          type="checkbox"
          checked={value.usage_confirmed}
          onChange={(e) =>
            onChange({ ...value, usage_confirmed: e.target.checked })
          }
        />
        我确认这些文本及所选系统语音可用于本次本地制作，并同意合成配音
      </label>
      <p className="muted">
        在本机离线运行，不调用 DeepSeek
        或收费配音接口。声音使用确认由你提供，不代表软件认证商业许可。
      </p>
    </fieldset>
  );
}

type Job = {
  id: string;
  status: string;
  stage: string;
  error_code?: string;
  error_message?: string;
  receipt: {
    completed_shots?: number;
    total_shots?: number;
    duration_sec?: number;
    original_duration_sec?: number;
    video_revision?: number;
  };
};

export function NarrationPanel({
  video,
  action,
  busy,
  dirty,
}: Pick<PageProps, "action" | "busy"> & { video: Video; dirty: boolean }) {
  const [settings, setSettings] = useState<VoiceSettings>({
    ...defaultVoiceSettings,
    subtitles: !video.ir.subtitles?.length,
  });
  const initialLines = () =>
    video.ir.shots.map((s, i) => ({
      shot_id: s.shot_id,
      text:
        video.ir.narration?.segments.find((n) => n.shot_id === s.shot_id)
          ?.text ||
        video.ir.creation_brief?.script.shots[i]?.narration ||
        s.narration_text ||
        s.caption,
    }));
  const [lines, setLines] = useState(initialLines);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [error, setError] = useState("");
  const root = `/videos/${video.id}/narration-jobs`;
  const refresh = () =>
    api<Job[]>(root).then((data) => {
      setJobs(data);
      setError("");
    });
  useEffect(() => {
    setLines(initialLines());
    setSettings((s) => ({
      ...s,
      usage_confirmed: false,
      subtitles: !video.ir.subtitles?.length,
    }));
    // Refresh only on a persisted version change, preserving edits during status polls.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [video.id, video.revision]);
  useEffect(() => {
    let cancelled = false;
    const check = () => {
      if (!cancelled)
        refresh().catch((e) => {
          if (!cancelled) setError(e.message);
        });
    };
    check();
    const timer = setInterval(check, 4000);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [root]);
  const pending = jobs.some((j) => ["queued", "running"].includes(j.status));
  const latest = jobs[0];
  const stages: Record<string, string> = {
    "narration.queued": "等待后台开始",
    "narration.synthesizing": "正在逐镜头配音",
    "narration.aligning": "正在对齐音轨与字幕",
    "narration.preview_queued": "声音已加入工程；视频预览及播放在下方",
    "narration.failed": "制作未完成",
  };
  return (
    <Card>
      <h2>配音与视频制作</h2>
      <p>
        填写每镜旁白，选择声音，一次提交完成配音、同步字幕和视频预览。完成后在下方播放，核对音画并确认，再生成高清成片。
      </p>
      {error && (
        <p role="alert" className="alert warning">
          {error}
        </p>
      )}
      {latest && (
        <div className="subtle-note" role="status">
          <StatusBadge status={latest.status} />{" "}
          {stages[latest.stage] || latest.stage}
          {latest.receipt.total_shots && (
            <p>
              配音进度：{latest.receipt.completed_shots || 0} /{" "}
              {latest.receipt.total_shots} 镜头
            </p>
          )}
          {latest.error_message && (
            <p role="alert">
              {latest.error_message} · {latest.error_code}
            </p>
          )}
          {latest.receipt.duration_sec && (
            <p>
              合成时长 {latest.receipt.duration_sec.toFixed(2)} 秒（原工程{" "}
              {latest.receipt.original_duration_sec?.toFixed(2)} 秒）· V
              {latest.receipt.video_revision}
            </p>
          )}
          {latest.status === "completed" && (
            <>
              <p>试听已合成的配音：</p>
              <audio
                controls
                preload="metadata"
                src={`/api/v1${root}/${latest.id}/audio`}
                aria-label="已合成配音试听"
              />
              <p>
                <DownloadFile
                  href={`/api/v1${root}/${latest.id}/audio`}
                  filename={`narration-${video.id.slice(0, 8)}.wav`}
                >
                  下载配音 WAV
                </DownloadFile>
              </p>
            </>
          )}
        </div>
      )}
      <details open={!latest || latest.status === "failed"}>
        <summary>
          {latest?.status === "completed"
            ? "修改旁白并重新制作"
            : "设置配音内容与声音"}
        </summary>
        {lines.map((line, i) => (
          <Field key={line.shot_id} label={`镜头 ${i + 1} 配音文本`}>
            <textarea
              maxLength={600}
              rows={2}
              value={line.text}
              disabled={pending || busy || dirty}
              onChange={(e) =>
                setLines(
                  lines.map((n, j) =>
                    j === i ? { ...n, text: e.target.value } : n,
                  ),
                )
              }
            />
          </Field>
        ))}
        <VoiceControls
          value={settings}
          onChange={setSettings}
          disabled={pending || busy || dirty}
        />
        {dirty && (
          <p className="alert warning">先保存当前视频工程，再制作配音。</p>
        )}
        <Button
          disabled={
            busy ||
            pending ||
            dirty ||
            !settings.voice_id ||
            !settings.usage_confirmed ||
            !lines.some((l) => l.text.trim())
          }
          onClick={() =>
            action(async () => {
              await api(root, {
                ...post({
                  ...settings,
                  expected_revision: video.revision,
                  lines,
                }),
                headers: { "Idempotency-Key": crypto.randomUUID() },
              });
              setSettings((s) => ({ ...s, usage_confirmed: false }));
              await refresh();
            }, "配音与视频制作已排队，后台会自动合成预览")
          }
        >
          生成配音、字幕与视频预览
        </Button>
      </details>
    </Card>
  );
}
