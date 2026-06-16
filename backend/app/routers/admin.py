import os
import tempfile

from fastapi import APIRouter, File, Header, HTTPException, UploadFile

from app.config import settings
from app.importers.effects_importer import import_effects_json
from app.importers.excel_importer import import_excel
from app.models.database import get_pool
from app.services.cache import clear_all_caches
from app.services.es_mapping import build_index_settings_and_mappings
from app.services.es_sync_service import check_sync, reindex_with_alias
from app.services.parse_service import init_matcher
from app.services.search_service import get_tag_definitions

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def verify_admin(x_admin_key: str = Header(...)):
    if x_admin_key != settings.admin_api_key:
        raise HTTPException(status_code=403, detail="Invalid admin key")


@router.post("/reindex-es")
async def reindex_es(x_admin_key: str = Header(...)):
    verify_admin(x_admin_key)
    pool = await get_pool()
    all_defs = []
    for mod in [1, 2, 3]:
        defs = await get_tag_definitions(pool, mod)
        all_defs.extend(defs)
    index_body = build_index_settings_and_mappings(all_defs)
    result = await reindex_with_alias(pool, index_body)
    return result


@router.get("/check-sync")
async def admin_check_sync(x_admin_key: str = Header(...)):
    verify_admin(x_admin_key)
    pool = await get_pool()
    return await check_sync(pool)


@router.post("/refresh-dictionary")
async def refresh_dictionary(x_admin_key: str = Header(...)):
    verify_admin(x_admin_key)
    pool = await get_pool()
    await init_matcher(pool)
    clear_all_caches()
    return {"status": "refreshed"}


@router.post("/import-excel")
async def admin_import_excel(
    file: UploadFile = File(...),
    x_admin_key: str = Header(...),
):
    verify_admin(x_admin_key)
    pool = await get_pool()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    try:
        result = await import_excel(tmp_path, pool, "/data/previews")
        await init_matcher(pool)
        return result
    finally:
        os.unlink(tmp_path)


@router.post("/import-effects-json")
async def admin_import_effects_json(
    file: UploadFile = File(...),
    x_admin_key: str = Header(...),
):
    verify_admin(x_admin_key)
    pool = await get_pool()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    try:
        result = await import_effects_json(
            tmp_path, "/data/gifs", pool, "/data/previews"
        )
        await init_matcher(pool)
        return result
    finally:
        os.unlink(tmp_path)
