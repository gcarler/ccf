"""Persona timeline construction."""
import datetime as dt

from sqlalchemy.orm import Session

from backend import models
from backend.crud._utils import _to_uuid


def get_persona_timeline(db: Session, persona_id: str):
    persona = db.query(models.Persona).filter(models.Persona.id == _to_uuid(persona_id)).first()
    if not persona:
        return []

    timeline = []

    timeline.append(
        {
            "type": "participation",
            "title": "Ingreso a la Familia CCF",
            "description": f"Registro formal como {persona.church_role}.",
            "date": persona.created_at.isoformat(),
            "icon": "Sparkles",
            "color": "bg-purple-500",
        }
    )

    enrollments = db.query(models.Enrollment).filter(models.Enrollment.persona_id == persona.id).all()
    for en in enrollments:
        timeline.append(
            {
                "type": "academy",
                "title": "Inscripción Academia",
                "description": f"Inició el curso {en.course.title if en.course else 'de formación'}.",
                "date": en.created_at.isoformat(),
                "icon": "GraduationCap",
                "color": "bg-emerald-500",
            }
        )
        if en.certificate_issued:
            timeline.append(
                {
                    "type": "certificate",
                    "title": "Certificación Obtenida",
                    "description": f"Completó con éxito el curso: {en.course.title if en.course else 'de formación'}.",
                    "date": (en.created_at + dt.timedelta(days=30)).isoformat(),
                    "icon": "Award",
                    "color": "bg-amber-500",
                }
            )

    ministries = db.query(models.PersonaMinistryAssignment).filter(models.PersonaMinistryAssignment.persona_id == persona_id).all()
    for mm in ministries:
        timeline.append(
            {
                "type": "ministry",
                "title": "Vinculación Ministerial",
                "description": f"Se integró al ministerio de {mm.name}.",
                "date": (mm.created_at.isoformat() if mm.created_at else persona.created_at.isoformat()),
                "icon": "ShieldCheck",
                "color": "bg-indigo-600",
            }
        )

    sessions = db.query(models.CounselingTicket).filter(models.CounselingTicket.persona_id == persona_id).all()
    for s in sessions:
        timeline.append(
            {
                "type": "counseling",
                "title": "Sesión Pastoral",
                "description": f"Atención espiritual: {s.subject}.",
                "date": s.created_at.isoformat(),
                "icon": "Heart",
                "color": "bg-rose-500",
            }
        )

    calls = db.query(models.CommunicationLog).filter(models.CommunicationLog.persona_id == persona_id).all()
    for c in calls:
        timeline.append(
            {
                "type": "communication",
                "title": "Seguimiento Pastoral",
                "description": f"Contacto vía {c.channel}: {c.content[:50]}...",
                "date": c.created_at.isoformat(),
                "icon": "Phone",
                "color": "bg-blue-500",
            }
        )

    timeline.sort(key=lambda x: x["date"], reverse=True)
    return timeline
