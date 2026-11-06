from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from .models import (
    HandoffOutcome,
    Handoff,
    Content,
    Creator,
    LearningReport,
    Notification,
    Preferences,
    Reminder,
    RenderJob,
    Run,
    User,
)


def add(db, workspace_id, key, kind, title, body, path):
    existing = db.scalar(
        select(Notification.id).where(
            Notification.workspace_id == workspace_id, Notification.dedupe_key == key
        )
    )
    if existing:
        return
    try:
        with db.begin_nested():
            db.add(
                Notification(
                    workspace_id=workspace_id,
                    dedupe_key=key,
                    kind=kind,
                    title=title,
                    body=body,
                    action_path=path,
                )
            )
            db.flush()
    except IntegrityError:
        pass


def sync(db, workspace_id=None, now=None):
    now = now or datetime.now(timezone.utc)
    spaces = [workspace_id] if workspace_id else list(db.scalars(select(User.workspace_id).distinct()))
    for space in spaces:
        pref = db.scalar(select(Preferences).where(Preferences.workspace_id == space))
        mode = pref.notification_mode if pref else "instant"
        if mode == "off":
            continue
        local = now.astimezone(ZoneInfo(pref.timezone if pref else "Asia/Shanghai"))
        candidates = []
        for c in db.scalars(
            select(Content).where(
                Content.workspace_id == space,
                Content.status.in_(["awaiting_user_review", "awaiting_manual_publication"]),
            )
        ):
            review = c.status == "awaiting_user_review"
            if not review:
                package_ids = select(Handoff.id).where(
                    Handoff.content_id == c.id, Handoff.content_revision == c.revision
                )
                stopped = db.scalar(
                    select(HandoffOutcome.id).where(
                        HandoffOutcome.package_id.in_(package_ids), HandoffOutcome.outcome != "pending"
                    )
                )
                if stopped:
                    continue
            candidates.append(
                (
                    f"content:{c.id}:{c.revision}:{c.status}",
                    "content_review" if review else "manual_publication",
                    "内容等待人工审核" if review else "资料等待你手动发布",
                    c.title,
                    f"/studio/article/{c.id}" if review else "/publish",
                )
            )
        for run in db.scalars(
            select(Run).where(Run.workspace_id == space, Run.status.in_(["failed", "blocked"]))
        ):
            candidates.append(
                (
                    f"run:{run.id}:{run.error_code}",
                    "job_error",
                    "创作任务需要处理",
                    run.error_code or "请查看诊断编号",
                    "/creator/activity",
                )
            )
        for job in db.scalars(
            select(RenderJob).where(RenderJob.workspace_id == space, RenderJob.status == "failed")
        ):
            candidates.append(
                (
                    f"render:{job.id}",
                    "job_error",
                    "视频渲染需要处理",
                    job.error_code or "请查看工程回执",
                    f"/studio/video/{job.video_id}",
                )
            )
        for creator in db.scalars(
            select(Creator).where(Creator.workspace_id == space, Creator.status == "paused_by_budget")
        ):
            candidates.append(
                (
                    f"budget:{creator.id}:{local.date()}",
                    "budget",
                    "预算不足，已暂停创作",
                    "请核对账本与预算；软件不会自行提额。",
                    "/settings",
                )
            )
        for report in db.scalars(select(LearningReport).where(LearningReport.workspace_id == space)):
            candidates.append(
                (
                    f"report:{report.id}",
                    "learning_report",
                    "新的证据复盘已保存",
                    f"{report.period_start} — {report.period_end}，规则证据报告。",
                    "/growth",
                )
            )
        for reminder in db.scalars(
            select(Reminder).where(
                Reminder.workspace_id == space,
                Reminder.state == "scheduled",
                Reminder.due_at <= now.isoformat(),
            )
        ):
            candidates.append(
                (
                    f"reminder:{reminder.id}",
                    "manual_reminder",
                    "你设置的手动发布提醒到期",
                    "请检查资料后，由本人到官方平台发布。",
                    f"/publish/package/{reminder.package_id}",
                )
            )
            if mode == "instant" or local.hour >= pref.digest_hour:
                reminder.state = "delivered"
        if mode == "daily":
            if local.hour >= pref.digest_hour and candidates:
                add(
                    db,
                    space,
                    f"digest:{local.date()}",
                    "daily_digest",
                    "今日创作待办汇总",
                    f"当前有 {len(candidates)} 项审核、交接或诊断待办；点击查看工作台。",
                    "/dashboard",
                )
        else:
            for item in candidates:
                add(db, space, *item)
    db.flush()
