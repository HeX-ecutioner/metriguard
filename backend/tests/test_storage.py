import pytest
import os
from pathlib import Path
from app.services.storage import LocalStorageService, get_storage_service

import asyncio

def test_local_storage_lifecycle(tmp_path):
    async def _run():
        storage = LocalStorageService(base_dir=tmp_path)
        test_content = b"Legal Metrology Package Inspection Content"
        filename = "test_commodity_label.jpg"

        # Save
        file_key = await storage.save_file(filename, test_content)
        assert file_key is not None
        assert "test_commodity_label" in file_key

        # Retrieve
        retrieved = await storage.get_file(file_key)
        assert retrieved == test_content

        # Path
        path_str = storage.get_file_path(file_key)
        assert path_str is not None
        assert Path(path_str).exists()

        # Delete
        deleted = await storage.delete_file(file_key)
        assert deleted is True

        # Retrieve after delete
        retrieved_after = await storage.get_file(file_key)
        assert retrieved_after is None

    asyncio.run(_run())


def test_get_storage_service_default():
    service = get_storage_service()
    assert isinstance(service, LocalStorageService)
