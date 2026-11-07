# #37 · 语气配音与连续空间镜头试片

2026-11-08。目标：回应“配音生硬、动画不够成熟”。主模块是本地配音 `speech / narration`，另交付一个独立剪辑实验；不把实验片冒充正式引擎或自动导演能力。基线 `66ad22c0e50063ea92cb7caaa0579e36ce84964a`。

## 观察与最小改动

observed：上一条使用 Kokoro 固定声线，适配器没有语气指导；场景以文字/示意卡片逐镜入场为主。用户认为生硬、不够高级。hypothesis：韵律变化、连续空间动作、视觉层次和阅读负担会影响观感。这是创作判断，不能从测试数量推断满意度或审美根因。

本轮增加可选 Qwen 1.7B CustomVoice 本地适配器。调用链：配音页/指定内容 → NarrationOptions.delivery_style → 来源与语气冻结 → 独立 Python/GPU 合成 → 实测时长 → 音轨/字幕 → 视频预览 → 原人工复核。SAPI/Kokoro 保留；不向它们静默套用不支持的语气。语气仅固定预设：原声、聊天、温和讲述、清楚解释；四个内置声音，不支持克隆真人。

- `expressive_speech.py`、`scripts/qwen-speech.py`：完整配置才列出声音；冻结 11 个权重/配置/词典文件、语气指令、seed=37 和采样参数。实际回执保存运行时版本、用时、样本数与 GPU 峰值。离线加载本地 safetensors，明确禁用下载和遥测；GPU 模型用文件锁串行。失败不切换声音/云服务。
- `speech.py`、`narration.py`、`brief_api.py`、`video_edit_api.py`：语气字段兼容缺省 plain；计算既有幂等键时不补 plain 字段。旧排队任务保持原声；语气模型只接受正常语速，保留自然生成节奏。每段最多600字；实测累计超过既有120秒上限后立即停止，不继续合成剩余镜头。
- `narration.tsx`：四个声音和相应语气下拉；其他声音不显示无效预设。声音列表顶层 provider 改为 `local_offline`，避免把所有本地服务标成 Windows SAPI。新增统一错误 TTS_STYLE_UNSUPPORTED / TTS_RATE_UNSUPPORTED。
- `examples/video-motion/`：固定故事和相机的独立实验工具，没有加入正式 EngineProvider 注册，不改变 VideoIR/已有缓存。Three.js 曲面纸页、金属边框、线带、灯光、景深与连续相机，真实UI帧作为纹理；不是生成任意新场景的承诺。

## 实际模型与运行环境

模型：[Qwen 官方 CustomVoice](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice)，revision `0c0e3051f131929182e2c023b9537f8b1c68adfe`。主权重 SHA256 `38b1d5971bdbd982b561cccec982669a53b0537c3cf5e9bd4778ed07bb2f5137`；音频 tokenizer 权重 SHA256 `836b7b357f5ea43e889936a3709af68dfe3751881acefe4ecf0dbd30ba571258`。完整本机下载回执在私有 `.data/qwen-model-provenance.json`。只使用官方内置声音，不使用用户/演员录音。

使用 CPython 3.12.14、qwen-tts 0.1.1、torch 2.9.1+cu128 / torchaudio 2.9.1、transformers 4.57.3、accelerate 1.12.0，RTX4060 Laptop 8GB。bfloat16 / SDPA，do_sample=true / temperature=.8 / top_p=.9 / max_new_tokens=2048；seed37不保证跨硬件字节确定性。语气接口与硬件方式依据 [官方使用说明](https://github.com/QwenLM/Qwen3-TTS#custom-voice-generate)，不引用其效果宣传当作本机测量。

实际失败与修正：Anaconda 3.12.4 创建的隔离环境导入 torch 报 c10.dll / WinError1114；同一套已安装包改用独立 CPython 3.12.14 后实际导入与 CUDA 推理成功。没有把这认定为精确的 DLL 根因或修改生产 Python。2.8 回退安装尝试因 C盘临时空间不足失败，未投入使用；本轮创建的 2.86GB pip wheel 缓存和 D盘重复模型临时文件已清理。后续安装须将 TMP/TEMP/PIP_CACHE_DIR 放到足量磁盘，不使用系统盘承载数GB下载。本机当前语音环境是 `.data/qwen-clean-runtime` 通过 .pth 引用 `.data/qwen-tts-runtime/Lib/site-packages`，两者必须保留，且基于当前独立 CPython；不是可直接复制到其他电脑的安装包。

## 试片与真实性

《有招：把经历串起来》，30秒 / 1920×1080 / 30fps。固定故事是从“讲不清”到整理职责与复习重点；纸页内容是标注的练习示意。真实界面沿用隔离有招0.2.24捕获，源checkout `521e1f479c02fc4f00992ef5bcd128ff7fba77cf`，无个人账号/简历或模型回答。70张原始UI捕获不是原生30fps录屏；30fps为合成输出。

完整旁白 Serena/warm 实际24.8秒，推理49.42秒，GPU峰值4,708,569,600 bytes；没有 atempo、变调或裁切来凑镜头。另提供9.52秒女声及8秒男声试音。音乐/音效为本地程序合成，没有第三方歌曲或实拍素材。素材、音轨和模型留在被忽略的 `.data/`，不推送GitHub。

本机目录 `.data/有招动效试片-20261108/交付文件/`；当前MP4 SHA256 `8acf1f3bed4369c89965a8e46590883896c75b5cae7a50a72fa8427e8977ca9c`，7,463,481 bytes。900帧全部解码，880/899相邻缩小帧有变化（保留设计停顿），PTS间隔0.033333–0.033334秒；原始双声道RMS=.087528、peak=.822768，无截波，响度-16.73 LUFS / truepeak-1.69dBTP。首次校验用FFmpeg默认双声道下混单声道导致幅度提升而断言失败，改为测原双声道后通过；平均单声道峰值=.811802。未改写媒体来掩盖这次测量错误。

浏览器实际播放到30秒，totalVideoFrames=900 / droppedVideoFrames=0 / error=null；渲染器回执为 ANGLE / NVIDIA RTX4060 / Direct3D11。本次播放与技术测量不证明所有设备零卡顿，也不证明艺术质量。独立试片的 trace_id/creator_run_id/content_id/video_project_id/shot_id/render_job_id均为null，未伪造审核。

真实API最终隔离验收的 trace_id=`bea04e601f93ebb79a58d39098183804`，video_project_id=`bfd036a52591489b878f3b70b12b64c3`，narration_job_id=`b1248054c2a24826b4ef5cd5389c279d`；回执为narration_pipeline@3，包含11个文件哈希。与独立试片的null标识分开，不混作同一个渲染任务。

## 实际检查

Python产品命令使用 `.venv/Scripts/python.exe`，设置 PYTHONPATH=services/api / PYTHONUTF8=1；渲染混音脚本使用已有 NumPy/Pillow 环境。

| 命令或路径 | 退出码 | 结果 |
|---|---:|---|
| 新语气契约初次运行 | 1 | 2 failed / 1 passed，证明原实现无语气字段和校验 |
| `python -m pytest -q` | 0 | 168 passed / 1 skipped，89.88秒；本机无PostgreSQL；随后补充120秒提前停止用例，相关最终结果另记 |
| `python -m pytest tests/test_expressive_speech.py tests/test_narration_pipeline.py tests/test_creation_briefs.py -q`（版本/元数据补齐后） | 0 | 29 passed，13.93秒；新增上限用例的首轮失败为测试桩遗漏audio streams，修正后再验 |
| `python .data/qwen_voice_probe.py`（独立环境） | 0 | 两段真实试音，9.52s / 8s，分别17.62s / 14.67s推理；未人工评价听感 |
| `python .data/make_qwen_film_voice.py` | 0 | 通过实际适配器输出24.8秒整段声音、哈希/语气/资源回执 |
| `python .data/expressive_actual_pipeline.py`（最终隔离DB） | 0 | 真实API → warm声音 → 3.733秒带声预览HTTP200；未经人工复核高清409；没有写审核记录 |
| `node .data/motion_server.mjs` + 浏览器逐帧导出 | —（服务持续运行） | 浏览器命令退出0，导出实际完成900张1080pPNG，GPU渲染器确认；服务之后由本轮停止 |
| `python examples/video-motion/mix_sample.py` | 0 | 最终MP4/音轨/混音与抽帧图；原始旁白24.8s |
| `python .data/expressive_media_check.py` | 0 | 完整解码、PTS、双声道音频与播放校验通过；第一次下混测量失败如上 |
| `npm.cmd run typecheck` / `npm.cmd run check:boundary` | 0 | TS通过；94个源码/配置边界通过 |
| `python scripts/export-contracts.py` | 0 | 从实际代码导出OpenAPI及错误码 |
| `python engineering/scripts/validate_contracts.py` / 工程unittest | 0 | 基础契约及3项诊断测试通过 |

最终相关用例为30 passed（14.41秒），退出0；Ruff扫描services/tests/infra/scripts/examples通过，最终TypeScript再次通过。120秒用例先失败（测试桩缺少streams），补齐合法audio streams后通过，验证后续镜头不继续合成且作品修订不覆盖；它是受控时长测试，不是真实121秒声音。首次重复使用隔离QA账号的重跑失败，改用新的隔离DB后真实API验证再次成功。核心依赖安全审计按当前CI实际结果；本轮隔离Qwen/Three环境漏洞审计未运行，不能套用产品依赖审计结论。

最终本机已在活动付费/配音/渲染任务均为0时保存一致性SQLite备份，配置独立声音路径并重启0.17.0-dev。浏览器用既有合成QA工作区验证默认qwen:serena/warm、四种语气实际显示，切换Kokoro后语气控件消失；没有提交作品批准。`ruff format --check`本轮9个Python文件通过。交付ZIP共20,261,424 bytes，CRC通过，SHA256 `f6679d5407897737abaa0ece52903815d602389e43d5a59de8ae671509183a6d`；只含试片、音轨、源代码和来源回执，不含账号、数据库、私有配置或模型二进制。

功能提交 `b7d03e5ef2b5a2d8f812050f0b1c58d338ba4da3` 的 [Actions 42405735411](https://github.com/f123-b/tuiguang/actions/runs/42405735411) 已完成：PostgreSQL、SQLite、Web生产构建/npm审计、Python核心依赖审计四项全部success。[PR #38](https://github.com/f123-b/tuiguang/pull/38)仍开放，未合并、未上线。独立试片工具 `node examples/video-motion/serve.mjs` 也已从版本化源码实际启动，浏览器ready=true/duration=30；没有重复创建正式作品或审核。

## 影响、许可、回滚和未完成

API：可选语气字段与声音元数据；DB：0014不变、无迁移；视频引擎：正式provider@5/IR1.1不变；Prompt：文字创作fact_bound@2/story_direction@1不变，新增spoken_delivery@1语气指令；UI：声音/语气选择；文档：模块地图、状态、契约、手册与许可台账。新增付费云调用0，本地下载、CPU/GPU、磁盘与电力消耗实际存在。

模型卡和qwen-tts/transformers实际许可为Apache-2.0，torch为BSD-3-Clause，Three.js为MIT，SoundFile为BSD；详细打包组件、CUDA运行库、字体及声音用途仍需独立核实，不作全部商业兼容认证。没有克隆真人、外发消息、社媒账号操作或生产发布。

冻结0.17.0-dev / narration_pipeline@3 / qwen_local@1 / spoken_delivery@1 / motion_sample@1 / inventory@3；stable=false，其余见release_manifest.json。回滚到基线66ad22c并在空闲状态移除两个QWEN_TTS配置、重启后选择原声音，不删除数据库、旧视频或资产；无逆迁移。新语气任务应先完成或人工处理再回退，不能旧Worker忽略新参数继续跑。

未完成：艺术/听感须用户看片；空间动效仅是固定脚本的独立试片，尚未成为可组合的正式镜头Provider；无自动角色表演、云视频、真人播音或逐词强制对齐。下一步需根据用户对声音和镜头的选择，收敛可复用制作样式，而非据此次试片宣布自动生成质量达标。
