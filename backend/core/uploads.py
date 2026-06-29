import re
from pathlib import Path
from typing import Iterable, Optional

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "pdf", "mp4", "mp3", "wav", "zip"}
# Maximum upload size (10 MiB) — applies a hard guardrail for both CMS media
# and CRMM personas. Aligns with ``MAX_UPLOAD_SIZE`` below.
MAX_UPLOAD_SIZE = 10 * 1024 * 1024
FILENAME_PATTERN = re.compile(r"[^a-zA-Z0-9._-]")

# Mapa extensión-categoría → prefijo MIME esperado. Cualquier content_type
# enviado por el cliente debe coincidir con la categoría de la extensión
# declarada. Esto previene ataques donde un binario malicioso (e.g. ``.exe``,
# ``.html``) es renombrado con una extensión benigna (``malware.png``) y un
# content_type falsificado (``application/x-msdownload``).
_EXTENSION_CATEGORY_PREFIXES: dict[str, tuple[str, ...]] = {
    "image": ("image/",),
    "video": ("video/",),
    "audio": ("audio/",),
    "pdf": ("application/pdf",),
    "zip": ("application/zip", "application/x-zip", "application/x-zip-compressed"),
}


def _categorize_extension(ext: str) -> Optional[str]:
    """Devuelve la categoría ('image'/'video'/'audio'/'pdf'/'zip') para una
    extensión dada, o ``None`` si la extensión no está categorizada. Se
    mantiene conservador: si la extensión no es una de las conocidas, se
    retorna ``None`` y la validación de alineación se omite (caller debe
    rechazar la extensión primero vía ``ensure_allowed_extension``)."""
    ext = (ext or "").lower().lstrip(".")
    if ext in {"png", "jpg", "jpeg", "gif", "webp"}:
        return "image"
    if ext in {"mp4"}:
        return "video"
    if ext in {"mp3", "wav"}:
        return "audio"
    if ext == "pdf":
        return "pdf"
    if ext == "zip":
        return "zip"
    return None


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


def validate_mime_extension_alignment(
    filename: str, content_type: Optional[str]
) -> None:
    """Valida que el ``content_type`` declarado por el cliente sea coherente
    con la extensión del archivo. Previene el vector donde un binario
    malicioso es renombrado con extensión benigna y un ``Content-Type``
    falsificado. Es defense-in-depth sobre ``ensure_allowed_extension``:
    este último bloquea extensiones no permitidas; aquí bloqueamos
    inconsistencias MIME/extensión sobre extensiones permitidas.

    Categorías explícitas (mirrored from ``_EXTENSION_CATEGORY_PREFIXES``):

      - ``image/*`` → png, jpg, jpeg, gif, webp
      - ``video/*`` → mp4
      - ``audio/*`` → mp3, wav
      - ``application/pdf`` → pdf
      - ``application/zip`` (o x-zip*) → zip

    Caso especial: si la extensión no es categorizable (no debería ocurrir
    porque ``ensure_allowed_extension`` ya filtró), el check se omite. Esto
    asume que ``ensure_allowed_extension`` se llama antes.
    """
    ext = Path(filename).suffix.lower().lstrip(".")
    category = _categorize_extension(ext)
    if category is None:
        # Extensión ya validada por ensure_allowed_extension, así que esto
        # sólo se da cuando alguien pasa explícitamente content_type sin
        # pasar por ensure_allowed_extension. No fallamos en ese caso para
        # no romper callers anterior; podría haber extensiones permitidas
        # fuera del catálogo conocido que aún así sean válidas.
        return
    expected = _EXTENSION_CATEGORY_PREFIXES[category]
    ct = (content_type or "").lower().split(";", 1)[0].strip()
    if not ct:
        raise ValueError(
            "Content-Type requerido para validar coherencia con la extension"
        )
    if not any(ct.startswith(prefix) for prefix in expected):
        raise ValueError(
            f"Content-Type '{content_type}' no coincide con la extension "
            f"'.{ext}' (categoria esperada: {category})"
        )


def save_upload(contents: bytes, filename: str, uploads_dir: str) -> str:
    if len(contents) > MAX_UPLOAD_SIZE:
        raise ValueError("File exceeds maximum size")
    ensure_allowed_extension(filename)
    uploads_path = Path(uploads_dir)
    uploads_path.mkdir(parents=True, exist_ok=True)
    destination = uploads_path / filename
    destination.write_bytes(contents)
    return str(destination)
