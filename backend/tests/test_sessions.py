from app.redis_client import get_redis
from app.sessions import create_session, delete_session, get_session_user_id


def test_create_then_resolve_session():
    token = create_session(42)
    assert isinstance(token, str) and token
    assert get_session_user_id(token) == 42
    delete_session(token)


def test_unknown_token_returns_none():
    assert get_session_user_id("does-not-exist") is None


def test_delete_removes_session():
    token = create_session(7)
    delete_session(token)
    assert get_session_user_id(token) is None


def test_tokens_are_unique_per_call():
    t1 = create_session(1)
    t2 = create_session(1)
    assert t1 != t2
    delete_session(t1)
    delete_session(t2)


def test_session_has_ttl():
    token = create_session(99)
    ttl = get_redis().ttl("session:" + token)
    assert ttl > 0
    delete_session(token)
