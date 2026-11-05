import json
from pathlib import Path

from creator.main import app
from creator.schemas import VideoInput

directory = Path("packages/schemas")
directory.mkdir(parents=True, exist_ok=True)
for name, content in {
    "openapi.json": app.openapi(),
    "video-project-input.schema.json": VideoInput.model_json_schema(),
}.items():
    (directory / name).write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")
print("Exported OpenAPI and VideoProject input JSON Schema from actual code")
