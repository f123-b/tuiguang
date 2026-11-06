# C / M5-006 / #11：数据复盘与审批策略

0.6.0-dev / DB 0006 / evidence_review@1 / local_editorial@3。实际模块 `learning.py`、`learning_api.py`、`metrics_io.py`、`pages/learning.tsx`；连接 Metric/Feedback/ContentRevision → 冻结报告 → 待审批 Strategy → 新选题 strategy_snapshot → 冻结任务与事实约束草稿。原始创作者人设不被覆盖；既有锁定计划不被自动改写。

真实执行：

- `python -m pytest tests/test_learning.py -q` 实现前 2 failed（404）；实现后通过。
- 补充安全用例先执行 2 failed：撤销反馈后已批准偏好未停止、映射端点不存在；修复后通过。
- `.venv/Scripts/python.exe -m pytest -q`：58 passed / 1 skipped，24.01s，退出 0。14 条明确合成来源样本、指标缺失 NULL、旧报告冻结、撤销重算、审批/重复审批冲突/回滚、后续新计划绑定策略、跨租户拒绝、文件列映射与错误列拒绝通过。
- `python -m ruff check services tests infra scripts`、`npm.cmd run typecheck`、`npm.cmd run build`：通过，退出 0。
- `npm.cmd run check:boundary`：60 文件，通过。`python scripts/export-contracts.py`、`python engineering/scripts/validate_contracts.py`、`python -m unittest discover -s engineering/tests -v`：通过，后者 3 tests OK，退出 0。

报告按精确平台/窗口/来源分组；同作品同窗口累积快照只保留最新观察用于统计，不叠加；所有缺失值显示未知。报告保留完整指标来源、观察时间、反馈版本及标注修改 ID。统计只是描述性观察，不声称平台因果、预测流量或已由外部 AI 推理。当前没有真实模型周报联调，未来启用必须遵守授权/预算。

反馈/导入可停用。停用会撤销依赖的生效偏好，旧报告不改写；引用停用策略的未执行计划需复核。CSV/XLSX 有行列/压缩后及解压大小上限；用户明确匹配字段，不能由文件指定工作区。所有修改/审批事件只记录允许的 ID/状态，不记录私有反馈原文。

尚未运行的本机 0006 升级、浏览器和本轮 PostgreSQL CI，将在 E 集成报告补齐。没有新增依赖或付费服务；本地规则不需要模型许可，既有媒体/字体边界不变。回滚保留扩展结构并暂停新任务，完整回退使用升级前备份；不要将带策略的新任务交给不理解其语义的旧 Worker。

后续连续实施 D：站内通知/发布提醒、工作区隐私导出、模型与账本设置；随后 E 整链验收。
