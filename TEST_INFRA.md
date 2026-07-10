# E2E Test Infra: CRM Visual Enterprise Evolution

## Test Philosophy
- Opaque-box, requirement-driven. No dependency on implementation design.
- Methodology: Category-Partition + BVA + Pairwise + Workload Testing.

## Feature Inventory
| # | Feature | Source (requirement) | Tier 1 | Tier 2 | Tier 3 |
|---|---------|---------------------|:------:|:------:|:------:|
| 1 | Kanban UI | ORIGINAL_REQUEST R2 | 5 | 5 | Yes |
| 2 | Drag-and-Drop | ORIGINAL_REQUEST R2 | 5 | 5 | Yes |
| 3 | Reorder Endpoint | ORIGINAL_REQUEST R2 | 5 | 5 | Yes |
| 4 | Atomic Reordering | ORIGINAL_REQUEST R2 | 5 | 5 | Yes |
| 5 | Flow Builder UI | ORIGINAL_REQUEST R3 | 5 | 5 | Yes |
| 6 | 3-Node Connection | ORIGINAL_REQUEST R3 | 5 | 5 | Yes |
| 7 | Backend Branching Traversal | ORIGINAL_REQUEST R3 | 5 | 5 | Yes |
| 8 | Loop/Cycle Validation | ORIGINAL_REQUEST R3 | 5 | 5 | Yes |

## Test Architecture
- Test runner: pytest
- Test case format: Pytest integration tests checking attributes, endpoints, and behaviors.
- Directory layout: tests/test_crm_visual.py

## Real-World Application Scenarios (Tier 4)
| # | Scenario | Features Exercised | Complexity |
|---|----------|--------------------|------------|
| 1 | Lead Qualification Flow | F1, F2, F3, F7 | High |
| 2 | Support Ticket Routing | F1, F3, F6 | High |
| 3 | Cyclical Flow Resolution | F5, F8 | High |
| 4 | Bulk Reassignment & Reorder | F3, F4, F7 | High |
| 5 | Multi-Tenant Isolation CRM | F1, F3, F7 | High |

## Coverage Thresholds
- Tier 1: 40 tests (5 per feature)
- Tier 2: 40 tests (5 per feature)
- Tier 3: 8 tests (pairwise combinations)
- Tier 4: 5 tests (real-world workflows)
- Total minimum: 93 tests
