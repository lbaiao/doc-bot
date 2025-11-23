# Image Analysis: Vision-Powered Search and Analysis

This project provides comprehensive image search and analysis capabilities using FAISS vector embeddings for caption search and Claude's vision API for detailed image analysis.

## What gets indexed

Two separate FAISS indexes are built per PDF for image-related content:

### 1. Image Captions Index
Built under `extraction/<pdf_name>/faiss_index_images/` by `analyzer/FaissWrapper` and contains:
- **Caption embeddings**: Vector embeddings of image captions extracted from figures
- **Image metadata**: Image paths, IDs, page locations, dimensions, and caption text

### 2. Text Chunks Index (for reference)
Built under `extraction/<pdf_name>/faiss_index/` - see [vector_search.md](./vector_search.md)

## Architecture

The image analysis system consists of three main components:

### 1. Image Extraction and Caption Detection
**Module**: `preprocessing/pdf_extraction.py`

During PDF extraction (`PdfExtractor.extract_bitmap_images()`):
- Extracts images from PDF pages
- Detects captions by searching text near images (±100px below, 50px above)
- Looks for caption keywords: "figure", "fig.", "table", "image", "photo", "chart", "diagram"
- Stores metadata in `figures_metadata.parquet` with schema defined in `analyzer/schemas.py`

**Metadata Schema** (`FigureImageMetadata`):
```python
id: str              # UUID for the image
page_index: int      # Source page number
image_index: int     # Image number on page
image_path: str      # Absolute path to PNG file
has_caption: bool    # Whether a caption was detected
caption: str         # Caption text (empty if none)
width: int          # Image width in pixels
height: int         # Image height in pixels
```

### 2. Caption Indexing and Search
**Module**: `analyzer/faiss_wrapper.py`

#### Creating the Caption Index

`FaissWrapper.index_image_captions()` workflow:
1. Loads `figures_metadata.parquet` from extraction directory
2. Filters for images with non-empty captions
3. Creates LangChain Documents with:
   - `page_content`: The caption text
   - `metadata`: All image metadata (ID, path, dimensions, page location)
4. Builds FAISS index using the same embedding model as text chunks
5. Saves to `extraction/<pdf_name>/faiss_index_images/`

#### Searching Captions

`SessionRegistry.search_image_captions()` provides semantic search:
- Input: Natural language query (e.g., "neural network diagram")
- Output: Ranked list of images with matching captions
- Returns: Complete image metadata including paths for retrieval

**Configuration** (analyzer/config.py):
```python
EXTRACTION_FAISS_IMAGES_DIR: str = "faiss_index_images"
```

### 3. Image Analysis with Claude Vision
**Module**: `agents/tools.py` → `analyze_images` tool

#### Anthropic Files API Integration

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

#### Vision Analysis Tool

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

## Integration with Extraction Pipeline

The image analysis system is integrated into the PDF extraction pipeline:

**`PdfExtractor.extract_all()` sequence**:
1. `extract_text()` - Extract text from PDF
2. `extract_bitmap_images()` - Extract images + detect captions → `figures_metadata.parquet`
3. `extract_vector_graphics()` - Extract vector figures
4. `extract_text_chunks()` - Chunk text
5. `extract_lucene_index()` - Build lexical search index
6. `extract_embeddings()` - Build FAISS indexes:
   - Text chunks → `faiss_index/`
   - Image captions → `faiss_index_images/`

## Dependencies

```txt
anthropic==0.39.0           # Anthropic API client
langchain-anthropic==1.0.0  # LangChain Anthropic integration
pandas==2.3.3               # Parquet file reading
pyarrow==22.0.0            # Parquet support
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

## Future Enhancements

Potential improvements:
- Base64 encoding option (no API upload required)
- Image preprocessing/resizing before upload
- Persistent cache across sessions (database)
- Support for vector graphics analysis
- Batch analysis with parallel API calls
- Image similarity search (not just captions)
