# #25 创作质量与本地真实联调

0.12.0-dev / DB 0012 / creative_quality@1 / compatible_chat@2。用户明确个人本地使用，没有执行生产部署或合并。

影响文件：`quality.py / quality_api.py / quality_jobs.py`、`video.py / video_audio.py / video_edit.py / production.py`、`jobs.py / models.py / schemas.py / main.py / settings_api.py`，迁移 0012、网页 quality 组件及内容/视频/创作者入口、版本/生成契约、测试与文档。方案见 ADR 0007，父功能为 Issue #21/#23。

先失败：`pytest tests/test_creative_quality.py -q --maxfail=1` 在创建工程处返回 422，未知字段 preview_required，trace `29fe5f99566b8acbf14f1e1c802d9eb4`。新增报告、预览、审核及独立费用任务后，最初九项测试通过（6.21s），再补空 choices 回执用例，最新全量包含十项质量用例；覆盖预览与高清分离、修改后不可沿用、素材/品牌依据与预览字节、旧政策不可由保存绕过、自动任务停在预览、跨租户、重复依据、真实兼容参数、渲染中编辑、受控模型一次调用/未知费用不重试。

完整执行：`PYTHONPATH=services/api python -m pytest -q` **106 passed / 1 skipped，45.79s，退出 0**。跳过的是本机无 PostgreSQL 服务，不能算本机 PG 通过。`ruff check services tests infra scripts`、`npm run typecheck`、`npm run check:boundary`（81 文件）、工程契约结构检查和三个诊断 unittest 均退出 0。`npm run build` 退出 0。`node scripts/browser-smoke.mjs` 实际完成 **39 页面渲染 / 72 宽度检查**，退出 0（含模型设置、品牌监测、新质量工程）；不将路由渲染算作全部功能完成。远端 PG 以本 PR Actions 为准。

## 实际 DeepSeek 请求

2026-11-06 经用户明确授权，使用本机加密配置对 `https://api.deepseek.com` 联调。官方模型列表成功，模型为 deepseek-flash / deepseek-v4-pro；读取记录 `6434e59dddc54671834db7646a0d888e`。工作区“有招”已保存配置，尚无创作者，不会自行启动日程。实际生成在已有合成验收工作区进行，没有替换用户品牌资料。

| 实际请求 | 运行编号 | 返回结果 |
|---|---|---|
| 固定 JSON | 72746bf5ef4b4656bcc35488a8b0337a | connection=ok，45 输入 / 5 输出 token，未发送品牌资料 |
| 质量复核 | 832d2697a7fe416eae71e24cf729f6c6 | 482 输入 / 319 输出 token，结构/引用校验通过，生成独立待审建议，草稿和审批状态未改写 |

两次均完成、无重试；各按配置报价向上取整记 1 分。这里使用官方高峰/缓存未命中报价作为保守估算，不是服务商扣款回执。模型建议提示补核另一条已核实事实、精确限定“编辑”等功能范围并人工检查 AI 标识。没有把模型建议算作事实认证或流量证据。真实响应与运行元数据私有保存于 `.data/deepseek-real-receipts.json`，不含凭据。密钥没有进入代码、Prompt、日志或导出。测试结束已暂停验收创作者、撤回模型授权并恢复原预算。

## 实际媒体与监测

合成验收工程 `58b48ae0bccf4298adc4584b86242060`：五个镜头、30 秒、授权验收音调、五条字幕。预览实际输出 640×360，SHA256 `f7728a9f807923371a8c56f0f260366927c7ebca309ace3a61a9206c94acb301`，烧录内部预览水印。浏览器完整播放至 30 秒，检查五个时间点画面，再填写“自动化验收登记，不代表用户实际发布审核”，确认后提交高清。

高清实际输出 1920×1080 / 30 秒 / H.264 + AAC，SHA256 `0ff3080a24fa99c62464345a64ac980b80b221eeec12b599dcec9a9d79343766`，没有预览水印；HTTP 文件读取和哈希检查通过。回执见 `docs/evidence/quality-render-receipts.json`，采样图 `quality-preview-frames.png`，界面 `quality-review-desktop.png`。素材、字幕与实际来源保留在回执中；这是功能验收，不是商业画质或营销效果证明。可用 `scripts/quality-local-acceptance.py` 在既有合成工作区新建同类验收，脚本不会读取模型密钥。

上传 qa-v1/qa-v2 两版合成说明后，事件 `46d8398afad64efe9db423ec91d23349` 保存差异，关联素材自动 needs_review / verified=false，品牌事实保持不变；在浏览器打开来源、证据与差异，来源已停用。真实公网文档抓取另见 PRODUCT_MONITOR_VALIDATION.md。网页变化只生成待核实事件，不自动声称新功能已上线。

## 版本、风险和回退

本机升级前备份 `pre-0012-20261106-232236.db`，integrity_check=ok；升级至 0012 后同样为 ok。0010/0011 的先前备份也保留。新增列有兼容默认值；旧工程继续原政策，启用预览的工程保存/恢复不会关闭该政策。费用预留与人工发布边界沿用原服务，未知结果继续阻止重试。字体、系统语音及 FFmpeg 的商业使用许可仍须按原许可证台账核实，没有新增依赖。

恢复时先停 API/Worker，保全当前数据库、工作区文件及独立加密主密钥，再用对应已验证提交和隔离备份恢复。历史审核记录不删列降级。升级前备份不包含之后新增的配置或作品；需要保留这些数据时使用最新兼容备份，不能把旧库与新记录混合覆盖。浏览器自动保存文件的既有取消问题仍未算通过；本轮实际验证的是文件 HTTP 字节、播放和哈希。


补充边界：受控测试同时覆盖模型返回空 choices 时立即进入未知回执处理，保留预留且只调用一次，不把结构异常留成可重试运行。公开的脱敏请求摘要见 `docs/evidence/deepseek-validation.json`，不包含密钥或思考过程。当前网关没有持久化每次响应的精确模型修订号，配置中的版本备注来自官方文档，不冒充响应证明。


## 最终集成补记 · 2026-11-07

功能提交 `c884f2cbcc695b274b78c2d20ebfae297b073186` 的 Actions **42248103408** 四项全部成功：SQLite API、PostgreSQL API（含增量升级）、Web（含构建与依赖审计）、Python 依赖审计。浏览器完整报告保存于 `docs/evidence/quality-browser-smoke.json`；逐页标题已核对为实际业务页面。稍后的截图会话丢失时重新载入私有测试状态，截图复核后才交付。

另补一次真实创作全链路，而非只检查连接：选用已确认的 2026-11-08 功能速览选题提前备稿（不是伪造当日自动执行）。运行 `3574d9dce3854b2aa2dd7ef2f62dca4c` 经真实 DeepSeek 生成文案 `e1b2045572464629957751ef4cc3ef0e`，generation_source=openai；事实引用与输出结构通过，继而由本地规则生成两页图文和 30 秒混合预览 `b0bd156084af42c3a0968ced848c96c6`。预览 SHA256 `c7908c7ca61c61177b38b4473f7bf1bc7e9044e0ce9d405508af4f6f3c0643c7`，HTTP 读取及哈希通过。任务正常停在 awaiting_review / preview.ready，内容 needs_preview_review、未审核且成片附件 hash=null；没有自动生成高清或发布。

该次预留 2 分、按配置单价估算结算 1 分；加前两次共估算 3 分，均非服务商实际账单。全链路文案任务未持久化逐响应 token 用量，不能编造 token 数。输出与账本见 `docs/evidence/deepseek-creation.json`，界面截图 `deepseek-created-article.png`。验收创作者已再次暂停、撤回模型授权、恢复原预算与制作选项。先前混合高清工程在新增比较标题后重新检查/记录验收确认，成片字节保持不变。

当前 0012 数据库另做一致性备份 `creator-0012-20261107-012713.db`，integrity_check=ok；主密钥单独私有备份并校验，不进入 Git 或公开证据。运行程序已用功能提交重启，API 的版本为 0.12.0-dev / 0012，git_sha 与功能提交一致，boot 时 working_tree_dirty=false。文档补记不会变更数据库或运行行为。
