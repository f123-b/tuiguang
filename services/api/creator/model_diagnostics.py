"""Explicit, revision-bound connectivity and fixed-input generation checks."""

import json
import math
from typing import Annotated, Literal

import httpx
from fastapi import APIRouter, Depends, Header, Request, Response
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from .agent import model_settings
from .auth import current_user
from .db import get_db
from .domains import digest, owned, serialize
from .editorial import local_today, lock_creator
from .errors import DomainError
from .model_config import execution_config, public_config, workspace_release
from .model_gateway import complete, cost
from .models import Creator, ModelCheck, Run, User, uid
from .observability import record
from .schemas import DTO

router = APIRouter(prefix="/api/v1/settings/models")
DB = Annotated[Session, Depends(get_db)]
Actor = Annotated[User, Depends(current_user)]
PROMPTS = [{"role": "user", "content": '连接测试。只回复 JSON：{"connection":"ok"}。不要执行工具。'}]


def admin(user):
    if user.role not in ("owner", "admin"):
        raise DomainError("AUTH_FORBIDDEN", "仅工作区管理员可以检查模型配置", 403)


class CheckInput(DTO):
    expected_revision: int = Field(ge=0)
    confirmed: Literal[True]


class ProbeInput(CheckInput):
    creator_id: str = Field(min_length=1, max_length=120)
    max_cost_cents: int = Field(ge=1, le=10000)


def settings_for(db, workspace_id, revision, require_enabled=True):
    current = public_config(db, workspace_id)
    if revision != current["revision"]:
        raise DomainError("MODEL_REVISION_CONFLICT", "模型设置已变化，请刷新")
    if require_enabled and current["mode"] != "openai":
        raise DomainError("AGENT_MODEL_UNCONFIGURED", "请先保存并启用模型配置", 422)
    return model_settings(
        {"model_config": execution_config(db, workspace_id, revision, allow_disabled=not require_enabled)}
    )


@router.post("/check", status_code=201)
def check_list(data: CheckInput, db: DB, user: Actor, request: Request):
    admin(user)
    settings = settings_for(db, user.workspace_id, data.expected_revision, require_enabled=False)
    check = ModelCheck(
        workspace_id=user.workspace_id, config_revision=data.expected_revision, kind="models_list"
    )
    db.add(check)
    db.commit()
    try:
        with httpx.Client(timeout=20, follow_redirects=False) as client:
            response = client.get(
                settings["base_url"] + "/models", headers={"Authorization": "Bearer " + settings["key"]}
            )
        response.raise_for_status()
        if len(response.content) > 1024 * 1024:
            raise ValueError("large response")
        raw = response.json()["data"]
        if not isinstance(raw, list) or len(raw) > 1000:
            raise ValueError("model list")
        names = sorted(
            {
                item["id"]
                for item in raw
                if isinstance(item, dict) and isinstance(item.get("id"), str) and 0 < len(item["id"]) <= 120
            }
        )
        if settings["key"] in json.dumps(names):
            raise ValueError("credential echo")
        check.status, check.result = "completed", {"models": names, "generation_sent": False}
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as error:
        code = "MODEL_CONNECTION_FAILED"
        if isinstance(error, httpx.HTTPStatusError):
            code = {
                401: "MODEL_KEY_REJECTED",
                403: "MODEL_ACCESS_DENIED",
                404: "MODEL_LIST_UNSUPPORTED",
                429: "MODEL_RATE_LIMITED",
            }.get(error.response.status_code, code)
        check.status, check.result = "failed", {"error_code": code, "generation_sent": False}
    record(
        db,
        user.workspace_id,
        request.state.trace_id,
        "model.connection",
        check.status,
        revision=data.expected_revision,
    )
    db.commit()
    return serialize(check)


@router.get("/checks")
def checks(db: DB, user: Actor):
    admin(user)
    result = []
    for check in db.scalars(
        select(ModelCheck)
        .where(ModelCheck.workspace_id == user.workspace_id)
        .order_by(ModelCheck.created_at.desc())
        .limit(30)
    ):
        row = serialize(check)
        run = db.get(Run, check.run_id) if check.run_id else None
        if run and run.status in ("failed", "blocked"):
            row["status"], row["result"] = run.status, {**row["result"], "error_code": run.error_code}
        result.append(row)
    return result


@router.post("/probe")
def enqueue_probe(
    data: ProbeInput,
    db: DB,
    user: Actor,
    request: Request,
    response: Response,
    idempotency_key: str = Header(min_length=1, max_length=160),
):
    admin(user)
    creator = owned(db, Creator, data.creator_id, user.workspace_id)
    lock_creator(db, creator)
    if creator.status != "active" or not creator.model_consent:
        raise DomainError("MODEL_CONSENT_REQUIRED", "请先在创作者中启用模型授权并恢复运行；没有发起请求")
    settings_for(db, user.workspace_id, data.expected_revision)
    frozen = {
        "config_revision": data.expected_revision,
        "max_cost_cents": data.max_cost_cents,
        "probe": "fixed_json@1",
    }
    existing = db.scalar(
        select(Run).where(Run.workspace_id == user.workspace_id, Run.idempotency_key == idempotency_key)
    )
    if existing:
        if (
            existing.release.get("job_kind") != "model_probe"
            or existing.input_snapshot != frozen
            or existing.creator_id != creator.id
        ):
            raise DomainError("IDEMPOTENCY_KEY_CONFLICT", "请求编号已用于其他任务")
        response.status_code = 200
        return serialize(db.scalar(select(ModelCheck).where(ModelCheck.run_id == existing.id)))
    release = workspace_release(db, user.workspace_id)
    release.update(job_kind="model_probe", diagnostic_version="fixed_json@1", model_probe_consent=True)
    run = Run(
        workspace_id=user.workspace_id,
        creator_id=creator.id,
        operational_date=local_today(creator).isoformat(),
        slot="probe-" + uid()[:24],
        idempotency_key=idempotency_key,
        release=release,
        input_snapshot=frozen,
        trace_id=request.state.trace_id,
        stage="model.probe.queued",
    )
    db.add(run)
    db.flush()
    check = ModelCheck(
        workspace_id=user.workspace_id,
        config_revision=data.expected_revision,
        kind="generation",
        run_id=run.id,
    )
    db.add(check)
    db.commit()
    response.status_code = 201
    return serialize(check)


def process_probe(db, run, creator):
    from .jobs import reserve_budget

    check = db.scalar(select(ModelCheck).where(ModelCheck.run_id == run.id))
    if not check or not run.release.get("model_probe_consent") or not creator.model_consent:
        raise DomainError("MODEL_CONSENT_REQUIRED", "联调授权已撤销，未发起请求")
    if check.status == "completed":
        run.status = "completed"
        db.commit()
        return
    settings = settings_for(db, run.workspace_id, check.config_revision)
    cap = min(settings["max_tokens"], 512)
    size = sum(len(m["content"].encode()) + 64 for m in PROMPTS)
    reservation = max(
        1, math.ceil((size * settings["input_price"] + cap * settings["output_price"]) / 1_000_000)
    )
    if reservation > run.input_snapshot["max_cost_cents"]:
        raise DomainError("MODEL_PROBE_BUDGET_EXCEEDED", "预估费用超过本次确认上限，未发起请求")
    ledger = reserve_budget(db, creator, run, reservation)
    db.refresh(creator)
    live = workspace_release(db, run.workspace_id)
    if (
        not creator.model_consent
        or creator.status != "active"
        or live.get("model_config_hash") != run.release.get("model_config_hash")
    ):
        ledger.status, ledger.actual_cents = "cancelled", 0
        db.commit()
        raise DomainError("MODEL_CONSENT_REQUIRED", "授权、暂停状态或模型配置已变化，已释放预留且未发起请求")
    run.stage = "model.probe"
    db.commit()
    result = complete(settings, PROMPTS, cap)
    try:
        body = json.loads(result["choices"][0]["message"]["content"])
        if body != {"connection": "ok"}:
            raise ValueError("unexpected fixed JSON")
    except (ValueError, KeyError, TypeError):
        raise DomainError("AGENT_PROVIDER_RESULT_UNKNOWN", "联调格式或费用待核对，未重试请求") from None
    actual = cost(settings, result["usage"])
    check.status, check.result = (
        "completed",
        {
            "connection": "ok",
            "actual_cents": actual,
            "usage": {k: result["usage"][k] for k in ("prompt_tokens", "completion_tokens")},
            "input_digest": digest(PROMPTS),
            "private_brand_data_sent": False,
        },
    )
    ledger.status, ledger.actual_cents = "settled", actual
    run.status, run.stage = "completed", "model.probe.ready"
    record(
        db,
        run.workspace_id,
        run.trace_id,
        "model.probe",
        "ok",
        run.id,
        actual_cents=actual,
        revision=check.config_revision,
    )
    db.commit()
