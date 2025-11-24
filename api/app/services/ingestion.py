import uuid
import logging
import os
import tempfile
from pathlib import Path
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import pandas as pd

from app.services.storage import StorageService
from app.services.embeddings import EmbeddingsService
from app.services.vector_db import get_vector_db
from app.db.models.document import Document, Page, Chunk, Figure
from preprocessing.pdf_extraction import PdfExtractor
from preprocessing.chunker import TextChunker

logger = logging.getLogger(__name__)


class IngestionService:
    """
    Facade for document ingestion and indexing.
    
    Orchestrates: PDF parsing → text/figure/table extraction → embedding → vector DB indexing.
    Delegates to existing PdfExtractor, then persists to Postgres + Qdrant.
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
        self.vector_db = get_vector_db()
    
    async def ingest_document(self, document_id: uuid.UUID) -> None:
        """
        Full ETL pipeline for a document:
        1. Load PDF from storage
        2. Extract pages, text, figures using PdfExtractor
        3. Store metadata in Postgres
        4. Generate embeddings
        5. Index in Qdrant
        6. Update document status
        """
        try:
            logger.info(f"Starting ingestion for document {document_id}")
            
            # 1. Fetch document from DB
            result = await self.session.execute(
                select(Document).where(Document.id == document_id)
            )
            document = result.scalar_one_or_none()
            
            if not document:
                raise ValueError(f"Document {document_id} not found")
            
            if document.status != "ingesting":
                logger.warning(f"Document {document_id} status is {document.status}, skipping")
                return
            
            # 2. Get PDF bytes from storage
            logger.info(f"Loading PDF from storage: {document.storage_uri}")
            pdf_bytes = await self.storage.get(document.storage_uri)
            
            # 3. Save to temp file and extract using PdfExtractor
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
                tmp_file.write(pdf_bytes)
                tmp_path = tmp_file.name
            
            try:
                # Use existing PdfExtractor - call extract_all() which does everything
                logger.info("Running PdfExtractor.extract_all()...")
                extractor = PdfExtractor(tmp_path)
                
                # This calls:
                # - extract_text()
                # - extract_bitmap_images()
                # - extract_vector_graphics()
                # - extract_text_chunks()
                # - extract_lucene_index() (Whoosh)
                # - extract_embeddings() (FAISS for text chunks + image captions)
                extractor.extract_all()
                
                logger.info("Extraction complete. Saving to Postgres + Qdrant...")
                
                # 4. Parse extracted data and save to Postgres + Qdrant
                await self._save_extraction_to_db(document, extractor)
                
                # Clean up
                extractor.close()
            
            finally:
                # Cleanup temp file
                os.unlink(tmp_path)
            
            # 5. Update document status
            document.status = "ready"
            await self.session.commit()
            
            logger.info(f"Successfully ingested document {document_id}")
            
        except Exception as e:
            logger.error(f"Error ingesting document {document_id}: {e}", exc_info=True)
            
            # Update status to failed
            try:
                result = await self.session.execute(
                    select(Document).where(Document.id == document_id)
                )
                document = result.scalar_one_or_none()
                if document:
                    document.status = "failed"
                    await self.session.commit()
            except Exception as rollback_err:
                logger.error(f"Error updating document status: {rollback_err}")
            
            raise
    
    async def _save_extraction_to_db(self, document: Document, extractor: PdfExtractor):
        """Save extracted data from PdfExtractor to Postgres and Qdrant."""
        logger.info("Saving extraction data to database...")
        
        # Get document pages from PyMuPDF
        doc = extractor.doc
        
        # 1. Save pages
        pages_map = {}  # page_no -> Page object
        for page_index in range(len(doc)):
            page = doc[page_index]
            rect = page.rect
            
            # Get page text
            page_text = page.get_text()
            
            page_obj = Page(
                document_id=document.id,
                page_no=page_index,
                width=float(rect.width),
                height=float(rect.height),
                text=page_text,
            )
            self.session.add(page_obj)
            pages_map[page_index] = page_obj
        
        await self.session.flush()  # Get page IDs
        
        # 2. Save chunks and generate embeddings
        await self._save_chunks(document, extractor, pages_map)
        
        # 3. Save figures
        await self._save_figures(document, extractor, pages_map)
        
        await self.session.commit()
        logger.info("Extraction data saved successfully")
    
    async def _save_chunks(self, document: Document, extractor: PdfExtractor, pages_map: dict):
        """Save text chunks to Postgres and embeddings to Qdrant."""
        logger.info("Processing text chunks...")
        
        # Read chunk files
        chunk_dir = os.path.join(extractor.output_dir, "chunks")
        if not os.path.exists(chunk_dir):
            logger.warning(f"Chunk directory not found: {chunk_dir}")
            return
        
        chunk_files = sorted([f for f in os.listdir(chunk_dir) if f.endswith(".txt")])
        
        chunks_data = []
        chunk_texts = []
        
        for chunk_file in chunk_files:
            chunk_path = os.path.join(chunk_dir, chunk_file)
            with open(chunk_path, "r", encoding="utf-8") as f:
                text = f.read()
            
            # Create chunk record
            chunk_obj = Chunk(
                document_id=document.id,
                page_id=pages_map[0].id,  # TODO: Better page mapping
                start_char=0,  # TODO: Track actual positions
                end_char=len(text),
                text=text,
            )
            self.session.add(chunk_obj)
            chunks_data.append({
                "chunk_id": chunk_obj.id,
                "text": text,
                "page_id": chunk_obj.page_id,
                "start_char": chunk_obj.start_char,
                "end_char": chunk_obj.end_char,
            })
            chunk_texts.append(text)
        
        await self.session.flush()  # Get chunk IDs
        
        # Generate embeddings in batch
        if chunk_texts:
            logger.info(f"Generating embeddings for {len(chunk_texts)} chunks...")
            embeddings = await self.embeddings.embed_texts(chunk_texts)
            
            # Store in Qdrant
            logger.info("Storing embeddings in Qdrant...")
            point_ids = self.vector_db.upsert_text_chunks(
                chunks=chunks_data,
                embeddings=embeddings,
                document_id=document.id,
                user_id=document.owner_id,
            )
            
            logger.info(f"Stored {len(point_ids)} chunk embeddings")
    
    async def _save_figures(self, document: Document, extractor: PdfExtractor, pages_map: dict):
        """Save figures to Postgres and generate embeddings for Qdrant."""
        logger.info("Processing figures...")
        
        # Read figures metadata from parquet
        parquet_path = extractor.parquet_path
        if not os.path.exists(parquet_path):
            logger.warning(f"Figures parquet not found: {parquet_path}")
            return
        
        df = pd.read_parquet(parquet_path)
        
        figures_data = []
        figure_captions = []
        
        for _, row in df.iterrows():
            page_index = int(row["page_index"])
            page_obj = pages_map.get(page_index)
            
            if not page_obj:
                logger.warning(f"Page {page_index} not found for figure")
                continue
            
            # Save image file to storage
            image_path = row["image_path"]
            if os.path.exists(image_path):
                with open(image_path, "rb") as f:
                    image_bytes = f.read()
                
                storage_uri = await self.storage.put(
                    image_bytes,
                    f"figures/{document.id}/{os.path.basename(image_path)}"
                )
            else:
                storage_uri = None
            
            caption = row.get("caption", "")
            
            figure_obj = Figure(
                document_id=document.id,
                page_id=page_obj.id,
                figure_no=int(row["image_index"]),
                caption_text=caption,
                storage_uri=storage_uri,
                bbox_json={
                    "width": int(row["width"]),
                    "height": int(row["height"]),
                }
            )
            self.session.add(figure_obj)
            
            # Store for embedding generation
            figures_data.append({
                "figure_id": figure_obj.id,
                "page_id": figure_obj.page_id,
                "caption": caption,
                "storage_uri": storage_uri,
            })
            figure_captions.append(caption or "image")  # Fallback if no caption
        
        await self.session.flush()  # Get figure IDs
        
        # Generate embeddings for captions
        if figure_captions:
            logger.info(f"Generating embeddings for {len(figure_captions)} figure captions...")
            embeddings = await self.embeddings.embed_texts(figure_captions)
            
            # Store in Qdrant
            logger.info("Storing figure embeddings in Qdrant...")
            point_ids = self.vector_db.upsert_image_embeddings(
                images=figures_data,
                embeddings=embeddings,
                document_id=document.id,
                user_id=document.owner_id,
            )
            
            logger.info(f"Stored {len(point_ids)} figure embeddings")
        
        logger.info(f"Saved {len(df)} figures")
