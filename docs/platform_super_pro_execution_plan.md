# Ruta de Ejecución – Plataforma “Super Pro”

## Resumen
Plan maestro para implementar la visión premium descrita en `platform_super_pro_plan.md`. Cada fase contiene entregables, responsables sugeridos y criterios de éxito. Secuencia recomendada: Fase 1 (UX + Performance) → Fase 2 (Datos/IA) → Fase 3 (Colaboración) → Fase 4 (DevEx & Integraciones).

---

## Fase 1 – UX Premium + Performance
### 1.1 Command Center Global (Command Palette Cmd+K)
- **Entregables**: Context provider (ya creado) + UI final dark glassmorphism; módulos registran comandos dinámicos.
- **Pasos**:
  1. Centralizar definiciones de comandos (IDs, iconos, permisos).
  2. Integrar Command Center en Academy, CRM, Projects, Support.
  3. Añadir acciones contextuales (crear tarea, emitir certificado) y tutorial onboarding.
- **Éxito**: 80% de navegación crítica se puede accionar vía palette.

### 1.2 SSR Streaming + Suspense
- **Entregables**: `loading.tsx` en Academy/CRM/Projects (listos). Próximos: Admin, Support, Community.
- **Pasos**:
  1. Convertir páginas principales a Server Components donde sea posible.
  2. Usar `fetch` cacheable + Suspense boundaries. Añadir `error.tsx` temáticos.
  3. Medir TTFB y reducir >30% en dashboards pesados.

### 1.3 Design System vivo + Storybook
- **Entregables**: Tokens (color, tipo, bordes), componentes base (Button, Card, Metric, Skeleton), documentación.
- **Pasos**:
  1. Extraer variables a `packages/ui` o `src/design/tokens`.
  2. Configurar Storybook y Chromatic para regression visual.
  3. Sincronizar con `aesthetic-expert` y crear checklists de aceptación.

---

## Fase 2 – Datos Unificados + IA Contextual
### 2.1 Knowledge Graph (PG + pgvector)
- **Entregables**: Base de datos `knowledge_graph`, procesos ETL, API `/graph/query`.
- **Pasos**:
  1. Diseñar esquema (nodes: Project, Course, Family, Ticket). 
  2. Jobs nocturnos + triggers on-change que actualicen el grafo.
  3. Endpoints GraphQL/REST para preguntas cruzadas (ej. “cursos que impactan familias X”).

### 2.2 IA Asistida
- **Entregables**: Microservicio `ai_coach`, hooks `useAIAssistant`, UI cards.
- **Pasos**:
  1. Integrar modelo (OpenAI/GPT) con prompts basados en grafo.
  2. Componentes reusable (ask AI en Academy, Projects, Support).
  3. Telemetría para medir adopción (inputs, outputs, rating).

### 2.3 Observabilidad Live
- **Entregables**: Websockets + dashboards en tiempo real (coordinación, CRM).
- **Pasos**:
  1. Extender `mesh_websockets` para métricas (asistencia, tareas completadas).
  2. Hooks `useLiveMetric` en frontend + fallback SSE.
  3. Alertas Slack/Teams a partir de thresholds.

---

## Fase 3 – Colaboración & Automations
### 3.1 Presencia en vivo / CRDT
- **Entregables**: Yjs + websockets en Projects/CRM (cursores, locks suaves).
- **Pasos**:
  1. Integrar Yjs + awareness provider.
  2. Mostrar avatares/cursors en tablas, formularios y documentos.
  3. Gestionar conflictos con merges automáticos y notificaciones.

### 3.2 Constructor de Automatizaciones ClickUp-style
- **Entregables**: Builder visual (drag/drop) + motor backend (Celery/worker) que ejecuta reglas.
- **Pasos**:
  1. Modelar `automation_rules` (trigger, conditions, actions).
  2. UI con canvas glassmorphism, historial y testing sandbox.
  3. Integrar con grafo y webhooks (ej. generar certificado al aprobar acta).

### 3.3 Editor Colaborativo
- **Entregables**: Tiptap + CRDT para actas, reuniones, notas.
- **Pasos**:
  1. Crear backend para versiones y permisos.
  2. UI con plantillas (acta formal, resumen de cohortes).
  3. Enlazar documentos a Projects/Academy para seguimiento.

---

## Fase 4 – DevEx + Integraciones
### 4.1 CI/CD Premium
- **Entregables**: GitHub Actions matrix (lint, tsc, vitest, playwright), preview env Docker, reportes en PR.
- **Pasos**:
  1. Configurar pipelines y seeds parciales para ambientes efímeros.
  2. Notificaciones Slack cuando CI falle o preview listo.
  3. Monitorear métricas (tiempo de build, flaky tests).

### 4.2 Feature Flags gestionados
- **Entregables**: Servicio flags (LaunchDarkly-like) + UI admin.
- **Pasos**:
  1. Migrar `useConfig` a client FF, exponer toggles en panel admin.
  2. Estrategia progressive rollouts (por rol o iglesia).

### 4.3 Integraciones Estratégicas
- **Calendario bidireccional**: Sync Google/Outlook con OAuth y webhooks.
- **Pagos/Donaciones**: Stripe (checkout, dashboards, webhooks).
- **Mensajería Omnicanal**: Servicio que centraliza WhatsApp/email/SMS con historial CRM.

---

## Gobernanza y Seguimiento
- Establecer comité quincenal (Producto + Diseño + Ingeniería) para revisar avances.
- Medir KPIs por fase (ej. adopción Command Center, latencia, uso IA, número de automatizaciones). 
- Mantener `platform_super_pro_plan.md` + este plan sincronizados; registrar log de decisiones.
- Abrir épicas/OKRs en Projects (p. ej. "Fase1-CommandCenter", "Fase2-KnowledgeGraph").

## Recomendaciones finales
1. Empezar inmediatamente con Fase 1 (Command Center + SSR streaming + Design System), ya se adelantaron componentes.
2. Asignar squads por fase para evitar context switching.
3. Documentar todo en Notion/Docs y comunicar a stakeholders para reforzar narrativa premium.

---

## Avance ejecutado (2026-03-27)
- **Fase 1.2/1.3**: Instrumentación Web Vitals activa (TTFB/LCP/FCP) con persistencia local y dashboard admin (`/admin/analytics/web-vitals`).
- **Fase 1.3**: Storybook estabilizado, nuevo layout story `WorkspaceShell` y componente base `DSCommandEntry` para command palette.
- **Fase 2.1**: `GET /graph/snapshot` ahora soporta `types`, `limit`, `offset`; agregado `GET /graph/connections/{node_id}`.
- **Fase 2.1/2.2**: Hook `useGraphInsights` integrado en Academy y vista interactiva de `/graph` con pan/zoom, filtro por tipo y buscador.
- **Fase 4.1**: CI ampliado con job frontend (`build`, `test`, `build-storybook`, `playwright smoke`) en `.github/workflows/ci.yml`.
- **Fase 4.2**: Feature flags operativos vía `/workspace/config` y `/workspace/flags` + panel admin en `/admin/settings/system`.
- **Fase 4.2**: Rollout segmentado inicial por rol/usuario/porcentaje (`/workspace/flags/rules/{feature_id}`) aplicado en runtime para `knowledge_graph` y `web_vitals_dashboard`.
- **Fase 4.1**: Smoke E2E con Playwright ejecutándose en CI; flujos autenticados listos con `E2E_EMAIL` y `E2E_PASSWORD`.
- **Fase 4.1**: CI ahora ejecuta smoke siempre y autenticados solo si existen secretos (`E2E_EMAIL`, `E2E_PASSWORD`, `E2E_API_URL`), con artefacto `playwright-report`.
- **Fase 4.2**: Auditoría de cambios de feature flags activa (`GET /workspace/flags/audit`) y visible en Admin Settings.
- **Fase 4.1**: Seed automático del usuario E2E antes de tests autenticados (`npm run test:e2e:seed-user`).
- **Fase 4.2**: Hardening de gobernanza de flags: validación estricta de schema, rechazo de feature ids desconocidos, export de auditoría (`/workspace/flags/audit/export?format=json|csv`) y rate limiting por endpoint sensible.
- **Fase 4.2**: Observabilidad operativa de flags con endpoint de resumen (`/workspace/flags/audit/summary`) y panel rápido de métricas/top actores en Admin Settings.
- **Fase 4.2**: Detección básica de anomalías en auditoría (`/workspace/flags/audit/anomalies`) con alerta visual en el panel de Settings.
- **Fase 4.2**: Trazabilidad avanzada de cambios con diff por evento (`before/after`) + filtros por acción/feature/actor en API y panel admin.
- **Fase 4.2**: Gestión de incidentes de flags (`/workspace/flags/incidents*`) con escaneo de anomalías, estados (`open/acknowledged/silenced/closed`) y acciones operativas desde Admin Settings.
- **Fase 4.2**: Operación madura de incidentes con métricas MTTA/MTTR, endpoint de resumen (`/workspace/flags/incidents/summary`) y cleanup controlado (`/workspace/flags/incidents/cleanup`).
- **Fase 4.2**: Timeline por incidente con notas operativas (`action=note`) y monitoreo SLA configurable (targets MTTA/MTTR + alertas de breach en panel admin).
- **Fase 4.2**: Escalamiento automatico de severidad de incidentes + notificaciones internas y endpoint de tendencias diarias (`/workspace/flags/incidents/trends`).
- **Fase 4.2**: Estadísticas ejecutivas weekly/monthly (`/workspace/flags/incidents/stats`) y export de incidentes con timeline (`/workspace/flags/incidents/export?format=json|csv`).
- **Fase 4.2**: Snapshot consolidado de compliance (`/workspace/flags/compliance/snapshot`) con flags, auditoría, anomalías, incidentes, tendencias y métricas operativas para adjuntar en PR/operaciones.
- **Fase 4.2**: Snapshot firmado/versionado (schema + `sha256` + `snapshot_id`) con historial temporal (`/workspace/flags/compliance/history`) y descarga de snapshots históricos desde Admin Settings.
- **Fase 4.2**: Gobernanza de snapshots con comparación entre versiones (`/workspace/flags/compliance/compare`) y política de retención/cleanup del historial (`/workspace/flags/compliance/history/cleanup`).
- **Fase 4.2**: Detección de drift entre snapshots con severidad (incluyendo flags críticos) y verificación de integridad hash en historial (`/workspace/flags/compliance/history/{snapshot_id}`).
- **Fase 4.2**: Alertas proactivas de drift al registrar snapshots (notificación automática en severidad `high/critical`) y resumen semanal de compliance (`/workspace/flags/compliance/history/weekly-summary`).
- **Fase 4.2**: Scoring de riesgo de drift (0-100) con sugerencias automáticas de mitigación y visualización de riesgo en panel de comparación/historial.
- **Fase 4.2**: Policy engine de drift por entorno (`development/staging/production`) y suppressions temporales con expiración (`/workspace/flags/compliance/policy`, `/workspace/flags/compliance/suppressions*`).
- **Fase 4.1**: CI frontend endurecido con `lint:critical`, `typecheck` + `lint` bloqueantes, quality gate de performance+compliance (`npm run quality:gate`) y artefactos de Storybook/Playwright en PR.

## Próximo bloque recomendado
1. Publicar Storybook visual snapshots (Chromatic o test-runner) y reporte en PR.
2. Endurecer validaciones de reglas de flags (schema estricto y límites de listas allow/deny).
3. Añadir export CSV/JSON de auditoría para compliance interno.
