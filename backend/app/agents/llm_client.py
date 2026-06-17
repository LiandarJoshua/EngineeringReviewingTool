import hashlib
import asyncio
from typing import Optional
from langchain_ollama import ChatOllama
from app.config import get_settings

settings = get_settings()


def get_ollama_llm(model: Optional[str] = None) -> ChatOllama:
    return ChatOllama(
        model=model or settings.ollama_primary_model,
        base_url=settings.ollama_host,
        temperature=0.1,
        num_predict=2048,
        num_ctx=8192,
    )


def get_synthesis_llm() -> ChatOllama:
    return get_ollama_llm(settings.ollama_synthesis_model)


def get_reviewer_llm() -> ChatOllama:
    """Fine-tuned severity classifier — falls back to primary if not yet created."""
    return get_ollama_llm(settings.ollama_reviewer_model)


async def cached_llm_call(llm: ChatOllama, prompt: str, cache_ttl: int = 3600) -> str:
    from app.storage.redis_cache import get_cached, set_cached
    cache_key = f"llm:{hashlib.md5(prompt.encode()).hexdigest()}"
    cached = await get_cached(cache_key)
    if cached:
        return cached
    response = await asyncio.to_thread(llm.invoke, prompt)
    content = response.content
    await set_cached(cache_key, content, ttl=cache_ttl)
    return content
