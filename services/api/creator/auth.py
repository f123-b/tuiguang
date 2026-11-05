import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import SECRET
from .db import get_db
from .errors import DomainError
from .models import LoginSession, User, uid


def password_hash(password):
    salt = secrets.token_bytes(16)
    result = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1)
    return salt.hex() + ":" + result.hex()


def verify_password(password, stored):
    salt, expected = stored.split(":")
    result = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1)
    return hmac.compare_digest(result.hex(), expected)


def issue_token(db, user):
    sid = uid()
    expires = datetime.now(timezone.utc) + timedelta(hours=12)
    db.add(LoginSession(id=sid, user_id=user.id, expires_at=expires.isoformat()))
    db.commit()
    return jwt.encode(
        {"sub": user.id, "sid": sid, "exp": expires, "iat": datetime.now(timezone.utc)},
        SECRET,
        algorithm="HS256",
    )


def current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("creator_session", "")
    try:
        data = jwt.decode(token, SECRET, algorithms=["HS256"], options={"require": ["exp", "sub", "sid"]})
        session = db.scalar(
            select(LoginSession).where(LoginSession.id == data["sid"], LoginSession.user_id == data["sub"])
        )
        user = db.get(User, data["sub"])
        if not session or not user:
            raise ValueError("session revoked")
        request.state.session_id = data["sid"]
        return user
    except (jwt.InvalidTokenError, ValueError, KeyError):
        raise DomainError("AUTH_REQUIRED", "请登录后继续", 401) from None
