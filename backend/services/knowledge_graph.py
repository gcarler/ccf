from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, List, Optional, Set, cast
from uuid import UUID

from sqlalchemy.orm import Session

from backend import models

logger = logging.getLogger(__name__)

# Cache de warnings emitido una vez por proceso, para no inundar el log
# cuando un modelo no está registrado en runtime (graceful degradation).
_warned_missing_models: Set[str] = set()


def _has_model(name: str) -> bool:
    """Convenio SQLAlchemy: ``getattr(models, name, None)`` idiomático.

    Retorna ``True`` cuando ``models.<name>`` existe y no es ``None``.
    Si retorna ``False``, el caller debe omitir la sección correspondiente
    (graceful degradation). Un único warning se emite por nombre ausente
    por proceso para evitar spam en logs producción.
    """
    cls = getattr(models, name, None)
    if cls is None and name not in _warned_missing_models:
        _warned_missing_models.add(name)
        logger.warning(
            "KnowledgeGraph: model '%s' not registered; skipping corresponding nodes",
            name,
        )
    return cls is not None


def _course_nodes(db: Session, limit: int, sede_id: Optional[UUID] = None) -> List[Dict[str, Any]]:
    q = db.query(models.Course).order_by(models.Course.created_at.desc())
    if sede_id is not None:
        q = q.filter(models.Course.sede_id == sede_id)
    courses = q.limit(limit).all()
    nodes: List[Dict[str, Any]] = []
    for course in courses:
        nodes.append(
            {
                "id": f"course-{course.id}",
                "type": "course",
                "label": course.title,
                "detail": course.description or "Sin descripción",
                "meta": {
                    "code": course.code,
                    "modality": course.modality,
                    "certificate": course.certificate_type,
                },
            }
        )
    return nodes


def _person_nodes(db: Session, limit: int, sede_id: Optional[UUID] = None) -> List[Dict[str, Any]]:
    q = db.query(models.Persona).order_by(models.Persona.created_at.desc())
    if sede_id is not None:
        q = q.filter(models.Persona.sede_id == sede_id)
    persons = q.limit(limit).all()
    nodes: List[Dict[str, Any]] = []
    for person in persons:
        nodes.append(
            {
                "id": f"person-{person.id}",
                "type": "person",
                "label": f"{person.first_name} {person.last_name}",
                "detail": person.email,
                "meta": {
                    "status": person.spiritual_status,
                    "gender": getattr(person, "gender", ""),
                },
            }
        )
    return nodes


def _asset_nodes(db: Session, limit: int, sede_id: Optional[UUID] = None) -> List[Dict[str, Any]]:
    # Graceful degradation: si AssetItem no está registrado en ``models``,
    # esta sección se omite silenciosamente (mismo patrón que el bloque
    # edges de mantenimiento más abajo, en este mismo archivo). Evita
    # que el resolver ``asset`` reviente con AttributeError cuando el
    # módulo de inventario no está desplegado en el entorno actual.
    if not _has_model("AssetItem"):
        return []
    q = db.query(models.AssetItem)
    if sede_id is not None:
        q = q.filter(models.AssetItem.sede_id == sede_id)
    assets = q.limit(limit).all()
    nodes: List[Dict[str, Any]] = []
    for asset in assets:
        nodes.append(
            {
                "id": f"asset-{asset.item_id}",
                "type": "asset",
                "label": asset.name,
                "detail": asset.serial_number,
                "meta": {
                    "brand": asset.brand,
                    "status": asset.current_status,
                },
            }
        )
    return nodes


def _fund_nodes(db: Session, sede_id: Optional[UUID] = None) -> List[Dict[str, Any]]:
    q = db.query(models.Fund)
    if sede_id is not None:
        q = q.filter(models.Fund.sede_id == sede_id)
    funds = q.limit(10).all()
    nodes: List[Dict[str, Any]] = []
    for fund in funds:
        is_public = cast(bool, getattr(fund, "is_public", False))
        balance = cast(float, getattr(fund, "current_balance", 0) or 0.0)
        nodes.append(
            {
                "id": f"fund-{fund.fund_id}",
                "type": "fund",
                "label": fund.name,
                "detail": "Fondo activo" if is_public else "Fondo privado",
                "meta": {
                    "balance": float(balance),
                },
            }
        )
    return nodes


def _family_nodes(db: Session, limit: int, sede_id: Optional[UUID] = None) -> List[Dict[str, Any]]:
    q = db.query(models.Family)
    if sede_id is not None:
        q = q.join(models.Persona, models.Persona.family_id == models.Family.id).filter(models.Persona.sede_id == sede_id)
    families = q.limit(limit).all()
    return [
        {
            "id": f"family-{family.family_id}",
            "type": "family",
            "label": family.family_name,
            "detail": family.address,
        }
        for family in families
    ]


def _project_nodes(db: Session, limit: int, sede_id: Optional[UUID] = None) -> List[Dict[str, Any]]:
    q = db.query(models.Project).order_by(models.Project.created_at.desc())
    if sede_id is not None:
        q = q.filter(models.Project.sede_id == sede_id)
    projects = q.limit(limit).all()
    nodes: List[Dict[str, Any]] = []
    for project in projects:
        nodes.append(
            {
                "id": f"project-{project.id}",
                "type": "project",
                "label": project.name,
                "detail": project.description or "Sin descripción",
                "meta": {
                    "status": project.status,
                    "tasks": len(project.tasks or []),
                },
            }
        )
    return nodes


def build_graph_snapshot(
    db: Session, limit: int = 50, types: Optional[Iterable[str]] = None,
    sede_id: Optional[UUID] = None,
) -> Dict[str, Any]:
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    seen: Set[str] = set()

    type_filter = {t.strip() for t in types or [] if t.strip()}

    resolvers: Dict[str, Any] = {
        "course": lambda: _course_nodes(db, limit // 2, sede_id=sede_id),
        "person": lambda: _person_nodes(db, limit, sede_id=sede_id),
        "asset": lambda: _asset_nodes(db, limit // 2, sede_id=sede_id),
        "fund": lambda: _fund_nodes(db, sede_id=sede_id),
        "family": lambda: _family_nodes(db, limit // 3, sede_id=sede_id),
        "project": lambda: _project_nodes(db, limit // 2, sede_id=sede_id),
    }

    for node_type, resolver in resolvers.items():
        if type_filter and node_type not in type_filter:
            continue
        for node in resolver():
            if node["id"] not in seen:
                nodes.append(node)
                seen.add(node["id"])

    # Build enrollment edges person -> course.
    # Axioma 3: limita edges a la sede del actor para evitar leaks
    # cross-sede cuando el grafo ya filtró los nodos visibles. Sin este
    # JOIN, la query global de Enrollment devuelve aristas que apuntan a
    # person/course de otras sedes y la vista local queda sin conexiones.
    edge_limit = max(limit, 1)
    if sede_id is not None:
        enrollment_q = (
            db.query(models.Enrollment)
            .join(models.Persona, models.Enrollment.persona_id == models.Persona.id)
            .filter(models.Persona.sede_id == sede_id)
            .limit(edge_limit)
        )
    else:
        enrollment_q = db.query(models.Enrollment).limit(edge_limit)
    for enrollment in enrollment_q.all():
        person_id = f"person-{enrollment.persona_id}" if enrollment.persona_id else None
        if person_id and f"course-{enrollment.course_id}" in seen:
            edges.append(
                {
                    "from": person_id,
                    "to": f"course-{enrollment.course_id}",
                    "relation": "ENROLLED_IN",
                }
            )

    # Asset maintenance edges — filtrar por sede del Asset referenciado.
    # Graceful degradation: si MaintenanceLog / AssetItem no están
    # registrados en ``models``, esta sección se omite silenciosamente.
    if _has_model("MaintenanceLog") and _has_model("AssetItem"):
        if sede_id is not None:
            logs_q = (
                db.query(models.MaintenanceLog)
                .join(models.AssetItem, models.MaintenanceLog.item_id == models.AssetItem.item_id)
                .filter(models.AssetItem.sede_id == sede_id)
                .limit(edge_limit)
            )
        else:
            logs_q = db.query(models.MaintenanceLog).limit(edge_limit)
        for log in logs_q.all():
            asset_id = f"asset-{log.item_id}"
            if asset_id in seen:
                edges.append(
                    {
                        "from": asset_id,
                        "to": f"maintenance-{log.log_id}",
                        "relation": "MAINTENANCE",
                    }
                )
                nodes.append(
                    {
                        "id": f"maintenance-{log.log_id}",
                        "type": "maintenance_log",
                        "label": log.description[:42] if log.description else "Servicio",
                        "detail": str(log.service_date),
                    }
                )

    # Family participation edges — la query ya filtra personas con
    # ``family_id`` no nulo. Sumamos el scope por sede aquí (defense-in-depth
    # complementario a ``_family_nodes`` que ya filtra).
    family_p_q = db.query(models.Persona).filter(models.Persona.family_id.isnot(None))
    if sede_id is not None:
        family_p_q = family_p_q.filter(models.Persona.sede_id == sede_id)
    family_personas = family_p_q.limit(edge_limit).all()
    for person in family_personas:
        pid = f"person-{person.id}"
        fid = f"family-{person.family_id}"
        if pid in seen and fid in seen:
            edges.append(
                {
                    "from": pid,
                    "to": fid,
                    "relation": "BELONGS_TO_FAMILY",
                }
            )

    # Project -> asset edges (when supplies reference asset). Filtra por
    # sede del proyecto (ya cubierto por ``_project_nodes`` si la sede
    # está resuelta) — defense-in-depth.
    if sede_id is not None:
        task_q = (
            db.query(models.ProjectTask)
            .join(models.Project, models.ProjectTask.project_id == models.Project.id)
            .filter(models.Project.sede_id == sede_id)
            .limit(edge_limit)
        )
    else:
        task_q = db.query(models.ProjectTask).limit(edge_limit)
    for task in task_q.all():
        project_id = f"project-{task.project_id}"
        if project_id in seen:
            edges.append(
                {
                    "from": project_id,
                    "to": f"task-{task.id}",
                    "relation": "HAS_TASK",
                }
            )
            nodes.append(
                {
                    "id": f"task-{task.id}",
                    "type": "task",
                    "label": task.title,
                    "detail": task.description,
                }
            )

    # Funds impact edges (donations) — filtrar por Donation.sede_id cuando
    # esté disponible. (Donation tiene ``sede_id`` desde la fase 4.)
    donation_q = db.query(models.Donation)
    if sede_id is not None:
        donation_q = donation_q.filter(models.Donation.sede_id == sede_id)
    donations = donation_q.limit(edge_limit).all()
    for donation in donations:
        if donation.fund_id is not None:
            source = "fund-untracked"
            if donation.persona_id is not None:
                source = f"person-{donation.persona_id}"
                if source not in seen:
                    nodes.append(
                        {
                            "id": source,
                            "type": "donor",
                            "label": f"Donante {str(donation.persona_id)[:6]}",
                            "detail": "Donación registrada",
                        }
                    )
                    seen.add(source)
            edges.append(
                {
                    "from": source,
                    "to": f"fund-{donation.fund_id}",
                    "relation": "DONATED_TO",
                    "meta": {"amount": float(cast(float, donation.amount) or 0)},
                }
            )

    return {
        "nodes": nodes,
        "edges": edges,
        "meta": {
            "counts": {
                "nodes": len(nodes),
                "edges": len(edges),
                "courses": len([n for n in nodes if n["type"] == "course"]),
                "people": len([n for n in nodes if n["type"] in {"person", "donor"}]),
                "assets": len([n for n in nodes if n["type"] == "asset"]),
            }
        },
    }
