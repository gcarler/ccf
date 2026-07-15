from __future__ import annotations

import logging
from datetime import datetime as _datetime
from datetime import timezone as _timezone
from types import SimpleNamespace
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from backend import models, schemas
from backend.api.evangelism_shared import (
    _can_manage_grupo,
    _check_absence_trigger,
    _check_first_time_lead_trigger,
    _sessions_grupo_live_column_names,
    expected_group_rows,
    persona_payload,
    session_estado_habilitacion,
    session_read_only_options,
    session_read_value,
    utc_now,
)
from backend.core.database import get_db
from backend.core.permissions import get_current_user, require_pastor_or_admin
from backend.core.tenant import require_user_sede_id
from backend.models import Asistencia, GrupoEvangelismo, SesionGrupo

router = APIRouter()
logger = logging.getLogger(__name__)

def _session_read_options(db: Session):
    return session_read_only_options(db)


def _session_live_columns(db: Session) -> set[str]:
    return _sessions_grupo_live_column_names(db)


# ── Session Attendance ──


@router.get("/grupos/sessions/{session_id}/attendance")
@router.get("/groups/sessions/{session_id}/attendance")
def get_groups_session_attendance(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    session = db.query(SesionGrupo).options(_session_read_options(db)).filter(
        models.SesionGrupo.id == session_id,
        models.SesionGrupo.deleted_at.is_(None),
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    house = db.query(GrupoEvangelismo).filter(
        models.GrupoEvangelismo.id == session.grupo_id,
        models.GrupoEvangelismo.deleted_at.is_(None),
    ).first()
    if not house:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")
    if not _can_manage_grupo(db, current_user, house):
        raise HTTPException(status_code=403, detail="No autorizado para este grupo")

    attendances = (
        db.query(Asistencia)
        .filter(
            models.Asistencia.sesion_id == session_id,
            models.Asistencia.deleted_at.is_(None),
        )
        .options(joinedload(models.Asistencia.persona))
        .all()
    )

    expected_rows = expected_group_rows(db, session.grupo_id)
    attendance_map = {attendance.persona_id: attendance for attendance in attendances}
    present = []
    absent = []
    expected_personas = []
    for _, persona in expected_rows:
        attendance = attendance_map.get(persona.id)
        attended = (
            bool(
                attendance.attended
                if hasattr(attendance, "attended")
                else (attendance.estado == "ASISTIO" if attendance else False)
            )
            if attendance
            else False
        )
        payload = persona_payload(
            persona,
            attended=attended,
            scanned_at=getattr(attendance, "scanned_at", None) if attendance else None,
            absence_reason=getattr(attendance, "absence_reason", None) if attendance else None,
            absence_reason_detail=(
                getattr(attendance, "absence_reason_detail", None) or getattr(attendance, "detalle_excusa", None)
            )
            if attendance
            else None,
            estado=attendance.estado if attendance else None,
            es_primera_vez=attendance.es_primera_vez if attendance else False,
        )
        expected_personas.append(payload)
        if attended:
            present.append(payload)
        else:
            absent.append(payload)

    return {
        "session_id": session_id,
        "session_date": session.session_date.isoformat(),
        "grupo_id": session.grupo_id,
        "status": session.status,
        "topic": session.topic,
        "offering_amount": (float(session.offering_amount) if session.offering_amount is not None else None),
        "report_notes": session.report_notes,
        "novelty_type": session_read_value(session, "novelty_type"),
        "novelty_detail": session_read_value(session, "novelty_detail"),
        "cancellation_reason": session.cancellation_reason,
        "reported_by_persona_id": session_read_value(session, "reported_by_persona_id"),
        "total": len(present),
        "present_count": len(present),
        "absent_count": len(absent),
        "attendees": present,
        "absentees": absent,
        "expected_personas": expected_personas,
    }


@router.post("/grupos/sessions/{session_id}/attendance", response_model=dict)
@router.post("/groups/sessions/{session_id}/attendance", response_model=dict)
def add_groups_attendance(
    session_id: UUID,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    persona_ids = payload.get("persona_ids") or payload.get("persona_ids", [])
    attendees = payload.get("attendees")

    # R1 fix (residual audit): si clientes futuros empiezan a enviar
    # ``status`` (string) en lugar de ``attended`` (bool), absorbemos la
    # variante usando el normalizador compartido. Cualquier valor
    # no-mapeado cae a ``True`` como fallback conservador.
    from backend.schemas.evangelism import _normalize_status_alias

    if isinstance(attendees, list):
        for item in attendees:
            if not isinstance(item, dict):
                continue
            if "status" in item and "attended" not in item:
                canonical_status = _normalize_status_alias(item.get("status"))
                item["attended"] = canonical_status in {"present", "first_time"}

    session = db.query(SesionGrupo).options(_session_read_options(db)).filter(
        models.SesionGrupo.id == session_id,
        models.SesionGrupo.deleted_at.is_(None),
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    house = db.query(GrupoEvangelismo).filter(
        models.GrupoEvangelismo.id == session.grupo_id,
        models.GrupoEvangelismo.deleted_at.is_(None),
    ).first()
    if not house:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")
    if not _can_manage_grupo(db, current_user, house):
        raise HTTPException(status_code=403, detail="No autorizado para este grupo")

    from backend.models_evangelism import HabilitacionSesionEnum
    estado_habilitacion = session_estado_habilitacion(session)
    if estado_habilitacion != HabilitacionSesionEnum.HABILITADO.value:
        raise HTTPException(
            status_code=403,
            detail=f"La sesión está {estado_habilitacion.lower()} y no acepta reportes de asistencia.",
        )

    from datetime import datetime, timezone

    report_deadline = session_read_value(session, "report_deadline")
    if report_deadline:
        current_time = datetime.now(timezone.utc)
        deadline = report_deadline
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)
        if current_time > deadline:
            raise HTTPException(
                status_code=403,
                detail="El plazo para reportar asistencia en esta sesión ha vencido.",
            )

    import uuid

    if attendees and not isinstance(attendees, list):
        raise HTTPException(status_code=400, detail="La lista de asistentes debe ser un arreglo")

    if attendees:
        processed = 0
        for item in attendees:
            persona_id = item.get("persona_id") or item.get("persona_id")
            if not persona_id:
                continue
            if isinstance(persona_id, str):
                try:
                    persona_id = uuid.UUID(persona_id)
                except ValueError:
                    raise HTTPException(status_code=400, detail=f"ID de persona inválido: {persona_id}")
            attended = bool(item.get("attended", True))
            absence_reason = item.get("absence_reason")
            absence_reason_detail = item.get("absence_reason_detail")

            if not attended and not absence_reason:
                raise HTTPException(
                    status_code=400,
                    detail=f"Razón de ausencia requerida para la persona {persona_id}.",
                )

            row = (
                db.query(Asistencia)
                .filter(
                    models.Asistencia.sesion_id == session_id,
                    models.Asistencia.persona_id == persona_id,
                )
                .first()
            )
            if row:
                row.attended = attended
                row.absence_reason = absence_reason
                row.absence_reason_detail = absence_reason_detail
            else:
                db.add(
                    Asistencia(
                        sesion_id=session_id,
                        persona_id=persona_id,
                        attended=attended,
                        absence_reason=absence_reason,
                        absence_reason_detail=absence_reason_detail,
                    )
                )
            processed += 1
    else:
        if not persona_ids:
            raise HTTPException(status_code=400, detail="Se requiere lista de personas o asistentes")
        processed = 0
        for persona_id in persona_ids:
            if isinstance(persona_id, str):
                try:
                    persona_id = uuid.UUID(persona_id)
                except ValueError:
                    raise HTTPException(status_code=400, detail=f"ID de persona inválido: {persona_id}")
            exists = (
                db.query(Asistencia)
                .filter(
                    models.Asistencia.sesion_id == session_id,
                    models.Asistencia.persona_id == persona_id,
                )
                .first()
            )
            if not exists:
                db.add(Asistencia(sesion_id=session_id, persona_id=persona_id, attended=True))
                processed += 1

    new_status = payload.get("status", session.status)
    new_cancellation_reason = payload.get("cancellation_reason", session.cancellation_reason)

    if new_status in ["Cancelada", "No realizada"] and not new_cancellation_reason:
        raise HTTPException(
            status_code=400,
            detail=f"Motivo de cancelación es requerido cuando el estado es {new_status}.",
        )

    new_offering_amount = payload.get("offering_amount", session.offering_amount)
    if new_offering_amount is not None and float(new_offering_amount) < 0:
        raise HTTPException(status_code=400, detail="La ofrenda no puede ser un valor negativo.")

    live_columns = _session_live_columns(db)
    session.topic = payload.get("topic", session.topic)
    session.offering_amount = new_offering_amount
    session.report_notes = payload.get("report_notes", session.report_notes)
    if "novelty_type" in live_columns:
        session.novelty_type = payload.get("novelty_type", session_read_value(session, "novelty_type"))
    if "novelty_detail" in live_columns:
        session.novelty_detail = payload.get("novelty_detail", session_read_value(session, "novelty_detail"))
    session.cancellation_reason = new_cancellation_reason
    session.status = new_status
    if "reported_by_persona_id" in live_columns:
        session.reported_by_persona_id = payload.get(
            "reported_by_persona_id",
            session_read_value(session, "reported_by_persona_id"),
        )
    if "reported_at" in live_columns:
        session.reported_at = utc_now()

    try:
        db.commit()
    except Exception:
        logger.exception("Failed to commit attendance for session=%s", session_id)
        db.rollback()
        raise
    return {"status": "success", "processed": processed, "session_id": session_id}


# ── Attendance ──


@router.post("/sessions/{session_id}/attendance", response_model=dict)
def submit_attendance(
    session_id: UUID,
    attendance_data: List[schemas.AsistenciaGrupoCreate],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Submit attendance for a session. Checks automation triggers."""

    user_sede = require_user_sede_id(db, current_user)
    session = (
        db.query(SesionGrupo)
        .options(_session_read_options(db))
        .join(models.GrupoEvangelismo, models.GrupoEvangelismo.id == models.SesionGrupo.grupo_id)
        .filter(models.SesionGrupo.id == session_id)
        .filter(models.GrupoEvangelismo.sede_id == user_sede)
        .filter(models.SesionGrupo.deleted_at.is_(None))
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    # Protección IDOR: solo sesiones habilitadas aceptan reportes
    from backend.models_evangelism import HabilitacionSesionEnum
    estado_habilitacion = session_estado_habilitacion(session)
    if estado_habilitacion != HabilitacionSesionEnum.HABILITADO.value:
        raise HTTPException(
            status_code=403,
            detail=f"La sesión está {estado_habilitacion.lower()} y no acepta reportes de asistencia."
        )

    # Soft-delete existing attendance for this session
    db.query(Asistencia).filter(Asistencia.sesion_id == session_id).update(
        {Asistencia.deleted_at: utc_now()}, synchronize_session=False
    )

    submitted = []
    trigger_candidates: list[dict] = []
    for att in attendance_data:
        raw_status = getattr(att.status, "value", att.status)
        is_first_time = bool(getattr(att, "es_primera_vez", False)) or raw_status == "first_time"
        requires_follow_up = bool(getattr(att, "requiere_seguimiento", False))
        # Map schema fields (status/notes) to model fields
        absence_reason_detail = None
        if raw_status == "absent":
            absence_reason_detail = att.notes

        # Mapear estado nuevo (EstadoAsistenciaEnum)
        from backend.models_evangelism import EstadoAsistenciaEnum
        nuevo_estado = "presente"
        if raw_status == "absent":
            nuevo_estado = EstadoAsistenciaEnum.FALTO.value
        elif raw_status == "first_time":
            nuevo_estado = "primera_vez"

        import uuid as _uuid

        persona_uuid = att.persona_id
        if isinstance(persona_uuid, str):
            persona_uuid = _uuid.UUID(persona_uuid)

        db_att = Asistencia(
            sesion_id=session_id,
            persona_id=persona_uuid,
            detalle_excusa=absence_reason_detail,
            estado=nuevo_estado,
            es_primera_vez=is_first_time,
            requiere_seguimiento=requires_follow_up,
        )
        db.add(db_att)
        submitted.append(db_att)
        trigger_candidates.append(
            {
                "persona_id": persona_uuid,
                "is_first_time": is_first_time,
                "requires_follow_up": requires_follow_up,
            }
        )

    live_columns = _session_live_columns(db)
    if "reported_at" in live_columns:
        session.reported_at = utc_now()

    session_fecha_sesion = session_read_value(session, "fecha_sesion")
    bridge_group = (
        db.query(GrupoEvangelismo)
        .filter(
            models.GrupoEvangelismo.id == session.grupo_id,
            models.GrupoEvangelismo.sede_id == user_sede,
            models.GrupoEvangelismo.deleted_at.is_(None),
        )
        .first()
    )
    bridge_group_snapshot = None
    if bridge_group:
        bridge_group_snapshot = {
            "id": bridge_group.id,
            "nombre": bridge_group.nombre,
            "sede_id": bridge_group.sede_id,
            "estrategia_id": bridge_group.estrategia_id,
        }

    try:
        db.commit()
    except Exception:
        logger.exception("Failed to commit attendance submission for session=%s", session_id)
        db.rollback()
        raise
    for att in submitted:
        db.refresh(att)

    # ── Automation triggers ──
    _check_absence_trigger(db, session_id, user_sede)
    _check_first_time_lead_trigger(db, session_id)

    # ── CRM Bridge: first-time / seguimiento ──
    from backend.models_crm import Persona
    from backend.services.evangelism_crm_bridge import crear_caso_desde_asistencia

    evento = None
    for att, candidate in zip(submitted, trigger_candidates):
        if candidate["is_first_time"] or candidate["requires_follow_up"]:
            persona = db.query(Persona).filter(Persona.id == candidate["persona_id"]).first()
            if not persona:
                continue
            if not bridge_group_snapshot:
                continue
            sede_id = bridge_group_snapshot["sede_id"]
            if not sede_id:
                continue
            grupo_ref = SimpleNamespace(
                id=bridge_group_snapshot["id"],
                nombre=bridge_group_snapshot["nombre"],
                estrategia_id=bridge_group_snapshot["estrategia_id"],
            )
            session_ref = SimpleNamespace(id=session_id)
            caso = crear_caso_desde_asistencia(db, att, persona, grupo_ref, session_ref, sede_id)
            estrategia_id = bridge_group_snapshot["estrategia_id"]
            tags_nuevos = [
                f"VISITANTE_ESTRATEGIA_{estrategia_id}" if estrategia_id else "VISITANTE_ESTRATEGIA_NONE",
                f"GRUPO_{bridge_group_snapshot['nombre']}",
                f"SESION_{session_fecha_sesion.date().isoformat()}"
                if session_fecha_sesion
                else f"SESION_{session_id}",
            ]
            persona.tags = list(set((persona.tags or []) + tags_nuevos))
            if estrategia_id:
                persona.origen_estrategia_id = estrategia_id
            persona.origen_grupo_id = bridge_group_snapshot["id"]
            persona.origen_fecha = _datetime.now(_timezone.utc)
            persona.spiritual_status = "VISITANTE_EVANGELISMO"
            db.commit()
            db.refresh(persona)

            evento = {
                "origen_modulo": "EVANGELISMO",
                "grupo_id": str(bridge_group_snapshot["id"]),
                "sesion_id": str(session_id),
                "estado": "CREADO" if caso else "TRIGGERED_SIN_CASO",
                "visitante_kernel": {
                    "persona_id": str(persona.id),
                    "nombre": f"{persona.first_name} {persona.last_name}",
                    "rol_iglesia": persona.spiritual_status,
                    "tags_aplicados": persona.tags,
                },
                "crm_consolidacion": (
                    {
                        "caso_id": str(caso.id),
                        "pipeline": "NUEVOS_VISITANTES",
                        "etapa_inicial": caso.etapa_actual.nombre if caso.etapa_actual else "NUEVO_CONTACTO",
                        "SLA_limite_horas": 48,
                        "sla_deadline": caso.sla_vencimiento_contacto.isoformat()
                        if caso.sla_vencimiento_contacto
                        else None,
                    }
                    if caso
                    else None
                ),
            }
            break

    return {
        "evento_integracion": evento,
        "metadata": {
            "engine": "Mesh CCF",
            "trazabilidad": "AUTOMATIC_EVENT_TRIGGER_SUCCESS",
        },
    }


# ──────────────────────────────────────────────
# SEGUIMIENTO (FOLLOW-UP)
# ──────────────────────────────────────────────


@router.get("/follow-up/pending", response_model=List[schemas.RegistroSeguimientoResponse])
def list_pending_follow_ups(
    limit: int = 50,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_pastor_or_admin),
):
    """Lista todos los seguimientos pendientes (no completados)."""
    from backend.crud.evangelism import get_pendientes_seguimiento

    rows = get_pendientes_seguimiento(db, limit=limit)
    # Pydantic v2 strict: UUID→str requiere serialización explícita vía
    # model_dump(mode="json") — evita el 500 ``string_type`` en
    # ``RegistroSeguimientoResponse.asistencia_id``.
    return [
        schemas.RegistroSeguimientoResponse.model_validate(r).model_dump(mode="json")
        for r in rows
    ]


def _serialize_seguimiento(obj) -> dict:
    """Serializa un ORM ``RegistroSeguimiento`` a dict compatible con
    ``RegistroSeguimientoResponse`` (UUID→str, datetime→ISO)."""
    return schemas.RegistroSeguimientoResponse.model_validate(obj).model_dump(mode="json")


@router.get("/follow-up/{asistencia_id}", response_model=List[schemas.RegistroSeguimientoResponse])
def list_seguimientos_for_attendance(
    asistencia_id: UUID,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_pastor_or_admin),
):
    """Lista los seguimientos de una asistencia."""
    from backend.crud.evangelism import get_seguimientos

    rows = get_seguimientos(db, asistencia_id)
    return [
        schemas.RegistroSeguimientoResponse.model_validate(r).model_dump(mode="json")
        for r in rows
    ]


@router.post("/follow-up/{asistencia_id}", response_model=schemas.RegistroSeguimientoResponse)
def create_seguimiento(
    asistencia_id: UUID,
    payload: schemas.RegistroSeguimientoCreate,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_pastor_or_admin),
):
    """Crea un registro de seguimiento para una asistencia."""
    from backend.crud.evangelism import create_seguimiento

    asistencia = db.query(Asistencia).filter(
        models.Asistencia.id == asistencia_id,
        models.Asistencia.deleted_at.is_(None),
    ).first()
    if not asistencia:
        raise HTTPException(status_code=404, detail="Asistencia no encontrada")

    payload.asistencia_id = asistencia_id
    return _serialize_seguimiento(create_seguimiento(db, payload, actor_user_id=str(_user.id)))


@router.patch("/follow-up/{seguimiento_id}", response_model=schemas.RegistroSeguimientoResponse)
def update_seguimiento(
    seguimiento_id: UUID,
    payload: schemas.RegistroSeguimientoUpdate,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_pastor_or_admin),
):
    """Actualiza un seguimiento (marcar completado, agregar resultado, etc.)."""
    from backend.crud.evangelism import update_seguimiento

    result = update_seguimiento(db, seguimiento_id, payload, actor_user_id=str(_user.id))
    if not result:
        raise HTTPException(status_code=404, detail="Seguimiento no encontrado")
    return _serialize_seguimiento(result)
