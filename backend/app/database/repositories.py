from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import select, and_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import hashlib
import logging

from app.database.models import User, ApiKey, Subscription, UsageLog, TokenBlacklist
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)


class UserRepository:
    """Repository for user-related database operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.auth_service = AuthService()
    
    async def create_user(self, email: str, password: str = None, full_name: str = None) -> User:
        """Create a new user"""
        # Hash password if provided
        hashed_password = None
        if password:
            hashed_password = self.auth_service.hash_password(password)
        
        user = User(
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            subscription_tier="free"
        )
        
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        
        logger.info(f"Created user: {user.email}")
        return user
    
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        stmt = select(User).where(User.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_user_with_subscriptions(self, user_id: str) -> Optional[User]:
        """Get user with their subscriptions"""
        stmt = select(User).where(User.id == user_id).options(
            selectinload(User.subscriptions)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def update_user(self, user_id: str, **kwargs) -> Optional[User]:
        """Update user information"""
        user = await self.get_user_by_id(user_id)
        if not user:
            return None
        
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
        
        user.updated_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(user)
        
        logger.info(f"Updated user: {user.email}")
        return user
    
    async def update_last_login(self, user_id: str) -> None:
        """Update user's last login timestamp"""
        user = await self.get_user_by_id(user_id)
        if user:
            user.last_login = datetime.utcnow()
            await self.session.commit()
    
    async def deactivate_user(self, user_id: str) -> bool:
        """Deactivate a user account"""
        user = await self.get_user_by_id(user_id)
        if not user:
            return False
        
        user.is_active = False
        user.updated_at = datetime.utcnow()
        await self.session.commit()
        
        logger.info(f"Deactivated user: {user.email}")
        return True
    
    async def verify_password(self, user_id: str, password: str) -> bool:
        """Verify user password"""
        user = await self.get_user_by_id(user_id)
        if not user or not user.hashed_password:
            return False
        
        return self.auth_service.verify_password(password, user.hashed_password)
    
    async def change_password(self, user_id: str, new_password: str) -> bool:
        """Change user password"""
        user = await self.get_user_by_id(user_id)
        if not user:
            return False
        
        user.hashed_password = self.auth_service.hash_password(new_password)
        user.updated_at = datetime.utcnow()
        await self.session.commit()
        
        logger.info(f"Changed password for user: {user.email}")
        return True


class ApiKeyRepository:
    """Repository for API key-related database operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_api_key(self, user_id: str, key_hash: str, name: str) -> ApiKey:
        """Create a new API key"""
        api_key = ApiKey(
            user_id=user_id,
            key_hash=key_hash,
            name=name
        )
        
        self.session.add(api_key)
        await self.session.commit()
        await self.session.refresh(api_key)
        
        logger.info(f"Created API key for user: {user_id}")
        return api_key
    
    async def get_api_key_by_hash(self, key_hash: str) -> Optional[ApiKey]:
        """Get API key by hash"""
        stmt = select(ApiKey).where(
            and_(ApiKey.key_hash == key_hash, ApiKey.is_active == True)
        ).options(selectinload(ApiKey.user))
        
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_user_api_keys(self, user_id: str) -> List[ApiKey]:
        """Get all API keys for a user"""
        stmt = select(ApiKey).where(ApiKey.user_id == user_id).order_by(desc(ApiKey.created_at))
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def update_last_used(self, api_key_id: str) -> None:
        """Update API key last used timestamp"""
        stmt = select(ApiKey).where(ApiKey.id == api_key_id)
        result = await self.session.execute(stmt)
        api_key = result.scalar_one_or_none()
        
        if api_key:
            api_key.last_used = datetime.utcnow()
            await self.session.commit()
    
    async def deactivate_api_key(self, api_key_id: str) -> bool:
        """Deactivate an API key"""
        stmt = select(ApiKey).where(ApiKey.id == api_key_id)
        result = await self.session.execute(stmt)
        api_key = result.scalar_one_or_none()
        
        if api_key:
            api_key.is_active = False
            await self.session.commit()
            logger.info(f"Deactivated API key: {api_key_id}")
            return True
        
        return False
    
    async def cleanup_expired_keys(self) -> int:
        """Clean up expired API keys"""
        now = datetime.utcnow()
        stmt = select(ApiKey).where(
            and_(ApiKey.expires_at.is_not(None), ApiKey.expires_at < now)
        )
        result = await self.session.execute(stmt)
        expired_keys = result.scalars().all()
        
        for key in expired_keys:
            key.is_active = False
        
        await self.session.commit()
        logger.info(f"Cleaned up {len(expired_keys)} expired API keys")
        return len(expired_keys)


class SubscriptionRepository:
    """Repository for subscription-related database operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_subscription(self, user_id: str, tier: str, stripe_subscription_id: str = None) -> Subscription:
        """Create a new subscription"""
        subscription = Subscription(
            user_id=user_id,
            tier=tier,
            stripe_subscription_id=stripe_subscription_id,
            status="active"
        )
        
        self.session.add(subscription)
        
        # Update user's subscription tier
        user_stmt = select(User).where(User.id == user_id)
        user_result = await self.session.execute(user_stmt)
        user = user_result.scalar_one_or_none()
        
        if user:
            user.subscription_tier = tier
            user.updated_at = datetime.utcnow()
        
        await self.session.commit()
        await self.session.refresh(subscription)
        
        logger.info(f"Created subscription for user: {user_id}, tier: {tier}")
        return subscription
    
    async def get_active_subscription(self, user_id: str) -> Optional[Subscription]:
        """Get user's active subscription"""
        stmt = select(Subscription).where(
            and_(
                Subscription.user_id == user_id,
                Subscription.status == "active"
            )
        ).order_by(desc(Subscription.created_at))
        
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_subscription_by_stripe_id(self, stripe_subscription_id: str) -> Optional[Subscription]:
        """Get subscription by Stripe ID"""
        stmt = select(Subscription).where(
            Subscription.stripe_subscription_id == stripe_subscription_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def update_subscription(self, subscription_id: str, **kwargs) -> Optional[Subscription]:
        """Update subscription information"""
        stmt = select(Subscription).where(Subscription.id == subscription_id)
        result = await self.session.execute(stmt)
        subscription = result.scalar_one_or_none()
        
        if not subscription:
            return None
        
        for key, value in kwargs.items():
            if hasattr(subscription, key):
                setattr(subscription, key, value)
        
        subscription.updated_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(subscription)
        
        logger.info(f"Updated subscription: {subscription_id}")
        return subscription
    
    async def cancel_subscription(self, subscription_id: str) -> bool:
        """Cancel a subscription"""
        subscription = await self.update_subscription(
            subscription_id,
            status="canceled",
            canceled_at=datetime.utcnow()
        )
        
        if subscription:
            # Update user's tier to free
            user_stmt = select(User).where(User.id == subscription.user_id)
            user_result = await self.session.execute(user_stmt)
            user = user_result.scalar_one_or_none()
            
            if user:
                user.subscription_tier = "free"
                user.updated_at = datetime.utcnow()
                await self.session.commit()
            
            logger.info(f"Canceled subscription: {subscription_id}")
            return True
        
        return False


class UsageLogRepository:
    """Repository for usage logging"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def log_usage(self, user_id: str, endpoint: str, method: str, status_code: int,
                       ip_address: str = None, user_agent: str = None, 
                       response_time_ms: int = None, error_type: str = None,
                       error_message: str = None) -> UsageLog:
        """Log API usage"""
        usage_log = UsageLog(
            user_id=user_id,
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            ip_address=ip_address,
            user_agent=user_agent,
            response_time_ms=response_time_ms,
            error_type=error_type,
            error_message=error_message
        )
        
        self.session.add(usage_log)
        await self.session.commit()
        return usage_log
    
    async def get_user_usage_stats(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get usage statistics for a user"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Total requests
        total_stmt = select(func.count(UsageLog.id)).where(
            and_(
                UsageLog.user_id == user_id,
                UsageLog.created_at >= cutoff_date
            )
        )
        total_result = await self.session.execute(total_stmt)
        total_requests = total_result.scalar()
        
        # Requests by endpoint
        endpoint_stmt = select(
            UsageLog.endpoint,
            func.count(UsageLog.id).label('count')
        ).where(
            and_(
                UsageLog.user_id == user_id,
                UsageLog.created_at >= cutoff_date
            )
        ).group_by(UsageLog.endpoint)
        
        endpoint_result = await self.session.execute(endpoint_stmt)
        endpoints = {row.endpoint: row.count for row in endpoint_result}
        
        # Error rate
        error_stmt = select(func.count(UsageLog.id)).where(
            and_(
                UsageLog.user_id == user_id,
                UsageLog.created_at >= cutoff_date,
                UsageLog.status_code >= 400
            )
        )
        error_result = await self.session.execute(error_stmt)
        error_count = error_result.scalar()
        
        error_rate = (error_count / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "total_requests": total_requests,
            "endpoints": endpoints,
            "error_count": error_count,
            "error_rate": error_rate,
            "period_days": days
        }
    
    async def cleanup_old_logs(self, days: int = 90) -> int:
        """Clean up old usage logs"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        stmt = select(UsageLog).where(UsageLog.created_at < cutoff_date)
        result = await self.session.execute(stmt)
        old_logs = result.scalars().all()
        
        for log in old_logs:
            await self.session.delete(log)
        
        await self.session.commit()
        logger.info(f"Cleaned up {len(old_logs)} old usage logs")
        return len(old_logs)


class TokenBlacklistRepository:
    """Repository for token blacklist operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def blacklist_token(self, token_jti: str, token_type: str, expires_at: datetime,
                             revoked_by: str = None, reason: str = None) -> TokenBlacklist:
        """Add token to blacklist"""
        blacklisted_token = TokenBlacklist(
            token_jti=token_jti,
            token_type=token_type,
            expires_at=expires_at,
            revoked_by=revoked_by,
            revocation_reason=reason
        )
        
        self.session.add(blacklisted_token)
        await self.session.commit()
        
        logger.info(f"Blacklisted token: {token_jti}")
        return blacklisted_token
    
    async def is_token_blacklisted(self, token_jti: str) -> bool:
        """Check if token is blacklisted"""
        stmt = select(TokenBlacklist).where(
            and_(
                TokenBlacklist.token_jti == token_jti,
                TokenBlacklist.expires_at > datetime.utcnow()
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None
    
    async def cleanup_expired_tokens(self) -> int:
        """Clean up expired blacklisted tokens"""
        now = datetime.utcnow()
        stmt = select(TokenBlacklist).where(TokenBlacklist.expires_at <= now)
        result = await self.session.execute(stmt)
        expired_tokens = result.scalars().all()
        
        for token in expired_tokens:
            await self.session.delete(token)
        
        await self.session.commit()
        logger.info(f"Cleaned up {len(expired_tokens)} expired blacklisted tokens")
        return len(expired_tokens)