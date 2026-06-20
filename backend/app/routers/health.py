from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from redis.asyncio import Redis

from backend.app import schemas
from backend.app.database import get_db, engine
from backend.app.config import settings
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, Counter, Histogram

router = APIRouter(tags=["health"])

REQUEST_COUNT = Counter("http_requests_total", "Total HTTP requests", ["method", "endpoint"])
REQUEST_LATENCY = Histogram("http_request_duration_seconds", "HTTP request latency")

redis_client = Redis.from_url(settings.redis_url, decode_responses=True)


@router.get("/health", response_model=schemas.HealthResponse)
async def health():
    return {"status": "ok"}


@router.get("/ready", response_model=schemas.ReadyResponse)
async def ready(db: AsyncSession = Depends(get_db)):
    checks = {}
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"

    try:
        await redis_client.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"

    status_ok = all(v == "ok" for v in checks.values())
    return {"status": "ok" if status_ok else "error", "checks": checks}


@router.get("/metrics")
async def metrics():
    from starlette.responses import Response
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
