"""
Initialize database tables programmatically.
This creates all tables defined in SQLAlchemy models.
"""
import asyncio
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.db.base import Base

logger = logging.getLogger(__name__)


async def init_db():
    """Create all database tables."""
    logger.info("Initializing database...")
    
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    
    try:
        # Create all tables
        async with engine.begin() as conn:
            # Check if tables already exist
            result = await conn.execute(
                text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
            )
            existing_tables = [row[0] for row in result]
            
            if existing_tables:
                logger.info(f"Found {len(existing_tables)} existing tables: {existing_tables}")
            else:
                logger.info("No existing tables found, creating all...")
            
            # Create all tables (idempotent - won't fail if they exist)
            await conn.run_sync(Base.metadata.create_all)
            
        logger.info("✅ Database initialization complete!")
        
        # Verify tables were created
        async with engine.connect() as conn:
            result = await conn.execute(
                text("SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename")
            )
            tables = [row[0] for row in result]
            logger.info(f"Database tables: {tables}")
            
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise
    finally:
        await engine.dispose()


async def drop_all():
    """Drop all database tables (DANGEROUS - use only in development)."""
    logger.warning("⚠️  Dropping all tables...")
    
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.info("✅ All tables dropped!")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(init_db())
