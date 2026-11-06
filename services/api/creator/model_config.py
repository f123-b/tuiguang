"""Workspace secrets never enter response DTOs, diagnostics or project snapshots."""

import os
import ipaddress
from urllib.parse import urlsplit

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select, update

from .config import DATA_DIR, PRODUCTION
from .domains import digest
from .errors import DomainError
from .models import ModelConfig
from .observability import release_manifest


def cipher():
    key = os.getenv("MODEL_ENCRYPTION_KEY", "")
    try:
        if not key:
            if PRODUCTION:
                raise ValueError("production master missing")
            path = DATA_DIR / "model-encryption-key"
            if not path.exists():
                try:
                    with path.open("xb") as f:
                        f.write(Fernet.generate_key())
                    path.chmod(0o600)
                except FileExistsError:
                    pass
            key = path.read_bytes()
        return Fernet(key)
    except (ValueError, OSError, TypeError):
        raise DomainError(
            "MODEL_ENCRYPTION_UNAVAILABLE", "加密主密钥缺失或不可用；没有保存明文密钥", 503
        ) from None


def validate_base_url(value, approved=False):
    try:
        parts = urlsplit(value)
        hosts = {
            h.strip().lower()
            for h in os.getenv("MODEL_ALLOWED_HOSTS", "api.openai.com").split(",")
            if h.strip()
        }
        if (
            parts.scheme != "https"
            or not parts.hostname
            or (parts.hostname not in hosts and (not approved or PRODUCTION))
            or parts.username
            or parts.password
            or parts.port not in (None, 443)
            or parts.query
            or parts.fragment
        ):
            raise ValueError("url denied")
        host = parts.hostname.lower()
        if host == "localhost" or "." not in host or host.endswith((".local", ".internal", ".localhost")):
            raise ValueError("local endpoint denied")
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            address = None
        if address and not address.is_global:
            raise ValueError("private endpoint denied")
    except ValueError:
        raise DomainError(
            "MODEL_ENDPOINT_DENIED",
            "模型地址须为操作者允许主机的 HTTPS 地址，不接受账号、查询参数或重定向",
            422,
        ) from None
    return value.rstrip("/")


def config(db, workspace_id):
    return db.scalar(
        select(ModelConfig)
        .where(ModelConfig.workspace_id == workspace_id)
        .execution_options(populate_existing=True)
    )


def public_config(db, workspace_id):
    current = config(db, workspace_id)
    if current:
        return {
            "revision": current.revision,
            "mode": current.mode,
            "model_id": current.model_id,
            "model_revision": current.model_revision,
            "base_url": current.base_url,
            "input_price": current.input_price,
            "output_price": current.output_price,
            "max_tokens": current.max_tokens,
            "price_source": current.price_source,
            "key_configured": bool(current.encrypted_key),
            "endpoint_approved": current.endpoint_approved,
            "json_mode": current.json_mode,
            "token_parameter": current.token_parameter,
            "source": "workspace_encrypted",
        }

    def integer(name):
        try:
            return int(os.environ[name])
        except (KeyError, ValueError):
            return None

    return {
        "revision": 0,
        "mode": os.getenv("GENERATION_MODE", "template"),
        "model_id": os.getenv("MODEL_ID") or None,
        "model_revision": os.getenv("MODEL_REVISION") or None,
        "base_url": os.getenv("MODEL_BASE_URL", "https://api.openai.com/v1"),
        "input_price": integer("MODEL_INPUT_CENTS_PER_MILLION"),
        "output_price": integer("MODEL_OUTPUT_CENTS_PER_MILLION"),
        "max_tokens": integer("MODEL_MAX_OUTPUT_TOKENS") or 1800,
        "price_source": "服务端环境设置，价格来源仍需操作者核实",
        "key_configured": bool(os.getenv("MODEL_API_KEY")),
        "source": "server_environment",
        "endpoint_approved": False,
        "json_mode": True,
        "token_parameter": "max_tokens",
    }


def execution_config(db, workspace_id, expected_revision=None, allow_disabled=False):
    db.execute(
        update(ModelConfig)
        .where(ModelConfig.workspace_id == workspace_id)
        .values(revision=ModelConfig.revision)
    )
    current = config(db, workspace_id)
    if not current:
        return None
    if expected_revision != current.revision:
        raise DomainError("RUN_VERSION_UNSUPPORTED", "工作区模型配置已变化，未发起请求")
    if current.mode == "template" and not allow_disabled:
        return {"mode": "template"}
    try:
        key = cipher().decrypt((current.encrypted_key or "").encode()).decode()
    except (InvalidToken, UnicodeError):
        raise DomainError("MODEL_ENCRYPTION_UNAVAILABLE", "模型密钥无法解密，未发起模型请求", 503) from None
    validate_base_url(current.base_url, current.endpoint_approved)
    return {
        "mode": "openai",
        "key": key,
        "model": current.model_id,
        "base_url": current.base_url,
        "input_price": current.input_price,
        "output_price": current.output_price,
        "max_tokens": current.max_tokens,
        "json_mode": current.json_mode,
        "token_parameter": current.token_parameter,
    }


def workspace_release(db, workspace_id):
    manifest = release_manifest()
    public = public_config(db, workspace_id)
    manifest.update(
        generation_mode=public["mode"],
        model_id=public["model_id"] if public["mode"] == "openai" else None,
        model_revision=public["model_revision"] if public["mode"] == "openai" else None,
        workspace_model_revision=public["revision"] or None,
        model_config_hash=digest(public) if public["mode"] == "openai" else None,
    )
    return manifest
