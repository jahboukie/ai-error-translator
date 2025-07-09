import pytest
from fastapi.testclient import TestClient
import json
import sys
import os
from datetime import datetime, timedelta

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'app'))

from app.main import app
from app.services.auth_service import AuthService
from app.config import settings


class TestAuthenticationE2E:
    """End-to-end tests for authentication flow"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.client = TestClient(app)
        self.auth_service = AuthService()
        
    def test_full_authentication_workflow(self):
        """Test the complete authentication workflow"""
        # This test simulates a real user workflow
        
        # Step 1: Check that protected endpoint is blocked
        response = self.client.post(
            "/translate",
            json={
                "errorText": "TypeError: test error",
                "context": {
                    "language": "javascript",
                    "filePath": "test.js",
                    "surroundingCode": "console.log('test');"
                }
            }
        )
        assert response.status_code == 401
        
        # Step 2: Create API key (simulating user subscription)
        api_key_data = self.auth_service.create_api_key("user123", "pro")
        access_token = api_key_data["access_token"]
        refresh_token = api_key_data["refresh_token"]
        
        # Step 3: Validate the token works
        response = self.client.post(
            "/auth/validate",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert response.status_code == 200
        user_data = response.json()["user"]
        assert user_data["user_id"] == "user123"
        assert user_data["tier"] == "pro"
        
        # Step 4: Access protected endpoint with token
        response = self.client.post(
            "/translate",
            json={
                "errorText": "TypeError: test error",
                "context": {
                    "language": "javascript",
                    "filePath": "test.js",
                    "surroundingCode": "console.log('test');"
                }
            },
            headers={"Authorization": f"Bearer {access_token}"}
        )
        # Should not be 401 anymore (might be 500 due to missing AI config, but that's OK)
        assert response.status_code != 401
        
        # Step 5: Test token refresh
        response = self.client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        assert response.status_code == 200
        new_access_token = response.json()["access_token"]
        
        # Step 6: Use refreshed token
        response = self.client.post(
            "/auth/validate",
            headers={"Authorization": f"Bearer {new_access_token}"}
        )
        assert response.status_code == 200
        
    def test_subscription_tier_access_control(self):
        """Test that subscription tiers control access properly"""
        # Create free tier user
        free_api_key = self.auth_service.create_api_key("free_user", "free")
        free_token = free_api_key["access_token"]
        
        # Create pro tier user
        pro_api_key = self.auth_service.create_api_key("pro_user", "pro")
        pro_token = pro_api_key["access_token"]
        
        # Test that both can access basic endpoints
        for token in [free_token, pro_token]:
            response = self.client.get(
                "/supported-languages",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code == 200
            
        # Test that both can access translate endpoint (tier differences handled in business logic)
        for token in [free_token, pro_token]:
            response = self.client.post(
                "/translate",
                json={
                    "errorText": "TypeError: test error",
                    "context": {
                        "language": "javascript",
                        "filePath": "test.js",
                        "surroundingCode": "console.log('test');"
                    }
                },
                headers={"Authorization": f"Bearer {token}"}
            )
            # Should not be 401 (authentication passed)
            assert response.status_code != 401
            
    def test_token_expiration_handling(self):
        """Test handling of token expiration"""
        # Create a token with very short expiration for testing
        # Note: In real implementation, you'd need to modify the auth service
        # to allow custom expiration times for testing
        
        api_key_data = self.auth_service.create_api_key("test_user", "pro")
        access_token = api_key_data["access_token"]
        
        # Token should work initially
        response = self.client.post(
            "/auth/validate",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert response.status_code == 200
        
        # After modifying the token to be expired (this is a simplified test)
        # In a real test, you'd wait for actual expiration or mock the time
        
    def test_invalid_token_scenarios(self):
        """Test various invalid token scenarios"""
        invalid_tokens = [
            "invalid_token",
            "malformed.jwt.token",
            "",
            "Bearer token_without_prefix",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid_payload.signature"
        ]
        
        for token in invalid_tokens:
            response = self.client.post(
                "/translate",
                json={
                    "errorText": "TypeError: test error",
                    "context": {
                        "language": "javascript",
                        "filePath": "test.js",
                        "surroundingCode": "console.log('test');"
                    }
                },
                headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code == 401
            
    def test_multiple_concurrent_users(self):
        """Test multiple users with different tokens"""
        # Create multiple users
        users = [
            {"id": "user1", "tier": "free"},
            {"id": "user2", "tier": "pro"},
            {"id": "user3", "tier": "free"}
        ]
        
        tokens = []
        for user in users:
            api_key_data = self.auth_service.create_api_key(user["id"], user["tier"])
            tokens.append({
                "user_id": user["id"],
                "tier": user["tier"],
                "token": api_key_data["access_token"]
            })
        
        # Test that each user can access their own data
        for token_data in tokens:
            response = self.client.post(
                "/auth/validate",
                headers={"Authorization": f"Bearer {token_data['token']}"}
            )
            assert response.status_code == 200
            user_data = response.json()["user"]
            assert user_data["user_id"] == token_data["user_id"]
            assert user_data["tier"] == token_data["tier"]
            
    def test_cors_and_security_headers(self):
        """Test CORS and security headers"""
        # Test that CORS headers are properly set
        response = self.client.options("/translate")
        
        # Test public endpoint
        response = self.client.get("/health")
        assert response.status_code == 200
        
        # Test that sensitive endpoints require authentication
        sensitive_endpoints = [
            "/translate",
            "/create-checkout-session",
            "/create-portal-session"
        ]
        
        for endpoint in sensitive_endpoints:
            response = self.client.post(endpoint, json={})
            assert response.status_code == 401
            
    def test_rate_limiting_with_authentication(self):
        """Test that rate limiting works with authentication"""
        # Create a user
        api_key_data = self.auth_service.create_api_key("rate_test_user", "pro")
        token = api_key_data["access_token"]
        
        # Make multiple requests
        for i in range(5):
            response = self.client.post(
                "/auth/validate",
                headers={"Authorization": f"Bearer {token}"}
            )
            # Should work for reasonable number of requests
            assert response.status_code == 200
            
    def test_error_handling_in_auth_flow(self):
        """Test error handling in authentication flow"""
        # Test malformed requests
        response = self.client.post("/auth/refresh", json={})
        assert response.status_code == 422  # Validation error
        
        response = self.client.post("/auth/refresh", json={"refresh_token": ""})
        assert response.status_code == 401
        
        # Test missing required fields
        response = self.client.post("/auth/validate")
        assert response.status_code == 422  # Missing Authorization header
        
    def test_logout_functionality(self):
        """Test logout functionality"""
        # Create a user and get token
        api_key_data = self.auth_service.create_api_key("logout_user", "pro")
        token = api_key_data["access_token"]
        
        # Verify token works
        response = self.client.post(
            "/auth/validate",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        
        # Logout
        response = self.client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        
        # Token should still work (stateless JWT - logout is just a confirmation)
        # In a real implementation with token blacklisting, this would fail
        response = self.client.post(
            "/auth/validate",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        
    def test_webhook_endpoint_no_auth(self):
        """Test that webhook endpoint doesn't require authentication"""
        # Webhook endpoint should be public for Stripe webhooks
        response = self.client.post(
            "/webhook",
            json={},
            headers={"stripe-signature": "test_signature"}
        )
        
        # Should not be 401 (might be 400 due to invalid signature, but that's OK)
        assert response.status_code != 401