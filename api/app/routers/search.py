from fastapi import APIRouter, Depends, HTTPException, UploadFile, File

from app.core.dependencies import RetrievalDep
from app.core.security import current_active_user
from app.db.models.user import User
from app.db.schemas.search import (
    ChunkHit,
    FigureHit,
    ImageSearchRequest,
    TableHit,
    TableSearchRequest,
    TextSearchRequest,
)

router = APIRouter(prefix="/search", tags=["search"])


@router.post("/text", response_model=list[ChunkHit])
async def search_text(
    request: TextSearchRequest,
    retrieval: RetrievalDep = None,
    current_user: User = Depends(current_active_user),
):
    """
    Search text chunks using semantic search.
    
    Returns ranked chunks with provenance information.
    """
    try:
        results = await retrieval.search_text(
            user_id=current_user.id,
            query=request.query,
            document_ids=request.document_ids,
            top_k=request.top_k,
        )
        return results
    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e))


@router.post("/image", response_model=list[FigureHit])
async def search_image(
    request: ImageSearchRequest,
    retrieval: RetrievalDep = None,
    current_user: User = Depends(current_active_user),
):
    """
    Search figures using text query or image similarity.
    
    Supports:
    - Text-to-image search (query_text)
    - Image-to-image search (image_id)
    """
    try:
        results = await retrieval.search_image(
            user_id=current_user.id,
            query_text=request.query_text,
            image_bytes=None,
            image_id=request.image_id,
            top_k=request.top_k,
        )
        return results
    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e))


@router.post("/table", response_model=list[TableHit])
async def search_table(
    request: TableSearchRequest,
    retrieval: RetrievalDep = None,
    current_user: User = Depends(current_active_user),
):
    """
    Search tables using semantic or structured query.
    
    Returns ranked tables with schema and data URI.
    """
    try:
        results = await retrieval.search_table(
            user_id=current_user.id,
            query=request.query,
            filters=request.filters,
            top_k=request.top_k,
        )
        return results
    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e))
