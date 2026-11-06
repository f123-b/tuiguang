# 32 个目标屏幕与本轮实际对应

可访问不等于完整实现。统一 Shell 提供加载、错误、权限错误与空状态；后端以工作区校验权限。本轮深浅主题和 375–1920px 响应式共用同一套 tokens。

| ID | 路由 | 实际页面 / API | 本轮范围 |
|---|---|---|---|
| 01 | `/auth/login` | Auth / auth | 邮箱注册登录；手机号未实现 |
| 02 | `/onboarding/welcome` | Help | 实际功能说明；独立多步向导未实现 |
| 03 | `/onboarding/brand` | BrandPage / brands | 真实品牌表单，与品牌页共用 |
| 04 | `/onboarding/creator` | CreatorPage / creators | 频率/时区/预算；保存开启 |
| 05 | `/onboarding/preview` | CalendarPage / calendar | 14 日持久计划；规则规划，无 AI 热度分析 |
| 06 | `/dashboard` | Overview / dashboard | 真实任务、计数、无数据态 |
| 07 | `/creator` | CreatorPage / creators | 状态、暂停恢复、今日任务、下一次制作 |
| 08 | `/creator/edit` | CreatorPage / PATCH creator | 设置真实持久化 |
| 09 | `/creator/activity` | ActivityPage / creator-runs | 实际状态、错误和跳过未开始任务 |
| 10 | `/calendar` | CalendarPage / calendar、plan、prepare | 持久日历、规则补齐、最多 7 篇确认备稿；无拖拽 |
| 11 | `/topics` | CalendarPage | 复用真实日历；语义去重未实现 |
| 12 | `/topics/:id` | TopicPage / topics | 详情、事实来源、编辑/锁定/确认、日期交换/跳过、单篇备稿；执行依据冻结 |
| 13 | `/campaigns` | ContentLibrary / content | 真实草稿、筛选、进入编辑 |
| 14 | `/studio/article/:id`、`/studio/article/:id/graphics` | ArticlePage / GraphicsPage / content、graphics | 文案和 1–6 页图文工程、真实预览、审核、完整发布包；无任意坐标画布 |
| 15 | `/studio/covers` | GraphicsLibrary | 三版式说明与内容选择，进入真实图文编辑器；支持 PNG/JPG 和工程 JSON |
| 16 | `/studio/assets` | AssetsPage / assets | 上传、来源、许可、哈希、下载 |
| 17 | `/studio/video/new` | VideoCreate / videos | MG、素材、混合模式；高级引擎明确不可用 |
| 18 | `/studio/video/:id` | VideoEditor / scenes | 镜头参数、时间线、实际播放/下载 |
| 19 | `/studio/video/:id/storyboard` | VideoEditor | 复用分镜编辑；拖拽/AI 局部修改待做 |
| 20 | `/studio/video/:id/render` | VideoEditor / render-jobs | 真后台渲染；完整 QA 面板待做 |
| 21 | `/compliance` | ContentLibrary | 审核筛选；风险看内容详情 |
| 22 | `/compliance/:id` | ContentLibrary | 独立逐帧报告待做，不伪造平台审核 |
| 23 | `/publish` | PublishPage / handoff | 真 ZIP、文案、登记、撤销 |
| 24 | `/publish/package/:id` | PublishPage | 指定发布包详情；历史失效检查 |
| 25 | `/publish/guide/:platform` | PublishPage 内指引 | 仅官方站点首页及通用检查；未核实当前平台逐步 UI |
| 26 | `/publish/record/:id` | PublishPage 内表单 | 五项清单、时区日期、可选安全链接、用户自报 |
| 27 | `/analytics` | AnalyticsPage / analytics | 真实来源/窗口分组，缺失未知 |
| 28 | `/analytics/import` | AnalyticsPage / import | 固定 CSV/XLSX 模板，预览确认；自由字段映射待做 |
| 29 | `/growth` | GrowthPage | 真实记录汇总，AI 周报明确待接入 |
| 30 | `/growth/memory` | GrowthPage | 偏好记忆/策略版本未实现 |
| 31 | `/brand` | BrandPage | 事实来源/核实、版本、失效传播 |
| 32 | `/settings`、`/help` | SettingsPage、HelpPage | 模型状态/预算入口/实际手册；支付与完整隐私导出待做 |

工程扩展 `/ops/diagnostics` 与 `/ops/releases` 展示当前工作区事件和真实开发版本；完整基础设施维护/告警/工单 UI 尚未实施。`packages/schemas/openapi.json` 为实际可用 API，不能根据目标设计表猜测其他接口已经存在。

0.13 新增 `/studio/briefs`、`/studio/briefs/new`、`/studio/briefs/:id`，共用 BriefsPage；侧栏“指定内容创作”、创作者页和新建视频页均可进入。保存用户指定主题/内容，原文或 AI 分镜，编辑脚本、保留历史、确认后跳转真实视频工程。该页读取 `/creation-briefs`，AI 为单独授权的预算任务，页面加载不请求模型。具体时长/文字/事实/素材限制见实际 OpenAPI 和本地手册。
