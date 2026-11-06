# ADR 0005：个人本地模型网关与联调

2026-11-06，依据用户“先不上线，自己用；补齐模型设置与真实 AI 联调”的授权。本轮不部署生产。调用链：独立模型页 → 配置/读取列表/联调 API → 既有 Worker 和创作者预算 → 网关 → 脱敏 ModelCheck；日更与复盘共用可配置的 Chat Completions 请求参数。

本地管理员可确认信任自定义 HTTPS 公网网关，确认记录与配置修订冻结；生产仍遵守服务端允许列表。地址禁止账号、查询、片段、内网/保留 IP 和非 HTTPS。更换网关须重新输入密钥，不能静默转发旧密钥。密钥仍 Fernet 加密，只服务端执行时解密。

GET /models 仅在确认后发起，不生成内容；记录受限模型 ID 与脱敏 HTTP 分类，不展示提供者原始错误。生成联调单独入队，要求创作者授权/运行状态、单次金额确认、Idempotency-Key，与既有日/月预算共用账本；只发送固定测试 JSON，不上传品牌私有资料。回执未知不重试，人工核对沿用原流程。预留后再次检查授权和配置。

迁移 0010 扩展配置兼容参数与 ModelCheck，不改既有事实、内容、成片或账本。配置 public hash 新字段会阻断尚未执行的旧模型任务，不能悄悄重放。源码和测试不含真实凭据。

兼容契约依据官方 [模型列表](https://developers.openai.com/api/reference/resources/models/methods/list) 与 [Chat Completions](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create)。不同兼容服务对 JSON 模式和 token 参数不同，用户可显式选择，不在失败后自动改参数重试。真实模型联调仍需用户在本地设置密钥并主动授权测试。
