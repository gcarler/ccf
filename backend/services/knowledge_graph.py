from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Set, cast

from sqlalchemy.orm import Session

from backend import models


def _course_nodes(db: Session, limit: int) -> List[Dict[str, Any]]:
    courses = (
        db.query(models.Course)
        .order_by(models.Course.created_at.desc())
        .limit(limit)
        .all()
    )
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


def _person_nodes(db: Session, limit: int) -> List[Dict[str, Any]]:
    persons = (
        db.query(models.Member)
        .order_by(models.Member.created_at.desc())
        .limit(limit)
        .all()
    )
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


def _asset_nodes(db: Session, limit: int) -> List[Dict[str, Any]]:
    assets = db.query(models.AssetItem).limit(limit).all()
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


def _fund_nodes(db: Session) -> List[Dict[str, Any]]:
    funds = db.query(models.Fund).limit(10).all()
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


def _family_nodes(db: Session, limit: int) -> List[Dict[str, Any]]:
    families = db.query(models.Family).limit(limit).all()
    return [
        {
            "id": f"family-{family.family_id}",
            "type": "family",
            "label": family.family_name,
            "detail": family.address,
        }
        for family in families
    ]


def _lead_nodes(db: Session, limit: int) -> List[Dict[str, Any]]:
    leads = (
        db.query(models.ConsolidationPipeline)
        .order_by(models.ConsolidationPipeline.created_at.desc())
        .limit(limit)
        .all()
    )
    nodes: List[Dict[str, Any]] = []
    for lead in leads:
        nodes.append(
            {
                "id": f"lead-{lead.id}",
                "type": "lead",
                "label": f"{lead.first_name} {lead.last_name}",
                "detail": lead.phone,
                "meta": {
                    "stage": lead.stage,
                    "pastor_id": lead.assigned_pastor_id,
                },
            }
        )
    return nodes


def _project_nodes(db: Session, limit: int) -> List[Dict[str, Any]]:
    projects = (
        db.query(models.Project)
        .order_by(models.Project.created_at.desc())
        .limit(limit)
        .all()
    )
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
    db: Session, limit: int = 50, types: Optional[Iterable[str]] = None
) -> Dict[str, Any]:
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    seen: Set[str] = set()

    type_filter = {t.strip() for t in types or [] if t.strip()}

    resolvers: Dict[str, Any] = {
        "course": lambda: _course_nodes(db, limit // 2),
        "person": lambda: _person_nodes(db, limit),
        "asset": lambda: _asset_nodes(db, limit // 2),
        "fund": lambda: _fund_nodes(db),
        "family": lambda: _family_nodes(db, limit // 3),
        "lead": lambda: _lead_nodes(db, limit // 2),
        "project": lambda: _project_nodes(db, limit // 2),
    }

    for node_type, resolver in resolvers.items():
        if type_filter and node_type not in type_filter:
            continue
        for node in resolver():
            if node["id"] not in seen:
                nodes.append(node)
                seen.add(node["id"])

    # Build enrollment edges person -> course
    enrollments = db.query(models.Enrollment).limit(limit).all()
    for enrollment in enrollments:
        person_id = None
        if enrollment.user_id is not None:
            person = (
                db.query(models.Member)
                .filter(models.Member.user_id == enrollment.user_id)
                .first()
            )
            if person:
                person_id = f"person-{person.id}"
        if person_id and f"course-{enrollment.course_id}" in seen:
            edges.append(
                {
                    "from": person_id,
                    "to": f"course-{enrollment.course_id}",
                    "relation": "ENROLLED_IN",
                }
            )

    # Asset maintenance edges
    logs = db.query(models.MaintenanceLog).limit(limit).all()
    for log in logs:
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

    # Family membership edges
    family_members = (
        db.query(models.Member)
        .filter(models.Member.family_id.isnot(None))
        .limit(limit)
        .all()
    )
    for person in family_members:
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

    # Lead -> Pastor edges
    leads = (
        db.query(models.ConsolidationPipeline)
        .filter(models.ConsolidationPipeline.assigned_pastor_id.isnot(None))
        .limit(limit)
        .all()
    )
    for lead in leads:
        source = f"lead-{lead.id}"
        target = f"user-{lead.assigned_pastor_id}"
        if source in seen:
            if target not in seen:
                nodes.append(
                    {
                        "id": target,
                        "type": "pastor",
                        "label": f"Pastor #{lead.assigned_pastor_id}",
                        "detail": "Asignado",
                    }
                )
                seen.add(target)
            edges.append(
                {
                    "from": source,
                    "to": target,
                    "relation": "ASSIGNED_TO",
                }
            )

    # Project -> asset edges (when supplies reference asset)
    project_tasks = db.query(models.ProjectTask).limit(limit).all()
    for task in project_tasks:
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

    # Funds impact edges (donations)
    donations = db.query(models.Donation).limit(limit).all()
    for donation in donations:
        if donation.fund_id is not None:
            source = "fund-untracked"
            if donation.person_id is not None:
                source = f"person-{donation.person_id}"
                if source not in seen:
                    nodes.append(
                        {
                            "id": source,
                            "type": "donor",
                            "label": f"Donante {str(donation.person_id)[:6]}",
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
