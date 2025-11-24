import uuid
from typing import Optional

from pydantic import BaseModel


class TextSearchRequest(BaseModel):
    query: str
    document_ids: Optional[list[uuid.UUID]] = None
    top_k: int = 10


class ImageSearchRequest(BaseModel):
    query_text: Optional[str] = None
    image_id: Optional[uuid.UUID] = None
    top_k: int = 10


class TableSearchRequest(BaseModel):
    query: str
    filters: Optional[dict] = None
    top_k: int = 10


class ChunkHit(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    page_id: uuid.UUID
    text: str
    score: float
    bbox_json: Optional[dict] = None
    
    class Config:
        from_attributes = True


class FigureHit(BaseModel):
    figure_id: uuid.UUID
    document_id: uuid.UUID
    page_id: uuid.UUID
    caption_text: Optional[str] = None
    storage_uri: Optional[str] = None
    score: float
    bbox_json: Optional[dict] = None
    
    class Config:
        from_attributes = True


class TableHit(BaseModel):
    model_config = {"from_attributes": True}
    
    table_id: uuid.UUID
    document_id: uuid.UUID
    page_id: uuid.UUID
    caption_text: Optional[str] = None
    table_schema: Optional[dict] = None  # Renamed to avoid shadowing
    data_uri: Optional[str] = None
    score: float
    bbox_json: Optional[dict] = None
