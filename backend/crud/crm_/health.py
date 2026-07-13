"""Pastoral health scoring and updating logic."""

from datetime import date
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.orm import Session

from backend import models
from backend.api.crm._shared import persona_query, prepare_persona_for_output


def _load_persona_for_health(db: Session, persona_id: UUID):
    persona = db.get(models.Persona, persona_id)
    if persona is not None:
        return persona
    return db.query(models.Persona).filter(models.Persona.id == persona_id).first()



def calculate_pastoral_health(db: Session, persona_id: UUID) -> tuple[int, str]:
    """Calculates score as attendance_score + milestone_score + communication_score + donation_score, clamped to 0-100.

    - Attendance score: attended / opportunities * 50 if opportunities > 0 else 0.
      Opportunities = Asistencia (where deleted_at is null), EventAttendance, and CourseAttendance (linked via Enrollment where Enrollment.deleted_at is null).
      Attended = Asistencia (where lowercase trimmed estado is in asistio, presente, present, primera_vez, first_time), EventAttendance (where attended == True), CourseAttendance (where status is lowercase "present").
    - CommunicationLog content check: If a CommunicationLog has content containing "attend", "asist", "session", "class", "culto", or "grupo" (case-insensitive), increment both total_opportunities and total_attended by 1.
    - Milestone score: Count milestones in SpiritualMilestone (where deleted_at is null) plus 1 if Persona.is_baptized is True. Award 10 points per milestone, capped at 30 points.
    - Communication score: Count CommunicationLog records plus InteraccionCRM records linked to the persona via a CasoCRM. Award 5 points per contact/interaction, capped at 20 points.
    - Donation score:
      - Count active Donation records (where deleted_at is null).
      - If donation_count == 0: donation_score = 0.
      - If donation_count == 1: donation_score = 50.
      - If donation_count > 1: 50 + min(40, (donation_count - 1) * 5).
    - Total score: min(100, attendance_score + milestone_score + communication_score + donation_score)
    - Status boundaries:
      - EN_RIESGO: Score < 40
      - ESTABLE: 40 <= Score < 80
      - COMPROMETIDO: Score >= 80
    """
    persona = _load_persona_for_health(db, persona_id)
    if not persona:
        raise ValueError(f"Persona with ID {persona_id} not found")

    previous_status = getattr(persona, "health_status", None)
    is_baptized = bool(getattr(persona, "is_baptized", False))

    # 1. Attendance score
    # Asistencia opportunities & attended
    opp_asistencias = (
        db.query(models.Asistencia)
        .filter(models.Asistencia.persona_id == persona_id, models.Asistencia.deleted_at.is_(None))
        .all()
    )
    opp_asistencias_count = len(opp_asistencias)
    attended_asistencias_count = sum(
        1
        for a in opp_asistencias
        if a.estado and a.estado.strip().lower() in {"asistio", "presente", "present", "primera_vez", "first_time"}
    )

    # EventAttendance opportunities & attended
    event_attendances = db.query(models.EventAttendance).filter(models.EventAttendance.persona_id == persona_id).all()
    opp_events_count = len(event_attendances)
    attended_events_count = sum(1 for e in event_attendances if e.attended is True)

    # CourseAttendance opportunities & attended
    course_attendances = (
        db.query(models.CourseAttendance)
        .join(models.Enrollment, models.CourseAttendance.enrollment_id == models.Enrollment.id)
        .filter(models.Enrollment.persona_id == persona_id, models.Enrollment.deleted_at.is_(None))
        .all()
    )
    opp_courses_count = len(course_attendances)
    attended_courses_count = sum(1 for c in course_attendances if c.status and c.status.strip().lower() == "present")

    # CommunicationLog content check for attendance opportunity
    comm_logs = db.query(models.CommunicationLog).filter(models.CommunicationLog.persona_id == persona_id).all()
    comm_log_attend_count = 0
    for log in comm_logs:
        if log.content:
            content_lower = log.content.lower()
            if any(keyword in content_lower for keyword in ["attend", "asist", "session", "class", "culto", "grupo"]):
                comm_log_attend_count += 1

    opportunities = opp_asistencias_count + opp_events_count + opp_courses_count + comm_log_attend_count
    attended = attended_asistencias_count + attended_events_count + attended_courses_count + comm_log_attend_count

    if opportunities > 0:
        attendance_score = (attended / opportunities) * 50
    else:
        attendance_score = 0.0

    recent_score = 0.0
    today = date.today()
    if persona.last_meeting_attendance:
        last_meet = persona.last_meeting_attendance
        if hasattr(last_meet, "date") and callable(getattr(last_meet, "date")):
            last_meet = last_meet.date()
        if 0 <= (today - last_meet).days <= 30:
            recent_score = 40.0
    if persona.last_group_attendance:
        last_group = persona.last_group_attendance
        if hasattr(last_group, "date") and callable(getattr(last_group, "date")):
            last_group = last_group.date()
        if 0 <= (today - last_group).days <= 30:
            recent_score = 40.0

    attendance_score = max(attendance_score, recent_score)

    # 2. Milestone score
    all_milestones = (
        db.query(models.SpiritualMilestone)
        .filter(models.SpiritualMilestone.persona_id == persona_id, models.SpiritualMilestone.deleted_at.is_(None))
        .all()
    )
    # Filter out health status change milestones so they do not artificially inflate the health score
    active_milestones = [m for m in all_milestones if not (m.type and m.type.startswith("Health Status Change to"))]
    milestones_count = len(active_milestones)

    # Automatically set persona.is_baptized = True (and commit it) if the persona has any active SpiritualMilestone
    # of type containing "bapt" or "baut" (case-insensitive)
    has_bapt = False
    for m in active_milestones:
        if m.type and any(kw in m.type.lower() for kw in ["bapt", "baut"]):
            has_bapt = True
            break
    update_values = {}
    if has_bapt and hasattr(models.Persona, "is_baptized"):
        is_baptized = True
        update_values["is_baptized"] = True

    milestone_points = milestones_count
    if is_baptized or bool(getattr(persona, "is_baptized", False)):
        milestone_points += 1

    milestone_score = min(milestone_points * 10, 30)

    # 3. Communication score
    comm_logs_count = len(comm_logs)

    interactions_count = (
        db.query(models.InteraccionCRM)
        .join(models.CasoCRM, models.InteraccionCRM.caso_id == models.CasoCRM.id)
        .filter(models.CasoCRM.persona_id == persona_id, models.CasoCRM.deleted_at.is_(None))
        .count()
    )

    total_contacts = comm_logs_count + interactions_count
    communication_score = min(total_contacts * 5, 20)

    # 4. Donation score
    donation_count = (
        db.query(models.Donation)
        .filter(models.Donation.persona_id == persona_id, models.Donation.deleted_at.is_(None))
        .count()
    )
    if donation_count == 0:
        donation_score = 0.0
    elif donation_count == 1:
        donation_score = 50.0
    else:
        donation_score = 50.0 + min(40.0, (donation_count - 1) * 5.0)

    # Final score and status
    total_score = attendance_score + milestone_score + communication_score + donation_score
    clamped_score = max(0, min(100, int(round(total_score))))

    if clamped_score < 40:
        status = "EN_RIESGO"
    elif clamped_score < 80:
        status = "ESTABLE"
    else:
        status = "COMPROMETIDO"

    if previous_status is None or previous_status != status:
        if hasattr(models.Persona, "health_score") or hasattr(models.Persona, "health_status"):
            milestone = models.SpiritualMilestone(
                persona_id=persona_id,
                type=f"Health Status Change to {status}",
                event_date=date.today(),
                notes=f"Health score updated to {clamped_score}",
            )
            db.add(milestone)

    if hasattr(models.Persona, "health_score"):
        update_values["health_score"] = clamped_score
    if hasattr(models.Persona, "health_status"):
        update_values["health_status"] = status

    if update_values:
        db.execute(
            update(models.Persona)
            .where(models.Persona.id == persona_id)
            .values(**update_values)
        )

    return clamped_score, status


def update_pastoral_health(db: Session, persona_id: UUID) -> models.Persona:
    """Calculates, writes health_score and health_status to the Persona record in DB,
    commits the session, and returns the updated Persona object.
    """
    calculate_pastoral_health(db, persona_id)
    db.commit()
    persona = persona_query(db).filter(models.Persona.id == persona_id).first()
    if persona:
        return prepare_persona_for_output(db, persona)
    return None


calculate_pastoral_health_score = calculate_pastoral_health
calculate_health_score = calculate_pastoral_health
