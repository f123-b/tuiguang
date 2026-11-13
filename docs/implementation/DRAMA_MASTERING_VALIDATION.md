# #53 · 短剧前期制作与超分的实际验证

**用户后续明确否决本版嘴型、动作和声音；以下仅保留v3技术与制作历史，不代表艺术通过。重做完整v4的当前结果见[音频驱动验收](AUDIO_DRIVEN_DRAMA_VALIDATION.md)。**

日期：2026-11-13；基线297783bc148287dfea9ffc819073b456b6afb3dd。唯一主模块`examples/short-drama/try-it/v3/`；目标是用剧本→三视图→场景→单镜首帧与动作提示词→动态表演→声音/口型→AI超分→剪辑/检查的顺序，修正《你来试试》的有效清晰度。没有生产上线。

## observed与hypothesis

- observed：旧`try-it/edit.json`的S03和S04第二段从640×360放大至1920×1080；Wan原生1280×704，只有Lanczos，没有神经超分。有效采样不足是可重现事实。
- observed：本轮S04原生3秒处牙齿/嘴部可见，宽脸框v3口型在同处出现糊嘴；Haar首帧检测为[521,171,264,264]，原手工框[400,95,790,470]偏宽。显式缩窄到[521,171,785,471]并保持原声/原片/seed重做v4，抽查帧嘴部形变减轻。旧版均保留，不能将所有模糊归因于同一环节。
- hypothesis：原生生成能力、量化、口型256脸部处理和逐帧SR仍可能影响细节/时序。没有对照实验完全区分这些因素，不声称解决模型全部问题。
- trace/job/shot/prompt/source哈希和graph保留在`.data/short-drama-53/takes/*-receipt.json`；不存在的应用creator_run/content/video_project/render_job为null。四次明确提交，无未知提交自动重发。

## 实际产物

- 7张新PNG：两位人物各正/侧/背三视图、一个空场景、四张单镜首帧；完整图像提示词、英文动态提示词、剧本、分镜表、站位/道具/视线连续性与哈希在v3目录。
- 四条新1280×704/24fps动态，seed5302/5303/5304/5306，121/97/121/73帧；实际耗时951.5/711.2/991.6/521.0秒。S01沿用旧全幅双人动作，S07为真实获授权隔离录屏的虚构数据。
- 三镜口型v3弃用，检测框后的v4与原生细节混合采用；仅嘴周混合，原生眼睛/头发/身体保留。没有生成式换脸修复。完整模型冻结沿用#51。
- 五段实际神经x2超分，共422帧；官方RealESRGAN_x2plus权重67,061,725字节，SHA49fafd45f8fd7aa8d31ab2a22d14d91b536c34494a5cfe31eb5d89c2fa266abb，weights_only加载，现有spandrel0.4.2/torch2.9.1+cu128执行，tile384/pad24/FP16。每段独立回执，不把Lanczos当AI。
- 三个实际22秒/528帧/24fps/48kHz AAC的影片：2K2560×1440、1080p1920×1080、同构图原片对照。原生AI画面1280×704→神经2560×1408，加上下各16px留边；不是原生2K拍摄。字幕、片尾、真实UI最后合成，不做神经文字修复。UI原录屏裁切832×468常规放大，明确保留限制。
- 逐帧SR没有时序模型；无MCI运动插帧。25fps口型转24fps边界最多0.08秒末帧补齐，不循环表演。

## 验收命令与真实结果

| 命令/操作 | Exit/结果 |
|---|---|
| `.venv/Scripts/python.exe examples/short-drama/try-it/v3/preflight.py` 首次 | **1，失败（预期）**：空场景文件尚缺；生成和复制完成后相同命令 **0**，7份参考/逐镜契约通过 |
| 四次`v3/generate.py`（后三次由remaining-takes.py顺序执行） | **0**；四个prompt回执、输入SHA、原生帧数保留 |
| `.data/qwen-clean-runtime/Scripts/python.exe .../v3/prepare.py` | **0**；528帧/22秒重新混音和七句字幕 |
| 三镜v3 sync与preserve-detail，显式repair-sync.py的v4三镜 | **0**；v3抽查男主嘴部模糊，**艺术用途弃用**；v4抽查后采用但非用户艺术通过。上游diffusers提示缺少safetensors后加载已核验官方bin；警告保留，不宣称整个隔离环境安全审计通过 |
| `superresolve.py ... --limit 1` | **0**；同帧A/B可见发丝/眼部边缘变化，耗时1.95秒；只能证实此帧变化，非整片质量认证 |
| `.venv/Scripts/python.exe .../v3/master.py --sr` | **0**；最终采用S01-v3/S02-v4/S03-v3/S04-v4/S06-v4五段神经超分；被弃用口型对应SR试验仍保留 |
| `.venv/Scripts/python.exe .../v3/master.py` | **0**；三部影片真实输出；详情/字节/SHA在edit-manifest.json |
| `.venv/Scripts/python.exe .../v3/check.py` 首次 | **1，失败（预期）**：成片manifest未产生，未假成功 |
| 同一`check.py`最终 | **0**；三片完整解码、各528帧/22秒、声画长度、7字幕时点、四条原生与五份SR来源SHA全部通过；validation.json |
| `ffmpeg ... -af loudnorm=I=-16:TP=-1.5:LRA=9:print_format=json -f null -` | **0**；成片输入实测-16.11 LUFS / -1.38 dBTP / LRA21.60；分析器输出target值不是原片实测 |
| agent-browser实际1080p完整播放 | 到22秒ended=true，528帧、0丢帧、stalled/error0、waiting1（含启动/seek）；非静音。不是人工听审 |
| 2K浏览器首次/复播及原片对照 | 见browser-*.json和后续结果；首次2K限定28秒等待在7.75s超时，之后观察已ended22s、0丢帧，但未证明首次实时播放。保留失败，不将错误选中1080p的早期记录冒充2K验收 |
| 原片对照浏览器独立完整播放 | **未完成验证**：早期操作实际仍选择1080p，不记成功；该文件完整解码和真实附件下载SHA已通过 |
| Node语法/Python AST/git diff检查 | **0**；13个Python文件AST、review-server.mjs的node --check、git diff --check通过；仅Git换行规范化提示 |
| `.../v3/archive.py` | **0**；白名单制作包ZIP CRC与凭据形状扫描通过，无模型权重/运行时；最终文件数量/字节/SHA见bundle-receipt.json |
| `.venv/Scripts/python.exe .../v3/download-check.py` | **0**；五个附件实际下载SHA、七份参考图路由、206区间/416非法区间/405 POST/404 .env通过；未自动操纵保存对话框 |

## 影响/许可/成本/版本

正式API、数据库0016、video_ir_schema1.1、Provider注册、用户审核均未改变。独立制作Prompt drama_production@3、剪辑try_it_edit@3、rrdb_x2_tiled@1、native_detail_mouth_blend@1。应用0.20.0-dev / pillow_ffmpeg@8 / inventory@3保持，完整冻结见film-versions.json。正式VideoInput只收30fps和1080/1920画幅，因此不把本片24fps/2560时间线假标为可导入IR；未注册自动导演/口型/超分服务。

Real-ESRGAN代码许可为官方BSD-3-Clause，保留完整通知；[官方模型路径与推理说明](https://github.com/xinntao/Real-ESRGAN/blob/master/inference_realesrgan.py)、[许可](https://github.com/xinntao/Real-ESRGAN/blob/master/LICENSE)。权重、CUDA、FFmpeg、微软字体及Muse依赖/训练和输出权利不能仅由顶层LICENSE推定，**全部商业发行许可未确认**。仅虚构人物、库存声，无真人克隆；真实UI使用已授权隔离示例，不读真实账号/简历/发布凭据。

不新增付费云资源、不提交收费视频生成。使用本机GPU和内置ImageGen账户能力；电费和真实账户费用不确定。模型权重/运行时/Key不提交Git或ZIP。本次生成完成后检查Comfy队列running0/pending0，校验命令行属于本仓后停止本轮启动的8188进程；8791仅loopback本地审看。

## 已知风险、未运行与回滚

AI细节可能虚构/闪烁，口型、表情和动作仍需用户看整片判断。没有逐字人工听审、独立艺术评审、全应用回归/build、隔离模型环境漏洞审计、DB升级/回滚演练，不以技术检查代替这些结果。人物定妆和成片艺术状态始终pending/false。

2K独立媒体页实际复播完成：/sr.mp4、2560×1440、528帧、ended22秒，elapsed25.3033秒、waiting1、stalled/error0、丢帧10；见browser-2k-direct.json。不能宣称2K在本浏览器完全实时或零丢帧；默认1080p已实测零丢帧，2K另供下载。早期两次源切换按钮在视口外的CLI操作未切换，实际记录仍是1080p，不计作2K/原片测试。另一次等待seeked的CLI读取超时退出1，未据此伪造成片失败/通过；浏览器/工具边界原因未完全分离。

回滚停止本轮8791审看进程，使用原v2影片或297783b源码；保留新原片/前期/失败试验，不删除任何生产数据，不执行DB降级。用户个人本地使用，没有生产版本发布或第三方平台上传。
