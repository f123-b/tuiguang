# #41 多类型视频制作验收 · 0.18.0-dev

目标：让其他视频形式成为实际可制作的工程，而不是所有入口都改写成同一套产品发布片。主模块 VIDEO；依赖 WEB-PAGES、BRIEFS、NARRATION 既有边界。

## 实现与调用链

`/studio/video/new` → `GET /videos/recipes` / `POST /videos/from-recipe` → video_recipes.py 编译用户内容 → VideoProjectIR 1.1 / Shot → 原 NarrationJob / RenderJob → 带水印预览 → 质量报告与人工确认 → 高清 / 导出。指定内容脚本的 Build 也可传 production_mode / recipe_id 使用同一编译器。

五种本地形式：MG 图解（节点、连接与持续运动标记）、录屏教程（保留源比例）、素材混剪（全画幅）、插画故事（图像分镜框与对白区）、混合制作（逐镜选呈现）。六种内容结构：功能讲解、问答、教程、品牌故事、版本更新、品牌形象。结构指导用户填写，不代替事实核实或自动编造剧情。

新建工程可逐镜编辑标题、旁白、补充文字、图解节点、授权素材、入点、时长和排序；生成后继续使用原镜头编辑、裁切、锁定、配乐、字幕、历史恢复和导出。可选同步本机配音；不启用时明确为无旁白预览。素材缺失、未授权、过期、跨租户、视频过短或类型不匹配会拒绝，不自动换成文字片。

核心变更文件：`services/api/creator/video_recipes.py`、`film_types.py`、`film.py`、`video.py`、`schemas.py`、`video_edit_api.py`、`briefs.py`、`brief_api.py`；UI `pages/video.tsx`、`briefs.tsx`、`film-design.tsx` 与 `lib/api.ts`；测试 `tests/test_video_recipes.py`；契约 `packages/schemas/*`；版本清单与本文、模块地图、使用手册、状态及 CHANGELOG。`examples/video-recipes` 只有可选本地审片画廊，不取代正式工作台。

## 契约与兼容

- 新建请求要求 Idempotency-Key：同请求返回同工程，改参数复用键返回409。键按工作区隔离，数据库主键保证并发唯一；编辑后重放不覆盖修订或重新配音。
- production_recipe 为服务器维护的创建来源，保存时保留，scope=creation_provenance，不表示手工修订后的每镜仍由原配方控制。
- SceneDesign.layout 兼容增加 diagram/montage/comic；旧请求、classic 样式、旧脚本构建未提供 production_mode 时保持原行为。模板编译只接受短标题，超过80字明确提示修订，不截掉必现文字。
- 无迁移，SQLite仍0014；无新依赖、付费视频接口、Prompt或模型更换。新镜头缓存注册版本为 pillow_ffmpeg@7；开发中@6预览保留为first-cut文件，安全区修订不复用该缓存。
- 原每日持续任务配置保持兼容，未声称已升级为全自动多类型导演；云生成、连贯角色表演、Blender三维Provider仍未接入。已有授权AI/三维渲染素材可作为普通素材导入。

## 实际执行

所有命令在 D:/推广助手，Python使用 .venv/Scripts/python.exe，设置 PYTHONUTF8=1；导出契约另设置 PYTHONPATH=services/api。

| 命令 / 验收 | 实际结果 |
| --- | --- |
| `python -m pytest tests/test_video_recipes.py -q --maxfail=1`（实现前） | 退出1；目录API404，1 failed |
| 补充文字安全区失败用例（调整前） | 退出1；diagram文字框侵入字幕区，1 failed |
| `python -m pytest -q --junitxml=.data/pytest-video-types-final.xml` | 退出0；212 passed / 1 skipped（本机无PG） |
| `python -m pytest tests/test_video_recipes.py -q`（后补高清正向断言） | 退出0；42 passed，含五种预览、合成测试审批后的1920×1080文件、审核前409、五种配音/字幕、脚本入口、三比例构图、持续动画、素材/租户/时长/幂等/旧工程保存 |
| `python -m ruff check services tests infra scripts` | 退出0；All checks passed |
| `python scripts/export-contracts.py` | 退出0；实际API/DTO导出OpenAPI、视频输入与错误码 |
| `python engineering/scripts/validate_contracts.py` | 退出0；仅工程模板结构验证 |
| `python -m unittest discover -s engineering/tests -v` | 退出0；3 tests OK |
| `npm.cmd run typecheck` / `npm.cmd run check:boundary` | 均退出0；类型检查通过，96份源/配置边界检查通过 |
| `npm.cmd run build` | 退出0；Next16.4.5生产构建成功，不代表已部署 |
| `.data/video-types-acceptance.py` + `.data/video-types-rerender.py` | 均退出0；真实HTTP上传来源、制作13段本地Qwen旁白、自动字幕、五条预览；修订只复用已有音轨重新渲染 |
| `.data/video-types-verify.py` | 退出0；五条完整解码、帧数/尺寸/30fps/48kHz/非静音通过 |
| agent-browser 浏览器回归 | 真实表单创建MG与Qwen任务；指定内容脚本选择混剪并建立工程；五条预览静音自动播放到结尾，各0丢帧/无媒体错误；390px画廊无横向溢出 |

浏览器执行离屏按钮时，CLI引用点击未触发请求，改用页面原生DOM click触发React处理并核对201与工程；未把最初空点击计为通过。浏览器播放为自动静音技术检查，不代表人类听感或艺术审核。

全量最初仍复现原分支7项复盘日期失败，独立Issue #42 / PR #43修复合成证据日期，未改生产过滤；相关11项通过，远端42470704365四项通过。此视频分支继承该修复。详见 LEARNING_TEST_CLOCK_VALIDATION.md。

## 真实媒体

目录：`D:/推广助手/.data/多类型视频验收-20261108/`。五条都为未人工批准的带水印制作预览，没有替用户确认高清或发布。

| 类型 | 实际视频ID | 时长 / 帧数 / 尺寸 | 实测LUFS / 真峰值 |
| --- | --- | --- | --- |
| MG | 3e7fad97f22f1d622fff6a7570092237 | 20s / 600 / 640×360 | -16.7 / -1.6dBFS |
| 录屏 | ce2e7c9ddb51300c4153456e32db8f85 | 10s / 300 / 640×360 | -15.8 / -1.3dBFS |
| 混剪 | 9a2af6f2344aceb2dcf14b11dcd591b9 | 10s / 300 / 360×640 | -15.8 / -1.5dBFS |
| 插画 | 3a9c4d77f08fba203968320ccdfbbad4 | 10s / 300 / 360×360 | -15.2 / -1.4dBFS |
| 混合 | 263c8c69af00933d42315d83f8d49dd2 | 15s / 450 / 640×360 | -16.0 / -1.4dBFS |

来源/哈希/逐镜回执在 sources.json、projects.json、technical-checks.json；浏览器回执为 `.data/video-types-browser-playback.json`。响度与真峰值为成片测量，现有处理目标不等于精确达标承诺。首版文件和旧预览回执保留，不覆盖已审核成片。

## 安全、许可、风险与回滚

真实界面仅用合成项目备注；已核对 ProjectLibraryPage.tsx:368 与隔离实录，不用首页示例准确率或真实履历。Pexels咖啡素材与Coverr书写擦除素材沿用已核对公开许可（pexels.com/license、coverr.co/license），仅本地合成，不在Git分发原片，不暗示素材人物代言。插画由本对话image_gen生成，明确AI插画/情景演绎，用于内部验收；商业法律审查未运行。Qwen仍使用已冻结本地1.7B模型、内置声音与用途确认，无声纹克隆。

未新增外部收费视频/TTS调用；本轮图像生成工具1次，账单费用未知，不冒称免费。没有提交凭据、原片、权重或私有数据库；没有第三方发布动作、生产迁移、删除或上线。字幕安全区已抽帧修订并补契约用例，但任意长文/素材仍需预览检查；画面说明不是自动场景生成。

回滚至依赖PR #43提交2e9ee45可撤回本次应用功能，或至0d90ed2同时撤回测试日期修复；数据库无需降级。新类型工程先导出并停止新渲染，旧引擎不识别新layout，勿用旧Worker处理新工程。既有媒体文件和历史保留。本地启动前备份SQLite并校验integrity_check=ok，无活动制作任务时才重启；备份在.data/backups，不进Git。

版本冻结：App0.18.0-dev / DB0014 / creator_graph@2 / fact_bound@2 / IR1.1 / pillow_ffmpeg@7 / video_recipes@1 / video_presentation@1 / narration_pipeline@3 / story_direction@1 / qwen_local@1 / local_editorial@3 / inventory@3；模型修订与实际哈希沿用任务回执。未生产部署；用户艺术审批、真实片高清审批尚未运行。
