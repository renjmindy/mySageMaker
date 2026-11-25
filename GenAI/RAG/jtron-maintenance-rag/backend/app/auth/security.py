from datetime import datetime, timedelta, timezone
from uuid import UUID

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from passlib.context import CryptContext

from app.config import get_settings

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
_settings = get_settings()
_serializer = URLSafeTimedSerializer(_settings.secret_key, salt="jtron-session")

COOKIE_NAME = "jtron_session"


def hash_password(password: str) -> str:
    return _pwd.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _pwd.verify(password, password_hash)


def issue_session_token(user_id: UUID) -> str:
    payload = {"uid": str(user_id), "iat": datetime.now(timezone.utc).isoformat()}
    return _serializer.dumps(payload)


def read_session_token(token: str) -> UUID | None:
    try:
        payload = _serializer.loads(token, max_age=_settings.session_ttl_seconds)
    except (BadSignature, SignatureExpired):
        return None
    try:
        return UUID(payload["uid"])
    except (KeyError, ValueError, TypeError):
        return None


def cookie_params() -> dict:
    return {
        "key": COOKIE_NAME,
        "httponly": True,
        "secure": _settings.cookie_secure,
        "samesite": _settings.cookie_samesite,
        "max_age": _settings.session_ttl_seconds,
        "path": "/",
    }


def expired_delta() -> timedelta:
    return timedelta(seconds=_settings.session_ttl_seconds)
