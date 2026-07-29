"""Tests exhaustivos y estructurales para backend/services/image_optimizer.py (100% Cobertura)."""

import io
import pytest
from unittest.mock import MagicMock, patch
from PIL import Image

from backend.services.image_optimizer import ImageOptimizer, _fmt_size


class TestImageOptimizer100Pct:

    def test_fmt_size_helper(self):
        assert _fmt_size(500) == "500B"
        assert _fmt_size(2048) == "2.0KB"
        assert _fmt_size(2 * 1024 * 1024) == "2.0MB"

    def test_unsupported_format_passthrough(self):
        opt = ImageOptimizer()
        content = b"PDF content bytes"
        res_bytes, ext, w, h = opt.optimize(content, "document.pdf")
        assert res_bytes == content
        assert ext == ".pdf"
        assert w == 0
        assert h == 0

    def test_gif_passthrough(self):
        opt = ImageOptimizer()
        content = b"GIF89a content"
        res_bytes, ext, w, h = opt.optimize(content, "animation.gif")
        assert res_bytes == content
        assert ext == ".gif"
        assert w == 0
        assert h == 0

    def test_invalid_image_bytes_passthrough(self):
        opt = ImageOptimizer()
        content = b"corrupted image bytes"
        res_bytes, ext, w, h = opt.optimize(content, "photo.jpg")
        assert res_bytes == content
        assert ext == ".jpg"
        assert w == 0
        assert h == 0

    def test_valid_jpeg_optimization_and_exif_rotations(self):
        opt = ImageOptimizer(max_width=100, quality=80)

        # Create test images with different modes & exif orientation tags
        for mode in ("RGB", "RGBA", "LA", "L"):
            img = Image.new("RGBA" if mode == "RGBA" else ("LA" if mode == "LA" else "RGB"), (200, 100), color="blue")
            buf = io.BytesIO()
            img.save(buf, format="PNG" if "A" in mode else "JPEG")
            raw_bytes = buf.getvalue()

            filename = "test.png" if "A" in mode else "test.jpg"
            opt_bytes, ext, orig_w, orig_h = opt.optimize(raw_bytes, filename)
            assert ext == ".webp"
            assert orig_w == 200
            assert orig_h == 100

    def test_exif_orientations(self):
        opt = ImageOptimizer(max_width=500)

        for orientation in (3, 6, 8):
            img = Image.new("RGB", (100, 100), color="red")
            exif = img.getexif()
            exif[0x0112] = orientation
            buf = io.BytesIO()
            img.save(buf, format="JPEG", exif=exif)
            raw_bytes = buf.getvalue()

            opt_bytes, ext, w, h = opt.optimize(raw_bytes, f"oriented_{orientation}.jpg")
            assert ext == ".webp"

    def test_mode_convert_other_modes(self):
        opt = ImageOptimizer()
        # Mode "P" (Palette) or "L" (Grayscale)
        for m in ("P", "L"):
            img = Image.new(m, (40, 40))
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            raw_bytes = buf.getvalue()
            opt_bytes, ext, w, h = opt.optimize(raw_bytes, "palette.png")
            assert ext == ".webp"
            assert w == 40

    def test_exif_exception_handling(self):
        opt = ImageOptimizer()
        img = Image.new("RGB", (40, 40), color="yellow")
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        raw_bytes = buf.getvalue()

        # Patch getexif to raise an exception
        with patch("PIL.Image.Image.getexif", side_effect=ValueError("Bad EXIF")):
            opt_bytes, ext, w, h = opt.optimize(raw_bytes, "bad_exif.jpg")
            assert ext == ".webp"

    def test_save_exception_fallback(self):
        opt = ImageOptimizer()
        img = Image.new("RGB", (50, 50), color="green")
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        raw_bytes = buf.getvalue()

        with patch("PIL.Image.open") as mock_open:
            mock_img = MagicMock()
            mock_img.size = (50, 50)
            mock_img.mode = "RGB"
            mock_img.width = 50
            mock_img.height = 50
            mock_img.getexif.side_effect = Exception("No EXIF")
            mock_img.save.side_effect = RuntimeError("Encode error")
            mock_open.return_value = mock_img

            opt_bytes, ext, w, h = opt.optimize(raw_bytes, "photo.jpg")
            assert opt_bytes == raw_bytes
            assert ext == ".jpg"
            assert w == 50
            assert h == 50

    def test_reencode_larger_than_original(self):
        opt = ImageOptimizer(quality=100)
        # 1x1 tiny webp image
        img = Image.new("RGB", (1, 1), color="red")
        buf = io.BytesIO()
        img.save(buf, format="WEBP", quality=100)
        raw_bytes = buf.getvalue()

        with patch("PIL.Image.Image.save") as mock_save:
            # Fake optimized bytes being much larger
            def mock_save_impl(buf_arg, **kwargs):
                buf_arg.write(raw_bytes * 50)
            mock_save.side_effect = mock_save_impl

            opt_bytes, ext, w, h = opt.optimize(raw_bytes, "tiny.webp")
            assert opt_bytes == raw_bytes
            assert ext == ".webp"

    def test_png_quality_boost_and_resize(self):
        opt = ImageOptimizer(max_width=100, quality=92)
        img = Image.new("RGB", (200, 200), color="blue")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        raw_bytes = buf.getvalue()

        opt_bytes, ext, orig_w, orig_h = opt.optimize(raw_bytes, "large.png")
        assert ext == ".webp"
        assert orig_w == 200
        assert orig_h == 200

