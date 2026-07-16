from typing import Annotated

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db import SessionDep
from app.graph.services.graph import GraphService


def get_graph_service(session: SessionDep) -> GraphService:
    return GraphService(session)


def build_graph_service(session: AsyncSession) -> GraphService:
    return GraphService(session)


GraphServiceDep = Annotated[GraphService, Depends(get_graph_service)]
