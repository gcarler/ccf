## 2026-07-10T06:20:44Z
You are the Worker to apply fixes to backend files for Milestone 2 and Milestone 3 E2E test alignment.
Your working directory is /root/ccf/.agents/worker_m2_fix.
Your tasks are:
1. Fix the mock-detection and fallback logic in /root/ccf/backend/api/crm/pastoral.py inside the get_copilot_draft function (around line 963):
   - Simplify the OpenAI completions call. Do not use the complicated comp_create logic.
   - Simply call client.chat.completions.create(...) and catch any exceptions.
   - For extracting generated_content, do: generated_content = response.choices[0].message.content.
   - Update the check for fallback:
     ```python
     if not generated_content or isinstance(generated_content, (MagicMock, Mock)) or not isinstance(generated_content, str):
         if not os.getenv("OPENAI_API_KEY") and not os.getenv("OPENROUTER_API_KEY") and not getattr(settings, "openai_api_key", None):
             fallback_msg = "Fallback suggestion: OpenAI API key is missing. Please configure OPENAI_API_KEY."
             return {
                 "draft": fallback_msg,
                 "suggestion": fallback_msg
             }
         generated_content = "Mocked AI Response Suggestion"
     ```
     (Make sure to import MagicMock, Mock from unittest.mock).
2. Fix /root/ccf/backend/crud/crm_/timeline.py to query and include SpiritualMilestone events in the unified timeline:
   - Query all active milestones for the persona:
     ```python
     milestones = db.query(models.SpiritualMilestone).filter(
         models.SpiritualMilestone.persona_id == persona.id,
         models.SpiritualMilestone.deleted_at.is_(None)
     ).all()
     ```
   - For each milestone, append to the timeline list:
     ```python
     timeline.append({
         "type": "spiritual_milestone",
         "title": f"Hito Espiritual: {m.type}",
         "description": m.notes or f"Hito registrado: {m.type}",
         "date": m.created_at.isoformat() if m.created_at else m.event_date.isoformat(),
         "icon": "Milestone",
         "color": "bg-indigo-500",
     })
     ```
3. Fix the scoring engine in /root/ccf/backend/crud/crm_/health.py:
   - In calculate_pastoral_health, check persona.last_meeting_attendance and persona.last_group_attendance to implement recent engagement logic.
   - If last_meeting_attendance is within the last 30 days (from today), or if last_group_attendance is within the last 30 days (from today), set recent_score = 40.0.
   - Take the maximum of the calculated attendance_score and recent_score: attendance_score = max(attendance_score, recent_score).
4. Run the tests:
   - pytest --no-cov tests/test_crm_super_pro.py
5. Verify that all 38 tests in tests/test_crm_super_pro.py pass cleanly.
6. Write a detailed handoff report to /root/ccf/.agents/worker_m2_fix/handoff.md.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Communicate your results back to me by sending a message when done.
