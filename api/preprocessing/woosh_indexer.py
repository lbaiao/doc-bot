import os
import logging
from typing import Optional

import pandas as pd
from whoosh import index as whoosh_index
from whoosh.fields import Schema, TEXT, ID, NUMERIC, STORED
from whoosh.analysis import StemmingAnalyzer

from analyzer.config import default_config
from analyzer.schemas import FigureImageCols as FIC, DocumentTypes


logger = logging.getLogger(__name__)


class WooshIndexer:
	"""
	Builds a lightweight Lucene-style full-text index (using Whoosh) for each extracted PDF.

	Index contents:
	  - Text chunks from extraction/<pdf>/<EXTRACTION_CHUNK_DIR>/chunk_*.txt
	  - Image captions from `figures_metadata.parquet` when available

	Output directory structure (per PDF):
	  extraction/<pdf_name>/
		├── text.txt
		├── images/
		├── vector_graphics/
		├── figures_metadata.parquet
		└── lucene_index/              # created here
	"""

	def __init__(self, extraction_dir: str, pdf_name: Optional[str] = None):
		self.extraction_dir = extraction_dir
		self.pdf_name = pdf_name or os.path.basename(os.path.normpath(extraction_dir))
		self.parquet_path = os.path.join(extraction_dir, default_config.EXTRACTION_FIGURES_PARQUET_FILE)
		self.index_dir = os.path.join(extraction_dir, default_config.EXTRACTION_LUCENE_INDEX_DIR)
		self.chunks_dir = os.path.join(extraction_dir, default_config.EXTRACTION_CHUNK_DIR)

	# ---------- public API ----------

	def build(self) -> None:
		"""Create or refresh the index for this PDF's extracted artifacts."""
		os.makedirs(self.index_dir, exist_ok=True)

		ix = self._get_or_create_index()
		# Guard against stale schema (e.g., previous 'page' field vs new 'order/page_index')
		existing = set(ix.schema.names())
		expected = set(self._schema().names())
		if existing != expected:
			logger.info("Lucene index schema mismatch at build(); rebuilding index directory to new schema")
			try:
				ix.close()
			except Exception:
				pass
			try:
				for fn in os.listdir(self.index_dir):
					try:
						os.remove(os.path.join(self.index_dir, fn))
					except Exception:
						pass
			except FileNotFoundError:
				os.makedirs(self.index_dir, exist_ok=True)
			ix = whoosh_index.create_in(self.index_dir, self._schema())

		writer = ix.writer(limitmb=256)

		n_chunks = self._index_chunks(writer)
		n_caps = self._index_image_captions(writer)

		writer.commit()
		logger.info(
			f"Lucene index built for '{self.pdf_name}': {n_chunks} chunks, {n_caps} image captions → {self.index_dir}"
		)

	# ---------- internals ----------
	def _schema(self):
		analyzer = StemmingAnalyzer()
		return Schema(
			id=ID(stored=True, unique=True),
			pdf=ID(stored=True),
			type=ID(stored=True),  # see DocumentTypes
			order=NUMERIC(stored=True),      # chunk order (1-based), -1 for non-chunk docs
			page_index=NUMERIC(stored=True), # source page index for captions, -1 for chunks
			path=STORED,  # optional: file path for images or chunk file
			content=TEXT(analyzer=analyzer, stored=False),
		)

	def _get_or_create_index(self):
		if whoosh_index.exists_in(self.index_dir):
			try:
				return whoosh_index.open_dir(self.index_dir)
			except Exception:
				# If index is corrupt or incompatible, recreate
				pass
		# (Re)create index
		try:
			# If directory has stale files, purge and recreate
			for fn in os.listdir(self.index_dir):
				try:
					os.remove(os.path.join(self.index_dir, fn))
				except Exception:
					pass
		except FileNotFoundError:
			os.makedirs(self.index_dir, exist_ok=True)
		return whoosh_index.create_in(self.index_dir, self._schema())

	def _index_chunks(self, writer) -> int:
		if not os.path.isdir(self.chunks_dir):
			logger.warning(f"Chunk directory not found: {self.chunks_dir}")
			return 0
		files = sorted([f for f in os.listdir(self.chunks_dir) if f.lower().endswith(".txt")])
		count = 0
		for idx, fname in enumerate(files, start=1):
			fpath = os.path.join(self.chunks_dir, fname)
			try:
				with open(fpath, "r", encoding="utf-8") as f:
					content = f.read().strip()
			except Exception:
				continue
			if not content:
				continue
			writer.update_document(
				id=f"{self.pdf_name}-c{idx}",
				pdf=self.pdf_name,
				type=DocumentTypes.CHUNK,
				order=idx,
				page_index=-1,
				path=fpath,
				content=content,
			)
			count += 1
		logger.info(f"Indexed {count} text chunks for '{self.pdf_name}'")
		return count

	def _index_image_captions(self, writer) -> int:
		if not os.path.exists(self.parquet_path):
			logger.info("No figures metadata parquet found; skipping caption indexing")
			return 0

		try:
			df = pd.read_parquet(self.parquet_path)
		except Exception as e:
			logger.error(f"Failed reading figures parquet for indexing: {e}")
			return 0

		if df.empty or FIC.CAPTION not in df.columns:
			return 0

		# Filter only rows with non-empty captions
		def _non_empty(x: Optional[str]) -> bool:
			return isinstance(x, str) and x.strip() != ""

		rows = df[df.get(FIC.HAS_CAPTION, False) & df[FIC.CAPTION].map(_non_empty)]
		n_indexed = 0
		for _, row in rows.iterrows():
			try:
				rid = str(row.get(FIC.ID) or f"img-{_}")
				page_idx = int(row.get(FIC.PAGE_INDEX, -1))
				caption = str(row.get(FIC.CAPTION, "")).strip()
				img_path = row.get(FIC.IMAGE_PATH)
			except Exception:
				continue

			if not caption:
				continue

			writer.update_document(
				id=f"{self.pdf_name}-img-{rid}",
				pdf=self.pdf_name,
				type=DocumentTypes.IMAGE_CAPTION,
				order=-1,
				page_index=page_idx if page_idx >= 0 else -1,
				path=img_path,
				content=caption,
			)
			n_indexed += 1
		if n_indexed:
			logger.info(f"Indexed {n_indexed} image captions for '{self.pdf_name}'")
		return n_indexed


__all__ = ["WooshIndexer"]

