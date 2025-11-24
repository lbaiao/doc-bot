import uuid
import logging
import asyncio
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models.chat import Message, Chat, ToolRun
from agents.agent import make_document_agent

logger = logging.getLogger(__name__)


class ChatService:
    """
    Facade for chat orchestration and agent interaction.
    
    Delegates to existing LangGraph agent (agents.agent module).
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self._agent = None
    
    def _get_agent(self):
        """Lazy-load the agent."""
        if self._agent is None:
            logger.info("Initializing document agent...")
            self._agent = make_document_agent()
        return self._agent
    
    async def post_message(
        self,
        chat_id: uuid.UUID,
        user_id: uuid.UUID,
        content: dict
    ) -> Message:
        """
        Post a user message and orchestrate agent response.
        
        Flow:
        1. Store user message in DB
        2. Load chat context
        3. Call agent with message
        4. Store tool runs
        5. Store assistant response
        6. Return assistant message
        """
        logger.info(f"Processing message for chat {chat_id}")
        
        # 1. Verify chat exists and user owns it
        result = await self.session.execute(
            select(Chat).where(Chat.id == chat_id, Chat.owner_id == user_id)
        )
        chat = result.scalar_one_or_none()
        
        if not chat:
            raise ValueError(f"Chat {chat_id} not found or access denied")
        
        # 2. Store user message
        user_message = Message(
            chat_id=chat_id,
            role="user",
            content=content,
        )
        self.session.add(user_message)
        await self.session.flush()
        
        # 3. Get chat history for context
        history_result = await self.session.execute(
            select(Message)
            .where(Message.chat_id == chat_id)
            .order_by(Message.created_at)
            .limit(20)  # Last 20 messages
        )
        history = history_result.scalars().all()
        
        # 4. Build messages for agent
        agent_messages = []
        for msg in history[:-1]:  # Exclude the message we just added
            agent_messages.append({
                "role": msg.role,
                "content": msg.content.get("text", "") if isinstance(msg.content, dict) else str(msg.content)
            })
        
        # Add the new user message
        user_text = content.get("text", "") if isinstance(content, dict) else str(content)
        agent_messages.append({
            "role": "user",
            "content": user_text
        })
        
        # 5. Set up agent context (user + document)
        from session.db_registry import default_registry
        default_registry.set_user(user_id)
        
        # TODO: If chat has associated documents, set active document
        # For now, agent tools will need document_id passed explicitly
        
        # 6. Call agent in executor (agent is sync)
        try:
            logger.info(f"Calling agent with message: {user_text[:100]}")
            
            agent = self._get_agent()
            loop = asyncio.get_event_loop()
            
            # Run agent in executor since it's synchronous
            agent_response = await loop.run_in_executor(
                None,
                lambda: agent.invoke({"messages": agent_messages})
            )
            
            logger.info(f"Agent response received")
            
            # Extract response text
            if isinstance(agent_response, dict) and "messages" in agent_response:
                last_message = agent_response["messages"][-1]
                response_text = last_message.get("content", "") if isinstance(last_message, dict) else str(last_message)
            else:
                response_text = str(agent_response)
            
            # 6. Store assistant message
            assistant_message = Message(
                chat_id=chat_id,
                role="assistant",
                content={"text": response_text},
            )
            self.session.add(assistant_message)
            
            # 7. Store tool runs if available
            # TODO: Extract tool invocations from agent response
            # For now, this is a simplified version
            if isinstance(agent_response, dict) and "tool_calls" in agent_response:
                for tool_call in agent_response["tool_calls"]:
                    tool_run = ToolRun(
                        chat_id=chat_id,
                        message_id=assistant_message.id,
                        tool_name=tool_call.get("name", "unknown"),
                        status="completed",
                        request_payload=tool_call.get("args"),
                        response_payload=tool_call.get("result"),
                        latency_ms=0,  # TODO: Track actual latency
                    )
                    self.session.add(tool_run)
            
            await self.session.commit()
            await self.session.refresh(assistant_message)
            
            logger.info(f"Assistant message stored: {assistant_message.id}")
            return assistant_message
            
        except Exception as e:
            logger.error(f"Error calling agent: {e}", exc_info=True)
            
            # Store error message
            error_message = Message(
                chat_id=chat_id,
                role="assistant",
                content={
                    "text": f"Sorry, I encountered an error processing your request: {str(e)}",
                    "error": True
                },
            )
            self.session.add(error_message)
            await self.session.commit()
            await self.session.refresh(error_message)
            
            return error_message
