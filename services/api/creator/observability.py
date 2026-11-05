import hashlib
import json
import subprocess
import os
from pathlib import Path

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

from .config import ROOT
from .models import Event

trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer("creator", "0.1.0")


def release_manifest():
    manifest = json.loads((ROOT / "release_manifest.json").read_text(encoding="utf-8"))
    try:
        manifest["git_sha"] = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, stderr=subprocess.DEVNULL, text=True, timeout=3
        ).strip()
    except (OSError, subprocess.SubprocessError):
        manifest["git_sha"] = "unknown"
    manifest["license_inventory_revision"] = (
        hashlib.sha256((ROOT / "LICENSE_INVENTORY.md").read_bytes()).hexdigest()
        if Path(ROOT / "LICENSE_INVENTORY.md").exists()
        else "pending"
    )
    manifest["generation_mode"] = os.getenv("GENERATION_MODE", "template")
    manifest["model_id"] = os.getenv("MODEL_ID") or None
    manifest["model_revision"] = os.getenv("MODEL_REVISION") or None
    return manifest


def trace_context(trace_id):
    import secrets

    return trace.set_span_in_context(
        trace.NonRecordingSpan(
            trace.SpanContext(
                trace_id=int(trace_id, 16),
                span_id=secrets.randbits(64) or 1,
                is_remote=True,
                trace_flags=trace.TraceFlags(1),
            )
        )
    )


def record(db, workspace_id, trace_id, stage, status, run_id=None, error_code=None, **safe_context):
    allowed = {
        "content_id",
        "video_project_id",
        "shot_id",
        "render_job_id",
        "provider",
        "sha256",
        "revision",
        "cached",
        "actual_cents",
        "source",
        "release_id",
        "count",
    }
    db.add(
        Event(
            workspace_id=workspace_id,
            trace_id=trace_id,
            run_id=run_id,
            stage=stage,
            status=status,
            error_code=error_code,
            context={k: v for k, v in safe_context.items() if k in allowed},
        )
    )
