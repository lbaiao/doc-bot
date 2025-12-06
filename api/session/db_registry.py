"""
Database-backed session registry using Qdrant + Postgres instead of file-based indexes.

This replaces the old file-based SessionRegistry with a cloud-native version that:
- Uses Qdrant for vector search (instead of FAISS files)
- Uses Postgres for metadata (instead of parquet files)
- Uses StorageService for images (instead of local extraction/ dirs)
- Maintains the EXACT same interface for backward compatibility with agent tools

Agent tools work unchanged - they just call the same methods!
"""

import logging
import uuid
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import asyncio
import threading

from sqlalchemy import select

from app.db.models.document import Document, Chunk as ChunkModel, Figure as FigureModel
from app.services.vector_db import get_vector_db
from app.services.embeddings import EmbeddingsService
from app.services.storage import get_storage_service
from app.db.base import async_session_maker

logger = logging.getLogger(__name__)


# --------- Data models (same as old registry) ---------
@dataclass
class ChunkRecord:
    chunk_id: str
    text: str
    metadata: Dict[str, Any]


@dataclass
class SearchHit:
    """Unified search result format."""
    id: str
    doc_type: str  # 'chunk' or 'image_caption'
    score: float
    text: str
    metadata: Dict[str, Any]


class DBSessionRegistry:
    """
    Database-backed registry that maintains same interface as file-based SessionRegistry.
    
    Instead of loading FAISS/Whoosh indexes from disk, this:
    - Queries Qdrant for vector search
    - Queries Postgres for text/metadata
    - Uses StorageService for files
    """
    
    def __init__(self):
        self._vector_db = None
        self._embeddings = None
        self._storage = None
        self._active_session: Optional[uuid.UUID] = None  # Track by document UUID
        self._active_user: Optional[uuid.UUID] = None
        self._main_loop: Optional[asyncio.AbstractEventLoop] = None
        self._main_loop_thread: Optional[threading.Thread] = None
    
    @property
    def vector_db(self):
        """Lazy-load vector DB client."""
        if self._vector_db is None:
            self._vector_db = get_vector_db()
        return self._vector_db
    
    @property
    def embeddings(self):
        """Lazy-load embeddings service."""
        if self._embeddings is None:
            self._embeddings = EmbeddingsService()
        return self._embeddings
    
    @property
    def storage(self):
        """Lazy-load storage service."""
        if self._storage is None:
            self._storage = get_storage_service()
        return self._storage

    def set_main_loop(self, loop: asyncio.AbstractEventLoop):
        """Capture the main event loop so background threads can schedule work on it."""
        self._main_loop = loop
        self._main_loop_thread = threading.current_thread()

    def _run_sync(self, coro):
        """Run an async coroutine safely from sync code, regardless of loop state."""
        if self._main_loop and self._main_loop.is_running() and threading.current_thread() != self._main_loop_thread:
            # Schedule on the captured main loop from a background thread
            return asyncio.run_coroutine_threadsafe(coro, self._main_loop).result()

        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(coro)
        finally:
            asyncio.set_event_loop(None)
            loop.close()
    
    def set_active(self, document_id: str):
        """Set active document by ID (UUID string)."""
        try:
            self._active_session = uuid.UUID(document_id)
            logger.info(f"Set active document: {document_id}")
        except ValueError:
            logger.error(f"Invalid document ID: {document_id}")
            raise ValueError(f"Invalid document ID format: {document_id}")
    
    def get_active(self) -> Optional[str]:
        """Get active document ID as string."""
        return str(self._active_session) if self._active_session else None
    
    def set_user(self, user_id: uuid.UUID):
        """Set current user context for filtering."""
        self._active_user = user_id
        logger.info(f"Set active user: {user_id}")
    
    def ensure(self, document_id: str):
        """
        Ensure document is loaded and ready.
        
        In file-based system, this loaded indexes from disk.
        In DB system, this just validates the document exists.
        """
        try:
            doc_uuid = uuid.UUID(document_id)
            
            # Run async check in sync context
            async def check_exists():
                async with async_session_maker() as session:
                    result = await session.execute(
                        select(Document).where(Document.id == doc_uuid)
                    )
                    doc = result.scalar_one_or_none()
                    if not doc:
                        raise ValueError(f"Document {document_id} not found")
                    if doc.status != "ready":
                        raise ValueError(f"Document {document_id} not ready (status: {doc.status})")
                    return doc
            
            doc = self._run_sync(check_exists())
            
            self.set_active(document_id)
            if doc.owner_id:
                self.set_user(doc.owner_id)
            
            logger.info(f"Document {document_id} ready")
            
        except Exception as e:
            logger.error(f"Error ensuring document {document_id}: {e}")
            raise
    
    def search_lexical(
        self,
        document_id: str,
        query: str,
        doc_type: str = "any",
        limit: int = 10,
        preview_chars: int = 160
    ) -> List[Dict[str, Any]]:
        """
        Lexical (keyword) search using Postgres full-text search.
        
        Replaces Whoosh with Postgres text search.
        Returns same format as old registry for compatibility.
        """
        doc_uuid = uuid.UUID(document_id)
        
        async def do_search():
            async with async_session_maker() as session:
                # Search chunks by text content
                if doc_type in ("any", "chunk"):
                    from sqlalchemy import func
                    
                    result = await session.execute(
                        select(ChunkModel)
                        .where(ChunkModel.document_id == doc_uuid)
                        .where(ChunkModel.text.ilike(f"%{query}%"))  # Simple ILIKE for now
                        .limit(limit)
                    )
                    chunks = result.scalars().all()
                    
                    hits = []
                    for idx, chunk in enumerate(chunks):
                        preview = chunk.text[:preview_chars] if len(chunk.text) > preview_chars else chunk.text
                        hits.append({
                            "id": str(chunk.id),
                            "type": "chunk",
                            "order": idx,
                            "page_index": 0,  # TODO: Get from page relation
                            "score": 1.0,  # Lexical search, binary match
                            "preview": preview,
                            "text": chunk.text
                        })
                    
                    return hits
                
                return []
        
        return self._run_sync(do_search())
    
    def search_vector(
        self,
        document_id: str,
        query: str,
        k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Vector similarity search using Qdrant.
        
        Replaces FAISS with Qdrant.
        Returns same format as old registry.
        """
        doc_uuid = uuid.UUID(document_id)
        
        async def do_search():
            # Generate query embedding
            query_embedding = await self.embeddings.embed_text(query)
            
            # Search Qdrant
            vector_results = self.vector_db.search_text(
                query_vector=query_embedding,
                user_id=self._active_user,
                document_ids=[doc_uuid],
                top_k=k,
            )
            
            # Get full chunk data from Postgres
            chunk_ids = [uuid.UUID(r["chunk_id"]) for r in vector_results]
            
            async with async_session_maker() as session:
                result = await session.execute(
                    select(ChunkModel).where(ChunkModel.id.in_(chunk_ids))
                )
                chunks_db = {str(c.id): c for c in result.scalars().all()}
            
            # Format results
            hits = []
            for vector_result in vector_results:
                chunk_id = vector_result["chunk_id"]
                chunk = chunks_db.get(chunk_id)
                
                if chunk:
                    hits.append({
                        "chunk_number": str(chunk.id)[-4:],  # Last 4 chars for compat
                        "score": vector_result["score"],
                        "source": f"chunk_{chunk.id}",
                        "text": chunk.text[:200],  # Truncated preview
                        "full_text": chunk.text,
                        "metadata": {
                            "chunk_id": str(chunk.id),
                            "document_id": str(chunk.document_id),
                            "page_id": str(chunk.page_id) if chunk.page_id else None,
                        }
                    })
            
            return hits
        
        return self._run_sync(do_search())
    
    def search_image_captions(
        self,
        document_id: str,
        query: str,
        k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search image captions using Qdrant.
        
        Replaces FAISS caption search.
        """
        doc_uuid = uuid.UUID(document_id)
        
        async def do_search():
            # Generate query embedding
            query_embedding = await self.embeddings.embed_text(query)
            
            # Search Qdrant images collection
            vector_results = self.vector_db.search_images(
                query_vector=query_embedding,
                user_id=self._active_user,
                document_ids=[doc_uuid],
                top_k=k,
            )
            
            # Get full figure data from Postgres
            figure_ids = [uuid.UUID(r["figure_id"]) for r in vector_results]
            
            async with async_session_maker() as session:
                result = await session.execute(
                    select(FigureModel).where(FigureModel.id.in_(figure_ids))
                )
                figures_db = {str(f.id): f for f in result.scalars().all()}
            
            # Format results
            hits = []
            for vector_result in vector_results:
                figure_id = vector_result["figure_id"]
                figure = figures_db.get(figure_id)
                
                if figure:
                    hits.append({
                        "id": str(figure.id),
                        "caption": figure.caption_text or "",
                        "image_path": figure.storage_uri,  # Now a storage URI
                        "storage_uri": figure.storage_uri,
                        "page_index": 0,  # TODO: Get from page relation
                        "score": vector_result["score"],
                        "width": figure.bbox_json.get("width", 0) if figure.bbox_json else 0,
                        "height": figure.bbox_json.get("height", 0) if figure.bbox_json else 0,
                        "metadata": {
                            "figure_id": str(figure.id),
                            "document_id": str(figure.document_id),
                            "page_id": str(figure.page_id) if figure.page_id else None,
                        }
                    })
            
            return hits
        
        return self._run_sync(do_search())
    
    def hybrid_search(
        self,
        document_id: str,
        query: str,
        index_type: str = "text",
        k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search combining lexical and vector results.
        
        Merges Postgres text search + Qdrant vector search.
        """
        # Get both result sets
        lexical_hits = self.search_lexical(document_id, query, limit=k)
        
        if index_type == "captions":
            vector_hits = self.search_image_captions(document_id, query, k=k)
        else:
            vector_hits = self.search_vector(document_id, query, k=k)
        
        # Combine and re-rank (simple: 50/50 weight)
        combined = []
        
        # Add lexical with weight
        for hit in lexical_hits:
            hit["hybrid_score"] = 0.5 * hit.get("score", 1.0)
            hit["source_type"] = "lexical"
            combined.append(hit)
        
        # Add vector with weight
        for hit in vector_hits:
            hit["hybrid_score"] = 0.5 * hit.get("score", 0.0)
            hit["source_type"] = "vector"
            combined.append(hit)
        
        # Sort by hybrid score
        combined.sort(key=lambda x: x["hybrid_score"], reverse=True)
        
        return combined[:k]
    
    def get_chunks(
        self,
        document_id: str,
        chunk_ids: List[str]
    ) -> List[ChunkRecord]:
        """
        Fetch full chunk texts by IDs.
        
        Replaces reading from chunk_*.txt files with Postgres query.
        """
        doc_uuid = uuid.UUID(document_id)
        
        async def do_fetch():
            # Convert chunk IDs (might be like "0001") to UUIDs
            # Try to interpret as UUID or as chunk order
            chunk_uuids = []
            for cid in chunk_ids:
                try:
                    chunk_uuids.append(uuid.UUID(cid))
                except ValueError:
                    # Maybe it's a number like "0001", skip for now
                    logger.warning(f"Could not parse chunk ID as UUID: {cid}")
            
            if not chunk_uuids:
                return []
            
            async with async_session_maker() as session:
                result = await session.execute(
                    select(ChunkModel)
                    .where(ChunkModel.document_id == doc_uuid)
                    .where(ChunkModel.id.in_(chunk_uuids))
                )
                chunks_db = result.scalars().all()
                
                # Convert to old Chunk dataclass format
                return [
                    ChunkRecord(
                        chunk_id=str(c.id),
                        text=c.text,
                        metadata={
                            "document_id": str(c.document_id),
                            "page_id": str(c.page_id) if c.page_id else None,
                        }
                    )
                    for c in chunks_db
                ]
        
        return self._run_sync(do_fetch())
    
    def upload_images_to_anthropic(
        self,
        document_id: str,
        image_ids: List[str]
    ) -> Dict[str, Any]:
        """
        Upload images to Anthropic for vision analysis.
        
        Replaces loading from local extraction/ dir with StorageService.
        """
        doc_uuid = uuid.UUID(document_id)
        
        async def do_upload():
            # Convert image IDs to UUIDs
            figure_uuids = [uuid.UUID(iid) for iid in image_ids]
            
            async with async_session_maker() as session:
                result = await session.execute(
                    select(FigureModel)
                    .where(FigureModel.document_id == doc_uuid)
                    .where(FigureModel.id.in_(figure_uuids))
                )
                figures = result.scalars().all()
            
            uploaded = []
            for figure in figures:
                if figure.storage_uri:
                    # Get image bytes from storage
                    image_bytes = await self.storage.get(figure.storage_uri)
                    
                    # TODO: Upload to Anthropic and get cache token
                    # For now, return metadata
                    uploaded.append({
                        "id": str(figure.id),
                        "storage_uri": figure.storage_uri,
                        "size": len(image_bytes),
                        "caption": figure.caption_text,
                    })
            
            return {
                "uploaded": len(uploaded),
                "images": uploaded,
            }
        
        return self._run_sync(do_upload())


# Global registry instance
default_registry = DBSessionRegistry()
