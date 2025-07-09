import pytest
from fastapi.testclient import TestClient
import json
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'app'))

from app.main import app
from app.services.auth_service import AuthService


class TestAuthEndpoints:
    """Integration tests for authentication endpoints"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.client = TestClient(app)
        self.auth_service = AuthService()
        
    def test_create_token_endpoint(self):
        """Test the create token endpoint"""
        # This endpoint should only work in debug mode
        request_data = {
            "user_id": "test_user",
            "tier": "pro"
        }
        
        response = self.client.post("/auth/create-token", json=request_data)
        
        # Check if we're in debug mode
        if response.status_code == 200:
            data = response.json()
            assert "access_token" in data
            assert "refresh_token" in data
            assert "token_type" in data
            assert data["token_type"] == "bearer"
            assert "expires_in" in data
        else:
            # In production mode, should return 404
            assert response.status_code == 404
            
    def test_validate_token_endpoint(self):
        """Test the validate token endpoint"""
        # First create a token
        api_key_data = self.auth_service.create_api_key("test_user", "pro")
        token = api_key_data["access_token"]
        
        # Test valid token
        response = self.client.post(
            "/auth/validate",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert "user" in data
        assert data["user"]["user_id"] == "test_user"
        assert data["user"]["tier"] == "pro"
        
    def test_validate_invalid_token_endpoint(self):
        """Test the validate token endpoint with invalid token"""
        response = self.client.post(
            "/auth/validate",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code == 401
        data = response.json()
        assert "error" in data or "detail" in data
        
    def test_refresh_token_endpoint(self):
        """Test the refresh token endpoint"""
        # First create a token
        api_key_data = self.auth_service.create_api_key("test_user", "pro")
        refresh_token = api_key_data["refresh_token"]
        
        # Test refresh
        response = self.client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
        
    def test_refresh_invalid_token_endpoint(self):
        """Test the refresh token endpoint with invalid token"""
        response = self.client.post(
            "/auth/refresh",
            json={"refresh_token": "invalid_refresh_token"}
        )
        
        assert response.status_code == 401
        data = response.json()
        assert "error" in data or "detail" in data
        
    def test_logout_endpoint(self):
        """Test the logout endpoint"""
        # Create a token first
        api_key_data = self.auth_service.create_api_key("test_user", "pro")
        token = api_key_data["access_token"]
        
        response = self.client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        
    def test_register_endpoint_not_implemented(self):
        """Test that register endpoint returns not implemented"""
        response = self.client.post(
            "/auth/register",
            json={
                "email": "test@example.com",
                "password": "password123"
            }
        )
        
        assert response.status_code == 501
        data = response.json()
        assert "not yet implemented" in data["detail"]
        
    def test_login_endpoint_not_implemented(self):
        """Test that login endpoint returns not implemented"""
        response = self.client.post(
            "/auth/login",
            json={
                "email": "test@example.com",
                "password": "password123"
            }
        )
        
        assert response.status_code == 501
        data = response.json()
        assert "not yet implemented" in data["detail"]
        
    def test_forgot_password_endpoint_not_implemented(self):
        """Test that forgot password endpoint returns not implemented"""
        response = self.client.post(
            "/auth/forgot-password",
            json={"email": "test@example.com"}
        )
        
        assert response.status_code == 501
        data = response.json()
        assert "not yet implemented" in data["detail"]
        
    def test_reset_password_endpoint_not_implemented(self):
        """Test that reset password endpoint returns not implemented"""
        response = self.client.post(
            "/auth/reset-password",
            json={
                "token": "reset_token",
                "new_password": "new_password123"
            }
        )
        
        assert response.status_code == 501
        data = response.json()
        assert "not yet implemented" in data["detail"]


class TestProtectedEndpoints:
    """Test protected endpoints with authentication"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.client = TestClient(app)
        self.auth_service = AuthService()
        
    def test_translate_endpoint_without_auth(self):
        """Test translate endpoint without authentication"""
        response = self.client.post(
            "/translate",
            json={
                "errorText": "TypeError: Cannot read property 'length' of undefined",
                "context": {
                    "language": "javascript",
                    "filePath": "test.js",
                    "surroundingCode": "const arr = getData(); console.log(arr.length);"
                }
            }
        )
        
        assert response.status_code == 401
        
    def test_translate_endpoint_with_auth(self):
        """Test translate endpoint with authentication"""
        # Create a token
        api_key_data = self.auth_service.create_api_key("test_user", "pro")
        token = api_key_data["access_token"]
        
        response = self.client.post(
            "/translate",
            json={
                "errorText": "TypeError: Cannot read property 'length' of undefined",
                "context": {
                    "language": "javascript",
                    "filePath": "test.js",
                    "surroundingCode": "const arr = getData(); console.log(arr.length);"
                }
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # This might fail due to missing AI service configuration, but it should not be a 401
        assert response.status_code != 401
        
    def test_health_endpoint_public(self):
        """Test that health endpoint is public"""
        response = self.client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        
    def test_pricing_endpoint_public(self):
        """Test that pricing endpoint is public"""
        response = self.client.get("/pricing")
        
        assert response.status_code == 200
        data = response.json()
        assert "plans" in data
        
    def test_supported_languages_endpoint_public(self):
        """Test that supported languages endpoint is public"""
        response = self.client.get("/supported-languages")
        
        assert response.status_code == 200
        data = response.json()
        assert "languages" in data
        
    def test_docs_endpoint_public(self):
        """Test that docs endpoint is public"""
        response = self.client.get("/docs")
        
        assert response.status_code == 200
        
    def test_root_endpoint_public(self):
        """Test that root endpoint is public"""
        response = self.client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        
    def test_create_checkout_session_without_auth(self):
        """Test create checkout session endpoint without authentication"""
        response = self.client.post(
            "/create-checkout-session",
            json={
                "price_id": "price_123",
                "customer_email": "test@example.com"
            }
        )
        
        assert response.status_code == 401
        
    def test_create_portal_session_without_auth(self):
        """Test create portal session endpoint without authentication"""
        response = self.client.post(
            "/create-portal-session",
            json={
                "customer_id": "cus_123"
            }
        )
        
        assert response.status_code == 401


class TestTokenFlow:
    """Test complete token flow scenarios"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.client = TestClient(app)
        self.auth_service = AuthService()
        
    def test_complete_token_flow(self):
        """Test complete token creation, validation, and refresh flow"""
        # Step 1: Create a token
        api_key_data = self.auth_service.create_api_key("test_user", "pro")
        access_token = api_key_data["access_token"]
        refresh_token = api_key_data["refresh_token"]
        
        # Step 2: Validate the token
        response = self.client.post(
            "/auth/validate",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert response.status_code == 200
        
        # Step 3: Use the token to access protected endpoint
        response = self.client.get(
            "/health",  # Health is public, but let's use it to test headers
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert response.status_code == 200
        
        # Step 4: Refresh the token
        response = self.client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        assert response.status_code == 200
        
        new_access_token = response.json()["access_token"]
        
        # Step 5: Validate the new token
        response = self.client.post(
            "/auth/validate",
            headers={"Authorization": f"Bearer {new_access_token}"}
        )
        assert response.status_code == 200
        
    def test_token_validation_edge_cases(self):
        """Test token validation edge cases"""
        # Test with malformed token
        response = self.client.post(
            "/auth/validate",
            headers={"Authorization": "Bearer malformed.token"}
        )
        assert response.status_code == 401
        
        # Test with missing Bearer prefix
        response = self.client.post(
            "/auth/validate",
            headers={"Authorization": "token123"}
        )
        assert response.status_code == 401
        
        # Test with empty token
        response = self.client.post(
            "/auth/validate",
            headers={"Authorization": "Bearer "}
        )
        assert response.status_code == 401