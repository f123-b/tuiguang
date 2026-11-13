# 《你来试试》· 完整短剧制作修订3（用户已否决）

本机审看：`http://127.0.0.1:8791/watch`。22秒/528帧/24fps，有声、七句字幕。三个实际MP4在项目根目录`.data/short-drama-53/`：2K超分、1080p、原片对照。制作包ZIP在相同位置。默认播放1080p，按钮可在同一时间切换2K超分与超分前对照。

这是独立作品流程，不是正式工作台已经接入人物生图、MuseTalk或超分。正式应用0.20.0-dev、DB0016、IR1.1和Provider保持。正式VideoInput仅支持30fps/1080或1920尺寸；此24fps/2560影片没有伪装成可导入的正式IR，精确时间线在edit.json/edit-manifest.json。无生产部署、无第三方平台发布、未替用户艺术确认。

## 制作顺序与资料

1. `剧本与连续性.md`、`production.json`：人物目标/阻碍/决定/代价、场景轴线、对白和逐镜起止动作；动作→停手→修改→重试→回应→项目记录。
2. `assets/lin-three-view-v1.png`、`chen-three-view-v1.png`：正、侧、背三视图。同一既有虚构演员外观，真实照片风格；服装、头发、裤鞋固定。作为身份参考，不能把三面板直接当三人同框送入视频模型。
3. `assets/scene-empty-v1.png`：空场景。黑框左窗、木桌、浅墙、右侧银电脑、后架白盒；日内暖光，不跨人物轴。
4. 四张新单镜首帧，七个完整ImageGen提示词文本及`imagegen-provenance.json`，`production.json`另存动作提示词/焦距/视线/焦点。内置ImageGen完成；模型revision/实际费用未返回，不能编造。
5. 本机Wan四条新动态：1280×704/24fps；S01沿用原双人全幅动作。新特写不从640×360裁切放大。原生回执、graph、seed、输入/输出SHA保留。
6. 逐句Qwen库存Serena/Dylan声音复用，重新按24fps剪辑时点混音。MuseTalk后保留原生眼睛、头发、身体，只在嘴周做柔和混合。检测面部范围后显式重做v4口型；被弃用v3留存，不覆盖。
7. RealESRGAN_x2plus真实神经x2：1280×704→2560×1408，上下各16像素留边形成2560×1440。384像素tile/24像素上下文/FP16，逐帧、不做生成式脸修复、不做运动插帧。源25fps口型到24fps的边界最多补0.08秒末帧；没有长时间循环表演。
8. 字幕、片尾、真实项目备注最后合成，不送AI重绘。真实UI仍是原录屏832×468截取常规放大，不冒充原生2K文字。输出原片对照与2K版同时间/同构图，1080p是2K母版缩小兼容版。

## 真实运行命令

在仓库根目录执行，模型路径以本机为准，不含权重分发：

```powershell
.venv/Scripts/python.exe examples/short-drama/try-it/v3/preflight.py
node scripts/start-local-video.mjs
.venv/Scripts/python.exe examples/short-drama/try-it/v3/generate.py S02 s02-close-v3
.venv/Scripts/python.exe examples/short-drama/try-it/v3/remaining-takes.py
.data/qwen-clean-runtime/Scripts/python.exe examples/short-drama/try-it/v3/prepare.py
.venv/Scripts/python.exe examples/short-drama/try-it/v3/repair-sync.py
.venv/Scripts/python.exe examples/short-drama/try-it/v3/master.py --sr
.venv/Scripts/python.exe examples/short-drama/try-it/v3/master.py
.venv/Scripts/python.exe examples/short-drama/try-it/v3/check.py
node examples/short-drama/try-it/v3/review-server.mjs
```

新生成名字是显式版本，不静默重提交未知回执。已完成的动态/SR会核对哈希；口型重拍必须新名字。`repair-sync.py`本轮已执行，不能原名再次运行覆盖结果。模型始终用同一个推理文件锁；权重/服务由独立环境承担，不修改正式应用依赖。

Real-ESRGAN模型来自[官方v0.2.1资产](https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth)，67,061,725字节，SHA256 `49fafd45f8fd7aa8d31ab2a22d14d91b536c34494a5cfe31eb5d89c2fa266abb`。本地安全张量加载后用现有spandrel0.4.2推理，完整许可在notices/。这是来源和执行证据，不是完整商业发行许可证明。

## 已知限制与回滚

逐帧超分没有时序模型，仍可能有细节闪烁或虚构纹理。口型和表演需要用户判断，技术检查不等于艺术通过；不声称商业级真人短剧已获认证。1080p浏览器播放完22秒/528帧零丢帧；2K独立页完成22秒但记录10帧丢帧、25.3秒实际耗时，默认用1080p，2K另供下载。音频逐字人工听审、独立艺术审片、隔离模型环境漏洞审计、全应用回归和数据库升级/回滚未运行。没有新付费云视频请求；电费和ImageGen额度实际花费不确定。

回滚只需停止本次8791审看进程并选用原v2影片/297783b源码；不删除原片和任何生产数据，不改DB、不做downgrade。新前期资料、原生片、被弃用试验和超分文件均保留，便于另开明确版本。实际验证、输出哈希、失败记录见`docs/implementation/DRAMA_MASTERING_VALIDATION.md`及本目录validation.json。
