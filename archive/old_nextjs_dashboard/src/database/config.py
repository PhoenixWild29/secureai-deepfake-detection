#!/usr/bin/env python3
"""
Database Configuration for SecureAI DeepFake Detection
Async PostgreSQL session setup with vector extension support
"""

import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
import asyncpg
from pgvector.asyncpg import register_vector


class Base(DeclarativeBase):
    """Base class for all SQLModel tables"""
    pass


# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+asyncpg://secureai:secureai_password@localhost:5432/secureai_db"
)

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL query logging
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get database session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_database():
    """
    Initialize database with vector extension and create tables
    """
    # Create all tables
    async with engine.begin() as conn:
        # Enable vector extension
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)


async def check_database_connection():
    """
    Check if database connection is working
    """
    try:
        async with engine.begin() as conn:
            # Test basic connection
            result = await conn.execute(text("SELECT 1"))
            result.fetchone()
            
            # Test vector extension
            await conn.execute(text("SELECT vector_dims('[1,2,3]'::vector)"))
            
            return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False


async def setup_vector_extension():
    """
    Setup PostgreSQL vector extension for embedding storage
    """
    try:
        async with engine.begin() as conn:
            # Enable vector extension
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            
            # Verify extension is working
            result = await conn.execute(text("SELECT vector_dims('[1,2,3]'::vector)"))
            dims = result.fetchone()[0]
            print(f"Vector extension enabled. Test vector dimensions: {dims}")
            
            return True
    except Exception as e:
        print(f"Failed to setup vector extension: {e}")
        return False


# Database indexes for performance optimization
PERFORMANCE_INDEXES = [
    # EmbeddingCache indexes for sub-100ms lookups
    "CREATE INDEX IF NOT EXISTS idx_embedding_cache_video_hash ON embedding_cache(video_hash)",
    "CREATE INDEX IF NOT EXISTS idx_embedding_cache_redis_key ON embedding_cache(redis_cache_key)",
    "CREATE INDEX IF NOT EXISTS idx_embedding_cache_model_version ON embedding_cache(model_version_id)",
    "CREATE INDEX IF NOT EXISTS idx_embedding_cache_expiry ON embedding_cache(cache_expiry)",
    
    # MLModelVersion indexes
    "CREATE INDEX IF NOT EXISTS idx_ml_model_version_type ON ml_model_version(model_type)",
    "CREATE INDEX IF NOT EXISTS idx_ml_model_version_production ON ml_model_version(is_production)",
    "CREATE INDEX IF NOT EXISTS idx_ml_model_version_created_by ON ml_model_version(created_by)",
    
    # TrainingDataExport indexes
    "CREATE INDEX IF NOT EXISTS idx_training_export_batch_id ON training_data_export(export_batch_id)",
    "CREATE INDEX IF NOT EXISTS idx_training_export_status ON training_data_export(export_status)",
    "CREATE INDEX IF NOT EXISTS idx_training_export_classification ON training_data_export(data_classification)",
    
    # ModelPerformanceLog indexes
    "CREATE INDEX IF NOT EXISTS idx_performance_log_model_version ON model_performance_log(model_version_id)",
    "CREATE INDEX IF NOT EXISTS idx_performance_log_timestamp ON model_performance_log(evaluation_timestamp)",
    "CREATE INDEX IF NOT EXISTS idx_performance_log_anomaly ON model_performance_log(anomaly_flag)",
]


async def create_performance_indexes():
    """
    Create database indexes for performance optimization
    """
    try:
        async with engine.begin() as conn:
            for index_sql in PERFORMANCE_INDEXES:
                await conn.execute(text(index_sql))
            print("Performance indexes created successfully")
            return True
    except Exception as e:
        print(f"Failed to create performance indexes: {e}")
        return False


# Connection pool configuration
async def configure_connection_pool():
    """
    Configure connection pool for optimal performance
    """
    # Connection pool is already configured in engine creation
    # This function can be extended for additional pool configuration
    pass


# Database health check
async def health_check():
    """
    Comprehensive database health check
    """
    checks = {
        "connection": await check_database_connection(),
        "vector_extension": await setup_vector_extension(),
        "indexes": await create_performance_indexes(),
    }
    
    all_healthy = all(checks.values())
    
    return {
        "healthy": all_healthy,
        "checks": checks,
        "database_url": DATABASE_URL.split("@")[-1] if "@" in DATABASE_URL else DATABASE_URL
    }
