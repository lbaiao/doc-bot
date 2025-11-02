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

logger = logging.getLogger(__name__)

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

    def extract_image_caption(self, page: pymupdf.Page, image_rect: pymupdf.Rect) -> Tuple[bool, str]:
        """
        Search for caption text below (or above) an image.
        Returns (has_caption, caption_text)
        """
        # Define search zones
        search_below = pymupdf.Rect(
            image_rect.x0, 
            image_rect.y1,  # Start at bottom of image
            image_rect.x1, 
            image_rect.y1 + 100  # Search 100 pixels below
        )
        
        search_above = pymupdf.Rect(
            image_rect.x0,
            image_rect.y0 - 50,  # 50 pixels above
            image_rect.x1,
            image_rect.y0
        )
        
        # Get words in both zones
        all_words = page.get_text("words")
        if not isinstance(all_words, list):
            return False, ""
            
        words_below = [w for w in all_words 
                       if isinstance(w, (list, tuple)) and len(w) >= 5 and 
                       search_below.intersects(pymupdf.Rect(w[:4]))]
        words_above = [w for w in all_words 
                       if isinstance(w, (list, tuple)) and len(w) >= 5 and 
                       search_above.intersects(pymupdf.Rect(w[:4]))]
        
        # Combine text
        text_below = " ".join(w[4] for w in words_below if len(w) > 4).strip()
        text_above = " ".join(w[4] for w in words_above if len(w) > 4).strip()
        
        # Check for caption keywords
        caption_keywords = ("figure", "fig.", "fig", "table", "image", "photo", "chart", "diagram")
        
        text_below_lower = text_below.lower()
        text_above_lower = text_above.lower()
        
        has_caption_below = any(kw in text_below_lower for kw in caption_keywords)
        has_caption_above = any(kw in text_above_lower for kw in caption_keywords)
        
        if has_caption_below:
            return True, text_below
        elif has_caption_above:
            return True, text_above
        elif text_below:  # Return below text if exists, even without keywords
            return False, text_below
        
        return False, ""

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
            image_list = page.get_images()

            # print the number of images found on the page
            if image_list:
                logger.debug(f"Found {len(image_list)} images on page {page_index}")
                print(f"Found {len(image_list)} images on page {page_index}")
            else:
                logger.debug(f"No images found on page {page_index}")
                print("No images found on page", page_index)

            for image_index, img in enumerate(image_list, start=1): # enumerate the image list
                xref = img[0] # get the XREF of the image
                
                # Get image bounding box on page
                image_rects = page.get_image_rects(xref)
                
                pix = pymupdf.Pixmap(doc, xref) # create a Pixmap

                if pix.n - pix.alpha > 3: # CMYK: convert to RGB first
                    logger.debug(f"Converting CMYK image to RGB on page {page_index}")
                    pix = pymupdf.Pixmap(pymupdf.csRGB, pix)

                filename = f"page_{page_index}_image_{image_index}.png"
                os.makedirs(self.images_dir, exist_ok=True)
                output_path = os.path.join(self.images_dir, filename)
                pix.save(output_path) # save the image as png
                
                # Extract caption if image has bounding box
                caption = ""
                has_caption = False
                if image_rects:
                    rect = image_rects[0]  # Use first occurrence
                    has_caption, caption = self.extract_image_caption(page, rect)
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

    def extract_all(self):
        self.extract_text()
        self.extract_bitmap_images()
        self.extract_vector_graphics()
        self.extract_text_chunks()
        # Build Lucene-style index for this PDF's extracted artifacts
        self.extract_lucene_index()

    def close(self):
        if hasattr(self, 'doc') and self.doc:
            self.doc.close()
            logger.info(f"Closed document: {self.file_name}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return False  # Don't suppress exceptions
