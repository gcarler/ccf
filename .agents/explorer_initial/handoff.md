# Codebase Analysis Handoff Report

## 1. Observation
This codebase analysis investigated the backend and frontend components of CCF's CRM system to answer six specific questions.

### 1.1 Model Definitions (Question 1 & 2)
The database models are written in Python using SQLAlchemy and are located under `backend/`. The models are modularized and re-exported from `backend/models.py`.

#### A. Persona Model
*   **File Path:** `/root/ccf/backend/models_crm.py` (Line 330)
*   **Table Name:** `personas`
*   **Fields:**
    *   `id` = `Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)`
    *   `family_id` = `Column(UUID(as_uuid=True), ForeignKey("families.id", ondelete="SET NULL"), nullable=True, index=True)`
    *   `sede_id` = `Column(UUID(as_uuid=True), ForeignKey("sedes.id", ondelete="SET NULL"), nullable=True, index=True)`
    *   `first_name` = `Column(String(100), nullable=False, index=True)`
    *   `last_name` = `Column(String(100), nullable=False, index=True)`
    *   `second_name` = `Column(String(100), nullable=True)`
    *   `second_last_name` = `Column(String(100), nullable=True)`
    *   `email` = `Column(String(100), nullable=True, index=True)`
    *   `phone` = `Column(String(20), nullable=True, index=True)`
    *   `mobile_phone` = `Column(String(20), nullable=True)`
    *   `landline_phone` = `Column(String(20), nullable=True)`
    *   `other_phone` = `Column(String(20), nullable=True)`
    *   `church_role` = `Column(String(50), default="Miembro", index=True)`
    *   `is_baptized` = `Column(Boolean, default=False, index=True)`
    *   `baptism_date` = `Column(Date, nullable=True)`
    *   `spiritual_status` = `Column(String(50), default="Nuevo", index=True)`
    *   `estado_vital` = `Column(String(50), nullable=True, default="ACTIVO")`
    *   `ministerio` = `Column(String(100), nullable=True)`
    *   `permiso_plataforma` = `Column(String(50), nullable=True)`
    *   `id_type` = `Column(String(50), nullable=True)`
    *   `id_number` = `Column(String(50), nullable=True)`
    *   `marital_status` = `Column(String(50), nullable=True)`
    *   `birth_country` = `Column(String(100), nullable=True)`
    *   `address` = `Column(Text, nullable=True)`
    *   `housing_type` = `Column(String(50), nullable=True)`
    *   `education_level` = `Column(String(100), nullable=True)`
    *   `education_status` = `Column(String(50), nullable=True)`
    *   `profession` = `Column(String(100), nullable=True)`
    *   `economic_sector` = `Column(String(100), nullable=True)`
    *   `blood_type` = `Column(String(10), nullable=True)`
    *   `medical_notes` = `Column(Text, nullable=True)`
    *   `optional_info` = `Column(Text, nullable=True)`
    *   `registration_reason` = `Column(String(100), nullable=True)`
    *   `unregistration_reason` = `Column(String(100), nullable=True)`
    *   `registration_date` = `Column(Date, nullable=True)`
    *   `unregistration_date` = `Column(Date, nullable=True)`
    *   `responsible_adult_name` = `Column(String(200), nullable=True)`
    *   `responsible_adult_contact` = `Column(String(100), nullable=True)`
    *   `guardian_name` = `Column(String(200), nullable=True)`
    *   `guardian_contact` = `Column(String(100), nullable=True)`
    *   `sex` = `Column(String(1), nullable=True)`
    *   `last_group_attendance` = `Column(Date, nullable=True)`
    *   `last_meeting_attendance` = `Column(Date, nullable=True)`
    *   `participation_type` = `Column(String(50), nullable=True)`
    *   `attendance_type` = `Column(String(50), nullable=True)`
    *   `group_name` = `Column(String(100), nullable=True)`
    *   `campus` = `Column(String(100), nullable=True)`
    *   `church_join_date` = `Column(Date, nullable=True)`
    *   `colombian_department_id` = `Column(UUID(as_uuid=True), ForeignKey("colombian_departments.id", ondelete="SET NULL"), nullable=True, index=True)`
    *   `city` = `Column(String(100), nullable=True)`
    *   `latitud` = `Column(Numeric(10, 8), nullable=True)`
    *   `longitud` = `Column(Numeric(11, 8), nullable=True)`
    *   `qr_token` = `Column(String(100), nullable=True, index=True)`
    *   `birthday` = `Column(Date, nullable=True)`
    *   `role_in_family` = `Column(String(50), nullable=True)`
    *   `talents` = `Column(Text, nullable=True)`
    *   `spiritual_gifts` = `Column(Text, nullable=True)`
    *   `pastoral_notes` = `Column(Text, nullable=True)`
    *   `photo_url` = `Column(String(500), nullable=True)`
    *   `bio_short` = `Column(Text, nullable=True)`
    *   `bio_full` = `Column(Text, nullable=True)`
    *   `social_instagram` = `Column(String(200), nullable=True)`
    *   `social_facebook` = `Column(String(200), nullable=True)`
    *   `social_twitter` = `Column(String(200), nullable=True)`
    *   `is_pastoral_leader` = `Column(Boolean, default=False, index=True)`
    *   `is_main_pastor` = `Column(Boolean, default=False)`
    *   `pastoral_sort_order` = `Column(Integer, default=0)`
    *   `is_pastoral_published` = `Column(Boolean, default=True)`
    *   `tags` = `Column(JSON, nullable=True, default=list)`
    *   `origen_estrategia_id` = `Column(UUID(as_uuid=True), ForeignKey("estrategias_evangelismo.id", ondelete="SET NULL"), nullable=True, index=True)`
    *   `origen_grupo_id` = `Column(UUID(as_uuid=True), ForeignKey("grupos_evangelismo.id", ondelete="SET NULL"), nullable=True, index=True)`
    *   `origen_sesion_id` = `Column(UUID(as_uuid=True), ForeignKey("sesiones_grupo.id", ondelete="SET NULL"), nullable=True)`
    *   `origen_fecha` = `Column(DateTime(timezone=True), nullable=True)`
    *   `created_at` = `Column(DateTime(timezone=True), default=_utcnow, index=True)`
    *   `updated_at` = `Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)`
    *   `scanner_token_hash` = `Column(String(128), nullable=True, index=True, comment="SHA-256 hash del scanner token")`
    *   `scanner_token_expires_at` = `Column(DateTime(timezone=True), nullable=True, comment="Fecha de expiración del scanner token")`

#### B. Attendance Models
Three different types of attendance are defined:
1.  **Event Attendance:** `/root/ccf/backend/models_crm.py` (Line 132)
    *   `class EventAttendance(Base)`: Tracks attendance at church events.
    *   **Fields:** `id` (UUID), `event_id` (UUID FK crm_events), `session_date` (Date), `persona_id` (UUID FK personas), `status` (Str(30), default "present"), `role_at_event` (Str(30)), `source` (Str(30)), `check_in_at` (DateTime), `check_out_at` (DateTime), `notes` (Text), `scanned_at` (DateTime), `attended` (Bool, default True).
2.  **Course Attendance:** `/root/ccf/backend/models_academy_core.py` (Line 242)
    *   `class CourseAttendance(Base)`: Tracks class attendance in the academy module.
    *   **Fields:** `id` (UUID), `enrollment_id` (UUID FK academy_enrollments), `session_date` (DateTime), `status` (Str(50), default "present"), `recorded_by_persona_id` (UUID FK personas).
3.  **Group Attendance:** `/root/ccf/backend/models_evangelism.py` (Line 429)
    *   `class Asistencia(Base)`: Tracks attendance for cell/discipleship group meetings.
    *   **Fields:** `id` (UUID), `sesion_id` (UUID FK sesiones_grupo), `persona_id` (UUID FK personas), `estado` (Str(20)), `motivo_excusa_id` (UUID FK motivos_excusa), `detalle_excusa` (Str(255)), `es_primera_vez` (Bool), `requiere_seguimiento` (Bool), `deleted_at` (DateTime).

#### C. Donations Model
*   **File Path:** `/root/ccf/backend/models_crm.py` (Line 515)
*   **Table Name:** `donations`
*   **Fields:** `id` (UUID), `persona_id` (UUID FK personas), `amount` (Numeric(14,2)), `currency` (String(10)), `sede_id` (UUID FK sedes), `donation_type` (String(50)), `status` (String(20)), `reference_code` (String(100)), `payment_method` (String(50)), `fund_id` (UUID FK funds), `donor_name` (String(100)), `donor_email` (String(200)), `created_at` (DateTime), `updated_at` (DateTime), `deleted_at` (DateTime).

#### D. Groups Model
Discipleship/Evangelism groups are structured under the evangelism models:
*   **File Path:** `/root/ccf/backend/models_evangelism.py` (Line 241)
*   **Table Name:** `grupos_evangelismo`
*   **Fields:** `id` (UUID), `estrategia_id` (UUID FK), `sede_id` (UUID FK sedes), `codigo` (String(30)), `nombre` (String(150)), `ubicacion` (String(255)), `direccion` (String(255)), `capacidad` (Integer), `latitud` (Float), `longitud` (Float), `dia_reunion` (String(20)), `hora_reunion` (String(10)), `activo` (Boolean), `lider_persona_id` (UUID FK personas), `asistente_persona_id` (UUID FK personas), `anfitrion_persona_id` (UUID FK personas), `parent_group_id` (UUID FK), `notes_historial` (Text), `created_at` (DateTime), `updated_at` (DateTime), `deleted_at` (DateTime).

#### E. Counseling Case Models (Tickets & Message History Logs)
Counseling cases are tracked using two parallel mechanisms:
1.  **Pastoral Counseling Tickets:** `/root/ccf/backend/models_crm.py` (Line 169)
    *   `class CounselingTicket(Base)`: Represents a counseling case/session.
    *   **Fields:** `id` (UUID), `persona_id` (UUID FK personas), `pastor_id` (UUID FK personas), `subject` (String(200)), `notes` (Text), `status` (String(50), default "open"), `priority_level` (String(20), default "NORMAL"), `sentiment_score` (Float), `sentiment_label` (String(20)), `created_at` (DateTime), `deleted_at` (DateTime).
2.  **Generic Pipeline-Based CRM Cases:** `/root/ccf/backend/models_crm_pipeline.py` (Line 115)
    *   `class CasoCRM(Base)`: General CRM ticket where type is `CONSEJERIA` (`TipoPipelineEnum.CONSEJERIA`).
    *   **Fields:** `id` (UUID), `persona_id` (UUID FK personas), `sede_id` (UUID FK), `pipeline_id` (UUID FK), `etapa_actual_id` (UUID FK), `titulo_caso` (String(200)), `prioridad` (Enum), `estado` (Enum), `origen_canal` (Enum), `origen_detalle_id` (String(200)), `origen_sesion_id` (UUID FK), `origen_grupo_id` (UUID FK), `origen_estrategia_id` (UUID FK), `payload_web` (JSON), `asignado_a_id` (UUID FK personas), `fecha_creacion` (DateTime), `fecha_cierre` (DateTime), `sla_vencimiento_contacto` (DateTime), `deleted_at` (DateTime).
    *   **Message/History Logs (Interactions):** `/root/ccf/backend/models_crm_pipeline.py` (Line 162)
        *   `class InteraccionCRM(Base)`: Individual history log entries for a `CasoCRM`.
        *   **Fields:** `id` (UUID), `caso_id` (UUID FK crm_casos), `realizado_por_id` (UUID FK personas), `tipo` (SAEnum `TipoInteraccionEnum`), `fecha_interaccion` (DateTime), `resumen` (Text), `duration_seconds` (Integer), `plantilla_usada_id` (UUID FK crm_plantillas_mensaje).

#### F. Communication Logs (WhatsApp, SMS, Email)
*   **File Path:** `/root/ccf/backend/models_crm.py` (Line 599)
*   **Table Name:** `communication_logs`
*   **Fields:** `id` (UUID), `persona_id` (UUID FK personas), `channel` (String(50)), `recipient_phone` (String(30)), `campaign_name` (String(120)), `content` (Text), `leader_id` (UUID FK personas), `outcome` (String(50), default "sent"), `external_id` (String(120)), `is_read` (Boolean), `created_at` (DateTime).
*   **Analytical template send log:** `/root/ccf/backend/models_crm.py` (Line 302)
    *   `class BitacoraEnvioPlantilla(Base)`: Logs specific message templates sent.
    *   **Fields:** `id` (UUID), `sede_id` (UUID FK sedes), `plantilla_id` (UUID FK), `caso_id` (UUID FK), `enviado_por_id` (UUID FK), `destinatario_id` (UUID FK), `fecha_envio` (DateTime), `estado` (Enum), `payload_hidratado` (JSON), `log_error` (Text).

#### G. Spiritual Milestones Model
*   **File Path:** `/root/ccf/backend/models_crm.py` (Line 623)
*   **Table Name:** `spiritual_milestones`
*   **Fields:** `id` (UUID), `sede_id` (UUID FK sedes), `persona_id` (UUID FK personas), `type` (String(100)), `event_date` (Date), `minister_id` (UUID FK personas), `notes` (Text), `created_at` (DateTime), `deleted_at` (DateTime).

---

### 1.2 Multi-Tenant Isolation handling (Question 3)
*   **File Path:** `/root/ccf/backend/core/tenant.py`
*   **Implementation Details:**
    *   User identity resolution uses `get_user_sede_id(db, user_or_id)` and `require_user_sede_id(db, current_user)` helper functions. These functions look up the user's `sede_id` from their `Usuario` or related `Persona` record.
    *   In the APIs (e.g. `backend/api/evangelism_grupos/grupos_sesiones.py`), endpoints explicitly enforce scoping by filtering queries on `sede_id`: `.filter(Model.sede_id == require_user_sede_id(db, current_user))`.
    *   For entities that lack a direct `sede_id` column (like `CounselingTicket`), tenant isolation is enforced by joining on the related `Persona` record and checking that the target person belongs to the user's tenant:
        ```python
        query = query.join(
            models.Persona, models.CounselingTicket.persona_id == models.Persona.id
        ).filter(models.Persona.sede_id == user_sede)
        ```
        (See helper `_get_scoped_counseling_ticket` in `backend/api/crm/_shared.py` at line 109).

---

### 1.3 Counseling History Retrieval (Question 4)
*   **File Path:** `/root/ccf/backend/api/crm/pastoral.py` (Line 924)
*   **Route:** `GET /api/crm/counseling/{ticket_id}`
*   **Retrieval Process:**
    1.  The primary ticket is retrieved and validated using the `_get_scoped_counseling_ticket(db, current_user, ticket_id)` helper to prevent cross-tenant exposure.
    2.  The history is retrieved by querying all `CounselingTicket` entries belonging to the same persona (`persona_id == ticket.persona_id`), sorted by `created_at` and `id` descending:
        ```python
        history_rows = (
            db.query(models.CounselingTicket)
            .filter(models.CounselingTicket.persona_id == ticket.persona_id)
            .order_by(models.CounselingTicket.created_at.desc(), models.CounselingTicket.id.desc())
            .all()
        )
        ```
    3.  The response aggregates details of the current ticket along with a list of the history rows:
        ```json
        {
            "id": ticket.id,
            "persona_id": ticket.persona_id,
            "persona_name": "...",
            "topic": ticket.subject,
            "notes": ticket.notes,
            "status": ticket.status,
            "priority_level": ticket.priority_level,
            "history": [
                {
                    "id": row.id,
                    "text": row.subject,
                    "status": row.status,
                    "created_at": "..."
                }
            ]
        }
        ```

---

### 1.4 OpenAI Integration (Question 5)
*   **File Paths:**
    *   Orchestrator: `/root/ccf/backend/agents/orchestrator.py`
    *   AI Router/Endpoints: `/root/ccf/backend/api/agents.py`
    *   Tools Registry: `/root/ccf/backend/services/tool_registry.py`
*   **Configuration:**
    *   The `AgentOrchestrator` uses the standard `openai` SDK (`OpenAI` client).
    *   It fetches API keys from environment variables `OPENROUTER_API_KEY` or `OPENAI_API_KEY`:
        ```python
        key = api_key or os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
        ```
    *   If the key starts with `sk-or-`, OpenRouter integration is activated (setting the client base URL to `https://openrouter.ai/api/v1` and using default model `moonshotai/kimi-k2.6`). Otherwise, it falls back to standard OpenAI endpoints and default model `gpt-4o-mini`.
*   **AI Endpoints/Helpers:**
    *   `POST /api/agents/ask` (`ask_optimus` in `/root/ccf/backend/api/agents.py`): Searches the local knowledge base using the query, extracts contexts/sources, compiles a combined prompt, and queries the `AgentOrchestrator` to generate a response.
*   **AI Tools:**
    *   Tools are registered under `/root/ccf/backend/services/tool_registry.py` and decorated/converted to OpenAI formats via `to_openai_function()`.
    *   Active tools include:
        1.  `CRMSearchPersona` (search church personas by name, email, or phone).
        2.  `CRMGetPersonaProfile` (retrieve a persona's complete profile by UUID).
        3.  `AcademySearchCourse` (find courses in the academy).
        4.  `AcademyGetStats` (retrieve academy stats).
        5.  `ProjectsSearchTask` (find project management tasks).
        6.  `ProjectsGetStats` (get project metrics).
        7.  `AnalyticsGetRadar` (fetch church radar/growth analytics).
        8.  `AnalyticsProactive` (run proactive analysis for risk/bottlenecks).

---

### 1.5 Frontend View Locations (Question 6)
*   **Persona Details View:**
    *   **File Path:** `/root/ccf/frontend/src/app/plataforma/crm/personas/[id]/page.tsx`
    *   **Behavior:** A Next.js App Router dynamic page that retrieves the persona's details using `apiFetch` (GET `/crm/personas/{id}`) and displays their profile, family, groups, and logs.
*   **Counseling Ticket Detail View:**
    *   **File Path:** `/root/ccf/frontend/src/app/plataforma/crm/counseling/[id]/page.tsx`
    *   **Behavior:** A Next.js App Router dynamic page that fetches the counseling details using `apiFetch` (GET `/crm/counseling/{id}`) and displays the notes, priority, status, and the counseling history checklist/history logs.

---

## 2. Logic Chain
1.  **Directory and Module Structure:** I began by listing `/root/ccf` and discovered modular Python model definitions (`models_*.py`) and a standard Next.js frontend setup under `frontend/src/app`.
2.  **Models & Schema:** Inspecting `/root/ccf/backend/models.py` pointed directly to files like `models_crm.py`, `models_evangelism.py`, `models_crm_pipeline.py` and `models_academy_core.py`. Searching for class names in those files revealed the exact lines and fields for `Persona`, the three attendance tables, `Donation`, `GrupoEvangelismo`, the counseling models (`CounselingTicket` and `CasoCRM`/`InteraccionCRM`), the communication tables, and `SpiritualMilestone`.
3.  **Tenancy:** Searching for occurrences of `sede_id` led to `backend/core/tenant.py`, which maps user authentication to tenant filters. Further grep searches for `_scoped` helper functions showed how entities lacking a direct `sede_id` (like `CounselingTicket`) are joined with `Persona` to enforce tenancy.
4.  **Counseling Detail:** Locating routing paths matching `counseling/` in `backend/api/crm/pastoral.py` revealed `GET /counseling/{ticket_id}`, which fetches the history of past sessions by filtering other `CounselingTicket` records matching the same `persona_id`.
5.  **OpenAI Integration:** Locating references to `openai` inside `backend/agents/orchestrator.py` and `backend/api/agents.py` showed how `AgentOrchestrator` is initialized and how OpenAI/OpenRouter keys are handled. Searching inside `backend/services/tool_registry.py` revealed the exact set of database query tools exposed to the agent.
6.  **Frontend Pages:** Searching the frontend workspace (`frontend/src/app`) for files containing `persona` and `counseling` names led directly to `/plataforma/crm/personas/[id]/page.tsx` and `/plataforma/crm/counseling/[id]/page.tsx`.

---

## 3. Caveats
*   The system has two parallel counseling/ticket architectures: `CounselingTicket` (pastoral-focused, defined in `models_crm.py`) and `CasoCRM` (generic CRM pipelines, defined in `models_crm_pipeline.py`). While `CounselingTicket` is used by the frontend view at `/plataforma/crm/counseling/[id]`, it is possible that generic counseling pipelines also make use of `CasoCRM` for general processing.
*   No database migrations or live DB tables were inspected during this read-only static analysis, though SQLAlchemy models provide a direct mapping to the schemas.

---

## 4. Conclusion
The CCF CRM system is a highly structured, tenant-isolated Python backend and React/Next.js frontend. All security and tenant scope resolution checks are explicitly coded in the API routing layer rather than implicitly handled via SQLAlchemy interceptors. The AI agent (`Optimus Brain`) relies on a robust tools registry to safely query database tables under tenant restrictions when answering pastoral questions.

---

## 5. Verification Method
To verify these conclusions:
1.  **Inspect files:**
    *   Open `/root/ccf/backend/models_crm.py` to verify schema fields for `Persona`, `Donation`, and `CounselingTicket`.
    *   Open `/root/ccf/backend/api/crm/pastoral.py` to examine the `get_counseling_detail` endpoint.
    *   Open `/root/ccf/frontend/src/app/plataforma/crm/counseling/[id]/page.tsx` to verify the frontend fetch URL.
2.  **Run backend unit tests:**
    *   Run pytest command in the workspace directory to verify model structure and API endpoint rules are working:
        ```bash
        pytest backend/tests/
        ```
