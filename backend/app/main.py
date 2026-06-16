import time
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.models.database import close_pool, get_pool
from app.routers import admin, assets, filter, search
from app.services.es_mapping import build_index_settings_and_mappings
from app.services.es_sync_service import close_es, get_es
from app.services.parse_service import init_matcher


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        pool = await get_pool()
    except Exception:
        yield
        return
    try:
        es = await get_es()
        if not await es.indices.exists_alias(name="assets"):
            all_defs = []
            for mod in [1, 2, 3]:
                async with pool.acquire() as conn:
                    defs = await conn.fetch(
                        "SELECT field_name, field_type FROM tag_definitions"
                        " WHERE module_type=$1",
                        mod,
                    )
                all_defs.extend([dict(d) for d in defs])
            body = build_index_settings_and_mappings(all_defs)
            idx_name = f"assets_v{int(time.time())}"
            await es.indices.create(index=idx_name, body=body)
            await es.indices.put_alias(index=idx_name, name="assets")
        await init_matcher(pool)
    except Exception:
        pass
    yield
    await close_pool()
    await close_es()


app = FastAPI(title="美术标签搜索平台", lifespan=lifespan)
app.include_router(search.router)
app.include_router(filter.router)
app.include_router(assets.router)
app.include_router(admin.router)


@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}
