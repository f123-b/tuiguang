# F / #17 验收 · 0.9.0-dev

修改：analysis_jobs/api、学习/指标/日历与 Worker、0009、成长/设置 UI、OpenAPI 和版本矩阵。兼容性：全部新增字段可空，旧日更 slot=daily，模型复盘使用独立 slot；模型凭据只执行时解密，输入不含密钥、正文或反馈原文。

先失败：独立授权/费用核对接口未存在，指标版本被拒绝；原始三项用例失败。修复后新增“资料过期和零预算不请求”“外部来源 ID 拒绝且不重试”。

实际执行（Windows，2026-11-06）：
- `PYTHONPATH=services/api .venv/Scripts/python -m pytest -q`：退出 0，81 passed / 1 skipped，32.86s。跳过是本机没有 PostgreSQL；远端另测，不视作通过。
- `python -m ruff check services/api tests --fix`：退出 0；`npm run typecheck`、`npm run build`、`npm run check:boundary`：退出 0，扫描 70 文件。
- `python scripts/export-contracts.py`：退出 0，导出真实 OpenAPI。
- 模型测试均为受控 httpx 回应/超时，没有真实或付费调用。Windows 本地语音实际测试通过；商业授权仍需操作者核实。

成本：共享原子预留，回执未知不重试；人工核对标记 user_reported，不能充当提供者正式账单。权限：仅管理员发起分析/费用核对，按工作区筛选。

回退：停进程、保存最新数据、切回父提交。迁移是扩展式，不自动降级/删除数据；需要还原时使用停机前完整 SQLite 备份，并独立保管主密钥。最后的真实浏览器/三种 30 秒黄金片、0009 本机升级和远端检查汇总到最终集成报告，不用本页单测代替。
