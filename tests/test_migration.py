import os
import subprocess
import sys

from sqlalchemy import create_engine, inspect, text


def test_frozen_migration_repeat_upgrade_and_backup_restore(tmp_path):
    database = tmp_path / "migration.db"
    env = {**os.environ, "DATABASE_URL": "sqlite:///" + str(database), "PYTHONPATH": "services/api"}
    for _ in range(2):
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"], env=env, text=True, capture_output=True
        )
        assert result.returncode == 0, result.stdout + result.stderr
    engine = create_engine(env["DATABASE_URL"])
    with engine.begin() as connection:
        assert connection.scalar(text("select version_num from alembic_version")) == "0001"
        assert {
            "creator_profiles",
            "creator_runs",
            "manual_publish_records",
            "budget_ledgers",
            "video_projects",
        } <= set(inspect(connection).get_table_names())
        connection.execute(
            text(
                "insert into users (id,email,password_hash,workspace_id,name,role) values ('u','backup@test.org','hash','w','backup-test','owner')"
            )
        )
    engine.dispose()
    import sqlite3

    backup = tmp_path / "backup.db"
    with sqlite3.connect(database) as source, sqlite3.connect(backup) as dest:
        source.backup(dest)
    with sqlite3.connect(backup) as restored:
        assert restored.execute("select name from users").fetchone()[0] == "backup-test"
        assert restored.execute("pragma integrity_check").fetchone()[0] == "ok"
