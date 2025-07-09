import pytest
from unittest.mock import Mock, patch, AsyncMock
import json
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'app'))

from app.middleware.jwt_authentication import JWTAuthenticationMiddleware, get_current_user, require_tier
from app.services.auth_service import AuthService
from fastapi import HTTPException, Request
from starlette.responses import JSONResponse


class TestJWTAuthenticationMiddleware:
    """Test cases for JWT authentication middleware"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.mock_app = Mock()
        self.middleware = JWTAuthenticationMiddleware(self.mock_app)
        self.auth_service = AuthService()
        
    def create_mock_request(self, path="/", method="GET", headers=None):
        """Create a mock request object"""
        mock_request = Mock(spec=Request)
        mock_request.url.path = path
        mock_request.method = method
        mock_request.headers = headers or {}
        mock_request.state = Mock()
        return mock_request
        
    @pytest.mark.asyncio
    async def test_public_endpoint_no_auth(self):
        """Test that public endpoints don't require authentication"""
        public_endpoints = ["/", "/health", "/docs", "/pricing"]
        
        for endpoint in public_endpoints:
            request = self.create_mock_request(path=endpoint)
            
            # Mock the next function
            async def mock_call_next(req):
                return JSONResponse({"message": "success"})
            
            response = await self.middleware.dispatch(request, mock_call_next)
            
            assert response.status_code == 200
            
    @pytest.mark.asyncio
    async def test_options_request_no_auth(self):
        """Test that OPTIONS requests don't require authentication"""
        request = self.create_mock_request(path="/translate", method="OPTIONS")
        
        async def mock_call_next(req):
            return JSONResponse({"message": "success"})
        
        response = await self.middleware.dispatch(request, mock_call_next)
        
        assert response.status_code == 200
        
    @pytest.mark.asyncio
    async def test_missing_auth_header(self):
        """Test request without Authorization header"""
        request = self.create_mock_request(path="/translate")
        
        async def mock_call_next(req):
            return JSONResponse({"message": "success"})
        
        response = await self.middleware.dispatch(request, mock_call_next)
        
        assert response.status_code == 401
        response_data = json.loads(response.body)
        assert response_data["error"]["code"] == "MISSING_AUTH_HEADER"
        
    @pytest.mark.asyncio
    async def test_invalid_auth_header_format(self):
        """Test request with invalid Authorization header format"""
        request = self.create_mock_request(
            path="/translate",
            headers={"Authorization": "InvalidFormat token123"}
        )
        
        async def mock_call_next(req):
            return JSONResponse({"message": "success"})
        
        response = await self.middleware.dispatch(request, mock_call_next)
        
        assert response.status_code == 401
        response_data = json.loads(response.body)
        assert response_data["error"]["code"] == "MISSING_AUTH_HEADER"
        
    @pytest.mark.asyncio
    async def test_valid_token_authentication(self):
        """Test successful authentication with valid token"""
        # Create a valid token
        api_key_data = self.auth_service.create_api_key("test_user", "pro")
        token = api_key_data["access_token"]
        
        request = self.create_mock_request(
            path="/translate",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        async def mock_call_next(req):
            # Check that user data was added to request state
            assert hasattr(req.state, 'user_id')
            assert hasattr(req.state, 'user_tier')
            assert req.state.user_id == "test_user"
            assert req.state.user_tier == "pro"
            return JSONResponse({"message": "success"})
        
        response = await self.middleware.dispatch(request, mock_call_next)
        
        assert response.status_code == 200
        
    @pytest.mark.asyncio
    async def test_invalid_token_authentication(self):
        """Test authentication with invalid token"""
        request = self.create_mock_request(
            path="/translate",
            headers={"Authorization": "Bearer invalid_token_123"}
        )
        
        async def mock_call_next(req):
            return JSONResponse({"message": "success"})
        
        response = await self.middleware.dispatch(request, mock_call_next)
        
        assert response.status_code == 401
        response_data = json.loads(response.body)
        assert response_data["error"]["code"] == "INVALID_TOKEN"
        
    @pytest.mark.asyncio
    async def test_expired_token_authentication(self):
        """Test authentication with expired token"""
        from datetime import timedelta
        
        # Create a token with very short expiration
        api_key_data = self.auth_service.create_api_key("test_user", "pro")
        # Since we can't create expired tokens directly, we'll mock the validation
        
        request = self.create_mock_request(
            path="/translate",
            headers={"Authorization": f"Bearer {api_key_data['access_token']}"}
        )
        
        # Mock the auth service to return None (expired token)
        with patch.object(self.middleware.auth_service, 'validate_api_key', return_value=None):
            async def mock_call_next(req):
                return JSONResponse({"message": "success"})
            
            response = await self.middleware.dispatch(request, mock_call_next)
            
            assert response.status_code == 401
            response_data = json.loads(response.body)
            assert response_data["error"]["code"] == "INVALID_TOKEN"
            
    @pytest.mark.asyncio
    async def test_authentication_exception_handling(self):
        """Test handling of authentication exceptions"""
        request = self.create_mock_request(
            path="/translate",
            headers={"Authorization": "Bearer valid_token"}
        )
        
        # Mock the auth service to raise an exception
        with patch.object(self.middleware.auth_service, 'validate_api_key', side_effect=Exception("Auth error")):
            async def mock_call_next(req):
                return JSONResponse({"message": "success"})
            
            response = await self.middleware.dispatch(request, mock_call_next)
            
            assert response.status_code == 401
            response_data = json.loads(response.body)
            assert response_data["error"]["code"] == "AUTH_ERROR"
            
    @pytest.mark.asyncio
    async def test_debug_endpoints(self):
        """Test that debug endpoints work in debug mode"""
        request = self.create_mock_request(path="/dev/create-token")
        
        # Mock debug mode
        with patch('app.middleware.jwt_authentication.settings.API_DEBUG', True):
            async def mock_call_next(req):
                return JSONResponse({"message": "success"})
            
            response = await self.middleware.dispatch(request, mock_call_next)
            
            assert response.status_code == 200


class TestGetCurrentUser:
    """Test cases for get_current_user dependency"""
    
    def test_get_current_user_success(self):
        """Test getting current user from request state"""
        mock_request = Mock()
        mock_request.state.user_id = "test_user"
        mock_request.state.user_tier = "pro"
        mock_request.state.api_key = "test_key"
        mock_request.state.token_created_at = "2023-01-01T00:00:00"
        
        user = get_current_user(mock_request)
        
        assert user["user_id"] == "test_user"
        assert user["tier"] == "pro"
        assert user["api_key"] == "test_key"
        assert user["created_at"] == "2023-01-01T00:00:00"
        
    def test_get_current_user_not_authenticated(self):
        """Test getting current user when not authenticated"""
        mock_request = Mock()
        # Mock request without user_id attribute
        if hasattr(mock_request.state, 'user_id'):
            delattr(mock_request.state, 'user_id')
        
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(mock_request)
        
        assert exc_info.value.status_code == 401
        assert "not authenticated" in str(exc_info.value.detail)


class TestRequireTier:
    """Test cases for require_tier dependency"""
    
    def test_require_tier_success(self):
        """Test successful tier requirement check"""
        mock_request = Mock()
        mock_request.state.user_id = "test_user"
        mock_request.state.user_tier = "pro"
        mock_request.state.api_key = "test_key"
        mock_request.state.token_created_at = "2023-01-01T00:00:00"
        
        require_pro = require_tier("pro")
        user = require_pro(mock_request)
        
        assert user["tier"] == "pro"
        
    def test_require_tier_insufficient(self):
        """Test tier requirement with insufficient tier"""
        mock_request = Mock()
        mock_request.state.user_id = "test_user"
        mock_request.state.user_tier = "free"
        mock_request.state.api_key = "test_key"
        mock_request.state.token_created_at = "2023-01-01T00:00:00"
        
        require_pro = require_tier("pro")
        
        with pytest.raises(HTTPException) as exc_info:
            require_pro(mock_request)
        
        assert exc_info.value.status_code == 403
        assert "requires pro tier" in str(exc_info.value.detail)
        
    def test_require_tier_hierarchy(self):
        """Test tier hierarchy (pro can access free content)"""
        mock_request = Mock()
        mock_request.state.user_id = "test_user"
        mock_request.state.user_tier = "pro"
        mock_request.state.api_key = "test_key"
        mock_request.state.token_created_at = "2023-01-01T00:00:00"
        
        require_free = require_tier("free")
        user = require_free(mock_request)
        
        assert user["tier"] == "pro"  # Pro user can access free content
        
    def test_require_tier_not_authenticated(self):
        """Test tier requirement when not authenticated"""
        mock_request = Mock()
        # Mock request without user_id attribute
        if hasattr(mock_request.state, 'user_id'):
            delattr(mock_request.state, 'user_id')
        
        require_pro = require_tier("pro")
        
        with pytest.raises(HTTPException) as exc_info:
            require_pro(mock_request)
        
        assert exc_info.value.status_code == 401