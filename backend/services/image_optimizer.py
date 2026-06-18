"""Image optimization service.

Converts uploaded images to WebP (or keeps original JPEG/PNG) with
automatic compression, resizing, and EXIF-stripping.

Uses Pillow under the hood.  The goal is a balance of quality vs. file size
that is appropriate for the web — no user-perceptible quality loss, but
dramatically smaller files than camera-origin uploads.

Usage
-----
    optimizer = ImageOptimizer()
    webp_bytes = optimizer.optimize(raw_bytes, max_width=1920, quality=82)
    # Returns (optimized_bytes, "webp", original_width, original_height)
"""

from __future__ import annotations

import io
import logging
import os
from typing import Tuple

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
_DEFAULT_MAX_WIDTH = 1920
_DEFAULT_QUALITY = 82  # 82 % — visually lossless for most content


class ImageOptimizer:
    """Optimize raster images (JPEG, PNG, WebP) for the web.

    The output is always **WebP** unless the input is a GIF (returned as-is)
    or an already-optimized WebP smaller than the re-encode would produce.
    """

    # Raster formats we can process
    SUPPORTED_INPUT = frozenset({".jpg", ".jpeg", ".png", ".webp", ".gif"})

    def __init__(self, max_width: int = _DEFAULT_MAX_WIDTH,
                 quality: int = _DEFAULT_QUALITY):
        self.max_width = max_width
        self.quality = quality

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def optimize(
        self,
        content: bytes,
        original_filename: str,
    ) -> Tuple[bytes, str, int, int]:
        """Return ``(optimized_bytes, output_ext, width, height)``.

        *output_ext* is ``".webp"`` for raster images (GIF passthrough keeps
        ``".gif"``).  *width* and *height* are the **original** dimensions.
        """
        from PIL import Image

        ext = os.path.splitext(original_filename)[1].lower()

        if ext not in self.SUPPORTED_INPUT:
            # Unsupported → pass through untouched (e.g. PDF, MP4, ZIP)
            log.info("Unsupported image format '%s' — passthrough", ext)
            return content, ext, 0, 0

        if ext == ".gif":
            # Animated GIF → passthrough (WebP animation support exists but
            # adds complexity; keep GIFs simple for now)
            return content, ext, 0, 0

        # --- Decode ---
        try:
            img = Image.open(io.BytesIO(content))
        except Exception:
            log.warning("Cannot decode image '%s' — passthrough",
                        original_filename)
            return content, ext, 0, 0

        original_w, original_h = img.size

        # --- EXIF orientation ---
        # Some cameras / phones embed orientation in EXIF; apply it so the
        # saved image is correctly oriented.
        try:
            exif = img.getexif()
            orientation = exif.get(0x0112, 1)  # tag: Orientation
            if orientation == 3:
                img = img.rotate(180, expand=True)
            elif orientation == 6:
                img = img.rotate(270, expand=True)
            elif orientation == 8:
                img = img.rotate(90, expand=True)
        except Exception:
            pass  # best-effort orientation fix

        # --- RGBA → RGB  (WebP supports alpha, but JPEG doesn't — we output
        # WebP so alpha is fine; still strip alpha for truly opaque images)
        if img.mode in ("RGBA", "LA"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)  # type: ignore[arg-type]
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")

        # --- Resize (preserve aspect ratio) ---
        if img.width > self.max_width:
            ratio = self.max_width / img.width
            new_h = int(img.height * ratio)
            img = img.resize((self.max_width, new_h), Image.LANCZOS)

        # --- Encode to WebP ---
        buf = io.BytesIO()
        save_kwargs: dict = {"format": "WEBP", "quality": self.quality}

        if ext == ".png":
            # PNG files often benefit from a slightly higher quality setting
            # because they start with a lossless source; 85 % is a good
            # sweet-spot.
            save_kwargs["quality"] = min(self.quality + 5, 95)

        try:
            img.save(buf, **save_kwargs)
        except Exception:
            log.warning("WebP encode failed for '%s' — fallback to original",
                        original_filename)
            return content, ext, original_w, original_h

        optimized = buf.getvalue()

        # --- Sanity check: never return something *larger* than the original ---
        # For WebP input that is already well-compressed, re-encoding can
        # bloat the file.  If that happens, return the original.
        if len(optimized) > len(content) * 1.05:  # 5 % tolerance
            log.info("Re-encoded image is larger than original — keeping "
                     "original for '%s'", original_filename)
            return content, ext, original_w, original_h

        log.info(
            "Optimized '%s': %d×%d → %d×%d,  %s → %s  (%.1f× smaller)",
            original_filename,
            original_w, original_h,
            img.width, img.height,
            _fmt_size(len(content)),
            _fmt_size(len(optimized)),
            len(content) / max(len(optimized), 1),
        )
        return optimized, ".webp", original_w, original_h


def _fmt_size(n: int) -> str:
    if n < 1024:
        return f"{n}B"
    elif n < 1024 * 1024:
        return f"{n / 1024:.1f}KB"
    return f"{n / (1024 * 1024):.1f}MB"
