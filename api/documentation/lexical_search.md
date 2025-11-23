# Lexical search: indexing and querying

This project provides a fast, lightweight lexical search over extracted PDF content using Whoosh (a pure‑Python Lucene‑style engine).

## What gets indexed

The index is built per PDF under `extraction/<pdf_name>/lucene_index/` by `preprocessing/LuceneIndexer` and contains:

- Text chunks: produced from `text.txt` by `preprocessing/TextChunker`
- Image captions: read from `figures_metadata.parquet`

### Schema (Whoosh fields)

- `id` (stored): unique id per document in the index
- `pdf` (stored): the PDF base name (folder under `extraction/`)
- `type` (stored): one of `DocumentTypes.CHUNK` or `DocumentTypes.IMAGE_CAPTION`
- `order` (stored numeric): chunk order (1-based); `-1` for non-chunk docs
- `page_index` (stored numeric): source page for captions; `-1` for chunks
- `path` (stored): file path to the underlying chunk file or image
- `content` (indexed, not stored): analyzed text for ranking

Document type constants live in `analyzer/schemas.py`:

- `DocumentTypes.CHUNK`
- `DocumentTypes.IMAGE_CAPTION`

Figure/caption parquet columns are defined in `FigureImageCols` and the row schema in `FigureImageMetadata` (also in `analyzer/schemas.py`).

## Chunking

`preprocessing/TextChunker` splits `text.txt` into overlapping character-based chunks and writes ordered files under `extraction/<pdf_name>/<EXTRACTION_CHUNK_DIR>/` as `chunk_0001.txt`, `chunk_0002.txt`, etc.

Config (see `analyzer/config.py`):

- `EXTRACTION_CHUNK_SIZE` (chars)
- `EXTRACTION_CHUNK_OVERLAP` (chars)
- `EXTRACTION_CHUNK_DIR` (folder name, default `text_chunks`)

## Index build lifecycle

`LuceneIndexer.build()` is invoked at the end of the extraction pipeline (`PdfExtractor.extract_all()`). It:

1. Reads chunk files and image captions
2. Creates/opens the per-PDF Whoosh index
3. Automatically rebuilds the index directory if the on-disk schema differs from the current schema (handles upgrades)

Dependency: `Whoosh==2.7.4` (see `requirements.txt`).

## Programmatic search

Use `analyzer/SwooshSearcher` to open and query an index.

```python
from analyzer.swoosh_searcher import SwooshSearcher
from analyzer.schemas import DocumentTypes

with SwooshSearcher(pdf_name="ID 35") as s:
    hits = s.search(
        "optical flow",
        doc_type=DocumentTypes.CHUNK,  # or DocumentTypes.IMAGE_CAPTION, or None for any
        limit=5,
        return_preview=True,
        max_preview_chars=200,
    )
    for h in hits:
        print(h["id"], h["type"], h.get("order"), h.get("page_index"), h.get("path"))
```

Each `hit` is a dict: `id`, `type`, `pdf`, `order`, `page_index`, `path`, `score`, and optional `preview` (when `return_preview=True`).

## CLI search

There’s a ready-made CLI wrapper: `scripts/search_document.py`.

Examples (run from repo root):

```fish
# Search both chunks and captions
python scripts/search_document.py "ID 35" "cancer" --limit 10

# Only chunks, show a longer preview (up to 240 chars)
python scripts/search_document.py "ID 35" "transformer" --type chunk --show-text --max-chars 240

# Only image captions
python scripts/search_document.py "ID 35" "diagram" --type image_caption --limit 5
```

CLI output shows score, id, type, `order`/`page_index`, `path`, and a short content snippet. With `--show-text`, it also prints a longer preview when available.

## Notes and tips

- Content is indexed (analyzed) but not stored in the index; previews are read from the chunk files on disk to keep index size small.
- If you update the schema, the indexer auto-detects and rebuilds a mismatched per-PDF index on the next run.
- Image captions preview typically won’t show text because `path` for captions points to the image file. The caption text is still indexed and searchable.
