"""Semantic caching for LLM responses."""

import hashlib
import json
from typing import Any

from loguru import logger

from core.redis_client import get_redis


class SemanticCache:
    """Cache LLM responses using semantic similarity."""

    def __init__(self):
        self.redis = None
        self.enabled = True

    async def _get_redis(self):
        """Get Redis client."""
        if self.redis is None:
            self.redis = await get_redis()
        return self.redis

    def _generate_cache_key(
        self,
        prompt: str,
        model: str,
        params: dict[str, Any] | None = None,
    ) -> str:
        """Generate cache key from prompt and parameters."""
        # Include model and parameters in the key
        key_data = {
            "prompt": prompt,
            "model": model,
            "params": params or {},
        }
        key_str = json.dumps(key_data, sort_keys=True)
        hash_key = hashlib.sha256(key_str.encode()).hexdigest()
        return f"semantic:{model}:{hash_key}"

    async def get(
        self,
        prompt: str,
        model: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Get cached response if available."""
        if not self.enabled:
            return None

        try:
            redis = await self._get_redis()
            key = self._generate_cache_key(prompt, model, params)
            cached = await redis.cache_get(key)

            if cached:
                logger.info(f"Cache hit for model={model}")
                return json.loads(cached)

            return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    async def set(
        self,
        prompt: str,
        model: str,
        response: dict[str, Any],
        params: dict[str, Any] | None = None,
        ttl: int = 3600,
    ) -> None:
        """Cache a response."""
        if not self.enabled:
            return

        try:
            redis = await self._get_redis()
            key = self._generate_cache_key(prompt, model, params)
            await redis.cache_set(key, json.dumps(response), ttl)
            logger.info(f"Cached response for model={model} ttl={ttl}s")
        except Exception as e:
            logger.error(f"Cache set error: {e}")

    async def delete(
        self,
        prompt: str,
        model: str,
        params: dict[str, Any] | None = None,
    ) -> None:
        """Delete cached response."""
        try:
            redis = await self._get_redis()
            key = self._generate_cache_key(prompt, model, params)
            await redis.cache_delete(key)
        except Exception as e:
            logger.error(f"Cache delete error: {e}")

    async def invalidate_model(self, model: str) -> None:
        """Invalidate all cache entries for a model."""
        # This would require a scan operation - expensive
        # For now, just log a warning
        logger.warning(f"Model cache invalidation not implemented for {model}")

    async def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        try:
            redis = await self._get_redis()
            # Get approximate cache size using Redis INFO
            info = await redis.client.info("stats")
            return {
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "hit_rate": (
                    info.get("keyspace_hits", 0)
                    / (info.get("keyspace_hits", 0) + info.get("keyspace_misses", 1))
                    * 100
                ),
            }
        except Exception as e:
            logger.error(f"Cache stats error: {e}")
            return {}


class ExactCache:
    """Simple exact-match cache for deterministic responses."""

    def __init__(self):
        self.redis = None
        self.enabled = True

    async def _get_redis(self):
        """Get Redis client."""
        if self.redis is None:
            self.redis = await get_redis()
        return self.redis

    def _generate_cache_key(
        self,
        prompt: str,
        model: str,
        params: dict[str, Any] | None = None,
    ) -> str:
        """Generate exact cache key."""
        key_data = {
            "prompt": prompt,
            "model": model,
            "params": params or {},
        }
        key_str = json.dumps(key_data, sort_keys=True)
        hash_key = hashlib.sha256(key_str.encode()).hexdigest()
        return f"exact:{model}:{hash_key}"

    async def get(
        self,
        prompt: str,
        model: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Get cached response."""
        if not self.enabled:
            return None

        try:
            redis = await self._get_redis()
            key = self._generate_cache_key(prompt, model, params)
            cached = await redis.cache_get(key)

            if cached:
                logger.info(f"Exact cache hit for model={model}")
                return json.loads(cached)

            return None
        except Exception as e:
            logger.error(f"Exact cache get error: {e}")
            return None

    async def set(
        self,
        prompt: str,
        model: str,
        response: dict[str, Any],
        params: dict[str, Any] | None = None,
        ttl: int = 3600,
    ) -> None:
        """Cache a response."""
        if not self.enabled:
            return

        try:
            redis = await self._get_redis()
            key = self._generate_cache_key(prompt, model, params)
            await redis.cache_set(key, json.dumps(response), ttl)
            logger.info(f"Exact cached response for model={model} ttl={ttl}s")
        except Exception as e:
            logger.error(f"Exact cache set error: {e}")


# Global instances
_semantic_cache: SemanticCache | None = None
_exact_cache: ExactCache | None = None


async def get_semantic_cache() -> SemanticCache:
    """Get global semantic cache instance."""
    global _semantic_cache
    if _semantic_cache is None:
        _semantic_cache = SemanticCache()
    return _semantic_cache


async def get_exact_cache() -> ExactCache:
    """Get global exact cache instance."""
    global _exact_cache
    if _exact_cache is None:
        _exact_cache = ExactCache()
    return _exact_cache
