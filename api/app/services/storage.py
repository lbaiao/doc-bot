import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO

from app.core.config import settings


class StorageService(ABC):
    """Abstract storage interface for file operations."""
    
    @abstractmethod
    async def put(self, data: bytes, path_hint: str) -> str:
        """Store data and return storage URI."""
        pass
    
    @abstractmethod
    async def get(self, storage_uri: str) -> bytes:
        """Retrieve data by storage URI."""
        pass
    
    @abstractmethod
    async def delete(self, storage_uri: str) -> None:
        """Delete data by storage URI."""
        pass
    
    @abstractmethod
    async def exists(self, storage_uri: str) -> bool:
        """Check if file exists."""
        pass


class LocalStorageService(StorageService):
    """Local filesystem storage implementation."""
    
    def __init__(self, base_path: str = None):
        self.base_path = Path(base_path or settings.LOCAL_STORAGE_PATH)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    async def put(self, data: bytes, path_hint: str) -> str:
        """Store file locally and return URI."""
        # Clean path hint
        clean_path = path_hint.lstrip("/")
        file_path = self.base_path / clean_path
        
        # Create parent directories
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write file
        file_path.write_bytes(data)
        
        return f"local://{clean_path}"
    
    async def get(self, storage_uri: str) -> bytes:
        """Retrieve file from local storage."""
        if not storage_uri.startswith("local://"):
            raise ValueError(f"Invalid local storage URI: {storage_uri}")
        
        relative_path = storage_uri[len("local://"):]
        file_path = self.base_path / relative_path
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {storage_uri}")
        
        return file_path.read_bytes()
    
    async def delete(self, storage_uri: str) -> None:
        """Delete file from local storage."""
        if not storage_uri.startswith("local://"):
            raise ValueError(f"Invalid local storage URI: {storage_uri}")
        
        relative_path = storage_uri[len("local://"):]
        file_path = self.base_path / relative_path
        
        if file_path.exists():
            file_path.unlink()
    
    async def exists(self, storage_uri: str) -> bool:
        """Check if file exists in local storage."""
        if not storage_uri.startswith("local://"):
            return False
        
        relative_path = storage_uri[len("local://"):]
        file_path = self.base_path / relative_path
        
        return file_path.exists()


class S3StorageService(StorageService):
    """S3-compatible storage implementation (stub for future)."""
    
    def __init__(self, bucket: str, region: str = None):
        self.bucket = bucket
        self.region = region
        # TODO: Initialize S3 client with boto3
        raise NotImplementedError("S3 storage not yet implemented")
    
    async def put(self, data: bytes, path_hint: str) -> str:
        raise NotImplementedError("S3 storage not yet implemented")
    
    async def get(self, storage_uri: str) -> bytes:
        raise NotImplementedError("S3 storage not yet implemented")
    
    async def delete(self, storage_uri: str) -> None:
        raise NotImplementedError("S3 storage not yet implemented")
    
    async def exists(self, storage_uri: str) -> bool:
        raise NotImplementedError("S3 storage not yet implemented")


def get_storage_service() -> StorageService:
    """Factory function to get appropriate storage service."""
    if settings.STORAGE_TYPE == "local":
        return LocalStorageService()
    elif settings.STORAGE_TYPE == "s3":
        return S3StorageService(bucket=settings.S3_BUCKET, region=settings.S3_REGION)
    else:
        raise ValueError(f"Unknown storage type: {settings.STORAGE_TYPE}")
