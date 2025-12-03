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
        content: dict | str
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
        
        # 2. Normalize content and store user message
        user_text = content.get("text") if isinstance(content, dict) else str(content)
        document_id = None
        if isinstance(content, dict):
            document_id = content.get("document_id") or content.get("doc_id")
        
        user_message = Message(
            chat_id=chat_id,
            role="user",
            content={"text": user_text, "document_id": document_id} if user_text is not None else {"document_id": document_id},
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
        # Build agent messages (include a system primer)
        agent_messages.append({
            "role": "system",
            "content": "You are a document QA assistant. Use the provided tools to search documents and answer clearly.",
        })
        for msg in history:
            text_content = msg.content.get("text") if isinstance(msg.content, dict) else str(msg.content)
            agent_messages.append({
                "role": msg.role,
                "content": text_content or "",
            })
        
        # 5. Set up agent context (user + document)
        from session.db_registry import default_registry
        # Capture the main loop so registry can schedule coroutines from background threads
        default_registry.set_main_loop(asyncio.get_running_loop())
        default_registry.set_user(user_id)
        if document_id:
            try:
                default_registry.ensure(str(document_id))
            except Exception as e:
                logger.warning(f"Could not set active document {document_id}: {e}")
        
        # 6. Call agent in executor (agent is sync)
        try:
            logger.info(f"Calling agent with message: {user_text[:100]}")
            
            agent = self._get_agent()
            loop = asyncio.get_running_loop()

            def invoke_agent():
                # Agent may call asyncio.get_event_loop; ensure one exists in this worker thread
                thread_loop = asyncio.new_event_loop()
                try:
                    asyncio.set_event_loop(thread_loop)
                    return agent.invoke({"messages": agent_messages})
                finally:
                    asyncio.set_event_loop(None)
                    thread_loop.close()

            # Run agent in executor since it's synchronous
            agent_response = await loop.run_in_executor(None, invoke_agent)
            
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
            try:
                await self.session.rollback()
            except Exception as rollback_err:
                logger.warning(f"Rollback failed after agent error: {rollback_err}")
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
