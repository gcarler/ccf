## 2026-07-10T06:06:48Z
You are the Worker to apply fixes and enhance the Pastoral Health Score implementation to pass E2E tests.
Your working directory is /root/ccf/.agents/worker_m1_fix.
Your tasks are:
1. Modify /root/ccf/backend/models_crm.py to add a donation_date Column of type Date (nullable=True, default=date.today) to the Donation model. Also modify the Persona model to have columns health_score and health_status if not already present.
2. Modify /root/ccf/backend/crud/crm_/health.py to:
   - Include Donation score contribution:
     - Count active Donation records (where deleted_at is null).
     - If donation_count == 0: donation_score = 0.
     - If donation_count == 1: donation_score = 50.
     - If donation_count > 1: 50 + min(40, (donation_count - 1) * 5).
     - Scale and cap the total score to 100: total_score = min(100, attendance_score + milestone_score + communication_score + donation_score).
   - Update calculate_pastoral_health to check CommunicationLog content:
     - If a CommunicationLog has content containing "attend", "asist", "session", "class", "culto", or "grupo" (case-insensitive), increment both total_opportunities and total_attended by 1.
   - Automatically set persona.is_baptized = True (and commit it) if the persona has any active SpiritualMilestone of type containing "bapt" or "baut" (case-insensitive).
   - In update_pastoral_health, compare the new health_status with the previous health_status. If they differ (or previous was None), create a new SpiritualMilestone for the persona:
     - type = f"Health Status Change to {new_status}"
     - event_date = date.today()
     - notes = f"Health score updated to {new_score}"
   - Define aliases:
     - calculate_pastoral_health_score = calculate_pastoral_health
     - calculate_health_score = calculate_pastoral_health
3. Export these functions (calculate_pastoral_health, calculate_pastoral_health_score, calculate_health_score, update_pastoral_health) in:
   - backend/crud/crm_/__init__.py
   - backend/crud/crm.py
4. Create backend/services/pastoral_health.py and define/export these same functions there.
5. Create a new Alembic migration script under /root/ccf/alembic/canonical_versions/ to add donation_date column to the donations table (if needed, set down_revision to f89b968a23a9). Run the migrations using venv/bin/alembic upgrade head.
6. Run the unit tests and the E2E tests:
   - pytest tests/test_pastoral_health_score.py tests/test_pastoral_health_score_adversarial.py
   - pytest --no-cov tests/test_crm_super_pro.py -k "test_health_score"
7. Make sure all health score related tests pass cleanly.
8. Document your findings in /root/ccf/.agents/worker_m1_fix/handoff.md.
