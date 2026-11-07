# 系统模块地图（目标拓扑，不代表源码已经存在）

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
