# #19 · V1 本地闭环集成验收

2026-11-06，Windows / Asia-Shanghai。软件 `0.9.0-dev`，DB `0009`，Agent `creator_graph@2`，Prompt `fact_bound@2`，Video IR `1.1`，Provider `pillow_ffmpeg@2`，图文 `graphic_cards@1`，持续制作 `daily_media@1`，规则复盘 `evidence_review@1`，可选模型解释 `grounded_review@1`。`stable=false`。

本报告完成本轮可在本机验证的 V1 工作；不声称生产部署、真实模型付费联调、商业许可证确认或真实用户两周试点完成。阶段功能、兼容性和回退见 [持续开发清单](COMPLETION_PLAN.md) 及各阶段验收报告。

## 真实执行与产物

| 检查 | 命令 / 操作 | 真实结果 |
|---|---|---|
| API / Worker / 媒体 / 安全 / 迁移 | `PYTHONPATH=services/api .venv/Scripts/python -m pytest -q` | 退出 0，85 passed / 1 skipped，32.19s；本机没有 PostgreSQL，未把跳过计为通过 |
| 最后一处通知文案修正 | `pytest tests/test_ai_review.py::test_paid_review_is_idempotent_and_does_not_become_a_daily_task -q` | 先 1 failed，修正后 1 passed；新模型报告通知明确为模型复盘 |
| 静态与构建 | `python -m ruff check services tests infra scripts`；`npm run typecheck`；`npm run build`；`npm run check:boundary` | 退出 0；最终代码的远端结果见下文 |
| 契约 | `python scripts/export-contracts.py`；`python engineering/scripts/validate_contracts.py`；`python -m unittest discover -s engineering/tests -q` | 均退出 0，治理测试 3 项通过；OpenAPI 和错误目录来自实际代码 |
| 页面与宽度 | `node scripts/browser-smoke.mjs`，`SMOKE_BROWSER_SESSION=final-qa`，使用真实 QA 内容/视频/选题/发布包 ID | 退出 0，38 页面渲染、60 宽度检查通过；宽度 375/390/768/1024/1440/1920。只证明渲染和横向溢出，不冒充所有交互通过 |
| 三种真实成片 | `python scripts/local-media-acceptance.py`，仅独立合成测试工作区 | MG、实际软件录屏、混合各 30 秒，1920×1080，H.264/AAC，5 段字幕；退出 0。音轨是自行生成的 220Hz 验收音调，不是旁白或第三方音乐 |
| 局部重算 | 修改混合片第三镜头并重渲染 | `cached=[true,true,false,true,true]`，其他四镜头复用；[前后回执](../evidence/final-local-cache.json) |
| 图文与完整 ZIP | 实际 HTTP 经 3000 Web 代理下载、Pillow 解码、ZIP CRC/成员与视频 SHA 校验 | 三页 PNG 和 JPEG 各 1080×1440；完整 ZIP 含三页双格式、MP4、工程、SRT、来源和检查表。所有图片验证真实格式，不仅检查扩展名 |
| 私有导出 | `/settings/export` 及 `?include_files=true` | HTTP 200，ZIP CRC 通过，JSON 无密码哈希/加密密钥；这不是完整灾备 |
| SQLite 旧数据升级 | 停 API/Worker，`sqlite3.Connection.backup`，`alembic upgrade head`，`PRAGMA integrity_check` | 0008→0009；备份 `.data/backups/pre-0009-20261106-170620.db` 已校验，升级后 `0009 / ok`；先前 0003→0005→0007→0008 分别保存备份。自动测试另验 0001→head 旧记录保留和隔离恢复 |

运行和浏览器状态文件在忽略的 `.data/`，内含会话，不提交。测试创作者已暂停、模型未授权，未生成真实费用或平台发布。截图和片中工作区明确标记合成测试；既有用户记录未被替换。

实际 UI 操作包括：正文改题并以“希望更短”原因保存为新版本；视频工程 V2 恢复 V1 产生 V3，再点击渲染；图文更改配色/说明、保存与真实预览；提交主动反馈并生成当前窗口证据报告；未配置模型时收费按钮禁用；通知全部标为已读。没有从按钮存在推断这些操作成功。重启后 API `/releases/current` 确认为 `aff4201` / `0.9.0-dev` / `0009` / `working_tree_dirty=false`；浏览器播放到 29.396 秒，`readyState=4`、`paused=false`、无媒体错误，时长 30 秒。手机分镜标题修正后截图已更新。

成片：[MG](../evidence/final-mg-30s.mp4)、[真实软件录屏](../evidence/final-screen-30s.mp4)、[混合](../evidence/final-mixed-30s.mp4)。对应 `final-*-project.json` 与 `final-*-receipt.json` 保存实际 IR 和来源。混合黄金片是 V1；随后只改第三镜头为 V2 验证缓存，UI 恢复为 V3，完整发布包绑定 V3。没有用旧回执冒充新版本。

机器可读证据：[ffprobe / 哈希](../evidence/final-media-probe.json)、[真实下载](../evidence/final-downloads.json)、[页面与宽度](../evidence/final-browser-smoke.json)、[图文回执](../evidence/final-graphics-receipt.json)。截图：[总览](../evidence/final-dashboard.png)、[成长](../evidence/final-growth.png)、[手机视频](../evidence/final-video-mobile.png)、[草稿保护](../evidence/final-unsaved-guard.png)、[通知](../evidence/final-notifications.png)。截图已检查，只含合成验收资料。

## 集成中发现并修复的缺陷

- 平台文案未保存时，历史恢复仍可点击。实际 UI 复现 `is enabled=true`；现在文案草稿同时阻止恢复和平台切换，复测两个控件均为 `false`，保存入口仍可用。
- 损坏 ZIP/素材原来返回 200，缺失 ZIP 返回 500。三个失败用例复现；增加读取时 SHA256 校验后全部通过，返回明确的 `ARTIFACT_INTEGRITY_FAILED`。包含原始素材的私有导出不再静默遗漏缺失文件。
- 模型复盘在预算预留后、发送请求前撤销授权，原来仍可能发起请求。独立会话撤销授权的失败用例复现；现在再次刷新授权，取消预留并以 `MODEL_CONSENT_REQUIRED` 停止，完整回归增至 85 项。
- 模型报告通知原来一律写“规则证据报告”。受控模型用例先失败，修正后通过；模型解释仍需人工核对。
- 手机分镜栏标题被横向布局挤成竖排；限定标题不压缩、不换行，保持卡片在栏内横向滚动。

## 下载保存的实际限制

HTTP 下载及代理下载的真实字节、图片格式、ZIP CRC 和媒体哈希通过。agent-browser Chrome 的 `download` 命令仍返回 `Download was canceled`，普通链接保存也曾失败；未证实具体原因，不断言是某项系统策略。尝试内置浏览器备用工具，初始化报 `failed to write kernel assets (os error 3)`。因此“浏览器保存到下载目录”未通过，不能用 HTTP 下载测试代替。最终使用者须在目标浏览器验证保存；本机产物仍可从仓库 `docs/evidence/` 和应用下载接口读取。

## 远端检查与交付

本轮每个目的单独开放 PR、按依赖堆叠，均未合并 main。#8/#10/#12/#14 的阶段 CI 已通过；#16 [Actions 42182954923](https://github.com/f123-b/tuiguang/actions/runs/42182954923) 四项通过，#18 [Actions 42192618269](https://github.com/f123-b/tuiguang/actions/runs/42192618269) 四项通过。SQLite / PostgreSQL、Web 类型/构建/边界/npm audit、Python advisories 分别执行。最终功能提交 `aff4201d2115f29dc355bbe484578aa40f85c858` 的 [Actions 42195495485](https://github.com/f123-b/tuiguang/actions/runs/42195495485) 四项全部通过；[PR #20](https://github.com/f123-b/tuiguang/pull/20) 已开放并附在本任务，依赖 #18。其后文档提交 `2506bc7` 四项也全绿。最终另补一项预算预留后撤销模型授权的并发保护；当前提交的远端状态以 PR #20 的 Checks 为准，不以旧绿色替代。

## 权限、成本、许可和回退

所有平台最终发布仍由用户完成；没有平台凭据、自动上传/发布或绕过限制。样本指标和发布登记明确用户自报。模型调用只在受控测试中替换提供者，不产生真实请求；未知结果保留预算且不自动重试，人工核对有来源但未经提供者验证。

素材来自本软件真实界面和自行生成音调；未新增第三方商用素材。Microsoft 系统字体/离线语音、本机 FFmpeg 编译许可不能从技术测试推断商业可用，详情见根目录 LICENSE_INVENTORY.md。依赖锁版/漏洞检查不等于全部商业授权成立。

本机为开发环境，不部署生产。回退先暂停、停 API/Worker，保存 `.data` 与独立模型主密钥，再切回已验证提交；不执行危险 downgrade。旧 Worker 不理解新任务，不能并行运行；要恢复旧行为，先在隔离目录还原升级前备份并核对文件。详见 [恢复文档](RECOVERY.md)。

仍需外部条件：实际模型/付费提供者联调、目标浏览器文件保存确认、商业素材许可、生产部署与监控/限流/备份/PITR演练、M7 真实用户两周试点。高阶 GPU/3D、自由画布、团队/CRM/GEO、支付/S3 属后续扩展，未伪装实现。
