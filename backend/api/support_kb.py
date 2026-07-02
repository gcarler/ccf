"""Knowledge Base pública para el módulo de Soporte."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend import models
from backend.core.database import get_db
from backend.core.permissions import require_active_user

router = APIRouter(prefix="/support/kb", tags=["support_kb"])


@router.get("/categories", response_model=List[dict])
def list_kb_categories(db: Session = Depends(get_db)):
    """Lista las categorías de la base de conocimiento con conteo de artículos."""
    rows = (
        db.query(
            models.AgentKnowledgeBase.category,
            func.count(models.AgentKnowledgeBase.id).label("count"),
        )
        .filter(models.AgentKnowledgeBase.is_active.is_(True))
        .group_by(models.AgentKnowledgeBase.category)
        .all()
    )
    return [
        {
            "id": r.category,
            "label": r.category.replace("_", " ").title(),
            "count": r.count,
        }
        for r in rows
    ]


@router.get("/articles", response_model=List[dict])
def list_kb_articles(
    category: Optional[str] = None,
    popular: bool = False,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """Lista artículos de la base de conocimiento."""
    query = db.query(models.AgentKnowledgeBase).filter(
        models.AgentKnowledgeBase.is_active.is_(True)
    )
    if category:
        query = query.filter(models.AgentKnowledgeBase.category == category)
    if popular:
        query = query.order_by(models.AgentKnowledgeBase.relevance_score.desc())
    else:
        query = query.order_by(models.AgentKnowledgeBase.created_at.desc())

    articles = query.limit(limit).all()
    return [
        {
            "id": str(a.id),
            "title": a.title,
            "category": a.category,
            "summary": a.summary or "",
            "views": int(a.relevance_score * 100),
            "helpful": 95,
        }
        for a in articles
    ]


@router.get("/articles/{article_id}", response_model=dict)
def get_kb_article(
    article_id: UUID,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_active_user),
):
    """Devuelve el contenido de un artículo."""
    article = (
        db.query(models.AgentKnowledgeBase)
        .filter(
            models.AgentKnowledgeBase.id == article_id,
            models.AgentKnowledgeBase.is_active.is_(True),
        )
        .first()
    )
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return {
        "id": str(article.id),
        "title": article.title,
        "category": article.category,
        "summary": article.summary or "",
        "content": article.content,
        "views": int(article.relevance_score * 100),
        "helpful": 95,
    }
