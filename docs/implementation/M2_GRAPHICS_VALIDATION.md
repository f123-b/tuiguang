# M2-003 / 0.3.0-dev 图文增量验收

日期 2026-11-06；任务 [GitHub #5](https://github.com/f123-b/tuiguang/issues/5)，交付 [PR #6](https://github.com/f123-b/tuiguang/pull/6)。基线 20f8694 / PR #4，当前分支 `feat/5-graphic-cards`，功能提交 `30bd05e99cfff2d99f5e384d64a22d5f61d5119d`。本轮不合并既有 PR，不部署生产。

| 项目 | 实际命令/操作 | 结果 |
|---|---|---|
| 功能先失败 | `python -m pytest tests/test_graphics.py -q`，实现前 | 6 failed，新增图文 API 404，退出 1 |
| 素材哈希补充用例 | `test_changed_source_bytes_are_not_mislabeled_with_old_hash` | 首次实际返回 200、断言应为 409，失败；增加字节哈希核对后通过 |
| 完整本地回归 | `.venv/Scripts/python.exe -m pytest -q` | 46 passed / 1 skipped，退出 0；本机未配置 PostgreSQL 的迁移测试跳过 |
| Python 静态检查 | `python -m ruff check services tests infra scripts` | All checks passed，退出 0 |
| TS / Web | `npm.cmd run typecheck`、`npm.cmd run build` | 两项通过，生产构建和动态路由成功，退出 0 |
| 发布边界 | `npm.cmd run check:boundary` | 47 个源码/配置文件通过，退出 0；禁止 socket 出网的业务交接回归仍通过 |
| 契约 | `python scripts/export-contracts.py`、`python engineering/scripts/validate_contracts.py`、`python -m unittest discover -s engineering/tests -v` | 实际 OpenAPI/图文 IR Schema 已生成，示例检查通过，3 tests OK，退出 0 |
| 图文真实文件 | 三种版式 × 三种尺寸，PNG/JPG 读取与 ZIP 解包 | 1080×1440、1080×1080、1920×1080 正确；全部页、封面、工程、事实/授权/哈希在包中；封面与第一张 PNG 字节相同 |
| 截图完整性 | 测试三比一色卡 | 图像适配后仍为 3:1，中心像素与原色卡一致；无裁切/虚构界面 |
| 文本与缓存 | 156 字中文标题、自适应布局、图文超高文本、缓存文件损坏 | 标题完整保留；放不下报 GRAPHIC_TEXT_OVERFLOW，不提交部分回执；缓存损坏可重建，哈希一致 |
| 版本/审核 | 旧版本保存和渲染、修改后旧包下载、已登记内容编辑/审核 | 旧页面 409；取消审核/旧包失效；已登记历史只读，不通过重新审核退回可编辑状态 |
| 历史预审元数据 | 已登记后再次调用图文 render | 补充断言先失败（实际 200）；原 API 命中缓存后仍重算 compliance。增加已登记门后返回 409，保留历史预审记录；完整回归通过 |
| 事实/素材 | 跨工作区、未核实素材、文件替换、撤销核实、绝对化标题 | 阻断图文导出；已经准备但尚未登记的 ZIP 和登记入口也重新检查当前依据 |
| 本机升级 | 停止 API/Worker，SQLite backup，启动本地迁移 | 升级前 `.data/backups/pre-0003-20261106-085258.db` integrity_check=ok，0002→0003；私有数据未提交 |
| 旧库保留 | `test_migration.py` 的 0001→head 重复升级与备份恢复 | 原内容/任务/费用保留，图文为空，旧内容继续原封面路径 |
| 浏览器交互 | agent-browser `xuliu-dev` 测试工作区 | 实际建立三页、切换版式/配色、上传真实本软件截图、刷新素材列表、保存、生成预览、逐页查看、人工审核、准备完整图文发布包，均成功 |
| 路由/响应式 | `SMOKE_*_ID=实际测试资源 node scripts/browser-smoke.mjs` | 36 路由与 30 个视口检查通过；总览/日历/选题详情/图文模板/图文编辑器，各 375/390/768/1024/1440/1920px 无横向页面溢出 |
| 实际下载 | 登录本机 QA 工作区，HTTP 下载已审核 PNG/JPG/工程/ZIP；同时检查 Web 3000 代理下载 | 六个图像文件均可打开、三页尺寸 1080×1440、ZIP 含六个图像和相同封面字节；代理返回正确 Content-Disposition / Content-Length 和完整 PNG；退出 0 |
| 自动浏览器文件落盘 | `agent-browser download`，不同目标目录及显式 download-path | 未通过：Download was canceled；受管 Chrome 下载记录为“失败 - 下载错误”，工具快速诊断未完成。HTTP 下载完整，自动浏览器文件保存仍需另一浏览器环境复核 |
| 远端 PostgreSQL / SQLite | [GitHub Actions 42142631856](https://github.com/f123-b/tuiguang/actions/runs/42142631856)，功能提交 `30bd05e` | 全部四个作业 success；PostgreSQL 47 passed（22.01s），SQLite 46 passed / 1 skipped（14.36s），均退出 0；PostgreSQL 17 的业务及 0001→0003 隔离 schema 升级/保留检查通过 |
| 远端 Web / 供应链 | 同次 Actions：`npm run typecheck`、`npm run check:boundary`、`npm run build`、`npm audit --omit=dev --audit-level=high`、`python -m pip_audit --local --format json --output pip-audit.json` | Web 作业 success，npm found 0 vulnerabilities；Python 作业 success，No known vulnerabilities found；Ruff、契约与 engineering tests 也通过 |

影响：GRAPHICS / CONTENT / HANDOFF / Web 图文页面、DB 0003、图文 IR 1.0 和 graphic_cards@1。Agent graph@2、fact_bound@2、local_editorial@2、Video IR 1.0/pillow_ffmpeg@1 均不变。应用版本 0.3.0-dev、stable=false。

没有新增运行时依赖、付费调用、社媒凭据或外部平台发布。字体回执记录本机实际名字和 SHA256；这不是商业字体许可证明。现有字体与 FFmpeg 商业发行边界继续按 LICENSE_INVENTORY 核对。用户提供的素材授权由用户核实，内部预审不代表平台或法律审核结论。

当前是固定版式编辑器，未提供任意坐标画布、图层拖拽、历史版本对比、平台差异文案、TTS/视频多轨或 AI 周报。保存与生成预览分开，失败保留草稿；工程 JSON 是编辑数据，不代表审核通过。

可复核的 QA 产物：[模板桌面](../evidence/graphics-templates-desktop.png)、[编辑桌面](../evidence/graphics-editor-desktop.png)、[事实页](../evidence/graphics-editor-facts-desktop.png)、[真实截图页](../evidence/graphics-editor-screenshot-desktop.png)、[手机预览](../evidence/graphics-editor-mobile.png)、[封面 PNG](../evidence/graphic-card-01.png)、[截图 PNG](../evidence/graphic-card-03.png)、[截图 JPG](../evidence/graphic-card-03.jpg)、[工程 JSON](../evidence/graphic-project.json)、[真实回执](../evidence/graphics-render-receipt.json)、[视口回执](../evidence/graphics-browser-smoke.json)。ZIP 留在忽略的 `artifacts/graphics-manual-package.zip`，浏览器会话留在私有 `.data`，不提交。所有工作区/素材均为验收测试，无第三方发布。图文工程引用当前工作区素材 ID，跨工作区需重新上传并选图；本轮没有工程导入功能。

回滚先停止新进程并备份 `.data`，保留 0003 扩展列；旧打包器不能为含新图文的内容继续导出，否则会忽略用户图文。需要完整回退时在隔离目录恢复升级前备份并验证，不执行删列 downgrade。详见 [恢复手册](RECOVERY.md)。
