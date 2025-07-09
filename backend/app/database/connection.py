import logging
import time
from typing import AsyncGenerator, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool, QueuePool
from sqlalchemy import text
from contextlib import asynccontextmanager

from app.config import settings

logger = logging.getLogger(__name__)

# Database base class
class Base(DeclarativeBase):
    pass

# Database engine with optimized connection pooling
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,
    pool_recycle=3600,  # Recycle connections after 1 hour
    pool_timeout=30,    # Timeout for getting connection from pool
    echo=settings.API_DEBUG,  # Log SQL queries in debug mode
    poolclass=QueuePool if "postgresql" in settings.DATABASE_URL else NullPool,
    connect_args={
        "server_settings": {
            "application_name": "ai-error-translator",
            "jit": "off",  # Disable JIT for better performance on simple queries
        }
    } if "postgresql" in settings.DATABASE_URL else {},
)

# Session factory
AsyncSessionFactory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

class DatabaseManager:
    """Database manager for handling connections and sessions"""
    
    def __init__(self):
        self.engine = engine
        self.session_factory = AsyncSessionFactory
        self.connection_stats = {
            'total_connections': 0,
            'active_connections': 0,
            'pool_hits': 0,
            'pool_misses': 0
        }
        
    async def create_tables(self):
        """Create all database tables"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created successfully")
    
    async def drop_tables(self):
        """Drop all database tables"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            logger.info("Database tables dropped successfully")
    
    async def close(self):
        """Close database connections"""
        await self.engine.dispose()
        logger.info("Database connections closed")
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get a database session with performance tracking"""
        start_time = time.time()
        
        async with self.session_factory() as session:
            try:
                self.connection_stats['total_connections'] += 1
                self.connection_stats['active_connections'] += 1
                
                yield session
                
                # Track successful connection
                self.connection_stats['pool_hits'] += 1
                
            except Exception as e:
                await session.rollback()
                self.connection_stats['pool_misses'] += 1
                logger.error(f"Database session error: {e}")
                raise
            finally:
                self.connection_stats['active_connections'] -= 1
                await session.close()
                
                # Log slow queries
                duration = time.time() - start_time
                if duration > 1.0:  # Log queries taking more than 1 second
                    logger.warning(f"Slow database session: {duration:.2f}s")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check database health with detailed metrics"""
        try:
            start_time = time.time()
            
            async with self.get_session() as session:
                await session.execute(text("SELECT 1"))
                
            connection_time = time.time() - start_time
            
            # Get pool status
            pool = self.engine.pool
            pool_status = {
                'pool_size': pool.size(),
                'checked_in': pool.checkedin(),
                'checked_out': pool.checkedout(),
                'overflow': pool.overflow(),
                'invalid': pool.invalid(),
            }
            
            return {
                'status': 'healthy',
                'connection_time_ms': round(connection_time * 1000, 2),
                'pool_status': pool_status,
                'connection_stats': self.connection_stats.copy()
            }
            
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'connection_stats': self.connection_stats.copy()
            }
    
    async def get_pool_stats(self) -> Dict[str, Any]:
        """Get detailed connection pool statistics"""
        try:
            pool = self.engine.pool
            
            return {
                'pool_configuration': {
                    'pool_size': settings.DATABASE_POOL_SIZE,
                    'max_overflow': settings.DATABASE_MAX_OVERFLOW,
                    'pool_timeout': 30,
                    'pool_recycle': 3600
                },
                'current_pool_status': {
                    'pool_size': pool.size(),
                    'checked_in': pool.checkedin(),
                    'checked_out': pool.checkedout(),
                    'overflow': pool.overflow(),
                    'invalid': pool.invalid(),
                },
                'connection_stats': self.connection_stats.copy(),
                'utilization': {
                    'pool_utilization': (pool.checkedout() / (pool.size() + pool.overflow())) * 100 if (pool.size() + pool.overflow()) > 0 else 0,
                    'success_rate': (self.connection_stats['pool_hits'] / self.connection_stats['total_connections']) * 100 if self.connection_stats['total_connections'] > 0 else 0
                }
            }
        except Exception as e:
            logger.error(f"Error getting pool stats: {e}")
            return {'error': str(e)}

# Global database manager instance
db_manager = DatabaseManager()

# Dependency for FastAPI
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions"""
    async with db_manager.get_session() as session:
        yield session