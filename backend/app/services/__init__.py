"""External service clients: Open-Meteo (live), a small HTTP-JSON helper, the
Redis cache abstraction, and the non-blocking MOSDAC structure.
(Groq LLM client is added in Phase 5.)"""

from app.services.cache import (
    InMemoryCache,
    JsonCache,
    NullCache,
    RedisCache,
    marine_cache_key,
    weather_cache_key,
)
from app.services.http import HttpClientError, get_json

__all__ = [
    "get_json",
    "HttpClientError",
    "JsonCache",
    "RedisCache",
    "InMemoryCache",
    "NullCache",
    "weather_cache_key",
    "marine_cache_key",
]
