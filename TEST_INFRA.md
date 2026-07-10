# CCF Test Infrastructure (TEST_INFRA)

This document describes the test runner, architecture, and testing methodology implemented for the CCF CRM "Super Pro" evolution.

## 1. Test Runner & Framework
We use **pytest** as the primary test runner. The test infrastructure leverages direct async-to-sync testing mechanisms to match sandbox constraints and prevent execution hangs.

### Key Libraries:
- **pytest**: Test engine and test discovery.
- **SQLAlchemy**: ORM database session management.
- **httpx**: ASGI-compliant client (`ASGITransport`) to execute API tests synchronously.

---

## 2. Test Structure & Fixtures
All database and client setups are managed via standard pytest fixtures defined in `tests/conftest.py`:

- `db_session`: Manages transaction rollback and schema initialization (`Base.metadata.create_all`) for each test run, supporting SQLite by default and PostgreSQL in CI/CD.
- `client`: A synchronous ASGI test client (`LocalASGITestClient`) that drives the FastAPI application directly without starting a background thread.
- `seed_admin`: Idempotently sets up a platform administrator, their `Persona` profile, and their default `Sede` (campus).
- `auth_headers`: Authenticates users via `/api/v3/auth/login` to obtain access tokens for API requests.

---

## 3. The 4-Tier E2E Testing Methodology
Our E2E test suite in `tests/test_crm_super_pro.py` comprises exactly **38 tests** divided into four logical tiers:

### Tier 1: Feature Coverage (15 tests)
- **Pastoral Health Score**: 5 tests verifying default values, calculations for high/medium/no activity, and database persistence.
- **AI Copilot**: 5 tests checking endpoint behavior, empty case notes, missing API keys, OpenAI errors, and payload structure.
- **Omnichannel Inbox**: 5 tests asserting unified display of WhatsApp, SMS, Email, and SpiritualMilestone events, sorted chronologically descending.

### Tier 2: Boundary & Corner Cases (15 tests)
- **Pastoral Health Score Boundaries**: 5 tests verifying zero/100 score limits, null data handling, inactive personas, and overflow prevention.
- **AI Copilot Boundaries**: 5 tests verifying invalid ticket IDs, unauthorized access, context window truncation, unicode text, and cross-sede access blocks.
- **Omnichannel Inbox Boundaries**: 5 tests checking empty timelines, duplicate timestamps, cross-sede timeline leakage, long custom milestones, and HTML/XSS injection.

### Tier 3: Cross-Feature Combinations (3 tests)
- Health status change events logged directly to the timeline.
- AI Copilot leveraging unified timeline messages as contextual prompts.
- Spiritual Milestones automatically triggering health score recalculations.

### Tier 4: Real-world Application Scenarios (5 tests)
- **Convert Journey**: Entry -> Group Attendance -> Baptism -> Counseling -> Scoring.
- **Member Recovery**: Active -> Disengagement -> Status Change -> AI outreach -> Re-engagement -> Score Recovery.
- **Sede Isolation**: End-to-end data isolation across different campus tenants.
- **Rate Limiting & Concurrency**: Stress-testing rapid endpoint requests and database transaction safety.
- **Holistic Campaign**: Multi-channel touchpoints -> Milestone -> Calculation -> Unified Timeline.

---

## 4. External Integrations
For AI-related functionality, we mock the **OpenAI** library at the module level using `unittest.mock.patch` to simulate completions. If the `openai` package is missing in the execution environment, our test suite dynamically mocks it via `sys.modules["openai"]` to prevent `ModuleNotFoundError` during test collection.
