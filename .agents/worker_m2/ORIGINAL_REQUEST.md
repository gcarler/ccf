## 2026-07-10T06:14:01Z
You are the Worker for Milestone 2: AI Copilot for Counseling.
Your working directory is /root/ccf/.agents/worker_m2.
Your tasks are:
1. Implement the GET and POST /api/crm/counseling/{ticket_id}/copilot-draft endpoint in /root/ccf/backend/api/crm/pastoral.py.
   - The endpoint must require the user to have module access to crm (read).
   - Use _get_scoped_counseling_ticket(db, current_user, ticket_id) to fetch the ticket, enforcing Sede scope isolation.
   - Compile context by querying the persona's historical counseling tickets, communication logs, and spiritual milestones. Ensure the full content of recent communication logs is formatted into the prompt text to provide rich context to the LLM.
   - Check if OPENAI_API_KEY (or OPENROUTER_API_KEY or settings.openai_api_key) is available. If missing, return a graceful structured fallback draft response: {"draft": "..."} with status code 200 (not a crash).
   - Call OpenAI API using the official OpenAI client (import from openai import OpenAI and use client = OpenAI(), calling client.chat.completions.create(model="gpt-4o-mini", messages=[...])).
   - Catch all exceptions from the OpenAI client call and return a graceful fallback draft containing the exception details with status code 200 (not a 500 crash).
   - Return response format: {"draft": generated_content} (you can also include "suggestion": generated_content for extra safety).
2. Update the frontend file /root/ccf/frontend/src/app/plataforma/crm/counseling/[id]/page.tsx:
   - Introduce editing state for the "Resumen de la Sesion" notes card. When editing is toggled on, show a <textarea> with the current notes.
   - Include a toolbar inside the card when editing is active:
     - AI Copilot button: calls GET /api/crm/counseling/{id}/copilot-draft via apiFetch and appends/updates the notes textarea with the draft, showing a sonner toast message upon success. Show a loading indicator/disabled state while calling.
     - Guardar (Save) button: calls PATCH /api/crm/counseling/{id} with { "notes": ... } to save the updated notes, updates the frontend state, and toggles editing off.
     - Cancelar (Cancel) button: discards changes and toggles editing off.
3. Run the unit and E2E tests related to AI Copilot:
   - pytest --no-cov tests/test_crm_super_pro.py -k "test_ai_copilot"
4. Verify that all 5 E2E tests for AI Copilot pass successfully.
5. Document your implementation details, files modified, and test results in /root/ccf/.agents/worker_m2/handoff.md.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Communicate your results back to me by sending a message when done.
