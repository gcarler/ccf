# Milestone 1: Pastoral Health Score - Handoff Report

## 1. Observation
This report outlines the codebase investigation for Milestone 1: Pastoral Health Score, focusing on the database schema, migration structure, scoring business rules, and fix strategy.

### 1.1 Database Schema Locations
- **Persona Table**: Defined in `/root/ccf/backend/models_crm.py` (Line 330 onwards). The table name is `personas`.
- **Attendance Tables**:
  1. **Group Attendance (`Asistencia`)**: `/root/ccf/backend/models_evangelism.py` (Line 429). Fields: `id`, `sesion_id`, `persona_id`, `estado` (present/excused/absent), `es_primera_vez`, `attended` (property evaluating `estado` and `es_primera_vez`).
  2. **Event Attendance (`EventAttendance`)**: `/root/ccf/backend/models_crm.py` (Line 132). Fields: `id`, `event_id`, `persona_id`, `attended` (bool).
  3. **Course Attendance (`CourseAttendance`)**: `/root/ccf/backend/models_academy_core.py` (Line 242). Fields: `id`, `enrollment_id`, `status` (String, default "present").
- **Spiritual Milestones Table**: `/root/ccf/backend/models_crm.py` (Line 623). Fields: `id`, `persona_id` (FK to personas), `type` (baptism/course completion/etc.), `event_date`.
- **Communication Logs Table**: `/root/ccf/backend/models_crm.py` (Line 599). Fields: `id`, `persona_id`, `channel` (whatsapp/sms/email), `outcome` (sent/etc.).
- **Interactions Table**: `/root/ccf/backend/models_crm_pipeline.py` (Line 162). Fields: `id`, `caso_id` (FK to crm_casos), `realizado_por_id`.

### 1.2 Database Migration Configuration
- **alembic.ini**: Located at `/root/ccf/alembic.ini`. Revision scripts location is defined as:
  ```ini
  version_locations = %(here)s/alembic/canonical_versions
  ```
- **Migration scripts location**: `/root/ccf/alembic/canonical_versions/`.
- **Migration head**: `/root/ccf/alembic/canonical_versions/e71d968a23a8_add_crm_workflows_and_seaweed.py` (Revision: `'e71d968a23a8'`).

### 1.3 Business Rules for Pastoral Health Score
From `/root/ccf/.agents/implementation_orch/SCOPE.md` (Lines 26-31):
- **Columns**: `health_score` (Integer, 0-100) and `health_status` (String).
- **Scoring Engine**: Calculates score based on attendance, spiritual milestones, and communication logs.
- **Boundaries**:
  - `EN_RIESGO`: Score < 40
  - `ESTABLE`: 40 <= Score < 80
  - `COMPROMETIDO`: Score >= 80

---

## 2. Logic Chain
1. To introduce the new fields, the `personas` table schema must include columns `health_score` (Integer) and `health_status` (String). This is done by modifying `backend/models_crm.py` (adding columns to the `Persona` SQLAlchemy class) and adding corresponding fields in `backend/schemas/crm/base.py` (`PersonaResponse` Pydantic model) so the API serializes them.
2. A database migration script must be placed under `/root/ccf/alembic/canonical_versions/` to add these two columns. Since the current migration head is `e71d968a23a8`, the new script's `down_revision` must point to `'e71d968a23a8'`.
3. To calculate the score:
   - **Attendance contribution (0-50 pts)**: Retrieve all attendance records (`Asistencia` with `attended=True`, `EventAttendance` with `attended=True`, `CourseAttendance` with `status="present"`). Calculate the overall attendance rate `attended_count / total_opportunities`, scaled to 50 points.
   - **Spiritual Milestones contribution (0-30 pts)**: Count milestones in `SpiritualMilestone` for the persona plus the `is_baptized` column. Award 10 points per milestone, capped at 30 points.
   - **Communication contribution (0-20 pts)**: Count records in `CommunicationLog` and `InteraccionCRM` associated with the persona. Award 5 points per contact/interaction, capped at 20 points.
   - Sum components, clamp between 0-100, and classify status (`EN_RIESGO` / `ESTABLE` / `COMPROMETIDO`).

---

## 3. Caveats
- No specific scoring mathematical formula was provided in `SCOPE.md`; therefore, the proposed formula is a standard, robust additive engine scaling attendance (50%), milestones (30%), and communication logs (20%).
- Testing relies on SQLite for unit tests and local runs. Standard SQLite limitations for modifying tables are handled by Alembic's batch operations (`render_as_batch=True`), which is already configured in `/root/ccf/alembic/env.py`.

---

## 4. Conclusion
The database, schema files, and migration chain are fully documented. The proposed implementation will add the columns via an Alembic batch migration, write a scoring engine helper in `backend/crud/crm_/health.py`, update `PersonaResponse` in `backend/schemas/crm/base.py`, and expose the fields through the existing `GET /personas/{id}` endpoint.

---

## 5. Verification Method
### 5.1 Step-by-Step Fix Strategy
1. **Model Modification**: Add `health_score` (Integer, nullable=True) and `health_status` (String(20), nullable=True) to `/root/ccf/backend/models_crm.py`.
2. **Schema Modification**: Add `health_score: Optional[int] = None` and `health_status: Optional[str] = None` to `PersonaResponse` in `/root/ccf/backend/schemas/crm/base.py`.
3. **Migration Script**: Create `/root/ccf/alembic/canonical_versions/<timestamp>_add_pastoral_health_score.py` with:
   - `revision = '<new_revision_id>'`
   - `down_revision = 'e71d968a23a8'`
   - Batch alter table `personas` to add `health_score` and `health_status`.
4. **Scoring Engine**: Create `backend/crud/crm_/health.py` containing the logic to calculate and persist the scores:
   - `calculate_pastoral_health(db: Session, persona_id: UUID) -> tuple[int, str]`
   - `update_pastoral_health(db: Session, persona_id: UUID) -> models.Persona`
5. **API Updates**: Import and call `update_pastoral_health` prior to returning persona details in `get_persona` (`/root/ccf/backend/api/crm/personas.py`), keeping calculations up to date.

### 5.2 Baseline Verification Results
The existing test suite was executed to establish a baseline:
- **Command**: `venv/bin/pytest`
- **Result**: 3596 passed, 113 failed, 6 skipped, 11 xfailed, 7 xpassed, 90 warnings in 2692.81s (44:52).
- **Baseline Status**: There are 113 failing tests in the existing suite, primarily located in CMS, SEO, and old CRM endpoints. These represent pre-existing errors in the baseline codebase. Any implementation of Milestone 1 should ensure that these do not increase, and that the new test file (`tests/test_pastoral_health_score.py`) passes 100%.

### 5.3 Verification Commands
- Apply migrations:
  ```bash
  venv/bin/alembic upgrade head
  ```
- Run the new test suite for pastoral health score:
  ```bash
  venv/bin/pytest tests/test_pastoral_health_score.py
  ```
