"""Shared CMS media service.

Encapsulates upload, optimization and deletion logic for ``CmsMediaItem``
so that both the old v1 API (``backend/api/cms.py``) and the v2 API can
reuse the same code path. Keeping the business logic here prevents
duplication between the two routers and makes the migration to the v2
model easier.

Axioma 3 — Multi-Tenant: the service receives ``actor_user_id`` and
relies on the existing CRUD helpers (which already enforce sede scope)
to persist data. It does **not** bypass tenant checks.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

from backend import crud, models
from backend.core.config import get_settings
from backend.core.storage import storage_service
from backend.core.uploads import (
    MAX_UPLOAD_SIZE,
    ensure_allowed_extension,
    sanitize_filename,
    validate_mime_extension_alignment,
)
from backend.services.image_optimizer import ImageOptimizer

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def _uploads_root() -> str:
    """Return the absolute upload root from settings.

    Computed lazily so the module can be imported without requiring
    fully populated environment variables at import time.
    """
    settings = get_settings()
    return os.path.abspath(settings.uploads_dir)


def _guard_path(url: str) -> str:
    """Resolve a media URL to an absolute path inside the upload root.

    Mirrors the traversal guard used by the old v1 endpoints so that
    a malicious ``url`` like ``../../etc/passwd`` cannot escape the
    upload directory.

    Raises:
        ValueError: if the resolved path is outside the upload root.
    """
    uploads_root = _uploads_root()
    if url.startswith("/") and not url.startswith("/uploads/"):
        raise ValueError("Invalid file path")
    rel_path = url.lstrip("/").replace("uploads/", "", 1)
    full_path = os.path.normpath(os.path.join(uploads_root, rel_path))
    try:
        Path(full_path).resolve(strict=False).relative_to(Path(uploads_root).resolve(strict=False))
    except ValueError as exc:
        raise ValueError("Invalid file path") from exc
    return full_path


def upload_cms_media(
    db: "Session",
    *,
    content: bytes,
    filename: str,
    content_type: str | None,
    section: str = "general",
    alt_text: str = "",
    tags: list[str] | None = None,
    optimize: bool = True,
    actor_user_id: str | None = None,
) -> models.CmsMediaItem:
    """Upload a CMS media file, applying validation, optimization and tenant scoping.

    Args:
        db: SQLAlchemy session.
        content: Raw file bytes.
        filename: Original file name.
        content_type: MIME type declared by the client.
        section: Logical section (e.g. ``general``, ``branding``).
        alt_text: Alternative text for the asset.
        tags: Comma-separated string or list of tags.
        optimize: Whether to run image optimization.
        actor_user_id: UUID of the acting user (used for sede derivation).

    Returns:
        The persisted ``CmsMediaItem``.

    Raises:
        ValueError: if validation or path checks fail.
        HTTPException: propagated from the CRUD layer on scope violations.
    """
    original_name = sanitize_filename(filename or "asset.bin")

    # 1) Size guardrail
    if len(content) > MAX_UPLOAD_SIZE:
        raise ValueError("File exceeds maximum size")

    # 2) Extension allow-list
    ensure_allowed_extension(original_name)

    # 3) MIME/extension alignment
    validate_mime_extension_alignment(original_name, content_type)

    parsed_tags = tags or []

    # 4) Image optimization (convert to WebP, resize, compress)
    mime_type = content_type
    width: int | None = None
    height: int | None = None
    dimensions: str | None = None
    final_content = content
    final_name = original_name

    if optimize:
        try:
            optimizer = ImageOptimizer()
            optimized_bytes, output_ext, width, height = optimizer.optimize(content, original_name)
            if output_ext != os.path.splitext(original_name)[1].lower():
                # Extension changed (e.g. .jpg -> .webp)
                final_name = os.path.splitext(original_name)[0] + output_ext
                mime_type = f"image/{output_ext.lstrip('.')}"
            final_content = optimized_bytes
            if width and height:
                dimensions = f"{width}x{height}"
        except Exception as exc:
            logger.debug(
                "Image optimization failed for %s, falling back to original: %s",
                original_name,
                exc,
            )

    url = storage_service.save_file(final_content, final_name, subfolder="cms")

    return crud.create_cms_media_item(
        db,
        url=url,
        alt_text=alt_text or filename,
        section=section,
        tags=parsed_tags,
        created_by=actor_user_id,
        filename=filename,
        mime_type=mime_type,
        file_size=len(final_content),
        width=width,
        height=height,
        dimensions=dimensions,
        actor_user_id=actor_user_id,
    )


def optimize_cms_media(
    db: "Session",
    row: models.CmsMediaItem,
    *,
    actor_user_id: str | None = None,
) -> models.CmsMediaItem:
    """Optimize an existing image media item.

    Re-encodes the original file to WebP, resizes, compresses and updates
    the DB row with the new asset metadata.

    Args:
        db: SQLAlchemy session.
        row: Existing ``CmsMediaItem``.
        actor_user_id: UUID of the acting user.

    Returns:
        The updated ``CmsMediaItem``.

    Raises:
        ValueError: if the item is not an image or the file path is invalid.
    """
    if not row.mime_type or not row.mime_type.startswith("image/"):
        raise ValueError("Only images can be optimized")

    full_path = _guard_path(row.url)
    if not os.path.exists(full_path) or not os.path.isfile(full_path):
        raise ValueError("Original file not found")

    with open(full_path, "rb") as f:
        content = f.read()

    optimizer = ImageOptimizer()
    optimized_bytes, output_ext, width, height = optimizer.optimize(content, row.filename or "image.jpg")

    optimized_name = os.path.splitext(row.filename or "image.jpg")[0] + output_ext
    new_url = storage_service.save_file(optimized_bytes, optimized_name, subfolder="cms")

    return crud.update_cms_media_item(
        db,
        row.id,
        url=new_url,
        mime_type=f"image/{output_ext.lstrip('.')}",
        file_size=len(optimized_bytes),
        filename=optimized_name,
        width=width,
        height=height,
        dimensions=f"{width}x{height}" if width and height else None,
        actor_user_id=actor_user_id,
    )


def delete_cms_media(
    db: "Session",
    row: models.CmsMediaItem,
    *,
    permanent: bool = False,
    actor_user_id: str | None = None,
) -> bool:
    """Delete a CMS media item.

    When ``permanent`` is true, the physical file is removed (with path
    traversal guard) and the DB row is hard-deleted. Otherwise a soft
    delete (``status='archived'``) is performed.

    Args:
        db: SQLAlchemy session.
        row: ``CmsMediaItem`` to delete.
        permanent: Whether to hard-delete.
        actor_user_id: UUID of the acting user.

    Returns:
        ``True`` if the operation succeeded.
    """
    if permanent and row.url:
        full_path = _guard_path(row.url)
        if os.path.exists(full_path) and os.path.isfile(full_path):
            os.remove(full_path)

    return crud.delete_cms_media_item(
        db,
        row.id,
        actor_user_id=actor_user_id,
        permanent=permanent,
    )
