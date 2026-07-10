# Handoff Report — Pastoral Health Score Empirical Verification

## 1. Observation
- **Original test file:** `/root/ccf/tests/test_pastoral_health_score.py`
- **Implementation file:** `/root/ccf/backend/crud/crm_/health.py`
- **New adversarial tests file:** `/root/ccf/tests/test_pastoral_health_score_adversarial.py`
- **Verbatim Error:**
  When executing the test suite with `venv/bin/pytest tests/test_pastoral_health_score.py --no-cov`, the test `test_pastoral_health_adversarial_and_edge_cases` failed:
  ```
  DEBUG: Asistencia opps count = 9, attended = 5
  DEBUG: EventAttendance opps count = 3, attended = 2
  DEBUG: CourseAttendance opps count = 4, attended = 2
  DEBUG: score = 28, status = EN_RIESGO
  >       assert score == 25
  E       assert 28 == 25
  tests/test_pastoral_health_score.py:476: AssertionError
  ```
- **Schema configuration (from `/root/ccf/backend/models_crm.py`):**
  ```python
  class EventAttendance(Base):
      ...
      attended = Column(Boolean, default=True)
  ```
- **Test execution commands:**
  - Running all passing tests and new adversarial tests:
    `venv/bin/pytest tests/test_pastoral_health_score.py -k "not test_pastoral_health_adversarial_and_edge_cases" tests/test_pastoral_health_score_adversarial.py --no-cov`
    Result: `9 passed, 1 deselected, 7 warnings in 4.93s`

## 2. Logic Chain
1. In `backend/models_crm.py`, the `EventAttendance` table defines `attended` as `Column(Boolean, default=True)`.
2. When creating an `EventAttendance` object with `attended=None` (such as `evt_n` in `test_pastoral_health_score.py:438`), SQLAlchemy's python-side insertion logic treats `None` as the default unassigned state for columns with default values, omitting the column from the generated INSERT query. The database subsequently applies the default value of `True`.
3. Thus, `evt_n.attended` is stored and queried as `True`.
4. In `backend/crud/crm_/health.py`, `attended_events_count` evaluates `e.attended is True` for each opportunity. Since `evt_n.attended` is `True`, it is counted as an attended event.
5. In the test case `test_pastoral_health_adversarial_and_edge_cases`, 3 events are inserted: `evt_t` (attended=True), `evt_f` (attended=False), and `evt_n` (attended=None).
6. The scoring logic sees 2 attended events out of 3 total opportunities. Coupled with 5/9 Asistencias and 2/4 CourseAttendances, this yields a total attendance of 8/16.
7. Total attendance score is `(8 / 16) * 50 = 25.0`.
8. However, due to `evt_n` defaulting to `True`, the actual queried state sees 9 attended events out of 16 opportunities. This results in an attendance score of `(9 / 16) * 50 = 28.125`, which rounds to `28` and fails the assertion `assert score == 25`.
9. The implementation of `calculate_pastoral_health` itself is correct and behaves as designed (isolation, capping, boundaries work). The test case in `tests/test_pastoral_health_score.py` is bugged because it makes an incorrect assumption about default constraint behavior.

## 3. Caveats
- The test suite requires the `--no-cov` flag to run successfully, as the global project configuration has a 70% coverage requirement which is not met when running individual test files.

## 4. Conclusion
- The core scoring logic, boundaries, capping, status normalizations, and multi-tenant isolation are implemented correctly.
- The new adversarial tests successfully passed, demonstrating correct behavior across all edge cases (zero opportunities, banker's rounding, extreme inputs, and multi-tenant safety).
- There is a bug in the peer agent's newly added test `test_pastoral_health_adversarial_and_edge_cases` in `/root/ccf/tests/test_pastoral_health_score.py` where it asserts `score == 25` instead of `28` because of SQLAlchemy's `default=True` behavior on `EventAttendance.attended`. This test must be corrected to either use `attended=False` or assert the correct score of `28`.

## 5. Verification Method
To verify the findings and run the tests:
1. Run only the passing and new adversarial tests:
   ```bash
   venv/bin/pytest tests/test_pastoral_health_score.py -k "not test_pastoral_health_adversarial_and_edge_cases" tests/test_pastoral_health_score_adversarial.py --no-cov
   ```
2. Observe the bug in the original test file by running:
   ```bash
   venv/bin/pytest tests/test_pastoral_health_score.py::test_pastoral_health_adversarial_and_edge_cases --no-cov
   ```
