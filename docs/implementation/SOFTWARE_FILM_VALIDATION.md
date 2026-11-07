# Issue #31：软件产品发布片 / 0.15.0-dev

用户选择“真实界面、重点特写、品牌动效”，继续本地自用。原效果证据为 `narrated-mixed-11s.mp4`：相同文字卡重复、半尺寸文字放大、界面只作全景缩放。新实现围绕开场、要点、界面演示、重点特写、品牌收尾；不把自动检查称为专业质量认证。

## 范围与调用链

`video.tsx / briefs.tsx → VideoInput.presentation + Shot.design → video.render_project → film.render_scene → video_audio.finish → 原预览/人工复核/高清/本机导出`。

- `film.py` 在目标分辨率绘制文字及分层入场，支持标题与真实界面并排、编号要点、步骤、全景、重点裁切和收尾；深墨/浅纸主题、品牌署名、强调色、短淡变、推进/平移/静止。
- 每镜独立主标题、补充说明、要点及旁白，避免整段旁白重复堆在画面上。不能容纳的文字明确报 `VID_DESIGN_TEXT_OVERFLOW`，不静默截断。裁切边界、真实素材、哈希、品牌归属、声明扫描继续校验。
- 旁白/授权配乐可作响度整理，目标 -16 LUFS / -1.5 dBTP；同时有旁白与配乐才启用侧链压低，回执如实记录是否使用。目标参数不等同于任意短片均测量达标。字幕保留底部安全区。
- 质量报告追加本模板的信息密度、长停留与版式提示，明确非行业标准、非评分；人工审核保持必要。
- 旧 API 不传 presentation 时仍为 classic；旧工程不自动改风格。指定内容仅在首次建工程时应用视觉配置；重复建立返回同一项目，不覆盖编辑。无新数据库迁移，DB 0014 / IR 1.1 不变；provider 为 `pillow_ffmpeg@4`，视觉为 `video_presentation@1`。

## 先失败，再验证

- 初始 studio 字段 POST 返回 422，trace `5cd0cdc90663201fac9a402c94cd957f`，第一条用例失败。
- 竖屏真实素材用例失败，trace `b4a06e05ba619ee94fe88dcfdb486a9a`；视口与缩放统一为偶数像素后通过。
- 实际 35.5 秒仅旁白预览卡在声音处理，job `6c02c5d12a5047ff9f50385892c1f50d` / trace `2b41d126502c6c402d9a147c8a26d9fe`；追加仅旁白用例失败，trace `ef70bb0ca08dbf670dc305b25b0795d9`。原因是无配乐时仍分出无限填充的侧链并连接空接收器。改为只在有配乐时分流后，实际声音合成完成。重启后只重排了这个被中断的合成验收任务，未修改其 IR 或审批。

已执行：

| 命令/验证 | 结果 |
|---|---|
| `.venv/Scripts/python.exe -m pytest tests/test_film_presentation.py -q` | 18 passed；真实三比例 × 三素材版式、音频字节与配乐频段衰减、仅旁白结束、保存/缓存/旧预览失效、脚本原文与首次配置 |
| `.venv/Scripts/python.exe -m pytest -q` | 145 passed / 1 skipped，93.51 秒；跳过本机未配置的 PostgreSQL |
| `npm.cmd run typecheck` | 通过 |
| `.venv/Scripts/python.exe -m ruff check services/api tests` | 通过 |
| `npm.cmd run check:boundary` | 91 个源码/配置通过；无平台自动发布 |
| `scripts/export-contracts.py` | 实际 OpenAPI、视频输入及错误码已重新导出 |

实际样片：[35.5 秒高清 MP4](../evidence/software-product-film-35s.mp4)、[五镜头抽帧](../evidence/software-film-frames.png)、[脱敏实测回执](../evidence/software-film-validation.json)。项目 `7bbefbf8ed304120a766cd1f48a1da10` / V5，final job `a02ee64ac9654f63ad44d329426897b8`。真实界面分别为本软件总览和图文编辑器，非生成界面；开场并排、要点卡、全景、特写和收尾均实际输出。

浏览器创建五镜头工程、修改引导短句并保存、提交中文配音、播放 V5 预览到结束（35.5 秒、未静音），检查规则报告后记录“仅合成验收”的确认并排队高清，均已执行。高清 1,838,231 字节，H.264 / AAC / 1920×1080，HTTP 下载字节与本机导出 SHA-256 一致；目录同时有 WAV、SRT 和工程。声音解码 RMS 2486.15、峰值 27628（PCM16），测量 -16.31 LUFS / -1.48 dBTP，确认有声音，未把输出目标冒充精确实测值。

已执行 42 页面 / 84 宽度检查，报告为 `docs/evidence/film-browser-smoke.json`。工程结构检查和三项诊断 unittest 退出 0。最终新建/编辑页在 375、390、768、1024、1440、1920 共 12 项检查通过（含实际导演控件），见 `film-final-widths.json` 和两张 mobile 截图。`npm.cmd run build` 生产构建退出 0；最终 TypeScript、全目录 Ruff、工程结构、三项诊断 unittest 均退出 0。301 份仓库文本做常见密钥格式检查，命中 0。`git diff --check` 通过。此处不把路由渲染算作全部业务通过，也不把浏览器自动下载取消的旧问题算作修复；本轮验证的是实际 HTTP 文件和本机直接导出。

本地版本不部署；Issue [#31](https://github.com/f123-b/tuiguang/issues/31) 的增量分支为 `feat/31-software-film-direction`，基于开放的 #30。远端 PostgreSQL/SQLite/Web/依赖审计结果以对应 PR 的当前提交 Actions 为准。

## 使用、成本与许可

“AI 宣传视频 → 软件产品发布片”填开场、真实要点、结尾并选择授权素材。进入工程可修改品牌、版式、标题、取景百分比、镜头运动，保存后制作配音与预览，播放复核后生成高清并保存到本机。已有项目先主动切换风格，再逐镜头调整。

新视觉及声音整理均在本机 CPU 执行，没有本轮收费模型请求、云资源或上线。DeepSeek 仍只承担文本工作。本机 Huihui 是系统声音，不能承诺播音级音色；更自然的音色可上传有使用权的配音。未新增素材库或付费 TTS，也不提供虚构界面、指标、音乐许可。

画面使用本仓库真实界面及明确标注的合成验收工作区，界面上的数字不代表真实经营数据。样片不包含背景音乐，配乐压低只在受控音调测试中验证，不把测试音调称为商业配乐。FFmpeg、字体及系统声音的商业使用边界沿用 LICENSE_INVENTORY.md。滤镜参数依据 [FFmpeg 官方文档](https://ffmpeg.org/ffmpeg-filters.html)。

## 回滚与限制

没有新迁移；可在工程内选择 classic 并保存为新版本，重新预览/审核。保留历史版本和旧文件；新字段随工程 JSON 保存，不覆盖旧素材。代码回滚到父提交 `53f37f3` 时，请先导出新工程并保留当前数据库/文件备份：旧编辑器不认识新字段，不应继续编辑 studio 工程。可恢复任务前的一致性备份；不删除用户数据。

画面效果仍取决于真实素材清晰度、取景、文案和人工剪辑判断。长句会缩小文字，超出容纳范围会阻止渲染；竖屏截图通常需要专门取景。没有生成式新场景、3D、专业配音服务或自动音乐授权。
