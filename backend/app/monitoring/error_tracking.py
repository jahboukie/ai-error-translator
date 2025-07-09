import logging
from typing import Dict, Any, Optional, Callable
from functools import wraps
import traceback
import sys

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.asyncio import AsyncioIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

from app.config import settings

logger = logging.getLogger(__name__)


def setup_error_tracking():
    """Setup Sentry error tracking"""
    if not settings.SENTRY_DSN or not settings.ENABLE_ERROR_TRACKING:
        logger.info("Error tracking disabled")
        return
    
    # Setup Sentry
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        integrations=[
            FastApiIntegration(auto_enabling_integrations=True),
            SqlalchemyIntegration(),
            AsyncioIntegration(),
            LoggingIntegration(level=logging.INFO, event_level=logging.ERROR)
        ],
        traces_sample_rate=settings.ERROR_SAMPLE_RATE,
        environment="production" if not settings.API_DEBUG else "development",
        release="1.0.0",  # You can get this from environment or git
        before_send=before_send_filter,
        before_send_transaction=before_send_transaction_filter,
    )
    
    logger.info("Error tracking initialized with Sentry")


def before_send_filter(event: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Filter events before sending to Sentry"""
    
    # Don't send health check errors
    if event.get('request', {}).get('url', '').endswith('/health'):
        return None
    
    # Don't send authentication errors (they're expected)
    if event.get('exception', {}).get('values', [{}])[0].get('type') == 'HTTPException':
        status_code = event.get('contexts', {}).get('response', {}).get('status_code')
        if status_code in [401, 403]:
            return None
    
    # Add user context if available
    if 'user' not in event and hasattr(hint, 'user_id'):
        event['user'] = {
            'id': hint.user_id,
            'ip_address': hint.get('ip_address', '{{auto}}')
        }
    
    return event


def before_send_transaction_filter(event: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Filter transactions before sending to Sentry"""
    
    # Don't send transactions for health checks
    if event.get('transaction', '').endswith('/health'):
        return None
    
    # Don't send transactions for metrics endpoint
    if event.get('transaction', '').endswith('/metrics'):
        return None
    
    return event


class ErrorTracker:
    """Error tracking and reporting utilities"""
    
    def __init__(self):
        self.enabled = settings.ENABLE_ERROR_TRACKING and bool(settings.SENTRY_DSN)
    
    def capture_exception(self, exception: Exception, **kwargs):
        """Capture an exception with context"""
        if not self.enabled:
            return
        
        with sentry_sdk.configure_scope() as scope:
            # Add extra context
            for key, value in kwargs.items():
                scope.set_extra(key, value)
            
            sentry_sdk.capture_exception(exception)
    
    def capture_message(self, message: str, level: str = "info", **kwargs):
        """Capture a message with context"""
        if not self.enabled:
            return
        
        with sentry_sdk.configure_scope() as scope:
            # Add extra context
            for key, value in kwargs.items():
                scope.set_extra(key, value)
            
            sentry_sdk.capture_message(message, level)
    
    def set_user_context(self, user_id: str, email: str = None, ip_address: str = None):
        """Set user context for error tracking"""
        if not self.enabled:
            return
        
        with sentry_sdk.configure_scope() as scope:
            scope.set_user({
                "id": user_id,
                "email": email,
                "ip_address": ip_address or "{{auto}}"
            })
    
    def set_tag(self, key: str, value: str):
        """Set a tag for error tracking"""
        if not self.enabled:
            return
        
        with sentry_sdk.configure_scope() as scope:
            scope.set_tag(key, value)
    
    def set_extra(self, key: str, value: Any):
        """Set extra context for error tracking"""
        if not self.enabled:
            return
        
        with sentry_sdk.configure_scope() as scope:
            scope.set_extra(key, value)
    
    def add_breadcrumb(self, message: str, category: str = "default", level: str = "info", **kwargs):
        """Add a breadcrumb for error tracking"""
        if not self.enabled:
            return
        
        sentry_sdk.add_breadcrumb(
            message=message,
            category=category,
            level=level,
            data=kwargs
        )
    
    def start_transaction(self, name: str, op: str = "http.server") -> Optional[Any]:
        """Start a performance transaction"""
        if not self.enabled:
            return None
        
        return sentry_sdk.start_transaction(name=name, op=op)
    
    def finish_transaction(self, transaction, status: str = "ok"):
        """Finish a performance transaction"""
        if not self.enabled or not transaction:
            return
        
        transaction.set_status(status)
        transaction.finish()


# Global error tracker
error_tracker = ErrorTracker()


def track_errors(func: Callable) -> Callable:
    """Decorator to track errors in functions"""
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            error_tracker.capture_exception(
                e,
                function_name=func.__name__,
                args=str(args)[:200],  # Limit length
                kwargs=str(kwargs)[:200]
            )
            raise
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_tracker.capture_exception(
                e,
                function_name=func.__name__,
                args=str(args)[:200],
                kwargs=str(kwargs)[:200]
            )
            raise
    
    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper


def track_performance(operation_name: str):
    """Decorator to track function performance"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            transaction = error_tracker.start_transaction(
                name=f"{func.__name__}",
                op=operation_name
            )
            
            try:
                result = await func(*args, **kwargs)
                error_tracker.finish_transaction(transaction, "ok")
                return result
            except Exception as e:
                error_tracker.finish_transaction(transaction, "internal_error")
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            transaction = error_tracker.start_transaction(
                name=f"{func.__name__}",
                op=operation_name
            )
            
            try:
                result = func(*args, **kwargs)
                error_tracker.finish_transaction(transaction, "ok")
                return result
            except Exception as e:
                error_tracker.finish_transaction(transaction, "internal_error")
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


class ErrorReporter:
    """Comprehensive error reporting utility"""
    
    def __init__(self):
        self.tracker = error_tracker
    
    def report_authentication_error(self, error: Exception, user_id: str = None, 
                                   ip_address: str = None, user_agent: str = None):
        """Report authentication-related errors"""
        self.tracker.set_tag("error_category", "authentication")
        self.tracker.set_extra("user_id", user_id)
        self.tracker.set_extra("ip_address", ip_address)
        self.tracker.set_extra("user_agent", user_agent)
        
        self.tracker.capture_exception(
            error,
            error_type="authentication_error",
            severity="high"
        )
    
    def report_business_logic_error(self, error: Exception, user_id: str = None, 
                                   operation: str = None, **context):
        """Report business logic errors"""
        self.tracker.set_tag("error_category", "business_logic")
        self.tracker.set_extra("user_id", user_id)
        self.tracker.set_extra("operation", operation)
        
        for key, value in context.items():
            self.tracker.set_extra(key, value)
        
        self.tracker.capture_exception(
            error,
            error_type="business_logic_error",
            severity="medium"
        )
    
    def report_external_service_error(self, error: Exception, service_name: str, 
                                     user_id: str = None, **context):
        """Report external service errors"""
        self.tracker.set_tag("error_category", "external_service")
        self.tracker.set_tag("service_name", service_name)
        self.tracker.set_extra("user_id", user_id)
        
        for key, value in context.items():
            self.tracker.set_extra(key, value)
        
        self.tracker.capture_exception(
            error,
            error_type="external_service_error",
            service=service_name,
            severity="medium"
        )
    
    def report_database_error(self, error: Exception, query_type: str = None, 
                             table: str = None, user_id: str = None):
        """Report database-related errors"""
        self.tracker.set_tag("error_category", "database")
        self.tracker.set_extra("query_type", query_type)
        self.tracker.set_extra("table", table)
        self.tracker.set_extra("user_id", user_id)
        
        self.tracker.capture_exception(
            error,
            error_type="database_error",
            severity="high"
        )
    
    def report_security_incident(self, incident_type: str, user_id: str = None, 
                                ip_address: str = None, **context):
        """Report security incidents"""
        self.tracker.set_tag("error_category", "security")
        self.tracker.set_tag("incident_type", incident_type)
        self.tracker.set_extra("user_id", user_id)
        self.tracker.set_extra("ip_address", ip_address)
        
        for key, value in context.items():
            self.tracker.set_extra(key, value)
        
        self.tracker.capture_message(
            f"Security incident: {incident_type}",
            level="error",
            incident_type=incident_type,
            severity="critical"
        )


# Global error reporter
error_reporter = ErrorReporter()


import asyncio  # Import asyncio for iscoroutinefunction check