"""Domain-specific exceptions for CCF backend modules.

Each module should define its own exception hierarchy rooted in a
module-specific base (e.g. ``CmsError``). The global exception handler
in ``app.py`` maps these domain exceptions to HTTP responses via their
``status_code`` attribute, eliminating the need for ad-hoc
``raise HTTPException(...)`` calls directly in endpoint code.

Usage::

    from backend.exceptions.cms import CmsNotFoundError

    raise CmsNotFoundError("Page not found")
    # → HTTP 404 with ``{"detail": "Page not found"}``
"""
