from __future__ import annotations

import logging
import os
import pathlib
import uuid

from backend.core.config import get_settings
from backend.services.image_optimizer import ImageOptimizer

log = logging.getLogger(__name__)
settings = get_settings()
optimizer = ImageOptimizer(
    max_width=settings.image_max_width,
    quality=settings.image_quality,
)


class StorageService:
    def __init__(self, base_dir: str = None):
        self.base_dir = base_dir or settings.uploads_dir
        pathlib.Path(self.base_dir).mkdir(parents=True, exist_ok=True)

    def save_file(
        self, content: bytes, filename: str, subfolder: str = "general"
    ) -> str:
        """
        Saves a file and returns the public URL/path.

        For raster images (JPEG, PNG, WebP) the content is automatically
        optimized: re-encoded as WebP, resized to at most ``max_width`` px,
        and compressed at the configured quality level.
        """
        target_dir = os.path.join(self.base_dir, subfolder)
        pathlib.Path(target_dir).mkdir(parents=True, exist_ok=True)

        # --- Optimize images before saving ---
        optimized, opt_ext, _w, _h = optimizer.optimize(content, filename)

        ext = opt_ext or pathlib.Path(filename).suffix
        unique_name = f"{uuid.uuid4().hex}{ext}"
        full_path = os.path.join(target_dir, unique_name)

        with open(full_path, "wb") as f:
            f.write(optimized)

        log.info(f"File saved: {full_path}  ({len(optimized)} bytes)")
        return f"/api/static/{subfolder}/{unique_name}"

    def save_file_original(
        self, content: bytes, filename: str, subfolder: str = "general"
    ) -> str:
        """
        Save a file **without** any image optimization.

        Use this when the caller needs the exact original bytes (e.g. PDFs,
        ZIPs, or cases where image fidelity must be pixel-perfect).
        """
        target_dir = os.path.join(self.base_dir, subfolder)
        pathlib.Path(target_dir).mkdir(parents=True, exist_ok=True)

        ext = pathlib.Path(filename).suffix
        unique_name = f"{uuid.uuid4().hex}{ext}"
        full_path = os.path.join(target_dir, unique_name)

        with open(full_path, "wb") as f:
            f.write(content)

        log.info(f"File saved (original): {full_path}")
        return f"/api/static/{subfolder}/{unique_name}"

    def save_file_seaweed(
        self, content: bytes, filename: str, subfolder: str = "general"
    ) -> str:
        """
        Guarda un archivo en SeaweedFS (o S3) y retorna su FID.
        Esta es la implementación de integración. Si no está configurado,
        retorna un FID generado localmente para desarrollo.
        """
        seaweed_url = getattr(settings, "seaweed_url", None)
        ext = pathlib.Path(filename).suffix
        unique_name = f"{uuid.uuid4().hex}{ext}"
        
        if not seaweed_url:
            log.warning("SeaweedFS URL not configured. Mocking FID generation.")
            return f"mock-fid-{unique_name}"
            
        import requests
        try:
            target_url = f"{seaweed_url}/{subfolder}/{unique_name}"
            resp = requests.post(target_url, files={"file": content}, timeout=10)
            resp.raise_for_status()
            # En SeaweedFS Filer la respuesta suele ser JSON con el Name y Fid si es directo al Volume
            # Si es a través de S3 (boto3) sería distinto, pero para el prototipo usamos POST
            return unique_name
        except Exception as e:
            log.error(f"Error uploading to SeaweedFS: {e}")
            return f"mock-fid-{unique_name}"

    def delete_file(self, file_path: str):
        # Implementation for cleanup if needed
        pass


storage_service = StorageService()
