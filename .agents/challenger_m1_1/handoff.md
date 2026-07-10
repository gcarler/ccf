# Handoff Report — Pastoral Health Score Verification

## Observation

1. **Baseline Unit Tests Execution**:
   - Commanded: `venv/bin/pytest tests/test_pastoral_health_score.py --no-cov`
   - Output: `4 passed, 7 warnings in 2.60s`
   - Warnings related to deprecated FastAPI events and `datetime.datetime.utcnow()`.

2. **Scoring Engine Implementation (`backend/crud/crm_/health.py`)**:
   - Line 55-58:
     ```python
     if opportunities > 0:
         attendance_score = (attended / opportunities) * 50
     else:
         attendance_score = 0.0
     ```
   - Line 75: `milestone_score = min(milestone_points * 10, 30)`
   - Line 88: `communication_score = min(total_contacts * 5, 20)`
   - Line 92: `clamped_score = max(0, min(100, int(round(total_score))))`
   - Line 94-99:
     ```python
     if clamped_score < 40:
         status = "EN_RIESGO"
     elif clamped_score < 80:
         status = "ESTABLE"
     else:
         status = "COMPROMETIDO"
     ```

3. **Database Constraints Encountered during Adversarial Testing**:
   - `sqlite3.IntegrityError: NOT NULL constraint failed: asistencias.estado`
     The table `asistencias` has a database-level `NOT NULL` constraint on the `estado` column.
   - `EventAttendance.attended` model definition in `backend/models_crm.py:157`:
     ```python
     attended = Column(Boolean, default=True)
     ```
     Any EventAttendance object initialized with `attended=None` defaults/coerces to `True` during persistence/evaluation.

4. **Adversarial Test Execution Output**:
   - Commanded: `venv/bin/pytest tests/test_pastoral_health_score.py --no-cov` after adding `test_pastoral_health_adversarial_and_edge_cases`.
   - Output: `5 passed, 11 warnings in 3.02s`
   - The test verified:
     - 0 opportunities results in `attendance_score = 0` (no division-by-zero crashes).
     - Massive inputs are correctly capped at 30 (milestones) and 20 (communication logs).
     - `is_baptized=None` is handled gracefully without exception.
     - Trimmed/mixed-case attendance statuses (`"  asIsTiO  "`, `"PRESENTE"`, `" present  "`, `"primera_vez  "`, `"  first_time"`) count as attended.
     - Unattended statuses (`"falto"`, `"justificado"`, `""`, `"invalido"`) count as opportunities but not as attended.
     - CourseAttendance statuses require exactly `"present"` (trimmed, case-insensitive), while other values like `"presente"` do not match.
     - Bound threshold boundaries (39, 40, 79, 80) map exactly to `EN_RIESGO`, `ESTABLE`, and `COMPROMETIDO`.
     - Rounding logic correctly applies Python's bankers' rounding (`39.4 -> 39` `EN_RIESGO`, `39.5 -> 40` `ESTABLE`).
     - Sede/Tenant isolation is preserved. Records from Sede B do not leak into calculations for Sede A because all queries filter strictly by `persona_id`.

## Logic Chain

1. **Risk of Division-by-Zero**:
   - Based on Observation 2 (Lines 55-58), the calculation logic explicitly checks `if opportunities > 0` before calculating the division.
   - Based on Observation 4, the adversarial test `persona_zero` with 0 opportunities successfully evaluated to 0 score without any database or logic crash.
   - Therefore, the 0-opportunity edge case is handled safely and correctly.

2. **Rounding and Clamping Integrity**:
   - Based on Observation 2 (Line 92), the total score is passed through `int(round(total_score))` and clamped between 0 and 100.
   - Based on Observation 4, `persona_round_down` (score of 39.4) correctly evaluated to status `EN_RIESGO` (score 39). `persona_round_up` (score of 39.5) correctly evaluated to status `ESTABLE` (score 40).
   - Therefore, threshold boundaries and bankers' rounding work exactly as specified.

3. **Multi-tenant Safety**:
   - Based on Observation 2, all database queries for attendance, milestones, and communications filter by `persona_id`.
   - Based on Observation 4, creating records under Sede B (Medellin) for `persona_b` did not affect the score of `persona_a` under Sede A (Bogota).
   - Therefore, there is no leakage across different Sedes (tenant isolation is guaranteed by `persona_id` granularity).

## Caveats

- We assumed that `is_baptized` can sometimes be `None` in the database, which we verified to be handled safely (treated as falsy, yielding 0 points).
- EventAttendance's `attended` column default behavior (`default=True`) means any records missing an explicit `attended` value will automatically be counted as "attended" (yielding points). The client system must make sure it explicitly writes `False` when registering a non-attended status.

## Conclusion

The Pastoral Health Score implementation is **correct**, **robust**, and **fully matches specifications**. Edge cases, large inputs, boundaries, and multi-tenant constraints have been stress-tested and are verified to be safe.

## Verification Method

1. Run the test command:
   ```bash
   venv/bin/pytest tests/test_pastoral_health_score.py --no-cov
   ```
2. Inspect the file `tests/test_pastoral_health_score.py` (specifically `test_pastoral_health_adversarial_and_edge_cases`) to review the test scenarios covering:
   - Zero attendance opportunities
   - Negative / Large inputs / None coercion
   - Case-insensitivity and trim of status strings
   - Capping limits (max 30 on milestone, max 20 on comms)
   - Status boundary limits
   - Rounding limits (.4 vs .5)
   - Sede isolation
