import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]
load_dotenv(ROOT / ".env")
DATA_DIR = Path(os.getenv("DATA_DIR", str(ROOT / ".data"))).resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///" + str(DATA_DIR / "creator.db"))
PRODUCTION = os.getenv("APP_ENV") == "production"
WEB_ORIGIN = os.getenv("WEB_ORIGIN", "http://localhost:3000").rstrip("/")
SECRET = os.getenv("JWT_SECRET", "")
if not SECRET and not PRODUCTION:
    import secrets

    path = DATA_DIR / "jwt-secret"
    if not path.exists():
        try:
            with path.open("x") as f:
                f.write(secrets.token_hex(32))
            path.chmod(0o600)
        except FileExistsError:
            pass
    SECRET = path.read_text().strip()
if len(SECRET) < 32:
    raise RuntimeError("JWT_SECRET must have at least 32 characters")
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
if PRODUCTION and (not COOKIE_SECURE or DATABASE_URL.startswith("sqlite")):
    raise RuntimeError("Production requires secure cookies and PostgreSQL")
