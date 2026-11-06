import json

from creator import observability


def test_running_process_does_not_adopt_a_different_checkout_manifest(tmp_path, monkeypatch):
    before = observability.release_manifest()
    (tmp_path / "release_manifest.json").write_text(
        json.dumps({"application_version": "999.0.0", "release_id": "unrelated-checkout"}), encoding="utf-8"
    )
    monkeypatch.setattr(observability, "ROOT", tmp_path)
    after = observability.release_manifest()
    assert after["application_version"] == before["application_version"]
    assert after["git_sha"] == before["git_sha"]
