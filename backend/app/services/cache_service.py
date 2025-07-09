"""
Redis-based caching service for AI Error Translator
"""

import json
import hashlib
import asyncio
from typing import Any, Optional, Dict, List
from datetime import datetime, timedelta
import redis.asyncio as redis
import logging

from app.config import settings
from app.monitoring.logging import get_logger, performance_logger

logger = get_logger(__name__)


class CacheService:
    """Redis-based caching service with intelligent cache management"""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.connected = False
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'errors': 0
        }
        
        # Cache TTL configurations (in seconds)
        self.cache_ttls = {
            'translation': 3600,  # 1 hour - translations are relatively stable
            'user_data': 300,     # 5 minutes - user data changes more frequently
            'api_response': 900,  # 15 minutes - general API responses
            'health_check': 60,   # 1 minute - health check data
            'pricing': 1800,      # 30 minutes - pricing data
            'languages': 3600     # 1 hour - supported languages rarely change
        }
    
    async def connect(self) -> bool:
        """Connect to Redis server"""
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Test connection
            await self.redis_client.ping()
            self.connected = True
            logger.info("Redis connection established successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.connected = False
            return False
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()
            self.connected = False
            logger.info("Redis connection closed")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Redis health and return status"""
        try:
            if not self.connected:
                return {"status": "disconnected", "error": "Not connected to Redis"}
            
            # Test ping
            ping_result = await self.redis_client.ping()
            
            # Get info
            info = await self.redis_client.info()
            
            return {
                "status": "healthy",
                "ping": ping_result,
                "connected_clients": info.get('connected_clients', 0),
                "used_memory": info.get('used_memory_human', 'unknown'),
                "cache_stats": self.cache_stats,
                "hit_rate": self._calculate_hit_rate()
            }
            
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}
    
    def _calculate_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total_requests = self.cache_stats['hits'] + self.cache_stats['misses']
        if total_requests == 0:
            return 0.0
        return (self.cache_stats['hits'] / total_requests) * 100
    
    def _generate_cache_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate a consistent cache key"""
        # Create a hash of the arguments
        key_data = {
            'args': args,
            'kwargs': sorted(kwargs.items())
        }
        key_string = json.dumps(key_data, sort_keys=True)
        key_hash = hashlib.md5(key_string.encode()).hexdigest()[:12]
        
        return f"{prefix}:{key_hash}"
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.connected:
            return None
            
        try:
            value = await self.redis_client.get(key)
            if value is not None:
                self.cache_stats['hits'] += 1
                logger.debug(f"Cache hit: {key}")
                return json.loads(value)
            else:
                self.cache_stats['misses'] += 1
                logger.debug(f"Cache miss: {key}")
                return None
                
        except Exception as e:
            self.cache_stats['errors'] += 1
            logger.error(f"Cache get error for key {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set value in cache with TTL"""
        if not self.connected:
            return False
            
        try:
            serialized_value = json.dumps(value, default=str)
            await self.redis_client.setex(key, ttl, serialized_value)
            logger.debug(f"Cache set: {key} (TTL: {ttl}s)")
            return True
            
        except Exception as e:
            self.cache_stats['errors'] += 1
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self.connected:
            return False
            
        try:
            result = await self.redis_client.delete(key)
            logger.debug(f"Cache delete: {key}")
            return result > 0
            
        except Exception as e:
            self.cache_stats['errors'] += 1
            logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching a pattern"""
        if not self.connected:
            return 0
            
        try:
            keys = await self.redis_client.keys(pattern)
            if keys:
                result = await self.redis_client.delete(*keys)
                logger.info(f"Cleared {result} keys matching pattern: {pattern}")
                return result
            return 0
            
        except Exception as e:
            self.cache_stats['errors'] += 1
            logger.error(f"Cache clear pattern error for {pattern}: {e}")
            return 0
    
    async def cache_translation(self, error_text: str, language: str, user_tier: str, 
                              translation_result: Dict[str, Any]) -> bool:
        """Cache translation result"""
        key = self._generate_cache_key(
            "translation",
            error_text=error_text,
            language=language,
            user_tier=user_tier
        )
        
        cache_data = {
            'result': translation_result,
            'cached_at': datetime.utcnow().isoformat(),
            'language': language,
            'user_tier': user_tier
        }
        
        return await self.set(key, cache_data, self.cache_ttls['translation'])
    
    async def get_cached_translation(self, error_text: str, language: str, 
                                   user_tier: str) -> Optional[Dict[str, Any]]:
        """Get cached translation result"""
        key = self._generate_cache_key(
            "translation",
            error_text=error_text,
            language=language,
            user_tier=user_tier
        )
        
        cached_data = await self.get(key)
        if cached_data:
            logger.info(f"Translation cache hit for {language} error")
            return cached_data['result']
        
        return None
    
    async def cache_user_data(self, user_id: str, user_data: Dict[str, Any]) -> bool:
        """Cache user data"""
        key = f"user:{user_id}"
        
        cache_data = {
            'data': user_data,
            'cached_at': datetime.utcnow().isoformat()
        }
        
        return await self.set(key, cache_data, self.cache_ttls['user_data'])
    
    async def get_cached_user_data(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get cached user data"""
        key = f"user:{user_id}"
        
        cached_data = await self.get(key)
        if cached_data:
            return cached_data['data']
        
        return None
    
    async def invalidate_user_cache(self, user_id: str) -> bool:
        """Invalidate user cache when data changes"""
        key = f"user:{user_id}"
        return await self.delete(key)
    
    async def cache_api_response(self, endpoint: str, params: Dict[str, Any], 
                               response_data: Dict[str, Any]) -> bool:
        """Cache API response"""
        key = self._generate_cache_key("api_response", endpoint=endpoint, **params)
        
        cache_data = {
            'response': response_data,
            'cached_at': datetime.utcnow().isoformat(),
            'endpoint': endpoint
        }
        
        return await self.set(key, cache_data, self.cache_ttls['api_response'])
    
    async def get_cached_api_response(self, endpoint: str, 
                                    params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get cached API response"""
        key = self._generate_cache_key("api_response", endpoint=endpoint, **params)
        
        cached_data = await self.get(key)
        if cached_data:
            return cached_data['response']
        
        return None
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            hit_rate = self._calculate_hit_rate()
            
            # Log cache performance metrics
            performance_logger.log_cache_metrics(
                cache_type="redis",
                hit_rate=hit_rate,
                total_hits=self.cache_stats['hits'],
                total_misses=self.cache_stats['misses'],
                total_errors=self.cache_stats['errors']
            )
            
            return {
                'hit_rate': hit_rate,
                'total_hits': self.cache_stats['hits'],
                'total_misses': self.cache_stats['misses'],
                'total_errors': self.cache_stats['errors'],
                'connected': self.connected
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {
                'hit_rate': 0.0,
                'total_hits': 0,
                'total_misses': 0,
                'total_errors': 0,
                'connected': False,
                'error': str(e)
            }


# Global cache service instance
cache_service = CacheService()


def cache_result(cache_type: str, ttl: Optional[int] = None):
    """Decorator to cache function results"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Generate cache key
            key = cache_service._generate_cache_key(cache_type, *args, **kwargs)
            
            # Try to get from cache
            cached_result = await cache_service.get(key)
            if cached_result is not None:
                return cached_result
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Cache result
            cache_ttl = ttl or cache_service.cache_ttls.get(cache_type, 3600)
            await cache_service.set(key, result, cache_ttl)
            
            return result
        
        return wrapper
    return decorator