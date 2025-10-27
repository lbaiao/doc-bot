from analyzer.config import default_config
from preprocessing.pdf_extraction import PdfExtractor
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    pdf_directory = default_config.PDF_DIR

    for pdf_file in os.listdir(pdf_directory):
        if pdf_file.endswith('.pdf'):
            file_path = os.path.join(pdf_directory, pdf_file)
            with PdfExtractor(file_path) as extractor:
                extractor.extract_all()

if __name__ == "__main__":
    main()
