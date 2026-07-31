"""Unit tests for the lazy (PEP 562) re-export in scripts/seed_public_content.py.

Regression guard for the refactor in commit ``6bf5e81e``:

* ``import seed_public_content`` must NOT pull in the backend stack: neither
  ``backend`` nor ``ensure_public_content_blocks`` may appear in ``sys.modules``.
* ``BLOCKS`` resolves lazily through the module-level ``__getattr__``: the
  canonical catalog (and with it ``backend.models`` / ``SessionLocal``) is only
  imported once ``BLOCKS`` is actually accessed.
* The resolved ``BLOCKS`` is the SAME object as
  ``ensure_public_content_blocks.BLOCKS`` (single canonical source).
* Unknown attributes raise ``AttributeError`` and ``getattr(..., default)``
  still works — the exact pattern used by the seeder
  (``deepcopy(getattr(_sp, "BLOCKS", {}))`` in
  ``scripts/seed_public_cms_v2_sections.py``).

Because the pytest process already imports ``backend`` (see ``tests/conftest.py``),
the "no backend on import" assertions must run in a FRESH interpreter via
subprocess (precedent: ``tests/test_canonical_baseline.py``).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

_PREAMBLE = "import sys\nsys.path.insert(0, 'scripts')\nimport seed_public_content as sp\n"


def _run_fresh(code: str) -> str:
    """Run ``code`` in a fresh interpreter with a hermetic, test-like env."""
    env = os.environ.copy()
    env["ENVIRONMENT"] = "test"
    env["DATABASE_URL"] = "sqlite:///:memory:"
    env["database_url"] = "sqlite:///:memory:"
    env["PYTHONUNBUFFERED"] = "1"
    try:
        proc = subprocess.run(
            [sys.executable, "-c", code],
            cwd=str(ROOT),
            env=env,
            text=True,
            capture_output=True,
            check=True,
            timeout=120,
        )
    except subprocess.CalledProcessError as exc:
        raise AssertionError(f"subprocess failed (exit {exc.returncode}):\n{exc.stderr}") from exc
    return proc.stdout.strip()


class TestImportDoesNotLoadBackend:
    def test_plain_import_leaves_backend_and_canonical_unloaded(self):
        """Importing the module alone must be side-effect free."""
        code = _PREAMBLE + (
            "print('backend' in sys.modules)\n"
            "print('ensure_public_content_blocks' in sys.modules)\n"
            "print(callable(sp.__getattr__))\n"
        )
        assert _run_fresh(code) == "False\nFalse\nTrue"

    def test_blocks_resolves_lazily_via_getattr(self):
        """BLOCKS only triggers the canonical/backend import on access."""
        code = _PREAMBLE + (
            "before_backend = 'backend' in sys.modules\n"
            "before_canonical = 'ensure_public_content_blocks' in sys.modules\n"
            "blocks = sp.BLOCKS\n"
            "import ensure_public_content_blocks as ep\n"
            "print(before_backend, before_canonical)\n"
            "print(blocks is ep.BLOCKS)\n"
            "print(len(blocks))\n"
            "print('backend' in sys.modules)\n"
        )
        out = _run_fresh(code).splitlines()
        assert out[0] == "False False", "BLOCKS access must be the first trigger"
        assert out[1] == "True", "BLOCKS must be the same object as the canonical catalog"
        assert int(out[2]) >= 20, "the full canonical catalog must resolve"
        assert out[3] == "True", "backend must be imported only after BLOCKS access"

    def test_getattr_with_default_matches_seeder_consumer_pattern(self):
        """``getattr(sp, "BLOCKS", {})`` resolves the canonical object."""
        code = _PREAMBLE + (
            "import ensure_public_content_blocks as ep\n"
            "print(getattr(sp, 'BLOCKS', {}) is ep.BLOCKS)\n"
            "print(getattr(sp, 'NOTHING_HERE', 'fallback'))\n"
        )
        assert _run_fresh(code) == "True\nfallback"


class TestGetattrSemantics:
    def test_unknown_attribute_raises_attribute_error(self):
        from scripts import seed_public_content as sp

        with pytest.raises(AttributeError):
            _ = sp.DOES_NOT_EXIST_ATTR
        assert getattr(sp, "DOES_NOT_EXIST_ATTR", "fallback") == "fallback"

    def test_blocks_is_consistent_singleton(self):
        """Every access resolves the SAME canonical object (same import name).

        Identity across naming schemes is intentionally NOT asserted here: the
        lazy ``__getattr__`` imports ``ensure_public_content_blocks`` under its
        top-level name, which is a distinct module instance from a
        ``scripts.ensure_public_content_blocks`` package import — same content,
        different object. The cross-module identity is verified in the fresh
        subprocess tests where both names resolve top-level.
        """
        from scripts import seed_public_content as sp

        first = sp.BLOCKS
        assert sp.BLOCKS is first, "repeated access must return the same object"
        for key in ("ccf_home_hero", "ccf_pastores_feed", "ccf_nav_items"):
            assert key in first, f"canonical catalog must expose {key!r}"
