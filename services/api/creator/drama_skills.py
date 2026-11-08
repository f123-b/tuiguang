"""Audited, immutable application skills; never an arbitrary tool executor."""

import json
import subprocess

from .config import ROOT
from .domains import canonical, digest
from .errors import DomainError

VERSION = "drama_skills@1"


def registry():
    path = ROOT / "vendor/skills/registry.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    for name, expected in data["files"].items():
        source = (ROOT / name).resolve()
        if (
            not source.is_relative_to(ROOT / "vendor/skills")
            or not source.is_file()
            or digest(source.read_bytes()) != expected
        ):
            raise DomainError(
                "DRAMA_SKILL_CHANGED", "内置技能文件缺失或变化，请恢复固定版本；未运行模型或脚本", 409
            )
    return {
        "version": data["version"],
        "digest": digest(path.read_bytes()),
        "skills": [{**s, "integrity": "verified"} for s in data["skills"]],
    }


def prompt_references():
    data = registry()
    # Read only the audited production reference, not allowed-tools declarations.
    # Bounded excerpts are identified in the frozen prompt receipt.
    return [
        {
            "skill": s["id"],
            "commit": s["commit"],
            "reference": s["prompt_reference"],
            "excerpt": (ROOT / s["path"] / s["prompt_reference"]).read_text(encoding="utf-8")[:2300],
            "excerpt_limit_chars": 2300,
        }
        for s in data["skills"]
    ]


def validate_script(plan, target):
    registry()
    try:
        result = subprocess.run(
            ["node", str(ROOT / "scripts/drama-skill-check.mjs")],
            input=canonical({"plan": plan, "target": target}),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=15,
            cwd=ROOT,
        )
        if result.returncode:
            raise ValueError("validator failed")
        return json.loads(result.stdout)
    except (OSError, ValueError, subprocess.SubprocessError):
        raise DomainError("DRAMA_VALIDATOR_UNAVAILABLE", "本地剧本检查未能运行，未标记为通过", 503) from None
