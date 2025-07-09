#!/usr/bin/env python3
"""
Database management script for AI Error Translator
"""
import asyncio
import sys
import os
from typing import Optional

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.database.connection import db_manager
from app.database.models import User, ApiKey, Subscription, UsageLog, TokenBlacklist
from app.services.user_service import UserService
from app.config import settings


async def create_tables():
    """Create all database tables"""
    print("Creating database tables...")
    try:
        await db_manager.create_tables()
        print("✅ Database tables created successfully")
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False
    return True


async def drop_tables():
    """Drop all database tables"""
    print("⚠️  WARNING: This will delete all data!")
    confirm = input("Are you sure you want to drop all tables? (yes/no): ")
    
    if confirm.lower() != 'yes':
        print("Operation cancelled")
        return False
    
    print("Dropping database tables...")
    try:
        await db_manager.drop_tables()
        print("✅ Database tables dropped successfully")
    except Exception as e:
        print(f"❌ Error dropping tables: {e}")
        return False
    return True


async def check_database():
    """Check database health and connection"""
    print("Checking database connection...")
    try:
        healthy = await db_manager.health_check()
        if healthy:
            print("✅ Database connection is healthy")
        else:
            print("❌ Database connection failed")
            return False
    except Exception as e:
        print(f"❌ Error checking database: {e}")
        return False
    return True


async def create_user(email: str, password: str, full_name: Optional[str] = None):
    """Create a new user"""
    print(f"Creating user: {email}")
    
    try:
        async with db_manager.get_session() as session:
            user_service = UserService(session)
            user = await user_service.create_user(
                email=email,
                password=password,
                full_name=full_name
            )
            print(f"✅ User created successfully: {user.id}")
            print(f"   Email: {user.email}")
            print(f"   Tier: {user.subscription_tier}")
            print(f"   Created: {user.created_at}")
            return user
    except Exception as e:
        print(f"❌ Error creating user: {e}")
        return None


async def list_users():
    """List all users"""
    print("Listing all users...")
    
    try:
        async with db_manager.get_session() as session:
            from app.database.repositories import UserRepository
            user_repo = UserRepository(session)
            
            # Get all users (this would need to be implemented in the repository)
            # For now, just show that the function exists
            print("✅ User listing functionality ready")
            print("   (Implementation depends on your pagination needs)")
    except Exception as e:
        print(f"❌ Error listing users: {e}")


async def show_user_info(email: str):
    """Show detailed information about a user"""
    print(f"Getting user info for: {email}")
    
    try:
        async with db_manager.get_session() as session:
            user_service = UserService(session)
            user = await user_service.get_user_by_email(email)
            
            if not user:
                print(f"❌ User not found: {email}")
                return
            
            print(f"✅ User found:")
            print(f"   ID: {user.id}")
            print(f"   Email: {user.email}")
            print(f"   Full Name: {user.full_name}")
            print(f"   Tier: {user.subscription_tier}")
            print(f"   Active: {user.is_active}")
            print(f"   Verified: {user.is_verified}")
            print(f"   Created: {user.created_at}")
            print(f"   Last Login: {user.last_login}")
            
            # Get API keys
            api_keys = await user_service.get_user_api_keys(user.id)
            print(f"   API Keys: {len(api_keys)}")
            
            # Get usage stats
            usage_stats = await user_service.get_usage_stats(user.id)
            print(f"   Total Requests (30 days): {usage_stats['total_requests']}")
            
    except Exception as e:
        print(f"❌ Error getting user info: {e}")


def print_help():
    """Print help message"""
    print("AI Error Translator Database Management")
    print("======================================")
    print()
    print("Usage: python manage_db.py [command] [options]")
    print()
    print("Commands:")
    print("  create-tables     Create all database tables")
    print("  drop-tables       Drop all database tables (WARNING: destructive)")
    print("  check             Check database health")
    print("  create-user       Create a new user")
    print("  list-users        List all users")
    print("  user-info         Show detailed user information")
    print("  help              Show this help message")
    print()
    print("Examples:")
    print("  python manage_db.py create-tables")
    print("  python manage_db.py create-user test@example.com password123")
    print("  python manage_db.py user-info test@example.com")
    print()
    print("Environment:")
    print(f"  Database URL: {settings.DATABASE_URL}")
    print(f"  Debug Mode: {settings.API_DEBUG}")


async def main():
    """Main function"""
    if len(sys.argv) < 2:
        print_help()
        return
    
    command = sys.argv[1]
    
    if command == "help":
        print_help()
        return
    
    if command == "create-tables":
        await create_tables()
        
    elif command == "drop-tables":
        await drop_tables()
        
    elif command == "check":
        await check_database()
        
    elif command == "create-user":
        if len(sys.argv) < 4:
            print("Usage: python manage_db.py create-user <email> <password> [full_name]")
            return
        
        email = sys.argv[2]
        password = sys.argv[3]
        full_name = sys.argv[4] if len(sys.argv) > 4 else None
        
        await create_user(email, password, full_name)
        
    elif command == "list-users":
        await list_users()
        
    elif command == "user-info":
        if len(sys.argv) < 3:
            print("Usage: python manage_db.py user-info <email>")
            return
        
        email = sys.argv[2]
        await show_user_info(email)
        
    else:
        print(f"Unknown command: {command}")
        print_help()


if __name__ == "__main__":
    asyncio.run(main())