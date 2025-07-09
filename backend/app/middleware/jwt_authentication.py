import logging
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response, JSONResponse

from app.services.auth_service import AuthService
from app.config import settings

logger = logging.getLogger(__name__)

class JWTAuthenticationMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.auth_service = AuthService()
        
        # Public endpoints that don't require authentication
        self.public_endpoints = {
            "/",
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/supported-languages",
            "/webhook",
            "/pricing",
            "/auth/login",
            "/auth/register",
            "/auth/refresh",
            "/auth/forgot-password",
            "/auth/reset-password"
        }
        
        # Development endpoints (only available in debug mode)
        self.dev_endpoints = {
            "/dev/create-token"
        }
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip authentication for public endpoints
        if request.url.path in self.public_endpoints:
            return await call_next(request)
        
        # Skip authentication for development endpoints in debug mode
        if settings.API_DEBUG and request.url.path in self.dev_endpoints:
            return await call_next(request)
        
        # Skip authentication for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # Extract and validate JWT token
        try:
            auth_header = request.headers.get("Authorization", "")
            
            if not auth_header.startswith("Bearer "):
                return self._create_error_response(
                    401, 
                    "Missing or invalid authorization header", 
                    "MISSING_AUTH_HEADER"
                )
            
            token = auth_header[7:]  # Remove "Bearer " prefix
            
            # Validate the JWT token
            user_data = self.auth_service.validate_api_key(token)
            
            if not user_data:
                return self._create_error_response(
                    401, 
                    "Invalid or expired token", 
                    "INVALID_TOKEN"
                )
            
            # Add user info to request state for use in endpoints
            request.state.user_id = user_data["user_id"]
            request.state.user_tier = user_data["tier"]
            request.state.api_key = user_data["api_key"]
            request.state.token_created_at = user_data["created_at"]
            
            logger.info(f"Authenticated user {user_data['user_id']} with tier {user_data['tier']}")
            
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return self._create_error_response(
                401, 
                "Authentication failed", 
                "AUTH_ERROR"
            )
        
        response = await call_next(request)
        return response
    
    def _create_error_response(self, status_code: int, message: str, error_code: str) -> JSONResponse:
        """Create a standardized error response"""
        return JSONResponse(
            status_code=status_code,
            content={
                "error": {
                    "code": error_code,
                    "message": message,
                    "status_code": status_code
                }
            }
        )

# Dependency for getting current user from request state
def get_current_user(request: Request) -> Dict[str, Any]:
    """Get current user from request state"""
    if not hasattr(request.state, 'user_id'):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated"
        )
    
    return {
        "user_id": request.state.user_id,
        "tier": request.state.user_tier,
        "api_key": request.state.api_key,
        "created_at": request.state.token_created_at
    }

# Dependency for checking subscription tier
def require_tier(required_tier: str):
    """Dependency factory for checking subscription tier"""
    def check_tier(request: Request) -> Dict[str, Any]:
        user = get_current_user(request)
        
        # Define tier hierarchy
        tier_levels = {"free": 0, "pro": 1, "enterprise": 2}
        
        user_level = tier_levels.get(user["tier"], 0)
        required_level = tier_levels.get(required_tier, 0)
        
        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This endpoint requires {required_tier} tier or higher"
            )
        
        return user
    
    return check_tier