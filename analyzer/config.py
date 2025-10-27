from pydantic_settings import BaseSettings

class Config(BaseSettings):
    EXTRACTION_DIR: str = "extraction"
    EXTRACTION_TEXT_FILE: str = "text.txt"
    EXTRACTION_IMAGE_DIR: str = "images"
    EXTRACTION_VECTOR_GRAPHICS_DIR: str = "vector_graphics"
    PDF_DIR: str = "pdf_files"

    
    class Config:
        env_file = '.env'
        case_sensitive = False  # Makes matching flexible

default_config = Config()

def get_config() -> Config:
    return default_config
