"""Record installed distribution metadata, exact versions and notice hashes (not a legal opinion)."""

import hashlib
import importlib.metadata as metadata
import json
from pathlib import Path

python = []
for distribution in sorted(metadata.distributions(), key=lambda d: d.metadata["Name"].lower()):
    info = distribution.metadata
    notices = []
    for file in distribution.files or []:
        if ".dist-info/" in str(file).replace("\\", "/") and any(
            x in str(file).lower() for x in ("license", "notice", "copying")
        ):
            path = distribution.locate_file(file)
            if path.is_file():
                notices.append(
                    {
                        "file": str(file).replace("\\", "/"),
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    }
                )
    python.append(
        {
            "name": info["Name"],
            "version": distribution.version,
            "license_expression": info.get("License-Expression") or info.get("License") or "unknown",
            "project_urls": info.get_all("Project-URL", []),
            "notice_files": notices,
        }
    )

lock = json.loads(Path("package-lock.json").read_text(encoding="utf-8"))
npm = [
    {
        "path": name,
        "version": info.get("version"),
        "license": info.get("license", "unknown"),
        "integrity": info.get("integrity"),
        "dev": info.get("dev", False),
    }
    for name, info in lock["packages"].items()
    if name.startswith("node_modules/")
]
Path("docs/evidence/dependency-inventory.json").write_text(
    json.dumps(
        {
            "source": "local installed wheel METADATA and npm package-lock; inspect upstream notices before redistribution",
            "python": python,
            "npm": npm,
        },
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)
print(f"Recorded {len(python)} Python distributions and {len(npm)} npm packages")
