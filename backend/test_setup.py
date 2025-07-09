#!/usr/bin/env python3
"""
Simple test to verify our test setup is working correctly
"""

import os
import sys
import subprocess

def test_imports():
    """Test that we can import our main modules"""
    print("Testing imports...")
    
    # Add app to path
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))
    
    try:
        from app.services.auth_service import AuthService
        print("✅ AuthService import successful")
        
        from app.middleware.jwt_authentication import JWTAuthenticationMiddleware
        print("✅ JWTAuthenticationMiddleware import successful")
        
        from app.routes.auth import router
        print("✅ Auth routes import successful")
        
        from app.config import settings
        print("✅ Settings import successful")
        
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_auth_service():
    """Test basic auth service functionality"""
    print("Testing auth service...")
    
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))
        from app.services.auth_service import AuthService
        
        auth_service = AuthService()
        
        # Test token creation
        api_key_data = auth_service.create_api_key("test_user", "pro")
        print("✅ Token creation successful")
        
        # Test token validation
        user_data = auth_service.validate_api_key(api_key_data["access_token"])
        if user_data and user_data["user_id"] == "test_user":
            print("✅ Token validation successful")
        else:
            print("❌ Token validation failed")
            return False
            
        # Test token refresh
        new_token = auth_service.refresh_access_token(api_key_data["refresh_token"])
        if new_token:
            print("✅ Token refresh successful")
        else:
            print("❌ Token refresh failed")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Auth service test failed: {e}")
        return False

def test_configuration():
    """Test configuration loading"""
    print("Testing configuration...")
    
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))
        from app.config import settings
        
        # Test that settings are loaded
        if hasattr(settings, 'JWT_SECRET_KEY'):
            print("✅ JWT_SECRET_KEY configured")
        else:
            print("❌ JWT_SECRET_KEY not configured")
            return False
            
        if hasattr(settings, 'API_SECRET_KEY'):
            print("✅ API_SECRET_KEY configured")
        else:
            print("❌ API_SECRET_KEY not configured")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def test_file_structure():
    """Test that all required files exist"""
    print("Testing file structure...")
    
    required_files = [
        "app/services/auth_service.py",
        "app/middleware/jwt_authentication.py",
        "app/routes/auth.py",
        "app/config.py",
        "app/main.py",
        "tests/unit/test_auth_service.py",
        "tests/integration/test_auth_endpoints.py",
        "tests/e2e/test_auth_flow.py",
        "pytest.ini",
        "run_tests.sh"
    ]
    
    all_exist = True
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path} exists")
        else:
            print(f"❌ {file_path} missing")
            all_exist = False
    
    return all_exist

if __name__ == "__main__":
    print("🧪 Testing AI Error Translator Backend Setup")
    print("=" * 50)
    
    tests = [
        ("File Structure", test_file_structure),
        ("Imports", test_imports),
        ("Configuration", test_configuration),
        ("Auth Service", test_auth_service),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        print("-" * 20)
        result = test_func()
        results.append((test_name, result))
    
    print("\n" + "=" * 50)
    print("Test Results:")
    print("=" * 50)
    
    all_passed = True
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if not result:
            all_passed = False
    
    print("=" * 50)
    
    if all_passed:
        print("🎉 All tests passed! Test setup is ready.")
        print("📝 Run './run_tests.sh' to execute the full test suite.")
    else:
        print("❌ Some tests failed. Please fix the issues above.")
        sys.exit(1)