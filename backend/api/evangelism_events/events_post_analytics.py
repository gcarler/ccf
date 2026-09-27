"""Módulo Super-PRO de Analytics Post-Evento, Embudo de Asistencia y Conversión CRM.

Implementa la Fase 3 Super-PRO de Evangelismo (TKT-EVT-ANALYTICS-03):
- Métricas de asistencia real vs registrada y utilización de aforo.
- Embudo de conversión a consolidación pastoral y grupos de vida (6 etapas).
- Tasa de retención de nuevos visitantes (cohortes 30d, 60d, 90d).
- Desglose de casos CRM y seguimiento pastoral.
- Reportes ejecutivos exportables en CSV (formato Excel / UTF-8-BOM).
- Dashboard ejecutivo pastoral a nivel de sede (Axioma 3).
- Canalización ejecutiva a CRM con idempotencia y auditoría canónica.
"""

from __future__ import annotations

import csv
import datetime
import io
import re
import uuid
from datetime import timedelta, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend import models
from backend.api.evangelism_events._shared import require_event_access
from backend.core.audit import record_admin_action
from backend.core.database import get_db
from backend.core.permissions import require_evangelism_manage, require_evangelism_read
from backend.core.tenant import require_user_sede_id
from backend.models_crm import Persona
from backend.models_crm_pipeline import (
    CanalOrigenEnum,
    CasoCRM,
    EstadoCasoEnum,
    EtapaPipeline,
    PipelineCRM,
    PrioridadCasoEnum,
    TipoPipelineEnum,
)
from backend.models_evangelism import Asistencia, GrupoEvangelismo, ParticipanteGrupo, SesionGrupo

router = APIRouter()


# ─────────────────────────────────────────────────────────────────────────────
# SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class CrmChannelRequest(BaseModel):
    persona_ids: Optional[List[UUID]] = Field(
        None,
        description="Lista opcional de IDs de personas para canalizar. Si se omite, canaliza todos los asistentes sin caso.",
    )
    assigned_agent_id: Optional[UUID] = Field(
        None,
        description="ID del agente pastoral responsable opcional para asignar a los casos creados.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _as_utc(dt: Optional[datetime.datetime]) -> Optional[datetime.datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _calculate_retention_health(rate_30d: float) -> str:
    if rate_30d >= 60.0:
        return "EXCELLENT"
    elif rate_30d >= 40.0:
        return "HEALTHY"
    elif rate_30d >= 20.0:
        return "ATTENTION_NEEDED"
    return "CRITICAL"


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/events/{event_id}/post-event-analytics")
def get_post_event_analytics(
    event_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_read),
):
    """Retorna analítica avanzada post-evento, embudo de conversión y retención."""
    event = require_event_access(db, current_user, event_id)
    event_uuid = event.id
    require_user_sede_id(db, current_user)

    # 1. Registros en EventRegistration
    registrations = (
        db.query(models.EventRegistration)
        .filter(
            models.EventRegistration.event_id == event_uuid,
            models.EventRegistration.deleted_at.is_(None),
        )
        .all()
    )

    reg_by_persona = {reg.persona_id: reg for reg in registrations}

    total_confirmed = sum(1 for r in registrations if r.registration_status == "CONFIRMED")
    total_cancelled = sum(1 for r in registrations if r.registration_status == "CANCELLED")
    total_registered_base = sum(1 for r in registrations if r.registration_status in ("CONFIRMED", "CHECKED_IN", "ABSENT"))

    # 2. Asistencias reales (EventAttendance + EventRegistration.check_in_at)
    attendances = (
        db.query(models.EventAttendance)
        .filter(
            models.EventAttendance.event_id == event_uuid,
            models.EventAttendance.attended.is_(True),
        )
        .all()
    )

    checked_in_reg_personas = {r.persona_id for r in registrations if r.check_in_at is not None or r.registration_status == "CHECKED_IN"}
    attendance_personas = {a.persona_id for a in attendances}
    all_attendee_ids = checked_in_reg_personas | attendance_personas
    total_attended = len(all_attendee_ids)

    # Walk-ins: asistieron pero no tenían pre-registro confirmado previo
    walk_ins_count = sum(1 for pid in all_attendee_ids if pid not in reg_by_persona or (reg_by_persona[pid].extras or {}).get("source") == "walk_in")

    # Inasistencias reales (no-show)
    no_show_personas = {
        r.persona_id
        for r in registrations
        if r.registration_status in ("CONFIRMED", "ABSENT") and r.persona_id not in all_attendee_ids
    }
    total_absent = len(no_show_personas)

    # Universo total convocado
    total_convocados = max(total_registered_base, total_attended)
    attendance_rate = round((total_attended / total_convocados * 100), 1) if total_convocados > 0 else 0.0
    no_show_rate = round((total_absent / total_convocados * 100), 1) if total_convocados > 0 else 0.0
    capacity_utilization = (
        round((total_attended / event.capacity_max * 100), 1)
        if event.capacity_max and event.capacity_max > 0
        else None
    )

    # 3. Datos de personas asistentes
    attendee_personas_db = []
    if all_attendee_ids:
        attendee_personas_db = (
            db.query(Persona)
            .filter(
                Persona.id.in_(all_attendee_ids),
                or_(Persona.estado_vital.is_(None), Persona.estado_vital != "ELIMINADO"),
            )
            .all()
        )
    persona_map = {p.id: p for p in attendee_personas_db}

    # Identificación de Nuevos Visitantes
    new_visitor_roles = {"visitante", "visitante servicios", "invitado", "contacto evangelistico"}
    new_visitor_ids = set()
    for pid in all_attendee_ids:
        p = persona_map.get(pid)
        if not p:
            continue
        role_lower = (p.church_role or "").strip().lower()
        if (
            role_lower in new_visitor_roles
            or p.origen_evento_id == event_uuid
            or (reg_by_persona.get(pid) and (reg_by_persona[pid].extras or {}).get("is_new_visitor"))
        ):
            new_visitor_ids.add(pid)

    new_visitors_count = len(new_visitor_ids)

    attendee_id_variants = list(all_attendee_ids) + [str(x) for x in all_attendee_ids]
    event_crm_cases = (
        db.query(CasoCRM)
        .filter(
            or_(
                CasoCRM.origen_evento_id.in_([event_uuid, str(event_uuid)]),
                CasoCRM.persona_id.in_(attendee_id_variants) if all_attendee_ids else False,
            ),
            CasoCRM.deleted_at.is_(None),
        )
        .all()
    )

    cases_by_persona = {str(c.persona_id): c for c in event_crm_cases}
    consolidated_attendee_ids = {str(pid) for pid in all_attendee_ids if str(pid) in cases_by_persona}
    consolidation_cases_count = len(consolidated_attendee_ids)

    # 5. Asignación a Grupos de Vida
    group_participations = []
    if all_attendee_ids:
        group_participations = (
            db.query(ParticipanteGrupo)
            .filter(
                ParticipanteGrupo.persona_id.in_(attendee_id_variants),
                ParticipanteGrupo.activo.is_(True),
                ParticipanteGrupo.deleted_at.is_(None),
            )
            .join(GrupoEvangelismo)
            .filter(GrupoEvangelismo.deleted_at.is_(None))
            .all()
        )

    groups_by_persona = {str(gp.persona_id): gp.grupo for gp in group_participations if gp.grupo}
    life_groups_count = len(groups_by_persona)

    # 6. Retención / Miembros Activos
    # Personas que asistieron y tienen: rol comprometido, o caso CRM cerrado/integrado, o asistencia a sesión posterior
    committed_roles = {"miembro", "discipulo", "servidor", "lider", "pastor", "coordinador"}
    retained_ids = set()
    for pid in all_attendee_ids:
        p = persona_map.get(pid)
        if not p:
            continue
        # Rol maduro
        if (p.church_role or "").strip().lower() in committed_roles:
            retained_ids.add(pid)
            continue
        # Asignado y activo en grupo de vida
        if pid in groups_by_persona:
            retained_ids.add(pid)
            continue
        # Caso CRM en etapa avanzada o cerrada exitosa
        caso = cases_by_persona.get(pid)
        if caso and str(caso.estado).upper() in ("CERRADO", "INTEGRADO", "GANADO"):
            retained_ids.add(pid)

    retained_count = len(retained_ids)

    # 7. Construcción del Embudo de Conversión (6 etapas)
    funnel_steps = [
        {
            "step": 1,
            "stage_id": "registered",
            "name": "Registrados / Convocados",
            "count": total_convocados,
            "pct_of_total": 100.0,
            "conversion_from_previous": 100.0,
            "dropoff_from_previous": 0.0,
            "description": "Total de inscritos y personas convocadas",
        },
        {
            "step": 2,
            "stage_id": "attended",
            "name": "Asistencia Real (Check-in)",
            "count": total_attended,
            "pct_of_total": round((total_attended / total_convocados * 100), 1) if total_convocados > 0 else 0.0,
            "conversion_from_previous": round((total_attended / total_convocados * 100), 1) if total_convocados > 0 else 0.0,
            "dropoff_from_previous": round(((total_convocados - total_attended) / total_convocados * 100), 1) if total_convocados > 0 else 0.0,
            "description": "Asistentes efectivos en puerta",
        },
        {
            "step": 3,
            "stage_id": "new_visitors",
            "name": "Nuevas Almas / Visitantes",
            "count": new_visitors_count,
            "pct_of_total": round((new_visitors_count / total_convocados * 100), 1) if total_convocados > 0 else 0.0,
            "conversion_from_previous": round((new_visitors_count / total_attended * 100), 1) if total_attended > 0 else 0.0,
            "dropoff_from_previous": round(((total_attended - new_visitors_count) / total_attended * 100), 1) if total_attended > 0 else 0.0,
            "description": "Contactos nuevos y por primera vez",
        },
        {
            "step": 4,
            "stage_id": "crm_consolidation",
            "name": "Consolidación CRM",
            "count": consolidation_cases_count,
            "pct_of_total": round((consolidation_cases_count / total_convocados * 100), 1) if total_convocados > 0 else 0.0,
            "conversion_from_previous": round((consolidation_cases_count / new_visitors_count * 100), 1) if new_visitors_count > 0 else (100.0 if consolidation_cases_count > 0 else 0.0),
            "dropoff_from_previous": round(((new_visitors_count - consolidation_cases_count) / new_visitors_count * 100), 1) if new_visitors_count > consolidation_cases_count else 0.0,
            "description": "Casos con seguimiento pastoral activo",
        },
        {
            "step": 5,
            "stage_id": "life_groups",
            "name": "Grupos de Vida",
            "count": life_groups_count,
            "pct_of_total": round((life_groups_count / total_convocados * 100), 1) if total_convocados > 0 else 0.0,
            "conversion_from_previous": round((life_groups_count / consolidation_cases_count * 100), 1) if consolidation_cases_count > 0 else (100.0 if life_groups_count > 0 else 0.0),
            "dropoff_from_previous": round(((consolidation_cases_count - life_groups_count) / consolidation_cases_count * 100), 1) if consolidation_cases_count > life_groups_count else 0.0,
            "description": "Conectados a un grupo de discipulado",
        },
        {
            "step": 6,
            "stage_id": "retained_members",
            "name": "Retenidos / Madurez",
            "count": retained_count,
            "pct_of_total": round((retained_count / total_convocados * 100), 1) if total_convocados > 0 else 0.0,
            "conversion_from_previous": round((retained_count / life_groups_count * 100), 1) if life_groups_count > 0 else (100.0 if retained_count > 0 else 0.0),
            "dropoff_from_previous": round(((life_groups_count - retained_count) / life_groups_count * 100), 1) if life_groups_count > retained_count else 0.0,
            "description": "Discípulos constantes y consolidados",
        },
    ]

    # 8. Análisis de Retención de Nuevos Visitantes (30d, 60d, 90d)
    event_date = _as_utc(event.event_date) or datetime.datetime.now(timezone.utc)
    t30 = event_date + timedelta(days=30)
    t60 = event_date + timedelta(days=60)
    t90 = event_date + timedelta(days=90)

    retained_30d_ids = set()
    retained_60d_ids = set()
    retained_90d_ids = set()

    if new_visitor_ids:
        # Asistencias en grupos de vida posteriores al evento
        subsequent_group_att = (
            db.query(Asistencia.persona_id, SesionGrupo.fecha_sesion)
            .join(SesionGrupo, Asistencia.sesion_id == SesionGrupo.id)
            .filter(
                Asistencia.persona_id.in_(new_visitor_ids),
                Asistencia.estado.in_(("Presente", "present", "asistio")),
                Asistencia.deleted_at.is_(None),
                SesionGrupo.deleted_at.is_(None),
            )
            .all()
        )
        for pid, s_date in subsequent_group_att:
            if s_date:
                dt_aware = datetime.datetime.combine(s_date, datetime.time.min, tzinfo=timezone.utc)
                if event_date <= dt_aware <= t30:
                    retained_30d_ids.add(pid)
                if event_date <= dt_aware <= t60:
                    retained_60d_ids.add(pid)
                if event_date <= dt_aware <= t90:
                    retained_90d_ids.add(pid)

        # Asistencias a otros eventos posteriores
        subsequent_event_att = (
            db.query(models.EventAttendance.persona_id, models.EventAttendance.session_date)
            .filter(
                models.EventAttendance.persona_id.in_(new_visitor_ids),
                models.EventAttendance.event_id != event_uuid,
                models.EventAttendance.attended.is_(True),
            )
            .all()
        )
        for pid, s_date in subsequent_event_att:
            if s_date:
                dt_aware = datetime.datetime.combine(s_date, datetime.time.min, tzinfo=timezone.utc)
                if event_date <= dt_aware <= t30:
                    retained_30d_ids.add(pid)
                if event_date <= dt_aware <= t60:
                    retained_60d_ids.add(pid)
                if event_date <= dt_aware <= t90:
                    retained_90d_ids.add(pid)

        # Si ya están en grupo de vida o caso CRM activo, se consideran retenidos al menos en 30d
        for pid in new_visitor_ids:
            if pid in groups_by_persona or pid in cases_by_persona:
                retained_30d_ids.add(pid)

    r30_count = len(retained_30d_ids)
    r60_count = len(retained_60d_ids)
    r90_count = len(retained_90d_ids)

    r30_rate = round((r30_count / new_visitors_count * 100), 1) if new_visitors_count > 0 else 0.0
    r60_rate = round((r60_count / new_visitors_count * 100), 1) if new_visitors_count > 0 else 0.0
    r90_rate = round((r90_count / new_visitors_count * 100), 1) if new_visitors_count > 0 else 0.0

    visitor_retention = {
        "new_visitors_count": new_visitors_count,
        "retained_30d_count": r30_count,
        "retained_30d_rate": r30_rate,
        "retained_60d_count": r60_count,
        "retained_60d_rate": r60_rate,
        "retained_90d_count": r90_count,
        "retained_90d_rate": r90_rate,
        "health_status": _calculate_retention_health(r30_rate),
    }

    # 9. Desglose detallado de CRM por Etapa
    stages = (
        db.query(EtapaPipeline)
        .filter(EtapaPipeline.deleted_at.is_(None))
        .order_by(EtapaPipeline.orden.asc())
        .all()
    )
    stage_map = {s.id: s for s in stages}
    cases_by_stage_count = {}
    for c in event_crm_cases:
        stage_id = c.etapa_actual_id
        cases_by_stage_count[stage_id] = cases_by_stage_count.get(stage_id, 0) + 1

    cases_by_stage_list = []
    total_cases = len(event_crm_cases)
    for s in stages:
        cnt = cases_by_stage_count.get(s.id, 0)
        cases_by_stage_list.append(
            {
                "stage_id": str(s.id),
                "stage_name": s.nombre,
                "color": getattr(s, "visual_color", None) or "hsl(var(--primary))",
                "count": cnt,
                "percentage": round((cnt / total_cases * 100), 1) if total_cases > 0 else 0.0,
            }
        )

    pending_followup_count = sum(1 for pid in all_attendee_ids if pid not in cases_by_persona and pid not in groups_by_persona)

    crm_breakdown = {
        "total_cases_created": total_cases,
        "cases_by_stage": cases_by_stage_list,
        "assigned_to_groups_count": life_groups_count,
        "assigned_to_groups_rate": round((life_groups_count / total_attended * 100), 1) if total_attended > 0 else 0.0,
        "pending_followup_count": pending_followup_count,
    }

    # 10. Listado completo de personas con estado en embudo para Drawer / Tabla
    attendees_funnel_summary = []
    for pid in all_attendee_ids:
        p = persona_map.get(pid)
        if not p:
            continue
        reg = reg_by_persona.get(pid)
        caso = cases_by_persona.get(str(pid))
        grupo = groups_by_persona.get(str(pid))
        is_new = pid in new_visitor_ids

        # Determinar el paso actual alcanzado en el embudo
        if pid in retained_ids:
            cur_step = "retained_members"
            cur_step_label = "Retenido / Activo"
        elif grupo:
            cur_step = "life_groups"
            cur_step_label = "Grupo de Vida"
        elif caso:
            cur_step = "crm_consolidation"
            cur_step_label = "En Consolidación"
        elif is_new:
            cur_step = "new_visitors"
            cur_step_label = "Nuevo Visitante"
        else:
            cur_step = "attended"
            cur_step_label = "Asistió"

        checkin_dt = None
        if reg and reg.check_in_at:
            checkin_dt = _as_utc(reg.check_in_at).isoformat()

        reg_code = None
        if reg and reg.registration_number:
            reg_code = f"#CCF-EVT-{reg.registration_number:04d}"

        attendees_funnel_summary.append(
            {
                "persona_id": str(p.id),
                "full_name": p.nombre_completo,
                "phone": p.phone or "",
                "email": p.email or "",
                "church_role": p.church_role or "Visitante Servicios",
                "is_new_visitor": is_new,
                "attended": True,
                "check_in_at": checkin_dt,
                "registration_code": reg_code,
                "has_crm_case": bool(caso),
                "crm_case_id": str(caso.id) if caso else None,
                "crm_stage_name": stage_map[caso.etapa_actual_id].nombre if caso and caso.etapa_actual_id in stage_map else None,
                "crm_stage_color": getattr(stage_map.get(caso.etapa_actual_id), "visual_color", None) if caso else None,
                "assigned_agent_id": str(caso.asignado_a_id) if caso and caso.asignado_a_id else None,
                "assigned_agent_name": f"{caso.asignado_a.first_name} {caso.asignado_a.last_name}" if caso and caso.asignado_a else None,
                "life_group_id": str(grupo.id) if grupo else None,
                "life_group_name": grupo.name if grupo else None,
                "current_funnel_step": cur_step,
                "current_funnel_step_label": cur_step_label,
            }
        )

    return {
        "event_id": str(event.id),
        "event_name": event.name,
        "event_date": _as_utc(event.event_date).isoformat() if event.event_date else None,
        "capacity_max": event.capacity_max,
        "attendance_metrics": {
            "total_registered": total_convocados,
            "total_confirmed": total_confirmed,
            "total_attended": total_attended,
            "total_absent": total_absent,
            "total_walk_ins": walk_ins_count,
            "total_cancelled": total_cancelled,
            "attendance_rate": attendance_rate,
            "no_show_rate": no_show_rate,
            "capacity_utilization": capacity_utilization,
        },
        "conversion_funnel": funnel_steps,
        "visitor_retention": visitor_retention,
        "crm_breakdown": crm_breakdown,
        "attendees_funnel_summary": attendees_funnel_summary,
    }


@router.get("/events/{event_id}/export/post-event-analytics")
def export_post_event_report(
    event_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_read),
):
    """Exporta el reporte exhaustivo post-evento en formato CSV compatible con Excel."""
    analytics = get_post_event_analytics(event_id, db=db, current_user=current_user)
    event_name = analytics.get("event_name", "evento").replace(" ", "_")
    event_date = analytics.get("event_date", "sin_fecha")[:10]

    output = io.StringIO()
    # Escribir UTF-8 BOM para apertura nativa y correcta de tildes en Microsoft Excel
    output.write("\ufeff")
    writer = csv.writer(output, delimiter=",", quoting=csv.QUOTE_MINIMAL)

    # 1. Resumen Ejecutivo
    writer.writerow(["REPORTE EJECUTIVO POST-EVENTO — COMUNIDAD CRISTIANA EL FARO"])
    writer.writerow(["Evento:", analytics.get("event_name"), "Fecha:", event_date])
    writer.writerow([])
    writer.writerow(["INDICADOR", "VALOR", "PORCENTAJE / TASA"])
    m = analytics["attendance_metrics"]
    writer.writerow(["Convocados / Registrados", m["total_registered"], "100.0%"])
    writer.writerow(["Asistencia Real en Puerta", m["total_attended"], f"{m['attendance_rate']}%"])
    writer.writerow(["Inasistencia (No-Show)", m["total_absent"], f"{m['no_show_rate']}%"])
    writer.writerow(["Walk-ins (Sin Pre-registro)", m["total_walk_ins"], "-"])
    writer.writerow(["Aforo Máximo", analytics.get("capacity_max") or "Ilimitado", f"{m['capacity_utilization'] or 0}%"])

    r = analytics["visitor_retention"]
    writer.writerow(["Nuevos Visitantes", r["new_visitors_count"], "-"])
    writer.writerow(["Retención 30 Días", r["retained_30d_count"], f"{r['retained_30d_rate']}%"])
    writer.writerow(["Retención 60 Días", r["retained_60d_count"], f"{r['retained_60d_rate']}%"])
    writer.writerow(["Retención 90 Días", r["retained_90d_count"], f"{r['retained_90d_rate']}%"])
    writer.writerow(["Salud de Retención", r["health_status"], "-"])
    writer.writerow([])

    # 2. Embudo de Conversión
    writer.writerow(["EMBUDO DE CONVERSIÓN MINISTERIAL"])
    writer.writerow(["Paso", "Etapa", "Cantidad", "% Total", "Conversión Etapa", "Dropoff"])
    for f in analytics["conversion_funnel"]:
        writer.writerow([
            f["step"],
            f["name"],
            f["count"],
            f"{f['pct_of_total']}%",
            f"{f['conversion_from_previous']}%",
            f"{f['dropoff_from_previous']}%",
        ])
    writer.writerow([])

    # 3. Detalle Asistentes
    writer.writerow(["DETALLE DE ASISTENTES Y SEGUIMIENTO PASTORAL"])
    writer.writerow([
        "Nombre Completo",
        "Teléfono",
        "Email",
        "Rol Iglesia",
        "Nuevo Visitante",
        "Código Registro",
        "Hora Check-in",
        "Etapa Embudo",
        "Caso CRM ID",
        "Etapa CRM",
        "Responsable Pastoral",
        "Grupo de Vida",
    ])

    for row in analytics["attendees_funnel_summary"]:
        writer.writerow([
            row["full_name"],
            row["phone"],
            row["email"],
            row["church_role"],
            "Sí" if row["is_new_visitor"] else "No",
            row["registration_code"] or "-",
            row["check_in_at"] or "-",
            row["current_funnel_step_label"],
            row["crm_case_id"] or "Sin Caso",
            row["crm_stage_name"] or "No Asignado",
            row["assigned_agent_name"] or "Sin Responsable",
            row["life_group_name"] or "Sin Grupo",
        ])

    safe_event_name = re.sub(r"[^a-zA-Z0-9_\-]", "_", str(event_name or "evento"))[:30]
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="reporte_post_evento_{safe_event_name}_{event_date}.csv"'},
    )


@router.get("/events/pastoral-executive-summary")
def get_pastoral_executive_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_read),
):
    """Resumen ejecutivo transversal para pastores y directores de evangelismo."""
    user_sede = require_user_sede_id(db, current_user)

    events = (
        db.query(models.CrmEvent)
        .filter(
            (models.CrmEvent.sede_id == user_sede) | models.CrmEvent.sede_id.is_(None),
            models.CrmEvent.deleted_at.is_(None),
        )
        .order_by(models.CrmEvent.event_date.desc().nullslast())
        .limit(50)
        .all()
    )

    total_events = len(events)
    total_attended_all = 0
    total_registered_all = 0
    total_new_visitors_all = 0
    total_crm_cases_all = 0
    total_groups_assigned_all = 0

    event_summaries = []

    for event in events:
        try:
            analytics = get_post_event_analytics(str(event.id), db=db, current_user=current_user)
            m = analytics["attendance_metrics"]
            r = analytics["visitor_retention"]
            cb = analytics["crm_breakdown"]

            total_attended_all += m["total_attended"]
            total_registered_all += m["total_registered"]
            total_new_visitors_all += r["new_visitors_count"]
            total_crm_cases_all += cb["total_cases_created"]
            total_groups_assigned_all += cb["assigned_to_groups_count"]

            event_summaries.append(
                {
                    "event_id": str(event.id),
                    "name": event.name,
                    "event_date": analytics.get("event_date"),
                    "attended": m["total_attended"],
                    "registered": m["total_registered"],
                    "attendance_rate": m["attendance_rate"],
                    "new_visitors": r["new_visitors_count"],
                    "retention_30d_rate": r["retained_30d_rate"],
                    "retention_health": r["health_status"],
                    "crm_cases": cb["total_cases_created"],
                    "life_groups": cb["assigned_to_groups_count"],
                    "pending_followup": cb["pending_followup_count"],
                }
            )
        except Exception:
            continue

    overall_attendance_rate = (
        round((total_attended_all / total_registered_all * 100), 1)
        if total_registered_all > 0
        else 0.0
    )
    overall_crm_channel_rate = (
        round((total_crm_cases_all / total_new_visitors_all * 100), 1)
        if total_new_visitors_all > 0
        else (100.0 if total_crm_cases_all > 0 else 0.0)
    )

    return {
        "sede_id": str(user_sede),
        "kpis": {
            "total_events": total_events,
            "total_registered": total_registered_all,
            "total_attended": total_attended_all,
            "overall_attendance_rate": overall_attendance_rate,
            "total_new_visitors": total_new_visitors_all,
            "total_crm_cases": total_crm_cases_all,
            "overall_crm_channel_rate": overall_crm_channel_rate,
            "total_life_groups_assigned": total_groups_assigned_all,
        },
        "event_summaries": event_summaries,
    }


@router.post("/events/{event_id}/crm-channel")
def channel_attendees_to_crm(
    event_id: str,
    payload: CrmChannelRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_manage),
):
    """Canaliza asistentes del evento a casos de consolidación CRM de forma atómica e idempotente."""
    event = require_event_access(db, current_user, event_id)
    user_sede = require_user_sede_id(db, current_user)

    analytics = get_post_event_analytics(event_id, db=db, current_user=current_user)
    attendees = analytics.get("attendees_funnel_summary", [])

    # Filtrar personas elegibles
    target_persona_ids = set()
    if payload.persona_ids:
        target_persona_ids = {str(pid) for pid in payload.persona_ids}
    else:
        # Por defecto canaliza los que no tienen caso aún
        target_persona_ids = {row["persona_id"] for row in attendees if not row["crm_case_id"]}

    if not target_persona_ids:
        return {
            "success": True,
            "created_cases": 0,
            "message": "No hay asistentes pendientes de canalización para procesar.",
        }

    personas = (
        db.query(Persona)
        .filter(
            Persona.id.in_([uuid.UUID(pid) for pid in target_persona_ids]),
            or_(Persona.estado_vital.is_(None), Persona.estado_vital != "ELIMINADO"),
        )
        .all()
    )

    sede_target = event.sede_id or user_sede

    # Obtener o crear pipeline de consolidación para la sede
    pipeline = (
        db.query(PipelineCRM)
        .filter(
            PipelineCRM.sede_id == sede_target,
            PipelineCRM.activo.is_(True),
            PipelineCRM.deleted_at.is_(None),
        )
        .first()
    )
    if not pipeline:
        pipeline = PipelineCRM(
            id=uuid.uuid4(),
            sede_id=sede_target,
            nombre="Consolidación Evangelismo",
            tipo=TipoPipelineEnum.NUEVOS_VISITANTES,
            activo=True,
            created_at=datetime.datetime.now(timezone.utc),
        )
        db.add(pipeline)
        db.flush()

    etapa = (
        db.query(EtapaPipeline)
        .filter(
            EtapaPipeline.pipeline_id == pipeline.id,
            EtapaPipeline.deleted_at.is_(None),
        )
        .order_by(EtapaPipeline.orden.asc())
        .first()
    )
    if not etapa:
        etapa = EtapaPipeline(
            id=uuid.uuid4(),
            pipeline_id=pipeline.id,
            nombre="Contacto Inicial",
            orden=1,
            requiere_accion=True,
            created_at=datetime.datetime.now(timezone.utc),
        )
        db.add(etapa)
        db.flush()

    created_count = 0
    assigned_agent = payload.assigned_agent_id
    now_utc = datetime.datetime.now(timezone.utc)

    for persona in personas:
        # Verificar si ya existe caso
        existing_case = (
            db.query(CasoCRM)
            .filter(
                CasoCRM.persona_id.in_([persona.id, str(persona.id)]),
                CasoCRM.deleted_at.is_(None),
            )
            .filter(
                or_(
                    CasoCRM.origen_evento_id.in_([event.id, str(event.id)]),
                    CasoCRM.pipeline_id == pipeline.id,
                )
            )
            .first()
        )
        if existing_case:
            continue

        caso = CasoCRM(
            id=uuid.uuid4(),
            persona_id=persona.id,
            sede_id=sede_target,
            pipeline_id=pipeline.id,
            etapa_actual_id=etapa.id,
            titulo_caso=f"Consolidación: {event.name}",
            prioridad=PrioridadCasoEnum.ALTA,
            estado=EstadoCasoEnum.ABIERTO,
            origen_canal=CanalOrigenEnum.EVANGELISMO,
            origen_evento_id=event.id,
            sla_vencimiento_contacto=now_utc + timedelta(hours=48),
            fecha_creacion=now_utc,
            asignado_a_id=assigned_agent,
        )
        db.add(caso)
        created_count += 1

    db.commit()

    # Registro de auditoría
    record_admin_action(
        db=db,
        actor=current_user,
        action="evangelism_crm_channeling",
        resource_type="crm_event",
        resource_id=str(event.id),
        metadata={
            "created_cases": created_count,
            "total_requested": len(target_persona_ids),
            "event_name": event.name,
        },
    )

    return {
        "success": True,
        "created_cases": created_count,
        "message": f"Se crearon exitosamente {created_count} casos de consolidación pastoral.",
    }
