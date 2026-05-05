from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.asr.router import router as asr_router
from app.chat.router import router as chat_router
from app.config import config
from app.core.exceptions import register_exception_handler
from app.db import dispose_engine
from app.graph.router import router as graph_router
from app.ingest.client import minio_client
from app.ingest.router import router as ingest_router
from app.logger import configure_logging
from app.meeting.client import redis_client
from app.meeting.routers.event import router as events_router
from app.meeting.routers.meeting import router as meeting_router
from app.metadata.router import router as metadata_router
from app.participant.router import router as participant_router
from app.tasks import broker
from app.transcript.router import router as transcript_router
from app.upload.router import router as upload_router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
    configure_logging()
    logger = structlog.get_logger()
    logger.info("application started", env=config.ENV, version=config.api.VERSION)
    logger.info("ASR Models are configured", live_asr_id=config.asr.live_asr_id, final_asr_id=config.asr.final_asr_id)

    await minio_client.ensure_bucket()
    if not broker.is_worker_process:
        await broker.startup()

    yield

    if not broker.is_worker_process:
        await broker.shutdown()
    await redis_client.close()
    await dispose_engine()
    logger.info("application ended")


app = FastAPI(
    title=config.api.NAME,
    version=config.api.VERSION,
    lifespan=lifespan,
    root_path="/api/v1",
    openapi_url=None if config.ENV == "PROD" else "/openapi.json",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.api.ALLOWED_HOSTS,
    allow_credentials=config.api.ALLOW_CREDENTIALS,
    allow_methods=config.api.ALLOWED_METHODS,
    allow_headers=config.api.ALLOWED_HEADERS,
)

app.include_router(meeting_router)
app.include_router(upload_router)
app.include_router(ingest_router)
app.include_router(transcript_router)
app.include_router(participant_router)
app.include_router(events_router)
app.include_router(asr_router)
app.include_router(graph_router)
app.include_router(metadata_router)
app.include_router(chat_router)

register_exception_handler(app)


@app.get(path="/health", tags=["Health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get(path="/models", tags=["Meta"])
async def get_models() -> dict[str, dict[str, str]]:
    return {
        "chat": {"provider": config.ai.PROVIDER, "model": config.chat.LLM_MODEL},
        "graph": {"provider": config.ai.PROVIDER, "model": config.graph.LLM_MODEL},
        "metadata": {"provider": config.ai.PROVIDER, "model": config.metadata.LLM_MODEL},
        "embeddings": {"provider": config.ai.PROVIDER, "model": config.ai.EMBED_MODEL},
        "asr_live": {"provider": config.asr.LIVE_PROVIDER, "model": config.asr.LIVE_MODEL},
        "asr_final": {"provider": config.asr.FINAL_PROVIDER, "model": config.asr.FINAL_MODEL},
    }
