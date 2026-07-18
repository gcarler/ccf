"""Shared utilities for crud modules."""

import datetime as dt
import uuid as _uuid

from fastapi import HTTPException


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
