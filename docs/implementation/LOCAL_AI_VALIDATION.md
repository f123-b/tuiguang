# #21 本地模型配置与联调验证

范围：独立模型设置、兼容网关参数、显式列表检查和预算生成测试。用户明确暂不上线，未执行部署或开通付费资源。

先失败：`pytest tests/test_model_diagnostics.py -q` 三项失败（未知配置字段、缺失检查接口、缺失生成接口）。实现后原三项通过，再增加未知回执不重试、错误密钥脱敏两项，五项通过（3.93s）。

实际：`PYTHONPATH=services/api python -m pytest -q` 88 passed / 1 skipped（35.17s，当时含前三项）；最新完整结果见后续总验收。`npm run typecheck` / `npm run build` / `npm run check:boundary` / Ruff 均退出 0，边界 73 文件。OpenAPI/浏览器/真实提供者、0010 本机升级在后续集成记录；未运行项不以单测替代。

迁移 0010 扩展 ModelConfig 与 ModelCheck。默认兼容旧 max_tokens/JSON Object；配置 hash 新字段会阻断尚未执行旧模型任务，禁止悄悄重放。所有凭据继续加密且不回显、不进入 Prompt/快照/导出；换网关不能带走旧密钥。生成联调共享日/月预算，预留后再检查授权/暂停/配置。

回退：停 Worker/API、备份 `.data`、独立保管主密钥，切回已验证父提交；需要完整旧行为时隔离还原升级前备份，不删列 downgrade。真实模型测试须用户在设置页输入凭据并主动发起。没有真实凭据时只报告未运行。


远端 PostgreSQL 首轮失败：Actions 42232372512，生成联调入队 trace `105293be7bf63ed0bf0ca64cc5190d8f` 返回 500，数据库记录 `value too long for type character varying(30)`；probe- 加完整 UUID 超过 Run.slot 的 30 字符契约，SQLite 没有长度强制所以本机通过。修正为受长度约束的随机槽并补跨后端长度断言；同一 Idempotency-Key 仍唯一，不扩大表或改写旧数据。远端修复结果见最新 PR #22 Checks。
