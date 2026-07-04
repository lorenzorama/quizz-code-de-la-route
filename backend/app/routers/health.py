from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.db import engine
from app.redis_client import get_redis

router = APIRouter()


@router.get("/health")
def health() -> JSONResponse:
    db_ok = True
    redis_ok = True

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    try:
        get_redis().ping()
    except Exception:
        redis_ok = False

    payload = {
        "status": "ok" if db_ok and redis_ok else "degraded",
        "database": "ok" if db_ok else "error",
        "redis": "ok" if redis_ok else "error",
    }
    code = 200 if db_ok and redis_ok else 503
    return JSONResponse(payload, status_code=code)
