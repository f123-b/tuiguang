import json
import ast
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
codes = {}
for source in Path("services/api/creator").glob("*.py"):
    tree = ast.parse(source.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in {"DomainError", "error_response"}
        ):
            if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                code = node.args[0].value
                codes[code] = {"module": source.stem}
codes["RUN_VERSION_UNSUPPORTED"] = {"module": "jobs"}
(directory / "error-codes.json").write_text(
    json.dumps({"schema_version": "1.0", "codes": dict(sorted(codes.items()))}, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
print("Exported OpenAPI and VideoProject input JSON Schema from actual code")
