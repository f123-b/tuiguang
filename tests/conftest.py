# ruff: noqa: E402
import os
import tempfile
from pathlib import Path

_temp = tempfile.TemporaryDirectory()
os.environ["DATA_DIR"] = _temp.name
os.environ["DATABASE_URL"] = os.getenv("TEST_DATABASE_URL") or "sqlite:///" + str(
    Path(_temp.name) / "test.db"
)
os.environ["JWT_SECRET"] = "test-only-secret-32-characters-or-more"
os.environ["GENERATION_MODE"] = "template"

import pytest
from fastapi.testclient import TestClient

from creator.main import app
from creator.db import Base, engine


@pytest.fixture
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with TestClient(app) as c:
        yield c
    engine.dispose()


@pytest.fixture
def user(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "test@example.org", "password": "TestPassword987!", "name": "测试工作区"},
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
def brand(client, user):
    response = client.post(
        "/api/v1/brands",
        json={
            "name": "事实测试软件",
            "description": "本地测试软件",
            "audience": "独立开发者",
            "website": "https://example.org",
            "facts": [
                {"claim": "支持本地文件整理", "source": "用户提供的 1.0 说明书", "verified": True},
                {"claim": "未上线功能", "source": "规划文档", "verified": False},
            ],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
def creator_profile(client, brand):
    r = client.post(
        "/api/v1/creators",
        json={
            "brand_id": brand["id"],
            "name": "测试创作者",
            "daily_budget_cents": 100,
            "monthly_budget_cents": 1000,
            "hour": 9,
            "timezone": "Asia/Shanghai",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture
def historical_learning_evidence():
    """Keep synthetic evidence inside the explicitly historical report period."""
    from sqlalchemy import event
    from creator.models import Content, ContentRevision, Feedback

    def timestamp(mapper, connection, target):
        if target.created_at is None:
            target.created_at = "2026-11-05T12:00:00+00:00"

    for model in (Content, ContentRevision, Feedback):
        event.listen(model, "before_insert", timestamp)
    try:
        yield
    finally:
        for model in (Content, ContentRevision, Feedback):
            event.remove(model, "before_insert", timestamp)
