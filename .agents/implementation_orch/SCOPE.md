# Scope: Implementation Track for CRM Super Pro

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
| 1 | Pastoral Health Score | Migration, schema updates, and scoring engine calculations | None | DONE |
| 2 | AI Copilot for Counseling | FastAPI GET/POST `/api/crm/counseling/{id}/copilot-draft` endpoint, OpenAI integration, frontend button | M1 | DONE |
| 3 | Omnichannel Inbox | Frontend unified timeline rendering on `/plataforma/crm/personas/[id]` page | M1 | DONE |
| 4 | E2E Integration & Hardening | Pass 100% E2E tests, white-box adversarial coverage | M1, M2, M3 | DONE |

## Interface Contracts
### Pastoral Health Score
- **Table**: `personas`
- **Columns**:
  - `health_score`: Integer (0-100)
  - `health_status`: String (EN_RIESGO, ESTABLE, COMPROMETIDO)
- **Scoring Engine**:
  - Calculates score based on attendance, spiritual milestones, and communication logs.
  - Status boundaries:
    - `EN_RIESGO`: Score < 40
    - `ESTABLE`: 40 <= Score < 80
    - `COMPROMETIDO`: Score >= 80

### AI Copilot for Counseling
- **Endpoint**: GET/POST `/api/crm/counseling/{id}/copilot-draft`
- **Request/Response**:
  - GET/POST returns JSON `{"draft": "..."}` or handles missing OpenAI API key gracefully.
- **Frontend integration**:
  - Button on counseling detail page `/plataforma/crm/counseling/[id]/page.tsx` to fetch and insert the draft.

### Omnichannel Inbox
- **Frontend component**:
  - Unified timeline on `/plataforma/crm/personas/[id]` page.
  - Shows SpiritualMilestones and CommunicationLogs in reverse chronological order.

## Code Layout
- `backend/models_crm.py`: Core CRM SQLAlchemy models (including `Persona`).
- `backend/api/crm/pastoral.py`: Counseling endpoints.
- `frontend/src/app/plataforma/crm/personas/[id]/page.tsx`: Persona detail/profile timeline.
- `frontend/src/app/plataforma/crm/counseling/[id]/page.tsx`: Counseling page with button.
