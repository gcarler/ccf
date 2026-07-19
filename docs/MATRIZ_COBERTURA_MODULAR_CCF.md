# Matriz de Cobertura Modular — CCF

> **Objetivo:** dejar verificable, en un solo lugar, qué artefactos canónicos tiene cada modulo y qué deuda sigue abierta dentro del plan de arquitectura modular.

**Actualizado:** 2026-07-19
**Estado:** Auditoría forense completa (30/33 módulos cubiertos)

---

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

### Módulos certificados (6/6 artefactos)

| Modulo | Estado | API contract | QA checklist | RBAC matrix | Smoke script | Gaps abiertos principales |
|---|---|---|---|---|---|---|
| CRM | `ESTADO_CRM.md` | `CRM_API_CONTRACTS.md` | `CRM_QA_CHECKLIST.md` | `CRM_RBAC_MATRIX.md` | `scripts/test_crm_quality.py` | ampliar smoke a groups bridge, messaging y resources |
| Academy | `ESTADO_ACADEMY.md` | `ACADEMY_API_CONTRACTS.md` | `ACADEMY_QA_CHECKLIST.md` | `ACADEMY_RBAC_MATRIX.md` | `scripts/test_academy_quality.py` | ampliar certificates, rutas duplicadas y flows admin |
| CMS | `ESTADO_CMS.md` | `CMS_API_CONTRACTS.md` | `CMS_QA_CHECKLIST.md` | `CMS_RBAC_MATRIX.md` | `scripts/test_cms_quality.py` | builder, enterprise profundo, visual QA |
| Messaging / Community | `ESTADO_MESSAGING_COMMUNITY.md` | `MESSAGING_COMMUNITY_API_CONTRACTS.md` | `MESSAGING_COMMUNITY_QA_CHECKLIST.md` | `MESSAGING_COMMUNITY_RBAC_MATRIX.md` | `scripts/test_messaging_quality.py` | contrato de chat directo, bridge CRM |
| Agenda / Calendar | `ESTADO_AGENDA.md` | `AGENDA_API_CONTRACTS.md` | `AGENDA_QA_CHECKLIST.md` | `AGENDA_RBAC_MATRIX.md` | `scripts/test_agenda_quality.py` | taxonomía heredada, reservas/participantes profundas |
| Evangelismo | `ESTADO_EVANGELISMO.md` | `EVANGELISMO_API_CONTRACTS.md` | `EVANGELISMO_QA_CHECKLIST.md` | `EVANGELISMO_RBAC_MATRIX.md` | `scripts/test_evangelism_quality.py` | runtime auth UI, descomposición de strategy page |
| Proyectos | `ESTADO_PROYECTOS.md` | `PROJECTS_API_CONTRACTS.md` | `PROJECTS_QA_CHECKLIST.md` | `PROJECTS_RBAC_MATRIX.md` | `scripts/test_projects_quality.py` | gaps operativos de quality/inbox/RBAC asimétrico |
| Plataforma compartida | `ESTADO_PLATAFORMA_COMPARTIDA.md` | `PLATAFORMA_AUTH_RBAC_API_UI.md` | `PLATAFORMA_COMPARTIDA_QA_CHECKLIST.md` | matriz raíz en `PLATAFORMA_AUTH_RBAC_API_UI.md` | `scripts/test_platform_quality.py` | drift auth legacy, guards frontend |

### Módulos auditados Fase 1 (6/6 artefactos)

| Modulo | Estado | API contract | QA checklist | RBAC matrix | Smoke script |
|---|---|---|---|---|---|
| Admin | `ESTADO_ADMIN.md` | `ADMIN_API_CONTRACTS.md` | `ADMIN_QA_CHECKLIST.md` | `ADMIN_RBAC_MATRIX.md` | `scripts/test_admin_quality.py` |
| Chat | `ESTADO_CHAT.md` | `CHAT_API_CONTRACTS.md` | `CHAT_QA_CHECKLIST.md` | `CHAT_RBAC_MATRIX.md` | `scripts/test_chat_quality.py` |
| Vida Espiritual | `ESTADO_VIDA_ESPIRITUAL.md` | `VIDA_ESPIRITUAL_API_CONTRACTS.md` | `VIDA_ESPIRITUAL_QA_CHECKLIST.md` | `VIDA_ESPIRITUAL_RBAC_MATRIX.md` | `scripts/test_spiritual_life_quality.py` |

### Módulos auditados Fase 2 (6/6 artefactos)

| Modulo | Estado | API contract | QA checklist | RBAC matrix | Smoke script |
|---|---|---|---|---|---|
| Auth v3 | `ESTADO_AUTH_V3.md` | (heredado de plataforma compartida) | `AUTH_V3_QA_CHECKLIST.md` | (heredado de plataforma compartida) | `scripts/test_auth_v3_quality.py` |
| Kernel | `ESTADO_KERNEL.md` | (heredado de plataforma compartida) | `KERNEL_QA_CHECKLIST.md` | (heredado de plataforma compartida) | `scripts/test_kernel_quality.py` |
| Workspace | `ESTADO_WORKSPACE.md` | (heredado de plataforma compartida) | `WORKSPACE_QA_CHECKLIST.md` | (heredado de plataforma compartida) | `scripts/test_workspace_quality.py` |
| Wiki | `ESTADO_WIKI.md` | `WIKI_API_CONTRACTS.md` | `WIKI_QA_CHECKLIST.md` | `WIKI_RBAC_MATRIX.md` | `scripts/test_wiki_quality.py` |
| Finance | `ESTADO_FINANCE.md` | (integrado en `MODULO_ADMIN.md`) | `FINANCE_QA_CHECKLIST.md` | `FINANCE_RBAC_MATRIX.md` | `scripts/test_finance_quality.py` |

### Módulos auditados Fase 3 (con ESTADO + auditoría)

| Modulo | Estado | Auditoría | Smoke |
|---|---|---|---|
| Support | `ESTADO_SUPPORT.md` | `AUDITORIA_FORENSE_SUPPORT.md` | `scripts/test_fase3_quality.py` |
| Community | `ESTADO_COMMUNITY.md` | `AUDITORIA_FORENSE_COMMUNITY.md` | `scripts/test_fase3_quality.py` |
| Dashboard | `ESTADO_DASHBOARD.md` | `AUDITORIA_FORENSE_DASHBOARD.md` | `scripts/test_fase3_quality.py` |
| Donations | `ESTADO_DONATIONS.md` | `AUDITORIA_FORENSE_DONATIONS.md` | `scripts/test_fase3_quality.py` |
| System | `ESTADO_SYSTEM.md` | `AUDITORIA_FORENSE_SYSTEM.md` | (heredado) |
| Agents | `ESTADO_AGENTS.md` | `AUDITORIA_FORENSE_AGENTS.md` | `scripts/test_fase3_quality.py` |
| Prayer | — | `AUDITORIA_FORENSE_PRAYER.md` | — |
| Graph, Analytics, Enterprise CMS, Governance, Tables, Youtube | `ESTADO_MODULOS_MENORES.md` | `AUDITORIA_FORENSE_MODULOS_MENORES.md` | `scripts/test_fase3_quality.py` |

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
| Admin | `PLAN_ADMIN_CALIDAD.md` |
| Chat | `PLAN_CHAT_CALIDAD.md` |
| Vida Espiritual | `PLAN_VIDA_ESPIRITUAL_CALIDAD.md` |

## 4. Estado de cobertura de tests

| Métrica | Valor |
|---|---|
| Tests totales | ~4,630 |
| Archivos de test | 166 |
| Cobertura global backend | ~39% |
| Módulos con tests dedicados | Admin, Wiki, Chat, Finance, Vida Espiritual, Support, Donations, Agents, Enterprise CMS, Graph, Services (10+ archivos) |
| Módulos al 100% de cobertura | ~35+ (models, schemas, api/governance, api/prayer, api/wiki, api/workspace, core/config, core/logging, core/audit, crud/audit, etc.) |

## 5. Arranque uniforme

Toda sesión nueva debe pasar por:

1. `docs/ARRANQUE_MODULAR_CCF.md`
2. el `ESTADO_*` del modulo owner
3. el subplan del modulo si el cambio no es trivial
4. `docs/ESTADO_PLATAFORMA_COMPARTIDA.md` cuando el owner real sea shared

## 6. Estado

Matriz actualizada el `2026-07-19` con los resultados de las 3 fases de auditoría forense. 30/33 módulos tienen al menos ESTADO + auditoría. 16 módulos tienen 6/6 artefactos canónicos completos.
