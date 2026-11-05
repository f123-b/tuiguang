# M1-002 / 0.2.0-dev 实际验收

任务：[GitHub #3](https://github.com/f123-b/tuiguang/issues/3)。基线 PR #2 尚未合入，本轮增量建立在 `feat/m0-creator-foundation` 上。日期 2026-11-05，Windows / Python 3.12 / Node 22.12。

| 验收 | 实际操作或命令 | 结果 |
|---|---|---|
| 功能先失败 | `python -m pytest tests/test_editorial.py -q`，实现前 | 7 failed，POST plan 404，退出 1 |
| 完整业务回归 | `.venv/Scripts/python.exe -m pytest -q` | 批量事实缓存修复后 36 passed / 1 skipped，退出 0；跳过为本机没有 PostgreSQL 服务 |
| Python 静态检查 | `python -m ruff check services tests infra scripts` | All checks passed，退出 0 |
| TS / 生产构建 | `npm.cmd run typecheck`、`npm.cmd run build` | 均退出 0 |
| 边界 | `npm.cmd run check:boundary` | 44 个源码/配置文件通过；既有禁止出网的完整交接测试仍通过 |
| 契约 | `python scripts/export-contracts.py`、`python engineering/scripts/validate_contracts.py`、`python -m unittest discover -s engineering/tests -v` | 实际 OpenAPI 已生成、示例检查通过、3 tests OK；退出 0 |
| 持久化与并发 | 14 行持久计划、3 线程补齐、乐观锁、过期交换/无效事实回滚、批量原子校验 | 通过；用户锁定/编辑保留，GET 不生成计划 |
| 执行依据 | 改题后拒绝执行、确认后精确使用标题、重复请求同一任务、冻结后拒绝改写 | 通过；旧页面备稿版本不一致返回 409 |
| 事实与权限 | 入队后品牌版本变化、跨工作区详情与修改 | 通过；事实过期停止，费用请求前阻断；跨租户 404 |
| 调度与兼容 | 7 天受控时钟、跳过、暂停、下一次制作、America/New_York DST、graph@1 旧任务 | 通过；未来计划不自动提前执行；不回补错过日期 |
| 实际预算 | 不同未来运营日各预留 60 分、当日限额 100 分 | 第二笔拒绝并暂停，计费日为真实执行日；未知费用不重试 |
| 七篇备稿 | 同时准备 7 个已确认选题，逐个审核并下载 ZIP | 7 个不同标题/正文，copy.txt 含实际标题；无未核实功能 |
| SQLite 升级 | 0001 先写入旧品牌/任务/内容/账本，再重复升级 0002 | 内容保留、费用保留、billing_date 回填、旧 input_snapshot 为 NULL；备份恢复 integrity_check=ok |
| 本机开发库 | 停止 API/Worker，SQLite backup 后启动迁移 | 0001→0002 已完成；升级前备份在私有 `.data/backups/pre-0002-20261105-225127.db`，未提交 |
| 浏览器交互 | agent-browser `xuliu-dev`，测试工作区 | 已实际补齐、改题、锁定、确认、跳过、交换日期；勾选两篇并明确同意后成功入队，后台生成待审稿 |
| 路由与视口 | `SMOKE_*_ID=实际测试资源 node scripts/browser-smoke.mjs` | 35 路由、18 个视口检查通过（总览/日历/详情，各 375/390/768/1024/1440/1920px），无横向溢出，退出 0 |
| PostgreSQL 17 | [Actions 42051765716](https://github.com/f123-b/tuiguang/actions/runs/42051765716)，提交 `350a51d` | 36 passed，含隔离 0001→0002 迁移和旧记录保留；退出 0 |
| SQLite CI | 同一 Actions | 35 passed / 1 skipped（该矩阵不连接 PostgreSQL）；退出 0 |
| 供应链 / Web CI | 同一 Actions | npm ci / typecheck / boundary / build / npm audit 均通过，0 vulnerabilities；pip-audit 报告 No known vulnerabilities found |

影响范围：EDITORIAL / CREATOR / AGENT / Web 页面、OpenAPI、数据库 0002、graph@2、fact_bound@2、local_editorial@2。视频 IR 1.0 / pillow_ffmpeg@1 未变更；实际 20s 视频和缓存回归继续通过。新图可恢复 v1 无计划快照任务，生成模式/模型版本仍必须一致。

本轮未新增运行时依赖、云服务、社媒凭据或发布请求。测试工作区和合成指标只用于验收，无真实平台发布、付费模型请求或生产迁移。许可证与原有 FFmpeg GPL-enabled/字体发行边界仍见 `LICENSE_INVENTORY.md`，不将内部检查等同商业许可或平台审核通过。

规则草稿为七种结构，未接入 AI 热度分析、语义去重、系列栏目、周报与长期学习。手动改题须再次确认；规则选题沿用用户已开启的创作者设置。冻结后事实过期的任务保留依据，在未执行日期安排新稿。批量可能集中占用执行日预算，确认界面明确提示。

回滚：先暂停创作者、停止新 Worker，保留 0002 扩展结构和备份；旧 Worker 不理解新计划确认/计费日期，不能继续处理新任务。完整回退从升级前备份在隔离目录恢复并验证，禁止危险 downgrade。详见 [恢复手册](RECOVERY.md)。未部署生产服务。

浏览器证据：[日历桌面](../evidence/editorial-calendar-desktop.png)、[日历手机](../evidence/editorial-calendar-mobile.png)、[选题桌面](../evidence/editorial-topic-desktop.png)、[批量确认](../evidence/editorial-batch-desktop.png)、[路由/视口回执](../evidence/editorial-browser-smoke.json)、[两个实际备稿任务回执](../evidence/editorial-run-receipts.json)。两个任务均 completed，内容标题与冻结选题一致；回执采于提交前本地开发进程，git_sha 指向基线，不能当作已发行构建证明。测试后已将测试创作者恢复暂停。首轮脚本曾在 `/auth/login` 的登录后跳转尚未完成时报告“无标题”；已让脚本等待实际内容出现，再复跑通过。不是把首次失败改写为通过。

批量期间事实变更的补充复现：`test_brand_change_between_batch_drafts_is_seen_in_same_worker_session` 在第一篇生成后从另一个 DB session 更新品牌版本，原实现实际调用了两次图（断言应为一次），失败退出 1。根因是 `expire_on_commit=False` 的 Worker 会话持有上一篇的 Brand ORM 对象，`db.get` 命中缓存。修复为每次执行前显式 refresh 品牌证据，刷新后再构建输入状态；第二篇收到 `EDITORIAL_FACTS_STALE`，不调用生成图。完整本地回归已通过；修复后远端检查以 PR #4 当前 head 为准。
