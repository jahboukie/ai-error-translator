import logging
from typing import Optional
from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import hashlib
import hmac
import time

from app.config import settings

logger = logging.getLogger(__name__)

class AuthenticationMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.bearer_scheme = HTTPBearer(auto_error=False)
        
        # Public endpoints that don't require authentication
        self.public_endpoints = {
            "/",
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/supported-languages",
            "/webhook",
            "/pricing"
        }
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip authentication for public endpoints
        if request.url.path in self.public_endpoints:
            return await call_next(request)
        
        # Skip authentication for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # Extract and validate token
        try:
            auth_header = request.headers.get("Authorization", "")
            
            if not auth_header.startswith("Bearer "):
                raise HTTPException(
                    status_code=401,
                    detail="Missing or invalid authorization header"
                )
            
            token = auth_header[7:]  # Remove "Bearer " prefix
            
            # Validate the token
            if not self._validate_token(token):
                raise HTTPException(
                    status_code=401,
                    detail="Invalid or expired token"
                )
            
            # Add user info to request state for use in endpoints
            request.state.user_id = self._extract_user_id(token)
            request.state.token = token
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            raise HTTPException(
                status_code=401,
                detail="Authentication failed"
            )
        
        response = await call_next(request)
        return response
    
    def _validate_token(self, token: str) -> bool:
        """
        Validate the API token
        This is a simple implementation - in production you might want to use JWT
        """
        try:
            # For development, accept any non-empty token
            if settings.API_DEBUG and token and len(token) > 0:
                return True
            
            # Simple token validation (you can replace with JWT or database lookup)
            if len(token) < 32:  # Minimum token length
                return False
            
            # Check if token contains valid characters
            valid_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")
            if not all(c in valid_chars for c in token):
                return False
            
            # In a real implementation, you would:
            # 1. Decode JWT token
            # 2. Verify signature
            # 3. Check expiration
            # 4. Validate claims
            # 5. Look up user in database
            
            return True
            
        except Exception as e:
            logger.error(f"Token validation error: {str(e)}")
            return False
    
    def _extract_user_id(self, token: str) -> str:
        """
        Extract user ID from token
        """
        # Simple implementation - hash the token to create a user ID
        # In production, you'd decode the JWT or look up in database
        return hashlib.sha256(token.encode()).hexdigest()[:16]
    
    def generate_api_key(self, user_id: str) -> str:
        """
        Generate an API key for a user (for development/testing)
        """
        # Simple API key generation
        # In production, use proper JWT or database-backed tokens
        timestamp = str(int(time.time()))
        data = f"{user_id}:{timestamp}"
        signature = hmac.new(
            settings.API_SECRET_KEY.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return f"{user_id}.{timestamp}.{signature}"
    
    def create_development_token(self) -> str:
        """
        Create a development token for testing
        """
        if settings.API_DEBUG:
            return "dev-token-12345678901234567890123456789012"
        else:
            return self.generate_api_key("dev-user")