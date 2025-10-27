from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple, Optional, Iterable, Dict, Any
import os
import pathlib

import pymupdf  # PyMuPDF
import logging

logger = logging.getLogger(__name__)


@dataclass
class FigureRegion:
    doc_path: str
    page_index: int
    rect: pymupdf.Rect
    score: float
    n_words_inside: int
    has_caption: bool
    caption_text: str
    # filled after rasterize()
    png_path: Optional[str] = None
    dpi: Optional[int] = None


class VectorFigureExtractor:
    """
    Detects vector-graphics figures/diagrams/charts in PDFs and rasterizes only those regions.

    Requires:
        pip install pymupdf
    Import:
        import pymupdf  # PyMuPDF

    Notes:
      - Heuristics are configurable via constructor.
      - Works best on typical academic/technical PDFs with captions like “Figure 2.” under the graphic.
    """

    CAPTION_TOKENS_DEFAULT = ("figure", "fig.", "chart", "diagram", "schematic")

    def __init__(
        self,
        min_segments: int = 50,
        min_area: Optional[float] = None,   # if None, computed as area_frac * page_area
        min_stroke: float = 0.2,
        area_frac: float = 0.01,            # 1% of page area if min_area is None
        max_words_inside: int = 12,         # allow small legends/labels
        caption_tokens: Iterable[str] = CAPTION_TOKENS_DEFAULT,
        caption_search_px: int = 220,       # how far below box to search for caption
        merge_iou_thresh: float = 0.2,
        pad_px: int = 6,
    ):
        self.min_segments = min_segments
        self.min_area = min_area
        self.min_stroke = min_stroke
        self.area_frac = area_frac
        self.max_words_inside = max_words_inside
        self.caption_tokens = tuple(t.lower() for t in caption_tokens)
        self.caption_search_px = caption_search_px
        self.merge_iou_thresh = merge_iou_thresh
        self.pad_px = pad_px

    # ---------- public API ----------

    def extract(
        self,
        doc: pymupdf.Document,
        doc_path: str,
        dpi: int = 300,
        out_dir: Optional[str] = None,
        save_png: bool = True,
        pages: Optional[Iterable[int]] = None,
        close: bool = False,
    ) -> List[FigureRegion]:
        """
        Process the PDF and return metadata for detected figures.
        Optionally saves cropped PNGs to `out_dir` (defaults to <pdfstem>_figures).

        Returns a flat list of FigureRegion.
        """
        if pages is None:
            pages = range(len(doc))
        pages = list(pages)

        if save_png:
            if out_dir is None:
                out_dir = f"{pathlib.Path(doc_path).stem}_figures"
            os.makedirs(out_dir, exist_ok=True)

        results: List[FigureRegion] = []
        for pidx in pages:
            logger.info(f"Processing page {pidx + 1} / {len(doc)} for vector figures")
            page = doc[pidx]
            boxes_scored = self._figure_boxes_scored(page)
            if not boxes_scored:
                continue

            for rect, score, n_words, has_cap, cap_text in boxes_scored:
                # rasterize
                clip = self._pad(rect, self.pad_px)
                pix = page.get_pixmap(clip=clip, dpi=dpi, alpha=False)
                png_path = None
                if save_png and out_dir is not None:
                    png_path = os.path.join(out_dir, f"p{pidx:04d}_y{int(rect.y0)}_x{int(rect.x0)}.png")
                    pix.save(png_path)

                results.append(
                    FigureRegion(
                        doc_path=doc_path,
                        page_index=pidx,
                        rect=pymupdf.Rect(rect),
                        score=score,
                        n_words_inside=n_words,
                        has_caption=has_cap,
                        caption_text=cap_text,
                        png_path=png_path,
                        dpi=dpi,
                    )
                )

        if close:
            doc.close()
        # sort by page then by score desc
        results.sort(key=lambda fr: (fr.page_index, -fr.score))
        return results

    # ---------- internals ----------

    def _pad(self, rect: pymupdf.Rect, px: int) -> pymupdf.Rect:
        return pymupdf.Rect(rect.x0 - px, rect.y0 - px, rect.x1 + px, rect.y1 + px)

    def _page_words(self, page: pymupdf.Page) -> List[Tuple[float, float, float, float, str, int, int, int]]:
        # (x0,y0,x1,y1,"word", block_no, line_no, word_no)
        words = page.get_text("words")
        # Type check: ensure it's a list
        if isinstance(words, list):
            return words  # type: ignore
        return []

    def _words_in_rect(self, page: pymupdf.Page, rect: pymupdf.Rect):
        return [w for w in self._page_words(page) if rect.intersects(pymupdf.Rect(w[:4]))]

    def _caption_below(self, page: pymupdf.Page, rect: pymupdf.Rect) -> Tuple[bool, str]:
        zone = pymupdf.Rect(rect.x0, rect.y1, rect.x1, rect.y1 + self.caption_search_px)
        words = [t for t in self._page_words(page) if zone.intersects(pymupdf.Rect(t[:4]))]
        text = " ".join(t[4] for t in words).strip()
        low = text.lower()
        has = any(tok in low for tok in self.caption_tokens)
        return has, text

    def _vector_candidates(self, page: pymupdf.Page) -> List[pymupdf.Rect]:
        # collect drawing groups and filter by complexity, area, and stroke width
        rects: List[pymupdf.Rect] = []
        page_area = page.rect.width * page.rect.height
        min_area = self.min_area if self.min_area is not None else self.area_frac * page_area

        for d in page.get_drawings():
            rect = pymupdf.Rect(d["rect"])
            area = rect.width * rect.height
            if area < min_area:
                continue

            items = d.get("items", [])
            # count segments that suggest shapes (lines/curves/rect/fill/stroke)
            segs = 0
            widths = []
            for it in items:
                op = it[0] if len(it) > 0 else None
                if op in ("l", "c", "re", "qu", "sh", "f", "s"):  # line/curve/rect/quad/shade/fill/stroke
                    segs += 1
                # try to read stroke width when present
                if len(it) > 1 and isinstance(it[1], dict):
                    w = it[1].get("width", None)
                    if w is not None:
                        widths.append(w)

            avg_stroke = (sum(widths) / len(widths)) if widths else 0.0
            if segs >= self.min_segments and avg_stroke >= self.min_stroke:
                rects.append(rect)
        return rects

    def _merge_boxes(self, rects: List[pymupdf.Rect]) -> List[pymupdf.Rect]:
        if not rects:
            return []
        rects = [pymupdf.Rect(r) for r in rects]
        changed = True
        while changed:
            changed = False
            out: List[pymupdf.Rect] = []
            used = [False] * len(rects)
            for i, r in enumerate(rects):
                if used[i]:
                    continue
                curr = r
                for j in range(i + 1, len(rects)):
                    if used[j]:
                        continue
                    s = rects[j]
                    inter = curr & s
                    inter_area = inter.width * inter.height
                    if inter_area == 0:
                        continue
                    union = curr | s
                    union_area = union.width * union.height
                    iou = inter_area / union_area if union_area > 0 else 0
                    if iou >= self.merge_iou_thresh or curr.intersects(s):
                        curr = curr | s
                        used[j] = True
                        changed = True
                used[i] = True
                out.append(curr)
            rects = out
        return rects

    def _score_candidate(self, page: pymupdf.Page, rect: pymupdf.Rect) -> Tuple[float, int, bool, str]:
        words = self._words_in_rect(page, rect)
        n_inside = len(words)
        has_cap, cap_text = self._caption_below(page, rect)

        # scoring: reward caption cue, reward fewer internal words
        score = (1000.0 if has_cap else 0.0) + max(0.0, 50.0 - float(n_inside))
        # small bonus for reasonably "large" figures (but not full-page)
        page_area = page.rect.width * page.rect.height
        area = rect.width * rect.height
        score += min(100.0, 100.0 * (area / page_area))

        return score, n_inside, has_cap, cap_text

    def _figure_boxes_scored(
        self, page: pymupdf.Page
    ) -> List[Tuple[pymupdf.Rect, float, int, bool, str]]:
        raw = self._vector_candidates(page)
        merged = self._merge_boxes(raw)
        scored: List[Tuple[pymupdf.Rect, float, int, bool, str]] = []
        for r in merged:
            score, n_words, has_cap, cap_text = self._score_candidate(page, r)
            if has_cap or n_words <= self.max_words_inside:
                scored.append((r, score, n_words, has_cap, cap_text))
        # sort by score desc
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

