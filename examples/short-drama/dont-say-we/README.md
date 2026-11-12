# 《别说“我们”》

Issue #49，原创职场内心短剧。小林认为自己只改过一个按钮；一次追问让她从项目记录里找回观察、取舍和验证。人物、项目及次数均为虚构；有招只呈现实际“项目备注”功能。

这是独立本机制作包，不修改正式产品 API、数据库、生成 Provider 或用户审核状态。角色画面是 AI 生成，配音是本机库存合成声；面试官画外、女主心声，未制作口型同步。当前成片及生成结果以 `validation.json` 和 `edit-manifest.json` 的真实记录为准，不能用本 README 代替完成证据或艺术评价。

## 文件与复现

- `production.json`：动机、因果节拍、逐句表演指示与事实边界。
- `assets/`：实际生成首帧与真实产品高清补录；`capture-evidence.json` 含保存重开证据、实际尺寸与哈希。
- `voice.py` / `generate.py`：独立本机制作，模型版本和每次参数随回执冻结。提交未知时不自动重发，已完成 takes 不覆写。
- `finish.py`：11句对白、雨声与原创程序音乐、字幕、12段剪辑；只有实际片段满足时长才输出，不暗中延长演员末帧。
- `check.py`：完整解码、1230帧、声画时长、字幕与素材哈希、本机生成回执、声音峰值和响度；技术通过不授予艺术/商用通过。
- `archive.py`：只打包明确白名单，排除本地配置、凭据、演示用户库和模型权重；ZIP 内含完成影片、字幕、声音、动态源片、回执和工程。

完整制作包解压后，将 `复现工程/` 内容放入本仓对应路径。需本仓依赖、本机 FFmpeg/微软雅黑字体，以及已安装的隔离 Qwen Python（含 NumPy/Pillow/SoundFile）；本包不下载/打包模型或运行时。已有源片即可重剪，不必重新生成：

```powershell
$env:PYTHONPATH='services/api'
$env:PYTHONUTF8='1'
.data/qwen-clean-runtime/Scripts/python.exe examples/short-drama/dont-say-we/finish.py --take v3
.venv/Scripts/python.exe examples/short-drama/dont-say-we/check.py --take v3
node examples/short-drama/dont-say-we/review-server.mjs
```

本次交付使用 v2，服务器 `http://127.0.0.1:8785/watch` 可播放和保存 v2。重剪使用新 take，不覆写已审看版本。需要重新生成时，先按 `docs/implementation/LOCAL_AI_VIDEO.md` 启动已冻结的本机服务，再按本次回执的首帧/提示词/seed 逐镜调用 `generate.py`；模型存在非确定性，不能保证重跑逐像素一致。未知提交只能查原 prompt_id，不能当作失败重发。

## 真实界面和边界

`capture-launch.cjs` 从 `D:/电脑面试` 载入未改写的真实有招 main/preload/renderer，在本仓新建隔离演示库，阻断 HTTP(S)。不要改成个人数据目录，不要复制账号/录音/真实简历。录制文本明确为“虚构项目练习”。软件并没有代用户面试、替用户发布，片中结果也不是产品效果数据。

Electron 此机的 `Page.startScreencast` 实测被限为1600×900，与截图的高 DPI 尺寸不同；前两次采集不作为高清证据。正式补录用逐帧 `Page.captureScreenshot` 的实测时间戳（上限10Hz，实际速率以回执为准）记录真实键入/保存/选择，再按原生时间选帧合成30fps。不得把这部分 UI 的静止保持称为新生成人物动作。

生成模型 Wan/Qwen 的模型版本与许可来源随回执/本仓许可台账保存；ComfyUI、FFmpeg、字体、CUDA、声音和 ImageGen 输出用途仍须分别核对。没有克隆真人、外部歌曲或未经授权的素材。商业发行许可未获确认；本次仅本机待用户审看，不生产部署，不向第三方平台发布。

回滚：退出本包的 Node 观看服务并还原本次独立目录/文档提交即可；不涉及应用数据库或线上数据。原始 take、失败采集与回执保留在 `.data/short-drama-49`，不能通过覆盖媒体伪造历史。
