import os
import logging
from typing import List

from analyzer.config import default_config

logger = logging.getLogger(__name__)


class TextChunker:
    """
    Splits a text file into overlapping chunks and writes them to disk with ordered names.

    - Source: the extracted `text.txt` for a PDF
    - Output: extraction/<pdf_name>/<EXTRACTION_CHUNK_DIR>/chunk_0001.txt, ...
    - Chunking is character-based with configurable size and overlap
    """

    def __init__(self, chunk_size: int | None = None, overlap: int | None = None, out_dir_name: str | None = None):
        cs = chunk_size if chunk_size is not None else int(default_config.EXTRACTION_CHUNK_SIZE)
        ov = overlap if overlap is not None else int(default_config.EXTRACTION_CHUNK_OVERLAP)
        self.chunk_size = max(1, int(cs))
        self.overlap = max(0, min(int(ov), self.chunk_size - 1))
        self.out_dir_name = out_dir_name or default_config.EXTRACTION_CHUNK_DIR

    def chunk_file(self, text_path: str, extraction_dir: str) -> List[str]:
        """
        Split the text file into chunks and write them under extraction_dir/<out_dir_name>.

        Returns a list of absolute paths to created chunk files in order.
        """
        if not os.path.exists(text_path):
            logger.warning(f"Chunker: text file does not exist: {text_path}")
            return []

        with open(text_path, "rb") as f:
            raw = f.read()
        text = raw.decode("utf-8", errors="replace")

        # Normalize page delimiters (form feed 0x0C) into newline so we don't produce weird tokens
        text = text.replace("\x0c", "\n")

        out_dir = os.path.join(extraction_dir, self.out_dir_name)
        os.makedirs(out_dir, exist_ok=True)

        paths: List[str] = []
        start = 0
        i = 0
        step = self.chunk_size - self.overlap if self.chunk_size > self.overlap else self.chunk_size
        n = len(text)

        while start < n:
            end = min(n, start + self.chunk_size)
            chunk = text[start:end].strip()
            if chunk:
                i += 1
                fname = f"chunk_{i:04d}.txt"
                fpath = os.path.join(out_dir, fname)
                with open(fpath, "w", encoding="utf-8") as out:
                    out.write(chunk)
                paths.append(fpath)
            if end >= n:
                break
            start += step

        logger.info(f"Chunker: created {len(paths)} chunks at {out_dir}")
        return paths


__all__ = ["TextChunker"]
