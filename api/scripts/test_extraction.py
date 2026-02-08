#!/usr/bin/env python3
import argparse
import os
import sys
import logging
import pandas as pd

# Add api directory to path so we can import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from preprocessing.pdf_extraction import PdfExtractor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Run image and caption extraction on a local PDF.")
    parser.add_argument("pdf_path", help="Path to the PDF file")
    args = parser.parse_args()

    if not os.path.exists(args.pdf_path):
        logger.error(f"File not found: {args.pdf_path}")
        sys.exit(1)

    logger.info(f"Processing {args.pdf_path}...")

    try:
        # Initialize extractor
        extractor = PdfExtractor(args.pdf_path)
        
        # Run extraction
        logger.info("Extracting bitmap images...")
        extractor.extract_bitmap_images()
        
        logger.info("Extracting vector graphics...")
        extractor.extract_vector_graphics()
        
        # Report results
        logger.info(f"Extraction complete. Output directory: {extractor.output_dir}")
        
        # Read and print metadata
        parquet_path = extractor.parquet_path
        if os.path.exists(parquet_path):
            df = pd.read_parquet(parquet_path)
            print("\nExtracted Figures Metadata:")
            print("-" * 80)
            # Adjust columns to display based on schema
            cols = ["page_index", "image_index", "has_caption", "caption", "width", "height"]
            # Filter cols that exist in df
            cols = [c for c in cols if c in df.columns]
            
            # Print formatted table
            print(df[cols].to_string(index=False))
            print("-" * 80)
            print(f"Total figures: {len(df)}")
        else:
            logger.warning("No metadata file found (no images extracted?)")

    except Exception as e:
        logger.error(f"Extraction failed: {e}", exc_info=True)
        sys.exit(1)
    finally:
        if 'extractor' in locals():
            extractor.close()

if __name__ == "__main__":
    main()
