# #51 ·《你来试试》短剧试拍验收

## 任务、证据与方案

目标：回应用户对“人物、分镜生硬、没有剧情”的反馈，实际重做一条有目的、阻碍、选择、结果的真人风格短剧。唯一主模块为 `examples/short-drama/try-it/`，没有修改应用API/数据库/正式引擎。

Observed：#49制作方案的11句全部为画外/心声，提示词禁止说话；开场低头、结尾低头微笑，中间约13秒界面解释。它缺少可见的同场互动。不能据此证明模型是唯一原因。新片通过递手机→停手→修改欢迎页→朋友重试→调侃与回应建立因果。

实际输出为 **21.9秒 / 657帧 / 1920×1080 / 30fps / AAC48kHz**，七句中文对白，五条新Wan原片。S01/S02/S06使用音频驱动口型；S03/S04使用手部/手机特写和画外对白。最终v2排除v1中男主侧脸口型软化的画面。不是用户艺术确认或专业发行合格声明。

## 实际命令与结果

所有命令在 `D:\推广助手` 执行；表内 `.../` 表示重复的 `examples/short-drama/try-it/` 目录，完整复查命令另列下方。日志及原始媒体均保留在 `.data/short-drama-51` 或 `.data/drama51-*`，没有把失败产物改写成成功。

| 命令 | 退出码 / 状态 | 实际结果 |
|---|---:|---|
| `.data/musetalk-runtime/Scripts/python.exe examples/short-drama/try-it/download-sync.py` | 首次1，恢复后0 | 首次网络流中断；按已冻结revision恢复文件下载，四个官方/上游指定模型库所用文件全量SHA256核对 |
| `.data/musetalk-runtime/Scripts/python.exe .../convert-resnet.py` | 0 | 独立下载PyTorch官网旧ResNet，与上游指定文件完整SHA一致；102个张量无损转为可weights-only读取的格式 |
| `.data/qwen-clean-runtime/Scripts/python.exe .../voice.py` 及两次 `--only` | 0 | 原库存声对白保留；补录“欢迎页，先拿掉”和短回应“对哦”；最终七句实际WAV及逐条回执 |
| `.venv/Scripts/python.exe .../generate.py S01 s01-handoff-v1` | 0 | 73帧1280×704/24fps，原始prompt回执 `6e25d6cc-5ba7-4e16-9ea3-9f89e1f1145a` |
| 同上，`S02 s02-stop-v1` | 0 | 121帧，回执 `63aca9b0-6fb3-4ec4-8c62-6541ce098a58` |
| 同上，`S03 s03-work-v1` | 0 | 97帧，回执 `f9acc24f-90fc-4e43-9934-3c678662dd84` |
| 同上，`S04 s04-retry-v1` | 0 | 121帧，回执 `cddae9b5-70ef-46db-b7bd-bc838fa80dc0`；没有重发生成请求 |
| 同上，`S06 s06-smile-v1` | 0 | 97帧，回执 `ca4f73c5-f56d-4e88-a50f-ba1d2e2a142f` |
| `.data/musetalk-runtime/Scripts/python.exe .../sync.py feasibility-v1 ... --bbox 550,100,815,390` | 1 | PyTorch拒绝默认weights-only读取官方旧tar格式ResNet；未禁用全部运行时安全检查 |
| 同上 `feasibility-v2` | 0 | 64帧音频驱动口型试验；约18秒，峰值CUDA分配约5.31GB |
| `sync.py S01-timed-v1 ... --bbox 305,55,520,285` | 0 | 67帧，原音频/原片哈希绑定 |
| `sync.py S02-timed-v1 ... --bbox 700,90,905,355` | 0 | 114帧，最终剪辑按帧对齐 |
| `sync.py S03-timed-v1 ... --bbox 690,45,905,300` | 1 | 光流越过每帧位移阈值，终止；该口型不用于成片，最终操作处只取手部 |
| `sync.py S04-timed-v1 ... --bbox 350,50,595,310` | 0 / 画面不全合格 | 120帧技术完成，实际播放发现侧脸下半脸软化；最终v2在1.6秒后不显示该脸部区域 |
| `sync.py S06-timed-v1/v2 ...` | 1 | 光流保护拦下；v2记录frame24位移约[-15.04,-3.76]，未直接放宽阈值 |
| `.data/musetalk-runtime/Scripts/python.exe .../measure-face.py` | 0 | 97帧中85帧有目标区域检测；缺失帧明确记录并插值，5帧中值处理；测量序列有独立哈希 |
| `sync.py S06-timed-v3 ... --boxes .data/short-drama-51/s06-measured-roi-v1.json` | 1 | 变更工作目录后相对路径解析错误；修正为显式工作区路径，保留失败回执 |
| 同上 `S06-timed-v4` | 0 / 未选用 | 原4秒口型输出；原表演前段反复摇头不适合最终反应，未整段塞入成片 |
| `sync.py S06-timed-v5 ... --bbox 650,50,885,310 --boxes .data/short-drama-51/s06-measured-roi-v1.json --start-sec 2.6` | 0 | 35帧，只选原片2.6秒后的一次回应，新台词0.72秒，不慢放或循环 |
| `.data/qwen-clean-runtime/Scripts/python.exe .../finish.py --prepare-only` | 0 | 最终657帧时间表、七句字幕及混音 |
| `.data/qwen-clean-runtime/Scripts/python.exe .../finish.py --take v2` | 0 | 七段精确输出81/138/120/144/42/72/60帧，21.9秒成片 |
| `.venv/Scripts/python.exe .../check.py --take v1`（成片前） | 1 | 正确拒绝未有成片即通过 |
| 同上（v1成片后早期） | 1 | FFmpeg日志JSON后含进度文本，检查脚本解析失败；修正为读取完整JSON对象，没有放宽媒体阈值 |
| `.venv/Scripts/python.exe .../check.py --take v2` | 0 | 全片解码、657帧、声画时长、五条原片/参考图/声音/S06测量序列哈希、七句字幕、原声道采样峰与响度通过 |
| `.venv/Scripts/python.exe .../export-ir.py --take v2` | 0 | 七镜离线VideoInput DTO通过；未导入应用或写人审通过 |
| Python `py_compile` 本模块11个文件 | 0 | 语法通过 |
| `node --check .../review-server.mjs` | 首次1，修正后0 | 修正多余转义字符，最终语法通过 |
| `agent-browser --session drama51-watch open/eval/click` | 0 | v2非静音播放至21.9秒，ended=true，waiting/stalled/error均0；首轮及复播均13/657显示丢帧（约1.98%）；带逐帧回调的第三次记录12/657。原始记录分别保存，原因未证实，不声称零掉帧或已证明是机器负载导致 |
| `.venv/Scripts/python.exe .../archive.py` | 0 | 白名单106文件、ZIP CRC及凭据形态扫描通过；无模型、运行时、环境密钥或个人用户库 |
| `.venv/Scripts/python.exe .../download-check.py` | 0 | MP4/SRT/ZIP HTTP200附件且SHA一致；字节范围206/100字节吻合；非法范围416、POST405、环境路径404 |

最终复查的完整命令（已实际执行，退出0）：

```powershell
.venv/Scripts/python.exe examples/short-drama/try-it/check.py --take v2
.venv/Scripts/python.exe examples/short-drama/try-it/export-ir.py --take v2
.venv/Scripts/python.exe examples/short-drama/try-it/archive.py
.venv/Scripts/python.exe examples/short-drama/try-it/download-check.py
node --check examples/short-drama/try-it/review-server.mjs
```

浏览器首次直接调用play受自动播放策略拒绝；实际点击播放控件后可正常播放，这不是网络媒体错误。没有自动操纵系统保存对话框。

最终音频实测：RMS 0.08000，原声道采样峰0.84420，输入响度−16.08LUFS、真峰−1.47dBTP；短片输入LRA为21.20，未声称实际LRA等于处理目标9。真人逐字听辨、独立艺术评审、核心全量pytest/构建/数据库升级回滚和独立模型运行时漏洞审计均**未运行**；此次未改动相关业务。

## 影响、许可、风险与回滚

API、数据库、正式视频引擎、正式Prompt/Agent图、预算和用户人工发布契约均不变；UI仅增加8790本地审看页，文档/来源/独立导演提示词及素材变化。应用0.20.0-dev、DB0016、IR1.1、pillow_ffmpeg@8；独立作品 `action_drama@2 / try_it_edit@2`，版本矩阵见制作包。

人物、项目经历、次数和结果为虚构；只使用Qwen库存声，无真人克隆。首帧来自内置ImageGen，具体模型revision及实际计费未知；音乐/环境声/拟音为程序合成。没有开通云付费资源或运行云视频服务。MuseTalk源码MIT及依赖声明保留，四个模型库revision/许可声明/字节与哈希分别冻结；传递依赖、训练资料、字体、FFmpeg/CUDA及全部商业发行权利未全部核验，不能认证商用。

五条人物原片为1280×704/24fps，特写/操作有更小取景，1080p只是成片画幅。生成式画面有边缘错人物和口型细节柔化；原始缺陷与具体选片/裁切保留，不承诺每像素可编辑、所有表情自然或艺术合格。作品未写入正式生成服务，软件本身尚未新增MuseTalk入口。

回滚：停止本轮8790服务，切回9fb8dae（或移除本独立制作模块及文档条目）；保留 `.data/short-drama-51` 可保全媒体和失败证据。不需要数据库回滚，不执行生产迁移。用户艺术审看和商业发行许可仍未完成，未部署、未社媒发布。
