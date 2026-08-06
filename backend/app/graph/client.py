from functools import lru_cache

import structlog

from app.config import config
from app.core.client import AIClient, get_ai_client
from app.core.constants import GRAPH_EXTRACTION_SYSTEM_PROMPT, AIRequestKind, StructuredRequest
from app.core.exceptions import AIValidationError
from app.core.prompts import GRAPH_PROMPT
from app.graph.constants import GRAPH_OPS_JSON_SCHEMA
from app.graph.exceptions import InvalidGraphOperationError
from app.graph.schemas import GraphOperation, GraphOperationsResponse

logger = structlog.get_logger()


class GraphExtractor:
    def __init__(self, ai_client: AIClient | None = None) -> None:
        self.ai_client = ai_client or get_ai_client()

    async def extract(self, window_text: str) -> list[GraphOperation]:
        request = StructuredRequest(
            kind=AIRequestKind.GRAPH_OPS,
            system=GRAPH_EXTRACTION_SYSTEM_PROMPT,
            user=window_text,
            schema=GRAPH_OPS_JSON_SCHEMA,
            dto=GraphOperationsResponse,
            model=config.graph.LLM_MODEL,
            max_tokens=config.graph.LLM_MAX_TOKENS,
            langfuse_kwargs={
                "name": "graph.extract.generation",
                "metadata": GRAPH_PROMPT.metadata(),
            },
        )
        with self.ai_client.langfuse.start_as_current_observation(
            name="graph.extract",
            as_type="span",
            input={"window": window_text},
            metadata={
                **GRAPH_PROMPT.metadata(),
                "environment": config.ENV,
                "model": config.graph.LLM_MODEL,
            },
        ) as observation:
            try:
                response: GraphOperationsResponse = await self.ai_client.complete_structured(request)
            except AIValidationError as e:
                observation.update(level="ERROR", status_message=str(e))
                logger.warning("graph extractor: invalid AI output", error=str(e))
                raise InvalidGraphOperationError() from e
            observation.update(output={"operation_count": len(response.ops)})
            return response.ops


@lru_cache(maxsize=1)
def get_extractor() -> GraphExtractor:
    return GraphExtractor(get_ai_client())
