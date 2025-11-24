"""
Cache Manager - Intelligent caching with Redis primary and in-memory fallback
Automatically switches to in-memory cache if Redis is unavailable
"""

import json
import logging
from abc import ABC, abstractmethod
from datetime import timedelta
from typing import Any, Optional
from functools import lru_cache

import redis.asyncio as redis

logger = logging.getLogger(__name__)


class CacheBackend(ABC):
    """Abstract cache backend interface"""

    @abstractmethod
    async def get(self, key: str) -> Optional[str]:
        pass

    @abstractmethod
    async def set(self, key: str, value: str, ttl: int) -> None:
        pass

    @abstractmethod
    async def delete(self, key: str) -> None:
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        pass


class RedisBackend(CacheBackend):
    """Redis cache backend with connection pooling"""

    def __init__(self, url: str = "redis://localhost:6379"):
        self.url = url
        self._client: Optional[redis.Redis] = None

    async def connect(self):
        """Establish Redis connection"""
        try:
            self._client = await redis.from_url(
                self.url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
            )
            await self._client.ping()
            logger.info("Redis connection established")
            return True
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}")
            return False

    async def get(self, key: str) -> Optional[str]:
        if not self._client:
            return None
        try:
            return await self._client.get(key)
        except Exception as e:
            logger.error(f"Redis GET error: {e}")
            return None

    async def set(self, key: str, value: str, ttl: int) -> None:
        if not self._client:
            return
        try:
            await self._client.setex(key, ttl, value)
        except Exception as e:
            logger.error(f"Redis SET error: {e}")

    async def delete(self, key: str) -> None:
        if not self._client:
            return
        try:
            await self._client.delete(key)
        except Exception as e:
            logger.error(f"Redis DELETE error: {e}")

    async def exists(self, key: str) -> bool:
        if not self._client:
            return False
        try:
            return bool(await self._client.exists(key))
        except Exception as e:
            logger.error(f"Redis EXISTS error: {e}")
            return False

    async def close(self):
        """Close Redis connection"""
        if self._client:
            await self._client.close()


class InMemoryBackend(CacheBackend):
    """
    In-memory cache backend with LRU eviction
    Fallback when Redis is unavailable
    """

    def __init__(self, max_size: int = 1000):
        self._cache: dict[str, tuple[str, float]] = {}
        self.max_size = max_size
        logger.info(f"Using in-memory cache (max {max_size} items)")

    async def get(self, key: str) -> Optional[str]:
        import time

        if key in self._cache:
            value, expiry = self._cache[key]
            if expiry == 0 or time.time() < expiry:
                return value
            else:
                del self._cache[key]
        return None

    async def set(self, key: str, value: str, ttl: int) -> None:
        import time

        # Simple LRU: if full, remove oldest entry
        if len(self._cache) >= self.max_size:
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]

        expiry = time.time() + ttl if ttl > 0 else 0
        self._cache[key] = (value, expiry)

    async def delete(self, key: str) -> None:
        self._cache.pop(key, None)

    async def exists(self, key: str) -> bool:
        return key in self._cache


class CacheManager:
    """
    Smart cache manager that tries Redis first, falls back to in-memory cache
    Provides transparent caching for API responses
    """

    # Cache TTLs
    TTL_SERIES_DATA = 3600  # 1 hour for time series data
    TTL_METADATA = 86400  # 24 hours for metadata
    TTL_SEARCH = 1800  # 30 minutes for search results

    def __init__(self, redis_url: Optional[str] = None, use_redis: bool = True):
        self.use_redis = use_redis
        self.backend: CacheBackend = InMemoryBackend()

        if use_redis and redis_url:
            self._redis_backend = RedisBackend(redis_url)
        else:
            self._redis_backend = None

    async def initialize(self):
        """Initialize cache backend (try Redis, fallback to in-memory)"""
        if self._redis_backend:
            connected = await self._redis_backend.connect()
            if connected:
                self.backend = self._redis_backend
                logger.info("Cache: Using Redis")
            else:
                logger.warning("Cache: Redis unavailable, using in-memory fallback")
                self.backend = InMemoryBackend()
        else:
            logger.info("Cache: Using in-memory backend")
            self.backend = InMemoryBackend()

    async def get(self, key: str) -> Any:
        """Directly get value from cache without fetch fallback"""
        cached_value = await self.backend.get(key)
        if cached_value is not None:
            try:
                return json.loads(cached_value)
            except json.JSONDecodeError:
                return cached_value
        return None

    async def get_or_fetch(
        self,
        key: str,
        fetch_func,
        ttl: int = TTL_SERIES_DATA,
        serialize: bool = True,
    ) -> Any:
        """
        Get value from cache or fetch and cache it

        Args:
            key: Cache key
            fetch_func: Async function to fetch data if not cached
            ttl: Time to live in seconds
            serialize: Whether to JSON serialize/deserialize

        Returns:
            Cached or fetched data
        """
        # Try cache first
        cached_value = await self.backend.get(key)

        if cached_value is not None:
            logger.debug(f"Cache HIT: {key}")
            return json.loads(cached_value) if serialize else cached_value

        # Cache miss - fetch data
        logger.debug(f"Cache MISS: {key}")
        value = await fetch_func()

        # Store in cache
        cache_value = json.dumps(value) if serialize else value
        await self.backend.set(key, cache_value, ttl)

        return value

    async def set(self, key: str, value: Any, ttl: int = TTL_SERIES_DATA):
        """Manually set a cache value"""
        cache_value = json.dumps(value)
        await self.backend.set(key, cache_value, ttl)

    async def invalidate(self, key: str):
        """Invalidate a specific cache entry"""
        await self.backend.delete(key)
        logger.debug(f"Cache invalidated: {key}")

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        return await self.backend.exists(key)

    async def close(self):
        """Close cache connections"""
        if isinstance(self.backend, RedisBackend):
            await self.backend.close()

    @staticmethod
    def make_key(prefix: str, *args) -> str:
        """
        Generate cache key from prefix and arguments

        Example:
            make_key("series_data", "IPC251856", last_n=12)
            -> "series_data:IPC251856:12"
        """
        parts = [prefix] + [str(arg) for arg in args if arg is not None]
        return ":".join(parts)
