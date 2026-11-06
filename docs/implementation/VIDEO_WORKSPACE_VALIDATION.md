# B / M3-005 / #9：可恢复的视频工程

版本 0.5.0-dev / DB 0005 / Video IR 1.1 / pillow_ffmpeg@2。视频工作室路径不变：`/studio/video/new`、`/studio/video/:id`。调用链：工程带版本保存 → 来源/授权/文本/音轨校验 → 分镜哈希缓存 → FFmpeg 字幕/混音 → 实际媒体探针 → 用户观看 → 内容绑定并人工审核 → ZIP 内 MP4/工程/SRT/来源。

新增 `video_edit.py`、`video_edit_api.py`、`video_audio.py`、`speech.py`、`pages/video-editor.tsx`、0005 扩展历史表与内容附件字段。旧项目与旧片可读取；旧 IR 1.0 未完成渲染明确停在 VID_IR_UPGRADE_REQUIRED，不悄然按新引擎继续。用户显式编辑/保存升级为 1.1 后可渲染。

实际验证：

- 新 API 失败用例：`python -m pytest tests/test_video_workspace.py -q`，3 failed（音频 422、工程 PUT 405、绑定 404），实现后通过。
- 损坏产物用例先失败：丢失成片时 render 返回旧 completed job；增加文件完整性判断后生成新任务并复用其他分镜缓存，恢复通过。
- `.venv/Scripts/python.exe -m pytest -q`：54 passed / 1 skipped，21.60s，退出 0；本机 PostgreSQL 未配置。
- `python -m pytest tests/test_speech.py -q`：1 passed，实际 Windows 中文系统语音生成 RIFF/WAVE，非空，资产保持 verified=false。Linux CI 不具备系统语音，明确跳过此真实 OS 用例。
- `python -m ruff check services tests infra scripts`、`npm.cmd run typecheck`、`npm.cmd run build`、`npm.cmd run check:boundary`：均退出 0，边界扫描 56 文件；实际契约已导出。
- 实际测试含字幕烧录、SRT 时间戳、授权 WAV 混音、三次连续编辑和恢复、锁定拒绝覆盖、音轨越界/未授权阻断、内容视频绑定、真实 MP4 进入 ZIP、视频修订后旧包阻断。
- 本机停止 API/Worker 后使用 SQLite backup 保存 `.data/backups/pre-0005-20261106-130428.db`，integrity_check=ok；实际 0003→0004→0005，保留 3 条已有内容，升级后 integrity_check=ok。

本阶段未执行的新增 30 秒三类黄金片、浏览器操作与 PostgreSQL CI，在持续开发 E 集成报告中补齐；既有 20 秒证据不能替代本轮 30 秒验收。

无新增运行时依赖、外部模型、GPU 或付费 TTS。离线 TTS 仅使用真实已安装 Windows 语音，不打包权重，商业权利未知并要求用户再核实。字体与 FFmpeg 延用 LICENSE_INVENTORY 的实际边界。原始素材、音频许可、字节哈希进入回执；内部技术探针不等于平台合规审核。未实现生成式视频/3D/连续卡通生产，UI 保留不可用能力说明。

回滚保留扩展表列并停止新版 Worker；完整回退恢复升级前备份到隔离目录。新版音轨/字幕/附件不得交给旧打包器处理，旧已完成文件不改写。下一步连续开发 C：真实数据复盘、用户反馈与可审批策略。
