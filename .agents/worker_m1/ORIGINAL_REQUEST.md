## 2026-07-10T05:37:00Z
You are the Worker for Milestone 1: Pastoral Health Score.
Your working directory is /root/ccf/.agents/worker_m1.
Your tasks are:
1. Modify /root/ccf/backend/models_crm.py to add health_score (Integer, nullable=True) and health_status (String(20), nullable=True) columns to the Persona class.
2. Modify /root/ccf/backend/schemas/crm/base.py to add health_score: Optional[int] = None and health_status: Optional[str] = None to the PersonaResponse Pydantic model.
3. Create backend/crud/crm_/health.py containing:
   - calculate_pastoral_health(db: Session, persona_id: UUID) -> tuple[int, str]:
     Calculates score as attendance_score + milestone_score + communication_score, clamped to 0-100.
     - Attendance score: attended / opportunities * 50 if opportunities > 0 else 0.
       Opportunities = Asistencia (where deleted_at is null), EventAttendance, and CourseAttendance (linked via Enrollment where Enrollment.deleted_at is null).
       Attended = Asistencia (where lowercase trimmed estado is in asistio, presente, present, primera_vez, first_time), EventAttendance (where attended == True), CourseAttendance (where status is lowercase "present").
     - Milestone score: Count milestones in SpiritualMilestone (where deleted_at is null) plus 1 if Persona.is_baptized is True. Award 10 points per milestone, capped at 30 points.
     - Communication score: Count CommunicationLog records plus InteraccionCRM records linked to the persona via a CasoCRM. Award 5 points per contact/interaction, capped at 20 points.
     - Status boundaries:
       - EN_RIESGO: Score < 40
       - ESTABLE: 40 <= Score < 80
       - COMPROMETIDO: Score >= 80
   - update_pastoral_health(db: Session, persona_id: UUID) -> models.Persona:
     Calculates, writes health_score and health_status to the Persona record in DB, commits the session, and returns the updated Persona object.
4. Update get_persona in /root/ccf/backend/api/crm/personas.py to call update_pastoral_health before returning the persona to ensure the response contains up-to-date score.
5. Create a new Alembic migration script under /root/ccf/alembic/canonical_versions/ to add health_score and health_status columns to personas table. Set its down_revision = 'e71d968a23a8'. Use batch operations so it works seamlessly on SQLite (using op.batch_alter_table).
6. Run database migrations to apply the schema changes (venv/bin/alembic upgrade head).
7. Write unit tests for this functionality (e.g. in /root/ccf/tests/test_pastoral_health_score.py) verifying database persistence, scoring logic calculations, status boundaries, and API serialization.
8. Run the test suite (venv/bin/pytest tests/test_pastoral_health_score.py and other relevant tests) and verify everything passes.
9. Write a detailed handoff report in /root/ccf/.agents/worker_m1/handoff.md.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Communicate your results back to me by sending a message when done.
