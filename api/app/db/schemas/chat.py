import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class ChatCreateIn(BaseModel):
    title: Optional[str] = None
    document_ids: Optional[list[uuid.UUID]] = None


class ChatOut(BaseModel):
    id: uuid.UUID
    title: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class MessageIn(BaseModel):
    # Accept either plain text or structured payloads
    content: str | dict


class MessageOut(BaseModel):
    id: uuid.UUID
    role: Literal["user", "assistant", "system"]
    content: dict
    created_at: datetime
    
    class Config:
        from_attributes = True
