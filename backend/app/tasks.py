from taskiq_redis import ListQueueBroker, RedisAsyncResultBackend

from app.config import config

backend: RedisAsyncResultBackend = RedisAsyncResultBackend(redis_url=config.redis.URL)
broker = ListQueueBroker(url=config.redis.URL).with_result_backend(backend)

import app.asr.tasks  # noqa: E402, F401
import app.graph.tasks  # noqa: E402, F401
import app.upload.tasks  # noqa: E402, F401
