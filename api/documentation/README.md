# Doc-Bot: PDF Document Processing and Intelligent Search System

## Overview

Doc-Bot is a comprehensive document intelligence platform that extracts, indexes, and analyzes PDF documents using advanced NLP and computer vision techniques. The system combines lexical search (Whoosh), semantic search (FAISS), and AI-powered analysis (Claude) to provide multi-modal document understanding.

## Key Features

- 🔍 **Multi-Modal Search**: Lexical (keyword), semantic (vector), and hybrid search capabilities
- 🖼️ **Image Analysis**: Extract images, detect captions, and analyze with Claude Vision
- 📊 **Vector Graphics**: Extract and save vector figures from PDFs
- 🤖 **AI Agent**: LangChain-powered conversational agent with tool access
- 💾 **Efficient Caching**: 12-hour TTL cache for image uploads to minimize API costs
- 🔄 **Session Management**: LRU cache for multi-document sessions

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     PDF Input                           │
│                  (pdf_files/)                           │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│              Extraction Pipeline                        │
│  (preprocessing/pdf_extraction.py)                      │
├─────────────────────────────────────────────────────────┤
│  1. Text Extraction      → text.txt                     │
│  2. Image Extraction     → images/ + captions           │
│  3. Vector Graphics      → vector_graphics/             │
│  4. Text Chunking        → text_chunks/                 │
│  5. Lexical Indexing     → lucene_index/                │
│  6. Vector Indexing      → faiss_index/                 │
│  7. Caption Indexing     → faiss_index_images/          │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│              Extraction Directory                       │
│           (extraction/{pdf_name}/)                      │
├─────────────────────────────────────────────────────────┤
│  ├── text.txt                                           │
│  ├── images/                                            │
│  ├── vector_graphics/                                   │
│  ├── text_chunks/                                       │
│  ├── lucene_index/                                      │
│  ├── faiss_index/                                       │
│  ├── faiss_index_images/                                │
│  ├── figures_metadata.parquet                           │
│  └── .anthropic_file_cache.json                         │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│            Session Registry (In-Memory)                 │
│         (session/session_registry.py)                   │
├─────────────────────────────────────────────────────────┤
│  • LRU cache for multiple documents                     │
│  • Lazy loading of indices                              │
│  • Search orchestration                                 │
│  • Image upload management                              │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│              Agent Tools Layer                          │
│            (agents/tools.py)                            │
├─────────────────────────────────────────────────────────┤
│  • set_active_document    • text_search                 │
│  • vector_search          • get_chunks                  │
│  • search_caption         • hybrid_search               │
│  • analyze_images                                       │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│           LangChain Agent (Claude)                      │
│            (agents/agent.py)                            │
└─────────────────────────────────────────────────────────┘
```

## Project Structure

```
api/
├── agents/                      # Agent and tool definitions
│   ├── agent.py                # LangChain agent factory
│   └── tools.py                # Tool implementations
├── analyzer/                    # Core analysis modules
│   ├── anthropic_cache.py      # Image upload cache
│   ├── config.py               # Configuration management
│   ├── faiss_wrapper.py        # Vector search wrapper
│   ├── schemas.py              # Data schemas
│   └── woosh_searcher.py       # Lexical search wrapper
├── documentation/               # Project documentation
│   ├── README.md               # This file
│   ├── getting_started.md      # Setup guide
│   ├── architecture.md         # Technical architecture
│   ├── extraction_pipeline.md  # PDF processing details
│   ├── lexical_search.md       # Whoosh indexing
│   ├── vector_search.md        # FAISS embeddings
│   ├── image_analysis.md       # Vision capabilities
│   ├── agent_tools.md          # Tool reference
│   └── api_reference.md        # Code API docs
├── preprocessing/               # PDF extraction modules
│   ├── chunker.py              # Text chunking
│   ├── pdf_extraction.py       # Main extraction logic
│   ├── vector_figure_extractor.py  # Vector graphics
│   └── woosh_indexer.py        # Lucene indexing
├── scripts/                     # CLI utilities
│   ├── agent_chat.py           # Interactive agent chat
│   ├── regular_chat.py         # Direct Claude chat
│   ├── search_document.py      # Search CLI
│   ├── vector_search.py        # Vector search CLI
│   └── print_parquet.py        # Parquet viewer
├── session/                     # Session management
│   └── session_registry.py     # Multi-doc session handler
├── extraction/                  # Extracted data (gitignored)
├── pdf_files/                   # Input PDFs (gitignored)
├── main.py                      # Batch extraction entry point
└── requirements.txt             # Python dependencies
```

## Core Components

### 1. Extraction Pipeline
**File**: `preprocessing/pdf_extraction.py`

Orchestrates the complete PDF processing workflow:
- Text extraction using PyMuPDF
- Image extraction with caption detection
- Vector graphics extraction
- Text chunking with overlap
- Multi-index building (lexical + vector)

See: [extraction_pipeline.md](./extraction_pipeline.md)

### 2. Search Engines

#### Lexical Search (Whoosh)
**Files**: `preprocessing/woosh_indexer.py`, `analyzer/woosh_searcher.py`

Fast keyword-based search over text chunks and image captions.

See: [lexical_search.md](./lexical_search.md)

#### Vector Search (FAISS)
**File**: `analyzer/faiss_wrapper.py`

Semantic search using Google Gemma embeddings (768D vectors).
- Text chunks index
- Image captions index

See: [vector_search.md](./vector_search.md)

#### Hybrid Search
**File**: `session/session_registry.py`

Combines lexical and vector search with configurable weights for optimal recall.

### 3. Image Analysis
**Files**: `analyzer/anthropic_cache.py`, `agents/tools.py`

Vision-powered image analysis using Claude:
- Caption-based image search
- Vision API integration
- Intelligent caching (12-hour TTL)

See: [image_analysis.md](./image_analysis.md)

### 4. AI Agent
**Files**: `agents/agent.py`, `agents/tools.py`

LangChain agent with conversational document analysis:
- Multi-turn conversations
- Tool-augmented reasoning
- Context-aware responses

See: [agent_tools.md](./agent_tools.md)

### 5. Session Registry
**File**: `session/session_registry.py`

Manages multi-document sessions with:
- LRU cache (max 4 documents)
- Lazy index loading
- Unified search interface
- Image upload orchestration

## Quick Start

### 1. Installation

```bash
cd api/
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configuration

Create `.env` file:
```bash
ANTHROPIC_API_KEY=your_api_key_here
```

### 3. Process PDFs

```bash
# Place PDFs in pdf_files/
python main.py
```

### 4. Interactive Agent Chat

```bash
python scripts/agent_chat.py
```

See: [getting_started.md](./getting_started.md)

## Usage Examples

### Batch Processing
```python
from preprocessing.pdf_extraction import PdfExtractor

with PdfExtractor("document.pdf") as extractor:
    extractor.extract_all()
```

### Search Documents
```python
from session.session_registry import default_registry

# Lexical search
results = default_registry.search_lexical("ID 35", "neural networks", limit=5)

# Vector search
results = default_registry.search_vector("ID 35", "deep learning architecture", k=5)

# Hybrid search
results = default_registry.hybrid_search("ID 35", "attention mechanism", k=5)
```

### Agent Conversation
```python
from agents.agent import make_document_agent

agent = make_document_agent()
response = agent.invoke({
    "messages": [("user", "What are the main findings in this paper?")]
})
```

## Key Technologies

| Technology | Purpose | Version |
|------------|---------|---------|
| **PyMuPDF** | PDF text/image extraction | 1.26.5 |
| **Whoosh** | Lexical search engine | 2.7.4 |
| **FAISS** | Vector similarity search | 1.12.0 |
| **LangChain** | Agent framework | 1.0.3 |
| **Anthropic** | Claude API client | 0.39.0 |
| **HuggingFace** | Embedding models | 0.36.0 |
| **Pandas** | Data manipulation | 2.3.3 |

See full dependencies in [requirements.txt](../requirements.txt)

## Configuration

All configuration is managed via `analyzer/config.py` with `.env` support:

### Key Settings

```python
# Extraction
EXTRACTION_CHUNK_SIZE = 2000      # Characters per chunk
EXTRACTION_CHUNK_OVERLAP = 300    # Overlap between chunks

# Vector Search
FAISS_EMBEDDING_MODEL = "google/embeddinggemma-300m"
FAISS_DISTANCE_STRATEGY = "MAX_INNER_PRODUCT"
FAISS_SEARCH_K = 5

# Image Analysis
ANTHROPIC_FILE_TTL_HOURS = 12
IMAGE_UPLOAD_LIMIT = 20
```

## Performance Characteristics

### Extraction Speed
- **Small PDF** (10 pages, few images): ~5-10 seconds
- **Medium PDF** (50 pages, ~20 images): ~30-60 seconds
- **Large PDF** (200+ pages, 100+ images): 2-5 minutes

Bottlenecks:
- PyMuPDF image extraction
- FAISS index building
- Vector graphics extraction

### Search Speed
- **Lexical**: <50ms (Whoosh is fast)
- **Vector**: 50-200ms (depends on corpus size)
- **Hybrid**: 100-300ms (combined)

### Memory Usage
- **Per-document session**: ~200-500MB
- **FAISS index**: ~5-50MB per document
- **Peak during extraction**: 1-2GB

## API Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `agent_chat.py` | Interactive agent interface | `python scripts/agent_chat.py` |
| `regular_chat.py` | Direct Claude chat | `python scripts/regular_chat.py` |
| `search_document.py` | Search CLI | `python scripts/search_document.py "query"` |
| `vector_search.py` | Vector search CLI | `python scripts/vector_search.py "query"` |
| `print_parquet.py` | View image metadata | `python scripts/print_parquet.py path.parquet` |

## Limitations

1. **Text Extraction**: OCR not supported - requires text-based PDFs
2. **Vector Graphics**: Complex diagrams may not extract cleanly
3. **Caption Detection**: Heuristic-based, may miss non-standard formats
4. **Memory**: Large documents (1000+ pages) may require significant RAM
5. **Image Analysis**: Subject to Anthropic API rate limits and costs

## Troubleshooting

### Common Issues

**Problem**: ModuleNotFoundError
```bash
# Solution: Ensure you're in the venv
source venv/bin/activate
pip install -r requirements.txt
```

**Problem**: Empty extraction results
```bash
# Check: Is the PDF text-based or scanned?
# Scanned PDFs require OCR (not implemented)
```

**Problem**: FAISS index fails to load
```bash
# Solution: Rebuild the index
rm -rf extraction/*/faiss_index*
python main.py
```

**Problem**: Anthropic API errors
```bash
# Check: Is ANTHROPIC_API_KEY set in .env?
# Check: Do you have API credits?
```

## Documentation Index

1. **[Getting Started](./getting_started.md)** - Installation and first steps
2. **[Architecture](./architecture.md)** - System design and data flow
3. **[Extraction Pipeline](./extraction_pipeline.md)** - PDF processing details
4. **[Lexical Search](./lexical_search.md)** - Whoosh indexing and search
5. **[Vector Search](./vector_search.md)** - FAISS embeddings and semantic search
6. **[Image Analysis](./image_analysis.md)** - Vision capabilities and caching
7. **[Agent Tools](./agent_tools.md)** - Tool reference and examples
8. **[API Reference](./api_reference.md)** - Code-level documentation

## Contributing

### Code Style
- Follow PEP 8
- Use type hints where possible
- Document with docstrings (Google style)

### Adding New Features
1. Create feature branch
2. Implement with tests
3. Update documentation
4. Submit PR

## License

[Add your license information here]

## Support

For issues, questions, or contributions:
- GitHub Issues: [your-repo-url]
- Email: [your-email]

## Changelog

See [CHANGELOG.md](./CHANGELOG.md) for version history.

---

**Version**: 1.0.0  
**Last Updated**: November 2025  
**Author**: [Your Name]
