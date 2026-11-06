# A / M2-004 / #7：事实与修订验收

版本 0.4.0-dev / 迁移 0004。主模块 EVIDENCE；变更 `evidence.py`、`evidence_api.py`、模型/扩展迁移、内容/图文保存钩子、预审/发布包、Web evidence/brand/content/assets。

- 新增用例先执行：`python -m pytest tests/test_evidence.py -q`，3 failed（提案/素材 API 404、内容字段 422）；实现后 3 passed。
- `.venv/Scripts/python.exe -m pytest -q`：49 passed / 1 skipped，16.46s，退出 0。PostgreSQL 未配置本机，跳过项不算通过。
- `python -m ruff check services tests infra scripts`、`npm.cmd run typecheck`、`npm.cmd run build`：退出 0。
- `npm.cmd run check:boundary`：51 个源码/配置文件，退出 0。`PYTHONPATH=services/api python scripts/export-contracts.py` 已更新实际契约。

提案只接受用户提供的资料，不访问外部私有仓库；未上线功能拒绝批准；批准前校验品牌版本和提案状态，阻止重复批准。版本恢复追加新版本并取消审核；历史自报不改写；平台文案全部预审后进入 ZIP。素材停用会使依赖的未发布图文及视频产物失效。历史正文/修改原因留在租户私有表，诊断只记录允许的 ID 与状态。

本轮没有新增依赖/付费请求/社媒凭据或生产操作；字体与 FFmpeg 许可沿用既有清单。尚未运行：本轮本机已有数据升级、浏览器交互和 PostgreSQL CI，将在持续开发集成阶段逐项记录。规则语义去重、产品公开来源定时扫描仍非本次完成范围。

回滚停止新代码，保留扩展表/列；完整数据恢复使用升级前备份，不做删列 downgrade。新数据中的平台版本和修订不能交给旧打包器处理。后续按 COMPLETION_PLAN 的 B/C/D/E 连续实施。
