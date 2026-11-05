# 诊断报告：run_demo_20261105

> 仅从提供的脱敏样例事件归纳事实；不是自动根因确认，更没有任何生产修复。

事件数：5

Trace ID：`0123456789abcdef0123456789abcdef`
运行发行：`demo-not-a-real-release`

| 阶段 | 状态 | 镜头 | 错误码 |
|---|---|---|---|
| creator.daily_plan | ok | - | - |
| content.script | ok | - | - |
| video.storyboard | ok | - | - |
| shot.render | error | scene_04 | VID_RENDER_RESOURCE_EXHAUSTED |
| video.compose | skipped | - | - |

## 失败事件（仅观察）
- **阶段** `shot.render`；**镜头** `scene_04`；**错误码** `VID_RENDER_RESOURCE_EXHAUSTED`；**Provider** `wan_worker`。
  - 收到证据摘要（原文已省略；应在有权限的观测平台核实）。

## 下一步
1. 在有权限的日志平台查看相关 trace 的首次失败 span 和脱敏错误原文。
2. 将当前发行号与 Provider/模型/Prompt/镜头版本进行关联。
3. 在隔离环境使用合法测试资产复现；若未复现，收集更多指标。
4. 修复后运行相关回归测试；生产操作仍须人工审批。

**结论：尚无充分证据证明最终根因。**
