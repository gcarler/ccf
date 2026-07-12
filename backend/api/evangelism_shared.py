from __future__ import annotations

import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import inspect, or_
from sqlalchemy.orm import Session, load_only

from backend import models
from backend.services.messaging_outcomes import DELIVERED_OUTCOMES, CommunicationOutcome

ABSENTEES_PREVIEW_LIMIT = 50
ABSENCE_REASON_LABELS = {
    "weather": "Clima",
    "work": "Trabajo",
    "health": "Salud",
    "family": "Familia",
    "other": "Otro",
}

ATTENDED_STATES = {"ASISTIO", "Presente", "present", "presente", "primera_vez", "first_time"}
ABSENT_STATES = {"FALTO", "Ausente", "absent", "ausente"}
EXCUSED_STATES = {"EXCUSA", "Excusa", "excusa"}
FIRST_TIME_STATES = {"primera_vez", "first_time"}


def sessions_grupo_has_estado_habilitacion(db: Session) -> bool:
    """Return whether the live schema exposes ``sesiones_grupo.estado_habilitacion``."""
    return "estado_habilitacion" in _sessions_grupo_live_column_names(db)


def _sessions_grupo_live_column_names(db: Session) -> set[str]:
    bind = db.get_bind()
    if bind is None:
        return set()
    try:
        columns = inspect(bind).get_columns("sesiones_grupo")
    except Exception:
        return set()
    return {str(column.get("name")) for column in columns if column.get("name")}


def session_estado_habilitacion(session, default: str = "HABILITADO") -> str:
    """Read ``estado_habilitacion`` without triggering a deferred load."""
    value = session_read_value(session, "estado_habilitacion", default)
    return value or default


def session_read_value(session, field: str, default=None):
    """Read a mapped attribute from the loaded instance state only.

    This avoids deferred-load queries against columns that may not exist in
    the live schema while still returning a sensible default when the field
    is absent or not loaded.
    """
    return getattr(session, "__dict__", {}).get(field, default)


def session_read_only_options(db: Session):
    """Build a load_only option that tolerates older schemas safely."""
    from backend.models import SesionGrupo

    live_columns = _sessions_grupo_live_column_names(db)
    desired_columns = [
        "id",
        "grupo_id",
        "fecha_sesion",
        "estado",
        "motivo_cancelacion",
        "tema_estudio",
        "notas_lider",
        "offering_amount",
        "season_id",
        "created_at",
        "deleted_at",
        "reported_at",
        "novelty_type",
        "novelty_detail",
        "reported_by_persona_id",
        "report_deadline",
        "estado_habilitacion",
        "habilitado_por",
        "habilitado_en",
    ]
    columns = [
        getattr(SesionGrupo, column_name)
        for column_name in desired_columns
        if column_name in live_columns and hasattr(SesionGrupo, column_name)
    ]
    if not columns:
        columns = [SesionGrupo.id, SesionGrupo.grupo_id, SesionGrupo.fecha_sesion]
    return load_only(*columns)


def normalize_attendance_status(value) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {state.lower() for state in FIRST_TIME_STATES}:
        return "present"
    if normalized in {state.lower() for state in ATTENDED_STATES}:
        return "present"
    if normalized in {state.lower() for state in ABSENT_STATES}:
        return "absent"
    if normalized in {state.lower() for state in EXCUSED_STATES}:
        return "excused"
    return normalized


def is_attended_status(value) -> bool:
    return normalize_attendance_status(value) in {"present", "first_time"}


def is_absent_status(value) -> bool:
    return normalize_attendance_status(value) == "absent"


def is_excused_status(value) -> bool:
    return normalize_attendance_status(value) == "excused"


def _is_crm_admin_or_pastor(user) -> bool:
    """Check if user has admin/pastor role (shared helper)."""
    from backend.core.permissions import normalize_role

    role = normalize_role(str(getattr(user, "role", "")))
    if not role and hasattr(user, "rol_plataforma") and user.rol_plataforma:
        role = normalize_role(user.rol_plataforma.nombre)
    return role in {"admin", "administrador", "pastor", "coordinador"}


def _get_persona_for_user(db: Session, user_id) -> Optional[models.Persona]:
    """Resolve user_id to Persona record (shared helper)."""
    import uuid as _uuid

    try:
        uid = _uuid.UUID(str(user_id))
    except (TypeError, ValueError, AttributeError):
        return None
    return db.query(models.Persona).filter(models.Persona.id == uid).first()


def _can_manage_grupo(db: Session, user, house) -> bool:
    """Check if user can manage a group (shared helper)."""
    if _is_crm_admin_or_pastor(user):
        return True
    persona = _get_persona_for_user(db, user.id)
    if not persona:
        return False
    return persona.id in {house.leader_persona_id, house.assistant_persona_id}


def _check_absence_trigger(db: Session, session_id: UUID, sede_id):
    """If a persona has 3 consecutive absences, create N2 task in Consolidation."""
    from backend.models import (
        Asistencia,
        GrupoEvangelismo,
        ParticipanteGrupo,
        SesionGrupo,
    )
    from backend.models_crm import Persona
    from backend.models_evangelism import EstadoAsistenciaEnum

    session = (
        db.query(SesionGrupo)
        .options(
            load_only(
                SesionGrupo.id,
                SesionGrupo.grupo_id,
                SesionGrupo.fecha_sesion,
                SesionGrupo.deleted_at,
            )
        )
        .join(GrupoEvangelismo, GrupoEvangelismo.id == SesionGrupo.grupo_id)
        .filter(
            SesionGrupo.id == session_id,
            GrupoEvangelismo.sede_id == sede_id,
            GrupoEvangelismo.deleted_at.is_(None),
            SesionGrupo.deleted_at.is_(None),
        )
        .first()
    )
    if not session:
        return

    house = (
        db.query(GrupoEvangelismo)
        .filter(GrupoEvangelismo.id == session.grupo_id)
        .first()
    )
    if not house:
        return

    # Get last 3 sessions for this house
    recent_sessions = (
        db.query(SesionGrupo)
        .options(
            load_only(
                SesionGrupo.id,
                SesionGrupo.grupo_id,
                SesionGrupo.fecha_sesion,
                SesionGrupo.deleted_at,
            )
        )
        .filter(
            SesionGrupo.grupo_id == house.id,
            SesionGrupo.deleted_at.is_(None),
        )
        .order_by(SesionGrupo.fecha_sesion.desc())
        .limit(3)
        .all()
    )

    if len(recent_sessions) < 3:
        return  # Not enough data

    expected_personas = (
        db.query(ParticipanteGrupo.persona_id)
        .filter(
            ParticipanteGrupo.grupo_id == house.id,
            ParticipanteGrupo.deleted_at.is_(None),
            ParticipanteGrupo.activo.is_(True),
        )
        .all()
    )
    for (persona_id,) in expected_personas:
        absent_count = 0
        for s in recent_sessions:
            att = (
                db.query(Asistencia)
                .filter(
                    Asistencia.sesion_id == s.id,
                    Asistencia.persona_id == persona_id,
                    Asistencia.deleted_at.is_(None),
                    Asistencia.estado == EstadoAsistenciaEnum.FALTO.value,
                )
                .first()
            )
            if att:
                absent_count += 1

        if absent_count >= 3:
            # Create N2 task in Consolidation
            p = db.query(Persona).filter(Persona.id == persona_id).first()
            if not p:
                continue
            from backend.models_crm import SupportTicket

            ticket = SupportTicket(
                user_id=persona_id,
                subject=f"Inasistencia recurrente: {p.nombre_completo}",
                description=(
                    f"{p.nombre_completo} ha faltado 3 sesiones consecutivas en {house.name}. "
                    "Requiere contacto pastoral. Severidad sugerida: N2."
                ),
                status="open",
            )
            db.add(ticket)
            db.commit()


def _check_first_time_lead_trigger(db: Session, session_id: UUID):
    """If a first_time attendee is recorded, mark as LEAD_NUEVO in CRM."""
    from backend.models_crm import Persona
    from backend.models_evangelism import Asistencia

    first_timers = (
        db.query(Asistencia)
        .filter(
            Asistencia.sesion_id == session_id,
            or_(
                Asistencia.es_primera_vez.is_(True),
                Asistencia.estado.in_(FIRST_TIME_STATES),
            ),
        )
        .all()
    )

    for att in first_timers:
        p = db.query(Persona).filter(Persona.id == att.persona_id).first()
        if p and str(getattr(p, "church_role", "")).lower() not in ("lead", "lead_nuevo"):
            try:
                p.church_role = "lead_nuevo"
                db.commit()
            except Exception:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(
                    "Failed to update church_role to lead_nuevo for persona %s",
                    att.persona_id,
                    exc_info=True,
                )


def utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def parse_session_date(value: object) -> datetime.date:
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            raise ValueError("session_date is required")
        try:
            return datetime.date.fromisoformat(raw[:10])
        except ValueError as exc:
            raise ValueError("Invalid session_date") from exc
    raise ValueError("Invalid session_date")


def normalize_role_scope_payload(payload: dict) -> dict:
    normalized = dict(payload)
    raw_role_ids = normalized.get("target_role_ids")
    raw_persona_ids = normalized.get("target_persona_ids")
    normalized_role_ids: list[str] = []
    normalized_persona_ids: list[str] = []
    if isinstance(raw_role_ids, list):
        for raw_role_id in raw_role_ids:
            try:
                normalized_role_ids.append(str(UUID(str(raw_role_id))))
            except (TypeError, ValueError):
                continue
    normalized_role_ids = list(dict.fromkeys(normalized_role_ids))
    if isinstance(raw_persona_ids, list):
        for raw_persona_id in raw_persona_ids:
            if isinstance(raw_persona_id, str) and raw_persona_id.strip():
                normalized_persona_ids.append(raw_persona_id.strip())
    normalized_persona_ids = list(dict.fromkeys(normalized_persona_ids))

    if normalized.get("target_audience") == "ROLE":
        if normalized_role_ids:
            normalized["target_role_ids"] = normalized_role_ids
            normalized["target_role_id"] = normalized_role_ids[0]
        elif normalized.get("target_role_id") is not None:
            try:
                normalized_role_id = str(UUID(str(normalized["target_role_id"])))
            except (TypeError, ValueError):
                normalized_role_id = None
            normalized["target_role_id"] = UUID(normalized_role_id) if normalized_role_id else None
            normalized["target_role_ids"] = (
                [normalized_role_id] if normalized_role_id is not None else None
            )
        else:
            normalized["target_role_ids"] = None
            normalized["target_role_id"] = None
        normalized["target_persona_ids"] = None
    elif normalized.get("target_audience") == "MANUAL":
        normalized["target_role_ids"] = None
        normalized["target_role_id"] = None
        normalized["target_persona_ids"] = normalized_persona_ids or None
    else:
        normalized["target_role_ids"] = None
        normalized["target_role_id"] = None
        normalized["target_persona_ids"] = None

    return normalized


def resolve_target_role_ids(event: models.CrmEvent) -> list[UUID]:
    role_ids = []
    if isinstance(event.target_role_ids, list):
        for raw_role_id in event.target_role_ids:
            try:
                role_ids.append(UUID(str(raw_role_id)))
            except (TypeError, ValueError):
                continue
    if not role_ids and event.target_role_id is not None:
        role_ids.append(UUID(str(event.target_role_id)))
    return list(dict.fromkeys(role_ids))


def get_expected_personas_for_event(
    db: Session, event: models.CrmEvent, sede_id=None
) -> list[models.Persona]:
    event_sede_id = sede_id or getattr(event, "sede_id", None)
    if event.target_audience == "ROLE":
        role_ids = resolve_target_role_ids(event)
        if not role_ids:
            return []
        role_names = [
            row[0]
            for row in db.query(models.RoleDefinition.name)
            .filter(models.RoleDefinition.id.in_(role_ids))
            .all()
        ]
        if not role_names:
            return []
        q = db.query(models.Persona).filter(models.Persona.church_role.in_(role_names))
        if event_sede_id:
            q = q.filter(models.Persona.sede_id == event_sede_id)
        return q.order_by(models.Persona.nombre_completo.asc()).all()
    if event.target_audience == "MANUAL":
        import uuid
        persona_ids = []
        if isinstance(event.target_persona_ids, list):
            for raw_persona_id in event.target_persona_ids:
                if isinstance(raw_persona_id, uuid.UUID):
                    persona_ids.append(raw_persona_id)
                elif isinstance(raw_persona_id, str) and raw_persona_id.strip():
                    try:
                        persona_ids.append(uuid.UUID(raw_persona_id.strip()))
                    except ValueError:
                        continue
        persona_ids = list(dict.fromkeys(persona_ids))
        if not persona_ids:
            return []
        q = db.query(models.Persona).filter(models.Persona.id.in_(persona_ids))
        if event_sede_id:
            q = q.filter(models.Persona.sede_id == event_sede_id)
        return q.order_by(models.Persona.nombre_completo.asc()).all()
    # Fallback: todas las personas de la sede del evento (Axioma 3)
    q = db.query(models.Persona)
    if event_sede_id:
        q = q.filter(models.Persona.sede_id == event_sede_id)
    return q.order_by(models.Persona.nombre_completo.asc()).all()


def expected_group_rows(db: Session, grupo_id: UUID):
    rows = (
        db.query(models.ParticipanteGrupo, models.Persona)
        .join(models.Persona, models.Persona.id == models.ParticipanteGrupo.persona_id)
        .filter(models.ParticipanteGrupo.grupo_id == grupo_id)
        .order_by(models.Persona.nombre_completo.asc())
        .all()
    )
    grupo = (
        db.query(models.GrupoEvangelismo)
        .filter(models.GrupoEvangelismo.id == grupo_id)
        .first()
    )
    seen_ids = {persona.id for _, persona in rows}
    extra_personas = []
    if grupo:
        for pid in [grupo.lider_persona_id, grupo.asistente_persona_id, grupo.anfitrion_persona_id]:
            if pid and pid not in seen_ids:
                p = (
                    db.query(models.Persona)
                    .filter(models.Persona.id == pid)
                    .first()
                )
                if p:
                    extra_personas.append((None, p))
                    seen_ids.add(p.id)
    return rows + extra_personas


def _channel_label(channel: str) -> str:
    """Normalize communication channel display name."""
    value = str(channel or "").strip().lower()
    if value == "whatsapp":
        return "WhatsApp"
    if value == "email":
        return "Email"
    return "SMS"


def _persona_matches_segment(
    persona: models.Persona, segment: str, donation_persona_ids: set[str]
) -> bool:
    value = str(segment or "").strip().lower()
    if value == "active":
        return str(persona.church_role_effective or "").strip().lower() in {
            "miembro",
            "servidor",
            "lider",
            "líder",
            "pastor",
            "coordinador",
        }
    if value == "new":
        return str(persona.estado_vital or "").strip().lower() == "nuevo"
    if value == "staff":
        return str(persona.church_role_effective or "").strip().lower() in {
            "pastor",
            "coordinador",
            "staff",
            "administrador",
            "admin",
        }
    if value == "groups":
        return persona.family_id is not None
    if value == "low":
        return str(persona.church_role_effective or "").strip().lower() in {
            "nuevo",
            "creyente",
        }
    if value == "vip":
        return persona.id in donation_persona_ids
    return False


def _resolve_campaign_personas(db: Session, segments: list[str], sede_id=None) -> list[models.Persona]:
    normalized_segments = [
        segment for segment in (s.strip().lower() for s in segments) if segment
    ]
    if not normalized_segments:
        return []

    donations_q = db.query(models.Donation.persona_id).filter(models.Donation.persona_id.isnot(None))
    if sede_id:
        donations_q = donations_q.filter(models.Donation.sede_id == sede_id)
    donation_persona_ids = {str(pid) for (pid,) in donations_q.distinct().all()}
    personas_q = db.query(models.Persona)
    if sede_id:
        personas_q = personas_q.filter(models.Persona.sede_id == sede_id)
    personas = personas_q.all()
    selected = []
    seen_ids: set[str] = set()
    for persona in personas:
        if persona.id in seen_ids:
            continue
        if any(
            _persona_matches_segment(persona, segment, donation_persona_ids)
            for segment in normalized_segments
        ):
            selected.append(persona)
            seen_ids.add(persona.id)
    return selected


def _serialize_message_group(logs: list[models.CommunicationLog]) -> dict:
    import datetime as _dt

    ordered = sorted(
        logs, key=lambda log: log.created_at or _dt.datetime.min, reverse=True
    )
    representative = ordered[0]
    persona = getattr(representative, "persona", None)
    persona_name = persona.nombre_completo if persona else "Desconocido"
    campaign_name = next(
        (log.campaign_name for log in ordered if log.campaign_name), None
    )
    sent_at_dt = ordered[0].created_at
    delivered_count = sum(
        1 for log in ordered if str(log.outcome).lower() in DELIVERED_OUTCOMES
    )
    failed_count = sum(1 for log in ordered if str(log.outcome).lower() == "failed")
    if failed_count and not delivered_count:
        status = "failed"
    elif failed_count:
        status = "partial"
    else:
        status = str(representative.outcome or CommunicationOutcome.INTERNAL_LOG.value).lower()
    display_name = campaign_name or (
        f"Mensaje a {persona_name}"
        if len(ordered) == 1
        else f"Campaña a {len(ordered)} contactos"
    )
    return {
        "id": representative.id,
        "name": display_name,
        "campaign_name": campaign_name,
        "persona_name": persona_name,
        "channel": str(representative.channel).lower(),
        "status": status,
        "sent_at": sent_at_dt.isoformat() if sent_at_dt else None,
        "target_count": len(ordered),
        "delivered_count": delivered_count,
        "failed_count": failed_count,
        "content": representative.content,
        "recipient_phone": representative.recipient_phone,
        "external_id": representative.external_id,
    }


def _serialize_crm_task(
    task: models.TareaCRM,
    contact_name: Optional[str] = None,
    assignee_name: Optional[str] = None,
) -> dict:
    persona = getattr(task, "persona", None)
    persona_name = contact_name or (
        persona.nombre_completo if persona else None
    )
    assignee = getattr(task, "assignee", None)
    assigned_to = assignee_name or (assignee.username if assignee else None)
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "status": task.status,
        "priority": task.priority,
        "category": task.category,
        "due_date": task.due_date.isoformat() if task.due_date else None,
        "persona_id": task.persona_id,
        "persona_name": persona_name,
        "contact_name": persona_name,
        "assigned_to": assigned_to,
        "created_at": task.created_at.isoformat() if task.created_at else None,
    }


def persona_payload(
    persona: models.Persona,
    attended: bool,
    scanned_at=None,
    absence_reason=None,
    absence_reason_detail=None,
    estado=None,
    es_primera_vez=False,
):
    return {
        "persona_id": persona.id,
        "name": persona.nombre_completo,
        "role": persona.church_role_effective or "Miembro",
        "attended": attended,
        "absence_reason": absence_reason,
        "absence_reason_detail": absence_reason_detail,
        "scanned_at": scanned_at.isoformat() if scanned_at else None,
        "estado": estado,
        "es_primera_vez": es_primera_vez,
    }
