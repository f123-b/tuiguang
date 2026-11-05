# 本地备份、恢复与回滚

适用当前开发版，不是已部署的生产灾备方案。

1. 暂停创作者，停止 `npm run dev`。确认 Worker 不再写库，备份整个 `.data` 目录和 `.env` 到你控制的安全位置；里面有用户内容及会话密钥，不能推送 GitHub。
2. 对运行中的 SQLite 单库备份使用 Python `sqlite3.Connection.backup`，不要只复制主 `.db` 而丢掉 WAL。自动测试 `test_migration.py` 已演练迁移、备份、恢复与 integrity_check。
3. 恢复到隔离目录，配置 `DATA_DIR`、`DATABASE_URL` 和原密钥。先检查数据库完整性及文件哈希，再启动兼容版本 Worker；恢复前暂停状态不会自动改成运行。
4. 旧代码版本回滚用已验证的 Git commit，并保持数据备份。当前初始迁移禁止危险 downgrade；不要通过删表模拟回滚。已有开发数据库升级只执行显式 `alembic upgrade head`。
5. 任务冻结 Agent 图 / 模型版本；不兼容时停在 `RUN_VERSION_UNSUPPORTED`。安全的本地生成任务可在租约到期后恢复；存在未知付费回执的任务不能自动重复发送。
6. PostgreSQL 的 pg_dump / PITR、S3 素材恢复、旧 Worker 版本并存仍需后续在真实部署中演练。不要将 SQLite 测试等同为生产数据库恢复通过。

回滚软件不会撤回用户在外部平台亲自发布的作品。生产变更、数据删除、付费资源开通和生产迁移须由有权限的操作者另行批准。
