"""
Redis cache layer for storing and retrieving company insights.
Handles serialization/deserialization of Pydantic models.
"""

import json
import logging
from typing import Optional
from datetime import timedelta

try:
    import redis
    from redis import Redis
except ImportError:
    redis = None
    Redis = None

from app.models.company import CompanyInsight
from app.core.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """Service for caching company insights in Redis."""
    
    def __init__(self):
        """Initialize Redis connection."""
        self.redis_client = None
        self.enabled = False
        
        try:
            if redis is None:
                logger.warning("Redis library not installed. Cache disabled.")
                return
            
            self.redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
            # Test connection
            self.redis_client.ping()
            self.enabled = True
            logger.info("Redis cache initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize Redis cache: {e}. Cache will be disabled.")
            self.redis_client = None
            self.enabled = False
    
    def _make_key(self, canonical_name: str) -> str:
        """Generate a cache key from a canonical name."""
        return f"company:{canonical_name}"
    
    async def get_cached_company(self, canonical_name: str) -> Optional[CompanyInsight]:
        """
        Retrieve a cached company insight.
        
        Args:
            canonical_name: Normalized company name
            
        Returns:
            CompanyInsight if found and valid, None otherwise
        """
        if not self.enabled or self.redis_client is None:
            return None
        
        try:
            key = self._make_key(canonical_name)
            cached_data = self.redis_client.get(key)
            
            if cached_data:
                data_dict = json.loads(cached_data)
                insight = CompanyInsight.model_validate(data_dict)
                logger.debug(f"Cache hit for {canonical_name}")
                return insight
            
            logger.debug(f"Cache miss for {canonical_name}")
            return None
        except Exception as e:
            logger.error(f"Error retrieving cached company {canonical_name}: {e}")
            return None
    
    async def set_cached_company(
        self,
        canonical_name: str,
        insight: CompanyInsight,
        ttl_seconds: Optional[int] = None
    ) -> bool:
        """
        Cache a company insight in Redis.
        
        Args:
            canonical_name: Normalized company name
            insight: CompanyInsight object to cache
            ttl_seconds: Time-to-live in seconds (defaults to config value)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or self.redis_client is None:
            return False
        
        try:
            if ttl_seconds is None:
                ttl_seconds = settings.CACHE_TTL_SECONDS
            
            key = self._make_key(canonical_name)
            data = insight.model_dump_json()
            
            self.redis_client.setex(
                key,
                timedelta(seconds=ttl_seconds),
                data
            )
            logger.debug(f"Cached company {canonical_name} with TTL {ttl_seconds}s")
            return True
        except Exception as e:
            logger.error(f"Error caching company {canonical_name}: {e}")
            return False
    
    async def invalidate_cache(self, canonical_name: str) -> bool:
        """
        Remove a company from cache.
        
        Args:
            canonical_name: Normalized company name
            
        Returns:
            True if successful or cache disabled, False on error
        """
        if not self.enabled or self.redis_client is None:
            return True
        
        try:
            key = self._make_key(canonical_name)
            self.redis_client.delete(key)
            logger.debug(f"Invalidated cache for {canonical_name}")
            return True
        except Exception as e:
            logger.error(f"Error invalidating cache for {canonical_name}: {e}")
            return False


# Global cache service instance
_cache_service: Optional[CacheService] = None


def get_cache_service() -> CacheService:
    """Get or initialize the global cache service."""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service
