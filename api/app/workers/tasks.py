import uuid
import asyncio

from app.workers.celery_app import celery_app


@celery_app.task(name="ingest_document")
def ingest_document_task(document_id: str):
    """
    Background task to ingest a document.
    
    This task:
    1. Calls IngestionService.ingest_document()
    2. Handles the full ETL pipeline
    3. Updates document status on completion/failure
    
    TODO: Wire to IngestionService and handle async context properly.
    """
    # Convert string UUID to UUID object
    doc_uuid = uuid.UUID(document_id)
    
    # TODO: Create async session and call ingestion service
    # This requires setting up async context in Celery worker
    # For now, this is a stub
    
    raise NotImplementedError(
        "TODO: Wire Celery task to IngestionService. "
        "Need to set up async context in Celery worker to call async service methods. "
        "Consider using celery-pool-asyncio or creating sync wrapper."
    )
