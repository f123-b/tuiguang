import os
import subprocess
import sys

from sqlalchemy import MetaData, create_engine, inspect, text
from sqlalchemy.engine import make_url

import pytest
import uuid


def upgrade_with_old_records(env):
    def upgrade(revision):
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", revision], env=env, text=True, capture_output=True
        )
        assert result.returncode == 0, result.stdout + result.stderr

    upgrade("0001")
    engine = create_engine(env["DATABASE_URL"])
    metadata = MetaData()
    metadata.reflect(engine)
    common = {"workspace_id": "w", "created_at": "2026-11-05T00:00:00Z"}
    with engine.begin() as connection:
        connection.execute(
            metadata.tables["brands"].insert(),
            dict(
                common,
                id="b",
                name="old brand",
                description="",
                audience="",
                website="",
                facts=[],
                revision=1,
            ),
        )
        connection.execute(
            metadata.tables["creator_profiles"].insert(),
            dict(
                common,
                id="c",
                brand_id="b",
                name="old creator",
                status="active",
                timezone="Asia/Shanghai",
                hour=9,
                weekdays=[0],
                style="",
                platform="xiaohongshu",
                daily_budget_cents=100,
                monthly_budget_cents=1000,
                model_consent=False,
            ),
        )
        connection.execute(
            metadata.tables["creator_runs"].insert(),
            dict(
                common,
                id="r",
                creator_id="c",
                operational_date="2026-11-05",
                slot="daily",
                idempotency_key="old",
                status="completed",
                stage="awaiting_user_review",
                trace_id="0" * 32,
                release={"agent_graph_version": "creator_graph@1"},
            ),
        )
        connection.execute(
            metadata.tables["content_packages"].insert(),
            dict(
                common,
                id="p",
                creator_id="c",
                run_id="r",
                title="preserve me",
                body="old evidence",
                platform="xiaohongshu",
                status="awaiting_user_review",
                generation_source="template",
                fact_refs=[],
                compliance={},
                revision=1,
            ),
        )
        connection.execute(
            metadata.tables["budget_ledgers"].insert(),
            dict(
                common,
                id="l",
                creator_id="c",
                run_id="r",
                operational_date="2026-11-05",
                reserved_cents=10,
                actual_cents=8,
                status="settled",
            ),
        )
    engine.dispose()
    upgrade("head")
    upgrade("head")
    engine = create_engine(env["DATABASE_URL"])
    with engine.connect() as connection:
        assert connection.scalar(text("select title from content_packages where id = 'p'")) == "preserve me"
        assert (
            connection.scalar(text("select billing_date from budget_ledgers where id = 'l'")) == "2026-11-05"
        )
        assert connection.scalar(text("select actual_cents from budget_ledgers where id = 'l'")) == 8
        assert connection.scalar(text("select input_snapshot from creator_runs where id = 'r'")) is None
        assert connection.scalar(text("select version_num from alembic_version")) == "0004"
        assert connection.scalar(text("select graphics from content_packages where id = 'p'")) is None
        assert connection.scalar(text("select graphics_render from content_packages where id = 'p'")) is None
    engine.dispose()


def test_frozen_migration_repeat_upgrade_and_backup_restore(tmp_path):
    database = tmp_path / "migration.db"
    env = {**os.environ, "DATABASE_URL": "sqlite:///" + str(database), "PYTHONPATH": "services/api"}
    upgrade_with_old_records(env)
    engine = create_engine(env["DATABASE_URL"])
    with engine.begin() as connection:
        assert connection.scalar(text("select version_num from alembic_version")) == "0004"
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


@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="PostgreSQL service not configured locally")
def test_postgres_additive_upgrade_preserves_old_records():
    url = make_url(os.environ["TEST_DATABASE_URL"])
    namespace = "migration_test_" + uuid.uuid4().hex
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{namespace}"'))
    try:
        isolated = url.update_query_dict({"options": f"-csearch_path={namespace}"})
        upgrade_with_old_records(
            {
                **os.environ,
                "DATABASE_URL": isolated.render_as_string(hide_password=False),
                "PYTHONPATH": "services/api",
            }
        )
    finally:
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{namespace}" CASCADE'))
        engine.dispose()
