## 2026-07-30T19:04:09Z
You are a Worker subagent assigned to implement Milestone 2: R2 Newsletter / Email Marketing Module.
Your working directory is: /root/ccf/.agents/worker_m2_newsletter_module

Detailed Requirements:
1. Backend Models (`backend/models_cms.py`):
   - `CmsNewsletter`: id (UUID PK), site_id (FK cms_sites.id), name (str), subject (str), content_html (Text), status (Enum/str: 'draft'|'scheduled'|'sent'), scheduled_at (datetime tz-aware nullable), sent_at (datetime tz-aware nullable), recipient_count (int default 0), created_at, updated_at.
   - `CmsSubscriber`: id (UUID PK), site_id (FK cms_sites.id), email (str unique per site), name (str nullable), is_active (bool default True), subscribed_at (datetime tz-aware), unsubscribed_at (datetime tz-aware nullable), source (str default 'manual': 'form'|'manual'|'import').

2. Backend Endpoints (`backend/api/cms_v2/newsletter.py`):
   - Admin CRUD for newsletters under `/api/cms/v2/sites/{site_key}/newsletters`: GET list, POST create, GET /{id}, PATCH /{id}, DELETE /{id}.
   - Admin CRUD for subscribers under `/api/cms/v2/sites/{site_key}/subscribers`: GET list, POST create, GET /{id}, PATCH /{id}, DELETE /{id}, plus bulk import POST `/api/cms/v2/sites/{site_key}/subscribers/import` (CSV/json list of emails).
   - Public endpoint: `POST /api/cms/v2/public/subscribe` — public subscription endpoint.
   - Public endpoint: `POST /api/cms/v2/public/unsubscribe` (or GET/POST with email/token) — public unsubscription endpoint.
   - Send endpoint: `POST /api/cms/v2/sites/{site_key}/newsletters/{id}/send` — updates status to 'sent', sets sent_at timestamp, calculates active recipient_count, sends email dispatch (with SMTP or mock fallback).
   - Register router in `backend/api/cms_v2/__init__.py`.

3. Alembic Migration:
   - Create migration script in `alembic/canonical_versions/` for `cms_newsletters` and `cms_subscribers` tables with foreign keys and unique constraint on (site_id, email).

4. Frontend Page (`frontend/src/app/plataforma/cms/newsletter/page.tsx`):
   - Tabs: "Campañas" and "Suscriptores".
   - **Tab Campañas**:
     - Newsletter cards/table showing name, subject, status badge (draft=gray, scheduled=blue, sent=green), sent date, recipient count.
     - Create/Edit drawer or modal using `RichEditor` for `content_html`, subject input, scheduled date selector.
     - "Enviar ahora" action button with confirmation modal displaying subscriber count.
   - **Tab Suscriptores**:
     - Table displaying email, name, subscription date, active/inactive toggle switch.
     - "+ Agregar" modal for single manual subscriber.
     - "Importar CSV" button with file input parsing CSV lines to import subscribers in bulk.
     - Total active subscriber count header/badge.
   - Use `apiFetch` from `@/lib/http`, `useAuth` from `@/context/AuthContext`, `toast` from `sonner`.
   - Skeleton loaders, empty states, confirmation modals.

5. Navigation (`frontend/src/components/cms/CmsModuleNav.tsx`):
   - Add "Newsletter" navigation item linking to `/plataforma/cms/newsletter` with icon `Mail` from `lucide-react`.

6. Testing & Typecheck:
   - Run `cd /root/ccf/frontend && npm run typecheck` to ensure 0 TypeScript errors.
   - Write pytest tests for backend endpoints in `tests/test_cms_v2_newsletter.py` and vitest tests for frontend page.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Upon completion, write a detailed handoff report to `/root/ccf/.agents/worker_m2_newsletter_module/handoff.md`.
