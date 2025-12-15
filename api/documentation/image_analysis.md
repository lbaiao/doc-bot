# Image Analysis: Vision-Powered Search and Analysis

This project provides comprehensive image search and analysis capabilities using **Qdrant** for semantic caption search and **Claude's Vision API** for detailed image analysis.

## Extraction Pipeline

The image extraction process is an asynchronous ETL pipeline that moves data from the raw PDF to Postgres, Object Storage, and Vector Indexes.

### 1. Triggering & Orchestration
**Files**: `api/app/routers/documents.py`, `api/app/services/ingestion.py`

1.  **Upload**: User uploads a PDF via `POST /documents:upload`.
2.  **Storage**: The raw PDF is saved to object storage (`documents/{id}/{filename}`).
3.  **Job Creation**: A `Document` record is created in Postgres with status `ingesting`.
4.  **Ingestion**: The `IngestionService.ingest_document` method is called (currently inline).

### 2. Core Extraction Logic
**Files**: `api/preprocessing/pdf_extraction.py`, `api/preprocessing/vector_figure_extractor.py`

The `PdfExtractor` class uses `PyMuPDF` (fitz) to perform two types of image extraction:

#### A. Bitmap (Raster) Images
*   **Method**: `extract_bitmap_images()`
*   **Detection**: Scans pages for embedded image objects (`page.get_images()`).
*   **Processing**: Extracts raw bytes, converts CMYK to RGB if necessary.
*   **Captioning**: Searches for text immediately above/below the image using heuristics (keywords like "Figure", "Table").
*   **Output**: Saves PNGs to disk and logs metadata to `figures_metadata.parquet`.

#### B. Vector Graphics
*   **Method**: `extract_vector_graphics()`
*   **Detection**: Identifies clusters of drawing commands (lines, curves) that likely represent charts or diagrams.
*   **Filtering**: Uses heuristics (segment count, density, aspect ratio) to ignore simple lines or text borders.
*   **Rasterization**: Converts the detected vector region into a high-DPI PNG.

### 3. Data Persistence
**File**: `api/app/services/ingestion.py` (`_save_figures`)

Once extraction is complete, the `IngestionService` persists the results:

1.  **Object Storage**: Uploads extracted PNGs to `figures/{doc_id}/{image_name}`.
2.  **Relational DB (Postgres)**: Creates `Figure` records containing:
    *   `document_id`, `page_id`
    *   `figure_no`
    *   `caption_text`
    *   `storage_uri`
    *   `bbox_json` (dimensions)
3.  **Vector DB (Qdrant)**:
    *   Generates embeddings for **captions** (using the text embedding model).
    *   Upserts points to the `image_embeddings` collection in Qdrant.
    *   *Note: We embed captions, not the image pixels, to enable semantic text-to-image search.*

## Indexing & Search

### Qdrant Collections
The system uses Qdrant for all vector operations.

*   **Collection**: `image_embeddings`
*   **Vector Size**: 768 (matches text embedding model)
*   **Payload**:
    *   `figure_id`: UUID of the figure
    *   `document_id`: UUID of the parent document
    *   `caption`: The extracted caption text
    *   `storage_uri`: Path to the image in object storage

### Local Artifacts (Legacy/Debug)
The `PdfExtractor` also generates local FAISS indexes in the extraction directory (`extraction/<pdf_name>/faiss_index_images/`). These are primarily for debugging or offline analysis and are not used by the main API endpoints.

## Image Analysis with Claude Vision
**Module**: `agents/tools.py` → `analyze_images` tool

### Anthropic Files API Integration

Images are uploaded to Anthropic's Files API for vision analysis:

**Cache Management** (`analyzer/anthropic_cache.py`):
- Per-document cache stored as `.anthropic_file_cache.json` in extraction directory
- TTL: 12 hours (configurable via `ANTHROPIC_FILE_TTL_HOURS`)
- Tracks: file_id, upload timestamp, expiry, image path, image ID
- Automatic expiry checking and cleanup

**Upload Process** (`SessionRegistry.upload_images_to_anthropic()`):
1. Check cache for existing file IDs (not expired)
2. Upload missing/expired images to Anthropic Files API
3. Update cache with new file IDs and expiry timestamps
4. Return file IDs and metadata for use in vision API calls

**Configuration** (analyzer/config.py):
```python
ANTHROPIC_FILE_CACHE_NAME: str = ".anthropic_file_cache.json"
ANTHROPIC_FILE_TTL_HOURS: int = 12
ANTHROPIC_FILES_BETA_HEADER: str = "files-api-2025-04-14"
IMAGE_UPLOAD_LIMIT: int = 20  # Max images per batch
```

### Vision Analysis Tool

The `analyze_images` tool provides flexible image analysis for LangChain agents:

**Parameters**:
- `image_ids` (required): Comma-separated UUIDs from `search_caption` results
- `instruction` (required): What you want Claude to analyze
  - Examples: "Describe what you see", "Extract equations", "Compare these diagrams"
- `context` (optional): Additional background to help with analysis
  - Examples: "These are from a neural networks paper", "User is asking about methodology"

**Process**:
1. Parse image IDs and fetch from parquet metadata
2. Upload images to Anthropic (using cache when possible)
3. Build message with:
   - Optional context text
   - Image content blocks (via Files API)
   - Analysis instruction
4. Call Claude Sonnet 4.5 with vision enabled
5. Return analysis with metadata and cache statistics

**Response Format**:
```json
{
  "document": "ID 35",
  "analysis": "Claude's detailed analysis text...",
  "images_analyzed": 2,
  "cached_count": 1,
  "uploaded_count": 1,
  "image_metadata": [
    {
      "image_id": "uuid123",
      "image_path": "/path/to/image.png",
      "page_index": 5,
      "caption": "Figure 10: ...",
      "width": 800,
      "height": 600
    }
  ]
}
```

## Agent Tools

### search_caption(query, k=5)
**Purpose**: Find images by caption similarity

**Usage**:
```python
search_caption("neural network architecture diagram")
```

**Returns**: List of images with captions matching the query
```json
{
  "document": "ID 35",
  "query": "neural network",
  "count": 3,
  "results": [
    {
      "image_id": "uuid123",
      "image_path": "/path/to/image.png",
      "page_index": 5,
      "image_index": 1,
      "caption": "Figure 3: Neural network architecture showing...",
      "score": 0.89,
      "width": 800,
      "height": 600,
      "has_caption": true
    }
  ]
}
```

### analyze_images(image_ids, instruction, context="")
**Purpose**: Get Claude's vision-powered analysis of images

**Usage Examples**:
```python
# Simple description
analyze_images(
    image_ids="uuid1,uuid2",
    instruction="Describe what you see in these figures"
)

# Specific information extraction
analyze_images(
    image_ids="uuid3",
    instruction="Find the intensity value for cisplatin + TSA in Panel A",
    context="This is Figure 10 from a cancer treatment study"
)

# Comparative analysis
analyze_images(
    image_ids="uuid4,uuid5",
    instruction="Compare these two network architectures and explain the key differences"
)

# Data extraction
analyze_images(
    image_ids="uuid6",
    instruction="Extract all equations and variable definitions",
    context="User is asking about the mathematical formulation in Section 3"
)
```

**Returns**: Claude's analysis with metadata
```json
{
  "document": "ID 35",
  "analysis": "The figure shows a convolutional neural network architecture with three main components...",
  "images_analyzed": 2,
  "cached_count": 1,
  "uploaded_count": 1,
  "image_metadata": [...]
}
```

## Complete Workflow Example

### User Query: "What's the architecture shown in the neural network diagram?"

**Agent Execution**:
```python
# Step 1: Find relevant images
search_caption("neural network architecture diagram")
# Returns: [{"image_id": "abc123", "caption": "Figure 3: Neural network..."}]

# Step 2: Analyze the image
analyze_images(
    image_ids="abc123",
    instruction="Describe the neural network architecture shown in this diagram, including the layer types, connections, and key components",
    context="User is asking about the neural network architecture"
)
# Returns: Detailed analysis of the architecture
```

## Dependencies

```txt
anthropic==0.39.0           # Anthropic API client
langchain-anthropic==1.0.0  # LangChain Anthropic integration
pandas==2.3.3               # Parquet file reading
pyarrow==22.0.0            # Parquet support
qdrant-client              # Vector DB client
```

## Files API Details

**Supported formats**: JPEG, PNG, GIF, WebP

**API Requirements**:
- Beta header: `anthropic-beta: files-api-2025-04-14`
- Model: `claude-sonnet-4-5-20250929` (vision-enabled)
- Request size limit: 32MB
- Images per request: Up to 100 (we limit to 20 by default)

**Upload Example**:
```python
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
file = client.beta.files.upload(
    file=("image.png", open("/path/to/image.png", "rb"), "image/png"),
)
file_id = file.id  # Use in message content blocks
```

**Message Format**:
```python
message = {
    "role": "user",
    "content": [
        {"type": "text", "text": "Optional context"},
        {"type": "image", "source": {"type": "file", "file_id": "file_abc123"}},
        {"type": "text", "text": "Analysis instruction"}
    ]
}
```

## Performance Considerations

### Caching Strategy
- **Purpose**: Avoid redundant uploads to Anthropic API
- **TTL**: 12 hours (Anthropic's files are temporary)
- **Storage**: Per-document JSON cache in extraction directory
- **Benefits**: Faster response times, reduced API costs

### Token Costs
Images consume tokens based on size:
- Formula: `tokens = (width × height) / 750`
- Example: 1000×1000 image ≈ 1,334 tokens
- Max efficient size: 1.15 megapixels (1568px max dimension)

### Best Practices
1. Use `search_caption` to find relevant images before analyzing
2. Provide specific instructions to get focused analysis
3. Include context to help Claude understand the domain
4. Batch related images in single `analyze_images` call
5. Images are cached for 12 hours - reanalyze within TTL to avoid re-upload

## Error Handling

The system handles common errors gracefully:
- Missing parquet file → Returns error, empty results
- Image file not found → Skips that image, continues with others
- Upload failure → Logs error, skips failed image
- Expired cache entries → Automatically re-uploads
- Invalid image format → Skips with warning
