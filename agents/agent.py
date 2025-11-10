from langchain.agents import create_agent
from langchain_anthropic import ChatAnthropic, convert_to_anthropic_tool

from agents.tools import vector_search, text_search, get_chunks

def make_document_agent():
    chat = ChatAnthropic(
        model="claude-haiku-4-5-20251001",
        temperature=0.3,
        # max_tokens=1024,
        timeout=None,
        max_retries=2,
        # other params...
)
    tools = [vector_search, text_search, get_chunks]
    return create_agent(chat, tools)