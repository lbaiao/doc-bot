import pymupdf
import os
import logging
from analyzer.config import default_config
from preprocessing.vector_figure_extractor import VectorFigureExtractor

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
        
        logger.info(f"Initialized PdfExtractor for file: {self.file_name}")
        logger.debug(f"Output directory: {self.output_dir}")

    def extract_text(self):
        logger.info(f"Starting text extraction from {self.file_name}")
        doc = self.doc
        out = open(self.text_path, "wb") # create a text output
        
        page_count = 0
        for page in doc: # iterate the document pages
            text = page.get_text().encode("utf8") # get plain text (is in UTF-8)
            out.write(text) # write text of page
            out.write(bytes((12,))) # write page delimiter (form feed 0x0C)
            page_count += 1
            logger.info(f"Extracted text from page {page_count + 1} / {len(doc)}")
        out.close()
        
        logger.info(f"Text extraction complete: {page_count} pages extracted to {self.text_path}")

    def extract_bitmap_images(self):
        logger.info(f"Starting bitmap image extraction from {self.file_name}")
        doc = self.doc
        
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
                pix = pymupdf.Pixmap(doc, xref) # create a Pixmap

                if pix.n - pix.alpha > 3: # CMYK: convert to RGB first
                    logger.debug(f"Converting CMYK image to RGB on page {page_index}")
                    pix = pymupdf.Pixmap(pymupdf.csRGB, pix)

                filename = f"page_{page_index}_image_{image_index}.png"
                os.makedirs(self.images_dir, exist_ok=True)
                output_path = os.path.join(self.images_dir, filename)
                pix.save(output_path) # save the image as png
                logger.debug(f"Saved image: {output_path}")
                pix = None
                total_images += 1
                logger.info(f"Extracted image {image_index} on page {page_index}")

        
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

    def extract_all(self):
        self.extract_text()
        self.extract_bitmap_images()
        self.extract_vector_graphics()

    def close(self):
        if hasattr(self, 'doc') and self.doc:
            self.doc.close()
            logger.info(f"Closed document: {self.file_name}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return False  # Don't suppress exceptions


