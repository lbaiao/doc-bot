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
from analyzer.config import get_config

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


@tool
def search_caption(query: str, k: int = 5) -> str:
    """Vector (FAISS) similarity search over image captions of the active document.
    
    Returns JSON list of images with caption, image_path, page_index, score, and dimensions.
    Use this to find images/figures by their captions or descriptions.
    """
    doc = _require_active_doc()
    results = _registry.search_image_captions(doc, query, k=k)
    return json.dumps({"document": doc, "query": query, "count": len(results), "results": results}, ensure_ascii=False)


@tool
def hybrid_search(query: str, search_type: str = "text", k: int = 5) -> str:
    """Hybrid search combining lexical (Whoosh) and vector (FAISS) results for the active document.
    
    search_type: 'text' for text chunks (default) or 'captions' for image captions.
    Returns combined results ranked by hybrid score (weighted combination of lexical + vector).
    """
    doc = _require_active_doc()
    index_type = "captions" if search_type.lower() == "captions" else "text"
    results = _registry.hybrid_search(doc, query, index_type=index_type, k=k)
    return json.dumps({
        "document": doc,
        "query": query,
        "search_type": search_type,
        "count": len(results),
        "results": results
    }, ensure_ascii=False)


@tool
def fetch_images(image_ids: str) -> str:
    f"""Upload images to Anthropic and get file IDs for use in the conversation.
    
    Takes comma-separated image UUIDs (from search_caption results) and uploads them
    to Anthropic's Files API. Returns file IDs and content blocks ready to use.
    Images are cached for {get_config().ANTHROPIC_IMAGE_CACHE_HOURS} hours to avoid re-uploading.
    
    Args:
        image_ids: Comma-separated list of image UUIDs (e.g., "uuid1,uuid2,uuid3")
    
    Returns:
        JSON with file_ids, image metadata, content_blocks, and cache statistics.
    """
    doc = _require_active_doc()
    
    # Parse image IDs
    ids: List[str] = [id.strip() for id in image_ids.split(",") if id.strip()]
    
    if not ids:
        return json.dumps({
            "error": "No image IDs provided",
            "document": doc,
            "file_ids": [],
            "images": [],
            "content_blocks": [],
        }, ensure_ascii=False)
    
    # Upload images
    result = _registry.upload_images_to_anthropic(doc, ids)
    result["document"] = doc
    result["requested_ids"] = ids
    
    return json.dumps(result, ensure_ascii=False)


__all__ = [
    "set_active_document",
    "text_search",
    "vector_search",
    "get_chunks",
    "search_caption",
    "hybrid_search",
    "fetch_images",
]
