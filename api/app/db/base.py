from typing import AsyncGenerator

import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)
_init_lock = asyncio.Lock()
_initialized = False


class Base(DeclarativeBase):
    pass


# Import all models here so alembic can discover them
from app.db.models.user import User  # noqa: E402, F401
from app.db.models.document import Document, Page, Chunk, Figure, Table  # noqa: E402, F401
from app.db.models.embedding import TextEmbedding, ImageEmbedding, TableEmbedding  # noqa: E402, F401
from app.db.models.chat import Chat, Message, ToolRun  # noqa: E402, F401


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async session, ensuring the schema exists before first use."""
    global _initialized
    
    if not _initialized:
        async with _init_lock:
            if not _initialized:
                async with engine.begin() as conn:
                    await conn.run_sync(Base.metadata.create_all)
                _initialized = True
    
    async with async_session_maker() as session:
        yield session
