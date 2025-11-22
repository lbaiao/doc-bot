from langchain.agents import create_agent
from langchain_anthropic import ChatAnthropic

from agents.tools import hybrid_search, search_caption, text_search, get_chunks, fetch_images

def make_document_agent():
    chat = ChatAnthropic(
        model="claude-haiku-4-5-20251001",
        temperature=0.3,
        # max_tokens=1024,
        timeout=None,
        max_retries=2,
        # other params...
)
    tools = [hybrid_search, text_search, get_chunks, search_caption, fetch_images]
    return create_agent(chat, tools)
