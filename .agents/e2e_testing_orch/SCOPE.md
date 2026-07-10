# Scope: E2E Testing Track

## Architecture
- Target features of "CRM Super Pro":
  - **R1: Pastoral Health Score**: Motor de análisis/cálculo, updates `health_score` and `health_status` columns on `Persona` model.
  - **R2: AI Copilot for Counseling**: Endpoint `/api/crm/counseling/{id}/copilot-draft` calling OpenAI standard client with missing key handling.
  - **R3: Omnichannel Inbox**: Unify email, SMS, WhatsApp (`CommunicationLog` channels), and spiritual milestones (`SpiritualMilestone`) in `/api/crm/personas/{persona_id}/timeline` and frontend profile timeline.
- E2E tests are written in python using pytest in `tests/test_crm_super_pro.py`.
- Run command: `pytest --no-cov tests/test_crm_super_pro.py` to bypass coverage thresholds.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Test Infra Setup | Define test runner, test structure, write `TEST_INFRA.md` | None | DONE |
| 2 | Tier 1 Tests | Feature Coverage: >= 5 cases per feature (R1, R2, R3) | M1 | DONE |
| 3 | Tier 2 Tests | Boundary & Corner Cases: >= 5 cases per feature (R1, R2, R3) | M2 | DONE |
| 4 | Tier 3 Tests | Cross-Feature Combinations: Pairwise combinations | M3 | DONE |
| 5 | Tier 4 Tests | Real-world Application Scenarios | M4 | DONE |
| 6 | Publish TEST_READY | Verify all tests, create `TEST_READY.md`, notify parent | M5 | DONE |

## Interface Contracts
- **Pastoral Health Score**:
  - `health_score` (Integer/Numeric, nullable) and `health_status` (String/Enum, nullable) fields in `Persona` database model and schemas (`PersonaResponse`, etc.).
  - A function/service `calculate_pastoral_health_score(db: Session, persona_id: UUID)` or similar scoring engine entry point.
- **AI Copilot**:
  - Endpoint `GET /api/crm/counseling/{id}/copilot-draft` returning a json object like `{"draft": "..."}` or `{"suggestion": "..."}`.
- **Omnichannel Inbox / Timeline**:
  - Endpoint `GET /api/crm/personas/{persona_id}/timeline` returning unified events, including communication logs (email, SMS, WhatsApp) and spiritual milestones, sorted chronologically descending.

## Test Case Inventory
### Tier 1 - Feature Coverage (15 cases)
1. `test_health_score_initial_defaults`: New personas have default health score/status.
2. `test_health_score_calc_no_activity`: Person with zero recent activity -> low score.
3. `test_health_score_calc_high_activity`: Person with high recent activity -> high score.
4. `test_health_score_calc_medium_activity`: Person with moderate activity -> medium score.
5. `test_health_score_calc_db_update`: Running calculation updates database columns.
6. `test_ai_copilot_endpoint_success`: Endpoint returns suggestion draft with mock OpenAI response.
7. `test_ai_copilot_empty_history`: Graceful suggestion when counseling history is empty.
8. `test_ai_copilot_openai_missing_key`: Returns standard error/warning message if key is missing.
9. `test_ai_copilot_openai_error_propagation`: Graceful handling of OpenAI API rate limits/service errors.
10. `test_ai_copilot_response_payload_structure`: Verifies response contains draft suggestion.
11. `test_timeline_unification_whatsapp`: WhatsApp logs show up in unified timeline.
12. `test_timeline_unification_sms`: SMS logs show up in unified timeline.
13. `test_timeline_unification_email`: Email logs show up in unified timeline.
14. `test_timeline_unification_spiritual_milestones`: Spiritual milestones show up in unified timeline.
15. `test_timeline_sorting_order`: Unified timeline sorted by date descending.

### Tier 2 - Boundary & Corner Cases (15 cases)
16. `test_health_score_calc_exactly_zero_score`: Minimum score boundary is handled.
17. `test_health_score_calc_exactly_hundred_score`: Maximum score boundary is handled.
18. `test_health_score_calc_missing_data_fields`: Missing optional data fields in calculations.
19. `test_health_score_calc_inactive_persona`: Inactive personas skipped or handled properly.
20. `test_health_score_calc_extreme_activities`: Out-of-bounds activities capped.
21. `test_ai_copilot_invalid_ticket_id`: Malformed/non-existent ticket ID returns 404/422.
22. `test_ai_copilot_unauthorized_user`: Unauthorized access returns 403.
23. `test_ai_copilot_extremely_long_history`: Counseling history truncation/context handling.
24. `test_ai_copilot_non_ascii_characters`: Special characters and emojis in ticket history.
25. `test_ai_copilot_cross_sede_isolation`: Accessing cross-sede ticket returns 404/403.
26. `test_timeline_empty_events`: Returns empty or creation milestone when no events exist.
27. `test_timeline_duplicate_timestamps`: Sorting identical timestamps handles correctly.
28. `test_timeline_cross_sede_leakage`: Accessing cross-sede persona timeline returns 404/403.
29. `test_timeline_special_milestone_types`: Custom/very long milestone types display correctly.
30. `test_timeline_html_or_injection_content`: Timeline content handles HTML/script injection gracefully.

### Tier 3 - Cross-Feature Combinations (3 cases)
31. `test_combo_scoring_affects_milestones`: Health score status change logged/noted.
32. `test_combo_copilot_uses_timeline`: Copilot reads from timeline/communication history for suggestions.
33. `test_combo_milestone_triggers_scoring`: Important milestone additions recalculate health score.

### Tier 4 - Real-world Application Scenarios (5 cases)
34. `test_scenario_new_convert_journey`: E2E journey of a new convert (joins -> academy -> baptized -> counseling).
35. `test_scenario_disengaged_member_recovery`: E2E journey of recovery (inactive -> risk status -> WhatsApp follow-up -> counseling -> active).
36. `test_scenario_sede_isolation_full_flow`: Separate sedes isolation of all data (scoring, copilot, timeline).
37. `test_scenario_copilot_rate_limiting_and_retry`: Concurrency test of scoring and copilot draft generation.
38. `test_scenario_milestone_and_multichannel_campaign`: Multichannel message campaign to personas and verification of timeline and scoring.
