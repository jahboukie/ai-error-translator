import logging
import structlog
import sys
from typing import Any, Dict, Optional
from datetime import datetime

from app.config import settings


def setup_logging() -> None:
    """Setup structured logging with structlog"""
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if not settings.API_DEBUG else structlog.dev.ConsoleRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.LOG_LEVEL.upper()),
    )
    
    # Set log levels for specific modules
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


class StructuredLogger:
    """Structured logger with contextual information"""
    
    def __init__(self, name: str):
        self.logger = structlog.get_logger(name)
        self.name = name
    
    def info(self, message: str, **kwargs):
        """Log info message with context"""
        self.logger.info(message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with context"""
        self.logger.warning(message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message with context"""
        self.logger.error(message, **kwargs)
    
    def exception(self, message: str, **kwargs):
        """Log exception with traceback"""
        self.logger.exception(message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log debug message with context"""
        self.logger.debug(message, **kwargs)
    
    def bind(self, **kwargs):
        """Bind context to logger"""
        return StructuredLogger(self.name).with_context(**kwargs)
    
    def with_context(self, **kwargs):
        """Add context to logger"""
        self.logger = self.logger.bind(**kwargs)
        return self


def get_logger(name: str) -> StructuredLogger:
    """Get a structured logger instance"""
    return StructuredLogger(name)


class RequestLogger:
    """Logger for HTTP requests with correlation IDs"""
    
    def __init__(self, correlation_id: str = None):
        self.correlation_id = correlation_id or self._generate_correlation_id()
        self.logger = get_logger("request").bind(correlation_id=self.correlation_id)
    
    def _generate_correlation_id(self) -> str:
        """Generate a unique correlation ID"""
        import uuid
        return str(uuid.uuid4())[:8]
    
    def log_request(self, method: str, path: str, user_id: str = None, **kwargs):
        """Log incoming request"""
        self.logger.info(
            "Request received",
            method=method,
            path=path,
            user_id=user_id,
            **kwargs
        )
    
    def log_response(self, status_code: int, response_time_ms: int, **kwargs):
        """Log outgoing response"""
        self.logger.info(
            "Response sent",
            status_code=status_code,
            response_time_ms=response_time_ms,
            **kwargs
        )
    
    def log_error(self, error: Exception, **kwargs):
        """Log request error"""
        self.logger.error(
            "Request failed",
            error_type=type(error).__name__,
            error_message=str(error),
            **kwargs
        )


class SecurityLogger:
    """Logger for security events"""
    
    def __init__(self):
        self.logger = get_logger("security")
    
    def log_authentication_attempt(self, user_id: str = None, ip_address: str = None, 
                                  success: bool = False, **kwargs):
        """Log authentication attempt"""
        self.logger.info(
            "Authentication attempt",
            user_id=user_id,
            ip_address=ip_address,
            success=success,
            **kwargs
        )
    
    def log_rate_limit_exceeded(self, ip_address: str = None, user_id: str = None, **kwargs):
        """Log rate limit violation"""
        self.logger.warning(
            "Rate limit exceeded",
            ip_address=ip_address,
            user_id=user_id,
            **kwargs
        )
    
    def log_suspicious_activity(self, activity_type: str, user_id: str = None, 
                               ip_address: str = None, **kwargs):
        """Log suspicious activity"""
        self.logger.warning(
            "Suspicious activity detected",
            activity_type=activity_type,
            user_id=user_id,
            ip_address=ip_address,
            **kwargs
        )
    
    def log_token_revoked(self, token_jti: str, user_id: str = None, reason: str = None, **kwargs):
        """Log token revocation"""
        self.logger.info(
            "Token revoked",
            token_jti=token_jti,
            user_id=user_id,
            reason=reason,
            **kwargs
        )


class BusinessLogger:
    """Logger for business events"""
    
    def __init__(self):
        self.logger = get_logger("business")
    
    def log_user_created(self, user_id: str, email: str, **kwargs):
        """Log user registration"""
        self.logger.info(
            "User created",
            user_id=user_id,
            email=email,
            **kwargs
        )
    
    def log_subscription_changed(self, user_id: str, old_tier: str, new_tier: str, **kwargs):
        """Log subscription change"""
        self.logger.info(
            "Subscription changed",
            user_id=user_id,
            old_tier=old_tier,
            new_tier=new_tier,
            **kwargs
        )
    
    def log_api_key_created(self, user_id: str, api_key_id: str, **kwargs):
        """Log API key creation"""
        self.logger.info(
            "API key created",
            user_id=user_id,
            api_key_id=api_key_id,
            **kwargs
        )
    
    def log_translation_request(self, user_id: str, error_type: str, confidence: float, **kwargs):
        """Log translation request"""
        self.logger.info(
            "Translation completed",
            user_id=user_id,
            error_type=error_type,
            confidence=confidence,
            **kwargs
        )
    
    def log_payment_processed(self, user_id: str, amount: float, currency: str, **kwargs):
        """Log payment processing"""
        self.logger.info(
            "Payment processed",
            user_id=user_id,
            amount=amount,
            currency=currency,
            **kwargs
        )


class PerformanceLogger:
    """Logger for performance metrics"""
    
    def __init__(self):
        self.logger = get_logger("performance")
    
    def log_slow_query(self, query_time_ms: int, query_type: str, **kwargs):
        """Log slow database query"""
        self.logger.warning(
            "Slow query detected",
            query_time_ms=query_time_ms,
            query_type=query_type,
            **kwargs
        )
    
    def log_ai_service_performance(self, service_name: str, response_time_ms: int, 
                                  tokens_used: int = None, **kwargs):
        """Log AI service performance"""
        self.logger.info(
            "AI service call",
            service_name=service_name,
            response_time_ms=response_time_ms,
            tokens_used=tokens_used,
            **kwargs
        )
    
    def log_cache_metrics(self, cache_type: str, hit_rate: float, **kwargs):
        """Log cache performance"""
        self.logger.info(
            "Cache metrics",
            cache_type=cache_type,
            hit_rate=hit_rate,
            **kwargs
        )


def setup_request_logging():
    """Setup request logging middleware"""
    import uuid
    from contextvars import ContextVar
    
    # Context variable for correlation ID
    correlation_id: ContextVar[str] = ContextVar('correlation_id', default=None)
    
    def get_correlation_id() -> str:
        """Get current correlation ID"""
        return correlation_id.get() or str(uuid.uuid4())[:8]
    
    def set_correlation_id(cid: str):
        """Set correlation ID for current context"""
        correlation_id.set(cid)
    
    return get_correlation_id, set_correlation_id


# Global logger instances
security_logger = SecurityLogger()
business_logger = BusinessLogger()
performance_logger = PerformanceLogger()