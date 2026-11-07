# #35 · 叙事、表达与本地神经配音

日期：2026-11-08。目标是回应“简单、机械、没有深度和趣味”的反馈。唯一主模块为指定内容创作 `briefs / brief_jobs`，声音是支撑这次表达的可选适配器。不是自动导演或生成式真人表演的交付。

## 观察、方案与兼容性

- observed：旧脚本提示词只约束主题、事实、帧数和 JSON，没有具体处境、选择、因果和回扣的创作约束；本机旧样片使用单一 Windows SAPI 朗读。用户明确不接受已有样片。
- hypothesis：功能列表、同一种朗读和均匀节奏可能强化机械感。这是创作判断，不以单元测试认定审美根因或保证满意。
- 调用链：创作要求 `narrative_mode` → 冻结输入与 `story_direction@1` → 可选 AI 分镜 → 人工修改 / 创作复看 → 可选本地配音 → 实测时长 / 字幕 → 预览 → 用户复核。画面建议仍只是建议，当前画面引擎保持原能力。
- 新增功能概览、轻剧情、反差幽默、真实故事四种意图；故事要求处境、摩擦、转折、证据和回扣，明确虚构须标注、产品声明须有事实。原文模式不被擅自改写。
- 旧文档缺少 `narrative_mode` 时快照不补字段，避免改变已冻结哈希；`directed_video@1` 保留。旧排队 Run 缺少 direction_version 时保持旧提示词。没有数据库迁移，DB 0014 / VideoIR 1.1 / pillow_ffmpeg@5 保留。
- 创作复看是人工问题清单，既有事实/素材/预览审核仍独立生效，不自动批准。不能把有问号、时长不同或旁白不等于字幕当作“好看”的证明。

## 可选声音与来源

`neural_speech.py` 调用独立本地 Python 子进程；JSON 通过 stdin，不用 shell，不联网或自动下载模型。配置完整才在现有配音下拉中出现 Kokoro 音色；SAPI 保留。失败明确报错，不暗中改音色或请求云服务。冻结五个模型/词典文件 SHA，回执保留实际 runtime_version。排队后权重变化、合成回执不符或提交前来源改变都会失败，工程不被覆盖。Windows 子进程显式使用 UTF-8，处理中文路径和文本。

本机隔离运行时：Python 3.12 / sherpa-onnx 2.0.1 / sherpa-onnx-core 2.0.1 / NumPy 2.5.4。模型为 `kokoro-multi-lang-v1_0`，model.onnx SHA256 `b40f62b166ac8164b0627ef48a0b358eda0985e272fb03ef5252e7206305da11`。权重、二进制、音频和安装环境保存在被忽略的 `.data/`，不加入生产依赖锁或 Git。

来源：[官方模型说明](https://k2-fsa.github.io/sherpa/onnx/tts/all/Chinese-English/kokoro-multi-lang-v1_0.html)、[模型发布包](https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/kokoro-multi-lang-v1_0.tar.bz2)、[Kokoro 权重说明](https://huggingface.co/hexgrad/Kokoro-82M)。下载包 LICENSE 为 Apache-2.0，两个运行时包 METADATA 为 Apache；模型依赖的 espeak 数据等打包组件还须独立核对，不能把顶层许可当作全部组件或声音商业用途的认证。完整分发审查与隔离运行时漏洞扫描本轮未完成。

## 独立导演剪辑样片

片名《别让“我们”挤掉“我”》，57.5 秒 / 1920×1080 / 60fps 合成。三种本地合成声音、面试追问情景、动态文字与小表情、具体知识库示例、真实有招资料整理界面。音乐和音效为程序合成，不使用第三方歌曲录音。配音保留原始生成时长，不为卡片强行加速。

本机交付目录 `.data/有招故事片-20261108/交付文件/`；脚本 `story_edit.py`、timeline、逐段声音回执、来源 SHA 和检查回执另随交付包保存。它是独立编辑样片，并非本软件一键自动分镜后的效果；API/Worker 的 trace_id、creator_run_id、content_id、video_project_id、shot_id、render_job_id 对此独立样片均为 null。没有创建虚假的人工审核记录。

有招真实界面沿用隔离演示捕获，源 checkout `521e1f479c02fc4f00992ef5bcd128ff7fba77cf` / 客户端 0.2.24；没有读取个人简历或账号，也不演示未经配置的 AI 回答。知识库方案是虚构练习，片中标注“示例做法 / 非有招界面 / 非客户案例”；测试边界是思路，未伪造通过结果。

实拍素材：[Artem Podrez · notebook](https://www.pexels.com/video/a-person-writing-on-a-notebook-8519332/)、[Taryn Elliott · typing](https://www.pexels.com/video/close-up-of-a-person-typing-on-laptop-6183190/)，按 [Pexels License](https://www.pexels.com/license/) 编辑用于情景示意。只呈现无法辨认身份的手部，不宣称客户或摄影作者背书。原素材分别 30 / 25fps；60fps 是合成输出，不把重复采样或镜头运动当作原生 60fps 实拍。字体仍使用本机安装字体，其商业用途独立确认。

## 真实验证记录

命令从仓库根执行，Python 指 `.venv/Scripts/python.exe`，设置 `PYTHONPATH=services/api`、`PYTHONUTF8=1`；私有剪辑脚本用本机已有 Python/NumPy/Pillow。完整结果在本轮结束时补记。

| 命令 / 范围 | 退出码 | 实际结果 |
|---|---:|---|
| 新叙事与声音用例，最初未实现时 | 1 | 4 failed / 2 passed；字段、方向、声音未接入 |
| `python -m pytest tests/test_story_direction.py tests/test_neural_speech.py tests/test_narration_pipeline.py tests/test_creation_briefs.py -q` | 0 | 30 passed，14.14 秒；随后增加回执/提交前模型一致性检查，全量结果另记 |
| `python .data/test_kokoro.py` | 0 | 真实 197711 samples / 24000Hz WAV；只证明实际推理成功，不证明听感 |
| `python .data/story_voices.py`（UTF-8） | 0 | 11 段实际中文语音，各自 SHA、声线、时长和运行时回执保留 |
| `python scripts/export-contracts.py` | 0 | 从实际代码导出 OpenAPI 与统一错误码 |
| `npm.cmd run typecheck` | 0 | TypeScript 通过 |
| `npm.cmd run check:boundary` | 0 | 93 个文件通过 |
| `python -m pytest -q` | 0 | 160 passed / 1 skipped，83.33 秒；本机 PostgreSQL 未配置，明确跳过 |
| `python -m ruff check services tests infra scripts` | 0 | All checks passed |
| `python -m ruff format --check`（本轮 10 个 Python 文件） | 0 | 10 files already formatted |
| `python engineering/scripts/validate_contracts.py` | 0 | 工程基础契约检查通过，不当作全部产品验证 |
| `python -m unittest discover -s engineering/tests -v` | 0 | 3 项通过 |
| `python .data/story_actual_pipeline.py` | 0 | 隔离数据库，真实 Kokoro 合成 → 4.333 秒预览 HTTP 200；未经人工复核的高清下载 409；没有批准审核 |
| `python .data/story_edit.py audio inspect render` | 0 | 57.5 秒 / 3450 帧 / 1080p / 60fps MP4、11 段配音、字幕与音轨实际输出 |
| `python .data/story_verify.py` | 0 | 完整解码 3450 帧；相邻 PTS 0.016666–0.016667 秒；AAC 非静音无截波；RMS 0.15690、peak 0.84228；响度 -16.50 LUFS |
| 最终相关四文件 `pytest`（加入未知提示词版本阻断后） | 0 | 31 passed，13.93 秒；Ruff 再次通过 |
| 最终 `npm.cmd run typecheck` | 0 | 空声音提示和本地声音确认文案修订后再次通过 |
| `python .data/story_package.py` | 0 | 31,750,833 bytes ZIP，逐项 CRC 检查通过；仅交付素材，无账号、数据库或密钥 |

成片 SHA256 `16b654650892a698c1980a0def888bc56486cfbefde98f0d4707bebb71098d2f`，11,469,725 bytes。3259/3449 次相邻缩小解码帧有像素变化；少量设计停顿保留，不以变化率衡量趣味。浏览器 60fps 版实际播放到 57.5 秒，error=null / totalVideoFrames=3450 / droppedVideoFrames=221，因此不声称本机浏览器零丢帧；另导出 30fps 兼容播放版降低解码负担，保持内容与声音一致。

兼容播放版在本轮浏览器实际播放至 57.566667 秒结尾，totalVideoFrames=1727 / droppedVideoFrames=0 / error=null。只代表这次本机播放，不保证所有设备。最后多出的约 0.067 秒是帧率转换的尾帧，无旁白截断。交付同时保留 60fps 主版，优先提供 30fps 版观看。

兼容版 SHA256 `5470a06a9ef12e576c9c96415cbc13c01a6125d563eca83726d86a1ba494f830`；交付 ZIP SHA256 `0fda5b29c733c197d813e481639a660a4ca30095935407085027e9d64950dbf3`。原始模型、运行时、个人账号、数据库和私有配置备份均不随包提供。

实际神经配音预览：video_project_id=`3afcd28c4a954710a503c38d1856926c`，narration_job_id=`5ec2e2fdd22d4fe5a49371b3fdbd5fb5`，render_job_id=`0a9f55b172f3494c80f2cd383ef55f11`，音频 SHA `2b47da34be3c5a13900eb86118c0dc341f8b194d9bd04b1815a13c35c0dfec98`。仅合成 QA 数据，独立 SQLite，不是用户作品或云模型请求。

浏览器还实际创建合成验收工作区，保存 contrast 创作要求、刷新后保持所选风格，按原文准备脚本并展开复看清单；四个神经声音与旧声音实际显示，默认选择晓贝。没有勾选使用权/作品批准或发起付费请求。CLI 指针点击在此长页面落到 HTML 元素，未触发表单事件；用页面 DOM requestSubmit/既有按钮 click 后实际保存成功，未把这一 CLI 点击问题当作产品根因。新叙事提示词的付费 DeepSeek 实际生成本轮未运行，覆盖契约与受控回复回归；不能据此声称模型审美改善已获验证。

首轮语音私有脚本没有设置 UTF-8，失败退出 1；之后给生产辅助进程显式编码并重跑实际推理成功。失败没有伪装成声音文件。

本机启用前确认活动模型/配音/渲染均为 0，使用 SQLite backup API 保存一致性备份。首次配置助手假定 `.env` 存在而失败，未停止服务；修正为首次创建后再核对唯一 dev 启动器并重启成功。API/Worker/Web 当前本机运行 0.16.0-dev。原用户密钥仍在既有加密配置中，没有读取或打印明文。

## 影响、安全、版本与回滚

API 增加可选叙事字段、复看建议、可选声音标签和来源回执；DB / 视频引擎无变更；Prompt 仅新指定内容 Run 冻结 story_direction@1；UI 增加叙事选择和复看清单。模型调用仍需已有授权和预算，本轮新增付费云调用 0；本地 CPU、下载和磁盘消耗实际存在。没有社媒登录/上传/发布、凭据复制或生产部署。

版本为 0.16.0-dev / narration_pipeline@2 / kokoro_local@1 / story_direction@1 / inventory@2，stable=false。完整冻结字段见 release_manifest.json；声音具体模型 SHA 和运行时版本见任务回执。回滚代码到基线 `526b8ca608ddf1c85b9b3b46011d159d16b6d1b4`，清除本次两个 KOKORO 配置并在无活动任务时重启；保留 SQLite、旧样片与音频，不需逆迁移。已有新模型任务/新方向任务应先完成或人工处理，不能旧 Worker 忽略新版本后继续执行。

未完成边界：没有真人表演/真人导演替代、自动镜头表演、云端视频、逐词强制对齐、商业许可认证或线上发行。自动脚本的趣味与听感必须由用户观看判断；当前本地神经声音只支持完整安装后的四个声线，不代表任意声音克隆或情绪控制。
