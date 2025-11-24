import uuid
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.storage import StorageService
from app.services.embeddings import EmbeddingsService


class IngestionService:
    """
    Facade for document ingestion and indexing.
    
    TODO: Wire this to core ingestion/ETL services.
    This orchestrates: PDF parsing → text/figure/table extraction → embedding → vector DB indexing.
    DO NOT implement parsing/extraction logic here - only call into core services.
    """
    
    def __init__(
        self,
        session: AsyncSession,
        storage: StorageService,
        embeddings: EmbeddingsService
    ):
        self.session = session
        self.storage = storage
        self.embeddings = embeddings
    
    async def ingest_document(self, document_id: uuid.UUID) -> None:
        """
        Full ETL pipeline for a document:
        1. Load PDF from storage
        2. Extract pages, text, figures, tables (delegate to core PdfExtractor)
        3. Generate embeddings (delegate to core embedding services)
        4. Index in vector DB
        5. Update document status
        
        TODO: Wire to existing preprocessing.pdf_extraction.PdfExtractor and related services.
        Import and orchestrate existing core logic - do not reimplement.
        """
        raise NotImplementedError(
            "TODO: Wire to core ingestion pipeline. "
            "Use existing PdfExtractor from preprocessing module. "
            "This should orchestrate: "
            "1. Fetch document row from DB "
            "2. Get PDF bytes from storage "
            "3. Call PdfExtractor.extract_all() "
            "4. Store extracted data in DB (pages, chunks, figures, tables) "
            "5. Generate and store embeddings "
            "6. Index in vector DB "
            "7. Update document status to 'ready' or 'failed'"
        )
