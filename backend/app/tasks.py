from importlib import import_module

from taskiq_redis import ListQueueBroker, RedisAsyncResultBackend

from app.config import config

backend: RedisAsyncResultBackend = RedisAsyncResultBackend(redis_url=config.redis.URL)
broker = ListQueueBroker(url=config.redis.URL).with_result_backend(backend)

task_modules = tuple(
    import_module(module_name)
    for module_name in (
        "app.asr.tasks",
        "app.chat.tasks",
        "app.graph.tasks",
        "app.metadata.tasks",
        "app.upload.tasks",
    )
)
