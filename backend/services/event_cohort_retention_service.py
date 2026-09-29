"""Servicio analítico de Cohortes de Retención, LTV Espiritual y Auditoría Pastoral Multi-Sede.

TKT-EVT-COHORT-RETENTION-05 (Fase 5 Super-PRO Evangelismo):
1. Motor de cohortes de retención post-evento (30, 60 y 90 días en Grupos de Vida y Academia).
2. Métricas de madurez / LTV espiritual (Spiritual Lifetime Value & Milestones).
3. Matriz temporal de retención de cohortes (heatmap de retención por cohorte mensual).
4. Auditoría pastoral comparativa multi-sede con ranking de efectividad.
5. Exportación ejecutiva CSV compatible con Excel (UTF-8 BOM).
"""

from __future__ import annotations

import csv
import datetime
from datetime import timedelta, timezone
import io
import logging
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from backend import models
from backend.models_academy_core import Course, Enrollment
from backend.models_crm import Persona
from backend.models_crm_pipeline import CasoCRM, EtapaPipeline
from backend.models_evangelism import Asistencia, GrupoEvangelismo, ParticipanteGrupo, Sede, SesionGrupo
from backend.models_kernel import PersonaMinistry

logger = logging.getLogger(__name__)


def _now_utc() -> datetime.datetime:
    return datetime.datetime.now(timezone.utc)


def _as_utc(dt: Optional[datetime.datetime | datetime.date]) -> Optional[datetime.datetime]:
    if dt is None:
        return None
    if isinstance(dt, datetime.date) and not isinstance(dt, datetime.datetime):
        dt = datetime.datetime.combine(dt, datetime.time.min)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _classify_spiritual_maturity(score: float) -> str:
    """Clasifica el nivel de madurez espiritual según el Spiritual Maturity Index (SMI 0-100)."""
    if score >= 80.0:
        return "MULTIPLICADOR"
    elif score >= 60.0:
        return "COMPROMETIDO"
    elif score >= 40.0:
        return "DISCIPULO"
    elif score >= 20.0:
        return "CRECIENTE"
    return "EXPLORADOR"


def calculate_event_cohort_retention(db: Session, event: models.CrmEvent) -> dict[str, Any]:
    """Calcula las métricas de cohorte temporal y LTV espiritual de los asistentes de un evento."""
    # 1. Obtener registros que asistieron al evento
    regs = (
        db.query(models.EventRegistration)
        .filter(
            models.EventRegistration.event_id == event.id,
            models.EventRegistration.deleted_at.is_(None),
            or_(
                models.EventRegistration.registration_status == "CHECKED_IN",
                models.EventRegistration.check_in_at.isnot(None),
            ),
        )
        .all()
    )

    total_cohort = len(regs)
    if total_cohort == 0:
        return {
            "event_id": str(event.id),
            "event_name": event.name,
            "event_date": event.event_date.isoformat() if event.event_date else None,
            "total_cohort_size": 0,
            "retention_metrics": {
                "day_30": {"count": 0, "percentage": 0.0},
                "day_60": {"count": 0, "percentage": 0.0},
                "day_90": {"count": 0, "percentage": 0.0},
            },
            "spiritual_ltv_summary": {
                "decision_rate_pct": 0.0,
                "group_integration_rate_pct": 0.0,
                "baptism_rate_pct": 0.0,
                "academy_rate_pct": 0.0,
                "service_leadership_rate_pct": 0.0,
                "avg_spiritual_maturity_score": 0.0,
                "maturity_distribution": {
                    "EXPLORADOR": 0,
                    "CRECIENTE": 0,
                    "DISCIPULO": 0,
                    "COMPROMETIDO": 0,
                    "MULTIPLICADOR": 0,
                },
            },
            "attendees_cohort": [],
        }

    now = _now_utc()
    base_event_date = _as_utc(event.event_date) or now

    # 2. Recolectar personas y evaluar retención y madurez
    attendee_results: list[dict[str, Any]] = []
    
    ret_30_count = 0
    ret_60_count = 0
    ret_90_count = 0

    decisions_count = 0
    group_integration_count = 0
    baptisms_count = 0
    academy_count = 0
    service_count = 0
    total_smi = 0.0

    distribution = {
        "EXPLORADOR": 0,
        "CRECIENTE": 0,
        "DISCIPULO": 0,
        "COMPROMETIDO": 0,
        "MULTIPLICADOR": 0,
    }

    for reg in regs:
        persona = reg.persona
        if not persona:
            continue

        t0 = _as_utc(reg.check_in_at) or base_event_date
        t30 = t0 + timedelta(days=30)
        t60 = t0 + timedelta(days=60)
        t90 = t0 + timedelta(days=90)

        # A) Asistencia a Grupos de Vida post-evento
        # Sesiones de grupo donde la persona asistió después de t0
        group_attendances = (
            db.query(Asistencia)
            .join(SesionGrupo, Asistencia.sesion_id == SesionGrupo.id)
            .filter(
                Asistencia.persona_id == persona.id,
                Asistencia.deleted_at.is_(None),
                SesionGrupo.deleted_at.is_(None),
                SesionGrupo.fecha_sesion >= t0,
                Asistencia.estado.in_(["presente", "primera_vez", "asistio"]),
            )
            .all()
        )

        attended_30d = sum(1 for a in group_attendances if _as_utc(a.sesion.fecha_sesion) <= t30)
        attended_60d = sum(1 for a in group_attendances if _as_utc(a.sesion.fecha_sesion) <= t60)
        attended_90d = sum(1 for a in group_attendances if _as_utc(a.sesion.fecha_sesion) <= t90)

        # Miembro oficial de grupo
        is_group_participant = (
            db.query(ParticipanteGrupo)
            .filter(
                ParticipanteGrupo.persona_id == persona.id,
                ParticipanteGrupo.deleted_at.is_(None),
            )
            .first()
            is not None
        )

        in_group_30 = attended_30d > 0 or is_group_participant
        in_group_60 = attended_60d > 0 or (attended_30d > 0 and is_group_participant)
        in_group_90 = attended_90d > 0 or (attended_60d > 0 and is_group_participant)

        if in_group_30:
            ret_30_count += 1
        if in_group_60:
            ret_60_count += 1
        if in_group_90:
            ret_90_count += 1

        # B) Academia / Discipulado
        academy_enrollments = (
            db.query(Enrollment)
            .filter(
                Enrollment.persona_id == persona.id,
                Enrollment.deleted_at.is_(None),
            )
            .all()
        )
        has_academy = len(academy_enrollments) > 0
        has_approved_academy = any(e.approved for e in academy_enrollments)

        # C) Decisión / Caso CRM
        crm_case = (
            db.query(CasoCRM)
            .filter(
                CasoCRM.persona_id == persona.id,
                CasoCRM.deleted_at.is_(None),
            )
            .first()
        )
        has_decision = (
            crm_case is not None
            or persona.spiritual_status in ["Creyente", "Consolidado", "Bautizado", "Líder"]
            or (persona.church_role and persona.church_role.upper() not in ["VISITANTE_EVENTO", "NUEVO"])
        )

        # D) Bautismo en agua
        is_baptized = bool(persona.is_baptized or persona.baptism_date is not None)

        # E) Servicio activo / Liderazgo
        ministries = (
            db.query(PersonaMinistry)
            .filter(
                PersonaMinistry.persona_id == persona.id,
                PersonaMinistry.deleted_at.is_(None),
            )
            .all()
        )
        role_upper = (persona.church_role or "").upper()
        is_servant_or_leader = (
            len(ministries) > 0
            or "LIDER" in role_upper
            or "SERVIDOR" in role_upper
            or "PASTOR" in role_upper
            or "MENTOR" in role_upper
        )

        # ── Cálculo del Spiritual Maturity Index (SMI) 0 - 100 ──────────────
        smi_score = 0.0
        milestones_achieved = []

        if has_decision:
            smi_score += 20.0
            decisions_count += 1
            milestones_achieved.append({"code": "DECISION", "label": "Decisión por Cristo", "points": 20})

        if in_group_30:
            smi_score += 20.0
            group_integration_count += 1
            milestones_achieved.append({"code": "GRUPO_VIDA", "label": "Integración a Grupo de Vida", "points": 20})

        if is_baptized:
            smi_score += 20.0
            baptisms_count += 1
            milestones_achieved.append({"code": "BAUTISMO", "label": "Bautismo en Agua", "points": 20})

        if has_academy:
            pts = 20.0 if has_approved_academy else 15.0
            smi_score += pts
            academy_count += 1
            milestones_achieved.append({"code": "ACADEMIA", "label": "Academia de Discipulado", "points": pts})

        if is_servant_or_leader:
            smi_score += 20.0
            service_count += 1
            milestones_achieved.append({"code": "SERVICIO", "label": "Servicio / Liderazgo Activo", "points": 20})

        smi_score = min(100.0, smi_score)
        total_smi += smi_score
        maturity_level = _classify_spiritual_maturity(smi_score)
        distribution[maturity_level] += 1

        reg_code = (
            f"#CCF-EVT-{reg.registration_number:04d}"
            if getattr(reg, "registration_number", None)
            else f"#CCF-EVT-{str(reg.id)[:8].upper()}"
        )

        attendee_results.append(
            {
                "persona_id": str(persona.id),
                "full_name": persona.nombre_completo,
                "email": persona.email,
                "phone": persona.phone or persona.mobile_phone,
                "registration_code": reg_code,
                "check_in_at": reg.check_in_at.isoformat() if reg.check_in_at else None,
                "retained_30d": in_group_30,
                "retained_60d": in_group_60,
                "retained_90d": in_group_90,
                "group_attendances_count": len(group_attendances),
                "has_academy_enrollment": has_academy,
                "is_baptized": is_baptized,
                "is_servant_or_leader": is_servant_or_leader,
                "spiritual_maturity_score": smi_score,
                "maturity_level": maturity_level,
                "milestones": milestones_achieved,
            }
        )

    # Ordenar asistentes por puntaje de madurez descendente
    attendee_results.sort(key=lambda a: a["spiritual_maturity_score"], reverse=True)

    pct_30 = round((ret_30_count / total_cohort) * 100, 1)
    pct_60 = round((ret_60_count / total_cohort) * 100, 1)
    pct_90 = round((ret_90_count / total_cohort) * 100, 1)

    avg_smi = round(total_smi / total_cohort, 1)

    return {
        "event_id": str(event.id),
        "event_name": event.name,
        "event_date": event.event_date.isoformat() if event.event_date else None,
        "total_cohort_size": total_cohort,
        "retention_metrics": {
            "day_30": {"count": ret_30_count, "percentage": pct_30},
            "day_60": {"count": ret_60_count, "percentage": pct_60},
            "day_90": {"count": ret_90_count, "percentage": pct_90},
        },
        "spiritual_ltv_summary": {
            "decision_rate_pct": round((decisions_count / total_cohort) * 100, 1),
            "group_integration_rate_pct": round((group_integration_count / total_cohort) * 100, 1),
            "baptism_rate_pct": round((baptisms_count / total_cohort) * 100, 1),
            "academy_rate_pct": round((academy_count / total_cohort) * 100, 1),
            "service_leadership_rate_pct": round((service_count / total_cohort) * 100, 1),
            "avg_spiritual_maturity_score": avg_smi,
            "maturity_distribution": distribution,
        },
        "attendees_cohort": attendee_results,
    }


def calculate_multi_sede_cohort_analysis(
    db: Session,
    requesting_user_sede_id: UUID | str | None = None,
) -> dict[str, Any]:
    """Genera la auditoría pastoral multi-sede y ranking de retención/LTV entre sedes."""
    # Listar sedes activas
    sedes = db.query(Sede).filter(Sede.es_activa.is_(True), Sede.deleted_at.is_(None)).all()

    sede_summaries: list[dict[str, Any]] = []

    global_events = 0
    global_cohort = 0
    global_ret_30 = 0
    global_ret_60 = 0
    global_ret_90 = 0
    global_baptisms = 0
    global_smi_sum = 0.0

    for sede in sedes:
        # Eventos de la sede
        events = (
            db.query(models.CrmEvent)
            .filter(
                models.CrmEvent.sede_id == sede.id,
                models.CrmEvent.deleted_at.is_(None),
            )
            .all()
        )

        sede_cohort_size = 0
        sede_ret_30 = 0
        sede_ret_60 = 0
        sede_ret_90 = 0
        sede_baptisms = 0
        sede_academy = 0
        sede_smi_sum = 0.0

        for ev in events:
            # Calcular cohort de cada evento
            cohort_data = calculate_event_cohort_retention(db, ev)
            c_size = cohort_data["total_cohort_size"]
            if c_size > 0:
                sede_cohort_size += c_size
                sede_ret_30 += cohort_data["retention_metrics"]["day_30"]["count"]
                sede_ret_60 += cohort_data["retention_metrics"]["day_60"]["count"]
                sede_ret_90 += cohort_data["retention_metrics"]["day_90"]["count"]
                
                # Bautismos y academia
                b_pct = cohort_data["spiritual_ltv_summary"]["baptism_rate_pct"]
                a_pct = cohort_data["spiritual_ltv_summary"]["academy_rate_pct"]
                sede_baptisms += int(round(c_size * (b_pct / 100.0)))
                sede_academy += int(round(c_size * (a_pct / 100.0)))
                
                sede_smi_sum += cohort_data["spiritual_ltv_summary"]["avg_spiritual_maturity_score"] * c_size

        events_count = len(events)
        pct_30 = round((sede_ret_30 / sede_cohort_size) * 100, 1) if sede_cohort_size > 0 else 0.0
        pct_60 = round((sede_ret_60 / sede_cohort_size) * 100, 1) if sede_cohort_size > 0 else 0.0
        pct_90 = round((sede_ret_90 / sede_cohort_size) * 100, 1) if sede_cohort_size > 0 else 0.0
        b_rate = round((sede_baptisms / sede_cohort_size) * 100, 1) if sede_cohort_size > 0 else 0.0
        a_rate = round((sede_academy / sede_cohort_size) * 100, 1) if sede_cohort_size > 0 else 0.0
        avg_smi = round(sede_smi_sum / sede_cohort_size, 1) if sede_cohort_size > 0 else 0.0

        # Puntuación de efectividad pastoral ponderada (0 - 100)
        pastoral_efficiency_score = round(
            (pct_90 * 0.40) + (avg_smi * 0.30) + (b_rate * 0.20) + (a_rate * 0.10),
            1,
        )

        global_events += events_count
        global_cohort += sede_cohort_size
        global_ret_30 += sede_ret_30
        global_ret_60 += sede_ret_60
        global_ret_90 += sede_ret_90
        global_baptisms += sede_baptisms
        global_smi_sum += sede_smi_sum

        sede_summaries.append(
            {
                "sede_id": str(sede.id),
                "sede_name": sede.nombre,
                "city": sede.ciudad,
                "total_events": events_count,
                "total_cohort_size": sede_cohort_size,
                "retention_30d_pct": pct_30,
                "retention_60d_pct": pct_60,
                "retention_90d_pct": pct_90,
                "baptism_rate_pct": b_rate,
                "academy_rate_pct": a_rate,
                "avg_spiritual_maturity_score": avg_smi,
                "pastoral_efficiency_score": pastoral_efficiency_score,
            }
        )

    # Ordenar por eficiencia pastoral descendente y asignar ranking
    sede_summaries.sort(key=lambda s: s["pastoral_efficiency_score"], reverse=True)
    for idx, s in enumerate(sede_summaries, start=1):
        s["rank_position"] = idx

    global_pct_30 = round((global_ret_30 / global_cohort) * 100, 1) if global_cohort > 0 else 0.0
    global_pct_60 = round((global_ret_60 / global_cohort) * 100, 1) if global_cohort > 0 else 0.0
    global_pct_90 = round((global_ret_90 / global_cohort) * 100, 1) if global_cohort > 0 else 0.0
    global_avg_smi = round(global_smi_sum / global_cohort, 1) if global_cohort > 0 else 0.0

    return {
        "calculated_at": _now_utc().isoformat(),
        "global_kpis": {
            "total_sedes": len(sedes),
            "total_events": global_events,
            "total_cohort_size": global_cohort,
            "avg_retention_30d_pct": global_pct_30,
            "avg_retention_60d_pct": global_pct_60,
            "avg_retention_90d_pct": global_pct_90,
            "global_avg_spiritual_maturity": global_avg_smi,
        },
        "sedes_ranking": sede_summaries,
    }


def calculate_temporal_cohort_matrix(
    db: Session,
    sede_id: UUID | str | None = None,
    months_count: int = 6,
) -> dict[str, Any]:
    """Genera la matriz de retención por cohortes temporales (mes a mes) para visualización en cuadrícula."""
    now = _now_utc()
    user_sede_uuid = UUID(str(sede_id)) if sede_id else None

    # Generar ventanas de cohortes para los últimos `months_count` meses
    cohort_rows: list[dict[str, Any]] = []

    for i in range(months_count - 1, -1, -1):
        # Primer día del mes
        month_dt = (now.replace(day=1) - timedelta(days=i * 30)).replace(day=1)
        year = month_dt.year
        month = month_dt.month
        month_key = f"{year}-{month:02d}"
        month_label = month_dt.strftime("%B %Y").capitalize()

        # Rango del mes
        next_month_year = year if month < 12 else year + 1
        next_month = month + 1 if month < 12 else 1
        month_start = datetime.datetime(year, month, 1, 0, 0, 0, tzinfo=timezone.utc)
        month_end = datetime.datetime(next_month_year, next_month, 1, 0, 0, 0, tzinfo=timezone.utc)

        # Buscar eventos del mes
        q = db.query(models.CrmEvent).filter(
            models.CrmEvent.event_date >= month_start,
            models.CrmEvent.event_date < month_end,
            models.CrmEvent.deleted_at.is_(None),
        )
        if user_sede_uuid:
            q = q.filter(models.CrmEvent.sede_id == user_sede_uuid)

        events_in_month = q.all()

        month_cohort_size = 0
        month_ret_30 = 0
        month_ret_60 = 0
        month_ret_90 = 0

        for ev in events_in_month:
            ev_data = calculate_event_cohort_retention(db, ev)
            c_size = ev_data["total_cohort_size"]
            if c_size > 0:
                month_cohort_size += c_size
                month_ret_30 += ev_data["retention_metrics"]["day_30"]["count"]
                month_ret_60 += ev_data["retention_metrics"]["day_60"]["count"]
                month_ret_90 += ev_data["retention_metrics"]["day_90"]["count"]

        # Si el mes es muy reciente, marcar no alcanzado aún
        is_30d_eligible = (now - month_end).days >= 30
        is_60d_eligible = (now - month_end).days >= 60
        is_90d_eligible = (now - month_end).days >= 90

        pct_30 = round((month_ret_30 / month_cohort_size) * 100, 1) if month_cohort_size > 0 else 0.0
        pct_60 = round((month_ret_60 / month_cohort_size) * 100, 1) if month_cohort_size > 0 else 0.0
        pct_90 = round((month_ret_90 / month_cohort_size) * 100, 1) if month_cohort_size > 0 else 0.0

        cohort_rows.append(
            {
                "cohort_key": month_key,
                "cohort_label": month_label,
                "events_count": len(events_in_month),
                "total_cohort_size": month_cohort_size,
                "m1_30d": {
                    "count": month_ret_30,
                    "percentage": pct_30,
                    "status": "COMPLETED" if is_30d_eligible else "IN_PROGRESS",
                },
                "m2_60d": {
                    "count": month_ret_60,
                    "percentage": pct_60,
                    "status": "COMPLETED" if is_60d_eligible else "IN_PROGRESS",
                },
                "m3_90d": {
                    "count": month_ret_90,
                    "percentage": pct_90,
                    "status": "COMPLETED" if is_90d_eligible else "IN_PROGRESS",
                },
            }
        )

    return {
        "sede_id": str(user_sede_uuid) if user_sede_uuid else "ALL",
        "generated_at": now.isoformat(),
        "cohorts": cohort_rows,
    }


def get_attendee_spiritual_journey(
    db: Session,
    persona_id: UUID | str,
) -> dict[str, Any]:
    """Retorna la línea de tiempo completa del camino espiritual del creyente con todos sus hitos."""
    p_uuid = UUID(str(persona_id)) if not isinstance(persona_id, UUID) else persona_id
    persona = db.query(Persona).filter(Persona.id == p_uuid).first()
    if not persona:
        raise ValueError("Persona no encontrada")

    # Eventos a los que ha asistido
    event_attendances = (
        db.query(models.EventRegistration)
        .filter(
            models.EventRegistration.persona_id == p_uuid,
            models.EventRegistration.deleted_at.is_(None),
            models.EventRegistration.check_in_at.isnot(None),
        )
        .all()
    )

    events_list = [
        {
            "event_id": str(reg.event_id),
            "event_name": reg.event.name if reg.event else "Evento",
            "attended_at": reg.check_in_at.isoformat() if reg.check_in_at else None,
        }
        for reg in event_attendances
    ]

    # Asistencias a grupo de vida
    group_attendances = (
        db.query(Asistencia)
        .join(SesionGrupo, Asistencia.sesion_id == SesionGrupo.id)
        .filter(
            Asistencia.persona_id == p_uuid,
            Asistencia.deleted_at.is_(None),
            SesionGrupo.deleted_at.is_(None),
            Asistencia.estado.in_(["presente", "primera_vez", "asistio"]),
        )
        .order_by(SesionGrupo.fecha_sesion.desc())
        .all()
    )

    # Academia
    academy = (
        db.query(Enrollment)
        .filter(
            Enrollment.persona_id == p_uuid,
            Enrollment.deleted_at.is_(None),
        )
        .all()
    )

    # CRM
    crm_case = (
        db.query(CasoCRM)
        .filter(
            CasoCRM.persona_id == p_uuid,
            CasoCRM.deleted_at.is_(None),
        )
        .first()
    )

    # Ministerios
    ministries = (
        db.query(PersonaMinistry)
        .filter(
            PersonaMinistry.persona_id == p_uuid,
            PersonaMinistry.deleted_at.is_(None),
        )
        .all()
    )

    # Calcular SMI
    has_decision = bool(crm_case or persona.spiritual_status in ["Creyente", "Consolidado", "Bautizado"])
    in_group = len(group_attendances) > 0
    is_baptized = bool(persona.is_baptized or persona.baptism_date is not None)
    has_academy = len(academy) > 0
    is_leader = len(ministries) > 0 or "LIDER" in (persona.church_role or "").upper()

    score = 0.0
    milestones = []
    if has_decision:
        score += 20.0
        milestones.append({"title": "Decisión de Fe", "date": persona.church_join_date or persona.created_at, "pts": 20})
    if in_group:
        score += 20.0
        milestones.append({"title": "Conexión a Grupo de Vida", "date": group_attendances[-1].sesion.fecha_sesion, "pts": 20})
    if is_baptized:
        score += 20.0
        milestones.append({"title": "Paso de Fe: Bautismo", "date": persona.baptism_date, "pts": 20})
    if has_academy:
        score += 20.0
        milestones.append({"title": "Formación en Academia", "date": academy[0].created_at, "pts": 20})
    if is_leader:
        score += 20.0
        milestones.append({"title": "Servicio Activo en la Obra", "date": None, "pts": 20})

    return {
        "persona_id": str(persona.id),
        "full_name": persona.nombre_completo,
        "email": persona.email,
        "phone": persona.phone or persona.mobile_phone,
        "church_role": persona.church_role,
        "spiritual_status": persona.spiritual_status,
        "spiritual_maturity_score": score,
        "maturity_level": _classify_spiritual_maturity(score),
        "events_attended_count": len(events_list),
        "group_meetings_attended_count": len(group_attendances),
        "academy_courses_count": len(academy),
        "milestones": milestones,
        "events": events_list,
    }


def export_cohort_pastoral_report_csv(
    db: Session,
    requesting_sede_id: UUID | str | None = None,
) -> str:
    """Genera el contenido CSV formateado para Excel (con UTF-8 BOM) del reporte pastoral multi-sede."""
    multi_sede_data = calculate_multi_sede_cohort_analysis(db, requesting_user_sede_id=requesting_sede_id)
    matrix_data = calculate_temporal_cohort_matrix(db, sede_id=requesting_sede_id, months_count=6)

    output = io.StringIO()
    # Escribir UTF-8 BOM para que Excel en español/Windows lo abra con tildes y caracteres correctos
    output.write("\ufeff")
    writer = csv.writer(output)

    # Cabecera Institucional
    writer.writerow(["COMUNIDAD CRISTIANA EL FARO — PLATAFORMA CCF"])
    writer.writerow(["INFORME EJECUTIVO DE RETENCIÓN DE COHORTES, LTV ESPIRITUAL Y EFECTIVIDAD PASTORAL"])
    writer.writerow([f"Fecha de Generación (UTC): {multi_sede_data['calculated_at']}"])
    writer.writerow([])

    # Sección 1: KPIs Globales
    kpis = multi_sede_data["global_kpis"]
    writer.writerow(["RESUMEN EJECUTIVO GLOBAL"])
    writer.writerow(["Total Sedes", "Total Eventos", "Total Asistentes Cohorte", "Retención Media 30d (%)", "Retención Media 60d (%)", "Retención Media 90d (%)", "LTV Espiritual Promedio (SMI)"])
    writer.writerow([
        kpis["total_sedes"],
        kpis["total_events"],
        kpis["total_cohort_size"],
        f"{kpis['avg_retention_30d_pct']}%",
        f"{kpis['avg_retention_60d_pct']}%",
        f"{kpis['avg_retention_90d_pct']}%",
        f"{kpis['global_avg_spiritual_maturity']} / 100",
    ])
    writer.writerow([])

    # Sección 2: Ranking Multi-Sede
    writer.writerow(["RANKING Y AUDITORÍA PASTORAL INTER-SEDES"])
    writer.writerow([
        "Puesto",
        "Sede",
        "Ciudad",
        "Eventos Realizados",
        "Total Asistentes",
        "Retención 30d (%)",
        "Retención 60d (%)",
        "Retención 90d (%)",
        "Tasa Bautismo (%)",
        "Tasa Academia (%)",
        "Madurez Espiritual Media",
        "Índice Efectividad Pastoral",
    ])
    for s in multi_sede_data["sedes_ranking"]:
        writer.writerow([
            s["rank_position"],
            s["sede_name"],
            s["city"],
            s["total_events"],
            s["total_cohort_size"],
            f"{s['retention_30d_pct']}%",
            f"{s['retention_60d_pct']}%",
            f"{s['retention_90d_pct']}%",
            f"{s['baptism_rate_pct']}%",
            f"{s['academy_rate_pct']}%",
            s["avg_spiritual_maturity_score"],
            s["pastoral_efficiency_score"],
        ])
    writer.writerow([])

    # Sección 3: Matriz Temporal de Cohortes
    writer.writerow(["MATRIZ TEMPORAL DE RETENCIÓN POR COHORTES MENSUALES"])
    writer.writerow(["Cohorte", "Mes", "Eventos", "Tamaño Cohorte", "Mes 1 (30d)", "Mes 2 (60d)", "Mes 3 (90d)"])
    for m in matrix_data["cohorts"]:
        writer.writerow([
            m["cohort_key"],
            m["cohort_label"],
            m["events_count"],
            m["total_cohort_size"],
            f"{m['m1_30d']['percentage']}% ({m['m1_30d']['status']})",
            f"{m['m2_60d']['percentage']}% ({m['m2_60d']['status']})",
            f"{m['m3_90d']['percentage']}% ({m['m3_90d']['status']})",
        ])

    return output.getvalue()
