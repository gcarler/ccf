## 2026-07-30T19:00:13Z
You are a Worker subagent assigned to implement Milestone 1: R1 Contact Forms Module.
Your working directory is: /root/ccf/.agents/worker_m1_forms_module

Detailed Requirements:
1. Backend Models (`backend/models_cms.py`):
   - `CmsForm`: id (UUID PK), site_id (FK cms_sites.id), name (str), description (str nullable), fields (JSON: list of {id, label, type: 'text'|'email'|'phone'|'textarea'|'select'|'checkbox', required: bool, options: list nullable}), submit_button_text (str default 'Enviar'), success_message (str default '¡Gracias por tu mensaje!'), notify_emails (JSON list of emails), is_active (bool default True), created_at, updated_at.
   - `CmsFormSubmission`: id (UUID PK), form_id (FK cms_forms.id), data (JSON), submitted_at, ip_address (str nullable).

2. Backend Endpoints (`backend/api/cms_v2/forms.py`):
   - CRUD under `/api/cms/v2/sites/{site_key}/forms`: GET list, POST create, GET /{form_id}, PATCH /{form_id}, DELETE /{form_id}.
   - Public endpoint: `POST /api/cms/v2/public/forms/{form_id}/submit` — creates CmsFormSubmission, sends notification email if notify_emails configured (or logs/mocks if SMTP not configured).
   - Submissions endpoint: `GET /api/cms/v2/sites/{site_key}/forms/{form_id}/submissions` (paginated submissions list with total count).
   - Register the router in `backend/api/cms_v2/__init__.py` or main API router so routes are active under `/api/cms/v2/`.

3. Alembic Migration:
   - Create migration script in `alembic/canonical_versions/` for `cms_forms` and `cms_form_submissions` tables with proper foreign keys and indexes.

4. Frontend Page (`frontend/src/app/plataforma/cms/forms/page.tsx`):
   - Tabs / View Modes: "Formularios" (grid/cards of forms with submission counts and active status toggle) and "Respuestas" (paginated table of form submissions).
   - Form Builder / Modal / Drawer:
     - Name & description fields.
     - Field builder: "+ Agregar campo" with type selector (text, email, phone, textarea, select, checkbox), label, placeholder, required toggle, and option list for select.
     - Submit button text, success message, notification email chips.
   - Use `apiFetch` from `@/lib/http`, `useAuth` from `@/context/AuthContext`, `toast` from `sonner`.
   - Skeletons for loading states, empty states when 0 forms/submissions exist, delete confirmation modals.

5. Navigation (`frontend/src/components/cms/CmsModuleNav.tsx`):
   - Add "Formularios" navigation item linking to `/plataforma/cms/forms` with icon `ClipboardList` from `lucide-react`.

6. Testing & Typecheck:
   - Run `cd /root/ccf/frontend && npm run typecheck` or `npx tsc --noEmit` to ensure 0 TypeScript errors.
   - Write unit/integration tests for backend endpoints and frontend forms page.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Upon completion, write a detailed handoff report to `/root/ccf/.agents/worker_m1_forms_module/handoff.md`.
