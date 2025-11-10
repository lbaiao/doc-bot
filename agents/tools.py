"""LangChain tool adapters wired to the session-level registry.

Tools operate on the "current active document" maintained in-module.
Call `set_active_document` first; subsequent `text_search` and `vector_search`
will automatically use the cached indices (lexical + vector) via `SessionRegistry`.

Returned values are JSON strings for structured downstream parsing.
"""

from __future__ import annotations

import json
from typing import Any, List

from langchain.tools import tool

from session.session_registry import default_registry

# -------- session state ---------
_registry = default_registry


def _require_active_doc() -> str:
    _active_doc = _registry.get_active()
    if not _active_doc:
        raise ValueError("No active document set. Call set_active_document(doc_file_name) first.")
    return _active_doc


@tool
def set_active_document(doc_file_name: str) -> str:
    """Set the active PDF document context (use the extraction folder name, e.g. 'ID 35')."""
    global _active_doc
    _active_doc = doc_file_name
    # Warm resources (lazy creation inside ensure)
    _registry.ensure(doc_file_name)
    return json.dumps({"status": "ok", "active_document": _active_doc})


@tool
def text_search(query: str, doc_type: str = "any", limit: int = 5, preview_chars: int = 160) -> str:
    """Lexical (Whoosh) search over the active document's index.

    doc_type may be: 'any', 'chunk', 'image_caption'.
    Returns JSON list of hits with id/type/order/page_index/score/preview.
    """
    doc = _require_active_doc()
    hits = _registry.search_lexical(doc, query, doc_type=doc_type, limit=limit, preview_chars=preview_chars)
    return json.dumps({"document": doc, "query": query, "count": len(hits), "results": hits}, ensure_ascii=False)


@tool
def vector_search(query: str, k: int = 5) -> str:
    """Vector (FAISS) similarity search over text chunks of the active document.

    Returns JSON list of matches with chunk_number, score, source, text (truncated).
    """
    doc = _require_active_doc()
    results = _registry.search_vector(doc, query, k=k)
    return json.dumps({"document": doc, "query": query, "count": len(results), "results": results}, ensure_ascii=False)


@tool
def get_chunks(chunk_numbers: str) -> str:
    """Fetch full chunk texts by comma-separated chunk numbers for the active document.

    Example chunk_numbers: "0001,0002".
    Returns JSON list of {chunk_id, text_length, text}.
    """
    doc = _require_active_doc()
    nums: List[str] = [n.strip() for n in chunk_numbers.split(",") if n.strip()]
    chunks = _registry.get_chunks(doc, nums)
    payload: List[dict[str, Any]] = []
    for c in chunks:
        payload.append({"chunk_id": c.chunk_id, "text_length": len(c.text), "text": c.text})
    return json.dumps({"document": doc, "requested": nums, "found": len(payload), "chunks": payload}, ensure_ascii=False)


__all__ = [
    "set_active_document",
    "text_search",
    "vector_search",
    "get_chunks",
]
