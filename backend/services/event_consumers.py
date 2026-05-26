"""Event Consumers — Handlers que responden a eventos del dominio.

Cada consumer se suscribe a tipos de eventos y ejecuta acciones:
- insights generados
- notificaciones
- indexación en KB
- actualización del grafo
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

log = logging.getLogger(__name__)


class EventConsumer:
    """Handler base para eventos del dominio."""

    @property
    def subscribed_events(self) -> List[str]:
        """Lista de nombres de eventos a los que se suscribe."""
        return []

    def handle(self, event_name: str, payload: Dict[str, Any]) -> None:
        """Procesa un evento."""
        handler = getattr(self, f"handle_{event_name}", None)
        if handler:
            try:
                handler(payload)
            except Exception as exc:
                log.exception(
                    "Error handling event %s in %s: %s",
                    event_name, self.__class__.__name__, exc,
                )


class IntelligenceConsumer(EventConsumer):
    """Genera insights cuando detecta patrones en los datos."""

    @property
    def subscribed_events(self) -> List[str]:
        return [
            "member_registered",
            "enrollment_created",
            "task_overdue",
        ]

    def handle_member_registered(self, payload: Dict[str, Any]) -> None:
        """Cuando se registra un miembro → genera insight de bienvenida."""
        from backend import schemas
        from backend.core.database import SessionLocal
        from backend.crud.agents import create_agent_insight

        db = SessionLocal()
        try:
            name = payload.get("name", "Nuevo miembro")
            role = payload.get("church_role", "visitante")
            create_agent_insight(
                db,
                schemas.AgentInsightCreate(
                    title=f"Nuevo miembro registrado: {name}",
                    insight_type="member_event",
                    description=f"{name} se registró como {role}",
                    confidence=1.0,
                    source_agent="system",
                    payload=payload,
                ),
            )
            log.info("Insight creado para nuevo miembro: %s", name)
        finally:
            db.close()

    def handle_enrollment_created(self, payload: Dict[str, Any]) -> None:
        """Nueva inscripción → re-indexa en KB."""
        from backend.core.database import SessionLocal
        from backend.services.knowledge_base import KnowledgeIndexer

        db = SessionLocal()
        try:
            indexer = KnowledgeIndexer(db)
            indexer._index_courses(agent_id=None)
            db.commit()
            log.info("KB re-indexed after enrollment")
        finally:
            db.close()

    def handle_task_overdue(self, payload: Dict[str, Any]) -> None:
        """Tarea vencida → genera insight de alerta."""
        from backend import schemas
        from backend.core.database import SessionLocal
        from backend.crud.agents import (
            create_agent_insight, create_agent_task,
        )

        db = SessionLocal()
        try:
            task_title = payload.get("title", "Tarea sin título")
            create_agent_insight(
                db,
                schemas.AgentInsightCreate(
                    title=f"Tarea vencida: {task_title}",
                    insight_type="alert",
                    description=f"La tarea '{task_title}' está vencida",
                    confidence=0.9,
                    source_agent="automation",
                    payload=payload,
                ),
            )
            create_agent_task(
                db,
                schemas.AgentTaskCreate(
                    title=f"Revisar tarea vencida: {task_title}",
                    description=payload.get("description", ""),
                    priority="high",
                    source="event_consumer",
                ),
            )
            log.info("Alerta creada para tarea vencida: %s", task_title)
        finally:
            db.close()


class GraphUpdateConsumer(EventConsumer):
    """Actualiza el grafo de conocimiento cuando cambian entidades."""

    @property
    def subscribed_events(self) -> List[str]:
        return [
            "member_status_changed",
            "spiritual_stage_transition",
        ]

    def handle_member_status_changed(self, payload: Dict[str, Any]) -> None:
        """Miembro cambió de estado → log."""
        log.info(
            "Graph update: member status changed for %s",
            payload.get("member_id"),
        )

    def handle_spiritual_stage_transition(self, payload: Dict[str, Any]) -> None:
        """Transición espiritual → log."""
        log.info(
            "Graph update: spiritual transition %s → %s for agent %s",
            payload.get("from_stage"),
            payload.get("to_stage"),
            payload.get("agent_id"),
        )


class KBIndexConsumer(EventConsumer):
    """Re-indexa la KB cuando cambia contenido."""

    @property
    def subscribed_events(self) -> List[str]:
        return [
            "course_created",
            "project_created",
            "strategy_created",
        ]

    def handle_course_created(self, payload: Dict[str, Any]) -> None:
        from backend.core.database import SessionLocal
        from backend.services.knowledge_base import KnowledgeIndexer

        db = SessionLocal()
        try:
            indexer = KnowledgeIndexer(db)
            indexer._index_courses(agent_id=None)
            db.commit()
        finally:
            db.close()

    def handle_project_created(self, payload: Dict[str, Any]) -> None:
        from backend.core.database import SessionLocal
        from backend.services.knowledge_base import KnowledgeIndexer

        db = SessionLocal()
        try:
            indexer = KnowledgeIndexer(db)
            indexer._index_projects(agent_id=None)
            db.commit()
        finally:
            db.close()

    def handle_strategy_created(self, payload: Dict[str, Any]) -> None:
        from backend.core.database import SessionLocal
        from backend.services.knowledge_base import KnowledgeIndexer

        db = SessionLocal()
        try:
            indexer = KnowledgeIndexer(db)
            indexer._index_evangelism(agent_id=None)
            db.commit()
        finally:
            db.close()


# ──────────────────────────────────────────────
# REGISTRY
# ──────────────────────────────────────────────

_event_registry: Dict[str, List[EventConsumer]] = {}


def register_consumer(consumer: EventConsumer):
    """Registra un consumer y sus eventos."""
    for event_name in consumer.subscribed_events:
        if event_name not in _event_registry:
            _event_registry[event_name] = []
        _event_registry[event_name].append(consumer)
    log.info(
        "Consumer registered: %s (%d events)",
        consumer.__class__.__name__,
        len(consumer.subscribed_events),
    )


def dispatch_event(event_name: str, payload: Dict[str, Any]):
    """Despacha un evento a todos los consumers suscritos."""
    consumers = _event_registry.get(event_name, [])
    for consumer in consumers:
        consumer.handle(event_name, payload)


def register_all_consumers():
    """Registra todos los consumers del sistema."""
    consumers = [
        IntelligenceConsumer(),
        GraphUpdateConsumer(),
        KBIndexConsumer(),
    ]
    for c in consumers:
        register_consumer(c)
    return _event_registry
