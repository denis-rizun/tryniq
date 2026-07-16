from functools import lru_cache

import structlog

from app.config import config
from app.core.client import get_ai_client
from app.core.constants import GRAPH_EXTRACTION_SYSTEM_PROMPT, AIRequestKind, StructuredRequest
from app.core.exceptions import AIValidationError
from app.graph.constants import GRAPH_OPS_JSON_SCHEMA
from app.graph.exceptions import InvalidGraphOperationError
from app.graph.schemas import GraphOperation, GraphOperationsResponse

logger = structlog.get_logger()


class GraphExtractor:
    async def extract(self, window_text: str) -> list[GraphOperation]:
        ai_client = get_ai_client()
        request = StructuredRequest(
            kind=AIRequestKind.GRAPH_OPS,
            system=GRAPH_EXTRACTION_SYSTEM_PROMPT,
            user=window_text,
            schema=GRAPH_OPS_JSON_SCHEMA,
            dto=GraphOperationsResponse,
            model=config.graph.LLM_MODEL,
            max_tokens=config.graph.LLM_MAX_TOKENS,
        )
        try:
            response: GraphOperationsResponse = await ai_client.complete_structured(request)
        except AIValidationError as e:
            logger.warning("graph extractor: invalid AI output", error=str(e))
            raise InvalidGraphOperationError() from e
        return response.ops


@lru_cache(maxsize=1)
def get_extractor() -> GraphExtractor:
    return GraphExtractor()
