"""Session-level resource registry for per-PDF search and vector indices.

Updated to match current project architecture:

Resources per PDF (doc_id):
    - Woosh (Whoosh) lexical index: built via preprocessing.WooshIndexer at
                extraction/<doc_id>/lucene_index/
    - FAISS vector store over text chunks: managed via analyzer.FaissWrapper at
                extraction/<doc_id>/<EXTRACTION_FAISS_DIR>/
    - Text chunks directory: extraction/<doc_id>/<EXTRACTION_CHUNK_DIR>/
    - Figures metadata parquet: extraction/<doc_id>/figures_metadata.parquet

This module caches opened indices (lexical + vector) with a small LRU to avoid
repeated disk I/O across an interactive session.

Public operations you likely wrap at a higher layer:
        registry.ensure(doc_id): load (or create) resources
        registry.search_lexical(doc_id, query, doc_type="any", limit=10)
        registry.search_vector(doc_id, query, k=5)
        registry.get_chunks(doc_id, chunk_ids)

Implementation details:
    - Uses WooshSearcher for lexical querying (Whoosh)
    - Uses FaissWrapper for vector similarity (FAISS via LangChain)
    - Chunk IDs are derived from filenames: chunk_0001.txt → c0001 etc.
"""

import os
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from analyzer.config import default_config
from analyzer.woosh_searcher import WooshSearcher
from analyzer.faiss_wrapper import FaissWrapper
from analyzer.schemas import DocumentTypes

logger = logging.getLogger(__name__)

# --------- Data models ---------
@dataclass
class Chunk:
    chunk_id: str
    text: str
    metadata: Dict[str, Any]

@dataclass
class VectorIndex:
    wrapper: FaissWrapper
    loaded: bool

@dataclass
class TextSearchIndex:
    woosh_dir: str
    searcher: WooshSearcher

@dataclass
class DocResources:
    doc_id: str
    vector_index: VectorIndex
    image_captions_index: VectorIndex
    text_index: TextSearchIndex
    chunks_dir: str
    parquet_path: str

# --------- Session registry (in-memory) ---------
class SessionRegistry:
    def __init__(self, max_sessions: int = 3):
        self.max_sessions = max_sessions
        self._sessions: Dict[str, DocResources] = {}
        self._lru: List[str] = []
        self._active_session: str = ""

    def get(self, doc_file_name: str) -> Optional[DocResources]:
        if doc_file_name in self._sessions:
            # update LRU
            self._lru = [d for d in self._lru if d != doc_file_name] + [doc_file_name]
            return self._sessions[doc_file_name]
        return None

    def put(self, doc_file_name: str, res: DocResources):
        if doc_file_name not in self._sessions and len(self._sessions) >= self.max_sessions:
            # evict LRU
            evict_id = self._lru.pop(0)
            self._sessions.pop(evict_id, None)
        self._sessions[doc_file_name] = res
        self._lru = [d for d in self._lru if d != doc_file_name] + [doc_file_name]

    def set_active(self, doc_file_name: str):
        self._active_session = doc_file_name

    def get_active(self) -> Optional[str]:
        return self._active_session

    # ---------- helpers ----------

    def ensure(self, doc_file_name: str) -> DocResources:
        existing = self.get(doc_file_name)
        if existing:
            return existing
        extraction_dir = os.path.join(default_config.EXTRACTION_DIR, doc_file_name)
        chunks_dir = os.path.join(extraction_dir, default_config.EXTRACTION_CHUNK_DIR)
        parquet_path = os.path.join(extraction_dir, default_config.EXTRACTION_FIGURES_PARQUET_FILE)
        woosh_dir = os.path.join(extraction_dir, default_config.EXTRACTION_LUCENE_INDEX_DIR)

        # Lexical index
        text_searcher = WooshSearcher(pdf_name=doc_file_name)
        try:
            text_searcher.open()
        except FileNotFoundError:
            logger.warning(f"Woosh index missing for {doc_file_name}: {woosh_dir}")

        # Vector index for text chunks
        faiss_wrapper = FaissWrapper()
        loaded = faiss_wrapper.load_index(extraction_dir)
        vector_index = VectorIndex(wrapper=faiss_wrapper, loaded=loaded)

        # Vector index for image captions
        captions_wrapper = FaissWrapper()
        captions_loaded = captions_wrapper.load_image_captions_index(extraction_dir)
        image_captions_index = VectorIndex(wrapper=captions_wrapper, loaded=captions_loaded)

        res = DocResources(
            doc_id=doc_file_name,
            vector_index=vector_index,
            image_captions_index=image_captions_index,
            text_index=TextSearchIndex(woosh_dir=woosh_dir, searcher=text_searcher),
            chunks_dir=chunks_dir,
            parquet_path=parquet_path,
        )
        self.put(doc_file_name, res)
        return res

    # ---------- operations ----------

    def search_lexical(
        self,
        doc_file_name: str,
        query: str,
        *,
        doc_type: str = "any",
        limit: int = 10,
        preview_chars: int = 120,
    ) -> List[Dict[str, Any]]:
        res = self.ensure(doc_file_name)
        searcher = res.text_index.searcher
        try:
            hits = searcher.search(
                query,
                doc_type=doc_type if doc_type != "any" else "any",
                limit=limit,
                return_preview=True,
                max_preview_chars=preview_chars,
            )
        except Exception as e:
            logger.error(f"Lexical search failed for {doc_file_name}: {e}")
            return []
        return hits

    def search_vector(self, doc_file_name: str, query: str, k: int = 5) -> List[Dict[str, Any]]:
        res = self.ensure(doc_file_name)
        vi = res.vector_index
        if not vi.loaded:
            logger.warning(f"Vector index not loaded for {doc_file_name}")
            return []
        raw = vi.wrapper.search(query, k=k)
        out: List[Dict[str, Any]] = []
        for doc, score in raw:
            out.append({
                "chunk_number": doc.metadata.get("chunk_number"),
                "score": float(score),
                "source": doc.metadata.get("source"),
                "text": doc.page_content[:200] + ("..." if len(doc.page_content) > 200 else ""),
            })
        return out

    def get_chunks(self, doc_file_name: str, chunk_numbers: List[str]) -> List[Chunk]:
        res = self.ensure(doc_file_name)
        chunks: List[Chunk] = []
        for num in chunk_numbers:
            fname = f"chunk_{num}.txt" if not num.startswith("chunk_") else num + ".txt" if not num.endswith(".txt") else num
            path = os.path.join(res.chunks_dir, fname)
            if not os.path.isfile(path):
                continue
            try:
                with open(path, "r", encoding="utf-8") as f:
                    text = f.read().strip()
                chunks.append(Chunk(chunk_id=fname, text=text, metadata={"doc_id": doc_file_name}))
            except Exception:
                continue
        return chunks

    def search_image_captions(self, doc_file_name: str, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Search image captions using FAISS vector similarity.
        
        Returns list of dicts with image metadata including path, caption, score, etc.
        """
        res = self.ensure(doc_file_name)
        ci = res.image_captions_index
        if not ci.loaded:
            logger.warning(f"Image captions vector index not loaded for {doc_file_name}")
            return []
        raw = ci.wrapper.search(query, k=k)
        out: List[Dict[str, Any]] = []
        for doc, score in raw:
            out.append({
                "image_id": doc.metadata.get("image_id"),
                "image_path": doc.metadata.get("image_path"),
                "page_index": doc.metadata.get("page_index"),
                "image_index": doc.metadata.get("image_index"),
                "caption": doc.page_content,
                "score": float(score),
                "width": doc.metadata.get("width"),
                "height": doc.metadata.get("height"),
                "has_caption": doc.metadata.get("has_caption"),
            })
        return out

    def hybrid_search(
        self,
        doc_file_name: str,
        query: str,
        *,
        index_type: str = "text",  # "text" or "captions"
        doc_type: str = "any",
        k: int = 5,
        lexical_weight: float = 0.3,
        vector_weight: float = 0.7,
    ) -> List[Dict[str, Any]]:
        """Hybrid search combining lexical (Woosh) and vector (FAISS) results.
        
        Args:
            doc_file_name: Document to search
            query: Search query
            index_type: "text" for text chunks, "captions" for image captions
            doc_type: Document type filter for lexical search (for text only)
            k: Number of results to return
            lexical_weight: Weight for lexical scores (0-1)
            vector_weight: Weight for vector scores (0-1)
            
        Returns:
            Combined and ranked results with normalized scores
        """
        # Get vector results
        if index_type == "captions":
            vector_results = self.search_image_captions(doc_file_name, query, k=k)
        else:
            vector_results = self.search_vector(doc_file_name, query, k=k)
        
        # Get lexical results (only applicable for text search)
        lexical_results = []
        if index_type == "text":
            lexical_results = self.search_lexical(
                doc_file_name, query, doc_type=doc_type, limit=k, preview_chars=200
            )
        
        # Normalize scores and combine
        combined: Dict[str, Dict[str, Any]] = {}
        
        # Process vector results
        max_vector_score = max([r["score"] for r in vector_results], default=1.0)
        for r in vector_results:
            key = r.get("chunk_number") or r.get("image_id")
            if not key:
                continue
            normalized_score = (r["score"] / max_vector_score) if max_vector_score > 0 else 0
            combined[key] = {
                **r,
                "hybrid_score": normalized_score * vector_weight,
                "vector_score": r["score"],
                "lexical_score": 0.0,
            }
        
        # Process lexical results
        if lexical_results:
            max_lexical_score = max([r.get("score", 0) for r in lexical_results], default=1.0)
            for r in lexical_results:
                key = r.get("id")
                if not key:
                    continue
                normalized_score = (r.get("score", 0) / max_lexical_score) if max_lexical_score > 0 else 0
                
                if key in combined:
                    # Boost items that appear in both
                    combined[key]["hybrid_score"] += normalized_score * lexical_weight
                    combined[key]["lexical_score"] = r.get("score", 0)
                else:
                    # Add lexical-only results
                    combined[key] = {
                        **r,
                        "hybrid_score": normalized_score * lexical_weight,
                        "vector_score": 0.0,
                        "lexical_score": r.get("score", 0),
                    }
        
        # Sort by hybrid score and return top k
        results = sorted(combined.values(), key=lambda x: x["hybrid_score"], reverse=True)
        return results[:k]

__all__ = ["SessionRegistry", "DocResources", "Chunk"]

default_registry = SessionRegistry(max_sessions=4)
