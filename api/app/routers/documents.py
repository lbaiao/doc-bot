import hashlib
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import IngestionDep, SessionDep, StorageDep
from app.core.security import current_active_user
from app.db.models.document import Document, Figure, Page, Table
from app.db.models.user import User
from app.db.schemas.document import DocumentOut, FigureOut, PageOut, TableOut, UploadResult
from app.core.config import settings

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post(":upload", response_model=UploadResult, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    file: UploadFile = File(...),
    session: SessionDep = None,
    storage: StorageDep = None,
    ingestion: IngestionDep = None,
    current_user: User = Depends(current_active_user),
):
    """
    Upload a PDF document for processing.
    
    Creates a document record with status='ingesting' and enqueues ETL task.
    """
    # Validate file type
    if file.content_type not in settings.ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {settings.ALLOWED_MIME_TYPES}"
        )
    
    # Read file
    file_bytes = await file.read()
    file_size = len(file_bytes)
    
    # Validate size
    max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if file_size > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Max size: {settings.MAX_UPLOAD_SIZE_MB}MB"
        )
    
    # Calculate hash
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    
    # Store file
    doc_id = uuid.uuid4()
    storage_uri = await storage.put(file_bytes, f"documents/{doc_id}/{file.filename}")
    
    # Create document record
    document = Document(
        id=doc_id,
        owner_id=current_user.id,
        title=file.filename,
        status="ingesting",
        original_filename=file.filename,
        mime=file.content_type,
        bytes_size=file_size,
        storage_uri=storage_uri,
        hash_sha256=file_hash,
    )
    
    session.add(document)
    await session.commit()
    
    # Run ingestion inline for now so pages/figures/tables are available after upload
    await ingestion.ingest_document(doc_id)
    
    return UploadResult(document_id=doc_id)


@router.get("/{document_id}", response_model=DocumentOut)
async def get_document(
    document_id: uuid.UUID,
    session: SessionDep = None,
    current_user: User = Depends(current_active_user),
):
    """Get document metadata and status."""
    result = await session.execute(
        select(Document).where(
            Document.id == document_id,
            Document.owner_id == current_user.id
        )
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return document


@router.get("/{document_id}/pages", response_model=list[PageOut])
async def get_document_pages(
    document_id: uuid.UUID,
    session: SessionDep = None,
    current_user: User = Depends(current_active_user),
):
    """Get all pages for a document."""
    # Verify ownership
    result = await session.execute(
        select(Document).where(
            Document.id == document_id,
            Document.owner_id == current_user.id
        )
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Get pages
    result = await session.execute(
        select(Page)
        .where(Page.document_id == document_id)
        .order_by(Page.page_no)
    )
    pages = result.scalars().all()
    
    return pages


@router.get("/{document_id}/figures", response_model=list[FigureOut])
async def get_document_figures(
    document_id: uuid.UUID,
    session: SessionDep = None,
    current_user: User = Depends(current_active_user),
):
    """Get all figures for a document."""
    # Verify ownership
    result = await session.execute(
        select(Document).where(
            Document.id == document_id,
            Document.owner_id == current_user.id
        )
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Get figures
    result = await session.execute(
        select(Figure)
        .where(Figure.document_id == document_id)
        .order_by(Figure.page_id, Figure.figure_no)
    )
    figures = result.scalars().all()
    
    return figures


@router.get("/{document_id}/tables", response_model=list[TableOut])
async def get_document_tables(
    document_id: uuid.UUID,
    session: SessionDep = None,
    current_user: User = Depends(current_active_user),
):
    """Get all tables for a document."""
    # Verify ownership
    result = await session.execute(
        select(Document).where(
            Document.id == document_id,
            Document.owner_id == current_user.id
        )
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Get tables
    result = await session.execute(
        select(Table)
        .where(Table.document_id == document_id)
        .order_by(Table.page_id, Table.table_no)
    )
    tables = result.scalars().all()
    
    return tables


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    session: SessionDep = None,
    storage: StorageDep = None,
    current_user: User = Depends(current_active_user),
):
    """Delete a document and all associated data."""
    result = await session.execute(
        select(Document).where(
            Document.id == document_id,
            Document.owner_id == current_user.id
        )
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Delete from storage
    try:
        await storage.delete(document.storage_uri)
    except Exception as e:
        # Log but don't fail if storage delete fails
        pass
    
    # Delete from database (cascades to pages, chunks, figures, tables)
    await session.delete(document)
    await session.commit()
    
    return None


@router.post("/{document_id}:reindex", status_code=status.HTTP_202_ACCEPTED)
async def reindex_document(
    document_id: uuid.UUID,
    session: SessionDep = None,
    ingestion: IngestionDep = None,
    current_user: User = Depends(current_active_user),
):
    """Re-run ETL pipeline for a document."""
    result = await session.execute(
        select(Document).where(
            Document.id == document_id,
            Document.owner_id == current_user.id
        )
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Update status
    document.status = "ingesting"
    await session.commit()
    
    # Run ingestion inline
    await ingestion.ingest_document(document_id)
    
    return {"message": "Reindexing started"}
