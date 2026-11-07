# #33 · 产品片慢镜头修复与有招操作样片

日期：2026-11-08。目标是修复用户反馈的“像 PPT、不流畅”。唯一代码主模块为 `services/api/creator/film.py`，调用链为渲染任务 → `video.render_project` → 镜头缓存 → `film.render_scene`。此任务没有生产发布，没有改动有招产品的业务源码。

## 客观证据与根因

被反馈的三条有招 MP4 的帧数与恒定 30fps 相符：总览 1223 帧、项目经历 1143 帧、竖屏 664 帧。对应项目为 e1ec094aadd64ff6b59b3ef7d43491b2 / 15c2a410f71347a3bd85dd797b967ed9 / 1d50cf10f6354711be9f1df6471e2938，最终任务分别为 7a6d1ff521fa48dc87af1fd85084e537 / f1b1818590764adeba91fe5b3d728da6 / 99dc7f8ce9f140d49dc343566eb41304。因此不能只根据观感认定文件掉帧。

实际内容以静态截图、标题入场、长时间停留为主，镜头硬切；这解释了 PPT 感，属于素材与剪辑结构问题。另有独立可重复的引擎缺陷：目标分辨率上的 `zoompan` 对采样窗口及位置取整，慢速运动大量重复像素。6 秒、640×360、30fps、无损编码的条纹素材，在排除文字入场后的 149 次相邻帧中：

| 运动 | 旧版变化次数 | 旧版最长相同帧串 | 修复后变化次数 | 修复后最长相同帧串 |
|---|---:|---:|---:|---:|
| pan | 13/149 | 12 帧 | 149/149 | 1 帧 |
| push | 34/149 | 6 帧 | 149/149 | 1 帧 |

原始两项失败退出 1；固定基线提交 `0851d3a32b85e87237f3d02caacb68596dd56d09` 的复测数值见 [脱敏回执](../evidence/smooth-camera-validation.json)。该最小复现不经过 API/Worker，因此 trace_id、creator_run_id、content_id、video_project_id、shot_id、render_job_id 均为 null，不伪造线上 trace 或错误码。

修复使用 `perspective` 每帧计算浮点源角点与 cubic 插值，不创建巨大中间位图。该滤镜的 on 从 1 开始，已扣除 1 对齐镜头首尾；依据 [FFmpeg 官方实现](https://github.com/FFmpeg/FFmpeg/blob/master/libavfilter/vf_perspective.c) 和 [官方滤镜文档](https://ffmpeg.org/ffmpeg-filters.html#perspective)。仍保留 6% 推进/平移幅度；没有声称修正运动就能使静态内容自动成为专业发布片。

## 真实执行结果

本机 PowerShell 使用 `npm.cmd` 和 `.venv\Scripts\python.exe`，Python 命令设置 `PYTHONPATH=services/api`、`PYTHONUTF8=1`。

| 命令 | 退出码 | 实际结果 |
|---|---:|---|
| `python -m pytest tests/test_film_motion.py -q`（旧引擎、初始两例） | 1 | pan 13/149、push 34/149，2 failed |
| `python -m pytest -q`（预览/1080p 与实际视频回归已加入） | 0 | 151 passed / 1 skipped，89.62 秒；本机没有 PostgreSQL，明确跳过 |
| `python -m pytest tests/test_film_motion.py tests/test_film_presentation.py tests/test_narration_pipeline.py -q`（最终帧计数适配后） | 0 | 35 passed，33.07 秒 |
| `python -m ruff check services/api/creator/film.py services/api/creator/video.py tests/test_film_motion.py` | 0 | All checks passed |
| `python -m ruff format --check`（上述三文件） | 0 | 3 files already formatted；初次格式检查失败，已修正后重跑 |
| `python scripts/export-contracts.py` | 0 | 从实际代码重新导出；仅 OpenAPI 应用版本变化 |
| `npm.cmd run typecheck` | 0 | TypeScript 通过 |
| `npm.cmd run check:boundary` | 0 | 91 个源码/配置文件；边界通过 |

新增测试实际解码预览及 1080p 的 pan/push 帧；另将红/绿两段真实 MP4 裁切后分别用 pan/still 渲染，核对 60 帧、前后颜色变化与原素材时间进度，防止把录屏冻结成静态图。既有相关测试覆盖三比例、原生排版、溢出、裁切、来源/审核、配音与混音。没有新增数据库迁移；升级回退检查包含在全量迁移用例内。本轮没有声称本机 PostgreSQL 或最终前端生产构建已运行；远端另看当前 PR 的真实检查。

## 样片与边界

有招样片放在本机 `.data/有招实录-20261108/交付文件/`。内容是实际运行的 Electron 有招客户端，用全新隔离资料目录，录制岗位要求输入、项目创建/职责备注和回答表达设置；全部文字为明确的演示资料，不使用个人账号、真实简历、模型密钥或面试录音。没有向外部模型发送请求，没有用 mock 回答冒充真实生成。简历自动分析在未配置模型的隔离环境中失败，该功能不在本条样片展示范围，也不因此声称已完成有招的模型联调。

该片为单独的本地编辑流程：真实客户端像素 + 按动作剪辑 + 浮点相机路径 + 重建的演示指针/点击圈 + 标题/字幕 + Huihui 系统旁白 + 本地合成配乐。最终 1920×1080 / 60fps / 29.5 秒；60fps 指合成画面帧率，原始操作捕获按实际 UI 更新，不宣称客户端原生录制了 60fps。它不是服务端的 RenderJob，不在数据库中伪造人工审核或发布批准，render_job_id=null。重新制作其他片仍需合适的真实素材和剪辑；没有新增自动录制任意软件、云视频或专业配音服务。

最终文件的 SHA、解码帧数、时间戳、音频测量、来源和浏览器播放结果随本机交付回执保存；请用该回执核对当前文件，历史迭代文件不能代替最终文件验证。

## 影响、版本与回滚

| 领域 | 本次影响 |
|---|---|
| API / DB / IR | 请求与审核契约不变；DB 0014、IR 1.1；无需迁移 |
| 视频引擎 | studio pan/push 浮点采样；注册、缓存和回执 provider 同为 @5；旧缓存隔离，旧 MP4 保留 |
| Prompt / 模型 | fact_bound@2、creator_graph@2 保留；没有新增调用或凭据复制 |
| UI | 没有新增控件；已有预览重新制作后应用修复 |
| 合规 | 人工发布、事实、素材、预览确认门槛不变；测试片没有实际用户审核记录 |
| 成本 | 本地 CPU/磁盘制作；本轮新增云模型调用为 0；不把 CPU/电费算作零 |
| 文档 | 状态、模块映射、契约、变更记录、手册和本报告更新 |

应用冻结为 0.15.1-dev / provider pillow_ffmpeg@5 / video_presentation@1；其余版本以 `release_manifest.json` 为准，stable=false。字体、系统语音、现有 FFmpeg 构建的商业许可仍需独立确认；本轮没有取得新的商业许可。配乐是本地数学合成，没有外部歌曲录音；这不构成法律许可认证。素材和私有脚本留在被忽略的 `.data/`，不推送个人数据、音频或密钥到 GitHub。

回滚代码可回到基线提交 `0851d3a`，不删除数据库或历史文件；旧 provider @4 与 @5 缓存相互区分。停机前已确认模型运行、配音、渲染活动数均为 0，并用 SQLite backup API 保存一致性备份到本轮私有目录。新成片不覆盖旧样片；引擎更新后重新制作预览，任何高清审核都须由真实操作者完成。风险仍包括 FFmpeg 构建/插值差异、录屏原始清晰度、剪辑和系统音色；不以测试数量代替用户对艺术质量的判断。
