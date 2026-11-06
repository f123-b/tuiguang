from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from creator.db import SessionLocal
from creator.jobs import process_pending
from creator.models import BudgetEntry, Content, Run
from test_continuous_media import configure


def test_crash_after_durable_draft_resumes_media_without_second_model_call(
    client, creator_profile, monkeypatch
):
    configure(client, creator_profile)
    import creator.production as production
    from creator.jobs import graph

    original = graph.invoke
    original_prepare = production.prepare
    calls = []

    def spy(*args, **kwargs):
        calls.append(1)
        return original(*args, **kwargs)

    def crash(*args, **kwargs):
        raise SystemExit("simulated worker process termination")

    monkeypatch.setattr(graph, "invoke", spy)
    monkeypatch.setattr(production, "prepare", crash)
    client.post(
        "/api/v1/creators/" + creator_profile["id"] + "/run-today", headers={"Idempotency-Key": "media-crash"}
    )
    with pytest.raises(SystemExit), SessionLocal() as db:
        process_pending(db)
    with SessionLocal() as db:
        run = db.scalar(select(Run))
        assert run.status == "running" and run.stage == "asset_rendering"
        assert db.scalar(select(BudgetEntry)).status == "settled"
        run.lease_until = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
        db.commit()
    monkeypatch.setattr(production, "prepare", original_prepare)
    with SessionLocal() as db:
        process_pending(db)
        assert db.scalar(select(Run)).status == "completed"
        assert db.scalar(select(Content)).graphics_render
    assert len(calls) == 1
