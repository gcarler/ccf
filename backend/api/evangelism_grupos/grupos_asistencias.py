from __future__ import annotations

from datetime import datetime as _datetime, timezone as _timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from backend import models, schemas
from backend.models import SesionGrupo, GrupoEvangelismo, Asistencia
from backend.api.evangelism_shared import (
    persona_payload,
    expected_group_rows,
    utc_now,
    _can_manage_grupo,
    _check_absence_trigger,
    _check_first_time_lead_trigger,
)
from backend.core.permissions import get_current_user, require_pastor_or_admin
from backend.core.database import get_db
from backend.core.tenant import require_user_sede_id

router = APIRouter()


# ── Session Attendance ──


@router.get("/grupos/sessions/{session_id}/attendance")
@router.get("/faro/sessions/{session_id}/attendance")
def get_faro_session_attendance(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    session = db.query(SesionGrupo).filter(
        models.SesionGrupo.id == session_id,
        models.SesionGrupo.deleted_at.is_(None),
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    house = db.query(GrupoEvangelismo).filter(models.GrupoEvangelismo.id == session.grupo_id).first()
    if not house:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")
    if not _can_manage_grupo(db, current_user, house):
        raise HTTPException(status_code=403, detail="No autorizado para este grupo")

    attendances = (
        db.query(Asistencia)
        .filter(models.Asistencia.sesion_id == session_id)
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
        "novelty_type": session.novelty_type,
        "novelty_detail": session.novelty_detail,
        "cancellation_reason": session.cancellation_reason,
        "reported_by_persona_id": session.reported_by_persona_id,
        "total": len(present),
        "present_count": len(present),
        "absent_count": len(absent),
        "attendees": present,
        "absentees": absent,
        "expected_personas": expected_personas,
    }


@router.post("/grupos/sessions/{session_id}/attendance", response_model=dict)
@router.post("/faro/sessions/{session_id}/attendance", response_model=dict)
def add_faro_attendance(
    session_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    persona_ids = payload.get("persona_ids") or payload.get("persona_ids", [])
    attendees = payload.get("attendees")

    session = db.query(SesionGrupo).filter(
        models.SesionGrupo.id == session_id,
        models.SesionGrupo.deleted_at.is_(None),
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    house = db.query(GrupoEvangelismo).filter(models.GrupoEvangelismo.id == session.grupo_id).first()
    if not house:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")
    if not _can_manage_grupo(db, current_user, house):
        raise HTTPException(status_code=403, detail="No autorizado para este grupo")

    from backend.models_evangelism import HabilitacionSesionEnum
    if session.estado_habilitacion != HabilitacionSesionEnum.HABILITADO.value:
        raise HTTPException(
            status_code=403,
            detail=f"La sesión está {session.estado_habilitacion.lower()} y no acepta reportes de asistencia.",
        )

    from datetime import datetime, timezone

    if session.report_deadline:
        current_time = datetime.now(timezone.utc)
        deadline = session.report_deadline
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
                    raise HTTPException(status_code=400, detail=f"ID de miembro inválido: {persona_id}")
            attended = bool(item.get("attended", True))
            absence_reason = item.get("absence_reason")
            absence_reason_detail = item.get("absence_reason_detail")

            if not attended and not absence_reason:
                raise HTTPException(
                    status_code=400,
                    detail=f"Razón de ausencia requerida para el miembro {persona_id}.",
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
                        session_id=session_id,
                        persona_id=persona_id,
                        attended=attended,
                        absence_reason=absence_reason,
                        absence_reason_detail=absence_reason_detail,
                    )
                )
            processed += 1
    else:
        if not persona_ids:
            raise HTTPException(status_code=400, detail="Se requiere lista de miembros o asistentes")
        processed = 0
        for persona_id in persona_ids:
            if isinstance(persona_id, str):
                try:
                    persona_id = uuid.UUID(persona_id)
                except ValueError:
                    raise HTTPException(status_code=400, detail=f"ID de miembro inválido: {persona_id}")
            exists = (
                db.query(Asistencia)
                .filter(
                    models.Asistencia.sesion_id == session_id,
                    models.Asistencia.persona_id == persona_id,
                )
                .first()
            )
            if not exists:
                db.add(Asistencia(session_id=session_id, persona_id=persona_id, attended=True))
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

    session.topic = payload.get("topic", session.topic)
    session.offering_amount = new_offering_amount
    session.report_notes = payload.get("report_notes", session.report_notes)
    session.novelty_type = payload.get("novelty_type", session.novelty_type)
    session.novelty_detail = payload.get("novelty_detail", session.novelty_detail)
    session.cancellation_reason = new_cancellation_reason
    session.status = new_status
    session.reported_by_persona_id = payload.get("reported_by_persona_id", session.reported_by_persona_id)
    session.reported_at = utc_now()

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {"status": "success", "processed": processed, "session_id": session_id}


# ── Attendance ──


@router.post("/sessions/{session_id}/attendance", response_model=dict)
def submit_attendance(
    session_id: int,
    attendance_data: List[schemas.AsistenciaGrupoCreate],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Submit attendance for a session. Checks automation triggers."""

    user_sede = require_user_sede_id(db, current_user)
    session = (
        db.query(SesionGrupo)
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
    if session.estado_habilitacion != HabilitacionSesionEnum.HABILITADO.value:
        raise HTTPException(
            status_code=403,
            detail=f"La sesión está {session.estado_habilitacion.lower()} y no acepta reportes de asistencia."
        )

    # Soft-delete existing attendance for this session
    db.query(Asistencia).filter(Asistencia.sesion_id == session_id).update(
        {Asistencia.deleted_at: utc_now()}, synchronize_session=False
    )

    submitted = []
    for att in attendance_data:
        # Map schema fields (status/notes) to model fields
        absence_reason_detail = None
        if att.status == "absent":
            absence_reason_detail = att.notes

        # Mapear estado nuevo (EstadoAsistenciaEnum)
        from backend.models_evangelism import EstadoAsistenciaEnum
        nuevo_estado = "presente"
        if att.status == "absent":
            nuevo_estado = EstadoAsistenciaEnum.FALTO.value
        elif att.status == "first_time":
            nuevo_estado = "primera_vez"

        import uuid as _uuid

        persona_uuid = att.persona_id
        if isinstance(persona_uuid, str):
            persona_uuid = _uuid.UUID(persona_uuid)

        db_att = Asistencia(
            session_id=session_id,
            persona_id=persona_uuid,
            detalle_excusa=absence_reason_detail,
            estado=nuevo_estado,
            es_primera_vez=(att.status == "first_time"),
        )
        db.add(db_att)
        submitted.append(db_att)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    for att in submitted:
        db.refresh(att)

    # ── Automation triggers ──
    _check_absence_trigger(db, session_id, user_sede)
    _check_first_time_lead_trigger(db, session_id)

    # ── CRM Bridge: first-time / seguimiento ──
    from backend.services.evangelism_crm_bridge import crear_caso_desde_asistencia
    from backend.models_crm import Persona

    evento = None
    for att in submitted:
        if att.es_primera_vez or att.requiere_seguimiento:
            persona = db.query(Persona).filter(Persona.id == att.persona_id).first()
            if not persona:
                continue
            grupo = session.grupo
            if not grupo:
                continue
            sede_id = grupo.sede_id
            if not sede_id:
                continue
            caso = crear_caso_desde_asistencia(db, att, persona, grupo, session, sede_id)
            if caso:
                estrategia = grupo.estrategia
                tags_nuevos = [
                    f"VISITANTE_ESTRATEGIA_{estrategia.id}" if estrategia else "VISITANTE_ESTRATEGIA_NONE",
                    f"GRUPO_{grupo.nombre}",
                    f"SESION_{session.fecha_sesion.date().isoformat()}"
                    if session.fecha_sesion
                    else f"SESION_{session.id}",
                ]
                persona.tags = list(set((persona.tags or []) + tags_nuevos))
                if estrategia:
                    persona.origen_estrategia_id = estrategia.id
                persona.origen_grupo_id = grupo.id
                persona.origen_fecha = _datetime.now(_timezone.utc)
                persona.spiritual_status = "VISITANTE_EVANGELISMO"
                db.commit()
                db.refresh(persona)
                db.refresh(caso)

                evento = {
                    "origen_modulo": "EVANGELISMO",
                    "grupo_id": str(grupo.id),
                    "sesion_id": str(session.id),
                    "visitante_kernel": {
                        "persona_id": str(persona.id),
                        "nombre": f"{persona.first_name} {persona.last_name}",
                        "rol_iglesia": persona.spiritual_status,
                        "tags_aplicados": persona.tags,
                    },
                    "crm_consolidacion": {
                        "caso_id": str(caso.id),
                        "pipeline": "NUEVOS_VISITANTES",
                        "etapa_inicial": caso.etapa_actual.nombre if caso.etapa_actual else "NUEVO_CONTACTO",
                        "SLA_limite_horas": 48,
                        "sla_deadline": caso.sla_vencimiento_contacto.isoformat()
                        if caso.sla_vencimiento_contacto
                        else None,
                    },
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

    return get_pendientes_seguimiento(db, limit=limit)


@router.get("/follow-up/{asistencia_id}", response_model=List[schemas.RegistroSeguimientoResponse])
def list_seguimientos_for_attendance(
    asistencia_id: int,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_pastor_or_admin),
):
    """Lista los seguimientos de una asistencia."""
    from backend.crud.evangelism import get_seguimientos

    return get_seguimientos(db, asistencia_id)


@router.post("/follow-up/{asistencia_id}", response_model=schemas.RegistroSeguimientoResponse)
def create_seguimiento(
    asistencia_id: int,
    payload: schemas.RegistroSeguimientoCreate,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_pastor_or_admin),
):
    """Crea un registro de seguimiento para una asistencia."""
    from backend.crud.evangelism import create_seguimiento

    asistencia = db.query(Asistencia).filter(models.Asistencia.id == asistencia_id).first()
    if not asistencia:
        raise HTTPException(status_code=404, detail="Asistencia no encontrada")

    payload.asistencia_id = asistencia_id
    return create_seguimiento(db, payload)


@router.patch("/follow-up/{seguimiento_id}", response_model=schemas.RegistroSeguimientoResponse)
def update_seguimiento(
    seguimiento_id: int,
    payload: schemas.RegistroSeguimientoUpdate,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_pastor_or_admin),
):
    """Actualiza un seguimiento (marcar completado, agregar resultado, etc.)."""
    from backend.crud.evangelism import update_seguimiento

    result = update_seguimiento(db, seguimiento_id, payload)
    if not result:
        raise HTTPException(status_code=404, detail="Seguimiento no encontrado")
    return result
