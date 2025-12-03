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

from session.db_registry import default_registry
from analyzer.config import get_config

from langchain_anthropic import ChatAnthropic


# -------- session state ---------
_registry = default_registry


def _require_active_doc() -> str:
    _active_doc = _registry.get_active()
    if not _active_doc:
        raise ValueError("No active document set. Call set_active_document(document_id) first.")
    return _active_doc


@tool
def set_active_document(document_id: str) -> str:
    """Set the active document context by UUID (document_id from the API)."""
    _registry.ensure(document_id)
    return json.dumps({"status": "ok", "active_document": document_id})


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
def analyze_images(image_ids: str, instruction: str, context: str = "") -> str:
    """Analyze images from the document using Claude's vision capabilities.
    
    Fetches images (by UUID from search_caption results), uploads them to Anthropic,
    and gets Claude's analysis based on your instruction. Images are cached for 12 hours.
    
    Args:
        image_ids: Comma-separated image UUIDs (e.g., "uuid1,uuid2,uuid3")
        instruction: What you want Claude to do with the images. Be specific.
                    Examples: "Describe what you see in these diagrams",
                             "Extract all text and equations from these figures",
                             "Compare these two charts and explain the differences",
                             "Identify the key components in this architecture diagram"
        context: Optional additional context or background information to help with analysis.
                Examples: "These are from a paper about neural networks",
                         "The user is asking about the methodology section"
    
    Returns:
        JSON with Claude's analysis, image metadata, and processing statistics.
    """
    
    doc = _require_active_doc()
    
    # Parse image IDs
    ids: List[str] = [id.strip() for id in image_ids.split(",") if id.strip()]
    
    if not ids:
        return json.dumps({
            "error": "No image IDs provided",
            "document": doc,
            "analysis": None,
        }, ensure_ascii=False)
    
    # Upload images to Anthropic
    upload_result = _registry.upload_images_to_anthropic(doc, ids)
    
    if "error" in upload_result:
        return json.dumps({
            "error": upload_result["error"],
            "document": doc,
            "analysis": None,
        }, ensure_ascii=False)
    
    # Build message content with images
    content = []
    
    # Add context if provided
    if context.strip():
        content.append({
            "type": "text",
            "text": f"Context: {context}\n\n"
        })
    
    # Add image content blocks
    content.extend(upload_result["content_blocks"])
    
    # Add the instruction
    content.append({
        "type": "text",
        "text": instruction
    })
    
    # Call Claude with vision
    try:
        config = get_config()
        vision_model = ChatAnthropic(
            model="claude-sonnet-4-5-20250929",
            api_key=config.ANTHROPIC_API_KEY,
            betas=["files-api-2025-04-14"],
        )
        
        message = {
            "role": "user",
            "content": content
        }
        
        response = vision_model.invoke([message])
        
        return json.dumps({
            "document": doc,
            "analysis": response.content,
            "images_analyzed": len(ids),
            "cached_count": upload_result.get("cached_count", 0),
            "uploaded_count": upload_result.get("uploaded_count", 0),
            "image_metadata": upload_result.get("images", []),
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "error": f"Failed to analyze images: {str(e)}",
            "document": doc,
            "analysis": None,
        }, ensure_ascii=False)


__all__ = [
    "set_active_document",
    "text_search",
    "vector_search",
    "get_chunks",
    "search_caption",
    "hybrid_search",
    "analyze_images",
]
