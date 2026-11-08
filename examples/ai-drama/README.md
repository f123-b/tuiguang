# AI 动态试镜

从仓库根执行 `node examples/ai-drama/review-server.mjs`，访问 http://127.0.0.1:8788/watch。
首页展示本机 `.data/ai-drama-quality-v2/youzhao-choice-v2-b-review.mp4`：16.066667秒、482帧、1280×720、48kHz，真人动态镜头与真实项目备注录像、双声线画外音、字幕和原创程序环境声。人物与项目是虚构演绎，待用户审看；不替用户审核或发布。`/previous`保留两段已被否决的低清旧试片。
新机器没有本机媒体时返回404。使用正式入口和安装边界见 [本机AI视频](../../docs/implementation/LOCAL_AI_VIDEO.md)。

V2的真实生成源是1280×704/24fps的2秒中景与5秒近景，按剪辑重采样到30fps；没有凭空增加人物动作。独立剪辑可运行 `PYTHONPATH=services/api python examples/ai-drama/finish-v2.py --take 新英文版本名`（Windows先设置环境变量），需要本机已完成的生成片段、声音回执和已有真实录屏。脚本保存来源哈希、剪辑清单及结构校验后的离线IR1.1；离线品牌/素材/生成ID需要映射到实际工作区，不能当成已写入正式API的工程。它不是新增的全自动导演，也不提供对口型或专业质量认证。
