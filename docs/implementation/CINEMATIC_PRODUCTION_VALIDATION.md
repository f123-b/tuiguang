# #39 · 有招剧情片前期制作与实际缺口

后续：用户要求先跳过Runway完成视频，现已实际完成 [44秒本地完整剪辑](LOCAL_CHOICE_FILM_VALIDATION.md)。本文保留前期阶段的真实结果；原演员正脸方案未执行，不能把新成片说成该生成演员已成功试拍。

2026-11-08。目标是回应用户对素材、动画、剧情简单的反馈，重做创意与素材生产方法。当前交付为 `production_pack@1` 的前期包和真实 UI 素材；**未完成角色动态试拍、整片或艺术审核**。不能以这份报告宣称“已符合优秀视频标准”。

## 观察与范围

Observed：用户提供上轮空间截图试片画面并明确指出素材、动画和剧情简单。现有正式 `pillow_ffmpeg@5` 能合成 MG、素材与实录，`examples/video-motion` 是独立空间截图实验，没有演员表演生成 Provider。帧率检测通过不能回应这次艺术反馈。这不是已定位的运行时异常，不编造 trace_id 或首个失败 span。

最小方案：在 `examples/video-production/youzhao-choice/` 做独立前期制作，以一个具体选择串起人物、方案示意与真实 UI。调用链为人工可审看分镜 → 原创图像关键帧 → 待连接服务上的单镜头报价/确认 → 动态试拍 → 实际素材编辑 → 既有 IR/审核交接。后三个阶段尚未完成。没有把前期 JSON 命名或解释为正式 VideoProjectIR。

## 交付与验收

| 项 | 真实状态与依据 |
|---|---|
| 剧本 | `DIRECTOR.md` / `production.json`，40 秒、1200 帧、12 镜；有问题、空泛尝试、自我叫停、具体方案、资料证据、重新回答；等待用户创作判断 |
| 首帧 | 内建 imagegen 实际生成 `s02-first-frame-v1.png`；2,105,629 字节，SHA256 `fc27f9012ae4667c0cb07fdd9585e04194fd1cc550e7570402309ddca0239afb`；模型精确版本/seed/单价未返回，不能填造 |
| 首次四格图 | 失败，工具返回 `network error: error sending request`；未保存不存在的产物 |
| 四格图重试 | 带成功首帧作参考重试，仍返回相同网络错误；没有四格图产物，没有切换CLI/API或索取/使用新密钥 |
| 试拍 | 8 秒 S02 的动作、连续性、声音和检查点保存在 `trial-shot.json`；未提交动态生成 |
| 云服务 | Figma/Weave 查询返回 OAuth 未连接；用户选择 Runway 后，`whoami` 三次返回 `-32001 Unknown tool`。未确认鉴权/可用模型/套餐，不推断余额或费用 |
| 消费许可 | 用户选择“连接 Runway，先审看单镜头与报价再生成”，不是金额确认；报价 null，spend_approved=false，请求 ID 空，实际费用未知且没有本轮 Runway 生成任务 |
| UI 事实 | 只读核对有招 `521e1f4` 的 ProjectLibraryPage.tsx:368；本轮隔离实例真实输入并保存演示备注，重开后值完全一致。未运行 AI 生成问答，不以界面宣传文案当作已验证能力 |
| UI 素材 | 新采集原生变化帧 211，其中起始尺寸变化 1 帧剔除；210 个原生帧按时间戳输出 413 帧 / 13.766667 秒 / 1080p / 30fps / 无声。只验证媒体和操作，未宣称每秒 30 个独立原帧或创作质量通过 |
| 整片 | 未运行。生成演员、纸面动作、方案动效、对白/环境声/音乐和最终剪辑仍待完成 |

## 实际命令与结果

| 命令 / 操作 | 退出码 / 结果 |
|---|---|
| `git status --short` / `git branch --show-current` | 0；起点干净，基于 `codex/37-expressive-voice-motion` 的 afa8ea5，新分支 `codex/39-cinematic-production` |
| `gh run view 42406114888 --json status,conclusion,jobs` | 0；上一轮最终提交的四项远端 CI 均 success，只证明上轮代码 |
| `agent-browser skills get core` / `... get electron` | 0；读取实际 CLI 指令 |
| `agent-browser --session cinematic39 connect 9349` / snapshot | CLI 0，但目标显示 about:blank；与 HTTP CDP 的真实 Electron renderer 不一致，**不算采集通过** |
| `agent-browser doctor --offline --quick` | 0；12 pass、0 warn、0 fail；没有使用破坏性 --fix，也未据此宣称连接正确 |
| `node .data/inspect_choice.cjs 项目库` / `... 项目设置` | 0；转用原生 CDP，只在本轮隔离副本观察真实项目库与备注输入 |
| `node .data/capture_choice.cjs` | 0；211 原始帧，13.865 秒采集过程；输入 1.074–6.324s，保存 9.109s，重开值校验 11.748s |
| `python .data/finish_choice_pickup.py` 初次 | 1；首帧 1525×1080 不满足 H.264 偶数宽度。实际查 211 帧尺寸，仅起始 1 帧不同，明确剔除 |
| 上述脚本早期 concat 尝试 | 1；时长断言不符。没有降低断言、把输出误差写成通过，改用原生时间戳直接选帧后编码 |
| 同脚本最终 | 0；ffprobe 解码计数 413，1920×1080 / 30/1 / 13.766667 秒；保存值校验 true；SHA256 `faf11b6936c4b90ce16552994ec7f6b7c2203d5d5fc19aed5be79610c1fbe61b` |
| 本轮完整应用单测 / API / Web 构建 | 未运行；没有更改应用服务、DTO、UI 或数据库；不借用上轮 168/30 项测试作为本轮动态试拍证明 |

后续 JSON/哈希/语法/解码检查的实际结果在本报告尾部补记。原始采集和内部过程在 `.data/有招剧情制作-20261108`，公开制作包只收录无真实个人资料的演示素材、提示词和脚本，不包含隔离用户数据库、缓存、密钥或模型。

补记（实际执行，退出码均 0）：

- `npx.cmd --no-install prettier --write examples/video-production/youzhao-choice/{production,trial-shot,imagegen-requests,capture-evidence}.json`（实际按四个完整文件名传入）：4 份 JSON 格式化，无安装。
- `node --check examples/video-production/youzhao-choice/tools/capture-choice.cjs`：语法通过。
- `.venv/Scripts/python.exe -m ruff check examples/video-production/youzhao-choice/tools`：All checks passed；两份 Python 制作/核对脚本已格式化。
- `python examples/video-production/youzhao-choice/tools/check-pack.py`：分镜帧数/镜头与资产引用、实际图片/视频字节哈希、ffprobe 413 帧/尺寸/时长和 FFmpeg 完整解码通过；明确返回 `preproduction_incomplete` / `not_reviewed_by_user` / `video_quote=null`，静帧不能满足动态镜头依赖。
- `git diff --check`：通过；仅提示已有 CRLF 文件将规范为 LF，无空白错误。

首帧实际尺寸为 1672×941；16:9 是后续试拍目标比例，不伪造图片输出参数。`capture-evidence.json` 已冻结实际源代码 commit、编译入口哈希、采集事件、原帧清单摘要与媒体测量。没有因为哈希/解码检查通过而把待制作镜头改成 ready。

## 影响、许可与回滚

| 面 | 本轮影响 |
|---|---|
| API / DB / 正式引擎 / Prompt | 无变更；0.17.0-dev / 0014 / IR1.1 / pillow_ffmpeg@5 / fact_bound@2 均不变 |
| UI | 无工作台页面变更；制作包中的真实界面来自隔离有招实例 |
| 模型与成本 | 内建图像生成；无新视频云请求/无云资源开通。原生图像调用单价未返回；视频报价未取得，不写 0 元或预算承诺 |
| 合规 | 角色与技术例子明确演绎；产品镜头用真实界面与合成资料；不造用户评价、成功录用、AI 回答、性能数值或平台回执 |
| 许可 | 自创剧本与图形规划；生成图片的商业条款/标识仍需复核，不冒充有实拍演员授权。真实产品界面依据用户“我们的有招”任务授权，仅采集合成资料；没有复制第三方影片、音乐或角色肖像 |
| 安全 | 不读取配置密钥、真实简历、私人录音、`.release-secrets`；只读产品源码。控制器连接失败未修改浏览器权限或安装大型运行时。采集后关闭本轮浏览器会话与 PID69904 的隔离 Electron 实例，保留用户原有服务 |
| 文档 | 模块地图、实际状态、使用说明、版本与来源清单更新；本包版号 production_pack@1 |
| 回滚 | 退回 afa8ea5 或移除此制作包/文档增量，无数据迁移。旧视频与旧包保留；本轮素材另目录保存 |

下一步需要 Runway 可用连接和首帧方向反馈，之后取得单镜头实际报价并单独确认消费。再以真实动态试拍决定是否制作余下镜头。当前没有上线、合并、社媒自动上传或发布。
