import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict


class ChatCreateIn(BaseModel):
    title: Optional[str] = None
    document_ids: Optional[list[uuid.UUID]] = None


class ChatOut(BaseModel):
    id: uuid.UUID
    title: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class MessageIn(BaseModel):
    # Accept either plain text or structured payloads
    content: str | dict


class ToolRunOut(BaseModel):
    tool_name: str
    status: str
    request_payload: Optional[dict] = None
    response_payload: Optional[dict] = None
    latency_ms: Optional[int] = None
    
    model_config = ConfigDict(from_attributes=True)


class MessageOut(BaseModel):
    id: uuid.UUID
    role: Literal["user", "assistant", "system"]
    content: dict
    tool_runs: list[ToolRunOut] = []
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
