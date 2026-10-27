"""Explicit opt-in to structured HTTP error details without flattening fields."""

from fastapi import HTTPException


class StructuredHTTPException(HTTPException):
    """An API contract whose ``detail`` is a JSON object, rather than a string."""
