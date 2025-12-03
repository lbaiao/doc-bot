import asyncio
import os
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.db.base import Base, get_async_session
from fastapi_users.password import PasswordHelper
from app.db.models.user import User
from app.services.storage import StorageService, get_storage_service
from app.core.dependencies import get_ingestion_service, get_chat_service
from app.services.chats import ChatService
from app.db.models.chat import Chat, Message
import uuid

# Use configured database or override via TEST_DATABASE_URL env var
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://docbot:docbot_password@localhost:5432/docbot",
)
# Point app settings to the same test DB
settings.DATABASE_URL = TEST_DATABASE_URL

engine = create_async_engine(
    TEST_DATABASE_URL,
    poolclass=NullPool,
)

TestingSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# --- Fakes for dependency overrides ---

class InMemoryStorageService(StorageService):
    def __init__(self):
        self._data = {}
    async def put(self, data: bytes, path_hint: str) -> str:
        uri = f"memory://{path_hint}"
        self._data[uri] = data
        return uri
    async def get(self, storage_uri: str) -> bytes:
        return self._data[storage_uri]
    async def delete(self, storage_uri: str) -> None:
        self._data.pop(storage_uri, None)
    async def exists(self, storage_uri: str) -> bool:
        return storage_uri in self._data


class FakeIngestionService:
    def __init__(self, session: AsyncSession, storage: StorageService):
        self.session = session
        self.storage = storage
    async def ingest_document(self, document_id: uuid.UUID) -> None:
        from app.db.models.document import Document, Page
        # mark ready and add a stub page
        result = await self.session.execute(
            select(Document).where(Document.id == document_id)
        )
        doc = result.scalar_one()
        doc.status = "ready"
        page = Page(
            document_id=document_id,
            page_no=0,
            width=1.0,
            height=1.0,
            text="stub page",
        )
        self.session.add(page)
        await self.session.commit()


class FakeChatService(ChatService):
    """Lightweight chat service that echoes without hitting the agent."""
    async def post_message(self, chat_id: uuid.UUID, user_id: uuid.UUID, content: dict | str) -> Message:
        # ensure chat exists and is owned
        result = await self.session.execute(select(Chat).where(Chat.id == chat_id))
        chat = result.scalar_one_or_none()
        if not chat or chat.owner_id != user_id:
            raise ValueError("Chat not found or access denied")
        text = content.get("text") if isinstance(content, dict) else str(content)
        user_msg = Message(chat_id=chat_id, role="user", content={"text": text})
        self.session.add(user_msg)
        await self.session.flush()
        assistant_msg = Message(chat_id=chat_id, role="assistant", content={"text": f"ack: {text}"})
        self.session.add(assistant_msg)
        await self.session.commit()
        await self.session.refresh(assistant_msg)
        return assistant_msg




@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session for each test."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create a test client with overridden dependencies."""
    
    async def override_get_db():
        yield db_session

    storage = InMemoryStorageService()
    def override_storage():
        return storage

    def override_ingestion():
        return FakeIngestionService(db_session, storage)

    def override_chat_service():
        return FakeChatService(db_session)

    from httpx import AsyncClient, ASGITransport
    from app.main import create_app

    test_app = create_app()
    test_app.dependency_overrides[get_async_session] = override_get_db
    test_app.dependency_overrides[get_storage_service] = override_storage
    test_app.dependency_overrides[get_ingestion_service] = override_ingestion
    test_app.dependency_overrides[get_chat_service] = override_chat_service

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as ac:
        yield ac
    
    test_app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def seeded_user(db_session: AsyncSession):
    """Create the default seeded user in the test DB."""
    helper = PasswordHelper()
    user = User(
        email="admin@example.com",
        hashed_password=helper.hash("changeme123!"),
        is_active=True,
        is_superuser=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user
