# Database Implementation

This document explains the database implementation for the AI Error Translator backend.

## Overview

The application uses **PostgreSQL** as the primary database with **SQLAlchemy** as the ORM and **Alembic** for migrations. The database supports:

- User management and authentication
- API key management  
- Subscription tracking
- Usage logging and analytics
- Token blacklisting

## Database Schema

### Users Table
Stores user account information and subscription details.

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255),
    full_name VARCHAR(255),
    subscription_tier VARCHAR(50) DEFAULT 'free',
    stripe_customer_id VARCHAR(255) UNIQUE,
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login TIMESTAMP WITH TIME ZONE
);
```

### API Keys Table
Stores API keys for user authentication.

```sql
CREATE TABLE api_keys (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    key_hash VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    last_used TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE
);
```

### Subscriptions Table
Tracks user subscriptions and billing information.

```sql
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    stripe_subscription_id VARCHAR(255) UNIQUE,
    stripe_price_id VARCHAR(255),
    tier VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'active',
    current_period_start TIMESTAMP WITH TIME ZONE,
    current_period_end TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    canceled_at TIMESTAMP WITH TIME ZONE
);
```

### Usage Logs Table
Stores API usage for analytics and billing.

```sql
CREATE TABLE usage_logs (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    endpoint VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL,
    status_code INTEGER NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    response_time_ms INTEGER,
    error_type VARCHAR(255),
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Token Blacklist Table
Stores revoked JWT tokens.

```sql
CREATE TABLE token_blacklist (
    id UUID PRIMARY KEY,
    token_jti VARCHAR(255) UNIQUE NOT NULL,
    token_type VARCHAR(50) NOT NULL,
    revoked_by VARCHAR(255),
    revocation_reason VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL
);
```

## Configuration

### Environment Variables

```bash
# PostgreSQL connection
DATABASE_URL=postgresql://username:password@localhost:5432/ai_error_translator

# Connection pool settings
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20
```

### Connection Pool
- **Pool Size**: 10 connections
- **Max Overflow**: 20 additional connections
- **Pre-ping**: Enabled for connection validation
- **Echo**: SQL logging in debug mode

## Services and Repositories

### Repository Pattern
Data access is organized using the repository pattern:

- `UserRepository`: User CRUD operations
- `ApiKeyRepository`: API key management
- `SubscriptionRepository`: Subscription tracking
- `UsageLogRepository`: Usage logging and analytics
- `TokenBlacklistRepository`: Token revocation

### Service Layer
Business logic is handled by services:

- `UserService`: High-level user operations
- `AuthService`: JWT token management
- `StripeService`: Payment processing

## Database Management

### Setup Commands

```bash
# Create database tables
python manage_db.py create-tables

# Check database health
python manage_db.py check

# Create a new user
python manage_db.py create-user user@example.com password123 "Full Name"

# Show user information
python manage_db.py user-info user@example.com

# Drop all tables (WARNING: destructive)
python manage_db.py drop-tables
```

### Migrations with Alembic

```bash
# Generate migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1

# Show migration history
alembic history
```

## API Endpoints

### User Management

#### Create User
```
POST /users/
{
    "email": "user@example.com",
    "password": "password123",
    "full_name": "John Doe"
}
```

#### Get Current User
```
GET /users/me
Authorization: Bearer <token>
```

#### Update Profile
```
PUT /users/me
Authorization: Bearer <token>
{
    "full_name": "Updated Name",
    "email": "new@example.com"
}
```

#### Change Password
```
POST /users/me/change-password
Authorization: Bearer <token>
{
    "current_password": "old_password",
    "new_password": "new_password"
}
```

### API Key Management

#### List API Keys
```
GET /users/me/api-keys
Authorization: Bearer <token>
```

#### Create API Key
```
POST /users/me/api-keys
Authorization: Bearer <token>
{
    "name": "My API Key"
}
```

#### Deactivate API Key
```
DELETE /users/me/api-keys/{key_id}
Authorization: Bearer <token>
```

### Analytics

#### Usage Statistics
```
GET /users/me/usage?days=30
Authorization: Bearer <token>
```

#### Dashboard Data
```
GET /users/me/dashboard
Authorization: Bearer <token>
```

## Security Features

### Password Security
- **Bcrypt hashing** with salt
- **Minimum password requirements** (configurable)
- **Password change tracking**

### API Key Security
- **JWT-based tokens** with expiration
- **Token refresh mechanism**
- **Token blacklisting** for revocation
- **Rate limiting** per user/key

### Data Protection
- **UUID primary keys** (no sequential IDs)
- **Indexed queries** for performance
- **Input validation** with Pydantic
- **SQL injection protection** via SQLAlchemy

## Performance Optimizations

### Database Indexes
- **User email** for authentication
- **API key hash** for token validation
- **Usage logs** by user and timestamp
- **Subscription status** for billing queries

### Connection Management
- **Connection pooling** for efficiency
- **Async operations** for non-blocking I/O
- **Proper session management**

### Query Optimization
- **Select specific columns** only
- **Use relationships** for joins
- **Pagination** for large datasets
- **Bulk operations** where possible

## Monitoring and Maintenance

### Health Checks
```python
# Database health check
healthy = await db_manager.health_check()
```

### Cleanup Tasks
```python
# Clean up expired API keys
await api_key_repo.cleanup_expired_keys()

# Clean up old usage logs
await usage_repo.cleanup_old_logs(days=90)

# Clean up expired blacklisted tokens
await token_blacklist_repo.cleanup_expired_tokens()
```

### Monitoring Queries
```sql
-- Active users
SELECT COUNT(*) FROM users WHERE is_active = true;

-- API usage last 24 hours
SELECT COUNT(*) FROM usage_logs 
WHERE created_at >= NOW() - INTERVAL '24 hours';

-- Error rate
SELECT 
    COUNT(*) FILTER (WHERE status_code >= 400) * 100.0 / COUNT(*) as error_rate
FROM usage_logs 
WHERE created_at >= NOW() - INTERVAL '24 hours';
```

## Testing

### Test Database
Use SQLite for testing:
```bash
export DATABASE_URL="sqlite:///test.db"
python test_database.py
```

### Test Coverage
- **Unit tests** for repositories
- **Integration tests** for services
- **End-to-end tests** for API endpoints

### Test Data
```python
# Create test user
user = await user_service.create_user(
    email="test@example.com",
    password="password123"
)

# Create API key
api_key = await user_service.create_api_key(user.id, "Test Key")
```

## Deployment

### Production Setup
1. **PostgreSQL database** (managed service recommended)
2. **Connection pooling** configured
3. **Backup strategy** in place
4. **Monitoring** enabled

### Environment Variables
```bash
# Production database
DATABASE_URL=postgresql://user:pass@prod-db:5432/ai_error_translator

# Pool settings
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=50
```

### Docker Deployment
```dockerfile
# Database initialization
RUN python manage_db.py create-tables

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import asyncio; from app.database.connection import db_manager; asyncio.run(db_manager.health_check())"
```

## Troubleshooting

### Common Issues

#### Connection Errors
```bash
# Check database is running
pg_isready -h localhost -p 5432

# Test connection
python -c "import asyncio; from app.database.connection import db_manager; asyncio.run(db_manager.health_check())"
```

#### Migration Issues
```bash
# Check migration status
alembic current

# Reset migrations (development only)
alembic downgrade base
alembic upgrade head
```

#### Performance Issues
```sql
-- Check slow queries
SELECT query, mean_time, calls 
FROM pg_stat_statements 
ORDER BY mean_time DESC;

-- Check connection usage
SELECT count(*) FROM pg_stat_activity;
```

## Best Practices

### Development
- **Use migrations** for schema changes
- **Test with real data** volumes
- **Monitor query performance**
- **Use proper indexing**

### Production
- **Regular backups**
- **Connection monitoring**
- **Query optimization**
- **Security updates**

### Security
- **Environment variables** for secrets
- **Encrypted connections**
- **Regular security audits**
- **Access control**