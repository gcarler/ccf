# Plan: CRM Super Pro Integration

## Step 1: Initial Exploration
- **Goal**: Explore codebase to map out:
  1. Persona activity relations (attendance, donations, groups) to calculate Health Score.
  2. Counseling ticket data model, history structure, and current routes.
  3. Timeline resources (CommunicationLog, SpiritualMilestone, etc.).
- **Verifiable by**: Explorer report.

## Step 2: E2E Test Suite Design
- **Goal**: Design and implement the opaque-box test runner and test cases (Tiers 1-4).
- **Verifiable by**: `TEST_READY.md` containing test list and running the runner on baseline.

## Step 3: Implement Pastoral Health Score (Milestone 2)
- **Goal**: Database migration, logic to calculate score (0-100) and status (EN_RIESGO, ESTABLE, COMPROMETIDO) on person activity, updating `personas` table.
- **Verifiable by**: Migrations applied and tests passing.

## Step 4: Implement AI Copilot for Counseling (Milestone 3)
- **Goal**: Endpoint `/api/crm/counseling/{id}/copilot-draft` calling OpenAI API using standard library, backend fallback, frontend button in counseling page.
- **Verifiable by**: Endpoint test cases and UI verification.

## Step 5: Implement Omnichannel Inbox (Milestone 4)
- **Goal**: Unified timeline showing messages (WhatsApp, SMS, Email) and milestones on the person profile page.
- **Verifiable by**: UI renders correctly with multiple message logs.

## Step 6: E2E Testing & Hardening (Milestone 5)
- **Goal**: Run E2E tests, find white-box coverage gaps, write adversarial tests (Tier 5), fix any issues, and audit.
- **Verifiable by**: 100% test pass and clean Forensic Audit.
