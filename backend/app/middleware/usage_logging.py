import logging
import time
from typing import Optional
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.database.connection import get_db_session
from app.services.user_service import UserService

logger = logging.getLogger(__name__)


class UsageLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log API usage for authenticated users"""
    
    def __init__(self, app):
        super().__init__(app)
        
        # Endpoints to log usage for
        self.logged_endpoints = {
            "/translate",
            "/create-checkout-session",
            "/create-portal-session"
        }
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip logging for non-logged endpoints
        if request.url.path not in self.logged_endpoints:
            return await call_next(request)
        
        # Skip logging if user is not authenticated
        if not hasattr(request.state, 'user_id'):
            return await call_next(request)
        
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Calculate response time
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # Log usage asynchronously (don't block the response)
        try:
            await self._log_usage(
                request=request,
                response=response,
                response_time_ms=response_time_ms
            )
        except Exception as e:
            logger.error(f"Failed to log usage: {str(e)}")
            # Don't fail the request if logging fails
        
        return response
    
    async def _log_usage(self, request: Request, response: Response, response_time_ms: int):
        """Log API usage to database"""
        try:
            async with get_db_session() as session:
                user_service = UserService(session)
                
                # Get client IP
                client_ip = self._get_client_ip(request)
                
                # Get user agent
                user_agent = request.headers.get("User-Agent")
                
                # Get error information if response failed
                error_type = None
                error_message = None
                if response.status_code >= 400:
                    error_type = f"HTTP_{response.status_code}"
                    # Try to get error message from response (simplified)
                    if hasattr(response, 'body'):
                        try:
                            import json
                            body = response.body.decode()
                            error_data = json.loads(body)
                            error_message = error_data.get('detail', 'Unknown error')
                        except:
                            error_message = f"HTTP {response.status_code}"
                
                # Log usage
                await user_service.log_api_usage(
                    user_id=request.state.user_id,
                    endpoint=request.url.path,
                    method=request.method,
                    status_code=response.status_code,
                    ip_address=client_ip,
                    user_agent=user_agent,
                    response_time_ms=response_time_ms,
                    error_type=error_type,
                    error_message=error_message
                )
                
        except Exception as e:
            logger.error(f"Error logging usage: {str(e)}")
    
    def _get_client_ip(self, request: Request) -> Optional[str]:
        """Get client IP address"""
        # Check for forwarded IP (useful when behind a proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        # Check for real IP
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fall back to client host
        if request.client:
            return request.client.host
        
        return None