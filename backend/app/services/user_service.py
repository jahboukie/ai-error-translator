import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
import hashlib
import secrets

from app.database.repositories import UserRepository, ApiKeyRepository, SubscriptionRepository, UsageLogRepository
from app.services.auth_service import AuthService
from app.database.models import User, ApiKey, Subscription

logger = logging.getLogger(__name__)


class UserService:
    """Service for user management operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)
        self.api_key_repo = ApiKeyRepository(session)
        self.subscription_repo = SubscriptionRepository(session)
        self.usage_repo = UsageLogRepository(session)
        self.auth_service = AuthService()
    
    async def create_user(self, email: str, password: str = None, full_name: str = None) -> User:
        """Create a new user"""
        # Check if user already exists
        existing_user = await self.user_repo.get_user_by_email(email)
        if existing_user:
            raise ValueError(f"User with email {email} already exists")
        
        # Create user
        user = await self.user_repo.create_user(
            email=email,
            password=password,
            full_name=full_name
        )
        
        # Create default API key
        await self.create_api_key(user.id, "Default API Key")
        
        logger.info(f"Created new user: {user.email}")
        return user
    
    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate a user with email and password"""
        user = await self.user_repo.get_user_by_email(email)
        if not user or not user.is_active:
            return None
        
        if not await self.user_repo.verify_password(user.id, password):
            return None
        
        # Update last login
        await self.user_repo.update_last_login(user.id)
        
        logger.info(f"User authenticated: {user.email}")
        return user
    
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        return await self.user_repo.get_user_by_id(user_id)
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        return await self.user_repo.get_user_by_email(email)
    
    async def update_user_profile(self, user_id: str, full_name: str = None, 
                                 email: str = None) -> Optional[User]:
        """Update user profile"""
        update_data = {}
        if full_name is not None:
            update_data['full_name'] = full_name
        if email is not None:
            # Check if email is already taken
            existing_user = await self.user_repo.get_user_by_email(email)
            if existing_user and existing_user.id != user_id:
                raise ValueError(f"Email {email} is already taken")
            update_data['email'] = email
        
        if update_data:
            return await self.user_repo.update_user(user_id, **update_data)
        
        return await self.user_repo.get_user_by_id(user_id)
    
    async def change_password(self, user_id: str, current_password: str, new_password: str) -> bool:
        """Change user password"""
        # Verify current password
        if not await self.user_repo.verify_password(user_id, current_password):
            raise ValueError("Current password is incorrect")
        
        # Change password
        return await self.user_repo.change_password(user_id, new_password)
    
    async def deactivate_user(self, user_id: str) -> bool:
        """Deactivate user account"""
        return await self.user_repo.deactivate_user(user_id)
    
    async def create_api_key(self, user_id: str, name: str) -> Dict[str, Any]:
        """Create a new API key for user"""
        # Generate JWT token
        user = await self.user_repo.get_user_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        
        # Create JWT token
        token_data = self.auth_service.create_api_key(user_id, user.subscription_tier)
        
        # Hash the access token for storage
        token_hash = hashlib.sha256(token_data["access_token"].encode()).hexdigest()
        
        # Store API key in database
        api_key = await self.api_key_repo.create_api_key(
            user_id=user_id,
            key_hash=token_hash,
            name=name
        )
        
        return {
            "id": api_key.id,
            "name": api_key.name,
            "access_token": token_data["access_token"],
            "refresh_token": token_data["refresh_token"],
            "token_type": token_data["token_type"],
            "created_at": api_key.created_at.isoformat()
        }
    
    async def validate_api_key(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate API key and return user data"""
        # First validate JWT token
        user_data = self.auth_service.validate_api_key(token)
        if not user_data:
            return None
        
        # Hash token to check in database
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        # Get API key from database
        api_key = await self.api_key_repo.get_api_key_by_hash(token_hash)
        if not api_key or not api_key.is_active:
            return None
        
        # Update last used timestamp
        await self.api_key_repo.update_last_used(api_key.id)
        
        # Return user data with database information
        return {
            "user_id": api_key.user.id,
            "email": api_key.user.email,
            "tier": api_key.user.subscription_tier,
            "api_key_id": api_key.id,
            "api_key_name": api_key.name,
            "created_at": user_data["created_at"],
            "last_used": api_key.last_used.isoformat() if api_key.last_used else None
        }
    
    async def get_user_api_keys(self, user_id: str) -> list[Dict[str, Any]]:
        """Get all API keys for user"""
        api_keys = await self.api_key_repo.get_user_api_keys(user_id)
        
        return [
            {
                "id": key.id,
                "name": key.name,
                "is_active": key.is_active,
                "created_at": key.created_at.isoformat(),
                "last_used": key.last_used.isoformat() if key.last_used else None,
                "expires_at": key.expires_at.isoformat() if key.expires_at else None
            }
            for key in api_keys
        ]
    
    async def deactivate_api_key(self, user_id: str, api_key_id: str) -> bool:
        """Deactivate an API key"""
        # Verify the API key belongs to the user
        api_keys = await self.api_key_repo.get_user_api_keys(user_id)
        if not any(key.id == api_key_id for key in api_keys):
            return False
        
        return await self.api_key_repo.deactivate_api_key(api_key_id)
    
    async def update_subscription(self, user_id: str, tier: str, 
                                 stripe_subscription_id: str = None) -> Subscription:
        """Update user subscription"""
        # Cancel existing active subscription
        existing_subscription = await self.subscription_repo.get_active_subscription(user_id)
        if existing_subscription:
            await self.subscription_repo.cancel_subscription(existing_subscription.id)
        
        # Create new subscription
        subscription = await self.subscription_repo.create_subscription(
            user_id=user_id,
            tier=tier,
            stripe_subscription_id=stripe_subscription_id
        )
        
        logger.info(f"Updated subscription for user {user_id} to {tier}")
        return subscription
    
    async def get_user_subscription(self, user_id: str) -> Optional[Subscription]:
        """Get user's active subscription"""
        return await self.subscription_repo.get_active_subscription(user_id)
    
    async def get_usage_stats(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get user's usage statistics"""
        return await self.usage_repo.get_user_usage_stats(user_id, days)
    
    async def log_api_usage(self, user_id: str, endpoint: str, method: str, 
                           status_code: int, **kwargs) -> None:
        """Log API usage"""
        await self.usage_repo.log_usage(
            user_id=user_id,
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            **kwargs
        )
    
    async def get_user_dashboard_data(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive user dashboard data"""
        user = await self.user_repo.get_user_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        
        # Get user data
        subscription = await self.subscription_repo.get_active_subscription(user_id)
        api_keys = await self.get_user_api_keys(user_id)
        usage_stats = await self.get_usage_stats(user_id, 30)
        
        return {
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "subscription_tier": user.subscription_tier,
                "is_active": user.is_active,
                "is_verified": user.is_verified,
                "created_at": user.created_at.isoformat(),
                "last_login": user.last_login.isoformat() if user.last_login else None
            },
            "subscription": {
                "id": subscription.id,
                "tier": subscription.tier,
                "status": subscription.status,
                "stripe_subscription_id": subscription.stripe_subscription_id,
                "current_period_start": subscription.current_period_start.isoformat() if subscription.current_period_start else None,
                "current_period_end": subscription.current_period_end.isoformat() if subscription.current_period_end else None,
                "created_at": subscription.created_at.isoformat()
            } if subscription else None,
            "api_keys": api_keys,
            "usage_stats": usage_stats
        }