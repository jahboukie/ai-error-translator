#!/usr/bin/env python3
"""
Test script for database functionality
"""
import asyncio
import sys
import os
import tempfile
from typing import Optional

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.database.connection import db_manager
from app.services.user_service import UserService
from app.config import settings


async def test_database_connection():
    """Test database connection"""
    print("Testing database connection...")
    
    try:
        healthy = await db_manager.health_check()
        if healthy:
            print("✅ Database connection successful")
            return True
        else:
            print("❌ Database connection failed")
            return False
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return False


async def test_user_operations():
    """Test user CRUD operations"""
    print("\nTesting user operations...")
    
    try:
        async with db_manager.get_session() as session:
            user_service = UserService(session)
            
            # Test 1: Create user
            print("  Creating test user...")
            user = await user_service.create_user(
                email="test@example.com",
                password="test_password_123",
                full_name="Test User"
            )
            print(f"  ✅ User created: {user.id}")
            
            # Test 2: Get user by email
            print("  Getting user by email...")
            retrieved_user = await user_service.get_user_by_email("test@example.com")
            assert retrieved_user is not None
            assert retrieved_user.email == "test@example.com"
            print("  ✅ User retrieved successfully")
            
            # Test 3: Authenticate user
            print("  Testing authentication...")
            auth_user = await user_service.authenticate_user("test@example.com", "test_password_123")
            assert auth_user is not None
            print("  ✅ Authentication successful")
            
            # Test 4: Create API key
            print("  Creating API key...")
            api_key_data = await user_service.create_api_key(user.id, "Test API Key")
            assert "access_token" in api_key_data
            print("  ✅ API key created")
            
            # Test 5: Validate API key
            print("  Validating API key...")
            user_data = await user_service.validate_api_key(api_key_data["access_token"])
            assert user_data is not None
            assert user_data["user_id"] == user.id
            print("  ✅ API key validation successful")
            
            # Test 6: Get user API keys
            print("  Getting user API keys...")
            api_keys = await user_service.get_user_api_keys(user.id)
            assert len(api_keys) >= 1
            print(f"  ✅ Found {len(api_keys)} API keys")
            
            # Test 7: Update user profile
            print("  Updating user profile...")
            updated_user = await user_service.update_user_profile(
                user.id,
                full_name="Updated Test User"
            )
            assert updated_user.full_name == "Updated Test User"
            print("  ✅ User profile updated")
            
            # Test 8: Change password
            print("  Changing password...")
            success = await user_service.change_password(
                user.id,
                "test_password_123",
                "new_password_456"
            )
            assert success
            print("  ✅ Password changed")
            
            # Test 9: Get usage stats
            print("  Getting usage stats...")
            usage_stats = await user_service.get_usage_stats(user.id)
            assert "total_requests" in usage_stats
            print("  ✅ Usage stats retrieved")
            
            # Test 10: Get dashboard data
            print("  Getting dashboard data...")
            dashboard_data = await user_service.get_user_dashboard_data(user.id)
            assert "user" in dashboard_data
            assert "api_keys" in dashboard_data
            assert "usage_stats" in dashboard_data
            print("  ✅ Dashboard data retrieved")
            
            print("\n🎉 All user operations tests passed!")
            return True
            
    except Exception as e:
        print(f"❌ User operations test failed: {e}")
        return False


async def test_subscription_operations():
    """Test subscription operations"""
    print("\nTesting subscription operations...")
    
    try:
        async with db_manager.get_session() as session:
            user_service = UserService(session)
            
            # Create a test user first
            user = await user_service.create_user(
                email="subscription_test@example.com",
                password="password123"
            )
            
            # Test subscription update
            print("  Creating subscription...")
            subscription = await user_service.update_subscription(
                user.id,
                "pro",
                "sub_test_stripe_id"
            )
            assert subscription.tier == "pro"
            print("  ✅ Subscription created")
            
            # Test getting subscription
            print("  Getting subscription...")
            retrieved_sub = await user_service.get_user_subscription(user.id)
            assert retrieved_sub is not None
            assert retrieved_sub.tier == "pro"
            print("  ✅ Subscription retrieved")
            
            print("\n🎉 All subscription operations tests passed!")
            return True
            
    except Exception as e:
        print(f"❌ Subscription operations test failed: {e}")
        return False


async def test_usage_logging():
    """Test usage logging operations"""
    print("\nTesting usage logging...")
    
    try:
        async with db_manager.get_session() as session:
            user_service = UserService(session)
            
            # Create a test user first
            user = await user_service.create_user(
                email="usage_test@example.com",
                password="password123"
            )
            
            # Test logging usage
            print("  Logging API usage...")
            await user_service.log_api_usage(
                user_id=user.id,
                endpoint="/translate",
                method="POST",
                status_code=200,
                ip_address="127.0.0.1",
                user_agent="Test Agent",
                response_time_ms=150
            )
            print("  ✅ Usage logged")
            
            # Test getting usage stats
            print("  Getting usage statistics...")
            usage_stats = await user_service.get_usage_stats(user.id)
            assert usage_stats["total_requests"] >= 1
            print("  ✅ Usage statistics retrieved")
            
            print("\n🎉 All usage logging tests passed!")
            return True
            
    except Exception as e:
        print(f"❌ Usage logging test failed: {e}")
        return False


async def cleanup_test_data():
    """Clean up test data"""
    print("\nCleaning up test data...")
    
    try:
        async with db_manager.get_session() as session:
            from app.database.repositories import UserRepository
            user_repo = UserRepository(session)
            
            # Delete test users
            test_emails = [
                "test@example.com",
                "subscription_test@example.com",
                "usage_test@example.com"
            ]
            
            for email in test_emails:
                user = await user_repo.get_user_by_email(email)
                if user:
                    await user_repo.deactivate_user(user.id)
            
            print("✅ Test data cleaned up")
            return True
            
    except Exception as e:
        print(f"❌ Cleanup failed: {e}")
        return False


async def main():
    """Main test function"""
    print("🧪 AI Error Translator Database Tests")
    print("=" * 50)
    
    # Test database connection
    if not await test_database_connection():
        print("❌ Database connection failed. Cannot proceed with tests.")
        return
    
    # Run tests
    tests = [
        ("User Operations", test_user_operations),
        ("Subscription Operations", test_subscription_operations),
        ("Usage Logging", test_usage_logging),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Running {test_name} Tests")
        print('='*50)
        
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test failed with exception: {e}")
            results.append((test_name, False))
    
    # Clean up test data
    await cleanup_test_data()
    
    # Show results
    print("\n" + "="*50)
    print("Test Results Summary")
    print("="*50)
    
    all_passed = True
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if not result:
            all_passed = False
    
    print("="*50)
    
    if all_passed:
        print("🎉 All database tests passed!")
        print("🚀 Database implementation is working correctly!")
    else:
        print("❌ Some database tests failed.")
        print("🔧 Please check the database configuration and try again.")
        return False
    
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)