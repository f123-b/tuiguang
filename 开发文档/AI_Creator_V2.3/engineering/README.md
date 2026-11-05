# Engineering starter kit（模板，不是已接入正式产品的服务）

本目录可拷贝到真实仓库后逐步接线。所有 Python 诊断代码仅使用标准库、合成演示数据，可本地执行：

```bash
python engineering/scripts/diagnose.py --input engineering/examples/demo_traces.jsonl --run-id run_demo_20261105 --out /tmp/creator_diag_report.md
python engineering/scripts/validate_contracts.py
python -m unittest discover -s engineering/tests -v
```

`diagnose.py` 只根据显式的错误事件输出**观察到的事实**，不声称已经做自动化根因分析，也不会连接 API、日志服务器或用户数据。正式工程应接入 OpenTelemetry SDK、Collector、时序指标、工作区 RBAC 和脱敏/留存策略。

`.github/workflows/engineering-quality-template.yml` 仅运行设计包本身的示例测试；安装到真实软件仓库时必须添加业务和端到端测试，设置合并必需门禁。本目录不会访问或发布社交平台内容。
