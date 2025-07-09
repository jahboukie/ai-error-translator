import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import os
import sys

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'app'))

from app.services.auth_service import AuthService
from app.config import settings


class TestAuthService:
    """Test cases for the AuthService class"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.auth_service = AuthService()
        self.test_user_id = "test_user_123"
        self.test_tier = "pro"
        
    def test_create_access_token(self):
        """Test creating an access token"""
        data = {"user_id": self.test_user_id, "tier": self.test_tier}
        token = self.auth_service.create_access_token(data)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are typically long
        assert "." in token  # JWT tokens have dots
        
    def test_create_refresh_token(self):
        """Test creating a refresh token"""
        data = {"user_id": self.test_user_id, "tier": self.test_tier}
        token = self.auth_service.create_refresh_token(data)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50
        assert "." in token
        
    def test_verify_valid_token(self):
        """Test verifying a valid access token"""
        data = {"user_id": self.test_user_id, "tier": self.test_tier}
        token = self.auth_service.create_access_token(data)
        
        payload = self.auth_service.verify_token(token)
        
        assert payload is not None
        assert payload["user_id"] == self.test_user_id
        assert payload["tier"] == self.test_tier
        assert payload["type"] == "access"
        
    def test_verify_invalid_token(self):
        """Test verifying an invalid token"""
        invalid_token = "invalid.token.here"
        
        payload = self.auth_service.verify_token(invalid_token)
        
        assert payload is None
        
    def test_verify_expired_token(self):
        """Test verifying an expired token"""
        data = {"user_id": self.test_user_id, "tier": self.test_tier}
        # Create token with very short expiration
        token = self.auth_service.create_access_token(
            data, 
            expires_delta=timedelta(microseconds=1)
        )
        
        # Wait a bit and verify token is expired
        import time
        time.sleep(0.01)
        
        payload = self.auth_service.verify_token(token)
        
        assert payload is None
        
    def test_verify_wrong_token_type(self):
        """Test verifying token with wrong type"""
        data = {"user_id": self.test_user_id, "tier": self.test_tier}
        refresh_token = self.auth_service.create_refresh_token(data)
        
        # Try to verify refresh token as access token
        payload = self.auth_service.verify_token(refresh_token, "access")
        
        assert payload is None
        
    def test_create_api_key(self):
        """Test creating an API key"""
        api_key_data = self.auth_service.create_api_key(
            user_id=self.test_user_id,
            tier=self.test_tier
        )
        
        assert "access_token" in api_key_data
        assert "refresh_token" in api_key_data
        assert "api_key" in api_key_data
        assert "token_type" in api_key_data
        assert api_key_data["token_type"] == "bearer"
        
        # Verify the access token contains correct data
        payload = self.auth_service.verify_token(api_key_data["access_token"])
        assert payload["user_id"] == self.test_user_id
        assert payload["tier"] == self.test_tier
        assert payload["api_key"] == api_key_data["api_key"]
        
    def test_validate_api_key(self):
        """Test validating an API key"""
        api_key_data = self.auth_service.create_api_key(
            user_id=self.test_user_id,
            tier=self.test_tier
        )
        
        user_data = self.auth_service.validate_api_key(api_key_data["access_token"])
        
        assert user_data is not None
        assert user_data["user_id"] == self.test_user_id
        assert user_data["tier"] == self.test_tier
        assert user_data["api_key"] == api_key_data["api_key"]
        assert "created_at" in user_data
        
    def test_validate_invalid_api_key(self):
        """Test validating an invalid API key"""
        invalid_key = "invalid_key_123"
        
        user_data = self.auth_service.validate_api_key(invalid_key)
        
        assert user_data is None
        
    def test_refresh_access_token(self):
        """Test refreshing an access token"""
        api_key_data = self.auth_service.create_api_key(
            user_id=self.test_user_id,
            tier=self.test_tier
        )
        
        new_token_data = self.auth_service.refresh_access_token(
            api_key_data["refresh_token"]
        )
        
        assert new_token_data is not None
        assert "access_token" in new_token_data
        assert "token_type" in new_token_data
        assert new_token_data["token_type"] == "bearer"
        
        # Verify new token contains same user data
        payload = self.auth_service.verify_token(new_token_data["access_token"])
        assert payload["user_id"] == self.test_user_id
        assert payload["tier"] == self.test_tier
        
    def test_refresh_with_invalid_token(self):
        """Test refreshing with an invalid refresh token"""
        invalid_refresh_token = "invalid_refresh_token"
        
        new_token_data = self.auth_service.refresh_access_token(invalid_refresh_token)
        
        assert new_token_data is None
        
    def test_refresh_with_access_token(self):
        """Test refreshing with an access token (should fail)"""
        api_key_data = self.auth_service.create_api_key(
            user_id=self.test_user_id,
            tier=self.test_tier
        )
        
        # Try to refresh with access token instead of refresh token
        new_token_data = self.auth_service.refresh_access_token(
            api_key_data["access_token"]
        )
        
        assert new_token_data is None
        
    def test_hash_password(self):
        """Test password hashing"""
        password = "test_password_123"
        hashed = self.auth_service.hash_password(password)
        
        assert hashed is not None
        assert hashed != password
        assert len(hashed) > 50  # Bcrypt hashes are long
        
    def test_verify_password(self):
        """Test password verification"""
        password = "test_password_123"
        hashed = self.auth_service.hash_password(password)
        
        # Test correct password
        assert self.auth_service.verify_password(password, hashed) is True
        
        # Test incorrect password
        assert self.auth_service.verify_password("wrong_password", hashed) is False
        
    def test_generate_reset_token(self):
        """Test generating a password reset token"""
        reset_token = self.auth_service.generate_reset_token(self.test_user_id)
        
        assert reset_token is not None
        assert isinstance(reset_token, str)
        assert len(reset_token) > 50
        
    def test_verify_reset_token(self):
        """Test verifying a password reset token"""
        reset_token = self.auth_service.generate_reset_token(self.test_user_id)
        
        user_id = self.auth_service.verify_reset_token(reset_token)
        
        assert user_id == self.test_user_id
        
    def test_verify_invalid_reset_token(self):
        """Test verifying an invalid reset token"""
        invalid_token = "invalid_reset_token"
        
        user_id = self.auth_service.verify_reset_token(invalid_token)
        
        assert user_id is None
        
    def test_verify_wrong_type_reset_token(self):
        """Test verifying an access token as reset token"""
        data = {"user_id": self.test_user_id, "tier": self.test_tier}
        access_token = self.auth_service.create_access_token(data)
        
        user_id = self.auth_service.verify_reset_token(access_token)
        
        assert user_id is None
        
    def test_token_expiration_times(self):
        """Test that tokens have correct expiration times"""
        data = {"user_id": self.test_user_id, "tier": self.test_tier}
        
        # Create tokens and verify their expiration
        access_token = self.auth_service.create_access_token(data)
        refresh_token = self.auth_service.create_refresh_token(data)
        
        access_payload = self.auth_service.verify_token(access_token)
        refresh_payload = self.auth_service.verify_token(refresh_token, "refresh")
        
        # Access token should expire before refresh token
        assert access_payload["exp"] < refresh_payload["exp"]
        
    def test_api_key_uniqueness(self):
        """Test that API keys are unique"""
        key1 = self.auth_service.create_api_key(self.test_user_id, "free")
        key2 = self.auth_service.create_api_key(self.test_user_id, "pro")
        
        assert key1["api_key"] != key2["api_key"]
        assert key1["access_token"] != key2["access_token"]
        
    @patch('app.services.auth_service.jose_jwt')
    def test_jwt_error_handling(self, mock_jwt):
        """Test JWT error handling"""
        mock_jwt.encode.side_effect = Exception("JWT encoding failed")
        
        data = {"user_id": self.test_user_id, "tier": self.test_tier}
        
        with pytest.raises(Exception):
            self.auth_service.create_access_token(data)
            
    def test_tier_validation(self):
        """Test that different tiers are properly handled"""
        tiers = ["free", "pro", "enterprise"]
        
        for tier in tiers:
            api_key_data = self.auth_service.create_api_key(
                user_id=f"user_{tier}",
                tier=tier
            )
            
            user_data = self.auth_service.validate_api_key(api_key_data["access_token"])
            assert user_data["tier"] == tier