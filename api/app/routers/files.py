import mimetypes

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import select

from app.core.dependencies import SessionDep, StorageDep
from app.core.security import current_active_user
from app.db.models.document import Document, Figure
from app.db.models.user import User

router = APIRouter(prefix="/files", tags=["files"])


@router.get("")
async def get_file_by_storage_uri(
    uri: str = Query(..., description="Storage URI (e.g. local://documents/...)"),
    session: SessionDep = None,
    storage: StorageDep = None,
    current_user: User = Depends(current_active_user),
):
    """
    Stream a file referenced by storage URI after ownership validation.

    Allowed only when the URI belongs to a document or figure owned by the current user.
    """
    document_result = await session.execute(
        select(Document).where(
            Document.storage_uri == uri,
            Document.owner_id == current_user.id,
        )
    )
    owned_document = document_result.scalar_one_or_none()

    figure_result = await session.execute(
        select(Figure)
        .join(Document, Figure.document_id == Document.id)
        .where(
            Figure.storage_uri == uri,
            Document.owner_id == current_user.id,
        )
    )
    owned_figure = figure_result.scalar_one_or_none()

    if not owned_document and not owned_figure:
        raise HTTPException(status_code=404, detail="File not found")

    try:
        file_bytes = await storage.get(uri)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to read file: {exc}")

    content_type = "application/octet-stream"
    if owned_document and owned_document.mime:
        content_type = owned_document.mime
    else:
        guessed = mimetypes.guess_type(uri)[0]
        if guessed:
            content_type = guessed

    return Response(content=file_bytes, media_type=content_type)
