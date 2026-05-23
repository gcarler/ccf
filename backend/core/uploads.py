import re
from pathlib import Path
from typing import Iterable

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "pdf", "mp4", "mp3", "wav", "zip"}
MAX_UPLOAD_SIZE = 10 * 1024 * 1024
FILENAME_PATTERN = re.compile(r"[^a-zA-Z0-9._-]")


def sanitize_filename(filename: str) -> str:
    name = filename or "upload"
    name = Path(name).name
    return FILENAME_PATTERN.sub("_", name)


def ensure_allowed_extension(
    filename: str, allowed: Iterable[str] = ALLOWED_EXTENSIONS
) -> None:
    ext = Path(filename).suffix.lower().lstrip(".")
    if ext not in allowed:
        raise ValueError(f"File extension '{ext}' is not permitted")


def save_upload(contents: bytes, filename: str, uploads_dir: str) -> str:
    if len(contents) > MAX_UPLOAD_SIZE:
        raise ValueError("File exceeds maximum size")
    ensure_allowed_extension(filename)
    uploads_path = Path(uploads_dir)
    uploads_path.mkdir(parents=True, exist_ok=True)
    destination = uploads_path / filename
    destination.write_bytes(contents)
    return str(destination)
