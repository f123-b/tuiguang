# 实际模块地图 · 0.19.0-dev

#45：`video_generation.py` / `wan_comfy.py` / `video_generation_api.py` / `video_generation_worker.py`与0015构成独立本机生成队列；启动器`scripts/start-local-video.mjs`只运行已安装的固定版本。`video-drama.tsx`提供真人/动漫分镜、任务、检查、排序与成片入口；`video_recipes.py`编译generative，`video.py`核对生成来源，`film_types.py`的cinema保留人物画面。真实试镜未替用户艺术确认；未接入唇形驱动、跨镜头身份锁或社媒发布。见[本轮报告](../implementation/AI_DRAMA_VALIDATION.md)。

#41：VIDEO新增video_recipes.py / film_types.py、类型API、逐镜创建与脚本构建复用；五种本地形式的有声预览已实际运行，42项类型测试含受控高清正向通过。真实样片仍待人工审看；云生成和3D未接入。见 [验收](../implementation/VIDEO_TYPES_VALIDATION.md)。

#39续：`examples/video-production/youzhao-choice/edit/` 已实际完成44.133333秒独立本地剪辑与媒体验收；三份实拍、原创方案动效、实际UI、逐句配音、分轨/字幕和离线IR均有来源与回执。无Runway、无新增正式Provider，用户艺术审批未运行。详见 [验收](../implementation/LOCAL_CHOICE_FILM_VALIDATION.md)。

#39：新增独立 `examples/video-production/youzhao-choice/` 前期包（production_pack@1）、原创静帧与13.77秒真实项目备注操作素材。动态人物生成服务尚不可用、未取得报价；没有新增正式Provider、自动导演或工作台功能。状态见 [实际缺口](../implementation/CINEMATIC_PRODUCTION_VALIDATION.md)。

0.17.0-dev：可选Qwen 1.7B内置声音、语气预设、离线GPU推理与资源回执已通过真实配音预览；最终人工审核仍未执行。连续空间镜头代码位于examples/video-motion，仅固定试片工具，未加入正式渲染注册。详见 [证据与边界](../implementation/EXPRESSIVE_MOTION_VALIDATION.md)。

0.16.0-dev：已接入叙事风格字段、按版本冻结的 direction 指令、人工创作复看问题；可选 Kokoro 中文神经声音已通过真实 API → 本地合成 → 实测时长 → 字幕 → 预览，未执行人工审核或高清批准。独立 57.5 秒故事样片不是服务端自动导演效果。详见 [实际范围](../implementation/STORY_VIDEO_VALIDATION.md)。

原 `MODULE_MAP.md` 为目标架构；此表索引本轮实际代码，模块负责人均为仓库维护者。

| module_id | 代码 | 责任与验收 |
|---|---|---|
| WEB-SHELL | `apps/web/components/workspace.tsx`、`packages/ui` | 导航、会话、深浅主题、错误态、响应式 |
| WEB-PAGES | `apps/web/components/pages/*` | 各业务页面独立模块，全部从 API 读写 |
| AUTH | `services/api/creator/auth.py`、`main.py` | JWT 会话、密码哈希、归属与来源校验；safety 测试 |
| BRAND | `models.py`、`schemas.py`、`main.py` | 事实与素材来源、哈希、锁定、失效传播 |
| CREATOR | `jobs.py`、`worker.py`、`celery_app.py` | 唯一日键、时区、预算、暂停、租约恢复 |
| EDITORIAL | `editorial.py`、`editorial_api.py`、`pages/editorial.tsx` | 持久化 14 日计划、乐观锁、事实时效、日期交换、确认与批量备稿；`test_editorial.py` |
| AGENT | `agent.py` | LangGraph 事实筛选 → 规则或真实模型；默认禁用外部追踪 |
| CONTENT | `domains.py`、`main.py` | 编辑版本、确定性预审、人工审核、品牌事实绑定 |
| GRAPHICS | `graphics.py`、`graphics_api.py`、`pages/graphics.tsx` | 独立图文 IR 1.0，三版式/三尺寸、PNG/JPG、真实预览、来源/哈希与发布包；`test_graphics.py` |
| VIDEO | `video.py`、`schemas.py` | 独立 IR、Pillow / FFmpeg 镜头、缓存、ffprobe |
| BRIEFS | `briefs.py`、`brief_api.py`、`brief_jobs.py`、`pages/briefs.tsx` | 用户规定内容、原文或预算 AI 脚本、不可变修订、版本/依据校验与确认建立预览工程；`test_creation_briefs.py` |
| NARRATION | `narration.py`、`narration_api.py`、`speech.py`、`pages/narration.tsx` | 本机逐镜配音、时长测量、音轨/字幕、异步预览任务、进度/试听/错误；`test_narration_pipeline.py` |
| HANDOFF | `domains.py`、`main.py` | 真实 ZIP、过期检查、手动登记和撤销，无平台写网络 |
| METRICS | `domains.py`、`main.py` | 字段匹配/手工指标/版本、NULL、日期/来源、幂等与分组 |
| OBS | `observability.py`、`job_events` | OTel 上下文、错误码、脱敏事件、运行版本 |
| OPS | `infra/migrations`、`.github`、`release_manifest.json` | 迁移、检查与开发发行元数据，尚无生产发布 |

```mermaid
flowchart TD
  Web[Next.js 工作台] --> API[FastAPI / 会话与租户校验]
  API --> DB[(SQLite 本地 / PostgreSQL 部署配置)]
  Worker[独立后台进程] --> DB
  Worker --> Graph[LangGraph 事实约束]
  Worker --> Render[独立 Shot Provider]
  Render --> MG[Pillow MG]
  Render --> FF[FFmpeg 素材合成]
  API --> Files[工作区本地不可变文件]
  Files --> User[用户下载与手动发布]
  User --> Metrics[用户自报 / 指标导入]
  Metrics --> API
```

API 错误含 `code/message/trace_id/request_id`。HTTP 使用 W3C Trace Context，日任务冻结发行信息与选题快照；安全日志不记录 Prompt 原文、密钥和原始私有文件路径。实际 OpenAPI 由 `scripts/export-contracts.py` 从实现生成。运行回执沿用 `engineering/contracts/runtime_receipt.schema.json` 并用真实数据库事件验证。

#27 / 0.13：`BriefsPage → brief_api → CreationBrief(0013)` 保存版本化要求；`plans/manual → manual_plan` 逐行保留原文；`plans/ai → brief_jobs.enqueue → jobs.reserve_budget → model_gateway.complete` 仅一次独立授权调用。`BriefPlan` 保留原始输出、规则问题、用量和人工修订，需求/事实/素材改变则旧脚本过期。用户确认后 `build_video → VideoProjectIR 1.1 → quality/checkpoint → RenderJob(preview)`，后续沿用人工确认/高清规则。正文和画面说明留在私有工程中，诊断仅安全标识；没有自动配音、任意场景生成或发布请求。DB 0013 / directed_video@1，旧日更任务与引擎版本保持兼容。

#29 / 0.14：`BriefScriptEditor / NarrationPanel → narration_api.enqueue → NarrationJob(0014) → worker.process_narration_jobs → speech.synthesize → ffprobe → 对齐 WAV/字幕 → 新 VideoRevision → RenderJob(preview)`。离线安全步骤按租约恢复，版本/素材/品牌依据在合成前后校验；人工操作产生新修订，移除自动创作者依赖。`freeze_end_frames` 是 IR 1.1 的兼容可选字段，pillow_ffmpeg@3 在录屏末尾停帧，旁白不截断。质量确认和最终下载沿用原规则；旧单独配音接口保持待核实素材行为。

M1 调用链：编辑/确认选题 → 日程或显式备稿 → `enqueue` 保存 `input_snapshot` → 版本、事实、暂停、实际计费日预算校验 → LangGraph → 既有内容审核与人工发布包。GET 计划只读取，补齐计划为 POST；新创作者/Worker 依照已开启设置维护规则计划。规则选题自动确认，手动修改后进入 `planned`。此处描述当时 M1 增量；当前视频见下方 B。

M2 图文调用链：图文编辑器 → 带内容版本的工程保存 → Content 图文 JSON（0003）→ 授权/事实/字数检查 → Pillow PNG/JPG 与字体/文件回执 → 逐页查看、人工审核 → 同一文件进入全部图文 ZIP。正文与图文共享内容 revision；预览 GET 不自动生成，不改变审核状态。无需模型网络请求，视频和 Agent 版本保持原值。

A / #7：EVIDENCE 模块位于 `evidence.py`、`evidence_api.py`、`pages/evidence.tsx`；0004 增加私有内容快照、品牌变更提案及平台文案。事实审批使待发布稿失效，历史登记不变。

B / #9：VIDEO 新增 `video_edit.py`、`video_edit_api.py`、`video_audio.py`、`speech.py`、`pages/video-editor.tsx`，IR 1.1 / pillow_ffmpeg@2 / DB 0005。已完成旧片可读取，旧版未完成渲染明确阻断、用户保存升级后重建。视频绑定经内容预审后进入人工 ZIP。

C / #11：LEARNING 位于 `learning.py`、`learning_api.py`、`metrics_io.py`、`pages/learning.tsx`；0006 为指标 active、私有反馈、不可变报告、策略审批与指针、计划策略快照。Worker 仅为 active 创作者自动整理上一完整周；只读查询不发起模型调用。

D / #13：SETTINGS/NOTIFY 位于 `model_config.py`、`settings_api.py`、`notifications.py`、`pages/system-settings.tsx`、`handoff-outcome.tsx`、`ops-console.tsx`。DB 0007；配置仅加密存储，任务冻结工作区修订并检查授权/预算，站内提醒无社媒外呼。

E / #15：PRODUCTION 模块 `production.py`，新增 Creator.render_options / 0008。Run.release 冻结本地制作配置和资产哈希；先保存草稿与实际模型费用，再制作图文或排队视频。暂停、过期依据、失败恢复和媒体完成接入既有 Run/Content 审核状态，禁止自动发布。


0.9.0 / #17：`analysis_api.py → analysis_jobs.py → jobs.reserve_budget` 维护独立复盘任务；`learning.py` 保留确定性证据，模型只能追加待审解释。`analysis_api.reconcile` 保存未知费用的人工来源与整数分，不重发请求。0009 扩展指标版本、唯一 AI 报告关联和费用核对。


#19 集成：下载通过 `domains.verified_file` 校验原始素材、人工 ZIP 和含素材的私有导出；缺失/损坏明确阻断。`pages/evidence.tsx` 的未保存平台文案同时阻止历史恢复和平台切换。实际浏览器/三种 30 秒成片证据在 FINAL_ACCEPTANCE.md。


#21 / 0.10：`model_diagnostics.py` / `model_gateway.py` / `pages/model-settings.tsx`，0010。独立模型配置与列表检查、固定 JSON 预算联调；Agent/学习复盘共享兼容参数，旧请求参数仍为默认值。联调不创建日更内容，不发送品牌资料。


#23：`source_http.py` 公网 IP 固定 HTTPS；`product_monitor.py` 快照/差异/租约/Worker 轮询；`product_sources_api.py` 来源/上传/提案/素材版本；`pages/product-sources.tsx` 品牌与素材界面。0011 增加来源、快照、事件、检查与可空素材关联；`evidence.invalidate_asset` 同时复核图文/视频引用的未登记稿。


#25：`quality.py` 冻结规则与来源、标题和镜头比较；`quality_api.py` 租户内报告/预览/人工确认；`quality_jobs.py` 单独授权的预算模型建议，复用一次性网关和未知费用处理。`pages/quality.tsx` 接入内容和视频工作室；`video.py` 单独 purpose=preview/final，真实水印与尺寸探针；`production.preview_ready` 在自动任务中等待复核。0012 新增质量表、视频政策与任务用途；`video_edit.current_output` 拒绝不再有效的确认，附件只取 final 回执。Session 不自动过期，网络/渲染后显式刷新品牌、素材与工程，再判断版本；竞态测试覆盖渲染期间修改。`compatible_chat@2` 冻结在公开配置 hash 中，DeepSeek 官方 JSON 使用已核实的非思考参数。真实联调和 30 秒预览/高清证据见 CREATIVE_QUALITY_VALIDATION.md。


#31 / 0.15：`film.py` 负责发布片原生排版、真实界面裁切和镜头运动，`video_audio.py` 可选声音整理；`pages/film-design.tsx` 共享全片/分镜设置，创作页和指定内容首次建立工程时接入。DB 0014 / IR 1.1 不变，pillow_ffmpeg@4 / video_presentation@1。具体边界与证据见 [发布片验收](../implementation/SOFTWARE_FILM_VALIDATION.md)。

#33 / 0.15.1：`film.render_scene` 对 studio 的 pan/push 使用逐帧浮点角点插值，修正慢速镜头的整像素步进；`video.py` 注册、镜头缓存和输出回执统一更新为 pillow_ffmpeg@5。没有新增 API、DB、Prompt 或 UI 控件；still、classic、素材、音轨与审核政策保留。`test_film_motion.py` 测量预览/1080p 的实际帧运动和真实视频裁切。独立剪辑的有招样片不是新增的自动录屏功能，见 [本轮验收](../implementation/SMOOTH_CAMERA_VALIDATION.md)。
