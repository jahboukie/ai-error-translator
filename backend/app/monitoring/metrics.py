import time
from typing import Dict, Any, Optional
from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, CollectorRegistry, CONTENT_TYPE_LATEST
from prometheus_client.multiprocess import MultiProcessCollector
import os
import logging

from app.config import settings

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Prometheus metrics collector for AI Error Translator"""
    
    def __init__(self):
        self.registry = CollectorRegistry()
        self.enabled = settings.ENABLE_METRICS
        
        if not self.enabled:
            logger.info("Metrics collection disabled")
            return
        
        # HTTP request metrics
        self.http_requests_total = Counter(
            'http_requests_total',
            'Total HTTP requests',
            ['method', 'endpoint', 'status_code', 'user_tier'],
            registry=self.registry
        )
        
        self.http_request_duration_seconds = Histogram(
            'http_request_duration_seconds',
            'HTTP request duration in seconds',
            ['method', 'endpoint', 'status_code'],
            registry=self.registry
        )
        
        # Authentication metrics
        self.auth_attempts_total = Counter(
            'auth_attempts_total',
            'Total authentication attempts',
            ['status', 'method'],
            registry=self.registry
        )
        
        self.active_users = Gauge(
            'active_users',
            'Number of active users',
            registry=self.registry
        )
        
        # API usage metrics
        self.api_calls_total = Counter(
            'api_calls_total',
            'Total API calls',
            ['endpoint', 'user_tier', 'status'],
            registry=self.registry
        )
        
        self.translation_requests_total = Counter(
            'translation_requests_total',
            'Total translation requests',
            ['language', 'error_type', 'user_tier'],
            registry=self.registry
        )
        
        self.translation_confidence = Histogram(
            'translation_confidence',
            'Translation confidence scores',
            ['language', 'error_type'],
            registry=self.registry
        )
        
        # Database metrics
        self.db_connections_active = Gauge(
            'db_connections_active',
            'Active database connections',
            registry=self.registry
        )
        
        self.db_query_duration_seconds = Histogram(
            'db_query_duration_seconds',
            'Database query duration in seconds',
            ['query_type', 'table'],
            registry=self.registry
        )
        
        # AI service metrics
        self.ai_service_calls_total = Counter(
            'ai_service_calls_total',
            'Total AI service calls',
            ['service', 'status'],
            registry=self.registry
        )
        
        self.ai_service_duration_seconds = Histogram(
            'ai_service_duration_seconds',
            'AI service call duration in seconds',
            ['service'],
            registry=self.registry
        )
        
        self.ai_tokens_used_total = Counter(
            'ai_tokens_used_total',
            'Total AI tokens used',
            ['service', 'user_tier'],
            registry=self.registry
        )
        
        # Error metrics
        self.errors_total = Counter(
            'errors_total',
            'Total errors',
            ['error_type', 'endpoint', 'user_tier'],
            registry=self.registry
        )
        
        # Rate limiting metrics
        self.rate_limit_exceeded_total = Counter(
            'rate_limit_exceeded_total',
            'Total rate limit violations',
            ['endpoint', 'user_tier'],
            registry=self.registry
        )
        
        # Subscription metrics
        self.subscription_changes_total = Counter(
            'subscription_changes_total',
            'Total subscription changes',
            ['from_tier', 'to_tier'],
            registry=self.registry
        )
        
        # System metrics
        self.system_info = Info(
            'system_info',
            'System information',
            registry=self.registry
        )
        
        # Set system info
        self.system_info.info({
            'version': '1.0.0',
            'python_version': f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}",
            'debug_mode': str(settings.API_DEBUG).lower()
        })
        
        logger.info("Metrics collection initialized")
    
    def record_http_request(self, method: str, endpoint: str, status_code: int, 
                           duration_seconds: float, user_tier: str = "unknown"):
        """Record HTTP request metrics"""
        if not self.enabled:
            return
        
        self.http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status_code=status_code,
            user_tier=user_tier
        ).inc()
        
        self.http_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint,
            status_code=status_code
        ).observe(duration_seconds)
    
    def record_auth_attempt(self, success: bool, method: str = "jwt"):
        """Record authentication attempt"""
        if not self.enabled:
            return
        
        status = "success" if success else "failure"
        self.auth_attempts_total.labels(status=status, method=method).inc()
    
    def set_active_users(self, count: int):
        """Set active users count"""
        if not self.enabled:
            return
        
        self.active_users.set(count)
    
    def record_api_call(self, endpoint: str, user_tier: str, success: bool):
        """Record API call"""
        if not self.enabled:
            return
        
        status = "success" if success else "failure"
        self.api_calls_total.labels(
            endpoint=endpoint,
            user_tier=user_tier,
            status=status
        ).inc()
    
    def record_translation_request(self, language: str, error_type: str, 
                                  user_tier: str, confidence: float):
        """Record translation request"""
        if not self.enabled:
            return
        
        self.translation_requests_total.labels(
            language=language,
            error_type=error_type,
            user_tier=user_tier
        ).inc()
        
        self.translation_confidence.labels(
            language=language,
            error_type=error_type
        ).observe(confidence)
    
    def record_db_query(self, query_type: str, table: str, duration_seconds: float):
        """Record database query"""
        if not self.enabled:
            return
        
        self.db_query_duration_seconds.labels(
            query_type=query_type,
            table=table
        ).observe(duration_seconds)
    
    def set_db_connections(self, count: int):
        """Set active database connections"""
        if not self.enabled:
            return
        
        self.db_connections_active.set(count)
    
    def record_ai_service_call(self, service: str, duration_seconds: float, 
                              success: bool, tokens_used: int = None, user_tier: str = "unknown"):
        """Record AI service call"""
        if not self.enabled:
            return
        
        status = "success" if success else "failure"
        self.ai_service_calls_total.labels(service=service, status=status).inc()
        
        self.ai_service_duration_seconds.labels(service=service).observe(duration_seconds)
        
        if tokens_used:
            self.ai_tokens_used_total.labels(
                service=service,
                user_tier=user_tier
            ).inc(tokens_used)
    
    def record_error(self, error_type: str, endpoint: str, user_tier: str = "unknown"):
        """Record error occurrence"""
        if not self.enabled:
            return
        
        self.errors_total.labels(
            error_type=error_type,
            endpoint=endpoint,
            user_tier=user_tier
        ).inc()
    
    def record_rate_limit_exceeded(self, endpoint: str, user_tier: str = "unknown"):
        """Record rate limit violation"""
        if not self.enabled:
            return
        
        self.rate_limit_exceeded_total.labels(
            endpoint=endpoint,
            user_tier=user_tier
        ).inc()
    
    def record_subscription_change(self, from_tier: str, to_tier: str):
        """Record subscription change"""
        if not self.enabled:
            return
        
        self.subscription_changes_total.labels(
            from_tier=from_tier,
            to_tier=to_tier
        ).inc()
    
    def get_metrics(self) -> str:
        """Get all metrics in Prometheus format"""
        if not self.enabled:
            return ""
        
        return generate_latest(self.registry)
    
    def get_content_type(self) -> str:
        """Get content type for metrics endpoint"""
        return CONTENT_TYPE_LATEST


# Global metrics collector
metrics = MetricsCollector()


class MetricsMiddleware:
    """Middleware to collect HTTP metrics"""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        start_time = time.time()
        
        # Extract request info
        method = scope["method"]
        path = scope["path"]
        
        # Track user tier if available
        user_tier = "unknown"
        
        async def send_wrapper(message):
            nonlocal user_tier
            
            if message["type"] == "http.response.start":
                # Calculate duration
                duration = time.time() - start_time
                status_code = message["status"]
                
                # Record metrics
                metrics.record_http_request(
                    method=method,
                    endpoint=path,
                    status_code=status_code,
                    duration_seconds=duration,
                    user_tier=user_tier
                )
            
            await send(message)
        
        await self.app(scope, receive, send_wrapper)


def setup_metrics_endpoint():
    """Setup metrics endpoint for Prometheus scraping"""
    from fastapi import FastAPI, Response
    
    metrics_app = FastAPI(title="Metrics", docs_url=None, redoc_url=None)
    
    @metrics_app.get("/metrics")
    async def get_metrics():
        """Prometheus metrics endpoint"""
        return Response(
            content=metrics.get_metrics(),
            media_type=metrics.get_content_type()
        )
    
    return metrics_app