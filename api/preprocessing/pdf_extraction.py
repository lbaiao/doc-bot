import pymupdf
import os
import logging
import uuid
from typing import Tuple
import pandas as pd
from analyzer.config import default_config
from analyzer.schemas import FigureImageCols as FIC, FigureImageMetadata
from preprocessing.woosh_indexer import WooshIndexer
from preprocessing.vector_figure_extractor import VectorFigureExtractor
from preprocessing.chunker import TextChunker
from analyzer.faiss_wrapper import FaissWrapper

logger = logging.getLogger(__name__)

class UsedAreaTracker:
    """Tracks areas of the page that have already been assigned as captions."""
    def __init__(self):
        self.used_rects = []

    def is_used(self, rect: pymupdf.Rect, threshold: float = 0.1) -> bool:
        """Check if rect overlaps significantly with any used rect."""
        for used in self.used_rects:
            # Calculate intersection
            intersect = rect & used
            if intersect.is_empty:
                continue
            
            # Check overlap area relative to the candidate rect
            overlap_area = intersect.width * intersect.height
            rect_area = rect.width * rect.height
            
            if rect_area > 0 and (overlap_area / rect_area) > threshold:
                return True
        return False

    def mark_used(self, rect: pymupdf.Rect):
        """Mark a rect as used."""
        self.used_rects.append(rect)


class PdfExtractor:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.file_name = os.path.basename(file_path).split('.')[0]
        self.output_dir = os.path.join(default_config.EXTRACTION_DIR, self.file_name)
        os.makedirs(self.output_dir, exist_ok=True)
        self.text_path = os.path.join(self.output_dir, default_config.EXTRACTION_TEXT_FILE)
        self.images_dir = os.path.join(self.output_dir, default_config.EXTRACTION_IMAGE_DIR)
        self.vector_graphics_dir = os.path.join(self.output_dir, default_config.EXTRACTION_VECTOR_GRAPHICS_DIR)
        self.doc = pymupdf.open(file_path)
        self.parquet_path = os.path.join(self.output_dir, default_config.EXTRACTION_FIGURES_PARQUET_FILE)
        
        logger.info(f"Initialized PdfExtractor for file: {self.file_name}")
        logger.debug(f"Output directory: {self.output_dir}")

    def extract_image_caption(self, page: pymupdf.Page, image_rect: pymupdf.Rect, tracker: UsedAreaTracker) -> Tuple[bool, str]:
        """
        Search for caption text below (or above) an image using block analysis.
        Returns (has_caption, caption_text)
        """
        # 1. Define search zones
        # Look 150px below (typical for figures) and 80px above (typical for tables)
        search_below = pymupdf.Rect(
            image_rect.x0 - 20, # Allow slight margin width-wise
            image_rect.y1, 
            image_rect.x1 + 20, 
            image_rect.y1 + 150
        )
        
        search_above = pymupdf.Rect(
            image_rect.x0 - 20,
            image_rect.y0 - 80,
            image_rect.x1 + 20,
            image_rect.y0
        )
        
        # 2. Get all text blocks on page
        # blocks are (x0, y0, x1, y1, "text", block_no, block_type)
        blocks = page.get_text("blocks")
        
        candidates = []
        
        caption_starts = ("figure", "fig.", "fig ", "table", "image", "photo", "chart", "diagram", "scheme")
        
        for b in blocks:
            b_rect = pymupdf.Rect(b[:4])
            text = b[4].strip()
            
            if not text or len(text) < 3:
                continue
                
            # Skip if already used
            if tracker.is_used(b_rect):
                continue
                
            # Check if block is in search zones
            is_below = search_below.intersects(b_rect)
            is_above = search_above.intersects(b_rect)
            
            if not (is_below or is_above):
                continue
                
            # Calculate distance to image
            if is_below:
                dist = b_rect.y0 - image_rect.y1
            else:
                dist = image_rect.y0 - b_rect.y1
                
            # Heuristics scoring
            score = 0
            text_lower = text.lower()
            
            # 1. Keyword bonus (strong indicator)
            if text_lower.startswith(caption_starts):
                score += 50
            elif any(kw in text_lower[:30] for kw in caption_starts): # Keyword early in text
                score += 20
                
            # 2. Distance penalty (closer is better)
            score -= abs(dist) * 0.2
            
            # 3. Alignment bonus (center alignment often used for captions)
            img_center = (image_rect.x0 + image_rect.x1) / 2
            block_center = (b_rect.x0 + b_rect.x1) / 2
            align_diff = abs(img_center - block_center)
            if align_diff < 50:
                score += 10
            
            candidates.append({
                "text": text,
                "rect": b_rect,
                "score": score,
                "is_keyword_start": text_lower.startswith(caption_starts)
            })
            
        if not candidates:
            return False, ""
            
        # Sort by score descending
        candidates.sort(key=lambda x: x["score"], reverse=True)
        best = candidates[0]
        
        # Threshold: If no keyword, require very close proximity or high confidence
        if not best["is_keyword_start"] and best["score"] < 0:
            return False, ""
            
        # Mark as used
        tracker.mark_used(best["rect"])
        
        return True, best["text"]

    def extract_text(self):
        logger.info(f"Starting text extraction from {self.file_name}")
        doc = self.doc
        out = open(self.text_path, "wb") # create a text output
        
        page_count = 0
        for page in doc: # iterate the document pages
            # get plain text (ensure str type for linters, then encode to UTF-8 bytes)
            text = str(page.get_text()).encode("utf8")
            out.write(text) # write text of page
            out.write(bytes((12,))) # write page delimiter (form feed 0x0C)
            page_count += 1
            logger.info(f"Extracted text from page {page_count + 1} / {len(doc)}")
        out.close()
        
        logger.info(f"Text extraction complete: {page_count} pages extracted to {self.text_path}")

    def extract_bitmap_images(self):
        logger.info(f"Starting bitmap image extraction from {self.file_name}")
        doc = self.doc
        
        # Store image metadata for parquet file
        image_data = []
        
        total_images = 0
        for page_index in range(len(doc)): # iterate over pdf pages
            page = doc[page_index] # get the page
            # Track used areas for captions on this page
            tracker = UsedAreaTracker()

            # Sort images top-to-bottom to ensure logical processing order
            # image_list is [(xref, smask, width, height, bpc, colorspace, alt.colorspace, name, filter, referencer), ...]
            # We need rects to sort.
            
            # First pass: gather all image rects and info
            image_list = page.get_images()
            page_images = []
            for img in image_list:
                xref = img[0]
                rects = page.get_image_rects(xref)
                if not rects:
                    continue
                # Use first rect for sorting/processing (simplification)
                rect = rects[0]
                page_images.append((rect.y0, rect.x0, img, rect))
            
            # Sort by vertical position (y0)
            page_images.sort(key=lambda x: (x[0], x[1]))
            
            for image_index, (_, _, img, rect) in enumerate(page_images, start=1):
                xref = img[0]
                
                pix = pymupdf.Pixmap(doc, xref) # create a Pixmap

                if pix.n - pix.alpha > 3: # CMYK: convert to RGB first
                    logger.debug(f"Converting CMYK image to RGB on page {page_index}")
                    pix = pymupdf.Pixmap(pymupdf.csRGB, pix)

                filename = f"page_{page_index}_image_{image_index}.png"
                os.makedirs(self.images_dir, exist_ok=True)
                output_path = os.path.join(self.images_dir, filename)
                pix.save(output_path) # save the image as png
                
                # Extract caption using tracker
                has_caption, caption = self.extract_image_caption(page, rect, tracker)

                if has_caption:
                    logger.info(f"Found caption: {caption[:100]}")
                elif caption:
                    logger.debug(f"Found text near image: {caption[:50]}")
                
                # Store metadata (use canonical schema/columns)
                record = FigureImageMetadata(
                    id=str(uuid.uuid4()),
                    page_index=page_index,
                    image_index=image_index,
                    image_path=output_path,
                    has_caption=has_caption,
                    caption=caption,
                    width=pix.width,
                    height=pix.height,
                )
                image_data.append(record.to_record())
                
                logger.debug(f"Saved image: {output_path}")
                pix = None
                total_images += 1
                logger.info(f"Extracted image {image_index} on page {page_index}")

        # Save metadata to parquet file
        if image_data:
            df = pd.DataFrame(image_data)
            df.to_parquet(self.parquet_path, index=False)
            logger.info(f"Saved image metadata to {self.parquet_path}")
        
        logger.info(f"Bitmap image extraction complete: {total_images} images extracted to {self.images_dir}")

    def extract_vector_graphics(self):
        logger.info(f"Starting vector graphics extraction from {self.file_name}")
        doc = self.doc

        extractor = VectorFigureExtractor(
            min_segments=40,          # relax if you miss sparse diagrams
            area_frac=0.008,          # 0.8% of page area minimum
            max_words_inside=14,
            caption_tokens=("figure", "fig.", "chart", "diagram", "schematic"),
        )

        figs = extractor.extract(
            doc=doc,
            doc_path=self.file_path,
            dpi=300,
            out_dir=self.vector_graphics_dir,
            save_png=True,
        )
        
        logger.info(f"Vector graphics extraction complete. {len(figs)} figures extracted to {self.vector_graphics_dir}")

    def extract_text_chunks(self):
        logger.info(f"Starting text chunking for {self.file_name}")
        chunker = TextChunker()
        paths = chunker.chunk_file(self.text_path, self.output_dir)
        logger.info(f"Text chunking complete: {len(paths)} chunks saved to {default_config.EXTRACTION_CHUNK_DIR}")

    def extract_lucene_index(self):
        logger.info(f"Starting Lucene index extraction from {self.file_name}")
        # Build Lucene-style index for this PDF's extracted artifacts
        try:
            indexer = WooshIndexer(self.output_dir, pdf_name=self.file_name)
            indexer.build()
            logger.info(f"Lucene index built successfully for {self.file_name}")
        except Exception as e:
            logger.error(f"Failed to build Lucene index for {self.file_name}: {e}")

    def extract_embeddings(self):
        logger.info(f"Starting FAISS embedding extraction from {self.file_name}")
        try:
            # Initialize FAISS indexer
            faiss_indexer = FaissWrapper()
            
            # Create and save FAISS index for this PDF's text chunks
            success = faiss_indexer.index_extraction_directory(self.output_dir)
            
            if success:
                # Get index information for logging
                index_info = faiss_indexer.get_index_info()
                logger.info(f"FAISS text index created successfully for {self.file_name}. "
                           f"Documents: {index_info.get('total_documents', 'unknown')}, "
                           f"Embedding dimension: {index_info.get('embedding_dimension', 'unknown')}")
            else:
                logger.error(f"Failed to create FAISS text index for {self.file_name}")
            
            # Create and save FAISS index for image captions
            logger.info(f"Starting FAISS image captions index creation for {self.file_name}")
            captions_indexer = FaissWrapper()
            captions_success = captions_indexer.index_image_captions(self.output_dir)
            
            if captions_success:
                # Get index information for logging
                captions_info = captions_indexer.get_index_info()
                logger.info(f"FAISS image captions index created successfully for {self.file_name}. "
                           f"Captions: {captions_info.get('total_documents', 'unknown')}, "
                           f"Embedding dimension: {captions_info.get('embedding_dimension', 'unknown')}")
            else:
                logger.warning(f"No image captions to index or failed to create index for {self.file_name}")
                
        except Exception as e:
            logger.error(f"FAISS embedding extraction failed for {self.file_name}: {e}")
        
        logger.info(f"FAISS embedding extraction complete for {self.file_name}")

    def extract_all(self):
        self.extract_text()
        self.extract_bitmap_images()
        self.extract_vector_graphics()
        self.extract_text_chunks()
        # Build Lucene-style index for this PDF's extracted artifacts
        self.extract_lucene_index()
        # Build FAISS vector embeddings index for semantic search
        self.extract_embeddings()

    def close(self):
        if hasattr(self, 'doc') and self.doc:
            self.doc.close()
            logger.info(f"Closed document: {self.file_name}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return False  # Don't suppress exceptions
