# 多类型本地视频制作

正式入口为 `/studio/video/new`，服务端 `video_recipes.py` 编译用户逐镜内容与授权资产，复用 VideoProjectIR 1.1 / Shot / Pillow 与 FFmpeg / NarrationJob / RenderJob。不是独立假 API 或一次性导演脚本。

五种本地形式：MG 图解、录屏教程、全画幅素材混剪、插画分镜、混合制作。六种内容结构：功能讲解、用户问答、操作教程、品牌故事、版本更新、品牌形象。栏目与制作引擎独立；插画为授权图片的镜头运动与对白，不代表连贯角色表演。

`GET /api/v1/videos/recipes` 读取当前能力，`POST /api/v1/videos/from-recipe` 创建并排队预览，必须带 Idempotency-Key。请求包含 brand_id/name/recipe_id/mode/size/scenes；每镜 headline/narration/supporting/points/duration_frames/asset_id/trim_start_frame/motion/treatment/crop。可选 narration 使用现有已安装声音与明确用途确认。无旁白时不提交 narration。先审看带水印预览，再按原审核流程生成1080p。示例请求见导出的 OpenAPI。

指定内容创作可直接在脚本确认阶段选择画面形式；Build 新增可选 production_mode / recipe_id，不提供时兼容旧版构建。AI 脚本、用户原文共用此编译器；不改变脚本模型或费用规则。连续日更的原制作配置保留，不声称已升级为全自动导演。

本地验收素材和视频不随 Git 分发。若已有 `projects.json` 与对应真实预览 MP4，可运行：

```powershell
node examples/video-recipes/review-server.mjs "D:/推广助手/.data/多类型视频验收-20261108"
```

打开 http://127.0.0.1:8787/watch。画廊仅服务明列的预览文件，不修改工程、批准高清或对外发布。实际验收、来源、版本和回滚见 `docs/implementation/VIDEO_TYPES_VALIDATION.md`。
