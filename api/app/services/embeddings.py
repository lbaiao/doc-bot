import logging
from typing import List
import asyncio

from langchain_huggingface.embeddings import HuggingFaceEmbeddings

from analyzer.config import default_config

logger = logging.getLogger(__name__)


class EmbeddingsService:
    """
    Facade for embedding operations using HuggingFace models.
    
    Delegates to the existing analyzer embeddings (same model as FAISS wrapper).
    """
    
    def __init__(self):
        """Initialize with the same embedding model used by FaissWrapper."""
        self.model_name = default_config.FAISS_EMBEDDING_MODEL
        logger.info(f"Initializing EmbeddingsService with model: {self.model_name}")
        
        # Initialize HuggingFace embeddings (same as analyzer/faiss_wrapper.py)
        self.embeddings = HuggingFaceEmbeddings(
            model_name=self.model_name,
            encode_kwargs={"normalize_embeddings": True}
        )
    
    async def embed_text(self, text: str) -> List[float]:
        """
        Generate text embedding using HuggingFace model.
        
        Uses the same embedding model as the existing FAISS wrapper for consistency.
        """
        # Run in executor since HuggingFace embeddings are sync
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(
            None,
            self.embeddings.embed_query,
            text
        )
        return embedding
    
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts (batch operation).
        
        More efficient than calling embed_text multiple times.
        """
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            None,
            self.embeddings.embed_documents,
            texts
        )
        return embeddings
    
    async def embed_image(self, image_bytes: bytes) -> List[float]:
        """
        Generate image embedding.
        
        NOTE: For now, we use CLIP or similar via caption-based embedding.
        TODO: Integrate proper image embedding model if needed.
        """
        # For MVP, we'll embed the image caption instead of the raw image
        # This is what the existing code does (caption-based search)
        logger.warning(
            "Direct image embedding not implemented yet. "
            "Use caption-based embedding via embed_text(caption) instead."
        )
        raise NotImplementedError(
            "Direct image embedding requires CLIP or similar vision model. "
            "For now, use caption-based search via embed_text()."
        )
    
    async def embed_table(self, table_data: dict) -> List[float]:
        """
        Generate table embedding by embedding a text representation.
        
        Combines caption + headers + sample rows into text for embedding.
        """
        # Create text representation of table
        parts = []
        
        if table_data.get("caption"):
            parts.append(f"Caption: {table_data['caption']}")
        
        if table_data.get("schema_json"):
            schema = table_data["schema_json"]
            if isinstance(schema, dict) and "columns" in schema:
                cols = schema["columns"]
                parts.append(f"Columns: {', '.join(cols)}")
        
        # Combine into text and embed
        text = " ".join(parts) if parts else "table"
        return await self.embed_text(text)
