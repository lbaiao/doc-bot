"""
Qdrant vector database client wrapper.

Handles all vector operations for text chunks, images, and tables.
"""
import logging
import uuid
from typing import List, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
    Filter,
    FieldCondition,
    MatchValue,
    MatchText,
    TextIndexParams,
    TokenizerType,
    Fusion,
    FusionQuery,
    FilterSelector,
)

from app.core.config import settings

logger = logging.getLogger(__name__)


class VectorDBClient:
    """Wrapper around Qdrant client for vector operations."""
    
    # Collection names
    COLLECTION_TEXT = "text_chunks"
    COLLECTION_IMAGE = "image_embeddings"
    COLLECTION_TABLE = "table_embeddings"
    
    def __init__(self):
        self.client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY,
        )
        self.text_vector_size = 768
        self._ensure_collections()
    
    def _ensure_collections(self):
        """Create collections if they don't exist."""
        collections = {
            self.COLLECTION_TEXT: 768,    # HuggingFace embeddings dimension
            self.COLLECTION_IMAGE: 768,   # Image embeddings dimension
            self.COLLECTION_TABLE: 768,   # Table embeddings dimension
        }
        self.text_vector_size = collections[self.COLLECTION_TEXT]
        
        existing = {c.name for c in self.client.get_collections().collections}
        
        for collection_name, vector_size in collections.items():
            if collection_name not in existing:
                logger.info(f"Creating Qdrant collection: {collection_name}")
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=vector_size,
                        distance=Distance.COSINE,
                    ),
                )
            
            # Ensure text payload index for lexical queries on text chunks
            if collection_name == self.COLLECTION_TEXT:
                try:
                    self.client.create_payload_index(
                        collection_name=collection_name,
                        field_name="text",
                        field_schema=TextIndexParams(
                            tokenizer=TokenizerType.WORD,
                            min_token_len=2,
                            lowercase=True,
                        ),
                    )
                except Exception as e:
                    # If index exists or server version lacks feature, log and continue
                    logger.debug(f"Payload index for text may already exist: {e}")
    
    # ========== Text Chunks ==========
    
    def upsert_text_chunks(
        self,
        chunks: List[dict],
        embeddings: List[List[float]],
        document_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> List[str]:
        """
        Store text chunk embeddings in Qdrant.
        
        Args:
            chunks: List of dicts with chunk metadata (chunk_id, text, page_id, etc.)
            embeddings: List of embedding vectors
            document_id: Document UUID
            user_id: Owner UUID
            
        Returns:
            List of Qdrant point IDs
        """
        points = []
        point_ids = []
        
        for chunk, embedding in zip(chunks, embeddings):
            point_id = str(uuid.uuid4())
            point_ids.append(point_id)
            
            points.append(
                PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        "chunk_id": str(chunk["chunk_id"]),
                        "document_id": str(document_id),
                        "user_id": str(user_id),
                        "page_id": str(chunk.get("page_id")),
                        "text": chunk.get("text", "")[:1000],  # Store preview
                        "start_char": chunk.get("start_char"),
                        "end_char": chunk.get("end_char"),
                    }
                )
            )
        
        if points:
            self.client.upsert(
                collection_name=self.COLLECTION_TEXT,
                points=points,
            )
            logger.info(f"Upserted {len(points)} text chunks to Qdrant")
        
        return point_ids
    
    def search_text(
        self,
        query_vector: List[float],
        user_id: uuid.UUID,
        document_ids: Optional[List[uuid.UUID]] = None,
        top_k: int = 10,
    ) -> List[dict]:
        """
        Search for similar text chunks using hybrid fusion (vector + lexical).
        """
        # Build filter
        must_conditions = [
            FieldCondition(
                key="user_id",
                match=MatchValue(value=str(user_id)),
            )
        ]
        
        if document_ids:
            must_conditions.append(
                FieldCondition(
                    key="document_id",
                    match=MatchValue(value=str(document_ids[0])) if len(document_ids) == 1 else MatchValue(value=[str(did) for did in document_ids]),
                )
            )
        
        # Hybrid fusion: combine vector similarity with text match on payload "text"
        results = self.client.search(
            collection_name=self.COLLECTION_TEXT,
            query_vector=query_vector,
            query_filter=Filter(must=must_conditions) if must_conditions else None,
            limit=top_k,
            with_vectors=False,
            # Qdrant hybrid: RRF fusion of vector + payload text index
            fusion=FusionQuery(
                fusion=Fusion.RRF,
                query=MatchText(text=""),
            ),
        )
        
        return [
            {
                "score": hit.score,
                "chunk_id": hit.payload.get("chunk_id"),
                "document_id": hit.payload.get("document_id"),
                "page_id": hit.payload.get("page_id"),
                "text": hit.payload.get("text"),
            }
            for hit in results
        ]

    
    # ========== Image Embeddings ==========
    def delete_image_embeddings_for_document(self, document_id: uuid.UUID) -> None:
        """Delete all image embeddings for a document (used before reindex)."""
        try:
            self.client.delete(
                collection_name=self.COLLECTION_IMAGE,
                points_selector=FilterSelector(
                    filter=Filter(
                        must=[
                            FieldCondition(
                                key="document_id",
                                match=MatchValue(value=str(document_id)),
                            )
                        ]
                    )
                ),
            )
            logger.info(f"Deleted image embeddings for document {document_id}")
        except Exception as e:
            logger.warning(f"Failed to delete image embeddings for document {document_id}: {e}")
    
    def upsert_image_embeddings(
        self,
        images: List[dict],
        embeddings: List[List[float]],
        document_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> List[str]:
        """Store image embeddings in Qdrant."""
        points = []
        point_ids = []
        
        for image, embedding in zip(images, embeddings):
            point_id = str(uuid.uuid4())
            point_ids.append(point_id)
            
            points.append(
                PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        "figure_id": str(image["figure_id"]),
                        "document_id": str(document_id),
                        "user_id": str(user_id),
                        "page_id": str(image.get("page_id")),
                        "caption": image.get("caption", ""),
                        "storage_uri": image.get("storage_uri", ""),
                    }
                )
            )
        
        if points:
            self.client.upsert(
                collection_name=self.COLLECTION_IMAGE,
                points=points,
            )
            logger.info(f"Upserted {len(points)} image embeddings to Qdrant")
        
        return point_ids
    
    def search_images(
        self,
        query_vector: List[float],
        user_id: uuid.UUID,
        document_ids: Optional[List[uuid.UUID]] = None,
        top_k: int = 10,
    ) -> List[dict]:
        """Search for similar images."""
        must_conditions = [
            FieldCondition(
                key="user_id",
                match=MatchValue(value=str(user_id)),
            )
        ]
        
        if document_ids:
            if len(document_ids) == 1:
                doc_ids_str = str(document_ids[0])
                match = MatchValue(value=doc_ids_str)
            else:
                doc_ids_str = [str(did) for did in document_ids]
                match = MatchValue(value=doc_ids_str)
            
            must_conditions.append(
                FieldCondition(
                    key="document_id",
                    match=match,
                )
            )
        
        results = self.client.search(
            collection_name=self.COLLECTION_IMAGE,
            query_vector=query_vector,
            query_filter=Filter(must=must_conditions) if must_conditions else None,
            limit=top_k,
        )
        
        return [
            {
                "score": hit.score,
                "figure_id": hit.payload.get("figure_id"),
                "document_id": hit.payload.get("document_id"),
                "page_id": hit.payload.get("page_id"),
                "caption": hit.payload.get("caption"),
                "storage_uri": hit.payload.get("storage_uri"),
            }
            for hit in results
        ]
    
    # ========== Table Embeddings ==========
    
    def upsert_table_embeddings(
        self,
        tables: List[dict],
        embeddings: List[List[float]],
        document_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> List[str]:
        """Store table embeddings in Qdrant."""
        points = []
        point_ids = []
        
        for table, embedding in zip(tables, embeddings):
            point_id = str(uuid.uuid4())
            point_ids.append(point_id)
            
            points.append(
                PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        "table_id": str(table["table_id"]),
                        "document_id": str(document_id),
                        "user_id": str(user_id),
                        "page_id": str(table.get("page_id")),
                        "caption": table.get("caption", ""),
                        "schema_json": table.get("schema_json"),
                    }
                )
            )
        
        if points:
            self.client.upsert(
                collection_name=self.COLLECTION_TABLE,
                points=points,
            )
            logger.info(f"Upserted {len(points)} table embeddings to Qdrant")
        
        return point_ids
    
    def search_tables(
        self,
        query_vector: List[float],
        user_id: uuid.UUID,
        document_ids: Optional[List[uuid.UUID]] = None,
        top_k: int = 10,
    ) -> List[dict]:
        """Search for similar tables."""
        must_conditions = [
            FieldCondition(
                key="user_id",
                match=MatchValue(value=str(user_id)),
            )
        ]
        
        if document_ids:
            must_conditions.append(
                FieldCondition(
                    key="document_id",
                    match=MatchValue(value=[str(did) for did in document_ids]),
                )
            )
        
        results = self.client.search(
            collection_name=self.COLLECTION_TABLE,
            query_vector=query_vector,
            query_filter=Filter(must=must_conditions) if must_conditions else None,
            limit=top_k,
        )
        
        return [
            {
                "score": hit.score,
                "table_id": hit.payload.get("table_id"),
                "document_id": hit.payload.get("document_id"),
                "page_id": hit.payload.get("page_id"),
                "caption": hit.payload.get("caption"),
                "schema_json": hit.payload.get("schema_json"),
            }
            for hit in results
        ]
    
    # ========== Cleanup ==========
    
    def delete_document_vectors(self, document_id: uuid.UUID):
        """Delete all vectors associated with a document."""
        for collection in [self.COLLECTION_TEXT, self.COLLECTION_IMAGE, self.COLLECTION_TABLE]:
            try:
                self.client.delete(
                    collection_name=collection,
                    points_selector=Filter(
                        must=[
                            FieldCondition(
                                key="document_id",
                                match=MatchValue(value=str(document_id)),
                            )
                        ]
                    ),
                )
                logger.info(f"Deleted vectors for document {document_id} from {collection}")
            except Exception as e:
                logger.error(f"Error deleting vectors from {collection}: {e}")


# Singleton instance
_vector_db_client: Optional[VectorDBClient] = None


def get_vector_db() -> VectorDBClient:
    """Get or create the vector DB client singleton."""
    global _vector_db_client
    if _vector_db_client is None:
        _vector_db_client = VectorDBClient()
    return _vector_db_client
