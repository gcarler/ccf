"""Search — execute + reindex + promotions de ``SearchIndex``/``SearchPromotion``.

Sub-router movido desde ``backend/api/enterprise_cms.py`` (split del
monolito, deuda estructural 🟠#4, 2026-08-05).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy import String, cast, desc, func, or_
from sqlalchemy.orm import Session

from backend.api.enterprise_cms.__common import _log_audit, require_cms_manage, require_cms_read
from backend.core.database import get_db
from backend.models_enterprise import SearchIndex, SearchPromotion
from backend.models_identity import User
from backend.services.cms_search_indexer import reindex_all_cms_content

router = APIRouter()


class SearchRequest(BaseModel):
    site_key: str = "ccf"
    query: str = ""
    entity_type: str | None = None
    category: str | None = None
    tags: list[str] | str | None = None
    author: str | None = None
    date_from: str | None = None
    date_to: str | None = None
    page: int = 1
    limit: int = 20


class SearchPromotionCreate(BaseModel):
    site_key: str
    query_text: str
    entity_type: str
    entity_id: str
    entity_slug: str | None = None
    title: str | None = None
    boost_score: int = 100


def execute_search(db: Session, body: SearchRequest) -> dict:
    """Ejecuta la búsqueda contra ``SearchIndex`` aplicando filtros,
    ranking por boost + coincidencia y paginación. Se reutiliza para los
    endpoints GET (query string) y POST (body JSON).
    """
    q = db.query(SearchIndex).filter(
        SearchIndex.site_key == body.site_key,
        SearchIndex.is_published == True,
    )
    if body.entity_type:
        q = q.filter(SearchIndex.entity_type == body.entity_type)
    if body.category:
        q = q.filter(SearchIndex.category == body.category)
    if body.author:
        try:
            author_uuid = uuid.UUID(body.author)
            q = q.filter(SearchIndex.author_persona_id == author_uuid)
        except ValueError:
            pass

    if body.date_from:
        try:
            dt_from = datetime.fromisoformat(str(body.date_from).replace("Z", "+00:00"))
            q = q.filter(SearchIndex.created_at >= dt_from)
        except ValueError:
            pass

    if body.date_to:
        try:
            dt_to = datetime.fromisoformat(str(body.date_to).replace("Z", "+00:00"))
            q = q.filter(SearchIndex.created_at <= dt_to)
        except ValueError:
            pass

    tag_list: list[str] = []
    if body.tags:
        if isinstance(body.tags, list):
            tag_list = [t.strip() for t in body.tags if t.strip()]
        elif isinstance(body.tags, str):
            tag_list = [t.strip() for t in body.tags.split(",") if t.strip()]

    for tag in tag_list:
        q = q.filter(cast(SearchIndex.tags, String).ilike(f"%{tag}%"))

    query_str = (body.query or "").strip()
    dialect_name = db.bind.dialect.name if db.bind else "sqlite"

    if query_str:
        if dialect_name == "postgresql":
            tsquery = func.websearch_to_tsquery("spanish", query_str)
            tsvector = func.to_tsvector(
                "spanish", func.coalesce(SearchIndex.title, "") + " " + func.coalesce(SearchIndex.body_text, "")
            )
            q = q.filter(
                or_(
                    tsvector.op("@@")(tsquery),
                    SearchIndex.title.ilike(f"%{query_str}%"),
                    SearchIndex.body_text.ilike(f"%{query_str}%"),
                    SearchIndex.category.ilike(f"%{query_str}%"),
                    SearchIndex.entity_slug.ilike(f"%{query_str}%"),
                )
            )
        else:
            search_pattern = f"%{query_str}%"
            q = q.filter(
                or_(
                    SearchIndex.title.ilike(search_pattern),
                    SearchIndex.body_text.ilike(search_pattern),
                    SearchIndex.category.ilike(search_pattern),
                    SearchIndex.entity_slug.ilike(search_pattern),
                )
            )

    candidates = q.all()

    def calc_relevance(item: SearchIndex) -> tuple[int, datetime]:
        score = item.boost_score or 0
        if query_str:
            q_lower = query_str.lower()
            if item.title and q_lower in item.title.lower():
                score += 10
            if item.category and q_lower in item.category.lower():
                score += 5
            if item.entity_slug and q_lower in item.entity_slug.lower():
                score += 3
            if item.body_text and q_lower in item.body_text.lower():
                score += 1
        updated = item.updated_at or datetime.min.replace(tzinfo=timezone.utc)
        return (score, updated)

    candidates.sort(key=calc_relevance, reverse=True)

    total = len(candidates)
    page = max(1, body.page)
    limit = max(1, min(100, body.limit))
    offset = (page - 1) * limit
    paged_results = candidates[offset : offset + limit]

    promoted_items: list[dict] = []
    if query_str:
        promoted = (
            db.query(SearchPromotion)
            .filter(
                SearchPromotion.site_key == body.site_key,
                SearchPromotion.query_text.ilike(f"%{query_str}%"),
                SearchPromotion.is_active == True,
            )
            .order_by(desc(SearchPromotion.boost_score))
            .all()
        )

        promoted_items = [
            {
                "entity_type": p.entity_type,
                "entity_id": p.entity_id,
                "entity_slug": p.entity_slug,
                "title": p.title,
                "boost_score": p.boost_score,
            }
            for p in promoted
        ]

    results_list = [
        {
            "entity_type": r.entity_type,
            "entity_id": r.entity_id,
            "entity_slug": r.entity_slug,
            "title": r.title,
            "body_text": r.body_text,
            "category": r.category,
            "tags": r.tags if isinstance(r.tags, list) else [],
            "author_persona_id": str(r.author_persona_id) if r.author_persona_id else None,
            "boost_score": r.boost_score,
            "relevance_score": calc_relevance(r)[0],
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }
        for r in paged_results
    ]

    return {
        "query": body.query,
        "total": total,
        "page": page,
        "limit": limit,
        "results": results_list,
        "promoted": promoted_items,
    }


@router.get("/search")
def search_content_get(
    q: str = Query(default=""),
    site_key: str = Query(default="ccf"),
    entity_type: str | None = None,
    category: str | None = None,
    tags: str | None = Query(default=None, description="Comma separated tags"),
    author: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(require_cms_read),
):
    parsed_tags = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    return execute_search(
        db,
        SearchRequest(
            site_key=site_key,
            query=q,
            entity_type=entity_type,
            category=category,
            tags=parsed_tags,
            author=author,
            date_from=date_from,
            date_to=date_to,
            page=page,
            limit=limit,
        ),
    )


@router.post("/search")
def search_content(
    body: SearchRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_cms_read),
):
    return execute_search(db, body)


@router.post("/search/reindex")
def reindex_search_content(
    site_key: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(require_cms_manage),
):
    summary = reindex_all_cms_content(db, site_key=site_key)
    _log_audit(db, user, "search.reindex", "search_index", site_key=site_key or "all")
    return summary


@router.get("/search/promotions")
def list_search_promotions(
    site_key: str = Query(default="ccf"),
    db: Session = Depends(get_db),
    user: User = Depends(require_cms_read),
):
    rows = (
        db.query(SearchPromotion)
        .filter(SearchPromotion.site_key == site_key)
        .order_by(desc(SearchPromotion.created_at))
        .all()
    )
    return [
        {
            "id": str(row.id),
            "query_text": row.query_text,
            "entity_type": row.entity_type,
            "entity_id": row.entity_id,
            "entity_slug": row.entity_slug,
            "title": row.title,
            "boost_score": row.boost_score,
            "is_active": row.is_active,
        }
        for row in rows
    ]


@router.post("/search/promotions")
def create_search_promotion(
    body: SearchPromotionCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_cms_manage),
):
    promo = SearchPromotion(
        site_key=body.site_key,
        query_text=body.query_text,
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        entity_slug=body.entity_slug,
        title=body.title,
        boost_score=body.boost_score,
        created_by_persona_id=getattr(user, "persona_id", None),
    )
    db.add(promo)
    _log_audit(
        db,
        user,
        "search.promotion.create",
        "search_promotion",
        str(promo.id),
        site_key=body.site_key,
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    return {"id": str(promo.id), "status": "created"}
