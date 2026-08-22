## 2026-07-31T00:02:20Z
<USER_REQUEST>
You are a Worker subagent assigned to implement Milestone 4: R4 Blog Post Comments.
Your working directory is: /root/ccf/.agents/worker_m4_post_comments

Detailed Requirements:
1. Backend Model (`backend/models_cms.py`):
   - `CmsPostComment`: id (UUID PK), post_id (FK cms_posts.id), parent_id (UUID FK cms_post_comments.id nullable), author_name (str), author_email (str), content (Text), status (str default 'pending': 'pending'|'approved'|'spam'|'deleted'), created_at, updated_at.

2. Backend Endpoints (`backend/api/cms_v2/post_comments.py`):
   - Public endpoint: `POST /api/cms/v2/public/posts/{post_id}/comments` (creates comment with status='pending').
   - Public endpoint: `GET /api/cms/v2/public/posts/{post_id}/comments` (returns approved comments with 1-level nested replies).
   - Admin endpoint: `GET /api/cms/v2/sites/{site_key}/post-comments` (lists comments with optional status filter, pagination, and pending count metadata).
   - Admin endpoint: `PATCH /api/cms/v2/sites/{site_key}/post-comments/{id}` (updates status: approve, mark spam, delete).
   - Register router in `backend/api/cms_v2/__init__.py`.

3. Alembic Migration:
   - Create migration script in `alembic/canonical_versions/` for `cms_post_comments` table with foreign keys and indexes.

4. Frontend Admin Page (`frontend/src/app/plataforma/cms/comments/page.tsx`):
   - Tabs: "Pendientes", "Aprobados", "Spam".
   - Pending moderation count badge on "Pendientes" tab.
   - Comment items displaying author, email, post reference, content excerpt, submission date.
   - Action buttons: Aprobar (check), Marcar Spam (slash/shield), Eliminar (trash).
   - Skeletons, empty states, sonner toasts.

5. Navigation (`frontend/src/components/cms/CmsModuleNav.tsx`):
   - Add "Comentarios" navigation item linking to `/plataforma/cms/comments` with icon `MessageCircle` from `lucide-react` and pending comments badge count.

6. Frontend Public Component (`frontend/src/components/public/cms/PostComments.tsx`):
   - Displays approved comments and nested replies for a post.
   - Form to submit new comment (name, email, content textarea).
   - "Responder" button per comment triggering inline reply form (setting `parent_id`).
   - Comment count header badge.

7. Testing & Typecheck:
   - Run `cd /root/ccf/frontend && npm run typecheck` to ensure 0 TypeScript errors.
   - Write pytest backend tests `tests/test_cms_v2_post_comments.py` and frontend vitest tests for `PostComments.tsx` and admin comments page.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Upon completion, write a detailed handoff report to `/root/ccf/.agents/worker_m4_post_comments/handoff.md`.
</USER_REQUEST>
