from typing import Annotated

from fastapi import Depends

from app.db import SessionDep
from app.search.service import SearchService


def get_search_service(session: SessionDep) -> SearchService:
    return SearchService(session)


SearchServiceDep = Annotated[SearchService, Depends(get_search_service)]
