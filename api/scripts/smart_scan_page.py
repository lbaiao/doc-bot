#!/usr/bin/env python3
import argparse
import os
import sys
import logging
import pymupdf

# Add api directory to path so we can import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from preprocessing.smart_extractor import SmartPageExtractor
from analyzer.config import default_config

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Run Smart Scan (Vision LLM) on a PDF page.")
    parser.add_argument("pdf_path", help="Path to the PDF file")
    parser.add_argument("--page", type=int, required=True, help="Page number (1-based)")
    args = parser.parse_args()

    if not os.path.exists(args.pdf_path):
        logger.error(f"File not found: {args.pdf_path}")
        sys.exit(1)

    # Check for API key
    if not default_config.ANTHROPIC_API_KEY:
        logger.error("ANTHROPIC_API_KEY environment variable not set.")
        sys.exit(1)
    
    # Set env var for LangChain if not already set (it might be loaded from .env by pydantic)
    if not os.environ.get("ANTHROPIC_API_KEY"):
        os.environ["ANTHROPIC_API_KEY"] = default_config.ANTHROPIC_API_KEY

    try:
        doc = pymupdf.open(args.pdf_path)
        page_idx = args.page - 1
        
        if page_idx < 0 or page_idx >= len(doc):
            logger.error(f"Page {args.page} out of range (1-{len(doc)})")
            sys.exit(1)
            
        page = doc[page_idx]
        
        logger.info(f"Initializing SmartPageExtractor for {args.pdf_path} page {args.page}...")
        extractor = SmartPageExtractor(model_name=default_config.VISION_LLM_MODEL)
        
        logger.info("Analyzing page with Claude...")
        result = extractor.extract_from_page(page)
        
        print("\nSmart Scan Results:")
        print("=" * 60)
        
        if not result.figures:
            print("No figures found.")
        
        for i, fig in enumerate(result.figures, 1):
            print(f"\nItem {i}: {fig.type.upper()} - {fig.label}")
            print("-" * 30)
            print(f"Caption:     {fig.caption}")
            print(f"Description: {fig.description}")
            print(f"BBox (0-1000): {fig.bbox_2d}")
            print("=" * 60)

    except Exception as e:
        logger.error(f"Smart Scan failed: {e}", exc_info=True)
        sys.exit(1)
    finally:
        if 'doc' in locals():
            doc.close()

if __name__ == "__main__":
    main()
