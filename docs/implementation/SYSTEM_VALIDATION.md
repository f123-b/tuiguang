# D / M4-M6-007 / #13：站内交接与私有设置

0.7.0-dev / DB 0007 / encrypted_workspace@1。新模块 `model_config.py`、`settings_api.py`、`notifications.py`；界面 system-settings/handoff-outcome/ops-console。调用链：设置加密 → 任务冻结工作区模型修订 → 授权/预算 → 模型网关；业务待办/发布提醒 → 持久站内通知 → 用户处理。没有社媒写请求。

实际检查：

- 新设置/通知用例先执行 2 failed（404）；接入后通过。
- 模型执行链用例先执行 2 failed：配置未被任务采用，未授权时错误地执行规则草稿。接入工作区配置和版本门禁后，未授权拒绝、一次受控模拟提供者请求、真实整数分结算/修订冻结通过；这是测试提供者，不冒充真实付费服务联调。
- `.venv/Scripts/python.exe -m pytest -q`：65 passed / 1 skipped，30.32s，退出 0。本机 PostgreSQL 未配置；Windows 离线语音真实测试通过。
- `python -m ruff check services tests infra scripts`、`npm.cmd run typecheck`、`npm.cmd run build`、`npm.cmd run check:boundary`：通过，退出 0；边界 67 文件。构建发现 JSON 命名导出弃用提示，改为默认导入并在整体验收复验。
- `python -m pip check`：No broken requirements found；实际锁定 cryptography 50.0.2、cffi 2.1.1、pycparser 3.12，清单有许可证和 notice 哈希。依赖漏洞扫描待本轮 CI，不能沿用旧结果。

密钥由 Fernet 加密、独立主密钥管理，主密钥不可用返回 503，不回退明文。生产必须显式配置；开发主密钥在私有 .data。模型 URL 受操作者 HTTPS 主机列表约束。保存不联网；密钥不进 Prompt、快照、诊断或私有导出，任务执行中的内存配置不持久化。配置修改阻止旧任务按新配置重放；未知付费结果保留预留，不重复调用。工作区受限角色不能改模型或导出私有资料。

通知支持及时、每日一次、关闭；提醒/已读持久化，重复检查幂等。暂缓/放弃/用户报告平台拒绝只写 user_reported，不写已发布登记或官方核验。私有 ZIP 仅含本工作区记录，可选原始素材，200 MB 上限；不含密码、会话、密钥/密文。它不是完整灾备，也不是发布包。

尚未运行的现有库 0007 升级、浏览器交互、完整 30 秒黄金片与 PostgreSQL 将在整体验收补录。支付/云存储/生产监控未接通且未收费；真实提供商和商业发行仍需凭据、许可与生产审批。回滚保留扩展结构，停用新 Worker；完整恢复需升级前数据库/资产及独立主密钥，不删列降级。
