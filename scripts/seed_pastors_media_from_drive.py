#!/usr/bin/env python3
from __future__ import annotations
# ruff: noqa: I001

"""Import public pastor photos from a Google Drive folder into CMS media library.

The public pastores page consumes CMS page sections, so the workflow is:

1. Download the Drive images.
2. Save them through StorageService into ``uploads/cms/pastores/`` and register
   each one as a ``CmsMediaItem`` (Axioma 3: with sede_id and created_by_persona_id).
3. Update the published CMS ``pastors`` page so each pastor points at the
   CMS-hosted asset URL.
4. Re-publish the page so the public snapshot stays in sync.

This script is idempotent. If a Drive file has already been downloaded and the
CMS image URL is already correct, rerunning it is a no-op.
"""

import json
import re
import sys
from pathlib import Path

import requests
from sqlalchemy import text

_HERE = Path(__file__).resolve()
_PROJECT_ROOT = next((p for p in _HERE.parents if (p / "backend" / "__init__.py").is_file()), None)
if _PROJECT_ROOT is None:
    raise RuntimeError(f"backend package not found above {_HERE}")
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend import crud, models  # noqa: E402
from backend.core.database import SessionLocal  # noqa: E402
from backend.core.storage import storage_service  # noqa: E402


FOLDER_ID = "1Hq9fUDEbyBHoCz_DPnoYNX1fKyhIBpOi"
SITE_KEY = "ccf"
PAGE_SLUG = "pastors"
UPLOAD_SUBDIR = "cms/pastores"

TARGET_FILES = {
    "luis-ricardo-meza": ["PASTOR LUIS RICARDO MEZA.jpg", "PASTOR  LUIS RICARDO MEZA.jpg"],
    "histar-ariza": ["PASTORA HISTAR ARIZA.jpg"],
    "yair-macea": ["PASTOR YAIR MACEA.jpg"],
    "nehemias-morales": ["PASTOR NEHEMIAS MORALES.jpg"],
    "martina-herrera": ["PASTORA MARTINA ARIZA.jpg"],
    "yanedith-wilches": ["PASTORA YANEDITH WILCHES.jpg"],
    "alex-y-elvia": ["PASTORES ALEX Y ELVIA.jpg"],
    "camilo-pajaro": ["PASTORES CAMILO Y ALBA.jpg"],
    "fernando-y-monica": ["PASTORES MONICA Y FERNANDO.jpg"],
    "pastors-banner": ["PASTORES LUIS RICARDO E HISTAR.jpg"],
}


def _find_admin_user(db) -> models.Usuario:
    user = (
        db.query(models.Usuario)
        .filter(models.Usuario.email == "gscarlosernesto@gmail.com")
        .first()
    )
    if user is None:
        user = (
            db.query(models.Usuario)
            .filter(models.Usuario.is_active.is_(True), models.Usuario.sede_id.isnot(None))
            .first()
        )
    if user is None:
        raise RuntimeError("No active admin/user with sede found to own CMS media items")
    return user


def _download_folder_index(folder_id: str) -> str:
    resp = requests.get(
        f"https://drive.google.com/drive/folders/{folder_id}",
        timeout=60,
    )
    resp.raise_for_status()
    return resp.text


def _extract_files(folder_html: str) -> dict[str, str]:
    pattern = re.compile(
        r'data-id="([^"]+)"[\s\S]{0,800}?data-tooltip="([^"]+?) Image"',
        re.S,
    )
    files: dict[str, str] = {}
    for file_id, title in pattern.findall(folder_html):
        title = title.strip()
        if title.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".gif")):
            files.setdefault(_normalize_name(title), file_id)
    return files


def _normalize_name(name: str) -> str:
    return re.sub(r"\s+", " ", name).strip().casefold()


def _download_drive_file(file_id: str) -> tuple[bytes, str]:
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    content_type = resp.headers.get("content-type", "application/octet-stream")
    return resp.content, content_type


def _ensure_cms_media(db, user: models.Usuario, slug: str, content: bytes, original_name: str) -> str:
    """Save image via StorageService and register/return the public CMS URL."""
    public_path = storage_service.save_file(content, original_name, subfolder=UPLOAD_SUBDIR)
    # StorageService returns ``/static/{subfolder}/{name}`` \u2014 the path
    # WITHIN the static mount. The app mounts StaticFiles at
    # ``/api/static`` (see ``backend/app.py``: ``app.mount("/api/static", ...)``),
    # so the public URL is the mount path + the storage path's tail. A naive
    # ``f"/api/static{public_path}"`` would produce
    # ``/api/static/static/cms/pastores/<uuid>.webp`` (DOUBLE static) and
    # the live endpoint would 500 on the wrong URL. Strip the leading
    # ``/static/`` so the public URL is canonical.
    if public_path.startswith("/static/"):
        relative = public_path[len("/static/"):]
    else:
        relative = public_path.lstrip("/")
    public_url = f"/api/static/{relative}"

    existing = (
        db.query(models.CmsMediaItem)
        .filter(models.CmsMediaItem.url == public_url)
        .first()
    )
    if existing is None:
        crud.create_cms_media_item(
            db,
            url=public_url,
            alt_text=slug.replace("-", " ").replace("_", " ").title(),
            section="pastores",
            tags=["public-site", "drive-import", slug],
            created_by=user.id,
            filename=Path(original_name).name,
            mime_type="image/webp",
            file_size=len(content),
            actor_user_id=user.id,
        )
    return public_url


def main() -> int:
    folder_html = _download_folder_index(FOLDER_ID)
    folder_files = _extract_files(folder_html)

    photo_urls: dict[str, str] = {}
    downloaded = 0

    with SessionLocal() as db:
        user = _find_admin_user(db)

        for slug, candidates in TARGET_FILES.items():
            file_id = next(
                (folder_files[_normalize_name(name)] for name in candidates if _normalize_name(name) in folder_files),
                None,
            )
            if not file_id:
                raise RuntimeError(f"Could not find a Drive file for {slug!r}")

            content, _content_type = _download_drive_file(file_id)
            original_name = candidates[0]
            public_url = _ensure_cms_media(db, user, slug, content, original_name)

            # Idempotency: count as downloaded only if this exact URL is new.
            if photo_urls.get(slug) != public_url:
                downloaded += 1
            photo_urls[slug] = public_url

        site = db.query(models.CmsSite).filter(models.CmsSite.site_key == SITE_KEY).first()
        if site is None:
            raise RuntimeError(f"CMS site {SITE_KEY!r} not found")

        page = (
            db.query(models.CmsPage)
            .filter(models.CmsPage.site_id == site.id, models.CmsPage.slug == PAGE_SLUG)
            .first()
        )
        if page is None:
            raise RuntimeError("pastors page not found; run ensure_public_cms_pastors.py first")

        sections = (
            db.query(models.CmsSection)
            .filter(models.CmsSection.page_id == page.id)
            .order_by(models.CmsSection.sort_order.asc(), models.CmsSection.id.asc())
            .all()
        )
        changed = False
        for section in sections:
            props = section.props_json or {}
            if section.section_key == "hero":
                desired = photo_urls.get("martina-herrera")
                if desired and props.get("bg_image") != desired:
                    props["bg_image"] = desired
                    if props.get("content"):
                        try:
                            parsed = json.loads(props["content"])
                        except Exception:
                            parsed = None
                        if isinstance(parsed, dict):
                            parsed["bg_image"] = desired
                            props["content"] = json.dumps(parsed, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
                    section.props_json = props
                    changed = True
            elif section.section_key == "pastors":
                payload = props.get("pastors")
                if isinstance(payload, list):
                    next_payload = []
                    local_changed = False
                    for item in payload:
                        if not isinstance(item, dict):
                            next_payload.append(item)
                            continue
                        slug = str(item.get("slug") or "").strip()
                        desired = photo_urls.get(slug)
                        if desired and item.get("image") != desired:
                            item = dict(item)
                            item["image"] = desired
                            local_changed = True
                        next_payload.append(item)
                    if local_changed:
                        props["pastors"] = next_payload
                        if props.get("content"):
                            try:
                                parsed = json.loads(props["content"])
                            except Exception:
                                parsed = None
                            if isinstance(parsed, dict):
                                parsed["pastors"] = next_payload
                                props["content"] = json.dumps(parsed, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
                        section.props_json = props
                        changed = True

        if not changed:
            print("Photos already in sync.")
            return 0

        current_sections = [
            {
                "section_key": s.section_key,
                "type": s.type,
                "props_json": s.props_json or {},
                "sort_order": s.sort_order,
                "is_visible": s.is_visible,
                "status": s.status or "active",
            }
            for s in sections
        ]
        version_number = db.execute(
            text("SELECT COALESCE(MAX(version_number), 0) + 1 FROM cms_page_versions WHERE page_id = :page_id"),
            {"page_id": page.id},
        ).scalar_one()
        snapshot = {
            "page": {
                "id": str(page.id),
                "slug": page.slug,
                "title": page.title,
                "status": "published",
                "seo_json": page.seo_json or {},
            },
            "sections": current_sections,
        }
        version = models.CmsPageVersion(
            page_id=page.id,
            version_number=int(version_number),
            snapshot_json=snapshot,
            notes="Sync pastor images from public Drive folder",
        )
        db.add(version)
        db.flush()
        page.status = "published"
        page.published_version_id = version.id
        db.commit()

    print(f"Downloaded/updated files: {downloaded}")
    print("CMS pastors page republished with Drive-backed assets.")
    for slug, url in sorted(photo_urls.items()):
        print(f"{slug}: {url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
