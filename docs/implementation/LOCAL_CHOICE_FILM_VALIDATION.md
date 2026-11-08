# #39 续 · 不使用 Runway 的完整本地剪辑

用户要求：“先不管 Runway，把视频做完。”唯一主模块为 `examples/video-production/youzhao-choice/edit/`。交付目标从前期人物试拍改为可直接播放的完整影片；沿用具体项目选择与验证，用真实手部素材、画外问答、原创方案动效与真实产品操作实现。不是新的自动导演服务。

## 实际产物

`有招-那个选择-完整版.mp4`，44.133333 秒 / 1920×1080 / 30fps / 1324 帧，12 镜、12 段对白字幕、立体声。最终文件 21,449,725 字节，SHA256 `45c68345cbb90b8fa1917fcac5183d8f99da8e450783a7df7b8ed7503b56b589`。

开场追问 → 空泛回答 → 擦掉重来 → 文档变多的问题 → 全量/分批方案 → 对比加载和滚动体验 → 在真实有招项目备注中保存 → 再问与具体回答 → 品牌收尾。技术项目是虚构练习；产品证据仅为实际项目库备注输入/保存，不宣称 AI 生成答案、性能数值或录用结果。

独立 Qwen 本地生成 Serena/Dylan 双声线、逐句指令和 seed；没有使用 Runway、图生视频、人物嘴型替换或真人声线克隆。原生成静帧未剪入电影。Three 0.187.0 实际生成360帧纸面方案示意；ANGLE/NVIDIA RTX4060/D3D11 已由浏览器读取。声明动画目的不等于证明其艺术质量。

## 执行与验收

| 实际命令 / 操作 | 真实结果 |
|---|---|
| `python .../edit/verify.py`，成片前 | 退出1，`FILM_MISSING: no completed video file`；没有将计划当作成片 |
| `.data/qwen-clean-runtime/Scripts/python.exe .../edit/voice.py` | 退出0，12份实际WAV；语音3.12/2.96等实际时长逐段保留，脚本/指令/seed/模型文件哈希/资源回执在dialogue-receipts.json。无外部请求 |
| 下载 Coverr 铅笔素材 / Pexels 8472301 | 成功，分别14.719987s/11.96s、1920×1080、实测25fps；不沿用网页50fps文案。初次curl TLS失败/猜测的50fpsURL404后，依据原页实际链接取成功文件，不绕登录/付费 |
| 本地 `window.choiceDiagram.exportFrames()` | 360 PNG 实际生成，两个6秒镜头；`/state` received=360 |
| 真实有招隔离实例采集 | 224个原生变化帧 / 13.456s，保存8.704s / 重开核对11.33s。DPR2录屏仍1280×720，如实记录。另实际采集保存状态2560×1440帧；没有以文件尺寸替代细节判断 |
| `python .../edit/finish.py --prepare` | 退出0，来源哈希/帧目录/十二镜时间表；总1324帧 |
| `python .../edit/finish.py` | 退出0，画面、四组声音、字幕、MP4、离线IR和映射全部实际输出 |
| 首版抽帧检查 | 发现几处白字对比不足；补文字侧渐变，重新完整输出并复核，最终哈希见上。原音频未改变 |
| `python .../edit/verify.py`，最终版本 | 退出0；1324帧/尺寸/时长、12字幕有序且范围正确、48kHz双声道、完整解码通过；RMS0.0833944、采样峰值0.796709、实测-17.0LUFS、真峰值-2.0dBFS |
| `.venv/Scripts/python.exe` 读取IR并 `VideoInput.model_validate` | 退出0，12shots /3audio tracks /12subtitles；仅契约验证，无工作台导入/资产注册/质量批准 |
| Ruff / Node语法 | 退出0；`ruff check .../edit` All checks passed，diagram.js与diagram-server.mjs语法通过 |
| 人工创作质量审批 / 公开发布 | 未运行；没有代用户标记通过或发布 |

浏览器实际播放、封装CRC与最后源文件检查完成后在下方补记。上述技术验收不是“优秀视频认证”。

浏览器补记：`agent-browser --session choice-film` 对本机`/watch`实际播放至ended（静音自动播放用于验收）。返回duration/currentTime均44.133333、totalFrames1324、droppedFrames0、error=null。音频另经实际PCM与响度检查；没有声称人已听完并认可配音。最终对比修正后的S07文字区域已再次抽帧检查。

便携重导出补记：实际将`reexport.py`连同静音画面、混音和ASS放入交付目录执行，退出0；输出SHA256与最终影片逐字节一致。重复执行退出1，明确`OUTPUT_EXISTS`，保留已有文件；这是预期负向用例。逐句WAV复制后已核对全部原哈希，离线资产映射改为包内相对路径；重导出无需模型、网络或原始stock文件。该脚本不替代重新修改画面内部动效的源配方。

源文件校验再次执行：`ruff check .../edit`、Node两份脚本语法、JSON格式化和`git diff --check`均退出0。提交的`edit/render-evidence.json`保留最终媒体、实际浏览器、重导出和运行时证据。最终审片ZIP排除重复重导出文件与原始stock，只打包已剪辑成片/静音画面、音轨、字幕、离线IR、配方和许可来源，CRC会实际校验后交付。

最终封装：`python .data/package_choice.py`退出0，41文件/61,925,978字节，CRC通过；包SHA256 `2bed0b2666af6e98c622e251765e995382355ef30e899d537a819d2485a6d77b`。本机文件为`.data/有招那个选择-本地成片-20261108/有招-那个选择-完整视频与工程-v1.zip`。一次PowerShell管道内嵌Python打包准备因终端编码失败，未产生包；改为UTF-8源文件执行后完成，未改变视频或降低校验。包不包含原始stock、权重、数据库或密钥。

## 影响与版本

调用链：dialogue.json → voice.py（独立本地模型）/ diagram.js（独立GPU镜头）/ 真实UI采集 → finish.py（逐镜编辑、混音、字幕）→ VideoProjectIR1.1离线资产引用 → verify.py / 浏览器 → 私有本地审片文件。不是 API/Worker 自动完成的新功能，没有绕过应用质量审查。

API、数据库、工作台UI、正式VideoProvider、Prompt、预算和模型设置均无变更。应用仍0.17.0-dev / DB0014 / IR1.1 / pillow_ffmpeg@5 / fact_bound@2；独立 `choice_edit@1`、`offline_choice_compositor@1`，模型 Qwen3-TTS-12Hz-1.7B-CustomVoice revision `0c0e3051f131929182e2c023b9537f8b1c68adfe`。实际镜头/源素材/音频哈希及关联本地 trace/video_project/render_job ID 保存在 edit-manifest.json；creator_run_id/content_id=null，不冒充应用数据库任务。

本轮没有新增安装、云生成请求、云付费资源、生产迁移、部署或社媒写操作。只使用本机已安装运行时和授权公共素材；电力/本机时间未折算成免费承诺。

## 来源、许可与安全

- Coverr 原页：https://coverr.co/videos/pencil-writing-and-erasing-boh8dalgsz；许可：https://coverr.co/license。Pexels 8472301 / 8519332 原页与许可由交付清单逐一引用。只用无可识别人脸的手部情景素材，经过剪辑/调色/图形整合，不暗示素材人物使用或推荐有招；审片包不重新分发原始stock文件。
- Qwen使用内置合成声音，Apache-2.0模型许可来源：https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice。精确模型文件摘要随回执保存。模型许可证不是对所有输出权利的法律保证；字体和公开发布的标识要求仍待适用条款复核。
- 有招UI只读代码commit `521e1f479c02fc4f00992ef5bcd128ff7fba77cf`；演示备注来自隔离实例，保存并重开核对。未读取真实简历、账户凭据、私人面试音频或 `.release-secrets`。本轮PID74112已关闭，不影响用户原有应用服务。
- 保留旧视频、旧前期包；新影片在另一个`.data`目录。回滚代码回到c589cbe；没有数据库回滚。保留已下载素材与私有回执，不递归删除用户目录。

## 已知软件CI状态

本轮检查到上一提交 c589cbe 的 Actions42452480828 整体失败，SQLite/Postgres均有7项复盘/AI复核测试失败；Web和依赖审计状态另以该run实际记录为准。最早可见错误为 `LEARNING_EVIDENCE_INSUFFICIENT`（例如trace4892e5dbe5d088af62a81a50dd5e750c），以及反馈计数0。观察到测试用2026-11-01至11-07固定复盘区间，而生成/反馈发生在11-08；这支持时间夹具问题的假设，但本轮未做隔离复现或改动这些业务测试，不能将假设当作已修复根因。

已查询该run实际jobs：api(sqlite)=failure、api(postgres)=failure、web=success、python-advisories=success。未运行的检查不写通过。

完整应用单测/API/Web构建本轮未运行；独立影片媒体验收已实际执行并分列。没有将旧软件CI失败改写为通过，也没有降低门禁。影片源代码继续保留在草稿PR，未合并或上线。
