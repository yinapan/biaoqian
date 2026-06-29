from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.models.database import get_pool
from app.services.es_sync_service import get_es

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/ready")
async def ready_check(request: Request):
    if not getattr(request.app.state, "ready", False):
        return JSONResponse(status_code=503, content={"status": "starting"})
    return {"status": "ready"}


@router.get("/health")
async def health_check():
    pg_ok = False
    es_ok = False

    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        pg_ok = True
    except Exception:
        pass

    try:
        es = await get_es()
        es_ok = await es.ping()
    except Exception:
        pass

    status = "ok" if (pg_ok and es_ok) else "error"
    code = 200 if status == "ok" else 503
    return JSONResponse(
        status_code=code,
        content={"status": status, "pg": pg_ok, "es": es_ok},
    )
