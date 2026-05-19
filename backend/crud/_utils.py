"""Shared utilities for crud modules."""
import datetime as dt


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.UTC).replace(tzinfo=None)


def analyze_pastoral_priority(notes: str) -> str:
    """Motor de IA Optimus Brain v1: Heurística de Priorización Pastoral."""
    if not notes:
        return "NORMAL"

    notes_lower = notes.lower()

    critical_keywords = [
        "suicidio", "atentado", "abuso", "depresion profunda",
        "violencia", "riesgo", "emergencia", "auxilio", "ayuda ya"
    ]
    if any(k in notes_lower for k in critical_keywords):
        return "URGENTE"

    high_keywords = [
        "conflicto familiar", "separacion", "crisis", "enfermedad grave",
        "perdida de fe", "soledad", "problemas economicos"
    ]
    if any(k in notes_lower for k in high_keywords):
        return "ALTA"

    return "NORMAL"


def analyze_pastoral_sentiment(content: str):
    """Motor de IA Optimus Brain v2: Análisis Heurístico de Sentimiento."""
    if not content:
        return 0.0, "NEUTRAL"

    text = content.lower()

    positive_words = ["aliento", "bendecido", "paz", "gozo", "agradecido", "crecimiento", "victoria", "fe", "esperanza"]
    negative_words = ["triste", "derrota", "angustia", "problema", "pelea", "dolor", "soledad", "duda", "miedo"]

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
