# FARO Public Pages to CCF Platform/CRM Integration Plan

**Created:** 2026-05-24
**Scope:** Close integration gaps between FARO public-facing pages and the CCF backend (FastAPI + SQLAlchemy) / CRM

---

## Current State

| Flow | Endpoint | Status | What Happens |
|------|----------|--------|-------------|
| "Conocer a Jesus" form | `POST /api/public/contact` | Working | Creates Member + ConsolidationCase + PrayerRequest |
| QR Registration | `POST /api/public/register` | Working | Creates Member + EventAttendance |
| Prayer requests | `POST /api/crm/prayer-requests/public` | Working | Creates PrayerRequest |
| Newsletter subscription | `POST /api/public/newsletter/subscribe` | Partial | Only saves to NewsletterSubscription table |
| Course enrollment | `POST /api/public/courses/{id}/enroll` | Missing | Endpoint does not exist |
| Course "add to cart" (books) | N/A | Missing | Just shows toast, no API call |

---

## Architecture Principles

1. **Every public contact becomes a CRM-visible record** -- either a `Member` (if we have enough identity), a `ConsolidationPipeline` lead, or both.
2. **Source tracking on every record** -- `source`, `landing_page`, and optional `campaign` fields must be populated.
3. **Reuse existing patterns** -- the `POST /api/public/contact` endpoint already demonstrates the pattern: find-or-create Member, attach ConsolidationCase, create PrayerRequest if notes provided.
4. **No dual-write without dedup** -- when creating a Member from newsletter email, check for existing by email first.
5. **Frontend changes are additive** -- no existing working flows should be broken.

---

## Phase 1: Quick Wins (Low Effort, High Impact)

### Task 1.1: Newsletter Subscriber --> CRM Lead

**Files to modify:**
- `/root/ccf/backend/api/public.py` -- modify `public_newsletter_subscribe` endpoint
- `/root/ccf/backend/schemas/cms.py` -- extend `NewsletterSubscriptionCreate` with optional tracking fields

**What the change does:**

When a user subscribes to the newsletter via `POST /api/public/newsletter/subscribe`, the endpoint currently only writes to `NewsletterSubscription`. After this change it will also:

1. Check if a `Member` already exists with that email. If not, create one with `church_role="Visitante"`, `spiritual_status="Nuevo"`.
2. Create a `ConsolidationPipeline` lead with `source="newsletter-web"`, `stage="new"`, linking to the Member.
3. Accept optional tracking fields: `landing_page` (string), `campaign` (string), `first_name` (string), `last_name` (string). These are optional to keep the current frontend form working without changes.

**Schema change (`NewsletterSubscriptionCreate`):**
```python
class NewsletterSubscriptionCreate(BaseModel):
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    landing_page: Optional[str] = None
    campaign: Optional[str] = None
```

**Endpoint logic (pseudocode):**
```
1. Save NewsletterSubscription (existing behavior, dedup by email)
2. Find or create Member by email
3. Create ConsolidationPipeline lead:
   - first_name/last_name from payload or extracted from email local-part
   - source="newsletter-web"
   - stage="new"
   - notes: f"Newsletter subscriber from {landing_page}" if landing_page
4. Return existing response (NewsletterSubscriptionRead)
```

**Complexity:** Low
**Dependencies:** None
**Risk:** Low -- the endpoint already returns `NewsletterSubscriptionRead`; the CRM lead creation is a side-effect that does not change the response contract.

---

### Task 1.2: Add Source Tracking to Existing Public Endpoints

**Files to modify:**
- `/root/ccf/backend/api/public.py` -- `public_register` and `public_contact` endpoints
- `/root/ccf/backend/schemas/legacy.py` -- `PublicRegistrationCreate` schema

**What the change does:**

Add optional `source`, `landing_page`, and `campaign` fields to the existing public endpoints so that the CRM team can filter and segment contacts by their origin.

1. **`PublicRegistrationCreate` schema**: Add `source: Optional[str]`, `landing_page: Optional[str]`, `campaign: Optional[str]`.
2. **`public_register` endpoint**: Pass `source` to `EventAttendance.source` field (already exists on the model).
3. **`public_contact` endpoint**: Already has a `source` field in `PublicContactCreate`; ensure it flows through to `ConsolidationCase.source` (it already does). Add optional `landing_page` and `campaign` tracking.

**Complexity:** Low
**Dependencies:** None
**Risk:** Low -- all new fields are optional with defaults; existing callers are unaffected.

---

### Task 1.3: Frontend -- Pass Source Context to Newsletter Subscribe

**Files to modify:**
- `/root/ccf/frontend/src/app/(public)/page.tsx` -- `handleNewsletterSubmit`
- `/root/ccf/frontend/src/app/(public)/cursos/page.tsx` -- `handleNewsletterSubmit`
- `/root/ccf/frontend/src/app/(public)/boletin/page.tsx` -- newsletter submit handler

**What the change does:**

Each newsletter form currently sends only `{ email }`. Update to send `{ email, landing_page: window.location.pathname }` so the backend can track which page the subscriber came from.

**Complexity:** Low
**Dependencies:** Task 1.1 (schema must accept the new fields)
**Risk:** Low -- backend will accept these fields as optional, so even if the frontend sends them, nothing breaks.

---

## Phase 2: Medium Complexity

### Task 2.1: Create Course Enrollment Public Endpoint

**Files to modify:**
- `/root/ccf/backend/api/public.py` -- add new `public_enroll_course` endpoint
- `/root/ccf/backend/schemas/academy.py` -- add `PublicCourseEnrollCreate` schema
- `/root/ccf/backend/api/academy.py` -- optionally add CRM visibility query (see Task 2.3)

**What the change does:**

Creates `POST /api/public/courses/{course_id}/enroll` that:

1. Validates the course exists and is published.
2. **If user is authenticated** (has auth token): looks up their `User` record, creates an `Enrollment` for them.
3. **If user is NOT authenticated** (anonymous): creates a `Member` from the provided contact info (name, email, phone), creates a `User` linked to that Member, then creates the `Enrollment`.
4. Creates a `ConsolidationCase` with `source="academy-enrollment"` so the CRM team can see and follow up with academy participants.
5. Accepts optional `source`, `landing_page`, `campaign` tracking fields.

**New schema (`PublicCourseEnrollCreate`):**
```python
class PublicCourseEnrollCreate(BaseModel):
    # Authenticated users: user_id is populated from token
    # Anonymous users: must provide at least email
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    source: Optional[str] = "academy-web"
    landing_page: Optional[str] = None
    campaign: Optional[str] = None
```

**Endpoint behavior:**
- If the caller is authenticated (via `Depends(get_current_user)` optional dependency), use their user_id directly.
- If anonymous, require at least `email` in the payload, create Member + User + Enrollment.
- Dedup: if an enrollment already exists for this user+course, return it (idempotent).
- Side-effect: create `ConsolidationCase` and optionally a `ConsolidationPipeline` lead.

**Complexity:** Medium
**Dependencies:** None (standalone endpoint)
**Risk:** Medium -- this touches the academy enrollment flow. Must handle the authenticated vs anonymous cases carefully.

---

### Task 2.2: Frontend -- Wire Course Enrollment Button to API

**Files to modify:**
- `/root/ccf/frontend/src/app/(public)/cursos/page.tsx` -- course card enrollment button
- `/root/ccf/frontend/src/app/(public)/cursos/[id]/page.tsx` or equivalent course detail page -- enroll button
- `/root/ccf/frontend/src/lib/http.ts` -- verify `apiFetch` handles the new endpoint

**What the change does:**

Replace the current "Ver Curso" link (or add an "Inscribirse" button) that calls `POST /api/public/courses/{id}/enroll`. For anonymous users, show a simple modal form collecting name, email, and phone before submitting. For authenticated users, enroll directly with a toast confirmation.

**Complexity:** Medium
**Dependencies:** Task 2.1 (endpoint must exist)
**Risk:** Medium -- UI changes require testing the authenticated and anonymous flows.

---

### Task 2.3: CRM Visibility for Course Enrollments

**Files to modify:**
- `/root/ccf/backend/api/crm/pastoral.py` -- add endpoint to list academy leads, or extend existing pipeline query
- `/root/ccf/backend/crud/crm.py` -- add helper to query Members with enrollments

**What the change does:**

The CRM team needs to see who enrolled in courses. Two options:

**Option A (preferred, lower effort):** Course enrollments already create `ConsolidationCase` records with `source="academy-enrollment"`. The CRM team can filter the existing pipeline/consolidation views by source. No new endpoint needed -- just document this for the CRM team.

**Option B (if a dedicated view is needed):** Add `GET /api/crm/academy/enrollments` that returns enrollments with member info, filterable by course and date range. This would be a read-only endpoint for CRM users.

**Recommendation:** Start with Option A. If the CRM team needs a dedicated view, add Option B later.

**Complexity:** Low (Option A) / Medium (Option B)
**Dependencies:** Task 2.1
**Risk:** Low

---

### Task 2.4: Frontend -- Books "Add to Cart" --> Wishlist API

**Files to modify:**
- `/root/ccf/frontend/src/app/(public)/cursos/page.tsx` -- `handleAddToCart` function
- `/root/ccf/backend/api/public.py` -- add `POST /api/public/wishlist` endpoint (or reuse existing)

**What the change does:**

Currently the "add to cart" button for books just shows a toast and stores the title in local state. This change:

1. Creates a simple `POST /api/public/wishlist` endpoint that records a wishlist interest: `{ book_title, email, source="books-web" }`.
2. Creates a `ConsolidationPipeline` lead with `source="books-web"` so the CRM/sales team can follow up.
3. Frontend calls this API when the user clicks "add to cart", passing the book title and (if available) the user's email from a prompt or session.

**Alternative (lower effort):** If a full wishlist table is overkill, the endpoint can directly create a `ConsolidationPipeline` lead with `notes` containing the book title and skip a dedicated table. This is the recommended approach since the goal is CRM visibility, not e-commerce.

**Complexity:** Low-Medium
**Dependencies:** None
**Risk:** Low

---

## Phase 3: Full Integration

### Task 3.1: Unified Contact Tracking Middleware

**Files to modify:**
- `/root/ccf/backend/api/public.py` -- add a shared helper/service for contact tracking
- New file: `/root/ccf/backend/services/public_contact_tracking.py`

**What the change does:**

Extract the repeated pattern of "find-or-create Member, create ConsolidationCase/Pipeline lead, track source" into a reusable service that all public endpoints can use. This prevents code duplication and ensures consistent behavior across all public contact points.

**Service interface:**
```python
class PublicContactTracker:
    def record_contact(
        self,
        db: Session,
        email: Optional[str],
        phone: Optional[str],
        first_name: Optional[str],
        last_name: Optional[str],
        source: str,
        landing_page: Optional[str] = None,
        campaign: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Member:
        """Find or create Member, attach ConsolidationCase, return Member."""
```

**Complexity:** Medium
**Dependencies:** Tasks 1.1, 2.1, 2.4 (need at least 2 callers to justify extraction)
**Risk:** Low -- refactoring existing inline code into a service.

---

### Task 3.2: Newsletter Subscriber CRM Dashboard View

**Files to modify:**
- `/root/ccf/backend/api/crm/pastoral.py` -- add `GET /api/crm/leads/newsletter` endpoint
- `/root/ccf/frontend/src/app/(crm)/...` -- CRM page or filter to view newsletter leads

**What the change does:**

After Task 1.1, newsletter subscribers become `ConsolidationPipeline` leads with `source="newsletter-web"`. This task adds a dedicated CRM view so the pastoral/CRM team can:

1. See all newsletter subscribers in a list view.
2. Filter by date range, landing page, and campaign.
3. Convert them to consolidation cases (assign a pastor/leader).
4. Export the list (CSV).

This can be implemented as a filter on the existing pipeline view (`GET /api/crm/consolidation/pipeline?source=newsletter-web`) or as a dedicated endpoint.

**Complexity:** Medium
**Dependencies:** Task 1.1
**Risk:** Low

---

### Task 3.3: Campaign Attribution System

**Files to modify:**
- `/root/ccf/backend/models_crm.py` -- optionally add `landing_page` and `campaign` columns to `ConsolidationPipeline` (if not already present)
- `/root/ccf/backend/api/public.py` -- all public endpoints
- `/root/ccf/frontend/` -- all public pages that make API calls

**What the change does:**

Currently `ConsolidationPipeline` has a `source` field but no dedicated `landing_page` or `campaign` columns. This task adds proper UTM-style tracking:

1. Add `landing_page: Optional[String(500)]` and `campaign: Optional[String(200)]` to `ConsolidationPipeline` model.
2. Create a database migration (Alembic).
3. Pass these fields from frontend (read from URL params `?utm_source=...&utm_campaign=...` or `window.location.pathname`).
4. CRM can filter and report on which campaigns drive the most contacts.

**Note:** `ConsolidationPipeline` already has `source` and `notes` fields. If the team decides `notes` is sufficient for landing page info, this task can be deferred or skipped.

**Complexity:** Medium
**Dependencies:** Database migration infrastructure must be available
**Risk:** Medium -- schema migration requires deployment coordination.

---

### Task 3.4: Academy-to-CRM Automated Follow-up Tasks

**Files to modify:**
- `/root/ccf/backend/api/public.py` -- course enrollment endpoint
- `/root/ccf/backend/crud/crm.py` -- helper to auto-create follow-up tasks

**What the change does:**

When a course enrollment is created (Task 2.1), automatically:

1. Create a `ConsolidationFollowUpTask` for the CRM team: "Follow up with new academy student: {name} enrolled in {course}".
2. Optionally send a welcome email via the messaging gateway (if the user provided an email).
3. Log the action in the `CommunicationLog` table.

This closes the loop so that every academy enrollment triggers a pastoral follow-up, not just a database record.

**Complexity:** Medium
**Dependencies:** Task 2.1, Task 3.1
**Risk:** Low

---

## Priority Order & Execution Sequence

```
Phase 1 (Day 1-2):
  1.1 Newsletter --> CRM Lead          [2-3 hours]
  1.2 Source tracking on endpoints     [1-2 hours]
  1.3 Frontend source context          [30 min]

Phase 2 (Day 3-5):
  2.1 Course enrollment endpoint       [4-6 hours]
  2.2 Frontend enrollment wiring       [3-4 hours]
  2.3 CRM visibility (Option A)        [1 hour -- documentation only]
  2.4 Books wishlist API               [2-3 hours]

Phase 3 (Day 6-8):
  3.1 Contact tracking service         [3-4 hours]
  3.2 Newsletter CRM dashboard view    [3-4 hours]
  3.3 Campaign attribution (optional)  [3-5 hours + migration]
  3.4 Auto follow-up tasks             [2-3 hours]
```

---

## File Change Summary

| File | Phase | Tasks |
|------|-------|-------|
| `backend/api/public.py` | 1, 2, 3 | 1.1, 1.2, 2.1, 2.4, 3.1 |
| `backend/schemas/cms.py` | 1 | 1.1 |
| `backend/schemas/legacy.py` | 1 | 1.2 |
| `backend/schemas/academy.py` | 2 | 2.1 |
| `backend/api/crm/pastoral.py` | 2, 3 | 2.3, 3.2 |
| `backend/crud/crm.py` | 2, 3 | 2.3, 3.4 |
| `backend/models_crm.py` | 3 | 3.3 (optional migration) |
| `backend/services/public_contact_tracking.py` | 3 | 3.1 (new file) |
| `frontend/src/app/(public)/page.tsx` | 1 | 1.3 |
| `frontend/src/app/(public)/cursos/page.tsx` | 1, 2 | 1.3, 2.2, 2.4 |
| `frontend/src/app/(public)/boletin/page.tsx` | 1 | 1.3 |

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Duplicate Members from newsletter + other flows | Dedup by email in every public endpoint (already pattern in `public_register`) |
| Anonymous enrollment abuse (spam) | Add rate limiting or simple CAPTCHA on the enrollment endpoint |
| CRM team overwhelmed by newsletter leads | Start with `stage="new"` in pipeline; team can triage at their pace |
| Book wishlist creates too many leads | Only create a lead if the user provides an email (not just a click) |
| Schema migration downtime (Task 3.3) | Use Alembic online migration; add columns as nullable with defaults |
