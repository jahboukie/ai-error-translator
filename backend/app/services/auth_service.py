import jwt
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from jose import JWTError, jwt as jose_jwt
import logging

from app.config import settings

logger = logging.getLogger(__name__)

class AuthService:
    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 30
        self.refresh_token_expire_days = 30
        
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({"exp": expire, "type": "access"})
        
        try:
            encoded_jwt = jose_jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=self.algorithm)
            return encoded_jwt
        except Exception as e:
            logger.error(f"Error creating access token: {str(e)}")
            raise
    
    def create_refresh_token(self, data: dict) -> str:
        """Create a JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        to_encode.update({"exp": expire, "type": "refresh"})
        
        try:
            encoded_jwt = jose_jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=self.algorithm)
            return encoded_jwt
        except Exception as e:
            logger.error(f"Error creating refresh token: {str(e)}")
            raise
    
    def verify_token(self, token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
        """Verify and decode a JWT token"""
        try:
            payload = jose_jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[self.algorithm])
            
            # Check token type
            if payload.get("type") != token_type:
                logger.warning(f"Invalid token type. Expected: {token_type}, Got: {payload.get('type')}")
                return None
            
            # Check expiration
            if payload.get("exp") < datetime.utcnow().timestamp():
                logger.warning("Token has expired")
                return None
                
            return payload
            
        except JWTError as e:
            logger.error(f"JWT verification failed: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Token verification error: {str(e)}")
            return None
    
    def create_api_key(self, user_id: str, tier: str = "free") -> Dict[str, str]:
        """Create an API key for a user"""
        # Generate a secure random API key
        api_key = secrets.token_urlsafe(32)
        
        # Create JWT token with user info
        token_data = {
            "user_id": user_id,
            "tier": tier,
            "api_key": api_key,
            "created_at": datetime.utcnow().isoformat()
        }
        
        access_token = self.create_access_token(token_data)
        refresh_token = self.create_refresh_token(token_data)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "api_key": api_key,
            "token_type": "bearer"
        }
    
    def validate_api_key(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate an API key token"""
        payload = self.verify_token(token)
        
        if not payload:
            return None
            
        # Extract user information
        return {
            "user_id": payload.get("user_id"),
            "tier": payload.get("tier", "free"),
            "api_key": payload.get("api_key"),
            "created_at": payload.get("created_at")
        }
    
    def refresh_access_token(self, refresh_token: str) -> Optional[Dict[str, str]]:
        """Refresh an access token using a refresh token"""
        payload = self.verify_token(refresh_token, "refresh")
        
        if not payload:
            return None
        
        # Create new access token with same user data
        new_token_data = {
            "user_id": payload.get("user_id"),
            "tier": payload.get("tier"),
            "api_key": payload.get("api_key"),
            "created_at": payload.get("created_at")
        }
        
        new_access_token = self.create_access_token(new_token_data)
        
        return {
            "access_token": new_access_token,
            "token_type": "bearer"
        }
    
    def hash_password(self, password: str) -> str:
        """Hash a password"""
        return self.pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def generate_reset_token(self, user_id: str) -> str:
        """Generate a password reset token"""
        token_data = {
            "user_id": user_id,
            "type": "password_reset",
            "exp": datetime.utcnow() + timedelta(hours=1)  # 1 hour expiry
        }
        
        return jose_jwt.encode(token_data, settings.JWT_SECRET_KEY, algorithm=self.algorithm)
    
    def verify_reset_token(self, token: str) -> Optional[str]:
        """Verify a password reset token and return user_id"""
        try:
            payload = jose_jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[self.algorithm])
            
            if payload.get("type") != "password_reset":
                return None
                
            return payload.get("user_id")
            
        except JWTError:
            return None