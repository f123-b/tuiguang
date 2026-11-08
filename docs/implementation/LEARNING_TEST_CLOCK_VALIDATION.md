# #42 历史复盘测试的证据日期

目标：恢复历史周期用例的确定性；应用版本、API、数据库、视频引擎、Prompt、预算、UI和许可均不变。

Observed：0d90ed2 在2026-11-08执行两个代表用例，退出1 / 2 failed：AI复核返回422 LEARNING_EVIDENCE_INSUFFICIENT（trace_id 22ad8eb711dda4ebb7aa50ee9cae8ad4），反馈计数0。测试声明11月1–7日周期，却以运行日创建证据。源码 learning.py 按 Content、ContentRevision 和 Feedback 的 created_at 筛选，生产过滤符合契约。

修复仅在三个复盘测试模块启用 historical_learning_evidence fixture，给未显式指定日期的合成内容/修订/反馈写入2026-11-05。SQLAlchemy监听器在finally移除，不修改全局时钟或生产函数。显式周期外日期保留，新用例证明10月30日反馈不计入11月报告。

实际命令（Windows / Python3.12）：

- 修复前：pytest tests/test_ai_review.py::test_paid_review_is_idempotent_and_does_not_become_a_daily_task tests/test_learning.py::test_report_missing_data_feedback_strategy_and_rollback -q --maxfail=2：退出1，2 failed。
- 修复后：pytest tests/test_ai_review.py tests/test_learning.py tests/test_learning_safety.py -q：退出0，11 passed。
- ruff check tests：退出0，All checks passed。
- 此独立分支全量与PostgreSQL：未运行；由依赖分支全量及远端CI补验。

变更：tests/conftest.py 与上述三个测试模块，以及本文/状态/变更记录。无外部调用、凭据和新商业资产；无生产操作。回滚本次提交即可恢复测试文件；应用运行状态没有变化。发行矩阵仍为0.17.0-dev / DB0014 / IR1.1 / provider@5。
