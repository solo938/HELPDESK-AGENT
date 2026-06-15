import json
import logging
from typing import Optional, Any, List
from redis import Redis, RedisError
from helpdesk_agent.config.settings import settings

logger = logging.getLogger(__name__)

# Module-level Redis client
try:
    redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
    # Test connection
    redis_client.ping()
    logger.info(f"Connected to Redis at {settings.redis_url}")
except RedisError as e:
    logger.warning(f"Redis connection failed: {e}. Caching will be disabled.")
    redis_client = None


def get_cached_kb_result(query: str) -> Optional[List[dict]]:
    """
    Get cached knowledge base search results for a query.
    
    Args:
        query: User's search query
    
    Returns:
        Cached results list if found and Redis available, else None
    """
    if not redis_client:
        return None
    
    try:
        # Create cache key from query (normalize whitespace, lowercase)
        cache_key = f"kb:{query.strip().lower()}"
        
        cached = redis_client.get(cache_key)
        if cached:
            results = json.loads(cached)
            logger.debug(f"Cache hit for query: {query[:50]}...")
            return results
        else:
            logger.debug(f"Cache miss for query: {query[:50]}...")
            return None
            
    except RedisError as e:
        logger.error(f"Redis error in get_cached_kb_result: {e}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode cached results: {e}")
        return None


def set_cached_kb_result(query: str, results: List[dict], ttl: int = 300) -> bool:
    """
    Cache knowledge base search results.
    
    Args:
        query: User's search query
        results: Results to cache
        ttl: Time to live in seconds (default 5 minutes)
    
    Returns:
        True if cached successfully, False otherwise
    """
    if not redis_client:
        return False
    
    try:
        cache_key = f"kb:{query.strip().lower()}"
        redis_client.set(cache_key, json.dumps(results), ex=ttl)
        logger.debug(f"Cached results for query: {query[:50]}... (TTL: {ttl}s)")
        return True
        
    except RedisError as e:
        logger.error(f"Redis error in set_cached_kb_result: {e}")
        return False
    except json.JSONEncodeError as e:
        logger.error(f"Failed to encode results for caching: {e}")
        return False


def clear_cache_for_query(query: str) -> bool:
    """
    Clear cache for a specific query (useful for invalidation).
    
    Args:
        query: Query to invalidate
    
    Returns:
        True if cleared successfully, False otherwise
    """
    if not redis_client:
        return False
    
    try:
        cache_key = f"kb:{query.strip().lower()}"
        redis_client.delete(cache_key)
        logger.debug(f"Cleared cache for: {query[:50]}...")
        return True
    except RedisError as e:
        logger.error(f"Failed to clear cache: {e}")
        return False


def clear_all_kb_cache() -> bool:
    """
    Clear all knowledge base cache keys.
    
    Returns:
        True if cleared successfully, False otherwise
    """
    if not redis_client:
        return False
    
    try:
        # Find and delete all kb:* keys
        keys = redis_client.keys("kb:*")
        if keys:
            redis_client.delete(*keys)
            logger.info(f"Cleared {len(keys)} cache entries")
        return True
    except RedisError as e:
        logger.error(f"Failed to clear all cache: {e}")
        return False