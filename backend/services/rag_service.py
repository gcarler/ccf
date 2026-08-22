"""Pastoral RAG Service — Hybrid semantic and full-text retrieval with multi-tenant RLS isolation."""

from __future__ import annotations

import logging
import math
import re
from typing import Any, List, Optional, Set, Tuple
from uuid import UUID

from sqlalchemy import or_, text
from sqlalchemy.orm import Session

from backend.core.pgvector_compat import (
    compute_cosine_similarity,
    generate_text_embedding,
)
from backend.models_knowledge_base import AgentKnowledgeBase, KnowledgeBaseArticle
from backend.models_sermones import Sermon
from backend.models_wiki import WikiPage
from backend.schemas.rag import PastoralSearchResult

logger = logging.getLogger("CCF-RAG")


class PastoralRAGService:
    """Service providing hybrid FTS + pgvector cosine similarity search across pastoral documents."""

    def __init__(
        self,
        db: Session,
        user_sede_id: Optional[UUID] = None,
        user_role: Optional[str] = None,
    ) -> None:
        self.db = db
        self.user_sede_id = user_sede_id
        self.user_role = (user_role or "").strip().lower()

    def _is_admin(self) -> bool:
        return self.user_role in {"admin", "superadmin", "administrador", "platform_admin"}

    def _set_rls_context(self, effective_sede_id: Optional[UUID] = None) -> None:
        """Set session-level variables for PostgreSQL Row-Level Security policies."""
        try:
            bind = self.db.get_bind()
            if bind.dialect.name == "postgresql":
                sede_str = str(effective_sede_id or self.user_sede_id or "")
                role_str = self.user_role or "guest"
                self.db.execute(text(f"SET LOCAL app.current_sede_id = '{sede_str}'"))
                self.db.execute(text(f"SET LOCAL app.current_user_role = '{role_str}'"))
        except Exception as exc:
            logger.debug("Failed to set PostgreSQL RLS session context: %s", exc)

    def _compute_text_score(self, query: str, title: str, content: str, summary: Optional[str] = None) -> float:
        """Compute normalized [0.0, 1.0] lexical / full-text relevance score."""
        if not query:
            return 0.0

        query_clean = query.strip().lower()
        title_clean = (title or "").lower()
        content_clean = (content or "").lower()
        summary_clean = (summary or "").lower()

        # Exact title match
        if query_clean == title_clean:
            return 1.0

        # Exact phrase inside title
        if query_clean in title_clean:
            return 0.9

        # Exact phrase inside summary
        if summary_clean and query_clean in summary_clean:
            return 0.85

        # Exact phrase inside content
        if query_clean in content_clean:
            return 0.8

        # Token-level matching
        words = [w for w in re.split(r"\W+", query_clean) if len(w) > 1]
        if not words:
            return 0.0

        title_hits = sum(1 for w in words if w in title_clean)
        summary_hits = sum(1 for w in words if summary_clean and w in summary_clean)
        content_hits = sum(1 for w in words if w in content_clean)

        total_words = len(words)
        title_ratio = title_hits / total_words
        summary_ratio = summary_hits / total_words
        content_ratio = content_hits / total_words

        # Frequency bonus in content
        freq_bonus = 0.0
        for w in words:
            count = content_clean.count(w)
            if count > 1:
                freq_bonus += min(0.1, math.log10(count) * 0.05)

        raw_score = (title_ratio * 0.5) + (summary_ratio * 0.25) + (content_ratio * 0.25) + freq_bonus
        return min(1.0, max(0.0, raw_score))

    def _get_item_embedding(self, item: Any, text_fallback: str) -> list[float]:
        """Extract item embedding or generate deterministic embedding from text."""
        emb = getattr(item, "embedding", None)
        if emb is not None:
            if isinstance(emb, list) and len(emb) == 1536:
                return emb
            if isinstance(emb, str):
                import json

                try:
                    parsed = json.loads(emb)
                    if isinstance(parsed, list):
                        return parsed
                except Exception:
                    pass
        return generate_text_embedding(text_fallback, dim=1536)

    def search(
        self,
        query: str,
        limit: int = 10,
        category: Optional[str] = None,
        alpha: float = 0.5,
        sede_id: Optional[UUID] = None,
    ) -> List[PastoralSearchResult]:
        """Execute hybrid retrieval combining FTS and pgvector cosine similarity with score fusion.

        Args:
            query: Search query text.
            limit: Maximum number of results.
            category: Optional category filter.
            alpha: Weight for vector similarity (0.0 = pure FTS, 1.0 = pure Vector).
            sede_id: Optional explicit sede override (for admin users).
        """
        if not query or not query.strip():
            return []

        effective_sede = sede_id if (self._is_admin() and sede_id is not None) else self.user_sede_id
        self._set_rls_context(effective_sede)

        alpha = max(0.0, min(1.0, float(alpha)))
        limit = max(1, min(100, int(limit)))
        query_text = query.strip()
        query_vector = generate_text_embedding(query_text, dim=1536)

        candidates: List[Tuple[float, PastoralSearchResult]] = []
        seen_keys: Set[Tuple[str, str]] = set()

        # 1. Search KnowledgeBaseArticle
        try:
            q_kba = self.db.query(KnowledgeBaseArticle).filter(
                KnowledgeBaseArticle.deleted_at.is_(None),
                KnowledgeBaseArticle.is_active.is_(True),
            )
            if not self._is_admin():
                if effective_sede is not None:
                    q_kba = q_kba.filter(
                        or_(
                            KnowledgeBaseArticle.sede_id == effective_sede,
                            KnowledgeBaseArticle.sede_id.is_(None),
                        )
                    )
                else:
                    q_kba = q_kba.filter(KnowledgeBaseArticle.sede_id.is_(None))
            elif effective_sede is not None:
                q_kba = q_kba.filter(
                    or_(
                        KnowledgeBaseArticle.sede_id == effective_sede,
                        KnowledgeBaseArticle.sede_id.is_(None),
                    )
                )

            if category:
                q_kba = q_kba.filter(KnowledgeBaseArticle.category.ilike(f"%{category.strip()}%"))

            articles = q_kba.all()
            for art in articles:
                key = ("knowledge_base", str(art.id))
                if key in seen_keys:
                    continue
                seen_keys.add(key)

                fts_score = self._compute_text_score(
                    query_text,
                    art.title,
                    art.content,
                    art.summary,
                )
                art_emb = self._get_item_embedding(art, f"{art.title} {art.summary or ''} {art.content}")
                vec_score = compute_cosine_similarity(query_vector, art_emb)
                fused_score = (alpha * vec_score) + ((1.0 - alpha) * fts_score)

                if fused_score > 0.05 or fts_score > 0.1 or vec_score > 0.6:
                    result = PastoralSearchResult(
                        id=art.id,
                        source="knowledge_base",
                        title=art.title,
                        content=art.content,
                        score=round(fused_score, 4),
                        sede_id=art.sede_id,
                        metadata={
                            "category": art.category,
                            "summary": art.summary,
                            "source_module": art.source_module,
                            "relevance_score": art.relevance_score,
                            "fts_score": round(fts_score, 4),
                            "vec_score": round(vec_score, 4),
                        },
                    )
                    candidates.append((fused_score, result))
        except Exception as exc:
            logger.warning("Error querying KnowledgeBaseArticle in RAG search: %s", exc)

        # 2. Search WikiPage
        try:
            q_wiki = self.db.query(WikiPage).filter(
                WikiPage.deleted_at.is_(None),
            )
            if not self._is_admin():
                if effective_sede is not None:
                    q_wiki = q_wiki.filter(
                        or_(
                            WikiPage.sede_id == effective_sede,
                            WikiPage.sede_id.is_(None),
                        )
                    )
                else:
                    q_wiki = q_wiki.filter(WikiPage.sede_id.is_(None))
            elif effective_sede is not None:
                q_wiki = q_wiki.filter(
                    or_(
                        WikiPage.sede_id == effective_sede,
                        WikiPage.sede_id.is_(None),
                    )
                )

            if category:
                q_wiki = q_wiki.filter(WikiPage.category.ilike(f"%{category.strip()}%"))

            pages = q_wiki.all()
            for page in pages:
                key = ("wiki", str(page.id))
                if key in seen_keys:
                    continue
                seen_keys.add(key)

                fts_score = self._compute_text_score(
                    query_text,
                    page.title,
                    page.content,
                )
                page_emb = self._get_item_embedding(page, f"{page.title} {page.content}")
                vec_score = compute_cosine_similarity(query_vector, page_emb)
                fused_score = (alpha * vec_score) + ((1.0 - alpha) * fts_score)

                if fused_score > 0.05 or fts_score > 0.1 or vec_score > 0.6:
                    result = PastoralSearchResult(
                        id=page.id,
                        source="wiki",
                        title=page.title,
                        content=page.content,
                        score=round(fused_score, 4),
                        sede_id=page.sede_id,
                        metadata={
                            "page_key": page.page_key,
                            "category": page.category,
                            "version": page.version,
                            "tags": page.tags,
                            "fts_score": round(fts_score, 4),
                            "vec_score": round(vec_score, 4),
                        },
                    )
                    candidates.append((fused_score, result))
        except Exception as exc:
            logger.warning("Error querying WikiPage in RAG search: %s", exc)

        # 3. Search Sermon
        try:
            q_sermon = self.db.query(Sermon).filter(
                Sermon.deleted_at.is_(None),
                Sermon.is_active.is_(True),
                Sermon.is_published.is_(True),
            )
            if not self._is_admin():
                if effective_sede is not None:
                    q_sermon = q_sermon.filter(
                        or_(
                            Sermon.sede_id == effective_sede,
                            Sermon.sede_id.is_(None),
                        )
                    )
                else:
                    q_sermon = q_sermon.filter(Sermon.sede_id.is_(None))
            elif effective_sede is not None:
                q_sermon = q_sermon.filter(
                    or_(
                        Sermon.sede_id == effective_sede,
                        Sermon.sede_id.is_(None),
                    )
                )

            if category:
                q_sermon = q_sermon.filter(
                    or_(
                        Sermon.category.ilike(f"%{category.strip()}%"),
                        Sermon.series.ilike(f"%{category.strip()}%"),
                    )
                )

            sermons = q_sermon.all()
            for srm in sermons:
                key = ("sermon", str(srm.id))
                if key in seen_keys:
                    continue
                seen_keys.add(key)

                fts_score = self._compute_text_score(
                    query_text,
                    srm.title,
                    f"{srm.preacher or ''} {srm.passage or ''} {srm.content}",
                    srm.summary,
                )
                srm_emb = self._get_item_embedding(
                    srm,
                    f"{srm.title} {srm.preacher or ''} {srm.passage or ''} {srm.summary or ''} {srm.content}",
                )
                vec_score = compute_cosine_similarity(query_vector, srm_emb)
                fused_score = (alpha * vec_score) + ((1.0 - alpha) * fts_score)

                if fused_score > 0.05 or fts_score > 0.1 or vec_score > 0.6:
                    result = PastoralSearchResult(
                        id=srm.id,
                        source="sermon",
                        title=srm.title,
                        content=srm.content,
                        score=round(fused_score, 4),
                        sede_id=srm.sede_id,
                        metadata={
                            "preacher": srm.preacher,
                            "passage": srm.passage,
                            "series": srm.series,
                            "category": srm.category,
                            "summary": srm.summary,
                            "video_url": srm.video_url,
                            "audio_url": srm.audio_url,
                            "fts_score": round(fts_score, 4),
                            "vec_score": round(vec_score, 4),
                        },
                    )
                    candidates.append((fused_score, result))
        except Exception as exc:
            logger.warning("Error querying Sermon in RAG search: %s", exc)

        # 4. Search AgentKnowledgeBase fallback
        try:
            q_akb = self.db.query(AgentKnowledgeBase).filter(
                AgentKnowledgeBase.is_active.is_(True),
            )
            if not self._is_admin():
                if effective_sede is not None:
                    q_akb = q_akb.filter(
                        or_(
                            AgentKnowledgeBase.sede_id == effective_sede,
                            AgentKnowledgeBase.sede_id.is_(None),
                        )
                    )
                else:
                    q_akb = q_akb.filter(AgentKnowledgeBase.sede_id.is_(None))
            elif effective_sede is not None:
                q_akb = q_akb.filter(
                    or_(
                        AgentKnowledgeBase.sede_id == effective_sede,
                        AgentKnowledgeBase.sede_id.is_(None),
                    )
                )

            if category:
                q_akb = q_akb.filter(AgentKnowledgeBase.category.ilike(f"%{category.strip()}%"))

            akb_items = q_akb.all()
            for item in akb_items:
                key = ("knowledge_base", str(item.id))
                if key in seen_keys:
                    continue
                seen_keys.add(key)

                fts_score = self._compute_text_score(
                    query_text,
                    item.title,
                    item.content,
                    item.summary,
                )
                item_emb = self._get_item_embedding(item, f"{item.title} {item.summary or ''} {item.content}")
                vec_score = compute_cosine_similarity(query_vector, item_emb)
                fused_score = (alpha * vec_score) + ((1.0 - alpha) * fts_score)

                if fused_score > 0.05 or fts_score > 0.1 or vec_score > 0.6:
                    result = PastoralSearchResult(
                        id=item.id,
                        source="knowledge_base",
                        title=item.title,
                        content=item.content,
                        score=round(fused_score, 4),
                        sede_id=item.sede_id,
                        metadata={
                            "category": item.category,
                            "summary": item.summary,
                            "source_module": item.source_module,
                            "relevance_score": item.relevance_score,
                            "fts_score": round(fts_score, 4),
                            "vec_score": round(vec_score, 4),
                        },
                    )
                    candidates.append((fused_score, result))
        except Exception as exc:
            logger.warning("Error querying AgentKnowledgeBase in RAG search: %s", exc)

        # Deduplication & Score sorting
        candidates.sort(key=lambda x: x[0], reverse=True)
        return [res for _, res in candidates[:limit]]

    # ── Indexing & Ingestion Helpers ────────────────────────────────────

    def index_knowledge_article(
        self,
        title: str,
        content: str,
        summary: Optional[str] = None,
        category: str = "general",
        sede_id: Optional[UUID] = None,
        author_id: Optional[UUID] = None,
        source_module: str = "knowledge_base",
        source_id: Optional[str] = None,
        source_url: Optional[str] = None,
        relevance_score: float = 1.0,
    ) -> KnowledgeBaseArticle:
        """Create and embed a knowledge base article."""
        text_for_embedding = f"{title} {summary or ''} {content}"
        emb = generate_text_embedding(text_for_embedding, dim=1536)

        article = KnowledgeBaseArticle(
            title=title,
            content=content,
            summary=summary,
            category=category,
            sede_id=sede_id,
            author_id=author_id,
            source_module=source_module,
            source_id=source_id,
            source_url=source_url,
            relevance_score=relevance_score,
            is_active=True,
            embedding=emb,
        )
        self.db.add(article)
        self.db.flush()
        return article

    def index_sermon(
        self,
        title: str,
        content: str,
        preacher: Optional[str] = None,
        passage: Optional[str] = None,
        summary: Optional[str] = None,
        series: Optional[str] = None,
        category: str = "sermon",
        sede_id: Optional[UUID] = None,
        author_id: Optional[UUID] = None,
        date: Any = None,
        video_url: Optional[str] = None,
        audio_url: Optional[str] = None,
    ) -> Sermon:
        """Create and embed a pastoral sermon."""
        text_for_embedding = f"{title} {preacher or ''} {passage or ''} {summary or ''} {content}"
        emb = generate_text_embedding(text_for_embedding, dim=1536)

        sermon = Sermon(
            title=title,
            preacher=preacher,
            passage=passage,
            content=content,
            summary=summary,
            series=series,
            category=category,
            sede_id=sede_id,
            author_id=author_id,
            date=date,
            video_url=video_url,
            audio_url=audio_url,
            is_published=True,
            is_active=True,
            embedding=emb,
        )
        self.db.add(sermon)
        self.db.flush()
        return sermon

    def index_wiki_page(
        self,
        page_key: str,
        title: str,
        content: str,
        category: Optional[str] = None,
        sede_id: Optional[UUID] = None,
        author_id: Optional[UUID] = None,
        tags: Optional[list] = None,
    ) -> WikiPage:
        """Create and embed a wiki page."""
        text_for_embedding = f"{title} {content}"
        emb = generate_text_embedding(text_for_embedding, dim=1536)

        page = WikiPage(
            page_key=page_key,
            title=title,
            content=content,
            category=category,
            sede_id=sede_id,
            author_id=author_id,
            tags=tags or [],
            embedding=emb,
        )
        self.db.add(page)
        self.db.flush()
        return page
