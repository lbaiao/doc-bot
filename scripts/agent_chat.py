from agents.agent import make_document_agent
from session.session_registry import SessionRegistry
from analyzer.config import FullConfigPaths

registry = SessionRegistry()
pdf_name = "ID 35"
registry.ensure(pdf_name)
registry.set_active(pdf_name)
agent = make_document_agent()


