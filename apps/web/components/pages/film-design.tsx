"use client";
import { type Presentation, type SceneDesign } from "../../lib/api";
import { Field } from "../page-shared";

export const defaultPresentation: Presentation = {
  style: "studio",
  theme: "ink",
  accent: "#B7F56B",
  brand_label: "",
  transition: "clean",
  audio_finish: true,
};

export function PresentationControls({
  value,
  onChange,
  disabled = false,
  fixedStudio = false,
}: {
  value: Presentation;
  onChange: (v: Presentation) => void;
  disabled?: boolean;
  fixedStudio?: boolean;
}) {
  return (
    <fieldset className="form-stack film-controls" disabled={disabled}>
      <legend>全片视觉与声音</legend>
      <div className="form-grid">
        {!fixedStudio && (
          <Field label="制作风格">
            <select
              value={value.style}
              onChange={(e) =>
                onChange({
                  ...value,
                  style: e.target.value as Presentation["style"],
                })
              }
            >
              <option value="studio">分层动效与素材</option>
              <option value="classic">经典文字卡</option>
            </select>
          </Field>
        )}
        <Field label="画面主题">
          <select
            value={value.theme}
            onChange={(e) =>
              onChange({
                ...value,
                theme: e.target.value as Presentation["theme"],
                accent: e.target.value === "paper" ? "#356A37" : "#B7F56B",
              })
            }
          >
            <option value="ink">深墨 · 荧光绿</option>
            <option value="paper">浅纸 · 森林绿</option>
          </select>
        </Field>
        <Field label="品牌署名">
          <input
            value={value.brand_label}
            maxLength={40}
            onChange={(e) =>
              onChange({ ...value, brand_label: e.target.value })
            }
          />
        </Field>
        <Field label="品牌强调色">
          <input
            type="color"
            value={value.accent}
            onChange={(e) => onChange({ ...value, accent: e.target.value })}
          />
        </Field>
        <Field label="镜头衔接">
          <select
            value={value.transition}
            onChange={(e) =>
              onChange({
                ...value,
                transition: e.target.value as Presentation["transition"],
              })
            }
          >
            <option value="clean">利落切换 · 分层入场</option>
            <option value="dip">短淡入淡出 · 分层入场</option>
          </select>
        </Field>
      </div>
      <label className="checkline">
        <input
          type="checkbox"
          checked={value.audio_finish}
          onChange={(e) =>
            onChange({ ...value, audio_finish: e.target.checked })
          }
        />
        声音整理：响度归一、首尾淡化，旁白时降低配乐
      </label>
      <p className="muted">
        发布片使用原生分辨率文字、不同分镜版式和真实素材特写。配乐需上传授权音频；声音整理不会改变系统语音的音色。修改后需重新制作和审核预览。
      </p>
    </fieldset>
  );
}

export function SceneDesignControls({
  value = { layout: "auto" },
  onChange,
  media,
  disabled,
}: {
  value?: SceneDesign;
  onChange: (v: SceneDesign) => void;
  media: boolean;
  disabled: boolean;
}) {
  const crop = value.crop || { x: 0, y: 0, width: 100, height: 100 };
  return (
    <fieldset className="form-stack film-controls" disabled={disabled}>
      <legend>分镜画面设计</legend>
      <Field label="分镜版式">
        <select
          value={value.layout}
          onChange={(e) =>
            onChange({
              ...value,
              layout: e.target.value as SceneDesign["layout"],
            })
          }
        >
          <option value="auto">自动</option>
          {media ? (
            <>
              <option value="hero">开场标题与真实界面</option>
              <option value="screen">界面演示</option>
              <option value="focus">界面重点特写</option>
              <option value="montage">全画幅素材混剪</option>
              <option value="cinema">剧情画面（仅标识与字幕）</option>
              <option value="comic">插画分镜框</option>
            </>
          ) : (
            <>
              <option value="hero">开场大标题</option>
              <option value="features">功能要点</option>
              <option value="steps">操作步骤</option>
              <option value="diagram">动态图解</option>
              <option value="closing">品牌收尾</option>
            </>
          )}
        </select>
      </Field>
      <Field label="引导短句">
        <input
          value={value.kicker || ""}
          maxLength={40}
          onChange={(e) => onChange({ ...value, kicker: e.target.value })}
        />
      </Field>
      <Field label="画面主标题">
        <textarea
          value={value.headline || ""}
          rows={2}
          maxLength={80}
          placeholder="留空使用镜头文案；建议精简为一句"
          onChange={(e) => onChange({ ...value, headline: e.target.value })}
        />
      </Field>
      {!["features", "steps", "focus"].includes(value.layout) && (
        <Field label="补充说明">
          <textarea
            value={value.supporting || ""}
            rows={2}
            maxLength={240}
            onChange={(e) => onChange({ ...value, supporting: e.target.value })}
          />
        </Field>
      )}
      {!media && ["features", "steps", "diagram"].includes(value.layout) && (
        <Field label="功能要点 / 步骤（每行一项，最多三项）">
          <textarea
            value={(value.points || []).join("\n")}
            maxLength={272}
            rows={3}
            onChange={(e) =>
              onChange({
                ...value,
                points: e.target.value.split("\n").slice(0, 3),
              })
            }
            onBlur={() =>
              onChange({
                ...value,
                points: (value.points || [])
                  .map((point) => point.trim())
                  .filter(Boolean),
              })
            }
          />
        </Field>
      )}
      {media && (
        <>
          <Field label="界面镜头运动">
            <select
              value={value.motion || "push"}
              onChange={(e) =>
                onChange({
                  ...value,
                  motion: e.target.value as SceneDesign["motion"],
                })
              }
            >
              <option value="push">缓慢推进 6%</option>
              <option value="pan">横向平移 6%</option>
              <option value="still">保持静止</option>
            </select>
          </Field>
          <p className="muted">
            取景范围以原素材百分比表示。全景为 0 / 0 / 100 /
            100；特写可缩小取景范围。裁切外的内容不会显示，请用预览核对。
          </p>
          <div className="form-grid">
            {(
              [
                ["x", "左侧起点"],
                ["y", "顶部起点"],
                ["width", "取景宽度"],
                ["height", "取景高度"],
              ] as const
            ).map(([key, label]) => (
              <Field label={`${label}（%）`} key={key}>
                <input
                  type="number"
                  min={key === "x" || key === "y" ? 0 : 25}
                  max={100}
                  value={crop[key]}
                  onChange={(e) =>
                    onChange({
                      ...value,
                      crop: { ...crop, [key]: Number(e.target.value) },
                    })
                  }
                />
              </Field>
            ))}
          </div>
        </>
      )}
    </fieldset>
  );
}
