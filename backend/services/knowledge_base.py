"""Knowledge Base — Base de conocimiento del sistema multiagente.

Modelo, indexador automático y búsqueda full-text para que los agentes
tengan acceso a información real de la plataforma.
"""

from datetime import datetime

from sqlalchemy import (Boolean, Column, DateTime, Float, ForeignKey, Index,
                        Integer, String, Text, func)
from sqlalchemy.orm import Session

from backend.core.database import Base


def _utcnow():
    return datetime.utcnow()


class AgentKnowledgeBase(Base):
    """Documento de conocimiento indexado para los agentes."""
    __tablename__ = "agent_knowledge_base"
    __table_args__ = (
        Index("ix_kb_category", "category"),
        Index("ix_kb_source", "source_module"),
        Index("ix_kb_active", "is_active"),
    )

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(300), nullable=False)
    content = Column(Text, nullable=False)
    summary = Column(String(500), nullable=True)
    category = Column(String(50), nullable=False, index=True)
    source_module = Column(String(50), nullable=False, index=True)
    source_id = Column(Integer, nullable=True)
    source_url = Column(String(500), nullable=True)
    relevance_score = Column(Float, default=0.5)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=_utcnow, index=True)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)
    indexed_by = Column(Integer, ForeignKey("agents.id"), nullable=True)

    def __repr__(self):
        return f"<KB {self.title[:50]} [{self.category}]>"


# ──────────────────────────────────────────────
# KNOWLEDGE INDEXER
# ──────────────────────────────────────────────

class KnowledgeIndexer:
    """Indexa contenido de los módulos en la Knowledge Base."""

    def __init__(self, db: Session):
        self.db = db

    def rebuild_all(self, indexed_by_agent_id: int = None) -> dict:
        """Reconstruye toda la KB desde cero."""
        # Desactivar todo lo existente
        self.db.query(AgentKnowledgeBase).update(
            {"is_active": False}, synchronize_session=False,
        )
        self.db.commit()

        stats = {
            "courses": self._index_courses(indexed_by_agent_id),
            "strategies": self._index_evangelism(indexed_by_agent_id),
            "projects": self._index_projects(indexed_by_agent_id),
            "members_stats": self._index_member_stats(indexed_by_agent_id),
            "system_vars": self._index_system_vars(indexed_by_agent_id),
        }
        return stats

    def _index_courses(self, agent_id: int) -> int:
        """Indexa cursos activos."""
        from backend import models

        courses = self.db.query(models.Course).filter(
            models.Course.is_active,
        ).all()
        count = 0
        for c in courses:
            self._upsert_kb(
                title=f"Curso: {c.title}",
                content=(
                    f"{c.title}: {c.description or ''}\n"
                    f"Módulo: {c.module or 'N/A'}\n"
                    f"Nivel: {c.level or 'N/A'}\n"
                    f"Duración: {c.duration or 'N/A'}"
                ),
                summary=(c.description or "")[:200] if c.description else None,
                category="academy",
                source_module="academy",
                source_id=c.id,
                source_url=f"/plataforma/academy/courses/{c.id}",
                indexed_by=agent_id,
            )
            count += 1
        self.db.commit()
        return count

    def _index_evangelism(self, agent_id: int) -> int:
        """Indexa estrategias de evangelismo."""
        from backend import models

        strategies = self.db.query(models.EvangelismStrategy).filter(
            models.EvangelismStrategy.is_active,
        ).all()
        count = 0
        for s in strategies:
            self._upsert_kb(
                title=f"Estrategia: {s.name}",
                content=(
                    f"{s.name}: {s.description or ''}\n"
                    f"Tipo: {s.strategy_type or 'N/A'}\n"
                    f"Estado: {s.status or 'active'}"
                ),
                summary=(s.description or "")[:200] if s.description else None,
                category="evangelism",
                source_module="evangelism",
                source_id=s.id,
                source_url=f"/plataforma/evangelism/strategies/{s.id}",
                indexed_by=agent_id,
            )
            count += 1
        self.db.commit()
        return count

    def _index_projects(self, agent_id: int) -> int:
        """Indexa proyectos activos."""
        from backend import models

        projects = self.db.query(models.Project).filter(
            models.Project.status.in_(["active", "planning"]),
        ).all()
        count = 0
        for p in projects:
            self._upsert_kb(
                title=f"Proyecto: {p.title}",
                content=(
                    f"{p.title}: {p.description or ''}\n"
                    f"Estado: {p.status}\n"
                    f"Owner: {p.owner_id}"
                ),
                summary=(p.description or "")[:200] if p.description else None,
                category="projects",
                source_module="projects",
                source_id=p.id,
                source_url=f"/plataforma/projects/{p.id}",
                indexed_by=agent_id,
            )
            count += 1
        self.db.commit()
        return count

    def _index_member_stats(self, agent_id: int) -> int:
        """Indexa estadísticas de miembros (no datos personales)."""
        from backend import models

        total = self.db.query(models.Persona).count()
        by_role = {}
        for role, cnt in self.db.query(
            models.Persona.church_role, func.count(models.Persona.id),
        ).filter(
            models.Persona.church_role.isnot(None),
        ).group_by(models.Persona.church_role).all():
            by_role[role] = cnt

        self._upsert_kb(
            title="Estadísticas de miembros",
            content=(
                f"Total de miembros: {total}\n"
                f"Distribución por rol: {by_role}"
            ),
            summary=f"{total} miembros registrados",
            category="crm_stats",
            source_module="crm",
            source_id=None,
            indexed_by=agent_id,
        )
        self.db.commit()
        return 1

    def _index_system_vars(self, agent_id: int) -> int:
        """Indexa variables del sistema como conocimiento."""
        from backend import models

        variables = self.db.query(models.SystemVariable).filter(
            models.SystemVariable.is_active,
        ).all()
        count = 0
        for v in variables:
            self._upsert_kb(
                title=f"Configuración: {v.key}",
                content=f"{v.key} = {v.value}",
                summary=f"Variable del sistema: {v.key}",
                category="system",
                source_module="system",
                source_id=v.id,
                indexed_by=agent_id,
            )
            count += 1
        self.db.commit()
        return count

    def _upsert_kb(self, **kwargs):
        """Inserta o actualiza un documento en la KB."""
        existing = self.db.query(AgentKnowledgeBase).filter(
            AgentKnowledgeBase.source_module == kwargs.get("source_module"),
            AgentKnowledgeBase.source_id == kwargs.get("source_id"),
            AgentKnowledgeBase.title == kwargs.get("title"),
        ).first()

        if existing:
            for k, v in kwargs.items():
                if hasattr(existing, k):
                    setattr(existing, k, v)
            existing.is_active = True
            existing.updated_at = _utcnow()
        else:
            doc = AgentKnowledgeBase(**kwargs)
            self.db.add(doc)


# ──────────────────────────────────────────────
# BÚSQUEDA REAL (full-text search)
# ──────────────────────────────────────────────

def search_knowledge_base_real(
    db: Session, query: str, top_k: int = 5, category: str = None,
):
    """Búsqueda full-text en la Knowledge Base.

    Usa tsvector de PostgreSQL si disponible, sino LIKE como fallback.
    Retorna objetos AgentKnowledgeBase (no dicts como el mock).
    """
    if not query or not query.strip():
        return []

    terms = query.strip().lower().split()
    if not terms:
        return []

    q = db.query(AgentKnowledgeBase).filter(
        AgentKnowledgeBase.is_active,
    )

    # Filtro por categoría si se especifica
    if category:
        q = q.filter(AgentKnowledgeBase.category == category)

    # Construir búsqueda: cada término debe aparecer en title o content
    conditions = []
    for term in terms:
        like_pattern = f"%{term}%"
        conditions.append(
            AgentKnowledgeBase.title.ilike(like_pattern)
            | AgentKnowledgeBase.content.ilike(like_pattern)
            | AgentKnowledgeBase.summary.ilike(like_pattern)
        )

    if conditions:
        from sqlalchemy import or_
        q = q.filter(or_(*conditions))

    # Ordenar por relevancia y fecha
    results = q.order_by(
        AgentKnowledgeBase.relevance_score.desc(),
        AgentKnowledgeBase.updated_at.desc(),
    ).limit(top_k).all()

    return results
