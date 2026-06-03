# AUDITORÍA FORENSE CCF — Resultados

## CRITICAL (backend 500)
1. /api/agents/insights → 500 — JSONB en modelos agents (SQLite incompat)
2. /api/agents/tasks → 500 — mismo

## HIGH (frontend llama endpoints inexistentes)  
3. /api/projects/{id}/tasks → 404 — frontend 6 calls, no backend route
4. /api/evangelism/grupos → debe funcionar vía alias

## MEDIUM
5. /api/crm/members/donations → renombrado a /personas/donations
6. card.trend.includes() → TypeError en dashboard (ya fixeado, no deployado)

## DB ↔ Models
7. SQLAlchemy models sync con PostgreSQL — verificar column types
