# #47：短剧技能制作流程验收

日期：2026-11-09。版本0.20.0-dev / DB0016 / drama_skills@1 / skill_registry@1。基于6d6ec05（#45），独立Issue目的。仅本机开发，未部署生产、未合并。

## 证据、范围与影响

Observed：#45 UI和GenerationInput只有孤立提示词/逐镜排序，用户否定实际16秒试片的逻辑及清晰度。源码没有故事级人物目标、因果引用、站位、镜头覆盖与原始尺寸门槛。不能把缺少流程推断成Wan是唯一画质原因。新增唯一主模块`drama.py`和独立持久计划，不声称修复所有艺术问题。

影响文件：`services/api/creator/drama{,_api,_jobs,_skills}.py`、models.py/0016、jobs.py/main.py/settings_api.py/observability.py、video_recipes.py的可选内部旁白列表、`scripts/drama-skill-check.mjs`、`vendor/skills/`、`apps/web/components/pages/video-drama-skills.tsx`及视频入口。API新增，数据库增量一表，旧IR1.1和引擎版本保持；新Prompt及技能冻结，LLM授权/预算复用，不增加视频云费。无外部发布工具。

## 实际执行

|命令/动作|退出码|结果|
|---|---|---|
|`.venv/Scripts/python.exe -m pytest tests/test_drama_skills.py -q`（先失败）|1|6 failed：模块不存在/新接口404|
|七目录各`node vendor/skills/shuohao/<skill>/scripts/selftest.mjs`|0|character-refs233、art151、characters337、outline249、script154、staging99、storyboard336，合计1559项；Windows真实运行，外部服务为自测mock|
|`.venv/Scripts/python.exe -m pytest -q --junitxml=.data/drama47-final.xml`|0|252 passed / 1 skipped，142.39秒；跳过本机无PostgreSQL。涵盖计划权限/失效/篡改、因果/站位/台词/覆盖、低清首帧提交前阻断、单镜幂等、模型授权预算/未知不重发/并发编辑不覆盖、4镜合成契约/静默反应保留/高清仍409、迁移旧记录保留/重复升级/备份恢复及既有媒体流程|
|`npm.cmd run typecheck`|0|通过（后续变更按最后补记）|
|`npm.cmd run build`|0|Next16.4.5生产构建通过；不表示生产已部署|
|`npm.cmd run check:boundary`|0|106文件通过；外发运行时边界另由pytest覆盖|
|`.venv/Scripts/python.exe -m ruff check services/api tests infra/migrations/versions/0016_drama_skills.py`|0|通过（后续变更按最后补记）|

初次完整回归251 passed/1 failed/1 skipped：新增正向测试误用不存在的视频详情URL，实际生产编译/旁白参数已成功；修正为既有`/videos/projects/{id}`后单项及完整252项通过。此前fixture错误拆包`store_file`的SHA字符串、台词超时被门禁拦截均在测试中修正，不将其当作成片质量证据。

真实HTTP与DeepSeek：合成验收工作区，Run `9449eee1c45640cf937fa0170d578fdc`，Drama `f2d7e6024aab4afcb1c3f628fd087669`。模型返回4镜/人物目标与弱点/场景光照轴线/前因和行动后果；保留原输出。共享预算预留16分，已知用量估算结算4分（不是服务商账单）。检查SH3/SH4旁白超时、保守剧本估时26.2秒超过20秒范围，状态needs_revision，未确认/未排GPU。前一次费用上限10分请求在发送前BRIEF_BUDGET_EXCEEDED，无模型或费用；显式开发验收上调合成账号上限后只发送一次。测试后合成创作者暂停并撤销模型授权，原工作区配置/预算未修改。密钥只复制本机加密配置，无明文记录。

浏览器与最后检查补记见下（未记录的项目不得当作已通过）。本轮未制作新完整AI短剧，不复用旧片伪称新技能成片。4镜视频为合成色块契约fixture，不是艺术质量验收；真实Wan动态生成沿用#45证据。

浏览器实际验证：合成账号完成新故事创建；打开上述真实DeepSeek第2版，缩短SH3/SH4旁白，将生成式屏幕文字镜头改为屏幕在画外的手部反应，再保存为第3版。结构阻断归零，人工确认保持空白、GPU绑定仍空，未代用户批准。1440与390宽度均无横向溢出，控制台无报错。截图位于`.data/drama47/screenshot-1794158010073.png`和`screenshot-1794158057261.png`，私有验收资料不进入Git。实际运行生成/审看/高清由#45及本轮合成契约共同覆盖，不声称本轮又跑完28分钟动态推理。

最终增量验证：`.venv/Scripts/python.exe -m pytest tests/test_drama_skills.py tests/test_video_recipes.py tests/test_video_generation.py -q` →78 passed（48.27秒、退出0）；后续单镜重拍/长编号哈希键/来源复核补充后短剧模块15 passed（退出0）。`engineering/scripts/validate_contracts.py`退出0但只表示模板结构合格，工程诊断测试3 passed（退出0）。`git diff --cached --check`对原样分发技能采用明确vendor属性保留上游空白，128份Git blob哈希逐项匹配，敏感凭据候选0。辅助调用曾误用不存在的test_narration.py和validate-engineering.py，分别未运行；已使用上列实际文件路径补验，不计为通过项目。

最后一次完整回归（包含提示词摘要冻结、已知用量/回执保存与上述补充）：`pytest -q --junitxml=.data/drama47-final2.xml`退出0，**252 passed / 1 skipped，135.92秒**；最终`npm.cmd run build`退出0，输出`.data/drama47-final-build.log`。此后仅更新文档和提交，未再改变运行代码。主应用停止时确认没有排队/运行/未知的本机任务，独立ComfyUI未关闭。

## 许可、安全、风险与回滚

shuohao Apache-2.0及NOTICE、zenstory MIT完整保留；原始文件不改，128份文件字节哈希固定。上游含生图联网/自定义命令，运行时仅固定离线剧本检查入口可执行，其他只读片段，技能权限不继承。付费外部服务未开通。原作、肖像、字体、声音、参考图和输出的商业许可仍由操作者核对，技能代码许可不等于素材许可。

备份`.data/backups/pre-0016-20261109-005653.db`使用SQLite在线backup，integrity_check=ok；当时无排队/运行/未知的生成/渲染/配音任务。0016仅本机执行；迁移测试覆盖旧记录升级与重复执行。回退：暂停drama_plan和本机生成，保全0016新表/来源/任务账本，将匹配的0015备份恢复到独立路径，再切回6d6ec05验证。**旧源码的Alembic不认识0016，不能只切Git直接运行新数据库**；禁止破坏性downgrade、伪造版本戳与线上删除，0016后的新计划须另行导出保留。

实际回滚检查：从Git归档6d6ec05到`.data/rollback47`（不是覆盖当前源码），将上述备份用SQLite backup恢复为`restored-0015.db`。`alembic current`退出0并显示0015；旧0.19应用TestClient健康检查、合成账号登录与已有生成回执读取均200（退出0），主数据库未修改、没有启动Worker或模型。结果`.data/drama47/rollback-result.json`。

提交后验证：运行代码0376bc18cdf55d761642a21ec690b1bddfe04329的应用实测0.20 / DB0016，boot_working_tree_dirty=false，八技能完整性/清单哈希、精简列表、take_key契约和第3版计划均正确；没有人工确认/生成绑定，合成创作者暂停且撤销模型授权。Git工作区干净。该代码提交的GitHub Actions 42504804235与42504875126均四项通过（SQLite、PostgreSQL、Web、Python依赖审计），弥补本机PG跳过项。本段为后续仅文档补记，不代表另一次代码发行或生产部署。

已知限制：连续性规则只对结构化声明检查，无法证明表演或因果语义；像素尺寸不能证明无模糊/畸形；需逐镜用户审看。没有口型、自动角色参考出图、逐角色配音/多集管理；当前一个画外音。剧情生成不能充当真实软件操作。长期持续创作/其他视频类型保留，外部发布始终人工。
