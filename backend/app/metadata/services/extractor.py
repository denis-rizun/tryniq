import structlog
from openai import OpenAIError

from app.config import config
from app.core.client import AIClient
from app.core.constants import METADATA_SYSTEM_PROMPT, AIRequestKind, StructuredRequest
from app.core.exceptions import AIValidationError
from app.metadata.constants import METADATA_JSON_SCHEMA
from app.metadata.schemas import ExtractedMetadata
from app.metadata.services.references import MetadataReferences

logger = structlog.get_logger()


class MetadataExtractor:
    def __init__(self, ai_client: AIClient) -> None:
        self.ai_client = ai_client

    async def extract(self, references: MetadataReferences) -> ExtractedMetadata | None:
        attempts = 2
        original = references.format_user_message()
        user_message = original

        for attempt in range(attempts):
            metadata = await self._call_ai(user_message, attempt)
            if metadata is None:
                if attempt == attempts - 1:
                    return None

                user_message = references.correction_message(original, errors="ai call failed", bad_refs=set())
                continue

            bad_refs = references.collect_bad_refs(metadata)
            if not bad_refs:
                return metadata

            if attempt == attempts - 1:
                logger.warning("Dropping metadata nodes after invalid refs", refs=list(bad_refs)[:20])
                return ExtractedMetadata(summary=metadata.summary)

            user_message = references.correction_message(original, errors="references unknown ids", bad_refs=bad_refs)
        return None

    async def _call_ai(self, user_message: str, attempt: int) -> ExtractedMetadata | None:
        request = StructuredRequest(
            kind=AIRequestKind.MEETING_METADATA,
            system=METADATA_SYSTEM_PROMPT,
            user=user_message,
            schema=METADATA_JSON_SCHEMA,
            dto=ExtractedMetadata,
            model=config.metadata.LLM_MODEL,
            max_tokens=config.metadata.LLM_MAX_TOKENS,
        )
        try:
            return await self.ai_client.complete_structured(request)
        except AIValidationError as e:
            logger.warning("Metadata response failed validation", attempt=attempt, errors=str(e)[:500])
            return None
        except OpenAIError as e:
            logger.warning("Metadata AI request failed", attempt=attempt, error=str(e))
            return None
