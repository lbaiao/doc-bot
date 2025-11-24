import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.schemas.search import ChunkHit, FigureHit, TableHit


class RetrievalService:
    """
    Facade for search and retrieval operations.
    
    TODO: Wire this to core retrieval/search services.
    This should call into existing vector search and ranking logic.
    DO NOT implement search logic here - only call into core services.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def search_text(
        self,
        user_id: uuid.UUID,
        query: str,
        document_ids: Optional[list[uuid.UUID]],
        top_k: int
    ) -> list[ChunkHit]:
        """
        Search text chunks using semantic search.
        
        TODO: Wire to existing FAISS/Whoosh search from analyzer module.
        Use existing faiss_wrapper and woosh_searcher logic.
        """
        raise NotImplementedError(
            "TODO: Wire to core text search service. "
            "Use existing analyzer.faiss_wrapper or analyzer.woosh_searcher. "
            "1. Generate query embedding "
            "2. Search vector DB with document_ids filter "
            "3. Retrieve chunk metadata from Postgres "
            "4. Return ranked results as ChunkHit objects"
        )
    
    async def search_image(
        self,
        user_id: uuid.UUID,
        query_text: Optional[str],
        image_bytes: Optional[bytes],
        image_id: Optional[uuid.UUID],
        top_k: int
    ) -> list[FigureHit]:
        """
        Search figures using image or text query.
        
        TODO: Wire to core image search service.
        """
        raise NotImplementedError(
            "TODO: Wire to core image search service. "
            "Support both text-to-image and image-to-image search. "
            "1. Generate query embedding (text or image) "
            "2. Search image embeddings in vector DB "
            "3. Retrieve figure metadata from Postgres "
            "4. Return ranked results as FigureHit objects"
        )
    
    async def search_table(
        self,
        user_id: uuid.UUID,
        query: str,
        filters: Optional[dict],
        top_k: int
    ) -> list[TableHit]:
        """
        Search tables using semantic or structured query.
        
        TODO: Wire to core table search service.
        """
        raise NotImplementedError(
            "TODO: Wire to core table search service. "
            "1. Generate query embedding "
            "2. Search table embeddings in vector DB "
            "3. Apply filters if provided "
            "4. Retrieve table metadata from Postgres "
            "5. Return ranked results as TableHit objects"
        )
