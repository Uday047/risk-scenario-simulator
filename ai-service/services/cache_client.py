"""
Day 13 — AI Developer 1
Redis cache client with graceful fallback.
If Redis is unavailable the service continues normally — caching is simply skipped.
Cache key = sha256(prompt); TTL = 1 hour.
"""
import os
import hashlib
import logging

logger = logging.getLogger(__name__)

try:
    import redis
    _redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    _client = redis.from_url(_redis_url, decode_responses=True, socket_connect_timeout=2)
    # Ping to verify connection at startup
    _client.ping()
    REDIS_AVAILABLE = True
    logger.info(f"Redis cache connected: {_redis_url}")
except Exception as e:
    _client = None
    REDIS_AVAILABLE = False
    logger.warning(f"Redis unavailable — caching disabled ({e})")


CACHE_TTL = 3600  # 1 hour


def make_cache_key(prompt: str) -> str:
    """Stable SHA-256 key derived from the prompt text."""
    return "rss:ai:" + hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def cache_get(prompt: str) -> str | None:
    """Return cached Groq response string, or None if cache miss / Redis down."""
    if not REDIS_AVAILABLE:
        return None
    try:
        return _client.get(make_cache_key(prompt))
    except Exception as e:
        logger.warning(f"Cache GET failed: {e}")
        return None


def cache_set(prompt: str, value: str) -> None:
    """Store a Groq response string in Redis with TTL. Silently fails if Redis is down."""
    if not REDIS_AVAILABLE:
        return
    try:
        _client.setex(make_cache_key(prompt), CACHE_TTL, value)
    except Exception as e:
        logger.warning(f"Cache SET failed: {e}")
