#!/usr/bin/env python3
"""
Simple test script to verify JWT authentication is working
"""
import requests
import json
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.services.auth_service import AuthService
from app.config import settings

def test_authentication():
    """Test the authentication flow"""
    
    # Test 1: Create a JWT token
    print("Test 1: Creating JWT token...")
    auth_service = AuthService()
    
    try:
        token_data = auth_service.create_api_key(
            user_id="test_user_123",
            tier="pro"
        )
        print(f"✅ Token created successfully")
        print(f"   Access Token: {token_data['access_token'][:50]}...")
        print(f"   Token Type: {token_data['token_type']}")
        
        # Test 2: Validate the token
        print("\nTest 2: Validating JWT token...")
        user_data = auth_service.validate_api_key(token_data['access_token'])
        
        if user_data:
            print(f"✅ Token validation successful")
            print(f"   User ID: {user_data['user_id']}")
            print(f"   Tier: {user_data['tier']}")
            print(f"   Created: {user_data['created_at']}")
        else:
            print("❌ Token validation failed")
            return False
            
        # Test 3: Test token refresh
        print("\nTest 3: Testing token refresh...")
        new_token_data = auth_service.refresh_access_token(token_data['refresh_token'])
        
        if new_token_data:
            print(f"✅ Token refresh successful")
            print(f"   New Access Token: {new_token_data['access_token'][:50]}...")
        else:
            print("❌ Token refresh failed")
            return False
            
        # Test 4: Test invalid token
        print("\nTest 4: Testing invalid token...")
        invalid_user_data = auth_service.validate_api_key("invalid_token_123")
        
        if invalid_user_data is None:
            print("✅ Invalid token correctly rejected")
        else:
            print("❌ Invalid token was accepted - security issue!")
            return False
            
        print("\n🎉 All authentication tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Authentication test failed: {str(e)}")
        return False

def test_api_endpoints():
    """Test the API endpoints with authentication"""
    
    # Only run this if the server is running
    base_url = "http://localhost:8000"
    
    print(f"\nTesting API endpoints at {base_url}...")
    
    # Test health endpoint (should work without auth)
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Health endpoint accessible without auth")
        else:
            print(f"❌ Health endpoint failed: {response.status_code}")
    except requests.exceptions.RequestException:
        print("⚠️  Server not running - skipping API tests")
        return True
    
    # Test create token endpoint (dev mode only)
    try:
        token_request = {
            "user_id": "test_api_user",
            "tier": "pro"
        }
        
        response = requests.post(
            f"{base_url}/auth/create-token",
            json=token_request,
            timeout=5
        )
        
        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data["access_token"]
            print("✅ Token creation endpoint working")
            
            # Test authenticated endpoint
            headers = {"Authorization": f"Bearer {access_token}"}
            
            # Test translate endpoint (should work with auth)
            translate_request = {
                "errorText": "TypeError: Cannot read property 'length' of undefined",
                "context": {
                    "language": "javascript",
                    "filePath": "test.js",
                    "surroundingCode": "const arr = getData(); console.log(arr.length);"
                }
            }
            
            response = requests.post(
                f"{base_url}/translate",
                json=translate_request,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                print("✅ Authenticated translate endpoint working")
            else:
                print(f"❌ Translate endpoint failed: {response.status_code}")
                print(f"   Response: {response.text}")
                
        else:
            print(f"❌ Token creation failed: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ API test failed: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    print("🔐 Testing JWT Authentication System")
    print("=" * 50)
    
    # Test authentication service
    auth_success = test_authentication()
    
    # Test API endpoints if available
    if auth_success:
        test_api_endpoints()
    
    print("\n" + "=" * 50)
    if auth_success:
        print("✅ Authentication system is working correctly!")
    else:
        print("❌ Authentication system has issues!")
        sys.exit(1)