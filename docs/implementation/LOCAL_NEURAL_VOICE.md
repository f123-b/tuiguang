# 可选本地神经声音

0.17.0-dev 新增可选Qwen 1.7B CustomVoice；这是本地GPU语气指导声音，不需要云密钥。当前本机实际配置：

```dotenv
QWEN_TTS_PYTHON=D:/推广助手/.data/qwen-clean-runtime/Scripts/python.exe
QWEN_TTS_MODEL_DIR=D:/推广助手/.data/qwen-model
```

当前独立CPython3.12.14运行时通过.pth引用.data/qwen-tts-runtime的包，两目录均需保留；移动电脑须重新安装，不能复制这两个路径冒充完整安装包。使用独立CPython3.12创建干净环境，按 [Qwen官方说明](https://github.com/QwenLM/Qwen3-TTS#quickstart) 安装和下载本轮指定权重；本机Anaconda环境曾有torch DLL失败，未继续采用。安装时将TEMP/TMP/PIP_CACHE_DIR设到足量磁盘，模型与CUDA依赖有数GB。本机已验证torch2.9.1+cu128、qwen-tts0.1.1、transformers4.57.3；详见 [模型SHA/完整验收](EXPRESSIVE_MOTION_VALIDATION.md)。

配置后在无活动任务时重启，声音选“语气配音 · 温和女声”等，再选语气。模型只接受正常语速；每段最多600字，建议用短口语段落。语气指导不保证每次听感，预览仍需完整试听；没有声音克隆。GPU不足/环境失效会明确报错，不转云端。要回退请先处理完队列，移除两个QWEN配置再重启并选既有声音；不删原音频或数据库。

0.16.0-dev 开始，配音沿用原制作流程，可选完整安装的 Kokoro 中文声音；不需要 API Key，不调用云服务。默认未安装的机器仍只有既有系统声音，软件不会自动下载权重或偷偷切换声音。

本机已安装并实际通过预览：Python 3.12 隔离环境、sherpa-onnx 2.0.1、sherpa-onnx-core 2.0.1、NumPy 2.5.4；四个声音是晓贝、晓妮、云健、云希。听感、语音名字和用途均不代表真人身份或背书。

其他机器需要自行核对运行环境与许可证后安装可选环境。例如在仓库根运行：

```powershell
py -3.12 -m venv .data/tts-runtime
.data/tts-runtime/Scripts/python.exe -m pip install sherpa-onnx==2.0.1 numpy==2.5.4
```

从 [官方 Kokoro 模型说明](https://k2-fsa.github.io/sherpa/onnx/tts/all/Chinese-English/kokoro-multi-lang-v1_0.html) 获取对应的 `kokoro-multi-lang-v1_0` 完整发布包，保留 LICENSE 和 espeak-ng-data 等完整文件。模型 model.onnx 的本机实际 SHA256 是 `b40f62b166ac8164b0627ef48a0b358eda0985e272fb03ef5252e7206305da11`。不要把其他修订文件冒充本轮验证版本。

在私有 `.env` 配置实际绝对路径（参见根目录 `.env.example`）：

```dotenv
KOKORO_PYTHON=D:/推广助手/.data/tts-runtime/Scripts/python.exe
KOKORO_MODEL_DIR=D:/推广助手/.data/story-assets/kokoro-multi-lang-v1_0
```

路径只对应本机示例，其他机器按真实目录填写。等模型、配音、渲染任务完成后重启 `npm.cmd run dev`；在“指定内容创作”或视频配音页选择“本地神经配音”。修改文本、声音或语速须重新制作并完整播放预览。仍需操作者确认使用权、观看预览并决定高清审核，不能以自动提示替代。

声音来源和模型文件哈希随任务冻结；运行中换权重会报 `TTS_PROVIDER_CHANGED`，请重新提交任务。安装不完整或推理失败报 `TTS_PROVIDER_UNAVAILABLE`，没有云端替补请求。独立进程使用 CPU，首次合成加载权重会有等待；当前每段超时 120 秒。没有逐词强制对齐、声音克隆或情绪参数。

回退时在空闲状态移除两个配置，再重启并选择旧系统声音。不删除原语音文件、工程或数据库。运行时、模型顶层 Apache 许可与第三方组件许可须分别核实；当前私人本地使用测试不是完整商业分发认证。详细证据与限制见 [本轮验收](STORY_VIDEO_VALIDATION.md)。
