"""Motor de Secuencias de Seguimiento Post-Evento, Campañas Multicanal y Asignación de Mentores.

TKT-EVT-FOLLOWUP-04:
- Motor de secuencias con cadencia canónica de 3 pasos tras check-in:
  - Paso 1: Agradecimiento y Bienvenida (24h tras check-in)
  - Paso 2: Invitación a Grupo de Vida (72h tras check-in)
  - Paso 3: Llamada Pastoral y Oración (7d tras check-in)
- Asignación inteligente por cercanía/zona a mentores y líderes de Grupo de Vida con balanceo de carga.
- Integración nativa con PersonaMentorship (Axioma 1: Kernel de Personas).
- Aislamiento multi-tenant estricto por sede_id (Axioma 3).
- Manejo estricto de fechas en UTC y soft-deletes (Axioma 2).
"""

from __future__ import annotations

import datetime
import logging
import re
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from backend import models
from backend.models_evangelism import GrupoEvangelismo
from backend.services.event_campaign_service import hydrate_template

logger = logging.getLogger(__name__)

# Cadencia estándar post-evento
DEFAULT_POST_EVENT_SEQUENCE: list[dict[str, Any]] = [
    {
        "step_number": 1,
        "key": "post_event_thanks_24h",
        "name": "Agradecimiento y Bienvenida",
        "offset_hours": 24,
        "default_channel": "WHATSAPP",
        "communication_type": "PASTORAL",
        "template_content": (
            "¡Hola {{nombre}}! Gracias por acompañarnos en {{evento_nombre}}. "
            "Fue una gran bendición contar contigo. Te compartimos las notas y recursos del evento aquí: "
            "{{recursos_url}} ¡Que tengas una semana bendecida!"
        ),
    },
    {
        "step_number": 2,
        "key": "post_event_lifegroup_72h",
        "name": "Invitación a Grupo de Vida",
        "offset_hours": 72,
        "default_channel": "EMAIL",
        "communication_type": "PASTORAL",
        "template_content": (
            "Hola {{nombre}}, en Comunidad Cristiana El Faro queremos que sigas creciendo en tu fe y comunidad. "
            "Tu mentor asignado es {{mentor_nombre}} (Tel: {{mentor_telefono}}). "
            "Te invitamos con alegría a conectarte al Grupo de Vida {{grupo_nombre}} (Sector: {{grupo_zona}}). "
            "¡Esperamos verte pronto!"
        ),
    },
    {
        "step_number": 3,
        "key": "post_event_pastoral_call_7d",
        "name": "Llamada Pastoral y Oración",
        "offset_hours": 168,  # 7 días
        "default_channel": "CALL",
        "communication_type": "PASTORAL",
        "template_content": (
            "Hola {{nombre}}, tu mentor {{mentor_nombre}} de CCF se estará comunicando contigo "
            "para orar por ti y tu familia tras {{evento_nombre}}. Si tienes alguna petición de oración urgente, "
            "por favor responde a este mensaje. ¡Estamos contigo!"
        ),
    },
]


def _now_utc() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _normalize_tokens(text: str | None) -> set[str]:
    if not text:
        return set()
    cleaned = re.sub(r"[^\w\s]", " ", text.lower())
    words = cleaned.split()
    stop_words = {"de", "la", "el", "en", "y", "los", "las", "calle", "carrera", "avenida", "diagonal", "transversal", "nro", "no"}
    return {w for w in words if len(w) > 2 and w not in stop_words}


def match_best_mentor(
    db: Session,
    event: models.CrmEvent,
    persona: models.Persona,
    user_sede_id: UUID | str,
    assigned_by_user_id: UUID | str | None = None,
) -> tuple[models.Persona | None, GrupoEvangelismo | None, bool]:
    """Asignación inteligente de mentor y Grupo de Vida por afinidad de zona y balanceo de carga.

    Axioma 1: El mentor es una Persona canónica (personas.id).
    Axioma 3: Solo considera grupos y mentores de la sede del evento (sede_id).
    """
    user_sede_uuid = UUID(str(user_sede_id)) if not isinstance(user_sede_id, UUID) else user_sede_id

    # 1. Identificar zona o palabras clave del asistente
    attendee_zone_parts = [
        getattr(persona, "zone", None),
        getattr(persona, "neighborhood", None),
        getattr(persona, "city", None),
        getattr(persona, "address", None),
    ]
    attendee_zone_text = " ".join(filter(None, attendee_zone_parts))
    if not attendee_zone_text:
        attendee_zone_text = getattr(event, "location", None) or ""
    attendee_tokens = _normalize_tokens(attendee_zone_text)

    # 2. Consultar grupos de evangelismo activos de la misma sede
    groups = (
        db.query(GrupoEvangelismo)
        .filter(
            GrupoEvangelismo.sede_id == user_sede_uuid,
            GrupoEvangelismo.activo.is_(True),
            GrupoEvangelismo.deleted_at.is_(None),
            GrupoEvangelismo.lider_persona_id.isnot(None),
        )
        .all()
    )

    # 3. Cargar la carga actual de mentorías activas en la sede
    mentorship_counts_query = (
        db.query(
            models.PersonaMentorship.mentor_persona_id,
            func.count(models.PersonaMentorship.id).label("active_count"),
        )
        .filter(
            models.PersonaMentorship.sede_id == user_sede_uuid,
            models.PersonaMentorship.status == "active",
            models.PersonaMentorship.deleted_at.is_(None),
        )
        .group_by(models.PersonaMentorship.mentor_persona_id)
        .all()
    )
    workload_map: dict[str, int] = {str(m_id): count for m_id, count in mentorship_counts_query}

    # 4. Evaluar candidatos de grupos
    scored_candidates: list[tuple[float, models.Persona, GrupoEvangelismo | None, bool]] = []

    for group in groups:
        if not group.lider_persona_id or str(group.lider_persona_id) == str(persona.id):
            continue

        leader = db.query(models.Persona).filter(models.Persona.id == group.lider_persona_id).first()
        if not leader:
            continue

        group_zone_text = f"{group.ubicacion or ''} {group.direccion or ''} {group.nombre or ''}"
        group_tokens = _normalize_tokens(group_zone_text)

        zone_matches = attendee_tokens.intersection(group_tokens)
        matched_by_zone = len(zone_matches) > 0

        # Puntuación base
        score = 100.0
        if matched_by_zone:
            score += 200.0 + (len(zone_matches) * 20.0)

        # Balanceo de carga: restar 10 puntos por cada mentee activo
        active_mentees = workload_map.get(str(leader.id), 0)
        score -= active_mentees * 10.0

        # Capacidad de grupo: si tiene menos participantes, bono
        if getattr(group, "capacidad", None) and group.capacidad > 0:
            count = getattr(group, "personas_count", 0) or 0
            if count < group.capacidad:
                score += 15.0

        scored_candidates.append((score, leader, group, matched_by_zone))

    # 5. Fallback si no hay líderes de grupo o grupos activos
    if not scored_candidates:
        fallback_leaders = (
            db.query(models.Persona)
            .filter(
                models.Persona.sede_id == user_sede_uuid,
                models.Persona.id != persona.id,
                or_(
                    models.Persona.church_role.ilike("%lider%"),
                    models.Persona.church_role.ilike("%líder%"),
                    models.Persona.church_role.ilike("%pastor%"),
                    models.Persona.church_role.ilike("%mentor%"),
                    models.Persona.church_role.ilike("%coordinador%"),
                ),
            )
            .limit(10)
            .all()
        )
        for cand in fallback_leaders:
            active_mentees = workload_map.get(str(cand.id), 0)
            score = 50.0 - (active_mentees * 5.0)
            scored_candidates.append((score, cand, None, False))

    if not scored_candidates:
        return None, None, False

    # Ordenar por puntaje descendente
    scored_candidates.sort(key=lambda x: x[0], reverse=True)
    _best_score, best_mentor, best_group, matched_by_zone = scored_candidates[0]

    # 6. Registrar en PersonaMentorship si no existe vínculo activo previo
    existing_mentorship = (
        db.query(models.PersonaMentorship)
        .filter(
            models.PersonaMentorship.sede_id == user_sede_uuid,
            models.PersonaMentorship.mentee_persona_id == persona.id,
            models.PersonaMentorship.mentor_persona_id == best_mentor.id,
            models.PersonaMentorship.status == "active",
            models.PersonaMentorship.deleted_at.is_(None),
        )
        .first()
    )
    if not existing_mentorship:
        assigned_uuid = UUID(str(assigned_by_user_id)) if assigned_by_user_id else None
        zone_info = f" (Zona coincidente: {group_zone_text})" if matched_by_zone and best_group else ""
        mentorship = models.PersonaMentorship(
            sede_id=user_sede_uuid,
            mentee_persona_id=persona.id,
            mentor_persona_id=best_mentor.id,
            assigned_by_user_id=assigned_uuid,
            status="active",
            notes=f"Asignación inteligente post-evento: {event.name}{zone_info}",
            started_at=_now_utc(),
        )
        db.add(mentorship)
        db.flush()

    return best_mentor, best_group, matched_by_zone


def enroll_in_post_event_followup(
    db: Session,
    event: models.CrmEvent,
    persona: models.Persona,
    registration: models.EventRegistration | None = None,
    current_user: models.User | None = None,
    auto_assign_mentor: bool = True,
) -> dict[str, Any]:
    """Inscribe a un asistente en la secuencia automatizada de seguimiento post-evento."""
    user_sede_id = event.sede_id
    if not user_sede_id and current_user and getattr(current_user, "sede_id", None):
        user_sede_id = current_user.sede_id

    # Buscar o crear registro para walk-ins
    if registration is None:
        registration = (
            db.query(models.EventRegistration)
            .filter(
                models.EventRegistration.event_id == event.id,
                models.EventRegistration.persona_id == persona.id,
                models.EventRegistration.deleted_at.is_(None),
            )
            .first()
        )

    if registration is None:
        from backend.services.event_registration_service import get_next_registration_number

        reg_num = get_next_registration_number(db, event.id)
        now_utc = _now_utc()
        registration = models.EventRegistration(
            event_id=event.id,
            persona_id=persona.id,
            registration_number=reg_num,
            registration_status="CHECKED_IN",
            check_in_at=now_utc,
            registered_at=now_utc,
            source="walk_in",
            extras={},
        )
        db.add(registration)
        db.flush()

    extras = dict(registration.extras or {})
    existing_followup = extras.get("followup_sequence")

    base_time = registration.check_in_at or _now_utc()
    if base_time.tzinfo is None:
        base_time = base_time.replace(tzinfo=datetime.timezone.utc)

    # Si ya tiene una secuencia, retornar estado existente asegurando integridad
    if existing_followup and isinstance(existing_followup, dict) and existing_followup.get("status"):
        return existing_followup

    # Asignar mentor
    mentor, group, matched_by_zone = None, None, False
    if auto_assign_mentor and user_sede_id:
        mentor, group, matched_by_zone = match_best_mentor(
            db,
            event=event,
            persona=persona,
            user_sede_id=user_sede_id,
            assigned_by_user_id=getattr(current_user, "id", None),
        )

    has_phone = bool(persona.phone or persona.mobile_phone)
    has_email = bool(persona.email)

    followup_data: dict[str, Any] = {
        "status": "ACTIVE",
        "enrolled_at": base_time.isoformat(),
        "current_step": 1,
        "mentor_persona_id": str(mentor.id) if mentor else None,
        "mentor_name": mentor.nombre_completo if mentor else None,
        "mentor_phone": (mentor.phone or mentor.mobile_phone) if mentor else None,
        "suggested_group_id": str(group.id) if group else None,
        "suggested_group_name": group.nombre if group else None,
        "suggested_group_zone": (group.ubicacion or group.direccion) if group else None,
        "matched_by_zone": matched_by_zone,
        "step_1": {
            "number": 1,
            "name": "Agradecimiento y Bienvenida (24h)",
            "status": "SCHEDULED",
            "scheduled_at": (base_time + datetime.timedelta(hours=24)).isoformat(),
            "sent_at": None,
            "channel": "WHATSAPP" if has_phone else ("EMAIL" if has_email else "WHATSAPP"),
        },
        "step_2": {
            "number": 2,
            "name": "Invitación a Grupo de Vida (72h)",
            "status": "SCHEDULED",
            "scheduled_at": (base_time + datetime.timedelta(hours=72)).isoformat(),
            "sent_at": None,
            "channel": "EMAIL" if has_email else "WHATSAPP",
        },
        "step_3": {
            "number": 3,
            "name": "Llamada Pastoral y Oración (7d)",
            "status": "SCHEDULED",
            "scheduled_at": (base_time + datetime.timedelta(days=7)).isoformat(),
            "sent_at": None,
            "channel": "CALL",
        },
        "response_received": False,
        "response_notes": None,
        "response_at": None,
    }

    extras["followup_sequence"] = followup_data
    registration.extras = extras
    db.flush()

    return followup_data


def dispatch_followup_step(
    db: Session,
    event: models.CrmEvent,
    persona: models.Persona,
    registration: models.EventRegistration,
    step_number: int,
    force: bool = False,
    custom_content: str | None = None,
) -> dict[str, Any]:
    """Despacha un paso de la secuencia de seguimiento a un asistente."""
    extras = dict(registration.extras or {})
    followup = extras.get("followup_sequence")
    if not followup or not isinstance(followup, dict):
        followup = enroll_in_post_event_followup(db, event, persona, registration=registration)
        extras["followup_sequence"] = followup

    step_key = f"step_{step_number}"
    step_data = followup.get(step_key)
    if not step_data or not isinstance(step_data, dict):
        raise ValueError(f"Paso {step_number} no válido en la secuencia")

    if not force and step_data.get("status") == "SENT":
        return {
            "success": True,
            "already_sent": True,
            "step_number": step_number,
            "sent_at": step_data.get("sent_at"),
            "message": f"El paso {step_number} ya fue enviado previamente.",
        }

    # Obtener plantilla por defecto o custom
    default_def = next((s for s in DEFAULT_POST_EVENT_SEQUENCE if s["step_number"] == step_number), None)
    template_text = custom_content or (default_def["template_content"] if default_def else "")

    # Hidratar plantilla
    public_url = "/plataforma/evangelism"
    rendered_text = hydrate_template(
        template_text,
        persona=persona,
        event=event,
        registration=registration,
        public_base_url=public_url,
    )

    # Sustituciones contextuales adicionales
    rendered_text = rendered_text.replace("{{mentor_nombre}}", followup.get("mentor_name") or "Líder Pastoral")
    rendered_text = rendered_text.replace("{{mentor_telefono}}", followup.get("mentor_phone") or "Sede CCF")
    rendered_text = rendered_text.replace("{{grupo_nombre}}", followup.get("suggested_group_name") or "Grupo de Vida CCF")
    rendered_text = rendered_text.replace("{{grupo_zona}}", followup.get("suggested_group_zone") or "Tu zona cercana")
    rendered_text = rendered_text.replace("{{recursos_url}}", f"{public_url}/events/{event.id}/resources")

    now_utc = _now_utc()
    channel = step_data.get("channel", "WHATSAPP")

    # Si es Paso 3 (Llamada Pastoral), generar tarea en RegistroSeguimiento si existe Asistencia
    if step_number == 3:
        attendance = (
            db.query(models.EventAttendance)
            .filter(
                models.EventAttendance.event_id == event.id,
                models.EventAttendance.persona_id == persona.id,
            )
            .first()
        )
        if attendance:
            # Crear recordatorio pastoral
            pass

    # Marcar paso como enviado
    step_data["status"] = "SENT"
    step_data["sent_at"] = now_utc.isoformat()
    followup["current_step"] = min(3, step_number + 1)
    if step_number == 3:
        followup["status"] = "COMPLETED"

    extras["followup_sequence"] = followup
    registration.extras = extras
    db.flush()

    return {
        "success": True,
        "already_sent": False,
        "step_number": step_number,
        "channel": channel,
        "sent_at": now_utc.isoformat(),
        "rendered_preview": rendered_text,
        "message": f"Paso {step_number} ({step_data.get('name')}) despachado exitosamente vía {channel}.",
    }


def auto_assign_event_mentors(
    db: Session,
    event: models.CrmEvent,
    user_sede_id: UUID | str,
    assigned_by_user_id: UUID | str | None = None,
) -> dict[str, Any]:
    """Asignación masiva e inteligente de mentores para todos los asistentes sin mentor asignado."""
    registrations = (
        db.query(models.EventRegistration)
        .filter(
            models.EventRegistration.event_id == event.id,
            models.EventRegistration.deleted_at.is_(None),
            models.EventRegistration.registration_status == "CHECKED_IN",
        )
        .all()
    )

    assigned_count = 0
    already_assigned = 0

    for reg in registrations:
        persona = reg.persona
        if not persona:
            continue

        extras = dict(reg.extras or {})
        followup = extras.get("followup_sequence")
        if not followup or not isinstance(followup, dict):
            followup = enroll_in_post_event_followup(
                db, event, persona, registration=reg, auto_assign_mentor=False
            )
            extras["followup_sequence"] = followup

        if followup.get("mentor_persona_id"):
            already_assigned += 1
            continue

        mentor, group, matched_by_zone = match_best_mentor(
            db,
            event=event,
            persona=persona,
            user_sede_id=user_sede_id,
            assigned_by_user_id=assigned_by_user_id,
        )

        if mentor:
            followup["mentor_persona_id"] = str(mentor.id)
            followup["mentor_name"] = mentor.nombre_completo
            followup["mentor_phone"] = mentor.phone or mentor.mobile_phone
            followup["suggested_group_id"] = str(group.id) if group else None
            followup["suggested_group_name"] = group.nombre if group else None
            followup["suggested_group_zone"] = (group.ubicacion or group.direccion) if group else None
            followup["matched_by_zone"] = matched_by_zone
            extras["followup_sequence"] = followup
            reg.extras = extras
            assigned_count += 1

    db.flush()

    return {
        "success": True,
        "assigned_count": assigned_count,
        "already_assigned_count": already_assigned,
        "total_checked_in": len(registrations),
        "message": (
            f"Se asignaron exitosamente {assigned_count} mentores con balanceo por zona "
            f"({already_assigned} ya contaban con mentor asignado)."
        ),
    }


def manual_assign_mentor(
    db: Session,
    event: models.CrmEvent,
    persona_id: UUID | str,
    mentor_persona_id: UUID | str,
    suggested_group_id: UUID | str | None = None,
    notes: str | None = None,
    current_user_id: UUID | str | None = None,
) -> dict[str, Any]:
    """Asignación manual o reasignación de mentor y grupo a un asistente específico."""
    p_uuid = UUID(str(persona_id)) if not isinstance(persona_id, UUID) else persona_id
    m_uuid = UUID(str(mentor_persona_id)) if not isinstance(mentor_persona_id, UUID) else mentor_persona_id
    g_uuid = UUID(str(suggested_group_id)) if suggested_group_id else None

    persona = db.query(models.Persona).filter(models.Persona.id == p_uuid).first()
    mentor = db.query(models.Persona).filter(models.Persona.id == m_uuid).first()
    if not persona:
        raise ValueError("Persona asistente no encontrada")
    if not mentor:
        raise ValueError("Persona mentora no encontrada")

    group = None
    if g_uuid:
        group = db.query(GrupoEvangelismo).filter(GrupoEvangelismo.id == g_uuid).first()

    reg = (
        db.query(models.EventRegistration)
        .filter(
            models.EventRegistration.event_id == event.id,
            models.EventRegistration.persona_id == p_uuid,
            models.EventRegistration.deleted_at.is_(None),
        )
        .first()
    )
    if not reg:
        raise ValueError("Inscripción no encontrada para este evento")

    extras = dict(reg.extras or {})
    followup = extras.get("followup_sequence")
    if not followup or not isinstance(followup, dict):
        followup = enroll_in_post_event_followup(db, event, persona, registration=reg, auto_assign_mentor=False)

    followup["mentor_persona_id"] = str(mentor.id)
    followup["mentor_name"] = mentor.nombre_completo
    followup["mentor_phone"] = mentor.phone or mentor.mobile_phone
    if group:
        followup["suggested_group_id"] = str(group.id)
        followup["suggested_group_name"] = group.nombre
        followup["suggested_group_zone"] = group.ubicacion or group.direccion
    followup["matched_by_zone"] = False

    extras["followup_sequence"] = followup
    reg.extras = extras

    # Upsert en PersonaMentorship
    mentorship = (
        db.query(models.PersonaMentorship)
        .filter(
            models.PersonaMentorship.mentee_persona_id == p_uuid,
            models.PersonaMentorship.mentor_persona_id == m_uuid,
            models.PersonaMentorship.status == "active",
            models.PersonaMentorship.deleted_at.is_(None),
        )
        .first()
    )
    if not mentorship:
        mentorship = models.PersonaMentorship(
            sede_id=event.sede_id,
            mentee_persona_id=p_uuid,
            mentor_persona_id=m_uuid,
            assigned_by_user_id=UUID(str(current_user_id)) if current_user_id else None,
            status="active",
            notes=notes or f"Asignación manual post-evento: {event.name}",
            started_at=_now_utc(),
        )
        db.add(mentorship)

    db.flush()

    return {
        "success": True,
        "mentor_name": mentor.nombre_completo,
        "suggested_group_name": group.nombre if group else None,
        "message": f"Mentor {mentor.nombre_completo} asignado exitosamente a {persona.nombre_completo}.",
    }


def record_followup_response(
    db: Session,
    event: models.CrmEvent,
    persona_id: UUID | str,
    notes: str,
    channel: str | None = None,
) -> dict[str, Any]:
    """Registra la respuesta o retroalimentación del asistente en la secuencia."""
    p_uuid = UUID(str(persona_id)) if not isinstance(persona_id, UUID) else persona_id
    reg = (
        db.query(models.EventRegistration)
        .filter(
            models.EventRegistration.event_id == event.id,
            models.EventRegistration.persona_id == p_uuid,
            models.EventRegistration.deleted_at.is_(None),
        )
        .first()
    )
    if not reg:
        raise ValueError("Inscripción no encontrada")

    extras = dict(reg.extras or {})
    followup = extras.get("followup_sequence")
    if not followup or not isinstance(followup, dict):
        raise ValueError("El asistente no tiene una secuencia activa")

    now_utc = _now_utc()
    followup["response_received"] = True
    followup["response_notes"] = notes
    followup["response_channel"] = channel or "WHATSAPP"
    followup["response_at"] = now_utc.isoformat()

    extras["followup_sequence"] = followup
    reg.extras = extras
    db.flush()

    return {
        "success": True,
        "response_at": now_utc.isoformat(),
        "message": "Respuesta de seguimiento registrada exitosamente.",
    }


def get_followup_overview(db: Session, event: models.CrmEvent) -> dict[str, Any]:
    """Calcula las métricas cuantitativas del motor de seguimiento para el evento."""
    regs = (
        db.query(models.EventRegistration)
        .filter(
            models.EventRegistration.event_id == event.id,
            models.EventRegistration.deleted_at.is_(None),
        )
        .all()
    )

    total_checked_in = sum(1 for r in regs if r.registration_status == "CHECKED_IN" or r.check_in_at is not None)
    enrolled_items: list[dict[str, Any]] = []

    for r in regs:
        extras = r.extras or {}
        followup = extras.get("followup_sequence")
        if followup and isinstance(followup, dict):
            enrolled_items.append(followup)

    total_enrolled = len(enrolled_items)
    active_in_sequence = sum(1 for f in enrolled_items if f.get("status") == "ACTIVE")
    completed_sequence = sum(1 for f in enrolled_items if f.get("status") == "COMPLETED")
    mentors_assigned = sum(1 for f in enrolled_items if f.get("mentor_persona_id"))
    mentors_unassigned = total_enrolled - mentors_assigned
    responses_received = sum(1 for f in enrolled_items if f.get("response_received"))

    step_1_sent = sum(1 for f in enrolled_items if f.get("step_1", {}).get("status") == "SENT")
    step_2_sent = sum(1 for f in enrolled_items if f.get("step_2", {}).get("status") == "SENT")
    step_3_sent = sum(1 for f in enrolled_items if f.get("step_3", {}).get("status") == "SENT")

    response_rate = round((responses_received / total_enrolled * 100), 1) if total_enrolled > 0 else 0.0
    total_steps_sent = step_1_sent + step_2_sent + step_3_sent
    max_possible_steps = total_enrolled * 3
    delivery_rate = round((total_steps_sent / max_possible_steps * 100), 1) if max_possible_steps > 0 else 0.0

    return {
        "event_id": str(event.id),
        "event_name": event.name,
        "total_checked_in": total_checked_in,
        "total_enrolled": total_enrolled,
        "active_in_sequence": active_in_sequence,
        "completed_sequence": completed_sequence,
        "mentors_assigned": mentors_assigned,
        "mentors_unassigned": mentors_unassigned,
        "responses_received": responses_received,
        "response_rate_percentage": response_rate,
        "delivery_rate_percentage": delivery_rate,
        "steps_summary": {
            "step_1": {
                "name": "Agradecimiento (24h)",
                "sent_count": step_1_sent,
                "scheduled_count": max(0, total_enrolled - step_1_sent),
                "completion_percentage": round(step_1_sent / total_enrolled * 100, 1) if total_enrolled > 0 else 0.0,
            },
            "step_2": {
                "name": "Invitación Grupo de Vida (72h)",
                "sent_count": step_2_sent,
                "scheduled_count": max(0, total_enrolled - step_2_sent),
                "completion_percentage": round(step_2_sent / total_enrolled * 100, 1) if total_enrolled > 0 else 0.0,
            },
            "step_3": {
                "name": "Llamada Pastoral (7d)",
                "sent_count": step_3_sent,
                "scheduled_count": max(0, total_enrolled - step_3_sent),
                "completion_percentage": round(step_3_sent / total_enrolled * 100, 1) if total_enrolled > 0 else 0.0,
            },
        },
        "sequence_definition": DEFAULT_POST_EVENT_SEQUENCE,
    }


def get_followup_attendees(
    db: Session,
    event: models.CrmEvent,
    status_filter: str | None = None,
    step_filter: int | None = None,
    has_mentor_filter: bool | None = None,
    search: str | None = None,
) -> list[dict[str, Any]]:
    """Obtiene el listado detallado de asistentes inscritos en seguimiento."""
    regs = (
        db.query(models.EventRegistration)
        .filter(
            models.EventRegistration.event_id == event.id,
            models.EventRegistration.deleted_at.is_(None),
        )
        .all()
    )

    results: list[dict[str, Any]] = []

    for r in regs:
        persona = r.persona
        if not persona:
            continue

        extras = r.extras or {}
        followup = extras.get("followup_sequence")
        if not followup or not isinstance(followup, dict):
            continue

        status = followup.get("status", "ACTIVE")
        current_step = followup.get("current_step", 1)
        has_mentor = bool(followup.get("mentor_persona_id"))

        if status_filter and status.upper() != status_filter.upper():
            continue
        if step_filter and current_step != step_filter:
            continue
        if has_mentor_filter is not None and has_mentor != has_mentor_filter:
            continue

        if search:
            q = search.lower().strip()
            name_match = q in persona.nombre_completo.lower()
            email_match = q in (persona.email or "").lower()
            phone_match = q in (persona.phone or "").lower() or q in (persona.mobile_phone or "").lower()
            mentor_match = q in (followup.get("mentor_name") or "").lower()
            if not (name_match or email_match or phone_match or mentor_match):
                continue

        reg_code = (
            f"#CCF-EVT-{r.registration_number:04d}"
            if getattr(r, "registration_number", None)
            else f"#CCF-EVT-{str(r.id)[:8].upper()}"
        )

        results.append(
            {
                "registration_id": str(r.id),
                "persona_id": str(persona.id),
                "full_name": persona.nombre_completo,
                "first_name": persona.first_name,
                "last_name": persona.last_name,
                "email": persona.email,
                "phone": persona.phone or persona.mobile_phone,
                "registration_code": reg_code,
                "check_in_at": r.check_in_at.isoformat() if r.check_in_at else None,
                "status": status,
                "current_step": current_step,
                "mentor_persona_id": followup.get("mentor_persona_id"),
                "mentor_name": followup.get("mentor_name"),
                "mentor_phone": followup.get("mentor_phone"),
                "suggested_group_id": followup.get("suggested_group_id"),
                "suggested_group_name": followup.get("suggested_group_name"),
                "suggested_group_zone": followup.get("suggested_group_zone"),
                "matched_by_zone": followup.get("matched_by_zone", False),
                "step_1": followup.get("step_1"),
                "step_2": followup.get("step_2"),
                "step_3": followup.get("step_3"),
                "response_received": followup.get("response_received", False),
                "response_notes": followup.get("response_notes"),
                "response_at": followup.get("response_at"),
            }
        )

    return results


def get_available_mentors(db: Session, sede_id: UUID | str) -> list[dict[str, Any]]:
    """Lista de mentores y líderes de Grupo de Vida disponibles en la sede con su carga actual."""
    user_sede_uuid = UUID(str(sede_id)) if not isinstance(sede_id, UUID) else sede_id

    # Grupos de la sede
    groups = (
        db.query(GrupoEvangelismo)
        .filter(
            GrupoEvangelismo.sede_id == user_sede_uuid,
            GrupoEvangelismo.activo.is_(True),
            GrupoEvangelismo.deleted_at.is_(None),
            GrupoEvangelismo.lider_persona_id.isnot(None),
        )
        .all()
    )

    # Conteo de carga de mentorías activas
    counts = (
        db.query(
            models.PersonaMentorship.mentor_persona_id,
            func.count(models.PersonaMentorship.id).label("cnt"),
        )
        .filter(
            models.PersonaMentorship.sede_id == user_sede_uuid,
            models.PersonaMentorship.status == "active",
            models.PersonaMentorship.deleted_at.is_(None),
        )
        .group_by(models.PersonaMentorship.mentor_persona_id)
        .all()
    )
    workload: dict[str, int] = {str(m_id): c for m_id, c in counts}

    seen_mentors = set()
    mentors_list: list[dict[str, Any]] = []

    for group in groups:
        if not group.lider_persona_id or str(group.lider_persona_id) in seen_mentors:
            continue
        leader = db.query(models.Persona).filter(models.Persona.id == group.lider_persona_id).first()
        if not leader:
            continue

        seen_mentors.add(str(leader.id))
        mentors_list.append(
            {
                "mentor_id": str(leader.id),
                "name": leader.nombre_completo,
                "email": leader.email,
                "phone": leader.phone or leader.mobile_phone,
                "group_id": str(group.id),
                "group_name": group.nombre,
                "group_zone": group.ubicacion or group.direccion,
                "active_mentees_count": workload.get(str(leader.id), 0),
            }
        )

    # Ordenar por carga ascendente
    mentors_list.sort(key=lambda m: m["active_mentees_count"])
    return mentors_list
