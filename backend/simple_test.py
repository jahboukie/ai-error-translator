#!/usr/bin/env python3
"""
Simple test to verify JWT token structure without dependencies
"""
import json
import base64
import sys
import os

def decode_jwt_payload(token):
    """Decode JWT payload without verification (for testing only)"""
    try:
        # Split the token into parts
        parts = token.split('.')
        if len(parts) != 3:
            return None
            
        # Decode the payload (second part)
        payload = parts[1]
        
        # Add padding if needed
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += '=' * padding
            
        # Decode base64
        decoded = base64.b64decode(payload)
        
        # Parse JSON
        return json.loads(decoded)
    except Exception as e:
        print(f"Error decoding JWT: {e}")
        return None

def test_jwt_structure():
    """Test JWT structure without external dependencies"""
    
    # Test if we can create a simple JWT-like token
    print("Testing JWT token structure...")
    
    # Create a simple payload
    payload = {
        "user_id": "test_user",
        "tier": "pro",
        "exp": 1234567890,
        "type": "access"
    }
    
    # Encode as base64 (simplified - not a real JWT)
    import json
    payload_json = json.dumps(payload)
    payload_b64 = base64.b64encode(payload_json.encode()).decode()
    
    # Create a mock JWT token (header.payload.signature)
    header = base64.b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).decode()
    signature = "mock_signature"
    
    mock_token = f"{header}.{payload_b64}.{signature}"
    
    print(f"Mock JWT token: {mock_token[:50]}...")
    
    # Test decoding
    decoded = decode_jwt_payload(mock_token)
    if decoded:
        print("✅ JWT structure test passed")
        print(f"   Decoded payload: {decoded}")
        return True
    else:
        print("❌ JWT structure test failed")
        return False

def test_file_structure():
    """Test if all required files exist"""
    
    required_files = [
        "app/services/auth_service.py",
        "app/middleware/jwt_authentication.py",
        "app/routes/auth.py",
        "app/config.py",
        "app/main.py"
    ]
    
    print("Testing file structure...")
    
    all_exist = True
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path} exists")
        else:
            print(f"❌ {file_path} missing")
            all_exist = False
    
    return all_exist

def test_config_structure():
    """Test if config has JWT settings"""
    
    print("Testing configuration...")
    
    try:
        with open("app/config.py", "r") as f:
            config_content = f.read()
            
        if "JWT_SECRET_KEY" in config_content:
            print("✅ JWT_SECRET_KEY found in config")
        else:
            print("❌ JWT_SECRET_KEY missing from config")
            return False
            
        if "API_SECRET_KEY" in config_content:
            print("✅ API_SECRET_KEY found in config")
        else:
            print("❌ API_SECRET_KEY missing from config")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Error reading config: {e}")
        return False

if __name__ == "__main__":
    print("🔐 Testing JWT Authentication Setup")
    print("=" * 50)
    
    # Test file structure
    files_ok = test_file_structure()
    
    # Test config structure
    config_ok = test_config_structure()
    
    # Test JWT structure
    jwt_ok = test_jwt_structure()
    
    print("\n" + "=" * 50)
    
    if files_ok and config_ok and jwt_ok:
        print("✅ Basic authentication setup is correct!")
        print("🚀 Ready to start the server and test with dependencies")
    else:
        print("❌ Authentication setup has issues!")
        sys.exit(1)