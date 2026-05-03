from typing import Annotated

from fastapi import Depends

from app.db import SessionDep
from app.graph.service import GraphService


def get_graph_service(session: SessionDep) -> GraphService:
    return GraphService(session)


GraphServiceDep = Annotated[GraphService, Depends(get_graph_service)]
