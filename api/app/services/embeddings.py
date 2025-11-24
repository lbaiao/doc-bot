from typing import Protocol
import uuid


class EmbeddingsService:
    """
    Facade for embedding operations.
    
    TODO: Wire this to core embedding services (text, image, table).
    This is a thin adapter that delegates to the existing core application services.
    DO NOT implement embedding logic here - only call into core services.
    """
    
    async def embed_text(self, text: str) -> list[float]:
        """
        Generate text embedding.
        
        TODO: Delegate to core text embedding service.
        """
        raise NotImplementedError(
            "TODO: Wire to core text embedding service. "
            "Import and call existing embedding logic from core app."
        )
    
    async def embed_image(self, image_bytes: bytes) -> list[float]:
        """
        Generate image embedding.
        
        TODO: Delegate to core image embedding service.
        """
        raise NotImplementedError(
            "TODO: Wire to core image embedding service. "
            "Import and call existing embedding logic from core app."
        )
    
    async def embed_table(self, table_data: dict) -> list[float]:
        """
        Generate table embedding.
        
        TODO: Delegate to core table embedding service.
        """
        raise NotImplementedError(
            "TODO: Wire to core table embedding service. "
            "Import and call existing embedding logic from core app."
        )
