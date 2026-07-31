"""CMS domain exceptions.

Replace raw ``raise HTTPException(...)`` calls with typed domain exceptions
so that endpoints express intent (\"not found\", \"conflict\") rather than
HTTP plumbing (404, 409). The global exception handler in ``app.py`` maps
these to the appropriate HTTP response automatically.

Pattern::

    from backend.exceptions.cms import CmsNotFoundError

    def get_page(slug: str):
        page = find_page(slug)
        if not page:
            raise CmsNotFoundError("Page not found", slug=slug)
        return page
"""

from __future__ import annotations


class CmsError(Exception):
    """Base exception for all CMS domain errors.

    Subclasses set ``status_code`` to the HTTP status that should be
    returned; the global exception handler reads this attribute.
    """

    status_code: int = 500
    detail: str = "Internal CMS error"
    _error_code: str | None = None

    def __init__(
        self,
        detail: str | None = None,
        status_code: int | None = None,
        error_code: str | None = None,
    ):
        if detail is not None:
            self.detail = detail
        if status_code is not None:
            self.status_code = status_code
        if error_code is not None:
            self._error_code = error_code
        super().__init__(self.detail)

    @property
    def error_code(self) -> str | None:
        return self._error_code

    def to_dict(self) -> dict:
        d: dict[str, object] = {"detail": self.detail}
        if self._error_code:
            d["error_code"] = self._error_code
        return d


# ── 404: Resource not found ─────────────────────────────────────────────────


class CmsNotFoundError(CmsError):
    """Raised when a CMS resource (page, section, media, etc.) is not found."""

    status_code: int = 404
    detail: str = "Resource not found"


class PageNotFoundError(CmsNotFoundError):
    detail: str = "Page not found"


class SectionNotFoundError(CmsNotFoundError):
    detail: str = "Section not found"


class SiteNotFoundError(CmsNotFoundError):
    detail: str = "Site not found"


class ThemeNotFoundError(CmsNotFoundError):
    detail: str = "Theme not found"


class MenuNotFoundError(CmsNotFoundError):
    detail: str = "Menu not found"


class MenuItemNotFoundError(CmsNotFoundError):
    detail: str = "Menu item not found"


class PostNotFoundError(CmsNotFoundError):
    detail: str = "Post not found"


class CategoryNotFoundError(CmsNotFoundError):
    detail: str = "Category not found"


class TagNotFoundError(CmsNotFoundError):
    detail: str = "Tag not found"


class MediaNotFoundError(CmsNotFoundError):
    detail: str = "Media not found"


class BlockNotFoundError(CmsNotFoundError):
    detail: str = "Global block not found"


class VersionNotFoundError(CmsNotFoundError):
    detail: str = "Version not found"


class PopupNotFoundError(CmsNotFoundError):
    detail: str = "Popup not found"


class FormNotFoundError(CmsNotFoundError):
    detail: str = "Form not found"


class NewsletterNotFoundError(CmsNotFoundError):
    detail: str = "Newsletter not found"


class SubscriberNotFoundError(CmsNotFoundError):
    detail: str = "Subscriber not found"


class AbTestNotFoundError(CmsNotFoundError):
    detail: str = "A/B test not found"


# ── 409: Conflict ────────────────────────────────────────────────────────────


class CmsConflictError(CmsError):
    """Raised when an operation conflicts with existing data (duplicate slug, etc.)."""

    status_code: int = 409
    detail: str = "Resource conflict"


class SlugConflictError(CmsConflictError):
    """Raised when a slug / key already exists."""

    detail: str = "Slug already exists"


class SectionConflictError(CmsConflictError):
    detail: str = "Section conflict"


class MenuKeyConflictError(CmsConflictError):
    detail: str = "Menu key already exists"


class MenuItemConflictError(CmsConflictError):
    detail: str = "Menu item conflict"


# ── 422: Validation error ────────────────────────────────────────────────────


class CmsValidationError(CmsError):
    """Raised when request data fails validation."""

    status_code: int = 422
    detail: str = "Validation error"


class InvalidSlugError(CmsValidationError):
    detail: str = "Slug is required"


class InvalidStatusError(CmsValidationError):
    detail: str = "Invalid status"


class UnsupportedSectionTypeError(CmsValidationError):
    detail: str = "Unsupported section type"


class UnsupportedSectionStatusError(CmsValidationError):
    detail: str = "Unsupported section status"


class InvalidWorkflowActionError(CmsValidationError):
    detail: str = "Invalid workflow action"


class DraftRequiredError(CmsValidationError):
    detail: str = "New pages must start in draft"


class SlugMismatchError(CmsValidationError):
    detail: str = "New slug must differ from source slug"


class SectionTypeAlreadyExistsError(CmsValidationError):
    detail: str = "Section type already exists"


class SiteKeyAlreadyExistsError(CmsConflictError):
    detail: str = "Site key already exists"


class SectionTypeNotFoundError(CmsNotFoundError):
    detail: str = "Section type not found"


# ── 403: Permission error ────────────────────────────────────────────────────


class CmsPermissionError(CmsError):
    """Raised when the actor lacks the required role for an operation."""

    status_code: int = 403
    detail: str = "Permission denied"


# ── 503: Service unavailable ─────────────────────────────────────────────────


class CmsServiceUnavailableError(CmsError):
    """Raised when a required dependency (e.g. Pillow) is not available."""

    status_code: int = 503
    detail: str = "Service unavailable"


# ── Aliases mapped to consistent HTTP status codes ────────────────────────────

CmsNotFound = CmsNotFoundError
CmsPermissionDenied = CmsPermissionError
CmsConflict = CmsConflictError
