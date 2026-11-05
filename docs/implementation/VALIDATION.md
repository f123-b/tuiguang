# 首轮真实验收 · M0-001 / 0.1.0-dev

日期：2026-11-05；本机 Windows、Node 22.12、Python 3.12、FFmpeg 9.0.1。所有浏览器工作区数据明确标注“验收测试”，未执行第三方平台发布。

| 检查 | 实际命令 / 操作 | 结果 |
|---|---|---|
| 业务 / 权限 / 任务 / 媒体 / 迁移 / 契约 | `.venv/Scripts/python.exe -m pytest -q` | 21 passed，退出 0 |
| Python 静态检查 | `python -m ruff check services tests infra scripts` | All checks passed，退出 0 |
| TypeScript | `npm.cmd run typecheck` | 退出 0 |
| Web 生产构建 | `npm.cmd run build` | 最终模块拆分后复跑通过，动态路由生成成功，退出 0 |
| 人工发布静态边界 | `npm.cmd run check:boundary` | 通过；源码无社媒自动发帖工具 |
| 人工发布动态边界 | `test_no_external_network_in_complete_handoff` | 禁止 socket 出网情况下走完创作/打包/登记 |
| 原设计示例检查 | `python engineering/scripts/validate_contracts.py`、unittest | Schema 校验通过、3 tests OK；与真实业务测试分开 |
| 7 天持久日程 | 受控时钟、每次新建 DB session | 7 天各 1 任务；重复触发不重复 |
| 并发 / 暂停 / 崩溃 | 3 线程入队、暂停不开始、租约恢复 | 通过；不等同真实长期生产压测 |
| 预算 / 模型未知状态 | 限额前阻止 HTTP、注入响应超时 | 通过；未知费用保留预留、不自动重试 |
| SQLite 迁移 / 备份 | `test_frozen_migration_repeat_upgrade_and_backup_restore` | 重复 upgrade、backup、integrity_check 通过 |
| 20 秒双引擎 PoC | `POC_SCREENSHOT=... POC_DURATION=20 python -m pytest tests/test_video.py::test_two_engine_video_and_local_revision_cache -q` | 真截图 + MG，1920×1080 / 30fps / 20s，静音 AAC 音轨；第三镜头修改仅其自身重渲染 |
| 浏览器核心交互 | agent-browser 会话 `xuliu-dev` | 注册、品牌、创作者、审核、ZIP、用户自报、CSV 预览确认均实际操作 |
| 路由与响应式 | `node scripts/browser-smoke.mjs` | 35 个路由有实际标题；375 / 390 / 768 / 1024 / 1440 / 1920 六个宽度无横向溢出。仅验证渲染，不表示计划功能全实现 |
| npm 漏洞扫描 | `npm audit --omit=dev` | 0 vulnerabilities，退出 0 |
| Python 漏洞扫描 | 本机 pip-audit / GitHub CI python-advisories | 本机 PyPI 超时；远端首轮运行已成功，最新 head 仍需最终核验 |
| PostgreSQL / Redis / Celery | 本机 `docker info` | Docker daemon 未运行，本机未验收；CI 配置 PostgreSQL 真集成测试 |
| 外部模型 / GPU / S3 / 支付 / 试点 | 无凭据或服务 | 未运行 / 未实现，不伪造结果 |

## 可复核产物

- [桌面总览](../evidence/dashboard-desktop.png)、[手机总览](../evidence/dashboard-mobile.png)、[人工发布](../evidence/publish-desktop.png)、[指标导入](../evidence/metrics-import.png)。
- [20 秒 MP4](../evidence/mixed-20s.mp4)、[独立镜头工程](../evidence/video-project.json)、[ffprobe 与镜头哈希/缓存回执](../evidence/video-receipts.json)。
- 自动化用例位于 `tests/`；测试产物写入 `artifacts/`，本地私有数据和会话不会提交。

## 影响面与限制

新 API、初始数据库、两种视频 Provider、版本化 Prompt/Agent、内容预审与 UI / 文档均有变更；没有执行生产迁移或发布，没有付费请求。未引入社媒凭据、外部发帖或私密后台数据采集。

合规仅为内部风险提示与人工作品复核，不代表平台官方或法律结论。许可证盘点保留不确定项，尤其当前 FFmpeg 构建为 GPL-enabled，字体和商业发行须另行核对。完整 M1–M7、AI 策略学习、多轨/TTS/GPU、S3 和生产安全设施仍见 `PROJECT_STATUS.md`。

回滚按照 [RECOVERY.md](RECOVERY.md)：暂停 / 停止进程，保留数据库与文件备份，恢复兼容代码；不执行危险初始 schema downgrade，也不会撤回外部平台作品。

## CI 首轮故障记录

观察证据：Actions 42027030417 / API PostgreSQL 在容器初始化阶段返回 `docker create: unknown shorthand flag: 'U'`，业务用例尚未启动。原因已由实际命令确认：GitHub runner 将单引号健康检查命令拆开。已改为 Docker 参数接受的双引号并关闭矩阵 fail-fast，让 SQLite / PostgreSQL 分别给出结果。Web 与 Python 漏洞扫描在该轮已通过。修复后的完整结果以最终 Actions 链接为准，不将首轮失败改写为通过。
