# Matriz de Cobertura Modular — CCF

> **Objetivo:** dejar verificable, en un solo lugar, qué artefactos canónicos tiene cada modulo y qué deuda sigue abierta dentro del plan de arquitectura modular.

## 1. Regla de lectura

Cada modulo critico debe cubrir, como mínimo:

1. handover de estado
2. contrato API
3. checklist QA
4. matriz RBAC
5. smoke script canónico
6. backlog estable con `PARCIAL-*` y `PEND-*`

Esta matriz no reemplaza los docs del modulo. Resume cobertura y huecos reales.

Complemento operativo:

- `docs/ARRANQUE_MODULAR_CCF.md` centraliza la entrada uniforme por modulo: lectura inicial, backlog vivo, smoke canónico y ruta mínima de validación.

## 2. Cobertura actual por modulo

| Modulo | Estado | API contract | QA checklist | RBAC matrix | Smoke script | Gaps abiertos principales |
|---|---|---|---|---|---|---|
| CRM | `ESTADO_CRM.md` | `CRM_API_CONTRACTS.md` | `CRM_QA_CHECKLIST.md` | `CRM_RBAC_MATRIX.md` | `scripts/test_crm_quality.py`, `frontend/tests/e2e/crm/smoke.spec.ts`, `frontend/tests/e2e/crm/persona-detail.spec.ts` | ampliar smoke a groups bridge, messaging y resources |
| Academy | `ESTADO_ACADEMY.md` | `ACADEMY_API_CONTRACTS.md` | `ACADEMY_QA_CHECKLIST.md` | `ACADEMY_RBAC_MATRIX.md` | `scripts/test_academy_quality.py`, `frontend/tests/e2e/academy/smoke.spec.ts`, `frontend/tests/e2e/academy/profile-detail.spec.ts` | ampliar certificates, rutas duplicadas y flows admin |
| CMS | `ESTADO_CMS.md` | `CMS_API_CONTRACTS.md` | `CMS_QA_CHECKLIST.md` | `CMS_RBAC_MATRIX.md` | `scripts/test_cms_quality.py`, `frontend/tests/e2e/cms/smoke.spec.ts`, `frontend/tests/e2e/cms/pages-preview.spec.ts` | builder, enterprise profundo, visual QA |
| Messaging / Community | `ESTADO_MESSAGING_COMMUNITY.md` | `MESSAGING_COMMUNITY_API_CONTRACTS.md` | `MESSAGING_COMMUNITY_QA_CHECKLIST.md` | `MESSAGING_COMMUNITY_RBAC_MATRIX.md` | `scripts/test_messaging_quality.py`, `frontend/tests/e2e/messaging/smoke.spec.ts`, `frontend/tests/e2e/messaging/direct-messages.spec.ts` | contrato de chat directo, bridge CRM |
| Agenda / Calendar | `ESTADO_AGENDA.md` | `AGENDA_API_CONTRACTS.md`, `SYSTEM_CALENDAR_CONTRACT.md` | `AGENDA_QA_CHECKLIST.md` | `AGENDA_RBAC_MATRIX.md` | `scripts/test_agenda_quality.py`, `frontend/tests/e2e/agenda/smoke.spec.ts`, `frontend/tests/e2e/agenda/calendar-events.spec.ts` | taxonomía heredada `spiritual_life:*`, reservas/participantes profundas |
| Evangelismo | `ESTADO_EVANGELISMO.md` | `EVANGELISMO_API_CONTRACTS.md` | `EVANGELISMO_QA_CHECKLIST.md` | `EVANGELISMO_RBAC_MATRIX.md` | `scripts/test_evangelism_quality.py`, `frontend/tests/e2e/evangelism/smoke.spec.ts`, `frontend/tests/e2e/evangelism/sessions-detail.spec.ts`, `frontend/tests/e2e/evangelism/rankings-multiplication.spec.ts`, `frontend/tests/e2e/evangelism/events-scanner.spec.ts` | runtime auth UI, descomposición de strategy page, búsqueda remota de personas |
| Proyectos | `ESTADO_PROYECTOS.md` | `PROJECTS_API_CONTRACTS.md` | `PROJECTS_QA_CHECKLIST.md` | `PROJECTS_RBAC_MATRIX.md` | `scripts/test_projects_quality.py`, `frontend/tests/e2e/projects/smoke.spec.ts` | gaps operativos nuevos de quality/inbox/RBAC asimétrico |
| Plataforma compartida | `ESTADO_PLATAFORMA_COMPARTIDA.md` | `PLATAFORMA_AUTH_RBAC_API_UI.md`, `PLATAFORMA_AUTH_RUNTIME_CONTRACT.md`, `PLATAFORMA_UI_BASE_PROTEGIDA.md` | `PLATAFORMA_COMPARTIDA_QA_CHECKLIST.md` | matriz raíz en `PLATAFORMA_AUTH_RBAC_API_UI.md` | `scripts/test_platform_quality.py`, `frontend/tests/e2e/platform-critical-routes.spec.ts` | drift auth legacy, guards frontend, blast radius multi-módulo |

## 3. Subplanes operativos existentes

| Modulo | Subplan |
|---|---|
| CRM | `PLAN_CRM_CALIDAD.md` |
| Academy | `PLAN_ACADEMY_CALIDAD.md` |
| CMS | `PLAN_CMS_CALIDAD.md` |
| Messaging / Community | `PLAN_MESSAGING_CALIDAD.md` |
| Agenda / Calendar | `PLAN_AGENDA_CALIDAD.md` |
| Evangelismo | `PLAN_EVANGELISMO_CALIDAD.md` |
| Proyectos | `PLAN_PROYECTOS_CALIDAD.md` |
| Plataforma compartida | `PLAN_PLATAFORMA_COMPARTIDA_CALIDAD.md` |

## 4. Arranque uniforme

Toda sesión nueva debe pasar por:

1. `docs/ARRANQUE_MODULAR_CCF.md`
2. el `ESTADO_*` del modulo owner
3. el subplan del modulo si el cambio no es trivial
4. `docs/ESTADO_PLATAFORMA_COMPARTIDA.md` cuando el owner real sea shared

## 5. Lectura operativa

- La cobertura base por modulo ya incluye planes operativos dedicados en todos los modulos críticos y en la plataforma compartida.
- El hueco actual ya no es crear paquetes base sino profundizar los gates restantes: reservas/participantes, contratos de dashboards, contratos cruzados y deuda estructural de pantallas complejas.
- El plan modular ya dejó de ser solo “crear md”; ahora el foco es endurecer los artefactos existentes.

## 6. Estado

Matriz creada el `2026-07-16` como evidencia de cobertura documental transversal dentro de `docs/PLAN_ARQUITECTURA_MODULAR_CCF.md`.
