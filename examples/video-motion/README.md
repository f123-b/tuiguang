# 有招连续空间镜头试片

这是独立剪辑实验，**没有注册为正式视频 Provider，也不是一键自动导演**。固定故事、相机、真实界面素材与时间线是本次人工编排；字幕关键词不是自动逐词强制对齐结果。原有 VideoProjectIR 和审核流程不变。

本轮实际使用 Three.js 0.187.0，在 RTX 4060 的 Chrome WebGL2 环境渲染；900 张 1920×1080 PNG 按 30fps 编码为 MP4。纸页曲面、金属框、线带、光照、景深和相机均由代码生成，产品界面纹理来自隔离演示环境的真实有招 0.2.24，文本为合成练习资料，不是客户证言。

从仓库根运行。只使用你有权处理的截图/录制与声音；本仓库不附带权重、二进制、原始捕获或账号数据。

1. 在独立目录安装 `npm.cmd install --prefix .data/motion-runtime three@0.187.0 --save-exact --ignore-scripts`。
2. 准备 `.data/motion-lab/assets/capture.json`，格式为 `{"frames":[{"wall":0.0,"url":"/assets/ui-000.jpg"}]}`；wall 按真实捕获秒数递增。放入真实捕获的对应 JPG，本片使用 70 张帧；原始帧不是 30fps 屏幕录制，不作此承诺。不能把无来源截图冒充真实 UI。
3. `node examples/video-motion/serve.mjs`，打开 `http://127.0.0.1:8769`，拖动滑杆检查画面，再点“逐帧导出”。服务仅绑定本机；帧写入 `.data/有招动效试片-20261108/frames/`，只接受会话令牌、同源请求、连续编号和受限 PNG 大小。
4. 准备本次有使用权的 `.data/有招动效试片-20261108/完整旁白-温和讲述.wav`。该固定样片要求旁白少于 29 秒，不裁切或加速；本轮使用 Qwen 本地模型实际生成 24.8 秒。
5. `python examples/video-motion/mix_sample.py`，需要 Pillow、NumPy、FFmpeg；输出两个音轨、混音、MP4 与抽帧图。本脚本使用 Windows 已安装字体，商业用途需独立确认。

渲染输出会重写该实验目录内同名编号帧和同名试片；用户正式项目与旧故事版文件不在目标目录。已完成试片请另存再实验。播放、帧连续和无截波可以测量；“高级、自然、好看”仍需观众判断。Three.js 依赖许可证是 MIT，分发依赖须保留其 LICENSE；具体本轮验证、模型来源和限制见 `docs/implementation/EXPRESSIVE_MOTION_VALIDATION.md`。
