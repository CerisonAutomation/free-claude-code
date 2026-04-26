"""Redis client for rate limiting, caching, and session storage."""

import json
from typing import Any

import redis.asyncio as redis
from loguru import logger

from config.settings import get_settings


class RedisClient:
    """Async Redis client with token bucket rate limiting and caching."""

    def __init__(self):
        self._client: redis.Redis | None = None
        self._settings = get_settings()

    async def connect(self) -> None:
        """Establish Redis connection."""
        redis_url = (
            self._settings.redis_url
            if hasattr(self._settings, "redis_url")
            else "redis://localhost:6379/0"
        )
        self._client = await redis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        logger.info("Redis client connected")

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            logger.info("Redis client disconnected")

    @property
    def client(self) -> redis.Redis:
        """Get Redis client, raising error if not connected."""
        if not self._client:
            raise RuntimeError("Redis client not connected. Call connect() first.")
        return self._client

    async def rate_limit_check(
        self, key: str, limit: int, window: int, burst: int | None = None
    ) -> tuple[bool, int]:
        """Token bucket rate limiting check.

        Args:
            key: Unique identifier for the rate limit (e.g., user_id)
            limit: Maximum tokens per window
            window: Window size in seconds
            burst: Optional burst capacity (default: limit)

        Returns:
            (allowed, remaining_tokens): Whether request is allowed and remaining tokens
        """
        if burst is None:
            burst = limit

        tokens_key = f"rate_limit_tokens:{key}"
        last_update_key = f"rate_limit_last:{key}"

        pipe = self.client.pipeline()
        pipe.get(tokens_key)
        pipe.get(last_update_key)
        pipe.time()
        results = await pipe.execute()

        tokens_str, last_update_str, current_time = results
        tokens = float(tokens_str) if tokens_str else burst
        last_update = float(last_update_str) if last_update_str else current_time

        # Refill tokens based on elapsed time
        elapsed = current_time - last_update
        refill_rate = limit / window
        tokens = min(burst, tokens + elapsed * refill_rate)

        # Check if request is allowed
        allowed = tokens >= 1
        if allowed:
            tokens -= 1

        # Update Redis (single operation)
        pipe.set(tokens_key, tokens)
        pipe.set(last_update_key, current_time)
        pipe.expire(tokens_key, window * 2)
        pipe.expire(last_update_key, window * 2)
        await pipe.execute()

        return allowed, int(tokens)

    async def cache_get(self, key: str) -> str | None:
        """Get cached value."""
        value = await self.client.get(f"cache:{key}")
        return value

    async def cache_set(self, key: str, value: str, ttl: int = 3600) -> None:
        """Cache value with TTL."""
        await self.client.setex(f"cache:{key}", ttl, value)

    async def cache_delete(self, key: str) -> None:
        """Delete cached value."""
        await self.client.delete(f"cache:{key}")

    async def session_get(self, session_id: str) -> dict[str, Any] | None:
        """Get session data."""
        data = await self.client.get(f"session:{session_id}")
        if data:
            return json.loads(data)
        return None

    async def session_set(
        self, session_id: str, data: dict[str, Any], ttl: int = 86400
    ) -> None:
        """Set session data with TTL."""
        await self.client.setex(f"session:{session_id}", ttl, json.dumps(data))

    async def session_delete(self, session_id: str) -> None:
        """Delete session."""
        await self.client.delete(f"session:{session_id}")

    async def increment_counter(self, key: str, amount: float = 1.0) -> float:
        """Increment a counter."""
        return await self.client.incrbyfloat(f"counter:{key}", amount)

    async def get_counter(self, key: str) -> float:
        """Get counter value."""
        value = await self.client.get(f"counter:{key}")
        return float(value) if value else 0.0

    async def set_counter(self, key: str, value: float, ttl: int | None = None) -> None:
        """Set counter value."""
        if ttl:
            await self.client.setex(f"counter:{key}", ttl, str(value))
        else:
            await self.client.set(f"counter:{key}", str(value))

    async def health_check(self) -> bool:
        """Check Redis health."""
        try:
            result = self.client.ping()
            if hasattr(result, "__await__"):
                await result
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False


# Global instance
_redis_client: RedisClient | None = None


async def get_redis() -> RedisClient:
    """Get global Redis client instance."""
    global _redis_client
    if _redis_client is None:
        _redis_client = RedisClient()
        await _redis_client.connect()
    return _redis_client


async def close_redis() -> None:
    """Close global Redis client."""
    global _redis_client
    if _redis_client:
        await _redis_client.disconnect()
        _redis_client = None
