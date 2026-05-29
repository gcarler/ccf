# PLAN DIRECTOR — CCF PLATFORM PRO v4.0

## Objetivo
Transformar CCF en una plataforma eclesial enterprise con 8 módulos profesionales
de alto impacto, implementados con rigor técnico absoluto.

## Principios de Ejecución
- **Atomic commits**: un feature, un commit, verificado
- **Type-safe**: Pydantic strict, SQLAlchemy 2.0 typing
- **Test-driven**: cada endpoint tiene smoke test + validation
- **Backward-compatible**: lo viejo sigue funcionando
- **Documentado**: OpenAPI + docstring + ejemplo curl

## Plan de 8 Frentes

### FASE 1: Arquitectura Base (hoy)
**Fundación multi-sede que todos los features necesitan**

| # | Característica | Archivos | Hrs |
|---|---|---|---|
| 1.1 | Tabla `sedes` con metadata (nombre, dirección, pastor_titular) | models, migration | 0.5 |
| 1.2 | Middleware `inject_sede_context` — detecta sede del usuario | middleware | 0.5 |
| 1.3 | Auditoría cross-sede: `log_id_sede` en logs_auditoria | migration | 0.3 |
| 1.4 | API `/sedes` CRUD (super_admin) + `/mi-sede` (pastores) | api, crud | 1.0 |
| 1.5 | Seed: Sede Central + Sede Norte + Sede Jóvenes | seed | 0.3 |

### FASE 2: Gamificación (hoy-tarde)
**Sistema XP + Insignias + Niveles + Rankings**

| # | Característica | Archivos | Hrs |
|---|---|---|---|
| 2.1 | Tabla `xp_transactions` (persona_id, amount, reason, module) | models | 0.5 |
| 2.2 | Tabla `badges` (name, icon, criteria_json, xp_reward) | models | 0.3 |
| 2.3 | Tabla `persona_badges` (persona_id, badge_id, awarded_at) | models | 0.2 |
| 2.4 | Tabla `levels` (name, min_xp, permissions_unlock) | models | 0.2 |
| 2.5 | XP Engine: award_xp(persona, action, module) | services | 1.0 |
| 2.6 | Badge Engine: check_badges(persona) — evalúa criterios | services | 1.0 |
| 2.7 | API `/gamificacion/perfil` — XP, nivel, insignias | api | 0.5 |
| 2.8 | API `/gamificacion/ranking?tipo=xp&sede_id=X` | api | 0.5 |
| 2.9 | Seed: 12 badges + 5 levels + XP inicial | seed | 0.3 |
| 2.10| Integración: award_xp en asistencia, crear grupo, invitar | hooks | 1.0 |

### FASE 3: Pipeline Kanban Visual (mañana)
**Tablero arrastrable + SLA + predicciones**

| # | Característica | Archivos | Hrs |
|---|---|---|---|
| 3.1 | API `/pipelines/{id}/kanban` — columnas con casos | api | 1.0 |
| 3.2 | Frontend KanbanBoard con drag-drop (@dnd-kit) | component | 2.0 |
| 3.3 | SLA Tracker: badge rojo si caso excede tiempo | component | 0.5 |
| 3.4 | API `/pipelines/stats` — tasas conversión, tiempo promedio | api | 0.5 |
| 3.5 | Predicción simple: "3 casos llegarán a CIERRE esta semana" | services | 0.5 |

### FASE 4: Finanzas Libro Mayor (mañana-tarde)
**Plan de cuentas + conciliación + presupuestos**

| # | Característica | Archivos | Hrs |
|---|---|---|---|
| 4.1 | Tabla `plan_cuentas` (codigo, nombre, tipo, padre_id) | models | 0.5 |
| 4.2 | Tabla `asientos_contables` (fecha, cuenta_id, debe, haber) | models | 0.5 |
| 4.3 | Tabla `presupuestos` (anio, cuenta_id, monto_presupuestado) | models | 0.3 |
| 4.4 | API `/contabilidad/libro-mayor?cuenta=&desde=&hasta=` | api, crud | 1.0 |
| 4.5 | API `/contabilidad/balance` — activo/pasivo/patrimonio | api | 0.5 |
| 4.6 | API `/contabilidad/presupuesto-vs-real` | api | 0.5 |
| 4.7 | Seed: plan cuentas estándar para iglesias | seed | 0.3 |

### FASE 5: Predicción IA (pasado mañana)
**Churn prediction + growth projection**

| # | Característica | Archivos | Hrs |
|---|---|---|---|
| 5.1 | `analytics/risk_scorer.py` — heurísticas de abandono | services | 1.5 |
| 5.2 | API `/analytics/churn-risk?sede_id=X` | api | 0.5 |
| 5.3 | `analytics/growth_projection.py` — regresión lineal | services | 1.0 |
| 5.4 | API `/analytics/growth-projection?sede_id=X` | api | 0.5 |
| 5.5 | Dashboard "Alertas" con tarjetas de riesgo | frontend | 1.0 |

### FASE 6: Eventos + Pagos (pasado mañana)
**Registro + MercadoPago + QR check-in**

| # | Característica | Archivos | Hrs |
|---|---|---|---|
| 6.1 | Extender `agenda_eventos` con: precio, capacidad, publico | migration | 0.5 |
| 6.2 | API `/eventos/{id}/inscripcion` — POST registro | api | 0.5 |
| 6.3 | Integración MercadoPago: preference → pago → webhook | services | 2.0 |
| 6.4 | Generación QR: `qrcode` library, endpoint `/checkin/{token}` | api | 0.5 |
| 6.5 | API `/eventos/{id}/asistentes` — lista con estado pago | api | 0.5 |

### FASE 7: API Pública + Webhooks (día 4)
**OpenAPI + webhook system**

| # | Característica | Archivos | Hrs |
|---|---|---|---|
| 7.1 | Documentación OpenAPI completa (ya existe) | docs | 0.5 |
| 7.2 | Tabla `api_keys` (iglesia_id, key_hash, scopes, activa) | models | 0.3 |
| 7.3 | Middleware `authenticate_api_key` | middleware | 0.5 |
| 7.4 | Tabla `webhooks` (iglesia_id, url, eventos[], secreto) | models | 0.3 |
| 7.5 | `services/webhook_dispatcher.py` — dispacha eventos | services | 1.0 |
| 7.6 | API `/integraciones/api-keys` CRUD + `/webhooks` CRUD | api | 0.5 |

### FASE 8: PWA Offline (día 4-5)
**Service workers + sync queue**

| # | Característica | Archivos | Hrs |
|---|---|---|---|
| 8.1 | Service Worker: cache estático + API caching | public/sw.js | 1.5 |
| 8.2 | IndexedDB sync queue: guarda operaciones offline | lib/offline-queue.ts | 1.5 |
| 8.3 | Botón "Sincronizar" con indicador de pendientes | component | 0.5 |
| 8.4 | Manifest PWA: iconos, nombre, theme_color (ya existe) | manifest.json | 0.2 |
| 8.5 | Push notifications: Firebase Cloud Messaging | services | 1.5 |

---

## TOTAL: ~40 horas de implementación
## Inicio: AHORA — Fase 1.1
