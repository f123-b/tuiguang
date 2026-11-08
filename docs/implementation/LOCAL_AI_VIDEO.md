# 本机 AI 动态短剧 · 0.19.0-dev

## 使用

当前机器已单独安装模型和隔离运行时。先从仓库根运行 `node scripts/start-local-video.mjs`（本机 8188），再运行 `npm.cmd run dev`。访问 `http://localhost:3000/studio/video/ai`；本机 WEB_ORIGIN 为 localhost，访问其他域名会被来源保护拒绝写请求。

1. 在素材库上传有权使用的角色首帧，填写来源和用途并核实。真人风格用真人参考，动漫用动漫参考；虚构人物也要检查手、脸和画面。用户自己的角色图不会默认发到云端。
2. 选择品牌、真人/动漫、首帧、单镜动作、画幅、时长和 seed，确认用途后生成。每镜2–5秒，默认1280×704/121帧，原生VAE解码；动作宜简单。512×288仅为低清试算，旧低清试片已被用户否决。生成是真实模型推理，不用静态图平移冒充。
3. 等待真实任务状态，在页面直接播放。排队且未领取的任务可取消；已提交不能伪装撤回。失败不会擅自切换模型。状态未知且有回执时只能“读取已有任务结果”，不会重发生成。
4. 看完整段，检查人物、手部、闪烁、连续性及用途；满意后记录自己的检查结论。未确认片段不能进入制作配方。勾选片段的顺序即镜头顺序，最多12镜；填写分镜标题和短旁白，可选本机声音/字幕后剪辑。
5. 短剧画面使用 cinema 全画幅，只保留小型 AI 标识，分镜标题不叠到人物上。成片仍进入原预览、人工确认、高清合成流程。512×288放大到1080p不会产生高清细节。站外发布仍由用户手工完成。

当前是本地短片段制作能力：**不提供人物对口型；不保证跨镜头身份一致、复杂表演或专业电影质量**。模型输出有时脸部变软、手部或背景形变，需要改参考图、动作或种子重新制作。任一生成、审核或质量检查失败都不以文字片代替。

V2已重拍真人中景/近景并独立剪辑16秒有声审看片，入口 http://127.0.0.1:8788/ 。本机RTX4060 8GB的5秒1280×704近景实际端到端1682.6秒（约28分钟）；高质量设置的资源与耗时明显增加，不能按低清试算速度估计。最大901120像素、尺寸为32倍数；可用49/73/97/121帧。新版本的最终艺术质量仍由用户审看决定。

## 安装边界与固定版本

运行时与权重在 `.data`，不进 Git、不打包给其他用户；主 API 不安装 Comfy 节点、不自动下载模型。新机器须单独安装，当前机器安装记录不是跨机器安装成功保证。

- ComfyUI：`https://github.com/Comfy-Org/ComfyUI`，commit `0decb39ee5b5e17c200334589fc317dbbe98310e`，实际版本0.44.0。启动脚本检查 commit，禁用自定义节点、付费 API 节点、自动浏览器、资产扫描和输出 Prompt 元数据，仅监听127.0.0.1:8188。不要将该端口暴露给局域网/公网。
- Python 3.12.14；独立 `.data/video-gen-runtime`。本机 `.pth` 只读复用已有 Qwen 依赖（Torch2.9.1+cu128、transformers4.57.3、NumPy2.5.4）；Comfy依赖另装在新环境，不修改Qwen环境。实际 torchvision0.24.1+cu128、comfy-aimdo0.6.0、comfy-kitchen0.2.41、av19.0.2。上游提示cu130可用优化，本机cu128使用eager路径已实测，未声称启用优化CUDA内核。
- 原生工作流取自 [Comfy官方Wan2.2教程](https://docs.comfy.org/tutorials/video/wan/wan2_2)；固定 I2V 节点 + 20steps / cfg5 / uni_pc / simple / shift8 / seed输入，24fps输出。当前服务采用GPU VAE；初次CPU VAE试验较慢，实际结果见验收。
- 模型为 [Comfy-Org/Wan_2.2_ComfyUI_Repackaged](https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/tree/ee6f4a40737a995bf5818954cfce6d59443b0f04)，revision `ee6f4a40737a995bf5818954cfce6d59443b0f04`；原生模板还列出同一Comfy-Org的[ModelScope镜像](https://modelscope.cn/models/Comfy-Org/Wan_2.2_ComfyUI_Repackaged)。本机通过该镜像分段下载，逐文件全量SHA256与固定HF LFS值一致。路径和哈希由 `services/api/creator/wan_comfy.py` 冻结；模型合计18,144,966,705字节，另需运行时、临时空间和缓存。

| `.data/wan22-models/` 下路径 | 字节 | SHA256 |
| --- | ---: | --- |
| diffusion_models/wan2.2_ti2v_5B_fp16.safetensors | 9999658848 | 456f901338bd9eadbded3828b819109a9b68e8a525ca5cf8d0049a69fcfeca1e |
| text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors | 6735906897 | c3355d30191f1f066b26d93fba017ae9809dce6c627dda5f6a66eaa651204f68 |
| vae/wan2.2_vae.safetensors | 1409400960 | e40321bd36b9709991dae2530eb4ac303dd168276980d3e9bc4b6e2b75fed156 |

本机配置（不含密钥）：`.env` 中 `VIDEO_GEN_BASE_URL=http://127.0.0.1:8188`，`VIDEO_GEN_MODEL_DIR=D:/推广助手/.data/wan22-models`。新机器按实际路径填写。API先校验完整权重哈希，再检查原生节点及模型注册；只接受 loopback HTTP 地址，不接受外部视频网关或任意工作流。服务关闭时不能新生成，已完成且来源仍有效的片段仍能剪辑。重新生成需新的幂等键；客户端网络重放复用原键，不重复产生任务。

## 运维与回滚

生成Worker独立运行，主创作者调度、监测和图文任务不被长视频请求阻塞。Wan与Qwen共用模型目录的 `.inference.lock`；有运行/未知生成任务时配音留在队列，待查清已有生成再继续。未知回执可能仍在消耗GPU，不能自动判断已取消。

DB0015增加 video_generation_jobs；升级前本机备份位于 `.data/backups/pre-0015-20261108-191536.db`，已执行SQLite integrity_check=ok。回滚停止各Worker/API，回到114d3c4并恢复经过验证的升级前备份及匹配媒体；不要执行破坏性降表。关闭生成服务不影响已有MG/录屏等方式。

模型卡Apache-2.0与独立ComfyUI GPL-3.0是上游组件许可信息，不是参考图、人物、声音、字体、FFmpeg或成片商用认证。首次pip安装曾因下载哈希不符失败，未绕过校验；重新下载后安装通过。未开通付费云资源、未使用真实个人肖像、未上线。
