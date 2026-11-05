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
