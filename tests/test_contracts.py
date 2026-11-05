import json
from pathlib import Path

from jsonschema import validate

from creator.main import app
from creator.observability import release_manifest
from creator.schemas import VideoInput
from test_workflow import run_content


def test_runtime_receipts_validate_actual_events(client, creator_profile):
    run_content(client, creator_profile)
    run = client.get("/api/v1/creator-runs").json()[0]
    diagnostic = client.get(f"/api/v1/creator-runs/{run['id']}/diagnostic").json()
    schema = json.loads(Path("engineering/contracts/runtime_receipt.schema.json").read_text(encoding="utf-8"))
    assert len(diagnostic["receipts"]) >= 3
    for receipt in diagnostic["receipts"]:
        validate(receipt, schema)
    assert diagnostic["run"]["release"]["agent_graph_version"] == "creator_graph@1"


def test_openapi_and_ir_schema_are_generated_from_implementation():
    spec = app.openapi()
    assert "/api/v1/manual-publication/records" in spec["paths"]
    assert "/api/v1/creators/{creator_id}/run-today" in spec["paths"]
    assert "Idempotency-Key" in str(spec["paths"]["/api/v1/creators/{creator_id}/run-today"])
    assert "Shot" in VideoInput.model_json_schema()["$defs"]
    manifest = release_manifest()
    assert len(manifest["git_sha"]) == 40
    assert manifest["stable"] is False


def test_error_catalog_covers_key_domain_failures():
    catalog = json.loads(Path("packages/schemas/error-codes.json").read_text(encoding="utf-8"))["codes"]
    assert {
        "AUTH_REQUIRED",
        "QA_CONTENT_BLOCKED",
        "BUDGET_LIMIT_REACHED",
        "AGENT_PROVIDER_RESULT_UNKNOWN",
        "AGENT_MODEL_UNCONFIGURED",
        "RUN_VERSION_UNSUPPORTED",
    } <= set(catalog)
