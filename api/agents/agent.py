from langchain.agents import create_agent
from langchain_anthropic import ChatAnthropic

from analyzer.config import get_config
from agents.tools import (
    set_active_document,
    hybrid_search,
    search_caption,
    text_search,
    get_chunks,
    analyze_images,
)


def make_document_agent():
    """Create the document agent wired to DB/Qdrant-backed tools."""
    cfg = get_config()
    chat = ChatAnthropic(
        api_key=cfg.ANTHROPIC_API_KEY or None,
        model="claude-haiku-4-5-20251001",
        temperature=0.3,
        timeout=None,
        max_retries=2,
    )
    tools = [set_active_document, hybrid_search, text_search, get_chunks, search_caption, analyze_images]
    return create_agent(chat, tools)
