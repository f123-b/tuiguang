# 核心工程契约与稳定标识

0.19 / #45：`/video-generation/capabilities`鉴权并真实检查本机权重/节点；POST `/video-generation/jobs`要求Idempotency-Key，字段brand_id/reference_asset_id/prompt/style(realistic|anime)/seed/width/height/frames/usage_confirmed=true。默认1280×704、121帧，尺寸32倍数且≤901120像素，49/73/97/121帧、24fps；保留旧512请求但界面标为低清试算。独立DB0015任务保存来源/版本，先durable submitting后唯一POST，未知回执不自动重发；有provider_request_id可显式check-existing，只取消未领取的queued。GET jobs、jobs/{id}/video与POST verify均按工作区隔离。生成输出未核实，用户确认后才可通过Recipe(mode=generative)制作，Shot保留generation_job_id；comfy_wan只代表已有片段剪辑，生成服务可用性由capabilities单独表示。cinema只加小型AI标识及字幕。IR1.1兼容可选字段，无值不序列化，旧锁定镜头/保存保持兼容。新增数据进入私有导出。wan_ti2v_fixed@2采用官方原生VAE解码；技术成功不表示艺术通过，不支持对口型。现有人工确认及站外人工发布边界不变。

0.18 / #41：GET /videos/recipes返回video_recipes@1与真实本机能力；POST /videos/from-recipe要求Idempotency-Key，接RecipeInput(mode=mg/screen_demo/montage/illustrated/mixed，六种recipe_id，1–12镜)，始终preview_required。逐镜标题、旁白、补充、节点、素材、入点、运动/取景进入Shot；可选NarrationOptions直接排本机配音，否则排无旁白预览。重复键内容不同409 VID_RECIPE_KEY_CONFLICT；缺素材/类型不符分别VID_RECIPE_ASSETS_REQUIRED/VID_RECIPE_ASSET_KIND。production_recipe是服务器维护的创建来源，手工保存保留，不可由请求覆写。Brief Build可选production_mode与recipe_id复用编译器，省略兼容旧逻辑；80字以上画面短句明确拒绝，不截断。SceneDesign新增diagram/montage/comic；pillow_ffmpeg@7，旧缓存不复用。DB0014、IR1.1、Prompt/模型不变；高清审核规则不变。

0.17.0-dev / #37：NarrationOptions及SpeechInput新增delivery_style=plain/conversational/warm/explainer，缺省plain在旧幂等摘要中省略。qwen:serena/dylan/uncle_fu/vivian提供delivery_styles及max_text_length=600；只接受rate=0，未知语气或不支持的声音明确拒绝。GET /videos/voices顶层provider=local_offline。新错误TTS_STYLE_UNSUPPORTED/TTS_RATE_UNSUPPORTED；冻结spoken_delivery@1，narration_pipeline@3。超过既有120秒上限后不再合成下一镜头。DB0014、IR1.1和正式provider@5不变。

0.16.0-dev / #35：BriefInput.narrative_mode 可选，枚举 overview/story/contrast/documentary，API 缺省 overview；新 UI 缺省 story。旧文档不补字段，旧 Run 不补 direction_version。新 Run 冻结 story_direction@1；plan.review.creative_review 为人工建议，不改变硬性审核门槛。声音条目新增可选 label，kokoro:45/46/49/50 仅完整配置才提供；NarrationJob.document.voice_source 冻结模型哈希，receipt.voice_receipts 包含实际 runtime_version；新错误 TTS_PROVIDER_CHANGED。DB0014 / IR1.1 / provider@5 不变，详见导出 OpenAPI 和 [验收](../implementation/STORY_VIDEO_VALIDATION.md)。

## 统一 ID
| ID | 生命周期 | 谁创建 | 用途 |
|---|---|---|---|
| `trace_id` | 一次分布式执行轨迹 | OpenTelemetry | 将跨服务 spans 关联 |
| `request_id` | 一次 API 请求 | API 网关 | 用户支持查单 |
| `creator_run_id` | 一个创作者某日任务 | Scheduler | 唯一日更任务 |
| `content_id` | 一个图文/视频内容实体 | Content | 草稿与版本 |
| `video_project_id` | 一个视频工程 | Video Domain | 跨镜头修订 |
| `shot_id` | 一个镜头 | Video Domain | 精确到镜头 |
| `render_job_id` | 一次实际渲染调用 | Render Worker | 费用、错误、重试 |
| `provider_request_id` | 第三方模型请求 | Provider | 排查服务商故障 |
| `artifact_id` | 一份实际产物 | Asset Store | 哈希与版权链 |
| `error_code` | 分类错误码 | 责任模块 | 告警路由与统一用户提示 |

`trace_id` 可能包含多个业务子任务；用户可见的 `request_id` 与业务 `creator_run_id` 不应相互替代。时间用 UTC ISO8601 存储并额外保留用户时区，运营日按用户所属时区计算。

## 示例 API
- `POST /api/v1/creator-runs` 必须要求 `Idempotency-Key`，请求重复返回同一 run，不重复创建任务。
- `GET /api/v1/creator-runs/{id}/diagnostic` 仅工作区授权用户或支持角色可见，默认展示脱敏摘要与错误码。
- `GET /api/v1/video-projects/{id}/shots/{shot_id}/render-jobs` 支持检索单个镜头版本与输出哈希。
- `GET /api/v1/releases/current` 返回应用及数据/模型/Prompt/IR schema 的版本清单，不能包含密钥。
- `POST /api/v1/handoff/{id}/confirm` 写入 `user_reported_published`，无外部平台 POST；平台发布 URL 可选，验证仅检查安全格式，不能当平台真实认证。

## 关键副作用
内容生成、低成本选题与预览可以有限重试；GPU 生成必须有费用预留/结算；导出包命名带内容版本哈希；第三方请求状态未知时绝不能按“安全重试”无条件重复计费。数据库事务处理原子状态，文件产物通过不可变哈希与指针提交关联。

Schema 文件参见 `engineering/contracts/`。每次发布冻结该版本，避免旧任务恢复时突然按新 schema 解包。

## 0.13 实际指定内容接口

- `GET/POST /api/v1/creation-briefs` 与 `GET/PUT /{brief_id}`：工作区内需求列表、创建、详情和带 expected_revision 保存；品牌不允许更换。BriefInput 包含主题/内容/受众/语气/逐镜头原文/必现和禁用文字/行动引导/3–60 秒时长/比例/制作形式/已核实事实和授权素材。
- `POST /{brief_id}/plans/manual`：expected_revision、confirmed=true；原文的每个非空行对应一镜，1–12 镜，画面文字逐行保留，均分总帧数，不请求模型。
- `POST /{brief_id}/plans/ai`：另需管理员、同品牌运行中创作者与模型授权、creator_id、max_cost_cents 和 Idempotency-Key。冻结需求和已核实事实，以 `job_kind=brief_video`、`directed_video@1` 执行，复用共享预算。未知回执保留预留且不自动重试。
- `POST /{brief_id}/plans/{plan_id}/revisions`：expected_revision、document，保存不可变子修订；ScriptInput 包含 title、fact_refs、1–12 个 shots 与 uncertainties。每镜 caption、narration、visual_note、asset_id、duration_frames；旁白/说明只是文字，不自动生成声音或画面。有效 JSON 未满足文字/时长等条件时保留 needs_revision，供免费修订。
- `POST .../build`：expected_revision、confirmed=true；校验当前需求及事实/素材哈希和脚本条件，再幂等建立一个独立视频工程与预览任务。人工确认、高清与发布附件继续使用 0.12 规则。用户需求不是已核实事实。
- DB 0013 增加 creation_briefs / brief_plans；私有导出包含两表，脚本任务诊断删除 input_snapshot。无新增依赖，Video IR/Provider 版本未变。

## 0.14 真实配音制作

- `POST /api/v1/videos/{id}/narration-jobs`：expected_revision、按镜头顺序的 lines[{shot_id,text}]、voice_id、rate(-5..5)、fit_mode(extend/fixed)、subtitles、usage_confirmed=true；Idempotency-Key。只排队，工作区校验且一次仅有一个活动制作任务，无语言模型或云 TTS 调用。
- `GET .../narration-jobs` 返回任务状态、阶段、完成镜头数、时长、错误与回执，省略原工程 source。`GET .../{job_id}/audio` 校验工作区、音频文件哈希，返回实际 WAV 试听/下载。私有导出保留完整制作依据。
- Brief build 可选 narration: NarrationOptions；同时提供时不先排无声预览，直接进入本地配音制作；不提供时兼容原行为。重复同一脚本/声音设置复用既有任务，失败后可在视频工作室修正并重新提交。
- 固定时长的超长配音拒绝提交到成片；自动适配逐镜延长，锁定镜头不改写，最大单镜 60 秒/总计 120 秒。IR 1.1 增加可选 Shot.freeze_end_frames(default=0)，只允许真实视频且小于镜头总帧；渲染器 @3 校验原素材时扣除停帧部分，使用 FFmpeg tpad 延长末帧。
- 制作完成自动保存新版本、用户确认用途的音频素材、音轨/字幕、规则报告和预览任务；没有质量确认或高清副作用。completion 指“声音已接入工程并排队预览”，视频最终状态以 RenderJob 为准。
- `POST /videos/{id}/export-local`：expected_revision、confirmed=true；仅非生产模式，在当前高清审核和输出校验通过后，保存到固定工作区 exports 子目录，返回路径、字节、哈希。包括 MP4、所用音频、SRT 和工程 JSON，无用户可选目标路径；不绕过高清质量门槛。
- 旧成片的人工确认绑定本作品、事实、素材及预览字节；titles/shot_history 仅作为确认时的历史比较保留，其他作品变化不撤销本片的确认。当前工程或来源变化仍阻止渲染、下载与本机导出。


## 0.12 实际质量接口

- `POST/GET /api/v1/content/packages/{id}/quality`、`/api/v1/videos/{id}/quality`：POST confirmed=true 创建/复用同作品、版本、依据哈希的不可变规则报告；GET 最近 30 份。
- 对应 `POST .../quality/ai`：管理员、独立资料同意、creator_id、expected_revision、max_cost_cents、Idempotency-Key；只入队，使用共享预算。未知回执不自动重试，不产生内容修改或人工审批。
- `POST /videos/{id}/preview`：expected_revision / confirmed；purpose=preview 真实渲染到 360/640 画布并烧录水印。`GET /preview/download` 校验当前 IR、素材和字节，不设置 output_hash。
- `POST /videos/{id}/quality-review`：expected_revision / confirmed / preview_job_id / report_id / decision / note，绑定当前规则报告、预览及操作者；accept 不能跳过硬阻断。`GET /quality-reviews` 读最近记录。
- `POST /videos/{id}/render` 对 preview_required 工程校验确认；Worker 在提交前后和文件读取时复查。RenderJob.purpose 明确区分 preview/final；发布附件仅接受 final。默认 false 兼容旧调用，网页新工程始终启用，保存/恢复不能关闭既有政策。
- DB 0012、creative_quality@1、compatible_chat@2；OpenAPI、输入 Schema、错误码目录由实际代码生成。质量报告含私有原文，仅同工作区可见并进入私有导出，不进入公共诊断。


## 0.15 / 发布片可选设计

VideoInput 新增可选 `presentation`（旧请求默认 classic）；Shot 增加 `design`、`narration_text`。设计字段包含版式、主标题、短句、说明、最多三项要点、百分比裁切和镜头运动。裁切必须位于源画面内，界面布局需真实授权素材。创建、全工程保存、历史、哈希及缓存均包含设计；改变设计需要新预览和审核。Brief Build 可选 presentation，仅首次建工程生效，重复请求不覆盖已有视频。音频回执区分响度目标和实际是否启用配乐压低；静音不声称已处理。错误码增加 VID_DESIGN_TEXT_OVERFLOW。无新迁移、无新外部接口。以 packages/schemas 实际导出为准。

0.15.1 修复 studio 相机采样，不改变上述请求/IR/审核契约。Provider 注册版本为 5，新任务的镜头缓存及输出 receipt 的 provider_adapter_version 为 pillow_ffmpeg@5，旧镜头缓存不复用；同修订已完成的任务仍按既有 API 幂等政策返回，旧输出文件不改写。旧工程需先保存为新修订，再生成新预览并重新人工确认。API 仍只接受 30fps，独立编辑的 60fps 演示文件不作为 API 新能力。
