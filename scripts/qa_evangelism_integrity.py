from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import and_, exists, func, or_

sys.path.append(str(Path(__file__).parent.parent))

from backend import models
from backend.core.database import SessionLocal


def _print_block(title: str) -> None:
    print(f"\n=== {title} ===")


def run_integrity_audit() -> int:
    db = SessionLocal()
    issues = 0
    warnings = 0

    try:
        print("CCF Evangelismo/Agenda - QA Integridad")

        _print_block("Eventos")
        events_without_name = (
            db.query(func.count(models.CrmEvent.id))
            .filter(
                or_(
                    models.CrmEvent.name.is_(None),
                    func.trim(models.CrmEvent.name) == "",
                )
            )
            .scalar()
            or 0
        )
        cancelled_without_reason = (
            db.query(func.count(models.CrmEvent.id))
            .filter(
                func.upper(func.coalesce(models.CrmEvent.status, "")) == "CANCELLED",
                or_(
                    models.CrmEvent.cancellation_reason.is_(None),
                    func.trim(models.CrmEvent.cancellation_reason) == "",
                ),
            )
            .scalar()
            or 0
        )
        print(f"- Eventos sin nombre: {events_without_name}")
        print(f"- Eventos cancelados sin razón: {cancelled_without_reason}")
        issues += int(events_without_name) + int(cancelled_without_reason)

        _print_block("Asistencia de Eventos")
        attendance_orphan_event = (
            db.query(func.count(models.EventAttendance.id))
            .filter(
                ~exists().where(models.CrmEvent.id == models.EventAttendance.event_id)
            )
            .scalar()
            or 0
        )
        attendance_orphan_member = (
            db.query(func.count(models.EventAttendance.id))
            .filter(
                ~exists().where(models.Member.id == models.EventAttendance.member_id)
            )
            .scalar()
            or 0
        )
        attendance_status_mismatch = (
            db.query(func.count(models.EventAttendance.id))
            .filter(
                or_(
                    and_(
                        models.EventAttendance.attended.is_(True),
                        models.EventAttendance.status != "present",
                    ),
                    and_(
                        models.EventAttendance.attended.is_(False),
                        models.EventAttendance.status != "absent",
                    ),
                )
            )
            .scalar()
            or 0
        )
        attendance_missing_session_date = (
            db.query(func.count(models.EventAttendance.id))
            .filter(models.EventAttendance.session_date.is_(None))
            .scalar()
            or 0
        )
        cancelled_event_with_present_attendance = (
            db.query(func.count(models.EventAttendance.id))
            .join(
                models.CrmEvent, models.CrmEvent.id == models.EventAttendance.event_id
            )
            .filter(
                func.upper(func.coalesce(models.CrmEvent.status, "")) == "CANCELLED",
                models.EventAttendance.attended.is_(True),
            )
            .scalar()
            or 0
        )
        print(
            f"- Asistencias huérfanas (evento inexistente): {attendance_orphan_event}"
        )
        print(
            f"- Asistencias huérfanas (miembro inexistente): {attendance_orphan_member}"
        )
        print(f"- Inconsistencia attended/status: {attendance_status_mismatch}")
        print(f"- Registros sin session_date: {attendance_missing_session_date}")
        print(
            f"- Presentes en eventos cancelados: {cancelled_event_with_present_attendance}"
        )
        issues += (
            int(attendance_orphan_event)
            + int(attendance_orphan_member)
            + int(attendance_status_mismatch)
            + int(attendance_missing_session_date)
            + int(cancelled_event_with_present_attendance)
        )

        _print_block("Agenda")
        agenda_invalid_range = (
            db.query(func.count(models.AgendaEvent.id))
            .filter(
                models.AgendaEvent.end_at.is_not(None),
                models.AgendaEvent.end_at < models.AgendaEvent.start_at,
            )
            .scalar()
            or 0
        )
        agenda_orphan_creator = (
            db.query(func.count(models.AgendaEvent.id))
            .filter(
                models.AgendaEvent.created_by_user_id.is_not(None),
                ~exists().where(
                    models.User.id == models.AgendaEvent.created_by_user_id
                ),
            )
            .scalar()
            or 0
        )
        print(
            f"- Eventos agenda con rango inválido (end_at < start_at): {agenda_invalid_range}"
        )
        print(f"- Eventos agenda con creador inexistente: {agenda_orphan_creator}")
        issues += int(agenda_invalid_range) + int(agenda_orphan_creator)

        _print_block("Faro")
        sessions_orphan_house = (
            db.query(func.count(models.GloryHouseSession.id))
            .filter(
                ~exists().where(
                    models.GloryHouse.id == models.GloryHouseSession.glory_house_id
                )
            )
            .scalar()
            or 0
        )
        sessions_orphan_season = (
            db.query(func.count(models.GloryHouseSession.id))
            .filter(
                models.GloryHouseSession.season_id.is_not(None),
                ~exists().where(
                    models.FaroSeason.id == models.GloryHouseSession.season_id
                ),
            )
            .scalar()
            or 0
        )
        faro_attendance_orphan_session = (
            db.query(func.count(models.GloryHouseAttendance.id))
            .filter(
                ~exists().where(
                    models.GloryHouseSession.id
                    == models.GloryHouseAttendance.session_id
                )
            )
            .scalar()
            or 0
        )
        faro_attendance_orphan_member = (
            db.query(func.count(models.GloryHouseAttendance.id))
            .filter(
                ~exists().where(
                    models.Member.id == models.GloryHouseAttendance.member_id
                )
            )
            .scalar()
            or 0
        )
        print(f"- Sesiones Faro sin casa válida: {sessions_orphan_house}")
        print(f"- Sesiones Faro con temporada inexistente: {sessions_orphan_season}")
        print(f"- Asistencias Faro sin sesión válida: {faro_attendance_orphan_session}")
        print(f"- Asistencias Faro sin miembro válido: {faro_attendance_orphan_member}")
        issues += (
            int(sessions_orphan_house)
            + int(sessions_orphan_season)
            + int(faro_attendance_orphan_session)
            + int(faro_attendance_orphan_member)
        )

        _print_block("Resumen")
        print(f"- Issues críticos: {issues}")
        print(f"- Warnings: {warnings}")

        if issues > 0:
            print("Resultado: FAIL")
            return 1

        print("Resultado: PASS")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(run_integrity_audit())
