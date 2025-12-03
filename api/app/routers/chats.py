import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.dependencies import ChatDep, SessionDep
from app.core.security import current_active_user
from app.db.models.chat import Chat, Message
from app.db.models.user import User
from app.db.schemas.chat import ChatCreateIn, ChatOut, MessageIn, MessageOut

router = APIRouter(prefix="/chats", tags=["chats"])


@router.post("", response_model=ChatOut, status_code=status.HTTP_201_CREATED)
async def create_chat(
    chat_in: ChatCreateIn,
    session: SessionDep = None,
    current_user: User = Depends(current_active_user),
):
    """Create a new chat session."""
    title = chat_in.title or "New Chat"
    
    chat = Chat(
        owner_id=current_user.id,
        title=title,
    )
    
    session.add(chat)
    await session.commit()
    await session.refresh(chat)
    
    # TODO: If document_ids provided, associate them with the chat
    # Need to create a chat_documents association table
    
    return chat


@router.get("", response_model=list[ChatOut])
async def list_chats(
    session: SessionDep = None,
    current_user: User = Depends(current_active_user),
):
    """List all chats for the current user."""
    result = await session.execute(
        select(Chat)
        .where(Chat.owner_id == current_user.id)
        .order_by(Chat.created_at.desc())
    )
    chats = result.scalars().all()
    
    return chats


@router.get("/{chat_id}", response_model=ChatOut)
async def get_chat(
    chat_id: uuid.UUID,
    session: SessionDep = None,
    current_user: User = Depends(current_active_user),
):
    """Get chat details."""
    result = await session.execute(
        select(Chat).where(
            Chat.id == chat_id,
            Chat.owner_id == current_user.id
        )
    )
    chat = result.scalar_one_or_none()
    
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    return chat


@router.post("/{chat_id}/messages", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
async def post_message(
    chat_id: uuid.UUID,
    message_in: MessageIn,
    session: SessionDep = None,
    chat_service: ChatDep = None,
    current_user: User = Depends(current_active_user),
):
    """
    Post a user message and get agent response.
    
    This endpoint:
    1. Stores the user message
    2. Calls the agent to process it
    3. Stores and returns the assistant response
    """
    # Verify chat exists and user owns it
    result = await session.execute(
        select(Chat).where(
            Chat.id == chat_id,
            Chat.owner_id == current_user.id
        )
    )
    chat = result.scalar_one_or_none()
    
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    # Store user message
    # Delegate to chat service (persists user/assistant messages)
    assistant_message = await chat_service.post_message(
        chat_id=chat_id,
        user_id=current_user.id,
        content=message_in.content,
    )
    return assistant_message


@router.get("/{chat_id}/messages", response_model=list[MessageOut])
async def get_messages(
    chat_id: uuid.UUID,
    cursor: Optional[uuid.UUID] = Query(None, description="Pagination cursor (message ID)"),
    limit: int = Query(50, ge=1, le=100),
    session: SessionDep = None,
    current_user: User = Depends(current_active_user),
):
    """Get message history for a chat with pagination."""
    # Verify chat exists and user owns it
    result = await session.execute(
        select(Chat).where(
            Chat.id == chat_id,
            Chat.owner_id == current_user.id
        )
    )
    chat = result.scalar_one_or_none()
    
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    # Build query
    query = select(Message).where(Message.chat_id == chat_id)
    
    if cursor:
        # Get timestamp of cursor message for pagination
        cursor_result = await session.execute(
            select(Message).where(Message.id == cursor)
        )
        cursor_message = cursor_result.scalar_one_or_none()
        if cursor_message:
            query = query.where(Message.created_at > cursor_message.created_at)
    
    query = query.order_by(Message.created_at).limit(limit)
    
    result = await session.execute(query)
    messages = result.scalars().all()
    
    return messages
