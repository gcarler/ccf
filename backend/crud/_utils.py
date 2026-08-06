"""Shared utilities for crud modules."""

import datetime as dt
import logging
import uuid as _uuid

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

_logger = logging.getLogger(__name__)


def _is_unique_violation(exc: IntegrityError) -> bool:
    """Detector de violación UNIQUE compartido entre CRUD/API layers.

    Distingue una ``IntegrityError`` de UNIQUE-key (Postgres ``pgcode ==
    '23505'`` o SQLite ``"UNIQUE constraint failed"``) de otras clases
    (NOT NULL, FK, check constraint). Esto permite que los commit helpers
    conviertan conflictos concurrentes de creación en ``409`` en vez de
    propagarse como ``500``, sin enmascarar bugs genuinos NOT NULL / FK /
    check como falsos 409.

    Single source of truth para el filtro de unique-violation — antes
    este patrón vivía triplicado (``crud/cms.py::_commit_or_conflict``,
    ``api/cms_v2/_shared.py::_commit_or_raise_conflict`` y
    ``crud/academy.py::_commit_or_raise_conflict``). Los tres callers
    ahora delegan aquí el filtro y deciden independentemente si
    retornar ``bool`` o levantar ``HTTPException``/``CmsConflictError``.
    """
    orig = getattr(exc, "orig", None)
    if orig is None:
        return False
    pgcode = getattr(orig, "pgcode", None)
    if pgcode == "23505":
        return True
    # SQLite expone unique violations via IntegrityError message.
    return "UNIQUE constraint failed" in str(orig)


def _commit_or_conflict_bool(db) -> bool:
    """Commit helper que retorna ``True`` on éxito y ``False`` si la
    ``IntegrityError`` es de UNIQUE-key; cualquier otra ``IntegrityError``
    se re-raise post-rollback. Origen canónico:
    ``crud/cms.py::_commit_or_conflict`` (M-12 defensivo) ahora delega aquí.
    """
    try:
        db.commit()
        return True
    except IntegrityError as exc:
        db.rollback()
        if not _is_unique_violation(exc):
            raise
        _logger.debug("Swallowed concurrent create unique-key conflict: %s", exc)
        return False


def _commit_or_raise_409(db, detail: str = "resource already exists") -> None:
    """Commit helper que levanta ``HTTPException(409)`` si la
    ``IntegrityError`` es de UNIQUE-key; cualquier otra se re-raise
    post-rollback. Origen canónico: ``crud/academy.py::_commit_or_raise_conflict``.
    """
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if not _is_unique_violation(exc):
            raise
        _logger.debug("Swallowed concurrent create unique-key conflict: %s", exc)
        raise HTTPException(status_code=409, detail=detail)


def _to_uuid(val) -> _uuid.UUID:
    if isinstance(val, _uuid.UUID):
        return val
    return _uuid.UUID(str(val))


def _coerce_uuid_or_404(value, detail: str = "Resource not found") -> _uuid.UUID:
    """UUID coercion con 404 existence-leak safe ante input malformado.

    Antes de cualquier query SQLA sobre un UUID de cliente, normalizamos
    y validamos el shape. Un UUID malformado NO llega al motor de BD, lo
    que cierra el vector 500 cuando el cliente envía basura. El ``detail``
    retornado es neutro: no revela si el recurso existe en otra sede o
    directamente no existe (existence-leak safe).

    Compartir este helper entre ``crud/evangelism.py`` y los API helpers
    evita drift y mantiene una sola política de error 404 para todos los
    módulos multi-tenant (CMS, CRM, Evangelismo).
    """
    try:
        return _uuid.UUID(str(value))
    except (TypeError, ValueError, AttributeError):
        raise HTTPException(status_code=404, detail=detail)


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def analyze_pastoral_priority(notes: str) -> str:
    """Motor de IA Optimus Brain v1: Heurística de Priorización Pastoral."""
    if not notes:
        return "NORMAL"

    notes_lower = notes.lower()

    critical_keywords = [
        "suicidio",
        "atentado",
        "abuso",
        "depresion profunda",
        "violencia",
        "riesgo",
        "emergencia",
        "auxilio",
        "ayuda ya",
    ]
    if any(k in notes_lower for k in critical_keywords):
        return "URGENTE"

    high_keywords = [
        "conflicto familiar",
        "separacion",
        "crisis",
        "enfermedad grave",
        "perdida de fe",
        "soledad",
        "problemas economicos",
    ]
    if any(k in notes_lower for k in high_keywords):
        return "ALTA"

    return "NORMAL"


def analyze_pastoral_sentiment(content: str):
    """Motor de IA Optimus Brain v2: Análisis Heurístico de Sentimiento."""
    if not content:
        return 0.0, "NEUTRAL"

    text = content.lower()

    positive_words = [
        "aliento",
        "bendecido",
        "paz",
        "gozo",
        "agradecido",
        "crecimiento",
        "victoria",
        "fe",
        "esperanza",
    ]
    negative_words = [
        "triste",
        "derrota",
        "angustia",
        "problema",
        "pelea",
        "dolor",
        "soledad",
        "duda",
        "miedo",
    ]

    pos_count = sum(1 for w in positive_words if w in text)
    neg_count = sum(1 for w in negative_words if w in text)

    score = (pos_count - neg_count) / (max(pos_count + neg_count, 1))

    if score > 0.1:
        label = "POSITIVE"
    elif score < -0.1:
        label = "NEGATIVE"
    else:
        label = "NEUTRAL"

    return round(score, 2), label


def _slugify(value: str) -> str:
    """Normalize a string to a URL-safe slug.

    Shared utility used by CMS, Wiki, and Evangelism modules.
    """
    import unicodedata

    text = unicodedata.normalize("NFD", str(value or "").strip().lower())
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    cleaned = []
    previous_dash = False
    for ch in text:
        if ch.isalnum():
            cleaned.append(ch)
            previous_dash = False
        elif not previous_dash:
            cleaned.append("-")
            previous_dash = True
    return "".join(cleaned).strip("-")
