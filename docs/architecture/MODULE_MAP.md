# 系统模块地图（目标拓扑，不代表源码已经存在）

#53续 / `audio_drama_edit@4`：独立主模块`examples/short-drama/try-it/v4/`；连续角色母带→audio-lock/固定16fps音频条件S2V→逐镜切选/24fps插帧→原生尺寸神经x2→finish/check/archive→8792本地审看。两片18.25秒/438帧，v3用户否决历史保留。9项结构契约与真实媒体验证不能替代人工艺术/逐字听审；正式API/DB/Provider/30fps IR和审核未改。见[实际证据](../implementation/AUDIO_DRIVEN_DRAMA_VALIDATION.md)。

#53 / `drama_production@3`：独立主模块`examples/short-drama/try-it/v3/`，剧本/三视图/空场景/分镜→复用耐久Wan单镜runner→校正ROI的Muse口型/原生细节混合→独立RealESRGAN x2→master/check/archive→8791本地审看。22秒三种对照输出；正式应用API/DB/Provider/人工审核未改。24fps/2560时间线与当前30fps/1080或1920的VideoInput不同，未伪造可导入IR。见[实际验证](../implementation/DRAMA_MASTERING_VALIDATION.md)。

#51 / `action_drama@2`：独立作品主模块 `examples/short-drama/try-it/`；production/edit → 高清首帧/本机Wan/库存声 → 独立MuseTalk口型试验 → FFmpeg/check/export-ir/archive → 8790本地审看。21.9秒v2；正式API/DB/Provider/人工审核未变，不代表软件已集成口型或自动导演；见[实际证据](../implementation/TRY_IT_DRAMA_VALIDATION.md)。

#49 / `short_drama_cut@1`：独立制作主模块 `examples/short-drama/dont-say-we/`，production → 库存合成声音/高清首帧/本机Wan/隔离真实UI → finish/check/archive → 8785本地观看。41秒v2成片及离线IR1.1，不注册正式Provider、不写用户审核通过，不修改DB/API。作品和软件能力必须分开记录；见[实际证据](../implementation/DONT_SAY_WE_FILM_VALIDATION.md)。

0.20 / #47：主模块`services/api/creator/drama.py`负责原创短剧计划、因果/覆盖/站位/源尺寸和逐镜绑定，`drama_api.py`提供HTTP，`drama_jobs.py`复用Run/预算/模型授权，`drama_skills.py`核对固定技能并由`scripts/drama-skill-check.mjs`实际执行上游剧本检查。DB0016独立DramaProject，私有导出和历史保留。WEB`video-drama-skills.tsx`位于`/studio/video/drama`，下接既有生成Worker、video_recipes/narration及人工预览复核。其他原生技能报告/生图未自动接入。见[使用与边界](../implementation/DRAMA_SKILLS_GUIDE.md)。

0.19 / #45：唯一主模块 `video_generation.py`（生成状态机）→ `wan_comfy.py`（固定本机原生工作流）→ 独立 `video_generation_worker.py`；HTTP为`video_generation_api.py`，DB0015。素材经独立用户检查，`video_recipes.py` / `video.py`保留Shot.generation_job_id，cinema版式只留AI标识；WEB为`video-drama.tsx`。真人/动漫均有实际动态片段，不提供对口型或跨镜头一致性保证；见[使用](../implementation/LOCAL_AI_VIDEO.md)及[验收](../implementation/AI_DRAMA_VALIDATION.md)。持续创作与人工发布边界保持。

0.18 / #41：VIDEO新增video_recipes.py（类型目录/配方编译/幂等创建）与film_types.py（三类画面）；video_edit_api.py / brief_api.py提供制作入口，briefs.py按可选类型编译原脚本，narration.py与RenderJob沿用。WEB为video.tsx / briefs.tsx / film-design.tsx；VIDEO IR1.1兼容扩展，provider@7，无DB/Prompt/云生成变更。见 [实际验证](../implementation/VIDEO_TYPES_VALIDATION.md)。

#39续：独立 `examples/video-production/youzhao-choice/edit/` 的 dialogue.json → voice.py / diagram.js / 真实UI采集 → finish.py → verify.py 已产出44秒完整影片与离线IR1.1。正式API、Provider注册、工作台和DB不变；这不是持续任务已具备自动导演。见 [实际范围](../implementation/LOCAL_CHOICE_FILM_VALIDATION.md)。

#39 / production_pack@1：`examples/video-production/youzhao-choice/` 是独立前期制作包和采集资料，含40秒分镜、实际生成首帧、真实UI补录、来源和缺口清单。未接入正式API/Provider，未完成演员动态试拍或整片。不得把其中的production.json当VideoProjectIR或艺术质量通过。见 [本轮证据](../implementation/CINEMATIC_PRODUCTION_VALIDATION.md)。

0.17.0 / #37：speech.py按声音路由expressive_speech.py → 独立scripts/qwen-speech.py；narration.py冻结delivery_style与来源，brief_api.py保留缺省幂等。UI为narration.tsx共享控件。examples/video-motion是独立剪辑实验，未注册正式Provider；API和DB依然不接触站外发布。见 [本轮验收](../implementation/EXPRESSIVE_MOTION_VALIDATION.md)。

0.16.0 / #35 实现增量：`briefs.py` 接收可选 narrative_mode，`story_direction.py` 提供 story_direction@1 的创作约束；`brief_jobs.py` 按 Run 版本生成提示词。`speech.py` → `neural_speech.py` → 独立 `scripts/kokoro-speech.py` 是可选本地声音路径；`narration.py` 冻结/核对声音来源，既有预览审核链保留。UI 在 briefs.tsx / narration.tsx。没有新增生成式视频引擎或数据库表；见 [本轮报告](../implementation/STORY_VIDEO_VALIDATION.md)。

| 模块责任 | 推荐目录（目标路径） | 入口/主要接口 | 上游 | 下游 | 不可越界的动作 | 关键测试 |
|---|---|---|---|---|---|---|
| Web 工作台 | `apps/web/` | `GET /dashboard`、编辑器和人工发布中心 | API | 无 | 不直接写数据库/平台 | UI/E2E、权限 |
| 品牌事实与版本 | `apps/api/domains/brand/` | 品牌事实与版本审核 API | 用户授权源 | KB、内容创作 | 不推断新功能已上线 | 事实来源/时效 |
| 创作者调度 | `apps/api/domains/creator/` | Schedule, Pause, Resume | 用户配置 | DailyRun | 不绕过预算或用户暂停 | 重启/幂等/时区 |
| Agent 编排 | `workers/agent/` | LangGraph Run / Checkpoint | CreatorRun | 选题、脚本、镜头 | 不访问未经许可外部账号 | tool ACL/回放 |
| 内容与分镜 | `apps/api/domains/content/` | Content / VideoProject IR | 品牌、Agent | Video Worker | 不绕开素材来源与版本 | IR schema/版本迁移 |
| 视频引擎注册中心 | `workers/video/providers/` | `render_shot()` 适配器 | Shot、素材 | MotionCanvas/Blender/Wan/OpenFilm | 不混淆真实 UI 与生成 UI | 适配/错误分类 |
| 合成与导出 | `workers/video/compositor/` | `compose()` / `export()` | 已完成镜头 | Object Storage | 禁止假成功/空文件 | 媒体探针、音频、哈希 |
| 合规审核 | `apps/api/domains/compliance/` | Scan/Review/Approval | Content | Handoff | 审核不合格不得交接 | 文本/版权/AI 标识 |
| 人工发布交接 | `apps/api/domains/handoff/` | 导出包 / `user_reported_published` | 审核 | 用户下载 | **不对第三方平台执行发布** | 禁止平台写请求 |
| 指标与成长 | `apps/api/domains/learning/` | Import, Review, Strategy | 用户报表/站内数据 | 下次选题 | 不编造平台数据 | 溯源/缺失值 |
| 可观测与诊断 | `packages/observability/` | trace / metric / diagnostics | 全部运行模块 | 运维后台 | 不泄露提示词/凭据 | 脱敏/关联/告警 |
| 发布与运维 | `ops/`、`.github/` | CI/CD、版本发布 | 代码/配置 | 灰度/回滚 | 无审批不生产部署 | smoke/备份恢复 |

架构约束：Web → API → Domain Services → Queue/Worker/DB；Agent 不得直接写跨领域表。VideoWorker 只通过 Shot Provider 接口运行。发布包任务没有社媒发帖 Connector。PostgreSQL 为内容与任务真相库，Redis 不作为长期记录的唯一来源。

**AI 查错顺序**：先按 `error_code` 找责任域 → 按 `trace_id` 找失败 span → 按 `creator_run_id` / `shot_id` 查业务上下文 → 通过 `git_sha` 和 manifest 确认运行版本 → 在对应模块写复现测试。

实际源码映射见 [IMPLEMENTED_MODULES.md](IMPLEMENTED_MODULES.md)；#33 的唯一主模块是 `services/api/creator/film.py`（产品片相机采样），由 `video.py` 的镜头 Provider 调用；不把本页目标目录当作已实现代码。
