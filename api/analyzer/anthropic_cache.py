"""Cache manager for Anthropic Files API uploaded images.

Manages a per-document cache of uploaded image file IDs with TTL-based expiration.
Cache is stored as JSON in the extraction directory for each document.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from dataclasses import dataclass, asdict

from analyzer.config import default_config

logger = logging.getLogger(__name__)


@dataclass
class CachedFile:
    """Represents a cached Anthropic file upload."""
    file_id: str
    uploaded_at: str  # ISO format timestamp
    image_path: str
    expires_at: str  # ISO format timestamp
    image_id: str  # UUID from parquet
    
    def is_expired(self) -> bool:
        """Check if the cached file has expired."""
        try:
            expires = datetime.fromisoformat(self.expires_at)
            return datetime.now() >= expires
        except Exception as e:
            logger.warning(f"Error checking expiry for file {self.file_id}: {e}")
            return True  # Treat as expired if we can't parse the date
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CachedFile":
        """Create from dictionary."""
        return cls(**data)


class AnthropicFileCache:
    """Manages cache of uploaded Anthropic file IDs for a document."""
    
    def __init__(self, extraction_dir: str):
        """Initialize cache for a specific document.
        
        Args:
            extraction_dir: Path to the document's extraction directory
        """
        self.extraction_dir = extraction_dir
        self.cache_path = os.path.join(
            extraction_dir, 
            default_config.ANTHROPIC_FILE_CACHE_NAME
        )
        self._cache: Dict[str, CachedFile] = {}
        self._load()
    
    def _load(self):
        """Load cache from disk."""
        if not os.path.exists(self.cache_path):
            logger.debug(f"No cache file found at {self.cache_path}")
            self._cache = {}
            return
        
        try:
            with open(self.cache_path, 'r') as f:
                data = json.load(f)
            
            # Convert dict entries to CachedFile objects
            self._cache = {
                image_id: CachedFile.from_dict(entry)
                for image_id, entry in data.items()
            }
            
            # Clean up expired entries
            self._clean_expired()
            
            logger.info(f"Loaded {len(self._cache)} cached file entries from {self.cache_path}")
        except Exception as e:
            logger.error(f"Failed to load cache from {self.cache_path}: {e}")
            self._cache = {}
    
    def _save(self):
        """Save cache to disk."""
        try:
            # Convert CachedFile objects to dicts
            data = {
                image_id: cached_file.to_dict()
                for image_id, cached_file in self._cache.items()
            }
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
            
            with open(self.cache_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.debug(f"Saved {len(self._cache)} cache entries to {self.cache_path}")
        except Exception as e:
            logger.error(f"Failed to save cache to {self.cache_path}: {e}")
    
    def _clean_expired(self):
        """Remove expired entries from cache."""
        expired_ids = [
            image_id for image_id, cached_file in self._cache.items()
            if cached_file.is_expired()
        ]
        
        for image_id in expired_ids:
            logger.debug(f"Removing expired cache entry for image {image_id}")
            del self._cache[image_id]
        
        if expired_ids:
            self._save()
    
    def get(self, image_id: str) -> Optional[CachedFile]:
        """Get cached file info for an image ID.
        
        Args:
            image_id: UUID of the image
            
        Returns:
            CachedFile if found and not expired, None otherwise
        """
        cached = self._cache.get(image_id)
        if cached and not cached.is_expired():
            return cached
        
        # Remove expired entry
        if cached:
            logger.debug(f"Cache entry for {image_id} has expired")
            del self._cache[image_id]
            self._save()
        
        return None
    
    def set(self, image_id: str, file_id: str, image_path: str):
        """Cache a new file upload.
        
        Args:
            image_id: UUID of the image
            file_id: Anthropic file ID
            image_path: Path to the image file
        """
        now = datetime.now()
        expires = now + timedelta(hours=default_config.ANTHROPIC_FILE_TTL_HOURS)
        
        cached_file = CachedFile(
            file_id=file_id,
            uploaded_at=now.isoformat(),
            image_path=image_path,
            expires_at=expires.isoformat(),
            image_id=image_id
        )
        
        self._cache[image_id] = cached_file
        self._save()
        
        logger.debug(f"Cached file {file_id} for image {image_id}, expires at {expires}")
    
    def get_all(self) -> Dict[str, CachedFile]:
        """Get all non-expired cached files.
        
        Returns:
            Dictionary mapping image_id to CachedFile
        """
        self._clean_expired()
        return self._cache.copy()
    
    def clear(self):
        """Clear all cache entries."""
        self._cache = {}
        self._save()
        logger.info(f"Cleared cache at {self.cache_path}")


__all__ = ["AnthropicFileCache", "CachedFile"]
