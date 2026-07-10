## 2026-07-10T05:31:10Z

Perform an initial codebase analysis of CCF's CRM system to answer:
1. Where are the models for `Persona`, attendance, donations, groups, counseling cases (tickets and message/history logs), communication logs (WhatsApp, SMS, Email), and spiritual milestones defined?
2. What are the database schema definitions/fields for these entities?
3. How is multi-tenant isolation (sede_id) handled on these entities?
4. How is the counseling history structured and retrieved?
5. How is the OpenAI integration set up in the backend (where are API keys config, existing AI helpers)?
6. Where in the frontend are the persona details view and counseling ticket detail view implemented?
7. Write your findings in a structured report `handoff.md` inside your directory. Also send a message to me (conversation ID 07b3cbfa-64a5-462b-bd23-3e5e89550b2f) with a summary of the report and the absolute path to your `handoff.md`.

Your identity:
- Working directory: /root/ccf/.agents/explorer_initial/
- Role: Codebase Explorer
