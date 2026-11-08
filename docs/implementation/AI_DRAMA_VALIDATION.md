# #45 · 本机AI动态短剧与质量重拍验收

目标：用户要求类似AI短剧，真人与动漫均支持、先真人，先不依赖Runway、不上线。应用0.19.0-dev / DB0015 / IR1.1；wan_comfy_local@1 / wan_ti2v_fixed@2 / video_recipes@2 / pillow_ffmpeg@8。LLM Prompt、站外发布和旧持续任务边界保持。

## 变更与调用链

主模块 `video_generation.py`：GenerationInput→品牌/参考图/权重验证→DB任务/幂等→独立video_generation_worker→固定wan_comfy图生视频→真实输出校验→未核实Asset→用户逐镜确认→Recipe/generation_job_id→既有配音/字幕/预览/高清审核。API `video_generation_api.py`，前端 `video-drama.tsx`；`schemas.py`可选来源字段在空值时不序列化，兼容旧锁定镜头。`film_types.py`的cinema只留小型标识，标题留在分镜记录，不遮挡人物；真实素材不标成AI。

0015新增任务表与来源、租约、服务回执、错误、输出关联；新增独立进程，不把长推理放到主创作者Worker。Wan/Qwen共享GPU文件锁；运行/未知生成任务期间配音排队。提交意图先落盘，再做唯一POST；未知回执不自动重发，有已有ID才允许显式读取，取消只限未领取任务。私有导出包含任务数据，公开日志不记录Prompt或密钥。API只连接显式端口的127.0.0.1，不接受URL素材或任意工作流。

正式功能与独立导演剪辑有区别：16秒V2由 `examples/ai-drama/finish-v2.py` 剪辑，不是持续任务自动导演。保存的离线IR1.1已通过VideoInput结构校验，离线品牌/素材/生成ID需映射后才能导入实际工作区，不冒充已写入正式API的工程。正式API链路分别有真实生成和受控合成测试覆盖；真实样片未代用户登记素材/成片审批。

## 质量问题：观察与假设

observed：最初API实测真人/动漫各49帧、512×288、24fps、2.041667秒，无声，虽然技术播放成功，但脸/手变形、背景闪烁，且没有形成剧情，用户明确否决。旧预览还开启两秒循环，增加突跳感。旧文件保留为问题证据，不称成片质量通过。

hypothesis：低分辨率、动作/负面提示词与手动分块可能共同影响。核对官方模板后，以1280×704、克制动作/静止背景重新采样；同一新latent分别执行旧分块和原生VAE。两种解码差异较小，因此**不能把旧画质问题单独归因于分块解码**；尺寸与提示词同时变化，未完成单因素因果实验。

诊断将视频归一为640×352，比较演员外固定区域(470,20)-(620,130)的相邻帧平均RGB绝对差：旧试片7.20，新原生0.67、新分块0.86（0–255标度）。相同latent两种解码全帧均差1.76。该指标只描述背景变化，不能评价人物真实性或认证艺术质量。实际图像抽查确认新镜头明显更稳定，仍由用户审看最终质量。

## 真实生成与V2剪辑

- 本机RTX4060 Laptop 8GB、32GB RAM；ComfyUI0.44.0/固定commit，Wan2.2 TI2V-5B固定revision与三份权重全SHA校验。来源/许可/隔离安装见[本机说明](LOCAL_AI_VIDEO.md)。未开启付费云资源，无外部视频请求。
- 初次CPU VAE试验约340.6秒输出2秒片段。正式HTTP/独立Worker实际输出两条低清镜头，Job `a2914b33939d49d39786e9dc60b491dc`（真人）与 `258b8fe856f64e9ab7a28b574cc155ed`（动漫）；另一张有多余手部的插画任务在提交前被取消，未用于新动漫首帧。
- V2中景原生1280×704/49帧/24fps；同采样双解码对照端到端761.35秒，prompt_id `3d48561e-b14b-48e2-88a4-00011a6d7352`。V2近景1280×704/121帧/24fps，prompt_id `fb891cde-8421-4a7d-9476-eb247423fa90`，端到端1682.56秒（约28分钟）。耗时不能按低清速度估计。
- 四段新声音均为本机Qwen内置Dylan/Serena，不克隆真人。保留文本、表达指导、seed101–104、实际样本、时长和模型文件哈希；模型revision按既有固定来源核对为0c0e3051f131929182e2c023b9537f8b1c68adfe。声音为画外音，不驱动嘴型。技术音频检查不等于人工审听。
- 真实有招备注录像SHA256 `faf11b6936c4b90ce16552994ec7f6b7c2203d5d5fc19aed5be79610c1fbe61b`，来自隔离虚构项目；只读源产品，不使用真实简历/账号/面试记录。画面中的技术选择是虚构练习，不是性能数据。镜头取3.6–9.9秒，呈现输入和真实保存；V2-b调整裁切以完整保留保存按钮。
- V2-b成片 `.data/ai-drama-quality-v2/youzhao-choice-v2-b-review.mp4`：16.066667秒、482帧、1280×720/30fps、AAC48kHz、3237050字节，SHA256 `78668d14b60194fff3d027cdf696be3c8fc03263da7dd279e056d48f78d2462f`。24fps生成源重采样到30fps，不声称有482帧独立生成动作。
- 剪辑结构：画外追问→人物停顿→真实项目备注中的选择→人物回看→品牌。音频为新合成画外音和原创程序雨/室内质感，无图库音乐。实测-18.5LUFS/-2.0dBFS真峰值；完整视频/音频解码退出0。
- 浏览器播放到结尾、duration16.066667、1280×720、loop=false、error=null；质量计数0丢帧/0损坏（含播放和随后seek的490显示帧，非编码帧数）。390px视口scrollWidth=390，无横向溢出。首页 http://127.0.0.1:8788/ ，旧试片仅在/previous。

真实私有回执位于 `.data/ai-drama-proof/`、`.data/ai-drama-quality-v2/`，包括模型/输入/工作流/seed、Comfy历史、声音、编辑清单、离线IR与浏览器结果；不把用户私有回执或18.1GB权重推入Git。

## 测试与实际结果

命令在仓库根；Python为`.venv/Scripts/python.exe`，设置PYTHONPATH=services/api、PYTHONUTF8=1。

| 命令/检查 | 结果 |
| --- | --- |
| 初始 `pytest tests/test_video_generation.py --maxfail=1` | 退出1，未实现的capabilities返回404 |
| 新原生尺寸/121帧失败用例（修订前） | 退出1，width/frames不支持返回422 |
| `pytest tests/test_video_generation.py tests/test_drama_layout.py -q` | 退出0，25 passed：鉴权/租户、许可/来源、幂等、种子/原生尺寸、状态未知不重发、已有回执恢复、取消/租约、合成资产/配音/字幕/预览与高清409、四画幅演员无遮挡 |
| Windows声音测试回归（首次全量） | 退出1，236 passed/1 skipped/1 failed；旧用例取voices[0]，实际选到正在与视频争用GPU的Qwen，并非预期系统SAPI。只将该Windows系统声音用例改为显式选SAPI，生产声音顺序未改 |
| `pytest tests/test_speech.py -q`（修正后） | 退出0，1 passed，真实系统音频RIFF/WAVE产物 |
| `pytest -q --junitxml=.data/drama-final-pass.xml`（最终） | 退出0，237 passed / 1 skipped，129.44秒；本机未配置PostgreSQL，因此该服务测试未运行，由CI补充 |
| `ruff check services tests infra scripts examples/ai-drama` | 退出0，All checks passed |
| `python scripts/export-contracts.py` | 退出0，实际OpenAPI/输入Schema/错误码导出 |
| `npm.cmd run typecheck` / `npm.cmd run check:boundary` | 均退出0；101个源码/配置文件扫描通过，实际网络边界由pytest另验 |
| `npm.cmd run build` | 退出0，Next16.4.5编译、TypeScript及页面生成通过 |
| `python engineering/scripts/validate_contracts.py` / `pytest engineering/tests -q` | 均退出0；工程模板结构通过、3 passed，不等于真实产品已上线 |
| FFmpeg整片解码、EBU响度、浏览器播放、移动视口 | 上述实际技术结果通过；声音主观听感/最终艺术认可未替用户执行 |

## 安全、商业许可、影响与回滚

影响：新增本机API与UI、DB0015、生成/素材来源验证、固定视频工作流/新cinema版式及文档/版本；LLM Prompt、付费预算与第三方最终发布未改。ComfyUI为单独GPL-3.0服务、权重模型卡标Apache-2.0，均未随仓库分发；参考图、人物、声音、字体及FFmpeg商业使用权不能据此认证。无真实个人肖像、无模型密钥入日志或Git、无生产部署。首次pip下载校验失败后重下成功，没有绕过哈希。

已知限制：本机高质量生成很慢；随机输出可能引入额外前景人物、构图/身份漂移、手部或细节错误；不保证连续角色、对口型或专业质量。最高物理输出源1280×704，本轮720p为审看合成，不称1080p原生生成。人物近景后半段出现了虚构对话者前景，属于待用户确认的剪辑素材。新的动漫高分辨率重拍未运行，已有动漫入口及低清真实推理证明，不称新动漫艺术质量已验收。

回滚：停止API/Worker，恢复114d3c4代码及已验证 `.data/backups/pre-0015-20261108-191536.db`（SQLite integrity_check=ok）和匹配媒体；不破坏性downgrade。不再运行生成服务仍可使用旧MG/录屏/授权混剪。版本仅为开发版，Git提交/PR不等于生产发行。下一步由用户审看片反馈决定艺术修订；未经用户确认不登记素材通过、成片通过或发布。
