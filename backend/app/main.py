from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import config
from app.core.exceptions import register_exception_handler
from app.db import dispose_engine
from app.ingest.client import MinioClient
from app.ingest.router import router as ingest_router
from app.logger import configure_logging
from app.meeting.router import router as meeting_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    configure_logging()
    logger = structlog.get_logger()
    logger.info("application started", env=config.ENV, version=config.api.VERSION)

    storage = MinioClient()
    await storage.ensure_bucket()
    app.state.storage = storage

    yield

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
app.include_router(ingest_router)

register_exception_handler(app)


@app.get(path="/health", tags=["Health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
