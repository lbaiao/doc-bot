import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.chat import Message


class ChatService:
    """
    Facade for chat orchestration and agent interaction.
    
    TODO: Wire this to core agent/chat services.
    This should delegate to existing LangGraph agent logic.
    DO NOT implement agent/LLM logic here - only call into core services.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def post_message(
        self,
        chat_id: uuid.UUID,
        user_id: uuid.UUID,
        content: dict
    ) -> Message:
        """
        Post a user message and orchestrate agent response.
        
        This should:
        1. Store user message in DB
        2. Call core agent to process message (delegate to agents.agent module)
        3. Store assistant response and tool runs
        4. Return assistant message
        
        TODO: Wire to existing agents.agent logic (LangGraph agent).
        Use existing agent.py and tools.py from agents module.
        """
        raise NotImplementedError(
            "TODO: Wire to core agent/chat service. "
            "Use existing agents.agent module with LangGraph. "
            "1. Store user message in messages table "
            "2. Load chat context and relevant documents "
            "3. Call agent with message and context "
            "4. Store tool runs in tool_runs table "
            "5. Store assistant response in messages table "
            "6. Return assistant message"
        )
