# 依赖与素材许可台账 · inventory@1

核对日期：2026-11-05。记录实际安装的版本和上游许可信息，不等同于完整法律意见或商业发行批准。自研代码的产品授权条款由仓库所有者另行决定；本次不擅自选择开源许可证。

锁版本：`package-lock.json`、`requirements.lock.txt`。所有已安装 Python wheel 的 METADATA、许可文件哈希与 npm integrity 记录在 [dependency-inventory.json](docs/evidence/dependency-inventory.json)，可通过 `python scripts/dependency-inventory.py` 更新。

| 运行依赖 | 本轮版本 | 许可依据 | 使用方式 / 核对 |
|---|---|---|---|
| Next.js | 16.4.5 | [官方许可](https://github.com/vercel/next.js/blob/canary/license.md)、安装包 LICENSE：MIT | npm 依赖；不修改源码 |
| React / React DOM | 19.3.1 | [官方 LICENSE](https://github.com/facebook/react/blob/main/LICENSE)：MIT | npm 依赖 |
| lucide-react | 见 lock | npm LICENSE / ISC | UI 图标，无外部图像资产 |
| FastAPI | 0.162.0 | [官方 LICENSE](https://github.com/fastapi/fastapi/blob/master/LICENSE)、wheel：MIT | Python 库 |
| SQLAlchemy / Alembic | 2.1.8 / 1.20.1 | wheel METADATA：MIT | Python 库，冻结初始迁移 |
| LangGraph | 1.2.20 | [官方 LICENSE](https://github.com/langchain-ai/langgraph/blob/main/LICENSE)、wheel：MIT | 本地流程；第三方 LangSmith 追踪明确关闭 |
| Pillow | 13.0.0 | [官方 LICENSE](https://github.com/python-pillow/Pillow/blob/main/LICENSE)、本版 METADATA：MIT-CMU | 本地 MG / PNG 生成；不沿用历史版本许可简称 |
| Celery | 5.6.3 | wheel METADATA：BSD-3-Clause | 可选独立任务进程；本机未连接 Redis |
| PyJWT | 2.15.1 | wheel METADATA：MIT | 本软件自己的会话，非社媒凭据 |
| HTTPX | 0.28.1 | wheel METADATA：BSD-3-Clause | 模型服务网关，无社媒网络写入 |
| OpenPyXL | 3.1.5 | wheel METADATA：MIT | 用户主动上传 XLSX |
| OpenTelemetry SDK | 1.45.2 | wheel METADATA：Apache-2.0 | 本地 spans；未部署外部采集后端 |
| PostgreSQL / pgvector / Redis | compose 指定镜像 | 镜像及全部依赖在商业部署时重新盘点 | 仅提供开发配置，不打包镜像；不将配置存在当成已部署 |

## 视频底座与候选审查

- 当前实际执行器为独立实现的 Pillow MG + FFmpeg Provider，业务真相为 VideoProjectIR。**没有复制 OpenFilm、Motion Canvas、MoneyPrinterTurbo、HiveMtk 的源码**。因此不会假称这些候选已接入或通过其 PoC。
- 本机 `ffmpeg -version` 实际为 `9.0.1-essentials_build-www.gyan.dev`，配置含 `--enable-gpl --enable-version3 --enable-libx264`。应按此实际构建审查 GPL 及编解码器义务，不能概括为 LGPL。项目只以独立子进程调用用户安装的二进制，仓库不分发 FFmpeg；是否打包商业安装器须另审。[FFmpeg 上游许可与说明](https://github.com/FFmpeg/FFmpeg/blob/master/LICENSE.md)。本机访问 ffmpeg.org/legal.html 超时，未把该页面记为已读取。
- OpenFilm [上游 LICENSE](https://github.com/openfilm/openfilm/blob/main/LICENSE) 为 MIT 候选；本轮优先实现最小 Provider 闭环，尚未验证其编辑器集成。Motion Canvas / MoneyPrinterTurbo 待固定具体 commit 并验证，不在运行依赖中。
- ComfyUI/Wan、Blender、OpenCut、Remotion、HiveMtk 均未安装、未复制、未开启收费服务。尤其不因上游代码许可推定模型权重、节点、声音或字体可商用。UI 的高级引擎明确标为“待接入”。

## 字体与素材

本机验收使用操作系统已有微软雅黑渲染文字，不分发字体文件；字体对商业产物的使用范围仍需产品负责人核对。Linux CI 使用系统包 Noto CJK，若打包字体须保留对应许可。生产可设置 `CREATOR_FONT` 指向已授权字体。

PoC 的素材为本软件真实界面截图；画面中的品牌、内容、登记、数据均清楚标注验收测试。没有使用图库音乐、声音模型、真人肖像、第三方 UI 或用户私有资产。PoC 不作为已完成商用授权的广告交付。

## 安全扫描状态

`npm audit --omit=dev` 已实际返回 0 条漏洞。Python `pip-audit` 本机因 pypi.org 连接超时未完成，不能宣称扫描通过；CI 中单独设置阻断检查。许可元数据缺失或多许可依赖仍需在发行前逐项人工核对；自动元数据清单不是“全部兼容”的结论。
