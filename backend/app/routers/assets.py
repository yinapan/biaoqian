from fastapi import APIRouter, HTTPException

from app.models.database import get_pool

router = APIRouter(prefix="/api/v1/assets", tags=["assets"])


@router.get("/{asset_id}")
async def get_asset(asset_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM assets WHERE id = $1", asset_id)
    if not row:
        raise HTTPException(status_code=404, detail="Asset not found")
    return dict(row)
