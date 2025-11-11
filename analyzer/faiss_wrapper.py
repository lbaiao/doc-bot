import os
import logging
from typing import List, Tuple, Optional

import pandas as pd
from langchain_core.documents.base import Document
from langchain_community.vectorstores import FAISS
from langchain_huggingface.embeddings import HuggingFaceEmbeddings

from analyzer.config import default_config

logger = logging.getLogger(__name__)


class FaissWrapper:
    """
    FAISS-based vector indexer for text chunks using LangChain and HuggingFace embeddings.
    
    - Loads text chunks from extraction/<pdf_name>/<EXTRACTION_CHUNK_DIR>/
    - Uses Google Gemma embedding model via HuggingFace
    - Saves/loads FAISS index to/from extraction/<pdf_name>/<EXTRACTION_FAISS_DIR>/
    - Follows the project's configuration-driven approach
    """

    def __init__(
        self,
        embedding_model: str | None = None,
        distance_strategy: str | None = None,
        search_k: int | None = None
    ):
        """Initialize the FAISS indexer with configurable parameters."""
        self.embedding_model = embedding_model or default_config.FAISS_EMBEDDING_MODEL
        self.distance_strategy = distance_strategy or default_config.FAISS_DISTANCE_STRATEGY
        self.search_k = search_k or default_config.FAISS_SEARCH_K
        
        # Initialize embeddings with query/document prompts as specified in the model config
        logger.info(f"FaissIndexer: initializing with model {self.embedding_model}")
        self.embeddings = HuggingFaceEmbeddings(
            model_name=self.embedding_model,
            query_encode_kwargs={"prompt_name": "query"},
            encode_kwargs={"prompt_name": "document"}
        )
        
        self.vector_store: Optional[FAISS] = None

    def load_text_chunks(self, extraction_dir: str) -> List[Document]:
        """
        Load all text chunks from extraction/<pdf_name>/<EXTRACTION_CHUNK_DIR>/.
        
        Returns:
            List of LangChain Document objects with content and metadata
        """
        chunks_dir = os.path.join(extraction_dir, default_config.EXTRACTION_CHUNK_DIR)
        
        if not os.path.exists(chunks_dir):
            logger.warning(f"FaissIndexer: chunks directory does not exist: {chunks_dir}")
            return []
        
        documents = []
        chunk_files = []
        
        # Get all chunk files and sort them to maintain order
        for filename in os.listdir(chunks_dir):
            if filename.endswith('.txt') and filename.startswith('chunk_'):
                chunk_files.append(filename)
        
        chunk_files.sort()  # Ensure consistent ordering
        
        for filename in chunk_files:
            chunk_path = os.path.join(chunks_dir, filename)
            try:
                with open(chunk_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                
                if content:  # Only add non-empty chunks
                    # Extract chunk number from filename for metadata
                    chunk_num = filename.replace('chunk_', '').replace('.txt', '')
                    
                    doc = Document(
                        page_content=content,
                        metadata={
                            "source": chunk_path,
                            "chunk_number": chunk_num,
                            "extraction_dir": extraction_dir,
                            "filename": filename
                        }
                    )
                    documents.append(doc)
            except Exception as e:
                logger.warning(f"FaissIndexer: failed to read chunk {chunk_path}: {e}")
                continue
        
        logger.info(f"FaissIndexer: loaded {len(documents)} text chunks from {chunks_dir}")
        return documents

    def create_index(self, extraction_dir: str) -> bool:
        """
        Create FAISS index from text chunks in the specified extraction directory.
        
        Args:
            extraction_dir: Path to the extraction directory containing text chunks
            
        Returns:
            True if index was created successfully, False otherwise
        """
        try:
            documents = self.load_text_chunks(extraction_dir)
            
            if not documents:
                logger.warning(f"FaissIndexer: no documents found to index in {extraction_dir}")
                return False
            
            logger.info(f"FaissIndexer: creating FAISS index for {len(documents)} documents")
            
            # Create FAISS vector store with the specified distance strategy
            self.vector_store = FAISS.from_documents(
                documents, 
                self.embeddings, 
                distance_strategy=self.distance_strategy
            )
            
            logger.info(f"FaissIndexer: successfully created FAISS index")
            return True
            
        except Exception as e:
            logger.error(f"FaissIndexer: failed to create index: {e}")
            return False

    def save_index(self, extraction_dir: str) -> bool:
        """
        Save the FAISS index to disk.
        
        Args:
            extraction_dir: Path to the extraction directory where index will be saved
            
        Returns:
            True if index was saved successfully, False otherwise
        """
        if not self.vector_store:
            logger.warning("FaissIndexer: no index to save")
            return False
        
        try:
            index_dir = os.path.join(extraction_dir, default_config.EXTRACTION_FAISS_DIR)
            os.makedirs(index_dir, exist_ok=True)
            
            # FAISS save_local expects the directory path
            self.vector_store.save_local(index_dir)
            
            logger.info(f"FaissIndexer: saved index to {index_dir}")
            return True
            
        except Exception as e:
            logger.error(f"FaissIndexer: failed to save index: {e}")
            return False

    def load_index(self, extraction_dir: str) -> bool:
        """
        Load an existing FAISS index from disk.
        
        Args:
            extraction_dir: Path to the extraction directory containing the saved index
            
        Returns:
            True if index was loaded successfully, False otherwise
        """
        try:
            index_dir = os.path.join(extraction_dir, default_config.EXTRACTION_FAISS_DIR)
            
            if not os.path.exists(index_dir):
                logger.warning(f"FaissIndexer: index directory does not exist: {index_dir}")
                return False
            
            # Load the FAISS index with the same embeddings
            self.vector_store = FAISS.load_local(
                index_dir, 
                self.embeddings, 
                allow_dangerous_deserialization=True  # Required for loading FAISS indexes
            )
            
            logger.info(f"FaissIndexer: loaded index from {index_dir}")
            return True
            
        except Exception as e:
            logger.error(f"FaissIndexer: failed to load index: {e}")
            return False

    def search(self, query: str, k: int | None = None) -> List[Tuple[Document, float]]:
        """
        Search the FAISS index for similar documents.
        
        Args:
            query: The search query string
            k: Number of results to return (uses default from config if not specified)
            
        Returns:
            List of tuples containing (Document, similarity_score)
        """
        if not self.vector_store:
            logger.warning("FaissIndexer: no index loaded for search")
            return []
        
        search_k = k or self.search_k
        
        try:
            results = self.vector_store.similarity_search_with_score(query, k=search_k)
            logger.info(f"FaissIndexer: found {len(results)} results for query")
            return results
            
        except Exception as e:
            logger.error(f"FaissIndexer: search failed: {e}")
            return []

    def index_extraction_directory(self, extraction_dir: str, force_rebuild: bool = False) -> bool:
        """
        Complete workflow: create and save FAISS index for an extraction directory.
        
        Args:
            extraction_dir: Path to the extraction directory
            force_rebuild: If True, rebuild even if index already exists
            
        Returns:
            True if indexing was successful, False otherwise
        """
        index_dir = os.path.join(extraction_dir, default_config.EXTRACTION_FAISS_DIR)
        
        # Check if index already exists
        if os.path.exists(index_dir) and not force_rebuild:
            logger.info(f"FaissIndexer: index already exists at {index_dir}, loading existing index")
            return self.load_index(extraction_dir)
        
        # Create new index
        if self.create_index(extraction_dir):
            return self.save_index(extraction_dir)
        else:
            return False

    def get_index_info(self) -> dict:
        """
        Get information about the current index.
        
        Returns:
            Dictionary with index information
        """
        if not self.vector_store:
            return {"status": "no_index_loaded"}
        
        try:
            # Get the underlying FAISS index
            index = self.vector_store.index
            return {
                "status": "loaded",
                "total_documents": index.ntotal,
                "embedding_dimension": index.d,
                "distance_strategy": self.distance_strategy,
                "embedding_model": self.embedding_model
            }
        except Exception as e:
            logger.error(f"FaissIndexer: failed to get index info: {e}")
            return {"status": "error", "error": str(e)}

    def load_image_captions(self, extraction_dir: str) -> List[Document]:
        """
        Load image captions from the figures_metadata.parquet file.
        
        Returns:
            List of LangChain Document objects with caption text and image metadata
        """
        parquet_path = os.path.join(extraction_dir, default_config.EXTRACTION_FIGURES_PARQUET_FILE)
        
        if not os.path.exists(parquet_path):
            logger.warning(f"FaissIndexer: parquet file does not exist: {parquet_path}")
            return []
        
        try:
            # Read the parquet file
            df = pd.read_parquet(parquet_path)
            
            # Filter for images with non-empty captions
            df_with_captions = df[df['caption'].notna() & (df['caption'].str.strip() != '')]
            
            documents = []
            for _, row in df_with_captions.iterrows():
                # Create document with caption as content
                doc = Document(
                    page_content=row['caption'],
                    metadata={
                        "image_id": row['id'],
                        "image_path": row['image_path'],
                        "page_index": int(row['page_index']),
                        "image_index": int(row['image_index']),
                        "has_caption": bool(row['has_caption']),
                        "width": int(row['width']),
                        "height": int(row['height']),
                        "extraction_dir": extraction_dir,
                        "source": "image_caption"
                    }
                )
                documents.append(doc)
            
            logger.info(f"FaissIndexer: loaded {len(documents)} image captions from {parquet_path}")
            return documents
            
        except Exception as e:
            logger.error(f"FaissIndexer: failed to read parquet file {parquet_path}: {e}")
            return []

    def create_image_captions_index(self, extraction_dir: str) -> bool:
        """
        Create FAISS index from image captions in the specified extraction directory.
        
        Args:
            extraction_dir: Path to the extraction directory containing figures_metadata.parquet
            
        Returns:
            True if index was created successfully, False otherwise
        """
        try:
            documents = self.load_image_captions(extraction_dir)
            
            if not documents:
                logger.warning(f"FaissIndexer: no image captions found to index in {extraction_dir}")
                return False
            
            logger.info(f"FaissIndexer: creating FAISS index for {len(documents)} image captions")
            
            # Create FAISS vector store with the specified distance strategy
            self.vector_store = FAISS.from_documents(
                documents, 
                self.embeddings, 
                distance_strategy=self.distance_strategy
            )
            
            logger.info(f"FaissIndexer: successfully created FAISS image captions index")
            return True
            
        except Exception as e:
            logger.error(f"FaissIndexer: failed to create image captions index: {e}")
            return False

    def save_image_captions_index(self, extraction_dir: str) -> bool:
        """
        Save the FAISS image captions index to disk.
        
        Args:
            extraction_dir: Path to the extraction directory where index will be saved
            
        Returns:
            True if index was saved successfully, False otherwise
        """
        if not self.vector_store:
            logger.warning("FaissIndexer: no index to save")
            return False
        
        try:
            index_dir = os.path.join(extraction_dir, default_config.EXTRACTION_FAISS_IMAGES_DIR)
            os.makedirs(index_dir, exist_ok=True)
            
            # FAISS save_local expects the directory path
            self.vector_store.save_local(index_dir)
            
            logger.info(f"FaissIndexer: saved image captions index to {index_dir}")
            return True
            
        except Exception as e:
            logger.error(f"FaissIndexer: failed to save image captions index: {e}")
            return False

    def load_image_captions_index(self, extraction_dir: str) -> bool:
        """
        Load an existing FAISS image captions index from disk.
        
        Args:
            extraction_dir: Path to the extraction directory containing the saved index
            
        Returns:
            True if index was loaded successfully, False otherwise
        """
        try:
            index_dir = os.path.join(extraction_dir, default_config.EXTRACTION_FAISS_IMAGES_DIR)
            
            if not os.path.exists(index_dir):
                logger.warning(f"FaissIndexer: image captions index directory does not exist: {index_dir}")
                return False
            
            # Load the FAISS index with the same embeddings
            self.vector_store = FAISS.load_local(
                index_dir, 
                self.embeddings, 
                allow_dangerous_deserialization=True  # Required for loading FAISS indexes
            )
            
            logger.info(f"FaissIndexer: loaded image captions index from {index_dir}")
            return True
            
        except Exception as e:
            logger.error(f"FaissIndexer: failed to load image captions index: {e}")
            return False

    def index_image_captions(self, extraction_dir: str, force_rebuild: bool = False) -> bool:
        """
        Complete workflow: create and save FAISS index for image captions.
        
        Args:
            extraction_dir: Path to the extraction directory
            force_rebuild: If True, rebuild even if index already exists
            
        Returns:
            True if indexing was successful, False otherwise
        """
        index_dir = os.path.join(extraction_dir, default_config.EXTRACTION_FAISS_IMAGES_DIR)
        
        # Check if index already exists
        if os.path.exists(index_dir) and not force_rebuild:
            logger.info(f"FaissIndexer: image captions index already exists at {index_dir}, loading existing index")
            return self.load_image_captions_index(extraction_dir)
        
        # Create new index
        if self.create_image_captions_index(extraction_dir):
            return self.save_image_captions_index(extraction_dir)
        else:
            return False


__all__ = ["FaissWrapper"]
