from fastapi import APIRouter

from app.models.database import get_pool
from app.models.schemas import SearchRequest, SearchResponse, SuggestionsResponse
from app.services.parse_service import get_matcher
from app.services.search_service import search

router = APIRouter(prefix="/api/v1/search", tags=["search"])


@router.post("/query", response_model=SearchResponse)
async def search_query(req: SearchRequest):
    pool = await get_pool()
    return await search(req, pool)


@router.get("/suggestions", response_model=SuggestionsResponse)
async def suggestions(module_type: int, q: str = ""):
    matcher = get_matcher()
    if not q:
        return SuggestionsResponse(suggestions=[])
    items = matcher.prefix_search(module_type, q, limit=10)
    return SuggestionsResponse(
        suggestions=[
            {"text": i["text"], "field": i["field"], "type": "tag"} for i in items
        ]
    )
