#!/usr/bin/env python3
"""CLI chat bot to interact with the document agent."""

import sys
import os
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
	sys.path.insert(0, PROJECT_ROOT)

import sys
from typing import List
import argparse
from langchain_core.messages import HumanMessage, ToolMessage

from agents.agent import make_document_agent
from session.session_registry import default_registry

from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file


def print_separator():
    """Print a visual separator."""
    print("\n" + "=" * 80 + "\n")

def truncate_output(text: str, max_length: int = 200) -> str:
    """Truncate text to max_length characters."""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."

def chat_loop(agent, document_name: str, verbose: bool = False):
    """Run the interactive chat loop."""
    print("\n🤖 Document Chat Bot")
    print(f"📄 Active Document: {document_name}")
    if verbose:
        print("🔊 Verbose mode: ON")
    print("\nCommands:")
    print("  • Type your question to chat with the document")
    print("  • 'quit' or 'exit' to end the session")
    print("  • 'clear' to clear chat history")
    print_separator()
    
    chat_history: List = [
        {"role": "system", "content": f"You are a helpful assistant specialized in answering questions about the document '{document_name}'. You have query tools to help you find information in the document."}
    ]

    while True:
        try:
            # Get user input
            user_input = input("You: ").strip()

            if not user_input:
                continue

            # Handle commands
            if user_input.lower() in ["quit", "exit"]:
                print("\n👋 Goodbye!\n")
                break

            if user_input.lower() == "clear":
                chat_history = []
                print("\n🗑️  Chat history cleared.\n")
                continue

            # Add user message to history
            chat_history.append({"role": "user", "content": user_input})

            # Invoke agent with chat history
            print("\n🔍 Processing...\n")
            response = agent.invoke({"messages": chat_history})

            # Display verbose information if enabled
            if verbose:
                print("🧠 Agent Thinking Process:")
                print("-" * 80)
                for msg in response['messages'][:-1]:  # All messages except the final answer
                    if hasattr(msg, 'tool_calls') and msg.tool_calls:
                        # Agent is calling tools
                        for tool_call in msg.tool_calls:
                            print(f"\n🔧 Tool Call: {tool_call['name']}")
                            print(f"   Arguments: {tool_call['args']}")
                    elif isinstance(msg, ToolMessage):
                        # Tool response
                        tool_output = str(msg.content)
                        print(f"\n📤 Tool Output ({msg.name}):")
                        print(f"   {truncate_output(tool_output, 200)}")
                    elif hasattr(msg, 'content') and msg.content and not isinstance(msg, (HumanMessage,)):
                        # Agent's reasoning (if any)
                        print(f"\n💭 Agent: {truncate_output(msg.content, 200)}")
                print("\n" + "-" * 80 + "\n")

            llm_answer = response['messages'][-1].content

            chat_history.append({"role": "assistant", "content": llm_answer})

            # Display response
            print(f"Agent: {llm_answer}")
            print_separator()

        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!\n")
            break
        except Exception as e:
            # raise e
            print(f"\n❌ Error: {e}\n")
            print("Continuing chat session...\n")


def main():
    """Main entry point."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Chat with a document using an AI agent")
    parser.add_argument("document", nargs="?", default="ID 35", help="Document name to query")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose mode to show agent thinking and tool outputs")
    args = parser.parse_args()

    document_name = args.document
    verbose = args.verbose

    # Initialize document session
    default_registry.ensure(document_name)
    default_registry.set_active(document_name)

    # Create agent
    print("\n🚀 Initializing agent...")
    agent = make_document_agent()
    print("✅ Agent ready!")

    # Start chat loop
    chat_loop(agent, document_name, verbose=verbose)


if __name__ == "__main__":
    main()
