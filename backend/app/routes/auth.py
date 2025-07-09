from fastapi import APIRouter, HTTPException, Depends, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional
import logging

from app.services.auth_service import AuthService
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])
auth_service = AuthService()
security = HTTPBearer()

# Request models
class TokenRequest(BaseModel):
    user_id: str
    tier: str = "free"
    email: Optional[str] = None

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None

# Response models
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int = 1800  # 30 minutes

class UserResponse(BaseModel):
    user_id: str
    tier: str
    email: Optional[str] = None
    created_at: str

@router.post("/create-token", response_model=TokenResponse)
async def create_api_token(request: TokenRequest):
    """Create a new API token (development endpoint)"""
    if not settings.API_DEBUG:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Endpoint not available in production"
        )
    
    try:
        token_data = auth_service.create_api_key(
            user_id=request.user_id,
            tier=request.tier
        )
        
        logger.info(f"Created API token for user {request.user_id} with tier {request.tier}")
        
        return TokenResponse(
            access_token=token_data["access_token"],
            refresh_token=token_data["refresh_token"],
            token_type=token_data["token_type"]
        )
        
    except Exception as e:
        logger.error(f"Error creating API token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create API token"
        )

@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(request: RefreshTokenRequest):
    """Refresh an access token using a refresh token"""
    try:
        token_data = auth_service.refresh_access_token(request.refresh_token)
        
        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )
        
        logger.info("Access token refreshed successfully")
        
        return TokenResponse(
            access_token=token_data["access_token"],
            refresh_token=request.refresh_token,  # Keep the same refresh token
            token_type=token_data["token_type"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh token"
        )

@router.post("/validate")
async def validate_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Validate a JWT token"""
    try:
        user_data = auth_service.validate_api_key(credentials.credentials)
        
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        
        return {
            "valid": True,
            "user": UserResponse(
                user_id=user_data["user_id"],
                tier=user_data["tier"],
                created_at=user_data["created_at"]
            )
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token validation failed"
        )

# Placeholder endpoints for future user management
@router.post("/register", response_model=TokenResponse)
async def register_user(request: RegisterRequest):
    """Register a new user (placeholder)"""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="User registration not yet implemented. Use /auth/create-token for development."
    )

@router.post("/login", response_model=TokenResponse)
async def login_user(request: LoginRequest):
    """Login a user (placeholder)"""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="User login not yet implemented. Use /auth/create-token for development."
    )

@router.post("/logout")
async def logout_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Logout a user (placeholder)"""
    # In a real implementation, you would blacklist the token
    # For now, just return success
    return {"message": "Logged out successfully"}

@router.post("/forgot-password")
async def forgot_password(email: EmailStr):
    """Request password reset (placeholder)"""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Password reset not yet implemented"
    )

@router.post("/reset-password")
async def reset_password(token: str, new_password: str):
    """Reset password (placeholder)"""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Password reset not yet implemented"
    )