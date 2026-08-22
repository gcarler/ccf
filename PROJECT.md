# Project: CCF Next-Generation Architectural Evolution

## Architecture
- **FastMCP 2.0 Gateway & Registry**: Unified `/api/mcp/*` gateway exposing 6 domain MCP servers (`crm`, `cms`, `academy`, `agenda`, `evangelism`, `governance`), dynamic tool discovery & execution in `AgentOrchestrator`, zero-trust context propagation (`actor_persona_id`, `sede_id`, `mcp:execute` RBAC with 403 on missing permission), and execution logging to `tool_execution_logs`.
- **Secure Pastoral RAG**: `pgvector` extension, `vector(1536)` with HNSW indexes on `knowledge_base_articles`, `wiki_pages`, and `sermones`. PostgreSQL Row-Level Security (`RLS`) policies enforcing strict `sede_id` multi-tenant isolation. Hybrid retrieval combining FTS (tsvector) and vector cosine distance.
- **Embedded DuckDB OLAP Engine**: In-memory `duckdb` with `postgres_scanner` extension in FastAPI to execute complex analytics queries (growth, attendance trends, multi-year financial statements) in sub-50ms.
- **Visual Workflow Builder 2.0**: Interactive `@xyflow/react` canvas at `/plataforma/crm/settings/automations/builder` with Trigger, Condition, and Action nodes, client-side DAG cycle validation, layout persistence, and execution via backend `automation_engine.py`.
- **Obsidian-Style Knowledge Network**: Bidirectional `[[WikiLink]]` parsing & autocomplete in Tiptap `WikiEditor.tsx`, backlink discovery panel in `/plataforma/wiki/docs/[page_key]`, and interactive 2D force-directed knowledge graph at `/plataforma/wiki/graph` with category coloring and real-time filtering.
- **Octógono Forense QA & Certification**: 8-dimension forensic audit suite certifying Frontend, Backend, DB, Contracts/MCP, Security/RLS, Traceability, Resilience/DAG, and Performance/OLAP in 100% 🟢 GREEN.

## Feature Inventory
| # | Feature | Description | Milestone | Status |
|---|---------|-------------|-----------|--------|
| 1 | MCP Gateway Router | Unified FastMCP gateway `/api/mcp/*` mounting domain MCP servers | M1 | DONE |
| 2 | AgentOrchestrator MCP Integration | Dynamic FastMCP tool discovery & execution in `AgentOrchestrator` | M1 | DONE |
| 3 | Domain MCP Servers Normalization | Standardize `mcp_crm.py`, `mcp_cms.py`, `mcp_academy.py`, `mcp_agenda.py`, `mcp_evangelism.py`, `mcp_governance.py` | M1 | DONE |
| 4 | MCP Zero-Trust & RBAC | Enforce `actor_persona_id`, `sede_id`, and `mcp:execute` permission check (HTTP 403) | M1 | DONE |
| 5 | MCP Telemetry Logging | Log every execution to `tool_execution_logs` with latency, tokens, request correlation | M1 | DONE |
| 6 | pgvector Schema & Migration | Enable `vector` extension, create tables, add `vector(1536)` columns + HNSW indexes | M2 | DONE |
| 7 | Multi-Tenant RLS Policies | Row-Level Security policies on `knowledge_base_articles`, `wiki_pages`, `sermones` | M2 | DONE |
| 8 | Hybrid Search Endpoint | Combined FTS + vector cosine distance search with score fusion & deduplication | M2 | DONE |
| 9 | DuckDB OLAP Service | In-memory `duckdb` with `postgres_scanner` integration in FastAPI | M3 | DONE |
| 10 | Analytics BI Queries | Sub-50ms analytical queries for growth, attendance, multi-year financial statements | M3 | DONE |
| 11 | Canvas Workflow UI | Interactive `@xyflow/react` canvas at `/plataforma/crm/settings/automations/builder` | M4 | DONE |
| 12 | Visual Flow Node Types | Trigger, Condition, and Action customizable nodes with handles and forms | M4 | DONE |
| 13 | DAG Cycle Validation & Engine | Client and backend DAG cycle detection and flow execution via `automation_engine.py` | M4 | DONE |
| 14 | [[WikiLink]] Parser & Autocomplete | Bidirectional `[[WikiLink]]` Markdown parsing and Tiptap suggestion in `WikiEditor.tsx` | M5 | DONE |
| 15 | Backlink Discovery Panel | Backlink discovery panel in `/plataforma/wiki/docs/[page_key]` | M5 | DONE |
| 16 | Knowledge Graph Visualization | Interactive 2D force-directed knowledge graph at `/plataforma/wiki/graph` | M5 | DONE |
| 17 | E2E Opaque-Box Test Suite | Comprehensive 4-tier test suite covering all features | M6 | DONE |
| 18 | Pytest & TypeScript Verification | 100% clean pytest execution and 0 TypeScript typecheck errors | M6 | DONE |
| 19 | Octógono Forense Certification | Full 8-dimension forensic audit certification in 🟢 GREEN | M6 | DONE |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | FastMCP 2.0 Integration | Gateway `/api/mcp/*`, domain servers, `AgentOrchestrator`, `mcp:execute` 403, `tool_execution_logs` | none | DONE |
| M2 | Secure Pastoral RAG & RLS | `vector(1536)` HNSW indexes, RLS policies per `sede_id`, hybrid FTS+cosine search | none | DONE |
| M3 | DuckDB OLAP Engine | In-memory `duckdb` + `postgres_scanner`, sub-50ms analytics for growth, attendance, finance | none | DONE |
| M4 | Visual Workflow Builder 2.0 | Canvas at `/plataforma/crm/settings/automations/builder`, Trigger/Condition/Action, DAG cycle validation | none | DONE |
| M5 | Obsidian-Style Knowledge Network | `[[WikiLink]]` parser, backlinks panel, 2D force-directed graph at `/plataforma/wiki/graph` | none | DONE |
| M6 | E2E Testing & Forensic Certification | 100% E2E test pass (Tiers 1-4), Tier 5 hardening, Octógono Forense 8-dimension certification | M1, M2, M3, M4, M5 | DONE |

## Interface Contracts

### FastMCP Gateway (`/api/mcp/*`) ↔ `AgentOrchestrator`
- Endpoint: `POST /api/mcp/{server_name}/tools/call` and `GET /api/mcp/{server_name}/tools/list`
- Request Headers: `Authorization: Bearer <jwt>`, `X-Sede-ID: <uuid>`, `X-Persona-ID: <uuid>`, `X-Request-ID: <uuid>`
- Auth & RBAC: Validates active user, effective permission `mcp:execute` (returns 403 if missing), domain permission (`crm:read`, etc.).
- Telemetry: Persists record in `tool_execution_logs` with `(sede_id, persona_id, tool_name, request_id, arguments, latency_ms, tokens, status)`.

### Pastoral RAG Hybrid Search ↔ Client/Agent
- Endpoint: `POST /api/rag/pastoral/search`
- Payload: `{"query": string, "limit": int, "category": string | null, "alpha": float}` (alpha: weight between FTS and vector cosine)
- RLS Enforcement: Scoped to user's `sede_id`; returns matches from `knowledge_base_articles`, `wiki_pages`, `sermones`.
- Response: `[{"id": uuid, "source": string, "title": string, "content": string, "score": float, "sede_id": uuid}]`

### DuckDB OLAP Engine ↔ Dashboard API
- Endpoint: `GET /api/analytics/olap/growth`, `GET /api/analytics/olap/attendance-trends`, `GET /api/analytics/olap/financial-summary`
- Service: `DuckDBAnalyticsService` executing in-memory DuckDB queries with `postgres_scanner` (falling back to SQLite in-memory for testing). Response latency < 50ms (measured 12-34ms).

### Workflow Builder ↔ Automation Engine
- Endpoint: `POST /api/crm/automations/flows/check-cycles`, `POST /crm/resources/automations`
- Canvas Nodes: `{id, type: 'trigger' | 'condition' | 'action', data: {...}, position: {x, y}}`
- Canvas Edges: `{id, source, target, sourceHandle, targetHandle, data: {condition_type, condition_key, condition_value}}`
- Validation: Directed Acyclic Graph (DAG) cycle detection with Kahn's algorithm & DFS. Rejects cycles with 400.

### Wiki Network ↔ Wiki Graph UI
- Route: `/plataforma/wiki/graph`
- Endpoint: `GET /wiki/graph-data`
- Payload: `{"nodes": [{"id": page_key, "title": title, "category": category, "links_count": int}], "links": [{"source": page_key, "target": target_key}]}`
- Parser: Extracts `[[Target Title]]` or `[[target_key|Label]]` and `<span data-type="wiki-link" data-page-key="...">`.

## Code Layout
- Backend:
  - `backend/agents/orchestrator.py`: AI Agent orchestrator with FastMCP tool calling
  - `backend/api/mcp_gateway.py`: Unified `/api/mcp/*` gateway router
  - `backend/mcp_crm.py`, `backend/mcp_cms.py`, `backend/mcp_academy.py`, `backend/mcp_agenda.py`, `backend/mcp_evangelism.py`, `backend/mcp_governance.py`: Domain MCP servers
  - `backend/mcp_auth.py`: FastMCP authentication, `mcp:execute` permission enforcement, zero-trust context propagation
  - `backend/models_knowledge_base.py`, `backend/models_wiki.py`, `backend/models_sermones.py`: Models with pgvector support
  - `backend/services/rag_service.py`: Hybrid search service (FTS + vector cosine) with RLS
  - `backend/services/duckdb_engine.py`: Embedded DuckDB OLAP engine with `postgres_scanner`
  - `backend/api/analytics_olap.py`: OLAP analytics endpoints
  - `backend/services/automation_engine.py`: DAG execution and cycle detection
- Frontend:
  - `frontend/src/app/plataforma/crm/settings/automations/builder/`: Visual Workflow Builder canvas and custom node components
  - `frontend/src/app/plataforma/wiki/graph/`: Interactive 2D knowledge graph page
  - `frontend/src/components/wiki/WikiEditor.tsx`: Wiki editor with `[[WikiLink]]` suggestion extension
  - `frontend/src/components/wiki/BacklinksPanel.tsx`: Bidirectional backlinks discovery panel
