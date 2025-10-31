# Doc-Bot Copilot Instructions

## Project Overview
This is a PDF document processing system that extracts text, bitmap images, and vector graphics from PDFs. The system is structured around PyMuPDF for PDF processing and uses a configuration-driven approach with pydantic.

## Architecture & Data Flow
- **Entry Point**: `main.py` orchestrates the extraction pipeline for all PDFs in the configured directory
- **Extraction Pipeline**: `PdfExtractor` (context manager) → extracts text, bitmap images, vector graphics
- **Configuration**: Centralized in `analyzer/config.py` using pydantic-settings with `.env` support
- **Output Structure**: Each PDF gets a dedicated extraction folder with structured subdirectories

## Key Patterns & Conventions

### Configuration Pattern
- Uses `pydantic-settings` with case-insensitive matching
- Default values defined in class, overridable via `.env` file
- Single global instance: `default_config = Config()`
- Access pattern: `from analyzer.config import default_config`

### Context Manager Usage
```python
with PdfExtractor(file_path) as extractor:
    extractor.extract_all()
```

### Output Organization
```
extraction/{pdf_name}/
  ├── text.txt
  ├── images/           # bitmap images with caption detection
  ├── vector_graphics/  # SVG/PNG exports of vector figures
  └── figures_metadata.parquet  # pandas DataFrame with image metadata
```

### Logging Convention
- Each module gets its own logger: `logger = logging.getLogger(__name__)`
- INFO level for high-level operations, DEBUG for detailed operations
- Structured messages with context (file names, page numbers, counts)

### Caption Detection Logic
- Searches 100px below and 50px above image bounding boxes
- Looks for keywords: "figure", "fig.", "fig", "table", "image", "photo", "chart", "diagram"
- Returns tuple: `(has_caption: bool, caption_text: str)`

### Vector Graphics Extraction
- Uses complex heuristics: minimum segments (40+), area fraction (0.8%), stroke analysis
- Configurable via `VectorFigureExtractor` constructor parameters
- Merges overlapping regions using IoU threshold
- Scoring system prioritizes figures with captions

## Environment Setup & Dependencies
- **Python Environment**: Uses `venv/` (gitignored)
- **Key Dependencies**: PyMuPDF, pandas, pyarrow, pydantic-settings
- **Data Storage**: Parquet format for structured metadata
- **PDF Input**: Place PDFs in `pdf_files/` directory (gitignored)

## Development Workflows

### Adding New Extractors
1. Create new module in `preprocessing/`
2. Follow context manager pattern if stateful
3. Add configuration options to `analyzer/config.py`
4. Integrate into `PdfExtractor.extract_all()`

### Testing Extraction Results
```bash
# View parquet metadata
python scripts/print_parquet.py extraction/{pdf_name}/figures_metadata.parquet -n 5 --stats
```

### Configuration Changes
- Add new settings to `Config` class with defaults
- Use environment variables for deployment-specific values
- Access via `default_config.SETTING_NAME`

## Common Issues & Solutions
- **Memory**: PyMuPDF pixmaps must be explicitly set to `None` after use
- **Image Formats**: CMYK images auto-converted to RGB before saving
- **Path Handling**: All paths built using `os.path.join()` for cross-platform compatibility
- **Error Recovery**: Each page/image processed independently with logging

## File Naming Conventions
- Images: `page_{page_index}_image_{image_index}.png`
- Vector figures: `p{page_index:04d}_y{int(rect.y0)}_x{int(rect.x0)}.png`
- Extraction folders: Based on PDF filename without extension