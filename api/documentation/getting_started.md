# Getting Started with Doc-Bot

This guide will help you set up and start using Doc-Bot for PDF document processing and analysis.

## Prerequisites

- **Python**: 3.10 or higher
- **Operating System**: Linux, macOS, or Windows
- **Memory**: Minimum 4GB RAM (8GB+ recommended for large PDFs)
- **Disk Space**: ~500MB for dependencies + space for extracted data

## Installation

### 1. Clone the Repository

```bash
git clone [your-repo-url]
cd doc-bot/api
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate it
# On Linux/macOS:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

This will install all required packages including:
- PyMuPDF (PDF processing)
- Whoosh (lexical search)
- FAISS (vector search)
- LangChain (agent framework)
- Anthropic SDK (Claude AI)

### 4. Set Up Configuration

Create a `.env` file in the `api/` directory:

```bash
# Required for image analysis and agent
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Optional: Override default settings
# EXTRACTION_CHUNK_SIZE=2000
# FAISS_SEARCH_K=5
```

**Get an Anthropic API Key:**
1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Sign up or log in
3. Navigate to API Keys
4. Create a new key

### 5. Verify Installation

```bash
# Test imports
python -c "import pymupdf, whoosh, faiss, langchain; print('✓ All dependencies installed')"
```

## First Steps

### Step 1: Prepare Your PDFs

Place PDF files in the `pdf_files/` directory:

```bash
mkdir -p pdf_files
cp /path/to/your/document.pdf pdf_files/
```

**Supported PDFs:**
- ✅ Text-based PDFs (most modern documents)
- ✅ PDFs with embedded images
- ✅ PDFs with vector graphics
- ❌ Scanned PDFs (OCR not yet supported)

### Step 2: Extract and Index

Run the extraction pipeline:

```bash
python main.py
```

This will:
1. Process all PDFs in `pdf_files/`
2. Extract text, images, and graphics
3. Build lexical and vector indexes
4. Store results in `extraction/{pdf_name}/`

**What happens:**
```
Processing: document.pdf
├── [1/7] Extracting text...                    ✓ (2.3s)
├── [2/7] Extracting images...                  ✓ (8.1s)
│   └── Found 15 images, 12 with captions
├── [3/7] Extracting vector graphics...         ✓ (3.2s)
├── [4/7] Chunking text...                      ✓ (0.5s)
│   └── Created 45 chunks
├── [5/7] Building lexical index...             ✓ (1.1s)
├── [6/7] Building text embeddings...           ✓ (12.4s)
└── [7/7] Building caption embeddings...        ✓ (3.8s)

Extraction complete: extraction/document/
```

### Step 3: Explore the Results

Check what was extracted:

```bash
ls -R extraction/document/
```

You should see:
```
extraction/document/
├── text.txt                      # Full extracted text
├── figures_metadata.parquet       # Image metadata
├── images/                        # Extracted images
│   ├── page_0_image_1.png
│   └── ...
├── text_chunks/                   # Text chunks
│   ├── chunk_0001.txt
│   └── ...
├── lucene_index/                  # Whoosh index
├── faiss_index/                   # Text embeddings
└── faiss_index_images/            # Caption embeddings
```

### Step 4: Try Searching

#### Command-Line Search

```bash
# Lexical search
python scripts/search_document.py "document" "neural networks" --limit 5

# Vector search
python scripts/vector_search.py "document" "deep learning architecture"
```

#### Python API

```python
from session.session_registry import default_registry

# Set active document
registry = default_registry
registry.ensure("document")  # Use folder name from extraction/

# Lexical search
results = registry.search_lexical(
    "document", 
    "neural networks",
    limit=5
)
print(f"Found {len(results)} results")

# Vector search
results = registry.search_vector(
    "document",
    "attention mechanism",
    k=5
)
for r in results:
    print(f"Score: {r['score']:.2f}")
    print(f"Text: {r['text'][:100]}...")
```

### Step 5: Chat with Your Documents

Start the interactive agent:

```bash
python scripts/agent_chat.py
```

**Example conversation:**

```
Agent: Hello! I'm ready to help analyze documents. Use set_active_document first.

You: set_active_document document

Agent: Active document set to: document

You: What are the main topics covered?

Agent: [Searches document, analyzes results]
Based on my analysis, the document covers:
1. Neural network architectures
2. Training methodologies
3. Experimental results

You: Find figures about network architecture

Agent: [Searches captions, finds images]
I found 3 figures related to network architecture:
- Figure 3: CNN architecture (page 5)
- Figure 7: ResNet diagram (page 12)
- Figure 10: Attention mechanism (page 18)

You: Analyze figure 3

Agent: [Uploads and analyzes image with Claude Vision]
Figure 3 shows a convolutional neural network with...
```

## Common Workflows

### Workflow 1: Extract and Search

```bash
# 1. Add PDF
cp research_paper.pdf pdf_files/

# 2. Extract
python main.py

# 3. Search
python scripts/search_document.py "research_paper" "methodology"
```

### Workflow 2: Image Analysis

```python
from session.session_registry import default_registry

# Setup
registry = default_registry
doc_id = "research_paper"
registry.ensure(doc_id)

# Find images
images = registry.search_image_captions(doc_id, "neural network diagram", k=3)

# Get image IDs
image_ids = [img['image_id'] for img in images]

# Analyze images
result = registry.upload_images_to_anthropic(doc_id, image_ids[:2])
print(f"Uploaded {result['uploaded_count']} images")
print(f"Cached {result['cached_count']} images")
```

### Workflow 3: Agent-Powered Analysis

```python
from agents.agent import make_document_agent

agent = make_document_agent()

# Multi-turn conversation
messages = [
    ("user", "Set active document to research_paper"),
]
response = agent.invoke({"messages": messages})

messages.append(("ai", response))
messages.append(("user", "What methods did they use?"))
response = agent.invoke({"messages": messages})
```

## Configuration Options

Edit `analyzer/config.py` or use environment variables:

### Text Chunking
```python
EXTRACTION_CHUNK_SIZE = 2000      # Characters per chunk
EXTRACTION_CHUNK_OVERLAP = 300    # Overlap between chunks
```

### Vector Search
```python
FAISS_EMBEDDING_MODEL = "google/embeddinggemma-300m"
FAISS_DISTANCE_STRATEGY = "MAX_INNER_PRODUCT"
FAISS_SEARCH_K = 5  # Default results
```

### Image Analysis
```python
ANTHROPIC_FILE_TTL_HOURS = 12   # Cache duration
IMAGE_UPLOAD_LIMIT = 20          # Max images per request
```

### Directories
```python
PDF_DIR = "pdf_files"
EXTRACTION_DIR = "extraction"
```

## Troubleshooting

### Issue: "No module named..."

**Solution:**
```bash
# Ensure virtual environment is activated
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue: "No text extracted from PDF"

**Possible causes:**
1. PDF is scanned/image-based (needs OCR)
2. PDF is encrypted
3. PDF uses non-standard encoding

**Check:**
```bash
# Test with a known-good PDF
python -c "import pymupdf; doc = pymupdf.open('pdf_files/test.pdf'); print(doc[0].get_text())"
```

### Issue: "Anthropic API error"

**Solutions:**
1. Check API key in `.env`
2. Verify API credits at console.anthropic.com
3. Check internet connectivity

### Issue: "FAISS index not loading"

**Solution:**
```bash
# Rebuild the index
rm -rf extraction/*/faiss_index*
python main.py
```

### Issue: "Out of memory during extraction"

**Solutions:**
1. Process PDFs one at a time
2. Reduce `EXTRACTION_CHUNK_SIZE`
3. Close other applications
4. Increase system swap space

## Next Steps

Now that you're set up:

1. **[Read the Architecture docs](./architecture.md)** - Understand how it works
2. **[Explore Agent Tools](./agent_tools.md)** - Learn all available tools
3. **[Review Image Analysis](./image_analysis.md)** - Master vision capabilities
4. **[Check API Reference](./api_reference.md)** - Dive into the code

## Getting Help

- **Documentation**: Check other `.md` files in `documentation/`
- **Examples**: Review `scripts/` for working examples
- **Issues**: [GitHub Issues](your-repo-url/issues)

## Tips for Success

1. **Start Small**: Test with 1-2 small PDFs first
2. **Check Logs**: Enable verbose logging for debugging
3. **Monitor Memory**: Large PDFs can use significant RAM
4. **Use Caching**: Image cache saves time and API costs
5. **Experiment**: Try different search strategies (lexical, vector, hybrid)

## What's Next?

After getting comfortable with basics:

- **Batch Processing**: Process multiple PDFs efficiently
- **Custom Tools**: Add domain-specific analysis tools
- **API Integration**: Build web services on top of Doc-Bot
- **Advanced Queries**: Combine multiple search modes
- **Production Deployment**: Scale for production workloads

Happy document processing! 🚀
