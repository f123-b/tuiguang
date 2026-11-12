# #49：《别说“我们”》独立短剧制作验收

2026-11-12，本机个人使用。目标：交付真实可播放、可保存的原创短剧、字幕与源工程；不是继续输出静态分镜，未生产部署。已输出v2：41秒、1230帧、1920×1080/30fps、48kHz AAC，MP4为19,744,883字节，SHA256 `3630236cd915b953aa6fbb24057c45cbbda225a8a4b4b3137852485a3c8849b0`。技术检查通过，用户艺术评价未代确认。

唯一主模块为 `examples/short-drama/dont-say-we/`，调用链：`production.json` → 独立 Qwen 逐句声音 / ImageGen 首帧 / 独立 Wan 本机生成 / 真实有招隔离补录 → `finish.py` → `check.py` → 本地观看和 ZIP。运行媒体、失败尝试及回执在 `.data/short-drama-49`，不会替用户写入软件人审通过。

## 证据和版本

新人物源镜头1280×704、121帧/24fps；首帧1672×941。声音Qwen3-TTS 1.7B CustomVoice / revision `0c0e3051f131929182e2c023b9537f8b1c68adfe`；Wan/Comfy源码和权重版本随每次真实回执保留。第一镜FP8载入、原生解码；其后FP8载入、512空间块/32帧时间块的VAE解码，是独立影片工作流，不改正式产品的固定工作流。首镜实际1642.7秒；结尾镜实际981.6秒；侧面镜实际991.7秒。相同硬件不同输入，不能据此做普遍加速承诺。

真实有招0.2.24加载实际main/preload/renderer，源仓HEAD `521e1f479c02fc4f00992ef5bcd128ff7fba77cf`；另保存实际编译文件哈希，不能只凭Git提交断言构建内容。新建隔离演示库并阻断HTTP(S)，没有读取真实账户/简历/录音。项目“上传入口 · 虚构项目练习”归属为partial，备注/负责边界实际输入、保存、重开相等。

实测`Page.startScreencast`只有1600×900，早期采集未冒充高清。正式v8为真实高DPI截图按实测时间采集，111张/约20.3秒，2560×1440，按实际时间保持未变化的UI并输出30fps。不是生成10fps人物或24/30fps新生画面。详见制作包`capture-evidence.json`。

## 命令与真实结果

| 命令/动作 | 退出码 | 结果 |
|---|---|---|
| `.venv/Scripts/python.exe examples/short-drama/dont-say-we/check.py`（交付前） | 1 | Finished film not yet available，正确拒绝“未有成片即通过” |
| `.../normalize-capture.py`（早期v1/v2） | 1 | 观测尺寸1600×900，未通过高清门槛；原文件移至忽略目录保留 |
| `.../normalize-capture.py`（v8） | 0 | 611帧、20.366667秒、2560×1440，保存重开核对通过 |
| `.../finish.py --prepare-only`（隔离Qwen Python） | 0 | 11句库存声、41秒混音、SRT/ASS、程序音乐/雨声 |
| `ffmpeg ... loudnorm ...`（mix.wav） | 0 | 输入约−15.67LUFS、−1.50dBTP、LRA4.90；非静音，无削波 |
| `python -m py_compile .../*.py` / `node --check` 四脚本 | 0 | 实际语法检查通过；未据此声称完成成片 |
| 变速/补帧预检（开头源片末段） | 0 | 实际输出70帧、1920×1080/30fps；不暗中补演员静止末帧 |
| 隔离Qwen Python `finish.py --take v2` | 0 | 12段实际剪辑、41秒成片及VideoInput DTO通过的离线IR1.1；未映射真实资产/品牌ID供应用导入 |
| `.venv/Scripts/python.exe .../check.py` | 0 | 1230帧完整解码、声画时长、11句、三条121帧原片、输入/输出SHA通过；RMS0.08870、原声道采样峰0.84057、−15.66LUFS/−1.50dBTP |
| `agent-browser ... open/eval video.play()` | 0 | 实际41秒、非静音、ended=true、1920×1080；首轮waiting/stalled/errors均0。首轮23/1230显示丢帧（1.87%）；释放本次GPU服务后复播仍23/1230、waiting1、stalled/errors0。两轮原始记录保留，不能声称0掉帧或已证明其原因 |
| `.venv/Scripts/python.exe .../archive.py` | 0 | 白名单ZIP、CRC及凭据形态扫描通过，不含模型或个人用户库；最终包哈希随本机bundle-receipt.json冻结 |
| `.venv/Scripts/python.exe .../download-check.py` | 0 | MP4、SRT、ZIP均HTTP200/attachment且字节SHA相等；区间请求206/100字节匹配。未自动确认浏览器系统保存对话框 |

早期命令的额外失败：核心`.venv`无NumPy，改用已装隔离Qwen运行时；FFmpeg不接受时长`.05`，更正为`0.05`。UI的模拟鼠标坐标在不同窗口尺寸下会点到遮罩，改用真实DOM控件聚焦/点击与条件等待；partial模式使用真实“我的负责边界”字段。v1检查将相关立体声折成单声道后测峰，产生约3dB合并增益并报1.18；独立loudnorm实测原片为−1.50dBTP，修正检查为测量原声道（v2峰0.84057），未放宽防削波阈值。均保留旧采集/日志，不覆盖历史或重发未知模型任务。可选旧Windows语音识别低置信/不完整，未纳入对白准确性通过；真人逐字听辨未运行。

## 影响、许可、回滚和未完成项

API、应用数据库、正式视频Provider、正式Prompt/预算/人工审核/平台边界不变。应用仍0.20.0-dev / DB0016 / IR1.1 / 引擎@8，独立影片`short_drama_cut@1`，完整冻结见制作包`film-versions.json`。新增独立剪辑提示词、媒体、字幕、文档和本地观看UI。

没有开通云付费资源，没有调用Runway；本机视频无云视频费用，电费和内置ImageGen实际计费不确定。不克隆真实人物/声音，不含外部歌曲；音乐和雨声程序合成。模型许可台账不能覆盖ImageGen输出、字体、FFmpeg、CUDA等全部商业用途，商业发行未批准。

风险：本机模型会产生背景/手部错误，逐镜取景不意味着原片每个区域都通过；无口型同步，心声形式不能代替真人对白表演。1920×1080为合成画幅，源人物不是原生1080p。用户艺术审看待完成。没有生产部署/发布回执。

独立界面语法/文档检查再次通过；本轮没有修改正式API/数据库，应用全量pytest、Next构建、PostgreSQL迁移回滚和正式Worker端到端未重跑，记为未运行，不套用上一任务的通过数。本地源代码/图像/真实UI补录进入Git；影片、生成源片、库存音轨与完整ZIP在本机忽略目录，不把Git推送称为成片已云端部署。

回滚：退出8785本地Node观看服务，还原本次独立目录/文档提交；保留`.data`原始takes及失败回执，不涉及数据库回滚或线上数据。
