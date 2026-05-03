import functools
from collections.abc import Awaitable, Callable

from starlette.websockets import WebSocketDisconnect


def suppress_ws_disconnect[**P, R](func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R | None]]:
    @functools.wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R | None:
        try:
            return await func(*args, **kwargs)
        except WebSocketDisconnect:
            return None

    return wrapper
