#!/usr/bin/env python3
"""CLI chat bot to interact with the document agent."""

import sys
import os
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
	sys.path.insert(0, PROJECT_ROOT)

import sys
from typing import List
from langchain_core.messages import HumanMessage, AIMessage

from agents.agent import make_document_agent
from session.session_registry import default_registry

from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file


def print_separator():
    """Print a visual separator."""
    print("\n" + "=" * 80 + "\n")

def chat_loop(agent, document_name: str):
    """Run the interactive chat loop."""
    print("\n🤖 Document Chat Bot")
    print(f"📄 Active Document: {document_name}")
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
    # Default document
    document_name = "ID 35"
    default_registry.ensure(document_name)
    default_registry.set_active(document_name)

    # Allow document name as command line argument
    if len(sys.argv) > 1:
        document_name = sys.argv[1]

    # Create agent
    print("\n🚀 Initializing agent...")
    agent = make_document_agent()
    print("✅ Agent ready!")

    # Start chat loop
    chat_loop(agent, document_name)


if __name__ == "__main__":
    main()
