import uuid
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.schemas.search import ChunkHit, FigureHit, TableHit
from app.db.models.document import Chunk, Figure, Table
from app.services.embeddings import EmbeddingsService
from app.services.vector_db import get_vector_db

logger = logging.getLogger(__name__)


class RetrievalService:
    """
    Facade for search and retrieval operations.
    
    Uses Qdrant for vector search + Postgres for metadata enrichment.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.vector_db = get_vector_db()
        self.embeddings = EmbeddingsService()
    
    async def search_text(
        self,
        user_id: uuid.UUID,
        query: str,
        document_ids: Optional[list[uuid.UUID]],
        top_k: int
    ) -> list[ChunkHit]:
        """
        Search text chunks using semantic search via Qdrant.
        
        1. Generate query embedding
        2. Search Qdrant with document_ids filter
        3. Enrich with Postgres metadata
        4. Return ranked ChunkHit objects
        """
        logger.info(f"Text search: query='{query}', top_k={top_k}")
        
        # 1. Generate query embedding
        query_embedding = await self.embeddings.embed_text(query)
        
        # 2. Search Qdrant
        vector_results = self.vector_db.search_text(
            query_vector=query_embedding,
            user_id=user_id,
            document_ids=document_ids,
            top_k=top_k,
        )
        
        if not vector_results:
            return []
        
        # 3. Get chunk IDs from results
        chunk_ids = [uuid.UUID(r["chunk_id"]) for r in vector_results]
        
        # 4. Fetch full chunk data from Postgres
        result = await self.session.execute(
            select(Chunk).where(Chunk.id.in_(chunk_ids))
        )
        chunks_db = {str(c.id): c for c in result.scalars().all()}
        
        # 5. Build response with scores
        hits = []
        for vector_result in vector_results:
            chunk_id_str = vector_result["chunk_id"]
            chunk = chunks_db.get(chunk_id_str)
            
            if chunk:
                hits.append(ChunkHit(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    page_id=chunk.page_id,
                    text=chunk.text,
                    score=vector_result["score"],
                    bbox_json=chunk.bbox_json,
                ))
        
        logger.info(f"Found {len(hits)} text results")
        return hits
    
    async def search_image(
        self,
        user_id: uuid.UUID,
        query_text: Optional[str],
        image_bytes: Optional[bytes],
        image_id: Optional[uuid.UUID],
        top_k: int
    ) -> list[FigureHit]:
        """
        Search figures using text query (caption-based search).
        
        For MVP: text-to-image search via captions.
        Image-to-image search requires CLIP or similar vision model.
        """
        if not query_text and not image_id:
            logger.warning("No query text or image_id provided for image search")
            return []
        
        if image_bytes:
            logger.warning("Direct image embedding not implemented, using caption search")
        
        # For now, only support text-to-image via captions
        if query_text:
            logger.info(f"Image search via caption: query='{query_text}', top_k={top_k}")
            
            # Generate embedding for query text
            query_embedding = await self.embeddings.embed_text(query_text)
            
            # Search Qdrant image collection
            vector_results = self.vector_db.search_images(
                query_vector=query_embedding,
                user_id=user_id,
                top_k=top_k,
            )
            
            if not vector_results:
                return []
            
            # Get figure IDs
            figure_ids = [uuid.UUID(r["figure_id"]) for r in vector_results]
            
            # Fetch from Postgres
            result = await self.session.execute(
                select(Figure).where(Figure.id.in_(figure_ids))
            )
            figures_db = {str(f.id): f for f in result.scalars().all()}
            
            # Build response
            hits = []
            for vector_result in vector_results:
                figure_id_str = vector_result["figure_id"]
                figure = figures_db.get(figure_id_str)
                
                if figure:
                    hits.append(FigureHit(
                        figure_id=figure.id,
                        document_id=figure.document_id,
                        page_id=figure.page_id,
                        caption_text=figure.caption_text,
                        storage_uri=figure.storage_uri,
                        score=vector_result["score"],
                        bbox_json=figure.bbox_json,
                    ))
            
            logger.info(f"Found {len(hits)} image results")
            return hits
        
        # If only image_id provided, find similar images
        if image_id:
            # Fetch the reference image's embedding from Qdrant
            # Then search for similar ones
            # TODO: Implement image-to-image search
            logger.warning("Image-to-image search not yet implemented")
            return []
        
        return []
    
    async def search_table(
        self,
        user_id: uuid.UUID,
        query: str,
        filters: Optional[dict],
        top_k: int
    ) -> list[TableHit]:
        """
        Search tables using semantic search via embeddings.
        
        Tables are embedded via their captions + schema information.
        """
        logger.info(f"Table search: query='{query}', top_k={top_k}")
        
        # Generate query embedding
        query_embedding = await self.embeddings.embed_text(query)
        
        # Search Qdrant
        vector_results = self.vector_db.search_tables(
            query_vector=query_embedding,
            user_id=user_id,
            top_k=top_k,
        )
        
        if not vector_results:
            return []
        
        # Get table IDs
        table_ids = [uuid.UUID(r["table_id"]) for r in vector_results]
        
        # Fetch from Postgres
        result = await self.session.execute(
            select(Table).where(Table.id.in_(table_ids))
        )
        tables_db = {str(t.id): t for t in result.scalars().all()}
        
        # Build response
        hits = []
        for vector_result in vector_results:
            table_id_str = vector_result["table_id"]
            table = tables_db.get(table_id_str)
            
            if table:
                hits.append(TableHit(
                    table_id=table.id,
                    document_id=table.document_id,
                    page_id=table.page_id,
                    caption_text=table.caption_text,
                    table_schema=table.schema_json,  # Map DB field to schema field
                    data_uri=table.data_uri,
                    score=vector_result["score"],
                    bbox_json=table.bbox_json,
                ))
        
        logger.info(f"Found {len(hits)} table results")
        return hits
