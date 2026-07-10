# Project: CCF CRM Super Pro

## Architecture
- **Backend**: FastAPI with SQLAlchemy models. Access control is handled by Auth v3. Tenant isolation via `sede_id`.
- **Frontend**: Next.js with `apiFetch` for API communications.
- **Database**: PostgreSQL (managed via Alembic).
- **Core Entities**:
  - `Persona` (in `personas` table): Canonical person model.
  - `SpiritualMilestone`, `CommunicationLog`: Models for the Omnichannel Inbox timeline.
  - `CounselingTicket`/`Case`: Model for pastoral counseling tickets.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | E2E Test Suite | Design E2E test infra and cases (Tiers 1-4) | None | DONE (c7cd5c31-82de-4e34-9435-dc26fbf96d98, outputs: tests/test_crm_super_pro.py) |
| 2 | Pastoral Health Score | Database migration and scoring calculations | None | DONE (8a3c398b-1012-4828-8bfa-4aa754c3d601) |
| 3 | AI Copilot for Counseling | `/api/crm/counseling/{id}/copilot-draft` endpoint and frontend button | M1 | DONE (8a3c398b-1012-4828-8bfa-4aa754c3d601) |
| 4 | Omnichannel Inbox | Frontend unified timeline rendering | M1 | DONE (5db48e85-cc03-4ae2-94c4-14cbf69923b9) |
| 5 | E2E & Hardening | Pass 100% E2E tests and perform white-box adversarial coverage | M1, M2, M3, M4 | DONE (5db48e85-cc03-4ae2-94c4-14cbf69923b9) |

## Interface Contracts
- **Pastoral Health Score**:
  - `health_score` (Integer, 0-100) and `health_status` (String: EN_RIESGO, ESTABLE, COMPROMETIDO) columns on `personas` table.
- **AI Copilot**:
  - GET/POST `/api/crm/counseling/{id}/copilot-draft` -> returns `{"draft": "..."}` or handles missing OpenAI API key gracefully.
- **Omnichannel Inbox**:
  - Unified timeline on `/plataforma/crm/personas/[id]` page.

## Code Layout
- `backend/models_crm.py`: Core CRM SQLAlchemy models (including `Persona`).
- `backend/api/crm/pastoral.py`: Counseling endpoints.
- `frontend/src/app/plataforma/crm/personas/[id]/page.tsx`: Persona detail/profile timeline.
- `frontend/src/app/plataforma/crm/counseling/[id]/page.tsx`: Counseling page with button.
