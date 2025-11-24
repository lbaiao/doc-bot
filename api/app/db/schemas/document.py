import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class DocumentOut(BaseModel):
    id: uuid.UUID
    title: str
    status: Literal["ingesting", "ready", "failed"]
    original_filename: str
    mime: str
    bytes_size: int
    storage_uri: str
    hash_sha256: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class PageOut(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    page_no: int
    width: float
    height: float
    text: Optional[str] = None
    
    class Config:
        from_attributes = True


class FigureOut(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    page_id: uuid.UUID
    figure_no: int
    bbox_json: Optional[dict] = None
    caption_text: Optional[str] = None
    ocr_text: Optional[str] = None
    storage_uri: Optional[str] = None
    phash: Optional[str] = None
    
    class Config:
        from_attributes = True


class TableOut(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    page_id: uuid.UUID
    table_no: int
    bbox_json: Optional[dict] = None
    caption_text: Optional[str] = None
    schema_json: Optional[dict] = None
    data_uri: Optional[str] = None
    
    class Config:
        from_attributes = True


class UploadResult(BaseModel):
    document_id: uuid.UUID
