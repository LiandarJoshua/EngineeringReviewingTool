import json
import hashlib
import redis.asyncio as aioredis
from typing import Any, Optional, AsyncGenerator
from app.config import get_settings

settings = get_settings()
_redis_client: Optional[aioredis.Redis] = None


def get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


async def get_cached(key: str) -> Optional[Any]:
    r = get_redis()
    value = await r.get(key)
    if value:
        return json.loads(value)
    return None


async def set_cached(key: str, value: Any, ttl: int = 3600) -> None:
    r = get_redis()
    await r.setex(key, ttl, json.dumps(value))


async def delete_cached(key: str) -> None:
    r = get_redis()
    await r.delete(key)


def make_cache_key(prefix: str, *parts: str) -> str:
    combined = ":".join(parts)
    return f"{prefix}:{hashlib.md5(combined.encode()).hexdigest()}"


async def publish_progress(review_id: str, stage: str, status: str, progress_pct: int = 0) -> None:
    r = get_redis()
    message = json.dumps({"stage": stage, "status": status, "progress_pct": progress_pct})
    await r.publish(f"progress:{review_id}", message)


async def subscribe_to_progress(review_id: str) -> AsyncGenerator[dict, None]:
    r = get_redis()
    pubsub = r.pubsub()
    await pubsub.subscribe(f"progress:{review_id}")
    async for message in pubsub.listen():
        if message["type"] == "message":
            yield json.loads(message["data"])


def get_sync_redis():
    """Synchronous Redis client for use inside Celery tasks."""
    import redis as syncredis
    return syncredis.from_url(settings.redis_url, decode_responses=True)


def set_task_id(review_id: str, task_id: str) -> None:
    r = get_sync_redis()
    r.setex(f"task:{review_id}", 86400, task_id)


def get_task_id(review_id: str) -> Optional[str]:
    r = get_sync_redis()
    return r.get(f"task:{review_id}")


def mark_cancelled(review_id: str) -> None:
    r = get_sync_redis()
    r.setex(f"cancel:{review_id}", 86400, "1")


def is_cancelled(review_id: str) -> bool:
    r = get_sync_redis()
    return bool(r.get(f"cancel:{review_id}"))


# Named cache key patterns
CACHE_KEYS = {
    "agent_output": "review:{review_id}:agent:{agent_name}",  # TTL: 1 hour
    "repo_metadata": "repo:{repo_id}:metadata",               # TTL: 24 hours
    "rag_query": "rag:{query_hash}",                           # TTL: 30 min
}
