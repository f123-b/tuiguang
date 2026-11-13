# 《你来试试》修订4 · 音频驱动表演

任务#53。修订3已被用户否决；本目录是重新制作的18.25秒完整短剧，**技术检查通过，用户艺术审核未通过/待审**。没有生产发布，也没有把独立影片当成正式软件的新Provider。

- [本机观看与下载](http://127.0.0.1:8792/watch)：超分成片、超分前对照、字幕、制作包、角色声音母带、前期资料。
- 成片：仓库根目录`.data/short-drama-53/v4/你来试试-v4-超分成片.mp4`；对照和原生片段同目录保存，未覆盖旧片。
- [剧本与表演](剧本与表演.md)、[实际验证、失败和回滚](../../../../docs/implementation/AUDIO_DRIVEN_DRAMA_VALIDATION.md)。两位人物三视图、空场景及逐镜首帧在[上版前期素材](../v3/assets/)，完整图像提示词与来源在v3目录；动态提示词冻结在s2v.py及每次真实graph回执。
- `edit.json`是独立剪辑契约，**不是VideoProjectIR**；正式VideoInput仅支持30fps，未伪造可导入的24fps IR。正式应用0.20.0-dev、DB0016、IR1.1不变。

## 本轮处理

每个角色先生成一条连续库存声音母带，再按固定样本切分。S2V以参考图、同一条音轨和动作提示一起生成嘴部、表情和身体，不再用MuseTalk嘴部覆盖。男声Dylan、女声Serena；无真人克隆。母带在视频生成前已固定语速，之后剪辑不单独变速或移动对白。

四段表演实际原生832×480/16fps，女主两段取自同一声音母带，分段音频逐样本匹配。逐镜插帧至24fps后实际运行RealESRGAN神经x2，最后合成1920×1080/24fps/48kHz AAC，共438帧。S01只裁去底部32px以移除模型虚构腕表，没有裁脸或盖嘴；手部操作沿用原生1280×704片段。真实UI与字幕在超分后合成。**不是原生1080p，超分不能保证真实细节、口型逐字准确或时序无瑕疵。**

## 本机使用

从仓库根目录运行；依赖为本机已安装的隔离环境、FFmpeg、固定模型，ZIP不含模型/运行时/密钥。新机器不能只解压ZIP就声称可运行。版本和来源见film-versions.json；不运行上游任意云脚本。

```powershell
# 已有影片：验证，不重新生成
.venv/Scripts/python.exe -m unittest discover -s examples/short-drama/try-it/v4 -p test_contracts.py -v
.data/qwen-clean-runtime/Scripts/python.exe examples/short-drama/try-it/v4/check.py
node examples/short-drama/try-it/v4/review-server.mjs

# 明确制作后续修订时才运行：本机GPU，数十分钟/镜头
node scripts/start-local-video.mjs
.venv/Scripts/python.exe examples/short-drama/try-it/v4/remainder.py
.venv/Scripts/python.exe examples/short-drama/try-it/v4/postprocess.py
```

现存完成回执会校验复用；错误或未知提交不自动重发。v1声音脚本与145帧女主失败记录只作历史，**不要作为推荐重做入口**。实测8GB显存145帧在KSampler OOM；改用77/69帧的显式新镜头，契约限制当前本机配置不超过77帧，不代表所有硬件的通用上限。重新生成必须使用新的take名称并保留原片。

## 交付边界

API、数据库、正式引擎注册、平台发布和人工审核流程均未修改。没有付费云视频调用或生产部署；本机用电、内置ImageGen实际账户费用不确定。库存声、模型训练/输出、FFmpeg和字体完整商业发行许可尚未确认。未人工逐字听审，未做全应用回归或模型环境漏洞审计。回滚可停止本轮8792审看进程并回到旧片/297783b源码；不涉及数据库降级或数据删除。
