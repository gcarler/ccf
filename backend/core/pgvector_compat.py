"""pgvector compatibility module for PostgreSQL and SQLite test fallbacks."""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Sequence

import sqlalchemy as sa
from sqlalchemy.types import JSON, TypeDecorator

try:
    from pgvector.sqlalchemy import Vector

    PGVECTOR_AVAILABLE = True
except ImportError:
    PGVECTOR_AVAILABLE = False
    Vector = None


class VectorEmbedding(TypeDecorator):
    """Dual-dialect vector embedding type for pgvector / SQLite test fallback.

    On PostgreSQL, renders as native `vector(dim)`.
    On SQLite and other engines, falls back to `JSON`.
    """

    impl = JSON
    cache_ok = True

    def __init__(self, dim: int = 1536, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.dim = dim

    def load_dialect_impl(self, dialect: sa.engine.Dialect):
        if dialect.name == "postgresql" and PGVECTOR_AVAILABLE and Vector is not None:
            return dialect.type_descriptor(Vector(self.dim))
        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value: Any, dialect: sa.engine.Dialect) -> Any:
        if value is None:
            return None
        if dialect.name == "postgresql" and PGVECTOR_AVAILABLE:
            if isinstance(value, (list, tuple)):
                return list(value)
            return value
        if isinstance(value, (list, tuple)):
            return list(value)
        return value

    def process_result_value(self, value: Any, dialect: sa.engine.Dialect) -> Any:
        if value is None:
            return None
        if isinstance(value, str):
            try:
                return json.loads(value)
            except Exception:
                return value
        return value


def generate_text_embedding(text: str, dim: int = 1536) -> list[float]:
    """Generate a normalized 1536-dimensional semantic embedding vector for text.

    Uses deterministic token hashing with multi-seed projection and L2 normalization.
    """
    if not text:
        return [0.0] * dim
    clean_text = str(text).strip().lower()
    tokens = clean_text.split()
    if not tokens:
        return [0.0] * dim

    vec = [0.0] * dim
    for i, token in enumerate(tokens):
        for seed in (13, 37, 73, 101, 149, 197):
            h = int(hashlib.sha256(f"{token}:{seed}".encode("utf-8")).hexdigest(), 16)
            idx = h % dim
            sign = 1.0 if ((h >> 8) & 1) == 0 else -1.0
            weight = 1.0 / math.log2(i + 3)
            vec[idx] += sign * weight

    # Character n-grams for typo and subword resilience
    for n in (3, 4):
        for i in range(max(0, len(clean_text) - n + 1)):
            ngram = clean_text[i : i + n]
            h = int(hashlib.sha256(f"ng:{ngram}".encode("utf-8")).hexdigest(), 16)
            idx = h % dim
            sign = 1.0 if ((h >> 8) & 1) == 0 else -1.0
            vec[idx] += sign * 0.25

    norm = math.sqrt(sum(x * x for x in vec))
    if norm > 0:
        vec = [float(x / norm) for x in vec]
    return vec


def compute_cosine_similarity(vec1: Sequence[float], vec2: Sequence[float]) -> float:
    """Calculate cosine similarity between two numeric vectors."""
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    sim = dot / (norm1 * norm2)
    # Bound to [-1.0, 1.0] and normalize to [0.0, 1.0] range
    sim = max(-1.0, min(1.0, sim))
    return float((sim + 1.0) / 2.0)
