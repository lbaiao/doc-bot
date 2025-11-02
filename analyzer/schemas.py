from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, Any, List


class FigureImageCols:
    """Canonical column names for figures_metadata.parquet."""
    ID = "id"
    PAGE_INDEX = "page_index"
    IMAGE_INDEX = "image_index"
    IMAGE_PATH = "image_path"
    HAS_CAPTION = "has_caption"
    CAPTION = "caption"
    WIDTH = "width"
    HEIGHT = "height"

    ALL: List[str] = [
        ID,
        PAGE_INDEX,
        IMAGE_INDEX,
        IMAGE_PATH,
        HAS_CAPTION,
        CAPTION,
        WIDTH,
        HEIGHT,
    ]


@dataclass
class FigureImageMetadata:
    """
    Schema for a single bitmap image figure record.

    Used to write/read `figures_metadata.parquet` consistently across the project.
    """

    id: str
    page_index: int
    image_index: int
    image_path: str
    has_caption: bool
    caption: str
    width: int
    height: int

    def to_record(self) -> Dict[str, Any]:
        """Return a dict following the canonical column names."""
        return asdict(self)


class DocumentTypes:
    """Canonical document types for search indexes and downstream consumers."""
    CHUNK = "chunk"
    IMAGE_CAPTION = "image_caption"


__all__ = [
    "FigureImageCols",
    "FigureImageMetadata",
    "DocumentTypes",
]
