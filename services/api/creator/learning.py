"""Deterministic evidence reports. Never infer causal platform preferences."""

from collections import Counter
from datetime import timedelta
from statistics import mean

from sqlalchemy import func, select

from .domains import digest, serialize
from .editorial import local_today, lock_creator
from .models import Content, ContentRevision, Creator, Feedback, LearningReport, Metric, Strategy


def strategy_snapshot(db, creator):
    current = db.get(Strategy, creator.active_strategy_id) if creator.active_strategy_id else None
    if current and current.creator_id == creator.id and current.status == "accepted":
        return {"strategy_id": current.id, "report_id": current.report_id, "settings": current.settings}
    return None


def build_report(db, creator, start, end):
    lock_creator(db, creator)
    content_ids = select(Content.id).where(Content.creator_id == creator.id)
    metrics = db.scalars(
        select(Metric).where(
            Metric.content_id.in_(content_ids),
            Metric.active.is_(True),
            Metric.period_start >= start,
            Metric.period_end <= end,
        )
    ).all()
    feedback = db.scalars(
        select(Feedback).where(
            Feedback.content_id.in_(content_ids),
            Feedback.active.is_(True),
            Feedback.created_at >= start,
            Feedback.created_at < end + "T99",
        )
    ).all()
    edits = db.scalars(
        select(ContentRevision).where(
            ContentRevision.content_id.in_(content_ids),
            ContentRevision.created_at >= start,
            ContentRevision.created_at < end + "T99",
            ContentRevision.reason_tag.not_in(
                ["edit", "restore", "graphics_edit", "brand_change", "asset_revoked", "video_attachment"]
            ),
        )
    ).all()
    fingerprint = digest(
        {
            "version": "evidence_review@1",
            "metrics": sorted((m.id, m.fingerprint) for m in metrics),
            "feedback": sorted(f.id for f in feedback),
            "edits": sorted(e.id for e in edits),
        }
    )
    existing = db.scalar(
        select(LearningReport).where(
            LearningReport.creator_id == creator.id,
            LearningReport.period_start == start,
            LearningReport.period_end == end,
            LearningReport.source_digest == fingerprint,
        )
    )
    if existing:
        return existing
    # Cumulative snapshots are not summed: retain latest observation per content/window/source.
    latest = {}
    for m in sorted(metrics, key=lambda m: (m.observed_at, m.created_at, m.id)):
        latest[(m.content_id, m.content_revision, m.platform, m.period_start, m.period_end, m.data_source)] = m
    groups = {}
    for key, m in latest.items():
        group = groups.setdefault(key[2:], [])
        group.append(m)
    summaries = []
    for key, rows in sorted(groups.items()):
        stats = {}
        for name in ("views", "likes", "saves", "clicks", "conversions"):
            values = [m.values[name] for m in rows if m.values.get(name) is not None]
            stats[name] = {
                "known_count": len(values),
                "missing_count": len(rows) - len(values),
                "min": min(values) if values else None,
                "max": max(values) if values else None,
                "mean": round(mean(values), 2) if values else None,
            }
        summaries.append(
            {
                "platform": key[0],
                "period_start": key[1],
                "period_end": key[2],
                "data_source": key[3],
                "sample_count": len(rows),
                "metrics": stats,
                "evidence_ids": [m.id for m in rows],
            }
        )
    reasons = Counter([f.reason_tag for f in feedback] + [e.reason_tag for e in edits])
    count = len({m.content_id for m in latest.values()})
    body = {
        "engine": "evidence_review@1",
        "generation_source": "deterministic_evidence_report",
        "metric_sample_count": count,
        "raw_snapshot_count": len(metrics),
        "feedback_count": len(feedback),
        "edit_count": len(edits),
        "groups": summaries,
        "metric_evidence": [serialize(m) for m in latest.values()],
        "feedback_evidence": [serialize(f) for f in feedback],
        "edit_evidence": [
            {"id": e.id, "content_id": e.content_id, "revision": e.revision, "reason_tag": e.reason_tag}
            for e in edits
        ],
        "reason_counts": dict(reasons),
        "confidence": "descriptive_only" if count >= 14 else "insufficient",
        "facts": [
            f"此窗口有 {count} 篇作品的可追溯指标、{len(feedback)} 条主动反馈和 {len(edits)} 次标注修改。"
        ],
        "unknowns": [
            "用户提供的指标未经平台核验；不同平台、窗口和来源分别统计。",
            "数据只支持描述性比较，不能证明因果、平台偏好或预测流量。",
            "缺失值保持未知；尚未接入真实模型生成的周报。",
        ],
        "next_experiments": ["保持统计窗口与来源一致，下一轮只改变一个表达因素，并继续收集用户反馈。"],
        "source_digest": fingerprint,
    }
    version = (
        db.scalar(
            select(func.max(LearningReport.version)).where(
                LearningReport.creator_id == creator.id,
                LearningReport.period_start == start,
                LearningReport.period_end == end,
            )
        )
        or 0
    ) + 1
    report = LearningReport(
        workspace_id=creator.workspace_id,
        creator_id=creator.id,
        period_start=start,
        period_end=end,
        source_digest=fingerprint,
        version=version,
        report=body,
    )
    db.add(report)
    db.flush()
    if count >= 14 or any(n >= 3 for n in reasons.values()):
        db.add(
            Strategy(
                workspace_id=creator.workspace_id,
                creator_id=creator.id,
                report_id=report.id,
                parent_id=creator.active_strategy_id,
                settings={
                    "tone": "restrained" if reasons["too_advertising"] >= 3 else "unchanged",
                    "concise": reasons["shorter"] >= 3,
                    "preferred_angles": ["使用前检查", "场景说明", "功能速览"],
                    "basis": {
                        "report_id": report.id,
                        "source_digest": fingerprint,
                        "reason_counts": dict(reasons),
                    },
                    "hypothesis_only": True,
                },
            )
        )
    db.flush()
    return report


def weekly_reviews(db, now=None):
    for creator in db.scalars(select(Creator).where(Creator.status == "active")).all():
        today = local_today(creator, now)
        start = today - timedelta(days=today.weekday() + 7)
        build_report(db, creator, start.isoformat(), (start + timedelta(days=6)).isoformat())
        db.commit()


def invalidate_evidence(db, workspace_id, kind, object_id):
    for strategy in db.scalars(
        select(Strategy).where(
            Strategy.workspace_id == workspace_id, Strategy.status.in_(["accepted", "proposed"])
        )
    ):
        report = db.get(LearningReport, strategy.report_id)
        rows = report.report.get("feedback_evidence" if kind == "feedback" else "metric_evidence", [])
        key = "id" if kind == "feedback" else "batch_id"
        if any(row.get(key) == object_id for row in rows):
            creator = db.get(Creator, strategy.creator_id)
            lock_creator(db, creator)
            if creator.active_strategy_id == strategy.id:
                creator.active_strategy_id = None
            strategy.status = "needs_review"
