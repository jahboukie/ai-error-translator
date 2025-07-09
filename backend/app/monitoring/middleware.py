import time
import uuid
from typing import Dict, Any, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import logging

from app.monitoring.logging import RequestLogger, security_logger, performance_logger
from app.monitoring.metrics import metrics
from app.monitoring.error_tracking import error_tracker, error_reporter
from app.config import settings

logger = logging.getLogger(__name__)


class MonitoringMiddleware(BaseHTTPMiddleware):
    """Comprehensive monitoring middleware"""
    
    def __init__(self, app):
        super().__init__(app)
        self.slow_request_threshold = 2.0  # seconds
        
    async def dispatch(self, request: Request, call_next):
        # Generate correlation ID
        correlation_id = str(uuid.uuid4())[:8]
        
        # Setup request context
        request.state.correlation_id = correlation_id
        request.state.start_time = time.time()
        
        # Create request logger
        request_logger = RequestLogger(correlation_id)
        
        # Get request info
        method = request.method
        path = request.url.path
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("User-Agent", "")
        
        # Set error tracking context
        error_tracker.set_extra("correlation_id", correlation_id)
        error_tracker.set_extra("request_path", path)
        error_tracker.set_extra("request_method", method)
        error_tracker.set_extra("client_ip", client_ip)
        
        # Log request
        user_id = getattr(request.state, 'user_id', None)
        user_tier = getattr(request.state, 'user_tier', 'unknown')
        
        request_logger.log_request(
            method=method,
            path=path,
            user_id=user_id,
            client_ip=client_ip,
            user_agent=user_agent[:100]  # Limit length
        )
        
        # Add breadcrumb for error tracking
        error_tracker.add_breadcrumb(
            message=f"Request started: {method} {path}",
            category="request",
            level="info",
            data={
                "method": method,
                "path": path,
                "user_id": user_id,
                "client_ip": client_ip
            }
        )
        
        # Process request
        response = None
        error_occurred = False
        
        try:
            # Start performance transaction
            transaction = error_tracker.start_transaction(
                name=f"{method} {path}",
                op="http.server"
            )
            
            # Process request
            response = await call_next(request)
            
            # Finish transaction
            error_tracker.finish_transaction(transaction, "ok")
            
        except Exception as e:
            error_occurred = True
            
            # Log error
            request_logger.log_error(e, user_id=user_id, client_ip=client_ip)
            
            # Report error
            error_reporter.report_business_logic_error(
                error=e,
                user_id=user_id,
                operation=f"{method} {path}",
                client_ip=client_ip,
                user_agent=user_agent,
                correlation_id=correlation_id
            )
            
            # Record error metrics
            metrics.record_error(
                error_type=type(e).__name__,
                endpoint=path,
                user_tier=user_tier
            )
            
            # Finish transaction with error
            if 'transaction' in locals():
                error_tracker.finish_transaction(transaction, "internal_error")
            
            # Create error response
            response = JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "correlation_id": correlation_id
                }
            )
        
        # Calculate response time
        response_time = time.time() - request.state.start_time
        response_time_ms = int(response_time * 1000)
        
        # Log response
        request_logger.log_response(
            status_code=response.status_code,
            response_time_ms=response_time_ms,
            user_id=user_id
        )
        
        # Record metrics
        metrics.record_http_request(
            method=method,
            endpoint=path,
            status_code=response.status_code,
            duration_seconds=response_time,
            user_tier=user_tier
        )
        
        # Log slow requests
        if response_time > self.slow_request_threshold:
            performance_logger.log_slow_query(
                query_time_ms=response_time_ms,
                query_type="http_request",
                method=method,
                endpoint=path,
                user_id=user_id,
                correlation_id=correlation_id
            )
        
        # Add correlation ID to response headers
        if hasattr(response, 'headers'):
            response.headers["X-Correlation-ID"] = correlation_id
            response.headers["X-Response-Time"] = f"{response_time_ms}ms"
        
        # Add breadcrumb for completion
        error_tracker.add_breadcrumb(
            message=f"Request completed: {response.status_code} in {response_time_ms}ms",
            category="request",
            level="info",
            data={
                "status_code": response.status_code,
                "response_time_ms": response_time_ms
            }
        )
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
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
        
        return "unknown"


class SecurityMonitoringMiddleware(BaseHTTPMiddleware):
    """Security-focused monitoring middleware"""
    
    def __init__(self, app):
        super().__init__(app)
        self.suspicious_paths = [
            "/admin",
            "/wp-admin",
            "/phpmyadmin",
            "/.env",
            "/config",
            "/backup"
        ]
        
        self.suspicious_user_agents = [
            "sqlmap",
            "nmap",
            "nikto",
            "burp",
            "owasp"
        ]
    
    async def dispatch(self, request: Request, call_next):
        # Check for suspicious activity
        await self._check_suspicious_activity(request)
        
        # Continue with request
        response = await call_next(request)
        
        # Log security-relevant events
        await self._log_security_events(request, response)
        
        return response
    
    async def _check_suspicious_activity(self, request: Request):
        """Check for suspicious activity"""
        path = request.url.path.lower()
        user_agent = request.headers.get("User-Agent", "").lower()
        client_ip = self._get_client_ip(request)
        
        # Check for suspicious paths
        if any(suspicious_path in path for suspicious_path in self.suspicious_paths):
            security_logger.log_suspicious_activity(
                activity_type="suspicious_path_access",
                ip_address=client_ip,
                path=path,
                user_agent=user_agent
            )
            
            # Report security incident
            error_reporter.report_security_incident(
                incident_type="suspicious_path_access",
                ip_address=client_ip,
                path=path,
                user_agent=user_agent
            )
        
        # Check for suspicious user agents
        if any(suspicious_ua in user_agent for suspicious_ua in self.suspicious_user_agents):
            security_logger.log_suspicious_activity(
                activity_type="suspicious_user_agent",
                ip_address=client_ip,
                user_agent=user_agent,
                path=path
            )
            
            # Report security incident
            error_reporter.report_security_incident(
                incident_type="suspicious_user_agent",
                ip_address=client_ip,
                user_agent=user_agent,
                path=path
            )
    
    async def _log_security_events(self, request: Request, response: Response):
        """Log security-relevant events"""
        # Log failed authentication attempts
        if response.status_code == 401:
            security_logger.log_authentication_attempt(
                success=False,
                ip_address=self._get_client_ip(request),
                user_agent=request.headers.get("User-Agent", ""),
                endpoint=request.url.path
            )
        
        # Log successful authentication
        if hasattr(request.state, 'user_id') and request.url.path.startswith('/auth/'):
            security_logger.log_authentication_attempt(
                success=True,
                user_id=request.state.user_id,
                ip_address=self._get_client_ip(request),
                user_agent=request.headers.get("User-Agent", ""),
                endpoint=request.url.path
            )
    
    def _get_client_ip(self, request: Request) -> str:
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
        
        return "unknown"


class HealthCheckMiddleware(BaseHTTPMiddleware):
    """Health check and system monitoring middleware"""
    
    def __init__(self, app):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next):
        # Add health check information to request
        if request.url.path == "/health":
            request.state.health_check = True
        
        response = await call_next(request)
        
        # Add health information to response
        if hasattr(request.state, 'health_check'):
            if hasattr(response, 'headers'):
                response.headers["X-Health-Check"] = "ok"
        
        return response