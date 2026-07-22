"""Lightweight whitelist-based HTML sanitizer.

This module avoids an extra production dependency by using only the Python
standard library. It parses HTML, keeps a conservative whitelist of tags and
attributes, strips everything else, and normalises ``href``/``src`` URLs to
prevent javascript: pseudo-protocol attacks.

Intended use: sanitise user-provided HTML stored in ``CmsSection.props_json``
before it reaches the public site rendered via ``dangerouslySetInnerHTML``.
"""
from __future__ import annotations

import re
import urllib.parse
from html.parser import HTMLParser

ALLOWED_TAGS = {
    "a",
    "b",
    "br",
    "blockquote",
    "code",
    "div",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "i",
    "img",
    "li",
    "ol",
    "p",
    "pre",
    "s",
    "span",
    "strong",
    "sub",
    "sup",
    "u",
    "ul",
}

ALLOWED_ATTRS = {
    "a": {"href", "title", "target", "rel"},
    "img": {"src", "alt", "title", "width", "height", "loading"},
    "blockquote": {"cite"},
    "q": {"cite"},
    "div": {"class"},
    "span": {"class"},
    "p": {"class"},
    "ol": {"class"},
    "ul": {"class"},
    "li": {"class"},
}

_ALLOWED_SCHEMES = {"http", "https", "mailto", "tel"}


def _normalise_url(value: str | None, attr_name: str) -> str | None:
    """Reject javascript:/data: URLs, unknown schemes and protocol-relative URLs."""
    if value is None:
        return None
    value = value.strip()
    if not value:
        return value
    parsed = urllib.parse.urlparse(value)
    scheme = parsed.scheme.lower() if parsed.scheme else ""
    if scheme:
        if scheme in {"javascript", "data"}:
            return None
        # For href/src, only http/https and mailto/tel are allowed.
        if attr_name in {"href", "src"}:
            if scheme not in _ALLOWED_SCHEMES:
                return None
        else:
            if scheme not in _ALLOWED_SCHEMES:
                return None
    if attr_name in {"href", "src"}:
        if not parsed.scheme and value.startswith("//"):
            # protocol-relative URLs are disallowed to prevent leakage
            return None
    return value


class _Sanitiser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.parts: list[str] = []
        self._ignore_until: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._ignore_until:
            return
        if tag not in ALLOWED_TAGS:
            # Disallowed tag: skip its content entirely.
            self._ignore_until = tag
            return
        allowed_attrs = ALLOWED_ATTRS.get(tag, set())
        attr_parts: list[str] = []
        for attr_name, attr_value in attrs:
            if attr_name not in allowed_attrs:
                continue
            normalised = _normalise_url(attr_value, attr_name) if attr_name in {"href", "src"} else attr_value
            if normalised is None:
                continue
            # Escape quotes to avoid attribute injection.
            safe_value = normalised.replace("\"", "&quot;").replace("'", "&#x27;")
            attr_parts.append(f'{attr_name}="{safe_value}"')
        space = " " + " ".join(attr_parts) if attr_parts else ""
        self.parts.append(f"<{tag}{space}>")

    def handle_endtag(self, tag: str) -> None:
        if self._ignore_until:
            if tag == self._ignore_until:
                self._ignore_until = None
            return
        if tag in ALLOWED_TAGS:
            self.parts.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        if self._ignore_until:
            return
        self.parts.append(data)

    def handle_entityref(self, name: str) -> None:
        if self._ignore_until:
            return
        self.parts.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        if self._ignore_until:
            return
        self.parts.append(f"&#{name};")


def sanitize_html(value: str) -> str:
    """Sanitise raw HTML using a conservative whitelist.

    Args:
        value: Raw HTML string.

    Returns:
        Sanitised HTML string with only allowed tags/attributes.
    """
    if not value:
        return value
    parser = _Sanitiser()
    parser.feed(value)
    return "".join(parser.parts)


def sanitize_props_html(props: dict[str, object], *, path: str = "") -> dict[str, object]:
    """Recursively sanitise string fields that look like HTML in section props.

    The function is conservative: it only touches string values whose key names
    strongly suggest HTML content (``content_html``, ``body``, ``content``,
    ``summary``, ``answer``, etc.) or that already contain HTML tags.
    """
    html_like_keys = {
        "content_html",
        "body",
        "content",
        "summary",
        "answer",
        "description",
        "empty_description",
        "empty_title",
        "featured_badge",
        "reserve_cta",
        "search_placeholder",
        "message_placeholder",
        "name_placeholder",
        "phone_placeholder",
        "request_placeholder",
        "submit_label",
        "success_message",
        "cta_label",
        "courses_description",
        "courses_title",
        "empty_message",
        "brand_description",
        "location_label",
        "newsletter_label",
        "copyright",
        "label",
    }
    result: dict[str, object] = {}
    for key, val in props.items():
        if isinstance(val, str):
            is_html_like = key in html_like_keys or re.search(r"<[^>]+>", val) is not None
            result[key] = sanitize_html(val) if is_html_like else val
        elif isinstance(val, dict):
            result[key] = sanitize_props_html(val, path=f"{path}.{key}")
        elif isinstance(val, list):
            cleaned: list[object] = []
            for item in val:
                if isinstance(item, dict):
                    cleaned.append(sanitize_props_html(item, path=f"{path}.{key}[]"))
                elif isinstance(item, str):
                    cleaned.append(sanitize_html(item) if re.search(r"<[^>]+>", item) else item)
                else:
                    cleaned.append(item)
            result[key] = cleaned
        else:
            result[key] = val
    return result
