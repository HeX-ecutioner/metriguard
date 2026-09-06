import os
import uuid
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
from app.core.config import settings, ensure_directories

class StorageService(ABC):
    """
    Abstract storage interface for handling file uploads.
    Allows local filesystem storage in development and cloud backends (S3, MinIO) later.
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
    Local filesystem storage implementation storing files under backend/storage/uploads/.
    Ensures backend/storage/, uploads/, and reports/ are automatically initialized.
    """

    def __init__(self, base_dir: Optional[Path] = None):
        if base_dir is None:
            self.base_dir = settings.get_resolved_storage_path()
        else:
            self.base_dir = Path(base_dir).resolve()

        self.uploads_dir = self.base_dir / "uploads"
        self.reports_dir = self.base_dir / "reports"

        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def _sanitize_filename(self, filename: str) -> str:
        name = Path(filename).name
        # Keep only alphanumeric, hyphens, underscores, and dots
        clean_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', name)
        return clean_name or "uploaded_file"

    def _resolve_key_path(self, file_key: str) -> Optional[Path]:
        if not file_key:
            return None
        safe_key = Path(file_key).name
        # Check uploads_dir first, then base_dir for backwards compatibility
        path_in_uploads = self.uploads_dir / safe_key
        if path_in_uploads.exists():
            return path_in_uploads
        path_in_base = self.base_dir / safe_key
        if path_in_base.exists():
            return path_in_base
        return None

    async def save_file(self, filename: str, content: bytes) -> str:
        safe_name = self._sanitize_filename(filename)
        unique_prefix = uuid.uuid4().hex[:8]
        file_key = f"{unique_prefix}_{safe_name}"
        destination = self.uploads_dir / file_key

        with open(destination, "wb") as f:
            f.write(content)

        return file_key

    async def get_file(self, file_key: str) -> Optional[bytes]:
        file_path = self._resolve_key_path(file_key)
        if file_path and file_path.is_file():
            with open(file_path, "rb") as f:
                return f.read()
        return None

    async def delete_file(self, file_key: str) -> bool:
        file_path = self._resolve_key_path(file_key)
        if file_path and file_path.is_file():
            file_path.unlink()
            return True
        return False

    def get_file_path(self, file_key: str) -> Optional[str]:
        if not file_key:
            return self.base_dir.as_posix()
        file_path = self._resolve_key_path(file_key)
        if file_path and file_path.exists():
            return file_path.as_posix()
        # If file hasn't been saved yet, return the expected location in uploads
        expected_path = self.uploads_dir / Path(file_key).name
        if expected_path.exists():
            return expected_path.as_posix()
        return None


def get_storage_service() -> StorageService:
    """
    Factory function returning the configured StorageService instance.
    Defaults to LocalStorageService.
    """
    ensure_directories()
    return LocalStorageService()
