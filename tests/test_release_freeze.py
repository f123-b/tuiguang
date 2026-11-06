import json
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

from creator.main import app


def test_application_packages_api_and_migration_share_release_freeze():
    manifest = json.loads(Path("release_manifest.json").read_text(encoding="utf-8"))
    for path in ("package.json", "apps/web/package.json", "packages/ui/package.json"):
        assert (
            json.loads(Path(path).read_text(encoding="utf-8"))["version"] == manifest["application_version"]
        ), path
    assert app.version == manifest["application_version"]
    assert (
        ScriptDirectory.from_config(Config("alembic.ini")).get_current_head()
        == manifest["database_migration"]
    )
