import structlog
from fastapi import APIRouter, Query, WebSocket, status

from app.asr.dependencies import LiveASRServiceDep
from app.config import config

router = APIRouter(tags=["asr"])
logger = structlog.get_logger()


@router.websocket("/asr/sessions")
async def live_asr_session(
    ws: WebSocket,
    service: LiveASRServiceDep,
    token: str | None = Query(default=None),
) -> None:
    if not config.asr.LIVE_ENABLED:
        await ws.close(code=status.WS_1008_POLICY_VIOLATION)
        logger.info("worker rejected: live ASR disabled")
        return

    if token != config.asr.LIVE_AUTH_TOKEN.get_secret_value():
        await ws.close(code=status.WS_1008_POLICY_VIOLATION)
        logger.warning("worker auth rejected")
        return

    await service.run_session(ws)
