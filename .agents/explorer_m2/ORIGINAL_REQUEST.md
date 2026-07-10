## 2026-07-10T06:12:29Z

You are the Explorer for Milestone 2: AI Copilot for Counseling.
Your working directory is /root/ccf/.agents/explorer_m2.
Your tasks are:
1. Locate where counseling endpoints are defined (hint: check backend/api/crm/pastoral.py or similar).
2. Examine the frontend file /root/ccf/frontend/src/app/plataforma/crm/counseling/[id]/page.tsx or search for counseling detail page to locate where the AI Copilot button should be integrated.
3. Check how the application imports and initializes OpenAI. Are there existing AI helpers or config variables (like settings)?
4. Propose a detailed step-by-step implementation plan for the /api/crm/counseling/{id}/copilot-draft FastAPI GET/POST endpoint, including:
   - Sede scope checking (using _get_scoped_counseling_ticket).
   - Extracting ticket notes and the persona's timeline events/communication logs for OpenAI context compilation.
   - Initializing openai.OpenAI() client.
   - Graceful fallback for missing OPENAI_API_KEY (returning a default template response).
   - Mocking or handling OpenAI API exceptions gracefully without a 500 error.
   - The exact JSON response format {"draft": "..."} or {"suggestion": "..."}.
5. Propose how the frontend button should be added to counseling detail page to fetch the draft and update the counseling ticket notes editor.
6. Write your findings to /root/ccf/.agents/explorer_m2/handoff.md.
7. Send me a message when done with your findings.
