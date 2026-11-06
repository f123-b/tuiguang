from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, Request, Response
from pydantic import Field
from sqlalchemy.orm import Session

from .auth import current_user
from .db import get_db
from .domains import owned, serialize
from .editorial import lock_creator
from .errors import DomainError
from .learning_api import Period
from .models import BudgetEntry, Creator, Run, User, now_iso
from .observability import record
from .schemas import DTO

router = APIRouter(prefix="/api/v1")
DB = Annotated[Session, Depends(get_db)]
Actor = Annotated[User, Depends(current_user)]


def cost_actor(user):
    if user.role not in ("owner", "admin"):
        raise DomainError("AUTH_FORBIDDEN", "仅工作区管理员可发起收费分析或核对费用", 403)


class Analyze(Period):
    confirmed: Literal[True]
    private_data_consent: Literal[True]


class Reconcile(DTO):
    confirmed: Literal[True]
    actual_cents: int = Field(ge=0, le=10000000)
    result: Literal["charged", "not_charged"]
    provider_receipt_source: str = Field(min_length=1, max_length=2000)


@router.post("/creators/{creator_id}/learning-reports/ai")
def create_review(
    creator_id: str,
    data: Analyze,
    db: DB,
    user: Actor,
    request: Request,
    response: Response,
    idempotency_key: str = Header(min_length=1, max_length=160),
):
    from .analysis_jobs import enqueue

    cost_actor(user)
    creator = owned(db, Creator, creator_id, user.workspace_id)
    if not 0 <= (data.period_end - data.period_start).days <= 31:
        raise DomainError("LEARNING_PERIOD_INVALID", "分析窗口需为 1–32 天", 422)
    run, created = enqueue(
        db,
        creator,
        data.period_start.isoformat(),
        data.period_end.isoformat(),
        idempotency_key,
        request.state.trace_id,
        user.id,
    )
    response.status_code = 201 if created else 200
    return serialize(run)


@router.post("/settings/billing/{ledger_id}/reconcile")
def reconcile(ledger_id: str, data: Reconcile, db: DB, user: Actor, request: Request):
    cost_actor(user)
    ledger = owned(db, BudgetEntry, ledger_id, user.workspace_id)
    creator = owned(db, Creator, ledger.creator_id, user.workspace_id)
    lock_creator(db, creator)
    db.refresh(ledger)
    run = owned(db, Run, ledger.run_id, user.workspace_id)
    if (
        ledger.status != "reserved"
        or run.status != "failed"
        or run.error_code != "AGENT_PROVIDER_RESULT_UNKNOWN"
    ):
        raise DomainError(
            "BUDGET_RECONCILIATION_DENIED", "只能核对明确停止且回执未知的模型请求；不修改运行中或已结算记录"
        )
    if data.result == "not_charged" and data.actual_cents != 0:
        raise DomainError("VALIDATION_ERROR", "未收费结果的实际金额须为 0", 422)
    ledger.reconciliation = {
        "source": "user_reported",
        "result": data.result,
        "provider_receipt_source": data.provider_receipt_source,
        "recorded_by": user.id,
        "recorded_at": now_iso(),
        "not_verified_by_provider": True,
    }
    ledger.actual_cents, ledger.status = data.actual_cents, "reconciled_user_reported"
    record(
        db,
        user.workspace_id,
        request.state.trace_id,
        "budget.user_reconcile",
        "ok",
        run.id,
        actual_cents=data.actual_cents,
        source="user_reported",
    )
    db.commit()
    return serialize(ledger)
