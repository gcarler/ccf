#!/usr/bin/env python3
from __future__ import annotations
# ruff: noqa: I001

"""Import public pastor photos from a Google Drive folder into CMS/public storage.

The public pastores page consumes CMS page sections, so the correct workflow is:

1. Download the Drive images.
2. Store them under the backend static uploads directory.
3. Update the published CMS `pastors` page so each pastor points at the
   project-hosted asset URL.
4. Re-publish the page so the public snapshot stays in sync.

This script is idempotent. If a file already exists and the CMS image URL is
already correct, rerunning it is a no-op.
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

from backend import models  # noqa: E402
from backend.core.database import SessionLocal  # noqa: E402
from backend.core.config import get_settings  # noqa: E402


FOLDER_ID = "1Hq9fUDEbyBHoCz_DPnoYNX1fKyhIBpOi"
SITE_KEY = "ccf"
PAGE_SLUG = "pastors"
UPLOAD_SUBDIR = "cms/pastores"
PUBLIC_SUBDIR = "images/pastores"


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


def _slug_to_filename(slug: str, original_name: str) -> str:
    suffix = Path(original_name).suffix.lower() or ".jpg"
    if suffix not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        suffix = ".jpg"
    return f"{slug}{suffix}"


def _public_url(filename: str) -> str:
    return f"/images/pastores/{filename}"


def _ensure_local_file(path: Path, content: bytes) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() == content:
        return False
    path.write_bytes(content)
    return True


def main() -> int:
    folder_html = _download_folder_index(FOLDER_ID)
    folder_files = _extract_files(folder_html)

    settings = get_settings()
    uploads_root = Path(settings.uploads_dir)
    public_root = _PROJECT_ROOT / "frontend" / "public"
    photo_urls: dict[str, str] = {}

    downloaded = 0
    for slug, candidates in TARGET_FILES.items():
        file_id = next((folder_files[_normalize_name(name)] for name in candidates if _normalize_name(name) in folder_files), None)
        if not file_id:
            raise RuntimeError(f"Could not find a Drive file for {slug!r}")

        content, _content_type = _download_drive_file(file_id)
        original_name = candidates[0]
        filename = _slug_to_filename(slug, original_name)
        local_upload_path = uploads_root / UPLOAD_SUBDIR / filename
        local_public_path = public_root / PUBLIC_SUBDIR / filename
        changed_upload = _ensure_local_file(local_upload_path, content)
        changed_public = _ensure_local_file(local_public_path, content)
        if changed_upload or changed_public:
            downloaded += 1
        photo_urls[slug] = _public_url(filename)

    with SessionLocal() as db:
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
        # Use SQL directly to keep the script self-contained and avoid coupling
        # to CRUD helpers that expect authenticated users.
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
