from dataclasses import dataclass

import structlog
from openai import OpenAIError

from app.config import config
from app.core.client import AIClient
from app.core.constants import METADATA_SYSTEM_PROMPT, AIRequestKind, StructuredRequest
from app.core.exceptions import AIValidationError
from app.core.prompts import METADATA_PROMPT
from app.metadata.constants import METADATA_JSON_SCHEMA
from app.metadata.schemas import ExtractedMetadata
from app.metadata.services.references import MetadataReferences

logger = structlog.get_logger()


@dataclass(frozen=True, slots=True)
class MetadataExtractionResult:
    metadata: ExtractedMetadata | None
    retry_count: int
    fallback_used: bool
    dropped_invalid_references: bool


class MetadataExtractor:
    def __init__(self, ai_client: AIClient) -> None:
        self.ai_client = ai_client

    async def extract(self, references: MetadataReferences) -> ExtractedMetadata | None:
        return (await self.extract_with_status(references)).metadata

    async def extract_with_status(self, references: MetadataReferences) -> MetadataExtractionResult:
        attempts = 2
        original = references.format_user_message()
        user_message = original
        with self.ai_client.langfuse.start_as_current_observation(
            name="metadata.extract",
            as_type="span",
            input={"reference_count": len(references.utterance_by_token)},
            metadata={
                **METADATA_PROMPT.metadata(),
                "environment": config.ENV,
                "model": config.metadata.LLM_MODEL,
            },
        ) as observation:
            for attempt in range(attempts):
                metadata = await self._call_ai(user_message, attempt)
                if metadata is None:
                    if attempt == attempts - 1:
                        result = MetadataExtractionResult(
                            metadata=None,
                            retry_count=attempt,
                            fallback_used=True,
                            dropped_invalid_references=False,
                        )
                        observation.update(output=_result_metadata(result))
                        return result

                    user_message = references.correction_message(
                        original,
                        errors="ai call failed",
                        bad_refs=set(),
                    )
                    continue

                bad_refs = references.collect_bad_refs(metadata)
                if not bad_refs:
                    result = MetadataExtractionResult(
                        metadata=metadata,
                        retry_count=attempt,
                        fallback_used=False,
                        dropped_invalid_references=False,
                    )
                    observation.update(output=_result_metadata(result))
                    return result

                if attempt == attempts - 1:
                    logger.warning(
                        "Dropping metadata nodes after invalid refs",
                        refs=list(bad_refs)[:20],
                    )
                    result = MetadataExtractionResult(
                        metadata=ExtractedMetadata(summary=metadata.summary),
                        retry_count=attempt,
                        fallback_used=True,
                        dropped_invalid_references=True,
                    )
                    observation.update(output=_result_metadata(result))
                    return result

                user_message = references.correction_message(
                    original,
                    errors="references unknown ids",
                    bad_refs=bad_refs,
                )
            result = MetadataExtractionResult(
                metadata=None,
                retry_count=attempts - 1,
                fallback_used=True,
                dropped_invalid_references=False,
            )
            observation.update(output=_result_metadata(result))
            return result

    async def _call_ai(self, user_message: str, attempt: int) -> ExtractedMetadata | None:
        request = StructuredRequest(
            kind=AIRequestKind.MEETING_METADATA,
            system=METADATA_SYSTEM_PROMPT,
            user=user_message,
            schema=METADATA_JSON_SCHEMA,
            dto=ExtractedMetadata,
            model=config.metadata.LLM_MODEL,
            max_tokens=config.metadata.LLM_MAX_TOKENS,
            langfuse_kwargs={
                "name": "metadata.extract.generation",
                "metadata": METADATA_PROMPT.metadata(),
            },
        )
        try:
            return await self.ai_client.complete_structured(request)
        except AIValidationError as e:
            logger.warning("Metadata response failed validation", attempt=attempt, errors=str(e)[:500])
            return None
        except OpenAIError as e:
            logger.warning("Metadata AI request failed", attempt=attempt, error=str(e))
            return None


def _result_metadata(result: MetadataExtractionResult) -> dict[str, object]:
    return {
        "have_metadata": result.metadata is not None,
        "retry_count": result.retry_count,
        "fallback_used": result.fallback_used,
        "dropped_invalid_references": result.dropped_invalid_references,
    }
