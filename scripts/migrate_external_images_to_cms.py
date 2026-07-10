#!/usr/bin/env python3
"""Download external images referenced by CMS sections and re-host them locally.

Usage:
    cd /root/ccf && source venv/bin/activate && python scripts/migrate_external_images_to_cms.py
"""
from __future__ import annotations

import hashlib
import json
import mimetypes
import re
import sys
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

_HERE = Path(__file__).resolve()
_PROJECT_ROOT = next(
    (p for p in _HERE.parents if (p / "backend" / "__init__.py").is_file()),
    None,
)
if _PROJECT_ROOT is None:
    raise RuntimeError(f"backend package not found above {_HERE}")
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import backend.models as models  # noqa: E402
from backend.core.config import get_settings  # noqa: E402
from sqlalchemy import text  # noqa: E402

try:
    from backend.database import SessionLocal  # noqa: E402
except Exception:
    from backend.core.database import SessionLocal  # noqa: E402

EXTERNAL_DOMAINS = {"unsplash.com", "picsum.photos"}
EXTERNAL_RE = re.compile(r"https?://[^\s\"'\)<>]+")


def _is_external(url: str) -> bool:
    parsed = urlparse(url)
    netloc = parsed.netloc.lower()
    return any(netloc == domain or netloc.endswith(f".{domain}") for domain in EXTERNAL_DOMAINS)


def _ext_from_headers(url: str, content_type: str | None) -> str:
    parsed = urlparse(url)
    path_ext = Path(parsed.path).suffix.lower()
    if path_ext in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif"}:
        return path_ext
    if content_type:
        ext = mimetypes.guess_extension(content_type.split(";")[0].strip())
        if ext:
            return ext
    return ".jpg"


def _download(url: str) -> tuple[bytes, str | None]:
    headers = {"User-Agent": "CCF-CMS-image-migration/1.0"}
    resp = requests.get(url, headers=headers, timeout=60)
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type")


def _find_external_urls(props: Any) -> list[str]:
    text = json.dumps(props, ensure_ascii=False)
    found: set[str] = set()
    for match in EXTERNAL_RE.finditer(text):
        url = match.group()
        if _is_external(url):
            found.add(url)
    return sorted(found)


def _replace_url(props: Any, old: str, new: str) -> Any:
    if isinstance(props, dict):
        return {k: _replace_url(v, old, new) for k, v in props.items()}
    if isinstance(props, list):
        return [_replace_url(item, old, new) for item in props]
    if isinstance(props, str):
        if old in props:
            return props.replace(old, new)
        # Some sections store nested JSON as a string (e.g. "parsed", "content").
        try:
            parsed = json.loads(props)
        except (json.JSONDecodeError, TypeError):
            return props
        replaced = _replace_url(parsed, old, new)
        return json.dumps(replaced, ensure_ascii=False)
    return props


def _get_system_persona_and_sede(db: Any) -> tuple[uuid.UUID, uuid.UUID]:
    persona = db.execute(text("SELECT id FROM personas LIMIT 1")).scalar()
    sede = db.execute(text("SELECT id FROM sedes LIMIT 1")).scalar()
    if persona is None or sede is None:
        raise RuntimeError("No personas/sedes found; cannot create CmsMediaItem")
    return uuid.UUID(str(persona)), uuid.UUID(str(sede))


def main() -> int:
    settings = get_settings()
    uploads_dir = Path(settings.uploads_dir)
    target_dir = uploads_dir / "cms" / "external"
    target_dir.mkdir(parents=True, exist_ok=True)

    db = SessionLocal()
    try:
        persona_id, sede_id = _get_system_persona_and_sede(db)
        sections = db.query(models.CmsSection).all()
        migrated = 0
        skipped = 0
        failed = 0

        for section in sections:
            props = section.props_json or {}
            external_urls = _find_external_urls(props)
            if not external_urls:
                continue

            for url in external_urls:
                # Use a hash of the full URL as the canonical filename so that
                # different dimensions of the same service produce distinct records.
                url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()
                existing = (
                    db.query(models.CmsMediaItem)
                    .filter(models.CmsMediaItem.filename == url_hash)
                    .first()
                )
                if existing:
                    section.props_json = _replace_url(props, url, existing.url)
                    props = section.props_json
                    skipped += 1
                    continue

                try:
                    data, content_type = _download(url)
                except Exception as exc:
                    print(f"Failed to download {url}: {exc}")
                    failed += 1
                    continue

                ext = _ext_from_headers(url, content_type)
                file_hash = hashlib.md5(data).hexdigest()
                file_name = f"{file_hash}{ext}"
                rel_path = f"cms/external/{file_name}"
                local_path = target_dir / file_name
                local_path.write_bytes(data)

                media_url = f"/api/static/{rel_path}"
                media = models.CmsMediaItem(
                    id=uuid.uuid4(),
                    filename=url_hash,
                    url=media_url,
                    file_size=len(data),
                    mime_type=content_type
                    or mimetypes.guess_type(file_name)[0]
                    or "image/jpeg",
                    status="active",
                    created_by_persona_id=persona_id,
                    sede_id=sede_id,
                )
                db.add(media)
                db.flush()

                section.props_json = _replace_url(props, url, media_url)
                props = section.props_json
                migrated += 1
                print(f"Migrated: {url} -> {media_url}")

        db.commit()
        print(f"\nDone: {migrated} migrated, {skipped} already local, {failed} failed")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
