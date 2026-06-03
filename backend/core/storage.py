from __future__ import annotations

import logging
import os
import pathlib
import uuid

from backend.core.config import get_settings

log = logging.getLogger(__name__)
settings = get_settings()


class StorageService:
    def __init__(self, base_dir: str = None):
        self.base_dir = base_dir or settings.uploads_dir
        pathlib.Path(self.base_dir).mkdir(parents=True, exist_ok=True)

    def save_file(
        self, content: bytes, filename: str, subfolder: str = "general"
    ) -> str:
        """
        Saves a file and returns the public URL/path.
        """
        target_dir = os.path.join(self.base_dir, subfolder)
        pathlib.Path(target_dir).mkdir(parents=True, exist_ok=True)

        ext = pathlib.Path(filename).suffix
        unique_name = f"{uuid.uuid4().hex}{ext}"
        full_path = os.path.join(target_dir, unique_name)

        with open(full_path, "wb") as f:
            f.write(content)

        log.info(f"File saved: {full_path}")
        return f"/static/{subfolder}/{unique_name}"

    def delete_file(self, file_path: str):
        # Implementation for cleanup if needed
        pass


storage_service = StorageService()
