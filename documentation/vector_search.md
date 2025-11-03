# Vector Search: FAISS Embeddings and Semantic Querying

This project provides semantic search over extracted PDF content using FAISS (Facebook AI Similarity Search) with HuggingFace embeddings for natural language queries.

## What gets indexed

The FAISS vector index is built per PDF under `extraction/<pdf_name>/faiss_index/` by `analyzer/FaissWrapper` and contains:

- **Text chunks**: Vector embeddings of text chunks from `extraction/<pdf_name>/text_chunks/`
- **Document metadata**: Chunk numbers, source paths, and extraction directory info

### Embedding Model

Uses **Google Gemma** embedding model via HuggingFace:
- Model: `google/embeddinggemma-300m` 
- Embedding dimension: 768D vectors
- Distance strategy: `MAX_INNER_PRODUCT` (optimized for inner product search)
- Query/document prompts: Configured per model specifications

## Architecture

The vector search implementation consists of:

### Core Components

1. **`analyzer/FaissWrapper`**: Main FAISS indexing and search interface
2. **`analyzer/config.py`**: Configuration for embedding model and search parameters  
3. **`scripts/vector_search.py`**: CLI tool for semantic search
4. **Integration**: Embedded in `PdfExtractor.extract_embeddings()`

### Configuration (analyzer/config.py)

```python
FAISS_EMBEDDING_MODEL: str = "google/embeddinggemma-300m"
FAISS_DISTANCE_STRATEGY: str = "MAX_INNER_PRODUCT" 
FAISS_SEARCH_K: int = 5  # Default search results
EXTRACTION_FAISS_DIR: str = "faiss_index"  # Index directory name
```

## Document Processing

### Text Chunk Loading

`FaissWrapper.load_text_chunks()` processes text chunks:

1. Reads all `chunk_*.txt` files from `extraction/<pdf_name>/text_chunks/`
2. Creates LangChain `Document` objects with content and metadata
3. Maintains chunk ordering and preserves source file paths
4. Filters out empty chunks

### Metadata Structure

Each indexed document includes:
```python
{
    "source": "/path/to/chunk_file.txt",
    "chunk_number": "0001", 
    "extraction_dir": "/extraction/pdf_name",
    "filename": "chunk_0001.txt"
}
```

## Index Lifecycle

### Build Process

`FaissWrapper.index_extraction_directory()` handles the complete workflow:

1. **Check existing**: Loads existing index if available
2. **Load chunks**: Reads and converts text chunks to documents
3. **Create embeddings**: Uses HuggingFace model to generate vectors
4. **Build index**: Creates FAISS vector store with specified distance strategy
5. **Persist**: Saves index to `extraction/<pdf_name>/faiss_index/`

### Integration

Called automatically in `PdfExtractor.extract_all()` pipeline:
```
extract_text() → extract_images() → extract_vector_graphics() → 
extract_text_chunks() → extract_lucene_index() → extract_embeddings()
```

## Programmatic Search

Use `FaissWrapper` for semantic similarity search:

```python
from analyzer.faiss_wrapper import FaissWrapper
from analyzer.config import default_config
import os

# Initialize wrapper
faiss_wrapper = FaissWrapper()

# Load index for specific PDF
extraction_dir = os.path.join(default_config.EXTRACTION_DIR, "my_document")
success = faiss_wrapper.load_index(extraction_dir)

# Perform semantic search
if success:
    results = faiss_wrapper.search("machine learning algorithms", k=5)
    
    for document, similarity_score in results:
        print(f"Score: {similarity_score:.4f}")
        print(f"Chunk: {document.metadata['chunk_number']}")
        print(f"Content: {document.page_content[:100]}...")
        print(f"Source: {document.metadata['source']}")
        print()
```

### Search Results

Returns list of `(Document, float)` tuples:
- **Document**: LangChain document with `page_content` and `metadata`
- **float**: Similarity score (higher = more similar)

## CLI Search

Ready-made CLI tool: `scripts/vector_search.py`

### Usage Examples

```bash
# Basic semantic search
python scripts/vector_search.py "my_document" "What is machine learning?"

# Extended results with full text preview  
python scripts/vector_search.py "research_paper" "neural networks" --show-text --limit 10

# Force rebuild index
python scripts/vector_search.py "technical_doc" "optimization" --force-rebuild

# Custom preview length
python scripts/vector_search.py "paper" "deep learning" --max-chars 500
```

### CLI Arguments

- `file_name`: PDF name without extension (folder under extraction/)
- `query`: Natural language query for semantic search
- `--limit`: Max results (default: 5)
- `--show-text`: Show extended content preview
- `--max-chars`: Max preview characters (default: 240)
- `--force-rebuild`: Force index rebuild

### Output Format

```
Loaded FAISS index: 33 documents, 768D embeddings
Model: google/embeddinggemma-300m
Distance strategy: MAX_INNER_PRODUCT

Top 5 semantic search results for: "machine learning algorithms"
============================================================
[01] similarity=0.8234 chunk=0015 file=chunk_0015.txt
    content100: Machine learning is a subset of artificial intelligence...
    source:     /path/to/extraction/doc/text_chunks/chunk_0015.txt

[02] similarity=0.7891 chunk=0023 file=chunk_0023.txt  
    content100: Deep learning networks use multiple layers...
    source:     /path/to/extraction/doc/text_chunks/chunk_0023.txt
```

## Performance & Storage

### Index Management

- **Automatic detection**: Loads existing indexes when available
- **Incremental updates**: Rebuilds only when forced or missing
- **Error recovery**: Graceful handling of corrupted or missing indexes

### Memory Efficiency  

- **Lazy loading**: Embeddings model loaded only when needed
- **Chunk-based**: Processes documents in manageable chunks
- **Configurable limits**: Adjustable search result limits

### Storage Requirements

- **Index size**: ~4KB per document (768D float32 vectors)
- **Model cache**: ~300MB for Gemma embedding model (cached locally)
- **Metadata**: Minimal overhead for document metadata

## Dependencies

Key packages (see `requirements.txt`):
```
langchain==1.0.3
langchain-community==0.4.1  
langchain-huggingface==1.0.0
faiss-cpu==1.12.0
transformers @ git+https://github.com/huggingface/transformers
```

## Comparison: Vector vs Lexical Search

| Feature | Vector Search (FAISS) | Lexical Search (Whoosh) |
|---------|----------------------|-------------------------|
| **Query Type** | Natural language | Keywords/boolean |
| **Matching** | Semantic similarity | Exact/fuzzy text match |
| **Use Cases** | Conceptual queries | Specific term lookup |
| **Performance** | ~10-50ms per query | ~1-5ms per query |
| **Index Size** | ~4KB per document | ~1KB per document |
| **Precision** | High for concepts | High for exact terms |

## Notes and Tips

- **Model download**: First run downloads ~300MB embedding model (cached locally)
- **GPU support**: Use `faiss-gpu` instead of `faiss-cpu` for GPU acceleration
- **Query optimization**: Longer, more descriptive queries often yield better results
- **Hybrid approach**: Combine with lexical search for comprehensive document retrieval
- **Index persistence**: Indexes are automatically saved and reloaded between sessions
- **Error handling**: Failed embeddings gracefully fallback without breaking extraction pipeline