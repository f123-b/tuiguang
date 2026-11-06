# 核心工程契约与稳定标识

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


## 0.12 实际质量接口

- `POST/GET /api/v1/content/packages/{id}/quality`、`/api/v1/videos/{id}/quality`：POST confirmed=true 创建/复用同作品、版本、依据哈希的不可变规则报告；GET 最近 30 份。
- 对应 `POST .../quality/ai`：管理员、独立资料同意、creator_id、expected_revision、max_cost_cents、Idempotency-Key；只入队，使用共享预算。未知回执不自动重试，不产生内容修改或人工审批。
- `POST /videos/{id}/preview`：expected_revision / confirmed；purpose=preview 真实渲染到 360/640 画布并烧录水印。`GET /preview/download` 校验当前 IR、素材和字节，不设置 output_hash。
- `POST /videos/{id}/quality-review`：expected_revision / confirmed / preview_job_id / report_id / decision / note，绑定当前规则报告、预览及操作者；accept 不能跳过硬阻断。`GET /quality-reviews` 读最近记录。
- `POST /videos/{id}/render` 对 preview_required 工程校验确认；Worker 在提交前后和文件读取时复查。RenderJob.purpose 明确区分 preview/final；发布附件仅接受 final。默认 false 兼容旧调用，网页新工程始终启用，保存/恢复不能关闭既有政策。
- DB 0012、creative_quality@1、compatible_chat@2；OpenAPI、输入 Schema、错误码目录由实际代码生成。质量报告含私有原文，仅同工作区可见并进入私有导出，不进入公共诊断。
