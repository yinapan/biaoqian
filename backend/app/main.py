from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.models.database import close_pool, get_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await get_pool()
    except Exception:
        pass  # Pool init fails in test env without PG
    yield
    await close_pool()


app = FastAPI(title="美术标签搜索平台", lifespan=lifespan)


@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}
