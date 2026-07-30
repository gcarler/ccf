"""Mention parsing and resolution for comments.

This module extracts ``@usuario``, ``@email`` and frontend-assisted
``@[Nombre](<uuid>)`` / ``<@uuid>`` tokens from comment text, resolves them
to persona UUIDs, and filters them by scope (sede) and self-mention.

The resolved UUIDs can then be stored in the ``mentions`` JSON column and
passed to ``notify_mention`` for in-app notifications.
"""
from __future__ import annotations

import logging
import re
import uuid
from typing import TYPE_CHECKING, Any, Iterable, List, Set

from sqlalchemy import func

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Frontend-assisted, unambiguous mention formats:
#   @[Juan Pérez](123e4567-e89b-12d3-a456-426614174000)
#   <@123e4567-e89b-12d3-a456-426614174000>
_MENTION_UUID_RE = re.compile(
    r"@\[[^\]]+\]\(([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})\)|"
    r"<@([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})>",
    re.IGNORECASE,
)

# Plain text mentions:
#   @username    -> Usuario.username
#   @user@email.com -> Usuario.email
# Must not match a bare UUID (36 chars with the usual hyphens).
_MENTION_USERNAME_RE = re.compile(
    r"(?<!\w)@([\w_.-]+(?:@[\w_.-]+)?)",
    re.UNICODE,
)

# Hand-written full names like @Juan Pérez. We deliberately match only
# words made of letters (Unicode-friendly) and up to 4 words so we do
# not swallow the rest of the sentence. Matching is case-insensitive;
# resolution later compares against the actual Persona display name.
_MENTION_FULLNAME_RE = re.compile(
    r"(?<!\w)@((?:[^\W\d_]+)(?:\s+(?:[^\W\d_]+)){1,3})",
    re.UNICODE | re.IGNORECASE,
)

# Common Spanish conjunctions / articles that people often write after a
# name. They get trimmed from the end of a full-name match so that
# "@Juan Pérez y" resolves to "Juan Pérez".
_FULLNAME_STOPWORDS = {
    "y",
    "e",
    "ni",
    "o",
    "u",
    "a",
    "en",
    "de",
    "del",
    "al",
    "el",
    "la",
    "los",
    "las",
}


def _to_uuid(val: Any) -> uuid.UUID | None:
    if not val:
        return None
    if isinstance(val, uuid.UUID):
        return val
    try:
        return uuid.UUID(str(val))
    except (ValueError, AttributeError):
        return None


def _is_uuid_shape(token: str) -> bool:
    """Return True if ``token`` looks like a UUID (36 chars, 4 hyphens)."""
    if len(token) != 36 or token.count("-") != 4:
        return False
    try:
        uuid.UUID(token)
        return True
    except ValueError:
        return False


def _normalize_text(token: str) -> str:
    """Normalize a mention token for comparison."""
    return " ".join(token.lower().split())


def _mask_ranges(content: str, ranges: list[tuple[int, int]]) -> str:
    """Replace characters inside ``ranges`` with spaces."""
    chars = list(content)
    for start, end in ranges:
        for i in range(start, end):
            if 0 <= i < len(chars):
                chars[i] = " "
    return "".join(chars)


def extract_mentions(content: str) -> tuple[Set[str], Set[str], Set[str]]:
    """Return (uuid_tokens, username_tokens, fullname_tokens) found in ``content``.

    ``uuid_tokens`` are valid UUID strings extracted from frontend-assisted
    patterns. ``username_tokens`` are the raw strings after ``@`` for
    plain-text usernames/emails. ``fullname_tokens`` are multi-word names
    like ``Juan Pérez``.
    """
    if not content:
        return set(), set(), set()

    # Extract UUID mentions first (they are unambiguous).
    uuid_tokens: Set[str] = set()
    for match in _MENTION_UUID_RE.finditer(content):
        token = match.group(1) or match.group(2)
        if token:
            uuid_tokens.add(token.lower())

    # Extract full-name mentions next. Their spans will be masked so that
    # @Juan inside @Juan Pérez is not also reported as a username. Trailing
    # conjunctions/articles are trimmed so the sentence keeps flowing.
    fullname_matches = list(_MENTION_FULLNAME_RE.finditer(content))
    fullname_tokens: Set[str] = set()
    for match in fullname_matches:
        token = match.group(1)
        if not token:
            continue
        words = token.split()
        while len(words) > 2 and words[-1].lower() in _FULLNAME_STOPWORDS:
            words.pop()
        if words:
            fullname_tokens.add(" ".join(words))
    masked_content = _mask_ranges(
        content, [(m.start(), m.end()) for m in fullname_matches]
    )

    # Extract plain-text usernames/emails from the masked content.
    username_tokens: Set[str] = set()
    for match in _MENTION_USERNAME_RE.finditer(masked_content):
        token = match.group(1)
        if token and not _is_uuid_shape(token):
            username_tokens.add(token)

    return uuid_tokens, username_tokens, fullname_tokens


def _build_display_name(persona: Any) -> str:
    parts = [
        persona.first_name,
        getattr(persona, "second_name", None),
        persona.last_name,
        getattr(persona, "second_last_name", None),
    ]
    return _normalize_text(" ".join(p for p in parts if p))


def resolve_mentions(
    db: "Session",
    content: str,
    payload_mentions: Iterable[Any],
    author_id: Any,
    user_sede: Any,
) -> List[uuid.UUID]:
    """Resolve every mention in ``content`` plus ``payload_mentions`` to
    persona UUIDs, filtered by sede scope and excluding the author.

    Args:
        db: SQLAlchemy session.
        content: comment text that may contain @mentions.
        payload_mentions: explicit list of UUIDs sent by the client (legacy
            or complementary channel). May contain strings or UUIDs.
        author_id: persona UUID of the comment author. Used to exclude
            self-mentions.
        user_sede: actor's sede. ``None`` (superadmin) disables scope filtering.

    Returns:
        A deduplicated list of resolved persona UUIDs sorted for stable tests.
    """
    from backend import models

    uuid_tokens, username_tokens, fullname_tokens = extract_mentions(content)

    # Start with explicit payload mentions and UUID tokens parsed from text.
    candidate_uuids: Set[uuid.UUID] = set()
    for raw in payload_mentions or []:
        parsed = _to_uuid(raw)
        if parsed:
            candidate_uuids.add(parsed)
    for token in uuid_tokens:
        parsed = _to_uuid(token)
        if parsed:
            candidate_uuids.add(parsed)

    # Resolve plain-text usernames / emails against auth_users.
    if username_tokens:
        # CITEXT columns make the lookup case-insensitive.
        users = (
            db.query(models.Usuario)
            .filter(
                models.Usuario.is_active.is_(True),
                models.Usuario.username.in_([t.lower() for t in username_tokens])
                | models.Usuario.email.in_([t.lower() for t in username_tokens]),
            )
            .all()
        )
        for user in users:
            user_uuid = _to_uuid(user.id)
            if user_uuid:
                candidate_uuids.add(user_uuid)
        # Diagnostic log for tokens that did not resolve.
        matched_usernames = {u.username.lower() for u in users}
        matched_emails = {u.email.lower() for u in users}
        for token in username_tokens:
            normalized = _normalize_text(token)
            if normalized not in matched_usernames and normalized not in matched_emails:
                logger.debug("Mention '@%s' could not be resolved to a user", token)

    # Resolve multi-word names like "Juan Pérez" against personas.
    if fullname_tokens:
        normalized_tokens = {_normalize_text(t) for t in fullname_tokens}

        q = db.query(models.Persona)
        if user_sede is not None:
            q = q.filter(models.Persona.sede_id == user_sede)

        # Load only personas whose first name matches any of the first words
        # of the requested tokens. This keeps the query small and uses an
        # indexed column, then we finish matching in Python.
        first_words = {t.split()[0].lower() for t in normalized_tokens if t.split()}
        if first_words:
            q = q.filter(
                func.lower(models.Persona.first_name).in_(list(first_words))
            )
        personas = q.all()

        matched_ids: Set[uuid.UUID] = set()
        resolved_names: Set[str] = set()
        for persona in personas:
            display = _build_display_name(persona)
            resolved_names.add(display)
            if display in normalized_tokens:
                persona_uuid = _to_uuid(persona.id)
                if persona_uuid:
                    matched_ids.add(persona_uuid)

        for persona_id in matched_ids:
            candidate_uuids.add(persona_id)

        # Diagnostic: log tokens that did not resolve.
        for token in fullname_tokens:
            if _normalize_text(token) not in resolved_names:
                logger.debug("Full-name mention '@%s' could not be resolved", token)

    if not candidate_uuids:
        return []

    # Scope filter (Axioma 3): keep only personas within the actor's sede.
    # Superadmin (user_sede is None) bypasses the filter.
    q = db.query(models.Persona.id).filter(models.Persona.id.in_(candidate_uuids))
    if user_sede is not None:
        q = q.filter(models.Persona.sede_id == user_sede)
    scoped: Set[uuid.UUID] = {row[0] for row in q.all()}

    # Self-exclusion.
    author_uuid = _to_uuid(author_id)
    scoped.discard(author_uuid)

    return sorted(scoped)
