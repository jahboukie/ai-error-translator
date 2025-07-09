from fastapi import APIRouter, HTTPException, Depends, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.database.connection import get_db_session
from app.services.user_service import UserService
from app.middleware.jwt_authentication import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["users"])
security = HTTPBearer()

# Request models
class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None

class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

class CreateApiKeyRequest(BaseModel):
    name: str

# Response models
class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str]
    subscription_tier: str
    is_active: bool
    is_verified: bool
    created_at: str
    last_login: Optional[str]

class ApiKeyResponse(BaseModel):
    id: str
    name: str
    is_active: bool
    created_at: str
    last_used: Optional[str]
    expires_at: Optional[str]

class NewApiKeyResponse(BaseModel):
    id: str
    name: str
    access_token: str
    refresh_token: str
    token_type: str
    created_at: str

class SubscriptionResponse(BaseModel):
    id: str
    tier: str
    status: str
    stripe_subscription_id: Optional[str]
    current_period_start: Optional[str]
    current_period_end: Optional[str]
    created_at: str

class UsageStatsResponse(BaseModel):
    total_requests: int
    endpoints: dict
    error_count: int
    error_rate: float
    period_days: int

class DashboardResponse(BaseModel):
    user: UserResponse
    subscription: Optional[SubscriptionResponse]
    api_keys: List[ApiKeyResponse]
    usage_stats: UsageStatsResponse

@router.post("/", response_model=UserResponse)
async def create_user(
    request: CreateUserRequest,
    session: AsyncSession = Depends(get_db_session)
):
    """Create a new user account"""
    try:
        user_service = UserService(session)
        user = await user_service.create_user(
            email=request.email,
            password=request.password,
            full_name=request.full_name
        )
        
        return UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            subscription_tier=user.subscription_tier,
            is_active=user.is_active,
            is_verified=user.is_verified,
            created_at=user.created_at.isoformat(),
            last_login=user.last_login.isoformat() if user.last_login else None
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create user")

@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """Get current user's profile"""
    try:
        user_service = UserService(session)
        user = await user_service.get_user_by_id(current_user["user_id"])
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            subscription_tier=user.subscription_tier,
            is_active=user.is_active,
            is_verified=user.is_verified,
            created_at=user.created_at.isoformat(),
            last_login=user.last_login.isoformat() if user.last_login else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user profile: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get user profile")

@router.put("/me", response_model=UserResponse)
async def update_user_profile(
    request: UpdateProfileRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """Update current user's profile"""
    try:
        user_service = UserService(session)
        user = await user_service.update_user_profile(
            user_id=current_user["user_id"],
            full_name=request.full_name,
            email=request.email
        )
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            subscription_tier=user.subscription_tier,
            is_active=user.is_active,
            is_verified=user.is_verified,
            created_at=user.created_at.isoformat(),
            last_login=user.last_login.isoformat() if user.last_login else None
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating user profile: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update user profile")

@router.post("/me/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """Change current user's password"""
    try:
        user_service = UserService(session)
        success = await user_service.change_password(
            user_id=current_user["user_id"],
            current_password=request.current_password,
            new_password=request.new_password
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to change password")
        
        return {"message": "Password changed successfully"}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error changing password: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to change password")

@router.delete("/me")
async def deactivate_account(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """Deactivate current user's account"""
    try:
        user_service = UserService(session)
        success = await user_service.deactivate_user(current_user["user_id"])
        
        if not success:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {"message": "Account deactivated successfully"}
        
    except Exception as e:
        logger.error(f"Error deactivating account: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to deactivate account")

@router.get("/me/api-keys", response_model=List[ApiKeyResponse])
async def get_user_api_keys(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """Get current user's API keys"""
    try:
        user_service = UserService(session)
        api_keys = await user_service.get_user_api_keys(current_user["user_id"])
        
        return [
            ApiKeyResponse(
                id=key["id"],
                name=key["name"],
                is_active=key["is_active"],
                created_at=key["created_at"],
                last_used=key["last_used"],
                expires_at=key["expires_at"]
            )
            for key in api_keys
        ]
        
    except Exception as e:
        logger.error(f"Error getting API keys: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get API keys")

@router.post("/me/api-keys", response_model=NewApiKeyResponse)
async def create_user_api_key(
    request: CreateApiKeyRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """Create a new API key for current user"""
    try:
        user_service = UserService(session)
        api_key_data = await user_service.create_api_key(
            user_id=current_user["user_id"],
            name=request.name
        )
        
        return NewApiKeyResponse(
            id=api_key_data["id"],
            name=api_key_data["name"],
            access_token=api_key_data["access_token"],
            refresh_token=api_key_data["refresh_token"],
            token_type=api_key_data["token_type"],
            created_at=api_key_data["created_at"]
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating API key: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create API key")

@router.delete("/me/api-keys/{api_key_id}")
async def deactivate_api_key(
    api_key_id: str,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """Deactivate an API key"""
    try:
        user_service = UserService(session)
        success = await user_service.deactivate_api_key(
            user_id=current_user["user_id"],
            api_key_id=api_key_id
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="API key not found")
        
        return {"message": "API key deactivated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deactivating API key: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to deactivate API key")

@router.get("/me/usage", response_model=UsageStatsResponse)
async def get_usage_stats(
    days: int = 30,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """Get current user's usage statistics"""
    try:
        user_service = UserService(session)
        stats = await user_service.get_usage_stats(current_user["user_id"], days)
        
        return UsageStatsResponse(
            total_requests=stats["total_requests"],
            endpoints=stats["endpoints"],
            error_count=stats["error_count"],
            error_rate=stats["error_rate"],
            period_days=stats["period_days"]
        )
        
    except Exception as e:
        logger.error(f"Error getting usage stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get usage stats")

@router.get("/me/dashboard", response_model=DashboardResponse)
async def get_user_dashboard(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """Get comprehensive user dashboard data"""
    try:
        user_service = UserService(session)
        dashboard_data = await user_service.get_user_dashboard_data(current_user["user_id"])
        
        user_data = dashboard_data["user"]
        subscription_data = dashboard_data["subscription"]
        api_keys_data = dashboard_data["api_keys"]
        usage_stats_data = dashboard_data["usage_stats"]
        
        return DashboardResponse(
            user=UserResponse(
                id=user_data["id"],
                email=user_data["email"],
                full_name=user_data["full_name"],
                subscription_tier=user_data["subscription_tier"],
                is_active=user_data["is_active"],
                is_verified=user_data["is_verified"],
                created_at=user_data["created_at"],
                last_login=user_data["last_login"]
            ),
            subscription=SubscriptionResponse(
                id=subscription_data["id"],
                tier=subscription_data["tier"],
                status=subscription_data["status"],
                stripe_subscription_id=subscription_data["stripe_subscription_id"],
                current_period_start=subscription_data["current_period_start"],
                current_period_end=subscription_data["current_period_end"],
                created_at=subscription_data["created_at"]
            ) if subscription_data else None,
            api_keys=[
                ApiKeyResponse(
                    id=key["id"],
                    name=key["name"],
                    is_active=key["is_active"],
                    created_at=key["created_at"],
                    last_used=key["last_used"],
                    expires_at=key["expires_at"]
                )
                for key in api_keys_data
            ],
            usage_stats=UsageStatsResponse(
                total_requests=usage_stats_data["total_requests"],
                endpoints=usage_stats_data["endpoints"],
                error_count=usage_stats_data["error_count"],
                error_rate=usage_stats_data["error_rate"],
                period_days=usage_stats_data["period_days"]
            )
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting dashboard data: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get dashboard data")