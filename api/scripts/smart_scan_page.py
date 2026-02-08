#!/usr/bin/env python3
import argparse
import os
import sys
import logging
import pymupdf
import matplotlib.pyplot as plt
from PIL import Image
import io
# Add api directory to path so we can import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from preprocessing.smart_extractor import SmartPageExtractor
from preprocessing.pdf_extraction import PdfExtractor
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
        extractor = SmartPageExtractor(model_name=default_config.VISION_LLM_MODEL, api_key=default_config.ANTHROPIC_API_KEY)
        
        logger.info("Analyzing page with Claude...")
        result = extractor.extract_from_page(page)
        
        print("\nSmart Scan Results:")
        print("=" * 60)
        
        if not result.figures:
            print("No figures found.")
            return
            
        # Create a directory for debug plots
        debug_plots_dir = os.path.join(os.path.dirname(args.pdf_path), "debug_plots")
        os.makedirs(debug_plots_dir, exist_ok=True)

        for i, fig in enumerate(result.figures, 1):
            print(f"\nItem {i}: {fig.type.upper()} - {fig.label}")
            print("-" * 30)
            print(f"Caption:     {fig.caption}")
            print(f"Description: {fig.description}")
            print(f"BBox (0-1000): {fig.bbox_2d}")
            print("=" * 60)
            
            # Reuse the refactored rendering method - using 300 DPI for consistency
            pix = PdfExtractor.render_page_crop(page, fig.bbox_2d, dpi=150)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            
            plt.figure(figsize=(12, 8))
            plt.imshow(img)
            plt.title(f"{fig.label}: {fig.type}")
            plt.axis('off')
            
            plot_path = os.path.join(debug_plots_dir, f"page_{args.page}_fig_{i}.png")
            plt.savefig(plot_path)
            print(f"Plot saved to: {plot_path}")
            
            try:
                plt.show()
            except Exception:
                # If show() fails (e.g. non-interactive backend), we already saved the file
                pass
            finally:
                plt.close()

    except Exception as e:
        logger.error(f"Smart Scan failed: {e}", exc_info=True)
        sys.exit(1)
    finally:
        if 'doc' in locals():
            doc.close()

if __name__ == "__main__":
    main()
