from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from analyzer.config import default_config
from analyzer.schemas import DocumentTypes

from whoosh import index as whoosh_index
from whoosh.qparser import QueryParser
from whoosh.query import Term as QTerm


class WooshSearcher:
    """
    Thin abstraction over Whoosh index opening and query execution.

    Usage:
        s = WooshSearcher(pdf_name="ID 35")
        hits = s.search("optical flow", doc_type=DocumentTypes.CHUNK, limit=5, return_preview=True)
    """

    def __init__(self, pdf_name: Optional[str] = None, index_dir: Optional[str] = None):
        if index_dir is None and pdf_name is None:
            raise ValueError("Provide either pdf_name or index_dir")
        self.index_dir = (
            index_dir
            if index_dir is not None
            else os.path.join(
                default_config.EXTRACTION_DIR,
                str(pdf_name),
                default_config.EXTRACTION_LUCENE_INDEX_DIR,
            )
        )
        self._ix = None

    # ---------- lifecycle ----------

    def open(self):
        if not whoosh_index.exists_in(self.index_dir):
            raise FileNotFoundError(f"No Whoosh index found in: {self.index_dir}")
        self._ix = whoosh_index.open_dir(self.index_dir)
        return self

    def close(self):
        if self._ix is not None:
            try:
                self._ix.close()
            finally:
                self._ix = None

    def __enter__(self):
        return self.open()

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False

    # ---------- querying ----------

    def _read_preview(self, path: Optional[str], max_chars: int = 240) -> Optional[str]:
        if not path or not os.path.isfile(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read(max_chars * 4)
            text = text.replace("\n", " ").strip()
            if len(text) > max_chars:
                text = text[: max_chars - 3] + "..."
            return text
        except Exception:
            return None

    def search(
        self,
        query: str,
        *,
        doc_type: str = DocumentTypes.CHUNK,
        limit: int = 10,
        return_preview: bool = False,
        max_preview_chars: int = 240,
    ) -> List[Dict[str, Any]]:
        """
        Execute a lexical search over the index.

        - doc_type: one of DocumentTypes.CHUNK, DocumentTypes.IMAGE_CAPTION, or None for any
        - returns a list of dicts with keys: id, type, pdf, order, page_index, path, score, preview?
        """
        if self._ix is None:
            self.open()
        ix = self._ix
        assert ix is not None

        qp = QueryParser("content", schema=ix.schema)
        try:
            q = qp.parse(query)
        except Exception as e:
            raise ValueError(f"Invalid query: {e}") from e

        f = None
        if doc_type and doc_type != "any":
            f = QTerm("type", doc_type)

        out: List[Dict[str, Any]] = []
        with ix.searcher() as s:
            results = s.search(q, limit=limit, filter=f)
            for r in results:
                rec: Dict[str, Any] = {
                    "id": r.get("id"),
                    "type": r.get("type"),
                    "pdf": r.get("pdf"),
                    "order": r.get("order"),
                    "page_index": r.get("page_index"),
                    "path": r.get("path"),
                    "score": getattr(r, "score", None),
                }
                if return_preview:
                    rec["preview"] = self._read_preview(rec.get("path"), max_preview_chars)
                out.append(rec)

        return out


__all__ = ["WooshSearcher"]