# 《那个选择》本地完整剪辑 · choice_edit@1

用户在 #39 续任务明确要求“先不管 Runway，把视频做完”。此目录是实际可执行的本地剪辑，沿用具体选择与验证的故事，把原人物正脸表演改为第一人称的实拍素材/画外对白。**不使用生成的人物首帧，也不以静帧冒充演员表演。**

实际成片：44.133333 秒、1920×1080、30fps、1324 帧，双声线、原创程序音乐与动作声、真实 UI、字幕和结尾。影片已导出，但艺术质量仍待用户观看判断；不是软件自动导演输出或平台已审核发布内容。

## 本机制作链

1. `dialogue.json` 定义十二个叙事节拍和逐句语气；`voice.py` 用已安装的独立 Qwen 本地环境，一次加载模型、逐句生成并保存模型文件哈希、seed、时长和 GPU 回执。没有克隆真人、外部模型调用或配置变更。
2. `diagram-server.mjs` / `diagram.html` / `diagram.js` 用已有 Three 0.187.0，在本地 8785 端口渲染 360 个 PNG。两镜分别表现记录全部聚集与首批先呈现；画面明确是方案示意，不能作为有招性能证据。代码和图层可改，成片像素是渲染结果。
3. 真实有招隔离实例补录输入、保存、重开。原生录屏实际为 1280×720 / 224 个变化帧；不因设置了 DPR2 就声称是 2K 录屏。另由真实保存状态采集 2560×1440 的界面帧，在读备注镜头使用。没有重画产品按钮、AI 答案或功能区。
4. `finish.py` 核对来源、解码/调色三份授权实拍，将实际对白时长排入十二个独立 Shot，按原生时间取 UI 帧，合成分组声音、字幕并输出 MP4。首版抽帧发现白字对比不足后，对文字侧增加柔和渐变，已重出最终文件。
5. `verify.py` 检查实际视频/音频、字幕范围和顺序、完整解码及实测响度。输出离线 `VideoProjectIR` 1.1 和资产映射；已按真实 `VideoInput` 验证。资产尚未注册进工作台，需要核实、上传并映射实际资产 ID，既有预览和人工审核流程仍适用。

所有路径以本仓根目录为工作目录，本机已存在环境：

```powershell
.data/qwen-clean-runtime/Scripts/python.exe examples/video-production/youzhao-choice/edit/voice.py
node examples/video-production/youzhao-choice/edit/diagram-server.mjs
# 在本地示意镜头页导出360帧，再执行：
python examples/video-production/youzhao-choice/edit/finish.py
python examples/video-production/youzhao-choice/edit/verify.py
```

完整审片包提供`静音画面.mp4`、`混音.wav`和可编辑的`subtitles.ass`。在包内执行`python reexport.py`可以不运行模型、也不获取原始stock素材，重出一个新文件；它拒绝覆盖已有重导出文件。已渲染的画面文字/内部动效需回到源配方重剪，不能承诺每个像素都可直接修改。

`voice.py` 已有 WAV 时明确拒绝覆盖，重录应使用新 take 目录。`finish.py` 是本次制作的固定剪辑配方，不是通用成片服务；重剪前另存本次交付，避免覆盖用户正在审看的版本。Node 服务只绑定 loopback，PNG 上传校验来源/随机令牌、序号、数量和大小。依赖复用本机 Python/Pillow/NumPy/FFmpeg、独立 Qwen 环境与缓存的 Three，没有本轮新增安装。

## 交付内容与来源

本机 `.data/有招那个选择-本地成片-20261108/交付文件/` 包含 MP4、字幕 SRT/ASS、对白/音乐/动作环境声/混音 WAV、离线 IR、资产映射、来源和技术回执。独立审片包另附静音合成画面与配方，**不收录原始 stock 影片、模型权重、用户数据库、配置或密钥**。

实拍使用 Coverr 的 Pencil writing and erasing、Pexels/Cup of Couple 的 Working on a Laptop and Drinking Coffee、Pexels/Artem Podrez 的 A Person Writing on a Notebook。原页面、实际文件哈希与许可 URL 均进入交付清单；源片是素材示意，不是客户经历或背书。音乐与动作声为自编的程序合成，不声称是现场录音或真人钢琴演奏。

公开使用前仍需核对素材/字体/内置声音的适用条款与 AI 标识要求，不将本地技术验收表述为法律或平台许可。最终对外发布由用户在官方平台页面完成。

主应用 0.17.0-dev / DB0014 / IR1.1 / pillow_ffmpeg@5 / fact_bound@2 均不变；离线剪辑版号 choice_edit@1 / offline_choice_compositor@1。移除此目录和相关文档即可回滚代码，不需要数据迁移；旧试片与前期制作包保留。
