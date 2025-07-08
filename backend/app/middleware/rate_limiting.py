import time
import asyncio
from typing import Dict, Optional
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import json
import logging

from app.config import settings

logger = logging.getLogger(__name__)

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.requests: Dict[str, Dict] = {}
        self.cleanup_interval = 300  # 5 minutes
        self.last_cleanup = time.time()
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip rate limiting for health checks and docs
        if request.url.path in ["/", "/health", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        
        # Get client identifier
        client_id = self._get_client_id(request)
        
        # Check rate limit
        if not self._is_allowed(client_id):
            logger.warning(f"Rate limit exceeded for client: {client_id}")
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Rate limit exceeded",
                    "limit": settings.RATE_LIMIT_REQUESTS,
                    "window": settings.RATE_LIMIT_WINDOW,
                    "retry_after": self._get_retry_after(client_id)
                }
            )
        
        # Record the request
        self._record_request(client_id)
        
        # Cleanup old entries periodically
        await self._cleanup_if_needed()
        
        response = await call_next(request)
        
        # Add rate limit headers
        remaining = self._get_remaining_requests(client_id)
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