# 可选本地神经声音

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
