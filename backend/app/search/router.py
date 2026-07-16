from typing import Annotated

from fastapi import APIRouter, Query, status

from app.search.dependencies import SearchServiceDep
from app.search.schemas import SearchResponse

router = APIRouter(prefix="/search", tags=["Search"])


@router.get(
    path="",
    response_model=SearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Global search",
    description="Search across meetings, people, and transcript utterances using Postgres full-text search.",
)
async def search(
    service: SearchServiceDep,
    query: Annotated[str, Query(min_length=1)],
    limit: int = Query(default=8, ge=1, le=20, description="Max results per entity type"),
    types: str | None = Query(default=None, description="Comma-separated filter: meetings,people,utterances"),
) -> SearchResponse:
    return await service.search(query=query, limit=limit, types=types)
