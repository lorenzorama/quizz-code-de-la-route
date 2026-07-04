import secrets

from app.config import settings
from app.redis_client import get_redis

_PREFIX = "session:"


def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    get_redis().set(_PREFIX + token, str(user_id), ex=settings.session_ttl_seconds)
    return token


def get_session_user_id(token: str) -> int | None:
    value = get_redis().get(_PREFIX + token)
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def delete_session(token: str) -> None:
    get_redis().delete(_PREFIX + token)
