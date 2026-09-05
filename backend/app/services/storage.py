import os
import uuid
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

class StorageService(ABC):
    """
    Abstract storage interface for handling file uploads.
    Allows local filesystem storage in MVP and cloud backends (S3, MinIO) later.
    """

    @abstractmethod
    async def save_file(self, filename: str, content: bytes) -> str:
        """
        Saves file content and returns a unique storage key/identifier.
        """
        pass

    @abstractmethod
    async def get_file(self, file_key: str) -> Optional[bytes]:
        """
        Retrieves file content given a storage key.
        """
        pass

    @abstractmethod
    async def delete_file(self, file_key: str) -> bool:
        """
        Deletes a file given a storage key. Returns True if deleted, False otherwise.
        """
        pass

    @abstractmethod
    def get_file_path(self, file_key: str) -> Optional[str]:
        """
        Returns local filesystem path if available, or None for remote storage backends.
        """
        pass


class LocalStorageService(StorageService):
    """
    Local filesystem storage implementation storing files under backend/storage/.
    """

    def __init__(self, base_dir: Optional[Path] = None):
        if base_dir is None:
            backend_dir = Path(__file__).resolve().parent.parent.parent
            base_dir = backend_dir / "storage"
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _sanitize_filename(self, filename: str) -> str:
        name = Path(filename).name
        # Keep only alphanumeric, hyphens, underscores, and dots
        clean_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', name)
        return clean_name or "uploaded_file"

    async def save_file(self, filename: str, content: bytes) -> str:
        safe_name = self._sanitize_filename(filename)
        unique_prefix = uuid.uuid4().hex[:8]
        file_key = f"{unique_prefix}_{safe_name}"
        destination = self.base_dir / file_key

        with open(destination, "wb") as f:
            f.write(content)

        return file_key

    async def get_file(self, file_key: str) -> Optional[bytes]:
        safe_key = Path(file_key).name
        file_path = self.base_dir / safe_key
        if file_path.is_file():
            with open(file_path, "rb") as f:
                return f.read()
        return None

    async def delete_file(self, file_key: str) -> bool:
        safe_key = Path(file_key).name
        file_path = self.base_dir / safe_key
        if file_path.is_file():
            file_path.unlink()
            return True
        return False

    def get_file_path(self, file_key: str) -> Optional[str]:
        safe_key = Path(file_key).name
        file_path = self.base_dir / safe_key
        if file_path.exists():
            return file_path.as_posix()
        return None


def get_storage_service() -> StorageService:
    """
    Factory function returning the configured StorageService instance.
    Defaults to LocalStorageService.
    """
    storage_type = os.getenv("STORAGE_TYPE", "local").lower()
    storage_dir = os.getenv("STORAGE_DIR")
    
    if storage_type == "local":
        base_dir = Path(storage_dir) if storage_dir else None
        return LocalStorageService(base_dir=base_dir)
    
    raise ValueError(f"Unsupported storage backend: '{storage_type}'. S3 or MinIO can be plugged in here.")
