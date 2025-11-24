# System Architecture

This document provides a detailed technical overview of Doc-Bot's architecture, design decisions, and data flows.

## High-Level Architecture

Doc-Bot follows a **layered architecture** with clear separation of concerns:

```
┌──────────────────────────────────────────────────────────────┐
│                    Presentation Layer                         │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐             │
│  │ Agent CLI  │  │ Search CLI │  │   API      │             │
│  └────────────┘  └────────────┘  └────────────┘             │
└──────────────────────────────────────────────────────────────┘
                           │
┌──────────────────────────────────────────────────────────────┐
│                    Application Layer                          │
│  ┌─────────────────────────────────────────────────────┐     │
│  │  LangChain Agent (agents/agent.py)                  │     │
│  │  ┌──────────┐ ┌──────────┐ ┌───────────────────┐   │     │
│  │  │  Tools   │ │ Memory   │ │  Conversation     │   │     │
│  │  └──────────┘ └──────────┘ └───────────────────┘   │     │
│  └─────────────────────────────────────────────────────┘     │
│                           │                                   │
│  ┌─────────────────────────────────────────────────────┐     │
│  │  Agent Tools (agents/tools.py)                      │     │
│  │  • search_caption  • text_search  • vector_search   │     │
│  │  • hybrid_search   • get_chunks   • analyze_images  │     │
│  └─────────────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────────┘
                           │
┌──────────────────────────────────────────────────────────────┐
│                    Service Layer                              │
│  ┌─────────────────────────────────────────────────────┐     │
│  │  Session Registry (session/session_registry.py)    │     │
│  │  • Document session management (LRU cache)          │     │
│  │  • Unified search interface                         │     │
│  │  • Image upload orchestration                       │     │
│  └─────────────────────────────────────────────────────┘     │
│                           │                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ FaissWrapper │  │WooshSearcher │  │AnthropicCache│       │
│  │ (analyzer/)  │  │ (analyzer/)  │  │ (analyzer/)  │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└──────────────────────────────────────────────────────────────┘
                           │
┌──────────────────────────────────────────────────────────────┐
│                 Data Processing Layer                         │
│  ┌─────────────────────────────────────────────────────┐     │
│  │  PDF Extraction (preprocessing/pdf_extraction.py)  │     │
│  │  • Text extraction       • Image extraction         │     │
│  │  • Caption detection     • Vector graphics          │     │
│  │  • Text chunking         • Index building           │     │
│  └─────────────────────────────────────────────────────┘     │
│                           │                                   │
│  ┌──────────┐  ┌──────────┐  ┌─────────────────┐            │
│  │ Chunker  │  │  Woosh   │  │ VectorExtractor │            │
│  │          │  │ Indexer  │  │                 │            │
│  └──────────┘  └──────────┘  └─────────────────┘            │
└──────────────────────────────────────────────────────────────┘
                           │
┌──────────────────────────────────────────────────────────────┐
│                    Storage Layer                              │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐             │
│  │ File System│  │  Parquet   │  │   Caches   │             │
│  │ (text,imgs)│  │ (metadata) │  │   (JSON)   │             │
│  └────────────┘  └────────────┘  └────────────┘             │
└──────────────────────────────────────────────────────────────┘
```

## Core Design Principles

### 1. **Configuration-Driven**
All settings centralized in `analyzer/config.py`:
- Uses `pydantic-settings` for type safety
- Environment variable support via `.env`
- Single source of truth for paths and parameters

### 2. **Context Manager Pattern**
Resources are managed with Python context managers:
```python
with PdfExtractor(file_path) as extractor:
    extractor.extract_all()
```
Ensures proper cleanup of file handles and memory.

### 3. **Lazy Loading**
Session registry loads resources on-demand:
- Indices opened only when needed
- LRU eviction for memory management
- Cached for subsequent access

### 4. **Separation of Concerns**
- **Extraction**: PDF → structured data
- **Indexing**: Data → searchable indices
- **Search**: Query → results
- **Analysis**: Results → insights

### 5. **Modular Tools**
Agent tools are self-contained and composable:
- Each tool has single responsibility
- Tools can be combined by agent
- Easy to add new capabilities

## Data Flow

### Extraction Pipeline

```
PDF File
   │
   ▼
┌─────────────────────────────────────┐
│ PdfExtractor.__init__()             │
│ • Opens PDF with PyMuPDF            │
│ • Creates output directory          │
└─────────────────────────────────────┘
   │
   ▼
┌─────────────────────────────────────┐
│ extract_text()                      │
│ • Iterates pages                    │
│ • Extracts text with PyMuPDF        │
│ • Writes to text.txt                │
└─────────────────────────────────────┘
   │
   ▼
┌─────────────────────────────────────┐
│ extract_bitmap_images()             │
│ • Gets images per page              │
│ • Converts CMYK → RGB               │
│ • Detects captions (±100px/50px)    │
│ • Saves PNG files                   │
│ • Builds parquet metadata           │
└─────────────────────────────────────┘
   │
   ▼
┌─────────────────────────────────────┐
│ extract_vector_graphics()           │
│ • Analyzes drawing commands         │
│ • Scores potential figures          │
│ • Merges overlapping regions        │
│ • Saves as PNG/SVG                  │
└─────────────────────────────────────┘
   │
   ▼
┌─────────────────────────────────────┐
│ extract_text_chunks()               │
│ • Reads text.txt                    │
│ • Splits with overlap               │
│ • Writes chunk_NNNN.txt files       │
└─────────────────────────────────────┘
   │
   ▼
┌─────────────────────────────────────┐
│ extract_lucene_index()              │
│ • Reads chunks + captions           │
│ • Creates Whoosh schema             │
│ • Builds searchable index           │
└─────────────────────────────────────┘
   │
   ▼
┌─────────────────────────────────────┐
│ extract_embeddings()                │
│ • Embeds text chunks → faiss_index  │
│ • Embeds captions → faiss_index_imgs│
│ • Uses Google Gemma model           │
└─────────────────────────────────────┘
```

### Search Pipeline

```
User Query
   │
   ▼
┌─────────────────────────────────────┐
│ SessionRegistry.ensure(doc_id)      │
│ • Check LRU cache                   │
│ • Load indices if not cached        │
│ • Initialize searchers              │
└─────────────────────────────────────┘
   │
   ├─────────────┬─────────────┬──────────────┐
   ▼             ▼             ▼              ▼
┌─────────┐ ┌─────────┐ ┌──────────┐ ┌─────────────┐
│Lexical  │ │ Vector  │ │ Caption  │ │   Hybrid    │
│ Search  │ │ Search  │ │  Search  │ │   Search    │
└─────────┘ └─────────┘ └──────────┘ └─────────────┘
   │             │             │              │
   ▼             ▼             ▼              ▼
┌─────────┐ ┌─────────┐ ┌──────────┐ ┌─────────────┐
│ Whoosh  │ │ FAISS   │ │  FAISS   │ │  Combined   │
│ Index   │ │Text Idx │ │Image Idx │ │ (weighted)  │
└─────────┘ └─────────┘ └──────────┘ └─────────────┘
   │             │             │              │
   └─────────────┴─────────────┴──────────────┘
                       │
                       ▼
                   Results
```

### Image Analysis Flow

```
User Request: "Analyze figure 3"
   │
   ▼
┌─────────────────────────────────────┐
│ search_caption("figure 3")          │
│ • Embeds query                      │
│ • Searches FAISS caption index      │
│ • Returns image metadata + IDs      │
└─────────────────────────────────────┘
   │
   ▼
┌─────────────────────────────────────┐
│ analyze_images(image_ids, instr)    │
│ • Parse image IDs                   │
└─────────────────────────────────────┘
   │
   ▼
┌─────────────────────────────────────┐
│ upload_images_to_anthropic()        │
│ • Load image metadata from parquet  │
└─────────────────────────────────────┘
   │
   ├─ For each image ───────────────┐
   │                                 │
   ▼                                 ▼
┌──────────────┐           ┌──────────────────┐
│ Check Cache  │           │   Cache Miss     │
│ (12hr TTL)   │           │   Read PNG       │
└──────────────┘           │   Upload to API  │
   │ Hit                   │   Cache file_id  │
   │                       └──────────────────┘
   └─────────┬─────────────────────┘
             │
             ▼
   ┌──────────────────────┐
   │ Build Message        │
   │ • Context (optional) │
   │ • Image blocks       │
   │ • Instruction        │
   └──────────────────────┘
             │
             ▼
   ┌──────────────────────┐
   │ Claude Vision API    │
   │ (Sonnet 4.5)         │
   └──────────────────────┘
             │
             ▼
         Analysis Result
```

## Component Details

### SessionRegistry

**Purpose**: Manage multi-document sessions with efficient resource loading

**Key Features:**
- LRU cache (max 4 documents by default)
- Lazy loading of indices
- Unified search interface
- Image upload coordination

**Data Structure:**
```python
@dataclass
class DocResources:
    doc_id: str
    vector_index: VectorIndex           # Text chunks FAISS
    image_captions_index: VectorIndex   # Captions FAISS
    text_index: TextSearchIndex         # Whoosh
    chunks_dir: str
    parquet_path: str
    anthropic_cache: AnthropicFileCache
```

**LRU Eviction:**
```python
# When cache full:
if len(sessions) >= max_sessions:
    evict_id = lru.pop(0)  # Oldest
    sessions.pop(evict_id)
```

### FaissWrapper

**Purpose**: Abstraction over FAISS with LangChain integration

**Key Methods:**
- `load_text_chunks()`: Read chunks → Documents
- `create_index()`: Documents → FAISS index
- `load_index()`: Disk → FAISS
- `search()`: Query → ranked results
- `index_image_captions()`: Captions workflow

**Embedding Process:**
```python
# Using HuggingFace Transformers
embeddings = HuggingFaceEmbeddings(
    model_name="google/embeddinggemma-300m",
    query_encode_kwargs={"prompt_name": "query"},
    encode_kwargs={"prompt_name": "document"}
)

# Create index
vector_store = FAISS.from_documents(
    documents,
    embeddings,
    distance_strategy="MAX_INNER_PRODUCT"
)
```

### WooshSearcher

**Purpose**: Whoosh search with document type filtering

**Schema:**
```python
schema = Schema(
    id=ID(stored=True),
    pdf=ID(stored=True),
    type=ID(stored=True),          # CHUNK or IMAGE_CAPTION
    order=NUMERIC(stored=True),     # Chunk order
    page_index=NUMERIC(stored=True),
    path=ID(stored=True),
    content=TEXT(stored=False)      # Analyzed, not stored
)
```

**Query Parsing:**
```python
# With doc_type filter
query_parser = QueryParser("content", schema=index.schema)
query = query_parser.parse(query_string)

if doc_type != "any":
    type_filter = Term("type", doc_type)
    query = And([query, type_filter])
```

### AnthropicFileCache

**Purpose**: Minimize redundant image uploads to Anthropic API

**Cache Structure:**
```json
{
  "image_uuid": {
    "file_id": "file_abc123",
    "uploaded_at": "2025-11-24T10:00:00",
    "expires_at": "2025-11-24T22:00:00",
    "image_path": "/path/to/image.png",
    "image_id": "image_uuid"
  }
}
```

**TTL Management:**
- Default: 12 hours
- Automatic expiry checking on load
- Cleanup on save

### Agent Architecture

**LangChain Agent:**
```python
agent = create_agent(
    model=ChatAnthropic(model="claude-haiku-4-5"),
    tools=[
        text_search,
        vector_search,
        search_caption,
        hybrid_search,
        get_chunks,
        analyze_images,
    ]
)
```

**Tool Execution Flow:**
1. User sends message
2. Agent decides which tool(s) to call
3. Tool returns JSON result
4. Agent synthesizes response
5. Loop continues for follow-ups

## Performance Optimizations

### 1. **Chunking Strategy**
```python
CHUNK_SIZE = 2000 chars      # ~500 tokens
OVERLAP = 300 chars          # 15% overlap
```
**Rationale:**
- 500 tokens fits most LLM context windows efficiently
- 15% overlap ensures semantic continuity
- Character-based (not token-based) for speed

### 2. **FAISS Distance Metric**
```python
distance_strategy = "MAX_INNER_PRODUCT"
```
**Rationale:**
- Optimized for embedding models that output normalized vectors
- Faster than cosine similarity
- Equivalent results for unit vectors

### 3. **Image Caching**
```python
TTL = 12 hours
```
**Rationale:**
- Anthropic file uploads are temporary anyway
- Balances freshness with API efficiency
- Reduces costs for multi-turn conversations

### 4. **LRU Session Cache**
```python
max_sessions = 4
```
**Rationale:**
- Most users work with 1-2 documents at a time
- Keeps memory footprint reasonable
- Allows quick switching between recent docs

## Scalability Considerations

### Current Limitations
- **Single-process**: No distributed processing
- **In-memory sessions**: Lost on restart
- **File-based storage**: Not suitable for thousands of PDFs
- **No async**: Sequential processing only

### Future Improvements

**For Production:**
1. **Database backend** (PostgreSQL + pgvector)
2. **Redis cache** for session state
3. **Celery queue** for async extraction
4. **FastAPI** for REST endpoints
5. **Docker** deployment
6. **Horizontal scaling** with load balancer

**For Large Scale:**
1. **Elasticsearch** for lexical search
2. **Pinecone/Weaviate** for vector search
3. **S3/MinIO** for file storage
4. **Kubernetes** orchestration
5. **Monitoring** (Prometheus + Grafana)

## Error Handling

### Strategy
- **Graceful degradation**: Continue on non-critical errors
- **Logging**: Comprehensive error logging
- **User feedback**: Clear error messages

### Examples

**Missing Index:**
```python
try:
    index = load_index(path)
except FileNotFoundError:
    logger.warning(f"Index not found: {path}")
    return []  # Empty results
```

**API Failure:**
```python
try:
    response = anthropic_client.upload(image)
except Exception as e:
    logger.error(f"Upload failed: {e}")
    continue  # Skip this image
```

## Security Considerations

### Data Privacy
- PDFs and extracted data stay local
- Only image content sent to Anthropic
- No text sent to external services (embeddings local)

### API Keys
- Stored in `.env` (not committed)
- Loaded via `pydantic-settings`
- Never logged

### File Access
- Sandboxed to `pdf_files/` and `extraction/`
- No arbitrary file system access

## Testing Strategy

### Unit Tests
- Individual components (extractors, searchers)
- Mock external dependencies (Anthropic API)

### Integration Tests
- End-to-end extraction pipeline
- Multi-document sessions
- Agent conversations

### Performance Tests
- Large PDFs (1000+ pages)
- Many images (100+)
- Concurrent sessions

## Monitoring and Observability

### Logging Levels
- **DEBUG**: Detailed operation logs
- **INFO**: High-level progress
- **WARNING**: Recoverable issues
- **ERROR**: Failures

### Metrics to Track
- Extraction time per PDF
- Search latency (p50, p95, p99)
- Cache hit rate
- API costs

## Deployment Architecture

### Development
```
Local Machine
├── Python venv
├── SQLite (Whoosh)
├── Local file storage
└── Direct API calls
```

### Production (Recommended)
```
Load Balancer
     │
     ├─── App Server 1 ─── Redis Cache
     ├─── App Server 2 ─── Redis Cache
     └─── App Server N ─── Redis Cache
              │
              ├─── PostgreSQL + pgvector
              ├─── S3/MinIO (files)
              └─── Celery Workers
```

## Further Reading

- [Extraction Pipeline Details](./extraction_pipeline.md)
- [Search Implementation](./lexical_search.md)
- [Vector Search Deep Dive](./vector_search.md)
- [Agent Tools Reference](./agent_tools.md)
