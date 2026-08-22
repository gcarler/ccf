# E2E Test Infra: CCF Next-Generation Architectural Evolution

## Test Philosophy
- Opaque-box, requirement-driven. No dependency on implementation internal tricks.
- Methodology: Category-Partition + Boundary Value Analysis (BVA) + Pairwise Combinatorial Testing + Real-World Workload Testing.
- 4-Tier Structure:
  - Tier 1: Feature Coverage (>=5 tests per feature area)
  - Tier 2: Boundary & Corner Cases (>=5 tests per feature area)
  - Tier 3: Cross-Feature Interactions & Combinations (pairwise coverage)
  - Tier 4: Real-World Application Scenarios (end-to-end pastoral and administrative workflows)
  - Tier 5: Adversarial Coverage Hardening (white-box gap discovery & stress testing)

## Feature Inventory
| # | Feature | Source (requirement) | Tier 1 | Tier 2 | Tier 3 |
|---|---------|---------------------|:------:|:------:|:------:|
| 1 | FastMCP Gateway & Tool Discovery | R1 | 5 | 5 | ✓ |
| 2 | FastMCP Zero-Trust & 403 RBAC | R1 | 5 | 5 | ✓ |
| 3 | FastMCP Telemetry in tool_execution_logs | R1 | 5 | 5 | ✓ |
| 4 | Domain MCP Servers Execution | R1 | 5 | 5 | ✓ |
| 5 | pgvector Migration & HNSW Indexing | R2 | 5 | 5 | ✓ |
| 6 | Multi-Tenant RLS Sede Isolation | R2 | 5 | 5 | ✓ |
| 7 | Hybrid RAG Search (FTS + Vector Cosine) | R2 | 5 | 5 | ✓ |
| 8 | Embedded DuckDB OLAP Engine | R3 | 5 | 5 | ✓ |
| 9 | Sub-50ms Dashboard Analytics | R3 | 5 | 5 | ✓ |
| 10 | Workflow Canvas No-Code Builder | R4 | 5 | 5 | ✓ |
| 11 | DAG Cycle Detection & Automation Engine | R4 | 5 | 5 | ✓ |
| 12 | [[WikiLink]] Parsing & Backlink Panel | R5 | 5 | 5 | ✓ |
| 13 | Interactive 2D Wiki Knowledge Graph | R5 | 5 | 5 | ✓ |

## Test Architecture
- **Test Runner Location**: `/root/ccf/tests/e2e/test_evolution_e2e.py`
- **Execution Command**: `PYTHONPATH=. ./venv/bin/python -m pytest tests/e2e/test_evolution_e2e.py -v`
- **Pass/Fail Semantics**: All tests must return exit code 0.
- **Client**: ASGI TestClient / requests simulating authentic client requests with JWT and headers.

## Real-World Application Scenarios (Tier 4)
| # | Scenario | Features Exercised | Complexity |
|---|----------|--------------------|------------|
| 1 | Multi-Tenant Pastoral Assistance: Pastor searches sermons & wiki articles for sermon prep; RLS prevents cross-sede leakage | R2, R5, R1 | High |
| 2 | Executive Dashboard & Financial Aggregation: Bishop queries 5-year multi-sede KPI trends via DuckDB OLAP in sub-50ms | R3 | Medium |
| 3 | Visual CRM Automation Lifecycle: Admin designs onboarding DAG on canvas, cycle check verifies valid DAG, persona trigger executes actions | R4 | High |
| 4 | Agent Orchestrator Multi-Tool FastMCP Call: Agent resolves pastoral request using MCP tools, logs telemetry in `tool_execution_logs` | R1, R2 | High |
| 5 | Ministerial Knowledge Graph Navigation: Leader links ministry docs via `[[WikiLinks]]`, explores backlink network and interactive graph | R5 | Medium |

## Coverage Thresholds
- Tier 1: ≥ 65 test cases across features
- Tier 2: ≥ 65 boundary/corner test cases
- Tier 3: ≥ 15 pairwise interaction tests
- Tier 4: ≥ 5 realistic application scenarios
- Tier 5: Adversarial stress testing & forensic verification
- **Target Total: ≥ 150 comprehensive test cases**
