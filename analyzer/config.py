from pydantic_settings import BaseSettings
import os

class Config(BaseSettings):
    EXTRACTION_DIR: str = "extraction"
    EXTRACTION_TEXT_FILE: str = "text.txt"
    EXTRACTION_IMAGE_DIR: str = "images"
    EXTRACTION_VECTOR_GRAPHICS_DIR: str = "vector_graphics"
    EXTRACTION_FIGURES_PARQUET_FILE: str = "figures_metadata.parquet"
    EXTRACTION_LUCENE_INDEX_DIR: str = "lucene_index"
    EXTRACTION_CHUNK_SIZE: int = 500 * 4  # number of characters per text chunk (500 tokens * 4 chars/token)
    EXTRACTION_CHUNK_OVERLAP: float = EXTRACTION_CHUNK_SIZE * 0.15
    EXTRACTION_CHUNK_DIR: str = "text_chunks" 
    EXTRACTION_FAISS_DIR: str = "faiss_index"
    PDF_DIR: str = "pdf_files"
    
    # FAISS Configuration
    FAISS_EMBEDDING_MODEL: str = "google/embeddinggemma-300m"
    FAISS_DISTANCE_STRATEGY: str = "MAX_INNER_PRODUCT"  # Optimized for inner product search
    FAISS_SEARCH_K: int = 5  # Default number of results to return in searches
    ANTHROPIC_API_KEY: str = ""

    
    class Config:
        env_file = '.env'
        case_sensitive = False  # Makes matching flexible

default_config = Config()

def get_config() -> Config:
    return default_config

class FullConfigPaths:
    def __init__(self, file_name: str):
        self.EXTRACTION_DIR = os.path.join(default_config.EXTRACTION_DIR, file_name)
        self.EXTRACTION_TEXT_FILE = os.path.join(self.EXTRACTION_DIR, file_name, default_config.EXTRACTION_TEXT_FILE)
        self.EXTRACTION_DIR: str = os.path.join(self.EXTRACTION_DIR, file_name, default_config.EXTRACTION_DIR)
        self.EXTRACTION_TEXT_FILE: str = os.path.join(self.EXTRACTION_DIR, file_name, default_config.EXTRACTION_TEXT_FILE)
        self.EXTRACTION_IMAGE_DIR: str = os.path.join(self.EXTRACTION_DIR, file_name, default_config.EXTRACTION_IMAGE_DIR)
        self.EXTRACTION_VECTOR_GRAPHICS_DIR: str = os.path.join(self.EXTRACTION_DIR, file_name, default_config.EXTRACTION_VECTOR_GRAPHICS_DIR)
        self.EXTRACTION_FIGURES_PARQUET_FILE: str = os.path.join(self.EXTRACTION_DIR, file_name, default_config.EXTRACTION_FIGURES_PARQUET_FILE)
        self.EXTRACTION_LUCENE_INDEX_DIR: str = os.path.join(self.EXTRACTION_DIR, file_name, default_config.EXTRACTION_LUCENE_INDEX_DIR)
        self.EXTRACTION_CHUNK_DIR: str = os.path.join(self.EXTRACTION_DIR, file_name, default_config.EXTRACTION_CHUNK_DIR)
        self.EXTRACTION_FAISS_DIR: str = os.path.join(self.EXTRACTION_DIR, file_name, default_config.EXTRACTION_FAISS_DIR)
