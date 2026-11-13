# #53续 · 用户否决后的音频驱动短剧重做

2026-11-13，基线297783bc148287dfea9ffc819073b456b6afb3dd，独立主模块`examples/short-drama/try-it/v4/`。目标：修正《你来试试》人物说话、身体动作、声音各自生成的问题，保留完整前期并交付真正运行过的超分影片。用户否决v3优先于此前技术检查；不把文件可播放当成剧情/口型/音色优秀。

## 证据、方案与失败

observed：用户截图指出嘴部、动作和音色错乱。旧流程的身体先按无声动作提示生成，逐句库存声再做256面部口型与混合；两条独立路径在源码/原片/回执可验证。播放器只显示整秒，**不能从截图13秒断言嘴部相对13.433秒对白提前**。旧S04静音段MediaPipe平均jawOpen约0.01091，多数接近闭嘴；它不能证明逐字口型准确。此前把截图当精确提前证据的推断已撤回。

hypothesis：独立身体和口型、逐句合成的语气变化可能破坏表演连续性；模型、声音偏好、渲染与浏览器对感受的影响未完全区分，不能声称唯一根因或全部解决。

最小方案：只重做独立作品链，不改正式API/DB。固定每角色连续声音母带 → 逐样本切分 → 同一音轨作为WanSoundImageToVideo的音频条件驱动全身表演 → 逐镜切选/24fps插帧 → 原生尺寸神经x2 → 真实UI/字幕/全局混音 → 解码/哈希/浏览器/白名单制作包。没有MuseTalk、脸部替换或嘴部模糊覆盖。变更集中v4，v3保留为用户否决历史；共享generate.py只保留seed缺省5101的兼容扩展。

两次明确失败保留：

- 声音v1实际152/163.76秒，远超预算，未进影片。v2去掉省略号、限制token后男3.28秒/女8.16秒；连续母带只生成一次，再按角色统一语速处理后冻结。WhisperTiny只作内容/时间诊断，女声存在同音字识别和末尾“哦”识别不确定，未人工听审。
- 女主145帧一次生成，prompt52985c79-d193-435b-8911-fec16e7a6da2、trace de5fa1b9f2474d82bc3ecc5343247444；首个失败span为`sample/KSampler/torch.OutOfMemoryError`，363.88秒后失败，无视频。没有自动重发，显式改为77/69帧两个新take，切自同一PCM母带；9项契约锁定本机8GB配置最大77帧。原始异常不是新造的正式API错误码，本独立工具尚未映射统一错误码目录；正式服务集成前仍需补齐。

四个完成prompt、trace、输入图/WAV/模型哈希、seed、steps/CFG、资源采样和完整graph在`.data/short-drama-53/v4/takes/*json`；缺少的creator_run/content/video_project/render_job字段明确null。紧凑摘要见v4/build-provenance.json，完整回执在制作包，无未知任务自动重发。

## 实际影片和画面边界

两个文件在`.data/short-drama-53/v4/`：`你来试试-v4-超分成片.mp4`20,975,375字节、SHA3a26687322ce3f261a676790e4a23d2ae4a518376a9faab21436839c85996ae1；`你来试试-v4-超分前对照.mp4`18,339,264字节、SHA135f407234430e18d3123b7ae8add8b5bb0caae2539185ba4b63b26e58ced837。均18.25秒、438帧、1920×1080/24fps、48kHz AAC双声道、7句字幕。

原生S2V四段832×480/16fps，分别37/77/77/69帧，耗时901.49/2223.16/2253.50/1943.02秒；非原生1080p。男主两段固定同一Dylan母带、女主两段同一Serena母带，库存声音非真人克隆。S02/S03使用连续女声，S06选择原生第二段3.125秒处和整段音轨7.875秒处，逐样本检验对应。

五段342帧实际RealESRGAN神经x2，不先放大再冒充原生：通常832×480→1664×960；S01因生成额外腕表只裁去底部32px，832×448→1664×896，保留整张脸；手部操作沿用1280×704原生→2560×1408。逐镜MCI至24fps，不跨切口补帧；边界不足最多一个24fps帧补齐。最后等比适配HD，字幕和真实UI不经神经文字修复。逐帧SR和MCI可能闪烁/变形，不恢复真实拍摄细节。

三视图、空场景、四张首帧及完整ImageGen提示词沿用v3实际7张PNG；本版剧本/站位/每镜目的在v4/剧本与表演.md。S02提示手掌放低，但生成仍有较明显掌部动作，未声称完全遵从导演。逐秒接触表已目视检查，未发现旧版糊嘴覆盖层；这不是逐字口型/艺术合格证明。

真实有招UI使用既有授权隔离示例录屏，未重新读取真实账号/简历；虚构练习数字明确标识，不编造真实产品效果或手机界面。AI剧情/合成声音标识进入成片。技能仅参考固定shuohao/zenstory流程，无上游云命令执行。

## 验收与真实执行结果

命令均从仓库根目录运行，`.../v4`指`examples/short-drama/try-it/v4`。

| 验收命令/操作 | 实际结果 |
|---|---|
| `.venv/Scripts/python.exe -m unittest discover -s .../v4 -p test_contracts.py -v` | 首次缺contracts导入退出1；增加145帧失败用例后发现未阻断，退出1；修复后最终退出0，9项通过：音频条件/采样链/16fps/覆盖/77帧上限/固定角色母带 |
| 固定S2V四镜与postprocess.py | 四份生成和五份超分回执complete，两部影片真实存在；外层等待进程退出码未保留，不以此虚报0。原始145帧失败记录error |
| `.data/qwen-clean-runtime/Scripts/python.exe .../v4/finish.py` | 首次超分缺失退出1；完成后幂等复查退出0，输出SHA不变 |
| `.data/qwen-clean-runtime/Scripts/python.exe .../v4/check.py` | 首次manifest缺失退出1；首次完整检查遇ffprobe UTF-8被Windows GBK解码而失败1，修正显式UTF-8后最终0 |
| 同一check.py实际覆盖 | 两部438帧完整解码/声画时长/最终哈希；四条原生实际解码帧数/832×480/16fps；输入图/WAV哈希；两位母带身份；女声分段与母带逐样本相等；五段实际x2来源/帧数；混音与生成音轨互相关延迟**0样本**。技术通过不等于音素准确 |
| `.data/face-qa-runtime/Scripts/python.exe .../v4/mouth-evidence.py <native> <locked-wav> <proof>` | 男77帧、女77/69帧均退出0，未缺脸；男静音jawOpen约0.001818。指标仅诊断，不做自动艺术通过 |
| `ffmpeg -hide_banner -nostdin -i <成片> -vn -af loudnorm=I=-16:TP=-1.5:LRA=8:print_format=json -f null -` | 0；原片输入实测-16.53LUFS、-1.49dBTP、LRA3.20，未把分析器output值当成原片值 |
| agent-browser实际整片播放 | /film.mp4、1920×1080、ended18.25秒、438帧、丢4帧、waiting/stalled/error均0、非静音；无人工听审 |
| agent-browser实际对照播放 | 明确DOM选择/baseline.mp4后1920×1080、ended18.25秒、438帧、丢8帧、elapsed18.781秒、waiting/stalled/error均0。先前视口外按钮/PowerShell stdin操作未生效，发生10060读取超时，实际仍播film或停0秒；这些失败不计成功 |
| 浏览器声音互斥 | 播放母带再播放影片后，两个audio均paused且video播放；通过，防止本地审看时多音轨叠播 |
| `node --check .../v4/review-server.mjs` | 0；loopback8792，固定白名单，成片验证状态与edit哈希一致才展示完整片 |
| `.venv/Scripts/python.exe .../v4/archive.py` | 0；实际白名单ZIP CRC与凭据形状扫描通过，无模型权重。最终文件数量/字节/SHA由bundle-receipt.json单独冻结 |
| `.venv/Scripts/python.exe .../v4/download-check.py` | 0；四个实际附件SHA、七参考路由、普通/尾部206、非法416、POST405、私有路径404通过；未操作保存对话框 |
| Python AST / JSON / Node静态检查 | 0；32个Python文件、v3/v4 JSON、两份review-server.mjs语法通过；不是全应用测试 |

`archive.py`执行真实ZIP CRC和凭据形状扫描，`download-check.py`下载实际附件并比对SHA、206/416/405/404与参考图路由。二者最后的实际执行结果分别冻结在v4/bundle-receipt.json和download-validation.json（不把制作包自己的摘要递归装进自己）。最终静态检查与Git提交证据另附于交付记录。没有人工逐字听审、独立艺术评审、全应用回归/build、数据库升级回滚演练或隔离模型环境漏洞审计；这些项均**未运行**。

## 影响、许可、成本、回滚

API、DB0016、正式视频引擎/Provider、IR1.1、正式Prompt/审核和发布流程均无变更。UI只新增独立本地审看页。版本冻结于v4/film-versions.json：应用0.20.0-dev、agent_graph@2、pillow_ffmpeg@8保持；独立audio_drama_s2v@1、audio_drama_edit@4、native_size_rrdb_x2@2。24fps不满足正式VideoInput的30fps契约，未导出伪IR。没有生产部署，第三方平台发布仍由用户手动完成。

固定[官方Comfy原生S2V流程](https://docs.comfy.org/tutorials/video/wan/wan2-2-s2v)，模型仓库revision ee6f4a40737a995bf5818954cfce6d59443b0f04，[仓库卡](https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged)标注Apache-2.0。Comfy源码GPL-3.0；没有将其运行时或权重分发进仓库/制作包。RealESRGAN官方BSD-3-Clause全文通知在v3/notices。诊断SDK[MediaPipe源码许可](https://github.com/google-ai-edge/mediapipe/blob/master/LICENSE)Apache-2.0；[FaceLandmarker模型](https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task)SHA64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff。以上不认证模型训练数据、音色、输出、CUDA、FFmpeg/字体完整商业权利，**商业发行许可尚未确认**。

无新增付费云资源，无付费视频调用；新增本机模型约17.28GB、隔离CPU诊断环境，实际用电及此前内置ImageGen账户费用不确定。下载/推理未访问社媒账号，密钥不进源码/日志/ZIP；凭据模式扫描不是完整安全审计。Comfy队列实测running0/pending0，核验PID命令行属于本轮本仓8188后停止；8792仅本地审看保留。

回滚：停止本轮8792审看服务、回到保留的旧影片或297783b源码，不删除新/旧原片、失败证据或任何生产数据，不执行DB降级。下一步仍是用户审看口型、动作、音色；正式服务集成与逐字人工审听未完成，不能用本次技术检查替代。
