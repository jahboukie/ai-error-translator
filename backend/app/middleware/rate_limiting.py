import time
import asyncio
from typing import Dict, Optional
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import json
import logging
import redis.asyncio as redis

from app.config import settings
from app.services.cache_service import cache_service

logger = logging.getLogger(__name__)

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.requests: Dict[str, Dict] = {}
        self.cleanup_interval = 300  # 5 minutes
        self.last_cleanup = time.time()
        self.use_redis = True  # Use Redis for rate limiting if available
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip rate limiting for health checks and docs
        if request.url.path in ["/", "/health", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        
        # Get client identifier
        client_id = self._get_client_id(request)
        
        # Check rate limit
        if self.use_redis and cache_service.connected:
            is_allowed, remaining, retry_after = await self._redis_check_rate_limit(client_id)
        else:
            is_allowed = self._is_allowed(client_id)
            remaining = self._get_remaining_requests(client_id)
            retry_after = self._get_retry_after(client_id)
            
        if not is_allowed:
            logger.warning(f"Rate limit exceeded for client: {client_id}")
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Rate limit exceeded",
                    "limit": settings.RATE_LIMIT_REQUESTS,
                    "window": settings.RATE_LIMIT_WINDOW,
                    "retry_after": retry_after
                }
            )
        
        # Record the request
        if self.use_redis and cache_service.connected:
            await self._redis_record_request(client_id)
        else:
            self._record_request(client_id)
            await self._cleanup_if_needed()
        
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(settings.RATE_LIMIT_REQUESTS)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + settings.RATE_LIMIT_WINDOW)
        
        return response
    
    def _get_client_id(self, request: Request) -> str:
        """
        Get client identifier for rate limiting
        Priority: API key > IP address
        """
        # Try to get API key from Authorization header
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return f"api_key:{auth_header[7:20]}..."  # Use first 20 chars of token
        
        # Fall back to IP address
        client_ip = request.client.host if request.client else "unknown"
        
        # Check for forwarded IP (useful when behind a proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        
        return f"ip:{client_ip}"
    
    def _is_allowed(self, client_id: str) -> bool:
        """
        Check if client is allowed to make a request
        """
        now = time.time()
        
        if client_id not in self.requests:
            return True
        
        client_data = self.requests[client_id]
        window_start = now - settings.RATE_LIMIT_WINDOW
        
        # Count requests in current window
        recent_requests = [
            req_time for req_time in client_data.get("requests", [])
            if req_time > window_start
        ]
        
        return len(recent_requests) < settings.RATE_LIMIT_REQUESTS
    
    def _record_request(self, client_id: str):
        """
        Record a request for rate limiting
        """
        now = time.time()
        
        if client_id not in self.requests:
            self.requests[client_id] = {"requests": [], "first_seen": now}
        
        self.requests[client_id]["requests"].append(now)
        
        # Keep only requests within the window
        window_start = now - settings.RATE_LIMIT_WINDOW
        self.requests[client_id]["requests"] = [
            req_time for req_time in self.requests[client_id]["requests"]
            if req_time > window_start
        ]
    
    def _get_remaining_requests(self, client_id: str) -> int:
        """
        Get remaining requests for client
        """
        if client_id not in self.requests:
            return settings.RATE_LIMIT_REQUESTS
        
        now = time.time()
        window_start = now - settings.RATE_LIMIT_WINDOW
        
        recent_requests = [
            req_time for req_time in self.requests[client_id].get("requests", [])
            if req_time > window_start
        ]
        
        return max(0, settings.RATE_LIMIT_REQUESTS - len(recent_requests))
    
    def _get_retry_after(self, client_id: str) -> int:
        """
        Get retry after time in seconds
        """
        if client_id not in self.requests:
            return 0
        
        requests = self.requests[client_id].get("requests", [])
        if not requests:
            return 0
        
        # Find oldest request in current window
        now = time.time()
        window_start = now - settings.RATE_LIMIT_WINDOW
        
        recent_requests = [req_time for req_time in requests if req_time > window_start]
        
        if len(recent_requests) < settings.RATE_LIMIT_REQUESTS:
            return 0
        
        # Time until oldest request expires
        oldest_request = min(recent_requests)
        retry_after = int(oldest_request + settings.RATE_LIMIT_WINDOW - now)
        
        return max(0, retry_after)
    
    async def _cleanup_if_needed(self):
        """
        Clean up old rate limiting data
        """
        now = time.time()
        
        if now - self.last_cleanup < self.cleanup_interval:
            return
        
        self.last_cleanup = now
        
        # Remove clients with no recent requests
        cutoff = now - settings.RATE_LIMIT_WINDOW * 2  # Keep data for 2x window size
        
        clients_to_remove = []
        for client_id, data in self.requests.items():
            if data.get("first_seen", 0) < cutoff and not data.get("requests"):
                clients_to_remove.append(client_id)
        
        for client_id in clients_to_remove:
            del self.requests[client_id]
        
        logger.info(f"Rate limiting cleanup: removed {len(clients_to_remove)} old clients")
    
    async def _redis_check_rate_limit(self, client_id: str) -> tuple[bool, int, int]:
        """
        Check rate limit using Redis sliding window
        Returns: (is_allowed, remaining_requests, retry_after_seconds)
        """
        try:
            redis_client = cache_service.redis_client
            now = time.time()
            window_start = now - settings.RATE_LIMIT_WINDOW
            
            # Key for storing request timestamps
            key = f"rate_limit:{client_id}"
            
            # Remove old entries and count current requests
            pipe = redis_client.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zcard(key)
            pipe.expire(key, settings.RATE_LIMIT_WINDOW)
            
            results = await pipe.execute()
            current_requests = results[1]
            
            # Calculate remaining requests
            remaining = max(0, settings.RATE_LIMIT_REQUESTS - current_requests)
            
            # Calculate retry after time
            retry_after = 0
            if current_requests >= settings.RATE_LIMIT_REQUESTS:
                # Get oldest request timestamp
                oldest_requests = await redis_client.zrange(key, 0, 0, withscores=True)
                if oldest_requests:
                    oldest_timestamp = oldest_requests[0][1]
                    retry_after = int(oldest_timestamp + settings.RATE_LIMIT_WINDOW - now)
                    retry_after = max(0, retry_after)
            
            is_allowed = current_requests < settings.RATE_LIMIT_REQUESTS
            return is_allowed, remaining, retry_after
            
        except Exception as e:
            logger.error(f"Redis rate limit check failed: {e}")
            # Fallback to in-memory rate limiting
            is_allowed = self._is_allowed(client_id)
            remaining = self._get_remaining_requests(client_id)
            retry_after = self._get_retry_after(client_id)
            return is_allowed, remaining, retry_after
    
    async def _redis_record_request(self, client_id: str):
        """
        Record a request in Redis using sorted set for sliding window
        """
        try:
            redis_client = cache_service.redis_client
            now = time.time()
            
            # Key for storing request timestamps
            key = f"rate_limit:{client_id}"
            
            # Add current request and set expiration
            pipe = redis_client.pipeline()
            pipe.zadd(key, {str(now): now})
            pipe.expire(key, settings.RATE_LIMIT_WINDOW + 60)  # Extra buffer
            
            await pipe.execute()
            
        except Exception as e:
            logger.error(f"Redis rate limit record failed: {e}")
            # Fallback to in-memory recording
            self._record_request(client_id)
    
    async def get_rate_limit_stats(self) -> Dict[str, any]:
        """
        Get rate limiting statistics
        """
        try:
            if self.use_redis and cache_service.connected:
                return await self._get_redis_stats()
            else:
                return self._get_memory_stats()
        except Exception as e:
            logger.error(f"Error getting rate limit stats: {e}")
            return {"error": str(e)}
    
    async def _get_redis_stats(self) -> Dict[str, any]:
        """
        Get Redis-based rate limiting statistics
        """
        try:
            redis_client = cache_service.redis_client
            
            # Get all rate limit keys
            keys = await redis_client.keys("rate_limit:*")
            
            total_clients = len(keys)
            active_clients = 0
            total_requests = 0
            
            # Sample some keys to get stats
            for key in keys[:100]:  # Limit to avoid performance issues
                count = await redis_client.zcard(key)
                total_requests += count
                if count > 0:
                    active_clients += 1
            
            return {
                "backend": "redis",
                "total_clients": total_clients,
                "active_clients": active_clients,
                "total_requests": total_requests,
                "rate_limit_config": {
                    "requests_per_window": settings.RATE_LIMIT_REQUESTS,
                    "window_seconds": settings.RATE_LIMIT_WINDOW
                }
            }
            
        except Exception as e:
            logger.error(f"Redis stats error: {e}")
            return {"error": str(e)}
    
    def _get_memory_stats(self) -> Dict[str, any]:
        """
        Get in-memory rate limiting statistics
        """
        total_clients = len(self.requests)
        active_clients = 0
        total_requests = 0
        
        now = time.time()
        window_start = now - settings.RATE_LIMIT_WINDOW
        
        for client_data in self.requests.values():
            recent_requests = [
                req_time for req_time in client_data.get("requests", [])
                if req_time > window_start
            ]
            
            if recent_requests:
                active_clients += 1
                total_requests += len(recent_requests)
        
        return {
            "backend": "memory",
            "total_clients": total_clients,
            "active_clients": active_clients,
            "total_requests": total_requests,
            "rate_limit_config": {
                "requests_per_window": settings.RATE_LIMIT_REQUESTS,
                "window_seconds": settings.RATE_LIMIT_WINDOW
            }
        }