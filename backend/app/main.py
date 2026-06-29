import logging
import time
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.importers.animator_importer import ensure_animator_tag_definitions
from app.models.database import close_pool, get_pool
from app.importers.tag_initializer import sync_all_tag_values
from app.routers import admin, assets, filter, health, search
from app.services.es_mapping import build_index_settings_and_mappings
from app.services.es_sync_service import close_es, get_es
from app.services.parse_service import init_matcher

logger = logging.getLogger(__name__)


async def refresh_runtime_dictionary(pool):
    try:
        await ensure_animator_tag_definitions(pool)
        await sync_all_tag_values(pool)
        await init_matcher(pool)
        logger.info("Dictionary matcher initialized")
    except Exception:
        logger.exception("Failed to refresh dictionary matcher")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.ready = False
    if not settings.admin_api_key or settings.admin_api_key == "dev-admin-key-change-in-prod":
        logger.warning(
            "ADMIN_API_KEY is using default value! "
            "Set a secure key in .env for shared deployments."
        )
    try:
        pool = await get_pool()
        logger.info("Database pool initialized")
    except Exception:
        logger.error("Failed to connect to database", exc_info=True)
        yield
        return
    try:
        es = await get_es()
        if not await es.indices.exists_alias(name="assets"):
            all_defs = []
            async with pool.acquire() as conn:
                modules = await conn.fetch(
                    "SELECT DISTINCT module_type FROM tag_definitions ORDER BY module_type"
                )
                for row in modules:
                    defs = await conn.fetch(
                        "SELECT field_name, field_type FROM tag_definitions"
                        " WHERE module_type=$1",
                        row["module_type"],
                    )
                    all_defs.extend([dict(d) for d in defs])
            body = build_index_settings_and_mappings(all_defs)
            idx_name = f"assets_v{int(time.time())}"
            await es.indices.create(index=idx_name, body=body)
            await es.indices.put_alias(index=idx_name, name="assets")
        logger.info("Elasticsearch ready")
        app.state.dictionary_refresh_task = asyncio.create_task(
            refresh_runtime_dictionary(pool)
        )
        app.state.ready = True
    except Exception:
        logger.exception("Failed to initialize ES/dictionary matcher — search may not work")
    yield
    task = getattr(app.state, "dictionary_refresh_task", None)
    if task and not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    await close_pool()
    await close_es()


app = FastAPI(title="美术资产检索工作台", lifespan=lifespan)
app.include_router(search.router)
app.include_router(filter.router)
app.include_router(assets.router)
app.include_router(admin.router)
app.include_router(health.router)
