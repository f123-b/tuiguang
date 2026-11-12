# 《你来试试》· 独立短剧试拍

任务 #51：重做一场能由动作推进的真人风格小戏。朋友找不到入口，递回手机；小林没有代劳，而是修改自己的设计，再让朋友试一次。最终21.9秒、657帧、1920×1080/30fps，七句中文对白。作品待用户艺术审看。

## 看与保存

工作区本机文件：`.data/short-drama-51/你来试试-v2.mp4`、`你来试试.srt`、`你来试试-制作包-v2.zip`。运行 `node examples/short-drama/try-it/review-server.mjs` 后打开 <http://127.0.0.1:8790/watch>，可观看并保存。仅监听本机，不上传任何平台。

ZIP以 `project/` 为根保留源文件相对路径、所用原片/首帧/声音/实际剪辑段、离线IR和回执。不包含模型、运行时、环境密钥或真实个人资料；不是解压即具备完整模型环境的安装包。

## 本轮具体改变

- 开场双人同框：陈俯身递手机，小林准备接机，目标失败发生在动作里。
- 小林停手，改用让朋友自己完成的策略；“欢迎页，先拿掉”明确她作出的取舍。
- 操作处切手部特写，台词画外续接；陈先试手机再调侃，小林以一次笑容回应，情绪有操作结果作为原因。
- 结尾删去原片反复摇头段，只取2.6–4.0秒的一次笑容回应，台词缩为“对哦”。没有慢放或循环演员动作。
- S01/S02/S06人物对白镜头使用本地音频驱动口型，S03/S04操作镜头使用画外对白；最后2.4秒才出现真实有招项目记录。项目经历、测试次数和结果均为虚构，不证明产品性能。

这是一条约22秒的原创微短剧广告试拍，并不等同于长篇短剧集或已经达到专业发行标准。

## 制作依据与限制

`production.json`记录目的、策略、因果、轴线、起止动作和提示词；`edit.json`记录实际裁切、逐段帧数、台词时点和选片范围。`imagegen-provenance.json`记录内置ImageGen请求（首张为摘要）和不确定项。`film-versions.json`冻结独立作品版本，正式应用仍0.20.0-dev / DB0016 / IR1.1 / pillow_ffmpeg@8。

五条Wan原片均1280×704/24fps，73、121、97、121、97帧；成片1080p是剪辑合成画幅。特写和操作处有裁切，不声称原生1080p人像细节；30fps使用插帧及至多0.1秒片尾对齐。界面源为既有授权隔离录屏2560×1440，未把它伪装成手机原型。

本机模型在S02/S03/S04/S06原片边缘生成了设定以外的人物/服装。`edit.json`保留缺陷记录；S02/S06裁切排除，S03仅取手部。S04在1.6秒前使用宽景，随后切手机操作特写，排除右侧陌生女性和发生口型软化的侧脸。原片没有被篡改或标为全部合格，v1旧剪辑保留本机作为失败画面证据。

MuseTalk为独立试验，未注册为应用Provider。S01/S02/S04用显式脸部ROI加光流；S06光流在快速转头时被阈值拦下，最终使用单独测量、哈希绑定的ROI序列，只处理2.6秒之后。S03跟踪失败的口型未用于成片，操作特写的对白为画外续接。唇形/下脸细节仍可能柔化，听感、艺术效果及用户满意度未由技术检查认证。

v2浏览器首播和复播都完整结束，无waiting/stalled/error，但均记录13/657显示丢帧；逐帧审计另一次为12/657，原因未证实。没有声称已经零掉帧或达到专业发行品质。三份原始播放记录保留在制作包中。

## 真实命令

以下命令以工作区根为当前目录；完整退出码见 [验收](../../../docs/implementation/TRY_IT_DRAMA_VALIDATION.md)。

```powershell
.data/musetalk-runtime/Scripts/python.exe examples/short-drama/try-it/download-sync.py
.data/musetalk-runtime/Scripts/python.exe examples/short-drama/try-it/convert-resnet.py
.data/qwen-clean-runtime/Scripts/python.exe examples/short-drama/try-it/voice.py
.venv/Scripts/python.exe examples/short-drama/try-it/generate.py S01 s01-handoff-v1
.venv/Scripts/python.exe examples/short-drama/try-it/generate.py S02 s02-stop-v1
.venv/Scripts/python.exe examples/short-drama/try-it/generate.py S03 s03-work-v1
.venv/Scripts/python.exe examples/short-drama/try-it/generate.py S04 s04-retry-v1
.venv/Scripts/python.exe examples/short-drama/try-it/generate.py S06 s06-smile-v1
.data/qwen-clean-runtime/Scripts/python.exe examples/short-drama/try-it/finish.py --prepare-only
.data/qwen-clean-runtime/Scripts/python.exe examples/short-drama/try-it/finish.py --take v2
.venv/Scripts/python.exe examples/short-drama/try-it/check.py --take v2
.venv/Scripts/python.exe examples/short-drama/try-it/export-ir.py
```

现有成片复查只需最后两条，不必再生成。重新配音/拍摄/口型/剪辑须显式选择新take并更新剪辑依据；工具会保留既有输出，提交未知状态不自动重发。最终口型命令及参数见验收，失败尝试保存在本机忽略目录，没有覆盖为成功。

`video-project-ir.json`是以已剪辑片段为资产的离线IR1.1，经过DTO校验；需映射真实品牌/资产并重新预览和用户确认后才能导入应用。它没有写入用户工作区、数据库或人审通过。

## 许可、安全与回滚

人物均为虚构AI角色，声音为Qwen库存Serena/Dylan，无真人克隆；音乐、环境声和拟音为原创程序合成。MuseTalk源码固定 `0a89dec45a0192b824e3cf4daf96c239440c5ed8`，上游MIT及依赖声明保留在 `notices/MuseTalk-LICENSE.txt`。四个模型库的revision、字节和SHA256见 `sync-models.json`，但模型卡许可声明不是全部传递依赖/训练素材/输出/字体/FFmpeg/CUDA的商业发行审核。

旧ResNet先与PyTorch官网同一文件独立下载并比对完整SHA256，再显式反序列化官方旧格式并验证全部102个张量无损转换，见 `resnet-conversion.json`。没有接受用户任意pickle输入。独立运行时依赖漏洞审计未运行。

没有开通付费云资源或调用云视频生成服务；电费及内置ImageGen实际计费不确定。软件API、数据库、正式引擎、预算和人工发布边界保持不变。停止8790服务并回到9fb8dae可移除此独立作品代码；保留 `.data/short-drama-51` 即可保全所有媒体。无需数据库回滚，也不应执行迁移或生产部署。
