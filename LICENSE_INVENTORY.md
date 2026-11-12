# 依赖与素材许可台账 · inventory@3

2026-11-12 / #49：独立《别说“我们”》使用三张实际ImageGen合成人物首帧、三条本机Wan新片及两个既有自制AI高清片段、真实有招隔离虚构项目画面，未引入外部歌曲/真人克隆。声音为Qwen库存Serena/Dylan，音乐和雨声为程序生成。来源/回执/哈希与不确定项见[制作包](examples/short-drama/dont-say-we/README.md)。内置ImageGen模型revision和实际费用未返回，记为不确定；模型/代码许可不等于输出、微软字体、FFmpeg/CUDA或全部商业发行许可，未认证商业使用。

2026-11-08 / #37：可选Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice模型卡为Apache-2.0，revision 0c0e3051f131929182e2c023b9537f8b1c68adfe；qwen-tts0.1.1/transformers4.57.3实际METADATA为Apache，torch2.9.1+cu128为BSD-3-Clause，SoundFile0.14.0为BSD。独立试片使用Three.js0.187.0（实际LICENSE为MIT）。权重/二进制不分发入仓；CUDA、其他打包组件、字体和声音用途须分别核实。来源与SHA见 [本轮验收](docs/implementation/EXPRESSIVE_MOTION_VALIDATION.md)。没有克隆真人或外部歌曲；音乐/音效为程序合成。当前隔离语音/动效环境漏洞审计未运行，不套用核心依赖的审计结论。

2026-11-08 / #35 新增可选运行时和独立样片素材：Kokoro 模型包 LICENSE 为 Apache-2.0；sherpa-onnx / core 2.0.1 METADATA 为 Apache，隔离环境 NumPy 2.5.4。未将二进制或权重打包进仓库，espeak 数据及其他随附组件的分发义务尚未完整核对，不能据顶层许可认证商业兼容。官方依据、实际权重 SHA 和限制见 [声音手册](docs/implementation/LOCAL_NEURAL_VOICE.md)。

样片另用 [Artem Podrez / notebook](https://www.pexels.com/video/a-person-writing-on-a-notebook-8519332/) 与 [Taryn Elliott / typing](https://www.pexels.com/video/close-up-of-a-person-typing-on-laptop-6183190/)，按 [Pexels License](https://www.pexels.com/license/) 编辑，用作情景示意，不暗示客户/作者背书。画面只用手部，不辨认身份。音乐和音效为本地程序合成；本机字体、FFmpeg 及声音实际用途仍需独立核对。素材 SHA/来源随本机交付保存。此次没有取得全部组件的商业许可认证，隔离语音环境漏洞审计未运行。

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
- Blender、OpenCut、Remotion、HiveMtk 尚未接入正式运行。0.19已在本机独立安装ComfyUI/Wan，未复制进应用包、未开启收费服务。ComfyUI源码GPL-3.0、固定Wan模型仓库卡标注Apache-2.0；输入、输出、声音和字体仍需独立核实，不据此认证成片商业使用。版本、权重哈希及来源见[本机AI视频](docs/implementation/LOCAL_AI_VIDEO.md)。

## 字体与素材

本机验收使用操作系统已有微软雅黑渲染文字，不分发字体文件；字体对商业产物的使用范围仍需产品负责人核对。Linux CI 使用系统包 Noto CJK，若打包字体须保留对应许可。生产可设置 `CREATOR_FONT` 指向已授权字体。

PoC 的素材为本软件真实界面截图；画面中的品牌、内容、登记、数据均清楚标注验收测试。没有使用图库音乐、声音模型、真人肖像、第三方 UI 或用户私有资产。PoC 不作为已完成商用授权的广告交付。

## 安全扫描状态

0.14 本地配音使用操作者机器已安装的 Windows SAPI / Microsoft Huihui Desktop（zh-CN），不分发语音引擎、权重或声音包。实际输出仅用于合成验收；加入成片前要求操作者确认本次使用权，不能把该确认当作软件认证商业授权。没有新增云端配音服务或依赖。安装和使用条款须由声音使用者按实际许可核实。

`npm audit --omit=dev` 已实际返回 0 条漏洞。Python `pip-audit` 本机因 pypi.org 连接超时未完成；[远端最终 CI](https://github.com/f123-b/tuiguang/actions/runs/42028107582) 已成功完成该检查，112 个包未报告已知漏洞。扫描不是永久安全保证。许可元数据缺失或多许可依赖仍需在发行前逐项人工核对；自动元数据清单不是“全部兼容”的结论。

## 0.7.0 开发增量：模型密钥加密

2026-11-06 实际安装 cryptography 50.0.2（METADATA：Apache-2.0 OR BSD-3-Clause），cffi 2.1.1、pycparser 3.12；用于高层 Fernet 接口，不自制密码算法。已记录 wheel NOTICE/LICENSE 哈希与锁版本，分发时仍需保留上游和其打包组件通知。参见 [官方 Fernet 文档](https://cryptography.io/en/latest/fernet/)。该功能不会保存社媒凭据，也不会默认向外部模型发请求。真实付费 API、语音、音乐和字体许可不因加入本库而获得确认。


2026-11-07 / #31：发布片视觉是本仓库 Pillow/FFmpeg 代码绘制，未引入新的素材库、字体、音乐或云配音依赖。验收使用本仓库真实界面及合成工作区；数字不是经营结果。未把测试音调用于最终配乐。字体、FFmpeg 本机构建和 Windows 系统语音商业使用仍需操作者独立核对。

## #47 内置短剧技能

- shuohao-skills固定5612d2a0bd5f19d978c3ee19d1e42840335e3b4b，七目录，Apache-2.0；完整LICENSE/NOTICE在vendor/skills/shuohao，原始文件未修改。
- zenstory-ai/drama-skills固定3d813c30871b4db5f2387d83bdc3a49db8ce7b2b，仅short-drama-review，MIT通知在vendor/skills/zenstory/LICENSE。
- 128份分发文件哈希冻结在registry.json，禁止运行请求提供的任意脚本。运行时仅固定novel-script离线校验；其余固定参考片段，不启用生图云API或自定义命令。Windows1559项原生自测通过。
- 上述代码/文档许可不认证原作改编、肖像、音色、参考素材或成片商业权利；仍须逐项核实。[安装、来源和边界](docs/implementation/DRAMA_SKILLS_GUIDE.md)。
