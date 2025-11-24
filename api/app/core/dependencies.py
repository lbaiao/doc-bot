from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_async_session
from app.services.storage import StorageService, get_storage_service
from app.services.embeddings import EmbeddingsService
from app.services.ingestion import IngestionService
from app.services.retrieval import RetrievalService
from app.services.chats import ChatService
from app.services.vector_db import VectorDBClient, get_vector_db


SessionDep = Annotated[AsyncSession, Depends(get_async_session)]
StorageDep = Annotated[StorageService, Depends(get_storage_service)]
VectorDBDep = Annotated[VectorDBClient, Depends(get_vector_db)]


def get_embeddings_service() -> EmbeddingsService:
    """Get embeddings service instance."""
    return EmbeddingsService()


def get_ingestion_service(
    session: SessionDep,
    storage: StorageDep,
    embeddings: Annotated[EmbeddingsService, Depends(get_embeddings_service)]
) -> IngestionService:
    """Get ingestion service with all dependencies."""
    return IngestionService(session, storage, embeddings)


def get_retrieval_service(
    session: SessionDep,
) -> RetrievalService:
    """Get retrieval service with session."""
    return RetrievalService(session)


def get_chat_service(
    session: SessionDep,
) -> ChatService:
    """Get chat service with session."""
    return ChatService(session)


# Type aliases for dependency injection
IngestionDep = Annotated[IngestionService, Depends(get_ingestion_service)]
RetrievalDep = Annotated[RetrievalService, Depends(get_retrieval_service)]
ChatDep = Annotated[ChatService, Depends(get_chat_service)]
EmbeddingsDep = Annotated[EmbeddingsService, Depends(get_embeddings_service)]
