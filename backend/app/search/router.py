from fastapi import APIRouter, Query

from app.search.constants import ALL_TYPES
from app.search.dependencies import SearchServiceDep
from app.search.schemas import SearchResponse

router = APIRouter(prefix="/search", tags=["Search"])


@router.get(
    path="",
    response_model=SearchResponse,
    summary="Global search",
    description="Search across meetings, people, and transcript utterances using Postgres full-text search.",
)
async def search(
    service: SearchServiceDep,
    q: str = Query(min_length=1),
    limit: int = Query(default=8, ge=1, le=20, description="Max results per entity type"),
    types: str | None = Query(default=None, description="Comma-separated filter: meetings,people,utterances"),
) -> SearchResponse:
    if types:
        requested = {t.strip() for t in types.split(",")} & ALL_TYPES
    else:
        requested = set(ALL_TYPES)
    return await service.search(query=q, limit=limit, types=requested)
