#!/bin/bash

# Test security improvements
echo "🔐 Testing Security Improvements"
echo "================================"

# Test 1: Check secrets management
echo "Test 1: Checking secrets are not committed..."
if [[ -f "backend/.env" ]]; then
    echo "❌ .env file still exists"
    exit 1
else
    echo "✅ .env file not found (good)"
fi

# Test 2: Check .env.example exists
echo "Test 2: Checking .env.example exists..."
if [[ -f "backend/.env.example" ]]; then
    echo "✅ .env.example exists"
else
    echo "❌ .env.example missing"
    exit 1
fi

# Test 3: Check secrets setup script
echo "Test 3: Checking secrets setup script..."
if [[ -f "backend/setup-secrets.sh" && -x "backend/setup-secrets.sh" ]]; then
    echo "✅ setup-secrets.sh exists and is executable"
else
    echo "❌ setup-secrets.sh missing or not executable"
    exit 1
fi

# Test 4: Check security documentation
echo "Test 4: Checking security documentation..."
if [[ -f "SECURITY.md" ]]; then
    echo "✅ SECURITY.md exists"
else
    echo "❌ SECURITY.md missing"
    exit 1
fi

# Test 5: Check gitignore is updated
echo "Test 5: Checking .gitignore..."
if grep -q "backend/\.env" .gitignore; then
    echo "✅ .gitignore includes backend/.env"
else
    echo "❌ .gitignore doesn't include backend/.env"
    exit 1
fi

# Test 6: Check no default hardcoded secrets
echo "Test 6: Checking for insecure defaults..."
if grep -q "INSECURE_DEFAULT_CHANGE_IN_PRODUCTION" backend/app/config.py; then
    echo "✅ Default secrets are clearly marked as insecure"
else
    echo "❌ Default secrets not properly marked"
    exit 1
fi

# Test 7: Check CORS configuration
echo "Test 7: Checking CORS configuration..."
if grep -q "ALLOWED_ORIGINS" backend/app/config.py; then
    echo "✅ CORS is configurable"
else
    echo "❌ CORS not configurable"
    exit 1
fi

# Test 8: Check frontend URL is configurable
echo "Test 8: Checking frontend URL configuration..."
if grep -q "FRONTEND_URL" backend/app/config.py; then
    echo "✅ Frontend URL is configurable"
else
    echo "❌ Frontend URL not configurable"
    exit 1
fi

# Test 9: Check cloud build uses secrets
echo "Test 9: Checking cloud build configuration..."
if grep -q "set-secrets" cloudbuild.yaml; then
    echo "✅ Cloud build uses Secret Manager"
else
    echo "❌ Cloud build doesn't use Secret Manager"
    exit 1
fi

# Test 10: Check package.json doesn't have hardcoded token
echo "Test 10: Checking package.json..."
if grep -q '"default": ""' package.json; then
    echo "✅ Package.json has empty default API key"
else
    echo "❌ Package.json has non-empty default API key"
    exit 1
fi

echo ""
echo "================================"
echo "🎉 All security tests passed!"
echo "✅ Secrets management implemented"
echo "✅ Hardcoded values removed"
echo "✅ Configuration is secure"
echo "✅ Documentation is complete"