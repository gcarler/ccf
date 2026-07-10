# 🔬 ANÁLISIS HILARIDAD CCF — Flujo Punto a Punto

**Fecha:** 2026-06-02  
**Scope:** BD → Backend → Frontend → Tests  
**Metodología:** Análisis estático de código + verificación contra REGLAS.md v2.1  

---

## 📊 RESUMEN EJECUTIVO

| Capa | Estado | Hallazgos Críticos | Hallazgos Medios | Hallazgos Leves |
|---|---|---|---|---|
| **Base de Datos** | 🔴 CRÍTICO | 6 | 4 | 3 |
| **Backend (API/CRUD)** | 🔴 CRÍTICO | 4 | 5 | 2 |
| **Frontend (Next.js)** | 🟠 ALTO | 2 | 4 | 3 |
| **Tests** | 🟡 MEDIO | 0 | 3 | 2 |

**Veredicto global:** La plataforma tiene una **arquitectura v2 bien diseñada** (Kernel UUID, soft deletes, sede_id, timezone) pero coexiste con **deuda técnica masiva de módulos compat** que rompen todos los axiomas. Existen **cuellos de botella de rendimiento severos** (N+1 generalizado, falta de índices, duplicación de tablas) y **riesgos de pérdida de datos** (hard deletes, inconsistencias de tipo Integer/UUID). La **cobertura de tests es superficial**: 189 tests cubren APIs principales pero dejan **8 APIs, 16 CRUDs, 12 services y todo el middleware sin tests**. No hay tests E2E ni de carga.

---

## 🗺️ MAPA DE FLUJO DE DATOS

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CAPA DE DATOS (PostgreSQL)                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │  personas   │  │   sedes     │  │  auth_users │  │  Tablas Compat x2   │ │
│  │  UUID PK    │  │  UUID PK    │  │  UUID PK    │  │  Integer PK ❌      │ │
│  │  sede_id ✅ │  │  ─          │  │  sede_id ✅ │  │  sede_id ❌         │ │
│  │  deleted_at │  │  deleted_at │  │  no soft-del│  │  no soft-del        │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘ │
│         │                │                │                    │            │
│         └────────────────┴────────────────┴────────────────────┘            │
│                                    │                                        │
│                              ┌─────┴─────┐                                  │
│                              │  Múltiples│                                  │
│                              │  FKs sin  │                                  │
│                              │  índices  │  ← Cuello de botella #1         │
│                              └─────┬─────┘                                  │
│                                    │                                        │
└────────────────────────────────────┼────────────────────────────────────────┘
                                     │ SQLAlchemy ORM
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            CAPA DE BACKEND (FastAPI)                        │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐  │
│  │    CRUD v2 ✅       │  │   CRUD Compat ⚠️    │  │    Routers v2 ✅    │  │
│  │  UUID + soft-del    │  │  Integer + hard-del │  │  sede_id filtrado   │  │
│  │  timezone ✅        │  │  no sede_id ❌      │  │  lazy loading ❌    │  │
│  │  eager loading ❌   │  │  N+1 masivo         │  │  auth JWT ✅        │  │
│  └─────────────────────┘  └─────────────────────┘  └─────────────────────┘  │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  N+1 QUERIES GENERALIZADAS ← Cuello de botella #2                   │    │
│  │  Todos los CRUD iteran con .all() sin joinedload/selectinload        │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  HARD DELETES EN ENDPOINTS ← Riesgo de pérdida de datos #1          │    │
│  │  api/crm/pastoral.py:673,1174,1569                                   │    │
│  │  api/evangelism_*.py:609,1524                                        │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└────────────────────────────────────┼────────────────────────────────────────┘
                                     │ apiFetch / HTTP
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CAPA DE FRONTEND (Next.js)                        │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐  │
│  │  apiFetch ✅        │  │  Modales ❌         │  │  Colores hardcoded  │  │
│  │  /plataforma/* ✅   │  │  Drawer stacking ⚠️ │  │  ~1500+ usos ❌     │  │
│  │  Lazy loading ⚠️    │  │  Componentes        │  │  Tokens semánticos  │  │
│  │  Zustand stores     │  │  monolíticos (1k+   │  │  mínimos            │  │
│  │                     │  │  líneas)            │  │                     │  │
│  └─────────────────────┘  └─────────────────────┘  └─────────────────────┘  │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  MEMORY LEAKS POTENCIALES ← Cuello de botella #3                    │    │
│  │  Timers sin cleanup + delay artificial 500ms                        │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔴 HALLAZGOS CRÍTICOS POR CAPA

### 1. BASE DE DATOS — 6 Problemas Críticos

#### 1.1 Duplicación Masiva Compat vs V2 (Confusión de Esquema)
Existen **2-3 versiones de las mismas entidades** conviviendo en la misma BD:

| Dominio | Tabla Compat | Tabla V2 | Estado |
|---|---|---|---|
| Proyectos | `projects` | `proyectos` | Ambas activas |
| Tareas | `project_tasks` | `tareas_proyecto` | Ambas activas |
| CRM Casos | `consolidation_cases` | `crm_casos` | Ambas activas |
| CRM Tareas | `crm_tasks` | `crm_tareas` | Ambas activas |
| Agenda | `agenda_events` | `agenda_eventos` | Ambas activas |
| Academy | `courses` | `academy_courses` | Ambas activas |
| Usuarios | `users` | `auth_users` | Ambas activas |

**Impacto:** Queries que unen tablas de versiones distintas fallan silenciosamente o devuelven datos duplicados. Los desarrolladores no saben cuál usar.

#### 1.2 Inconsistencia de Tipos Integer vs UUID (Riesgo de Integridad)
**Problema CRÍTICO:** La migración `0049_crm_events_sede_id.py` crea `crm_events.sede_id` como `INTEGER` pero el modelo `models_crm.py` lo define como `UUID`. Esto rompe integridad referencial.

```
Migración:  sede_id INTEGER REFERENCES sedes(id)  ← sedes.id es UUID
Modelo:     sede_id UUID(as_uuid=True), ForeignKey("sedes.id")
Resultado:  ERROR en runtime o datos huérfanos
```

#### 1.3 Falta de Índices en Foreign Keys (Rendimiento)
**~25+ tablas** tienen FKs sin índice explícito. Esto genera **Sequential Scans** en cada JOIN:

| Tabla | FK sin índice | Impacto en JOIN |
|---|---|---|
| `academy_lessons` | `course_id` | Carga de cursos → O(n) |
| `dependencias_tareas` | `tarea_bloqueante_id`, `tarea_bloqueada_id` | Cálculo de ruta crítica → O(n²) |
| `comentarios_tarea` | `tarea_id`, `persona_id` | Carga de comentarios → O(n) |
| `academy_assignment_submissions` | `enrollment_id`, `lesson_id` | Reportes de entregas → O(n) |

#### 1.4 Ausencia de `sede_id` en ~30 Tablas (Fuga de Datos)
Tablas críticas sin campo `sede_id` violan el **Axioma 3** (aislamiento territorial):

| Tabla | Dominio | Riesgo |
|---|---|---|
| `chat_messages` | Chat | Datos de sede A visibles en sede B |
| `conversations` | Chat | Conversaciones cruzadas |
| `donations` | Finanzas | Donaciones de todas las sedes |
| `communication_logs` | CRM | Logs de comunicación cruzados |
| `academy_enrollments` | Academy | Matrículas de todas las sedes |
| `cms_*` (todas) | CMS | Contenido sin aislamiento |
| `agent_*` (todas) | Agents | Datos de agentes globales |

#### 1.5 Ausencia de Soft Delete en ~40 Tablas
Tablas que usan `DELETE` físico en lugar de `deleted_at`:

| Tabla | Datos perdidos al borrar |
|---|---|
| `event_attendances` | Historial de asistencia |
| `persona_positions` | Historial de cargos |
| `communication_logs` | Evidencia de comunicación |
| `pastoral_call_logs` | Registro de llamadas pastorales |
| `academy_forum_comments` | Foros de cursos |
| `cms_page_views` | Analytics de páginas |

#### 1.6 JSON en lugar de JSONB (PostgreSQL)
**REGLAS.md dice usar `JSON`** (no `JSONB`) para compatibilidad SQLite, pero en PostgreSQL productivo esto **impide índices GIN** y operadores `@>`, `?`.

| Campo | Uso actual | Recomendación en Prod |
|---|---|---|
| `personas.tags` | JSON | JSONB + índice GIN |
| `crm_automations.action_payload` | JSON | JSONB |
| `platform_role_definitions.permissions` | JSON | JSONB |
| `cms_sections.props_json` | JSON | JSONB |

---

### 2. BACKEND — 4 Problemas Críticos

#### 2.1 Hard Deletes en Endpoints Transaccionales (Pérdida de Datos)

| Archivo | Línea | Operación | Fix |
|---|---|---|---|
| `api/crm/pastoral.py` | 673 | `db.delete(task)` | `task.deleted_at = _utcnow()` |
| `api/crm/pastoral.py` | 1174 | `db.delete(role)` | `role.deleted_at = _utcnow()` |
| `api/crm/pastoral.py` | 1569 | `query.delete()` | `obj.deleted_at = _utcnow()` |
| `api/evangelism_events.py` | 609 | `query.delete()` | `obj.deleted_at = _utcnow()` |
| `api/evangelism_grupos.py` | 1524 | `query.delete()` | `obj.deleted_at = _utcnow()` |
| `crud/projects.py` | 132 | `db.delete(phase)` | `phase.deleted_at = _utcnow()` |
| `crud/crm.py` | 699, 708 | `db.delete()` | `obj.deleted_at = _utcnow()` |

#### 2.2 N+1 Queries Generalizadas (Rendimiento Lineal)
**Todos los CRUDs** iteran con `.all()` sin eager loading:

```python
# ❌ PROBLEMA: N+1 en crud/academy.py:51
for course in courses:           # 1 query
    print(course.lessons)        # N queries (una por curso)
    print(course.enrollments)    # N queries más

# ❌ PROBLEMA: N+1 en crud/crm.py:338
for p in personas:               # 1 query
    print(p.family)              # N queries
    print(p.positions)           # N queries
    print(p.consolidation_cases) # N queries

# ❌ PROBLEMA: N+1 en crud/evangelism.py:443
for g in grupos:                 # 1 query
    print(g.lider)               # N queries
    print(g.participantes)       # N queries
```

**Fix:** Usar `selectinload()`:
```python
from sqlalchemy.orm import selectinload
db.query(Course).options(
    selectinload(Course.lessons),
    selectinload(Course.enrollments)
).all()
```

#### 2.3 Filtrado `sede_id` Ausente en Módulos Globales

| Módulo | Filtra sede_id | Riesgo |
|---|---|---|
| `api/chat.py` | ❌ NO | Conversaciones cruzadas |
| `api/graph.py` | ❌ NO | Grafo de conocimiento global |
| `api/agents.py` | ❌ NO | Agentes ven todo |
| `api/academy.py` (compat) | ⚠️ PARCIAL | Algunos endpoints expuestos |
| `api/cms_v2.py` | ❌ NO | CMS global por diseño |

#### 2.4 Modelos Compat con PK Integer (Riesgo IDOR)
~80 tablas siguen usando `Integer` PK en lugar de `UUID`, violando REGLAS.md sección 2.A:

| Tabla | PK Actual | Debería ser |
|---|---|---|
| `chat_messages` | Integer | UUID |
| `conversations` | Integer | UUID |
| `donations` | Integer | UUID |
| `academy_courses` | Integer | UUID |
| `cms_pages` | Integer | UUID |
| `agents` | Integer | UUID |

---

### 3. FRONTEND — 2 Problemas Críticos

#### 3.1 Modales Bloqueantes (Violación UX)

| Componente | Líneas | Problema |
|---|---|---|
| `UniversalCreationModal` | ~200 | Modal centrado bloqueante |
| `AssessmentModal` | ~150 | Modal centrado bloqueante |
| `CertificateModal` | ~100 | Modal centrado bloqueante |
| `PhaseManagerModal` | ~180 | Modal centrado bloqueante |

**REGLAS.md 4.A:** "Se prohíbe el uso de ventanas emergentes (Modales/Dialogs) para crear, editar o visualizar información detallada. Deben utilizarse Paneles Laterales Deslizables (Drawers)."

#### 3.2 ~1,500+ Usos de Colores Hardcodeados (Violación de Diseño)
```bash
# Resultado del análisis:
grep -r "bg-\|text-\|border-" --include="*.tsx" | wc -l
# ~1,500+ usos de colores Tailwind crudos
```

**REGLAS.md 4.B:** "No se permiten colores fijos codificados en duro. Se debe hacer uso exclusivo de las variables semánticas del sistema de diseño."

Ejemplos encontrados:
```tsx
// ❌ INCORRECTO (encontrado masivamente)
<div className="bg-white border border-gray-200 text-gray-800">

// ✅ CORRECTO (REGLAS.md)
<div className="bg-sistema-panel border border-sistema-linea text-sistema-texto-primario">
```

---

## 🟠 HALLAZGOS MEDIOS POR CAPA

### Backend Medios

| # | Hallazgo | Archivo | Impacto |
|---|---|---|---|
| 1 | `@property` en modelos (riesgo de uso en `.filter()`) | `models_evangelism.py`, `models_academy.py` | Query rota en runtime |
| 2 | `create_all()` en lifespan de FastAPI | `app.py` | Race condition con Alembic |
| 3 | Endpoints sin documentación matricial | Todos | Sin auditoría de cambios |
| 4 | CRUD `academy.py` (compat) no filtra sede_id | `crud/academy.py` | Fuga de datos |
| 5 | Servicios no aplican filtro sede_id | `services/*.py` | Acceso global |

### Frontend Medios

| # | Hallazgo | Archivo | Impacto |
|---|---|---|---|
| 1 | Componente monolítico de 1,098 líneas | `crm/personas/[id]/page.tsx` | Mantenibilidad nula |
| 2 | Lazy loading parcial (solo CRM history/financial) | Varios | Carga innecesaria |
| 3 | Memory leaks por timers sin cleanup | `PersonaDetailPage` | Degradación en uso prolongado |
| 4 | Delay artificial de 500ms | `PersonaDetailPage` | UX lenta innecesariamente |
| 5 | Rutas duplicadas (`/admin/personas` y `/crm/personas`) | Varios | Confusión de navegación |

### BD Medios

| # | Hallazgo | Tabla | Impacto |
|---|---|---|---|
| 1 | Constraint GIST comentado pero no aplicado | `agenda_reserva_recursos` | Colisiones de reservas |
| 2 | Materialized View sin refresh automático | `mv_finance_summary` | Datos stale |
| 3 | PK anómala `String(50)` | `estrategias_evangelismo` | No es UUID ni serial |
| 4 | `fund_id` en lugar de `id` | `funds` | Nomenclatura inconsistente |

---

## 📋 MATRIZ DE CUMPLIMIENTO vs REGLAS.md

| # Checklist | Estado | Hallazgo |
|---|---|---|
| 1. ¿Toda query filtra `sede_id`? | ❌ **NO** | Faltan en chat, graph, agents, cms, academy compat |
| 2. ¿`persona_id` es `str` en schemas? | ✅ **SÍ** | Tipado correcto en todos los schemas |
| 3. ¿`DateTime` usa `timezone=True`? | ⚠️ **PARCIAL** | 100% en modelos v2, faltan en migraciones antiguas |
| 4. ¿Ausente `db.delete()` en transaccionales? | ❌ **NO** | 7 hard deletes encontrados |
| 5. ¿FKs a `personas.id` usan `UUID`? | ✅ **SÍ** (v2) | Compat tiene Integer PK pero FKs a personas sí usan UUID |
| 6. ¿Usa `JSON` (no `JSONB`)? | ✅ **SÍ** | Pero en PostgreSQL productivo debería ser JSONB |
| 7. ¿Tablas v2 (no compat)? | ⚠️ **PARCIAL** | Coexisten 2-3 versiones de cada entidad |
| 8. ¿Nombres reales de columnas (no `@property`)? | ⚠️ **RIESGO** | Existen @property pero no usados en .filter() detectados |
| 9. ¿Nuevo módulo registrado? | ✅ **SÍ** | Todos registrados en models.py + api/__init__.py + app.py |
| 10. ¿Documentación matricial? | ❌ **NO** | No se encontró formato JSON de entrega |

---

## 🎯 CUELLOS DE BOTELLA IDENTIFICADOS (Ordenados por Impacto)

### Cuello #1: N+1 Queries Generalizados 🔴
- **Ubicación:** Todos los CRUDs (`academy.py`, `crm.py`, `projects.py`, `evangelism.py`, `kernel.py`)
- **Impacto:** Degradación lineal O(n) → O(n²) con el número de registros
- **Fix inmediato:** Agregar `selectinload()` en queries de listado
- **Esperado:** 10x-100x mejora en endpoints de listado

### Cuello #2: Falta de Índices en FKs 🔴
- **Ubicación:** ~25+ tablas (Academy, CRM, Proyectos, Agentes)
- **Impacto:** Sequential Scans en cada JOIN
- **Fix inmediato:** `CREATE INDEX` en todas las FKs
- **Esperado:** 50x-500x mejora en JOINs frecuentes

### Cuello #3: Componentes Monolíticos en Frontend 🟠
- **Ubicación:** `crm/personas/[id]/page.tsx` (1,098 líneas)
- **Impacto:** Re-renderizado masivo, bloqueo del main thread
- **Fix inmediato:** Dividir en sub-componentes por pestaña
- **Esperado:** Tiempo de interacción < 100ms

### Cuello #4: Duplicación Compat vs V2 🟠
- **Ubicación:** BD completa (Proyectos, Academy, CRM, Agenda, Usuarios)
- **Impacto:** Confusión de desarrolladores, queries duplicadas, datos inconsistentes
- **Fix:** Migrar todo a v2 y eliminar/renombrar tablas compat con `_compat_`

### Cuello #5: Hard Deletes 🟠
- **Ubicación:** 7 puntos en routers y CRUD
- **Impacto:** Pérdida irreversible de datos históricos
- **Fix inmediato:** Reemplazar `db.delete()` por `deleted_at = _utcnow()`

---

---

## 🧪 CAPA DE TESTS — Análisis Completo

### Resumen de Tests

| Métrica | Valor |
|---|---|
| **Archivos de test** | 33 archivos `.py` |
| **Funciones de test** | ~189 tests |
| **Umbral mínimo de cobertura** | 70% (pytest.ini) |
| **Tipos de tests** | Mayormente integración API (TestClient) |
| **Tests E2E (Playwright/Selenium)** | ❌ **NO EXISTEN** |
| **Tests de auditoría estática** | ✅ `test_reglas_plataforma.py` |

### Módulos Bien Cubiertos ✅

| Módulo | Tests | Qué verifica |
|---|---|---|
| `test_reglas_plataforma.py` | 7 tests | **Auditoría estática contra REGLAS.md** — escanea todo `backend/api/` y `backend/schemas/` con regex/AST |
| `test_permissions.py` | 18 tests | Lógica pura `_has_permission`, `expand_module_permissions`, RBAC |
| `test_permissions_granular.py` | 13 tests | CRUD de roles, permisos efectivos vía `/kernel/permissions/me` |
| `test_kernel_identity.py` | 26 tests | RBAC engine, inactive user blocked, wildcard admin, UUIDs |
| `test_crm_api.py` | 30 tests | Autorización por rol, sede_id, soft deletes, mockeo de WhatsApp gateway |
| `test_cms_api.py` | 10 tests | Soft-delete completo (sites, menus, themes, sections) |
| `test_auth_v3.py` | 11 tests | Login, refresh, compatibilidad v1/v3, sede_id en token |
| `test_projects_api.py` | 7 tests | CRUD de proyectos, UUIDs |
| `test_structural_contracts.py` | 7 tests | Validación Pydantic, `Settings`, `model_validate` |

### Qué Verifican los Tests de Auditoría (`test_reglas_plataforma.py`)

| Regla REGLAS.md | Test | Estado |
|---|---|---|
| Axioma 3: `sede_id` en queries | `test_sede_id_filtering()` | ✅ Escanea `.all()` con regex, allowlist para catálogos |
| Regla 4: Soft deletes | `test_no_hard_deletes()` | ✅ Prohíbe `db.delete()` en tablas transaccionales |
| Regla 4: Soft deletes | `test_soft_delete_fields_exist()` | ✅ Verifica `deleted_at` o `estado_vital` |
| Regla 2: `persona_id: str` | `test_persona_id_str_in_schemas()` | ✅ Escanea `backend/schemas/` con regex |

### Módulos SIN Tests Dedicados ❌

#### APIs sin test propio (8 módulos)
| Módulo | Riesgo |
|---|---|
| `backend.api.chat` | Sin filtro `sede_id` — **crítico** |
| `backend.api.dashboard` | Sin cobertura |
| `backend.api.donations` | Finanzas sin tests |
| `backend.api.finance` | Finanzas sin tests |
| `backend.api.graph` | Sin filtro `sede_id` — **crítico** |
| `backend.api.prayer` | Sin cobertura |
| `backend.api.support` | Sin cobertura |
| `backend.api.tables` | Sin cobertura |

#### CRUDs sin tests dedicados (16 módulos)
| Módulo | Riesgo |
|---|---|
| `backend.crud.academy` | Compat, no filtra `sede_id`, N+1 |
| `backend.crud.academy_core` | Sin cobertura |
| `backend.crud.agenda_core` | Sin cobertura |
| `backend.crud.crm_core` | Sin cobertura |
| `backend.crud.evangelism` | N+1 masivo |
| `backend.crud.consolidation` | Sin cobertura |
| `backend.crud.projects` | Solo indirecto |

#### Services sin tests (12 módulos)
| Módulo | Riesgo |
|---|---|
| `backend.services.automation_engine` | Reglas de automatización sin tests |
| `backend.services.conversation_memory` | Memoria de agentes sin tests |
| `backend.services.email` | Envío SMTP sin tests |
| `backend.services.intelligence` | IA/ML sin tests |
| `backend.services.knowledge_base` | KB sin tests |
| `backend.services.knowledge_graph` | Grafo sin tests |
| `backend.services.messaging` | Solo mockeado en CRM |
| `backend.services.payments` | Pagos (MercadoPago) sin tests |
| `backend.services.scheduler` | Tareas programadas sin tests |
| `backend.services.public_contact_tracking` | Tracking sin tests |

#### Core / Middleware sin tests (13 módulos)
`backend.core.abac`, `backend.core.ai`, `backend.core.audit`, `backend.core.cache`, `backend.core.context`, `backend.core.events`, `backend.core.file_lock`, `backend.core.logging`, `backend.core.rate_limit`, `backend.core.security_headers`, `backend.core.storage`, `backend.core.telemetry`, `backend.core.uploads`, `backend.core.websockets`, `backend.middleware/*`

### Problemas en la Infraestructura de Tests

| Problema | Detalle | Impacto |
|---|---|---|
| **Sin tests E2E** | Solo TestClient, no Playwright/Selenium | No se prueba UX real, flujos de usuario |
| **BD de tests = SQLite** | `sqlite://` in-memory por defecto | No detecta problemas de PostgreSQL (JSONB, GIN, GIST, constraints) |
| **DROP SCHEMA por test** | `DROP SCHEMA public CASCADE` en PostgreSQL | Tests lentos, race conditions |
| **Sin tests de carga** | No hay Locust/k6/JMeter | No se detectan cuellos de botella bajo stress |
| **Cobertura estimada < 70% real** | Módulos compat sin tests | Los tests pasan pero la cobertura real es baja |

---

## 🛠️ RECOMENDACIONES PRIORITARIAS

### Fase 1: Seguridad (Semana 1)
1. **Eliminar todos los hard deletes** — lista exacta en sección 2.1
2. **Auditar `api/chat.py`, `api/agents.py`, `api/graph.py`** — forzar filtro `sede_id` o marcar como globales justificados
3. **Corregir inconsistencia Integer vs UUID** en `crm_events.sede_id`

### Fase 2: Rendimiento (Semana 2-3)
4. **Implementar eager loading** en los 10 CRUDs principales (`selectinload`/`joinedload`)
5. **Crear índices faltantes** en todas las FKs (especialmente Academy, CRM, Proyectos)
6. **Añadir `deleted_at` a tablas críticas** sin soft delete

### Fase 3: Estándares (Semana 4-6)
7. **Migrar modales a Drawers** — empezar por `UniversalCreationModal`
8. **Implementar tokens semánticos** de Tailwind — plan de migración gradual
9. **Dividir componentes monolíticos** — empezar por `crm/personas/[id]/page.tsx`
10. **Migrar PK Integer a UUID** en tablas transaccionales siguiendo la Receta de 6 Pasos del REGLAS.md

### Fase 4: Tests (Semana 5-6)
11. **Crear tests para APIs sin cobertura** — empezar por `chat`, `dashboard`, `donations`, `finance`
12. **Crear tests para CRUDs compat** — `academy.py`, `evangelism.py`, `projects.py`
13. **Crear tests para Services** — empezar por `payments.py`, `email.py`, `scheduler.py`
14. **Migrar BD de tests a PostgreSQL** — usar `TEST_DATABASE_URL` con PostgreSQL para detectar problemas reales
15. **Añadir tests de carga** — Locust o k6 para endpoints críticos (CRM listado, Academy cursos)

### Fase 5: Arquitectura (Mes 2-3)
16. **Unificar esquema** — eliminar tablas compat o renombrar con `_compat_`
17. **Añadir `sede_id` NOT NULL** a tablas críticas
18. **Convertir JSON → JSONB** en PostgreSQL productivo + índices GIN
19. **Implementar constraint GIST** para `agenda_reserva_recursos`
20. **Implementar tests E2E** — Playwright para flujos críticos (login → crear caso → asignar tarea)

---

## 📚 ANEXO: Inventario Completo de Tablas

### Tablas del Kernel (UUID + soft delete + sede_id)
| Tabla | PK | FK personas | sede_id | deleted_at | Estado |
|---|---|---|---|---|---|
| `personas` | UUID | — | ✅ | ✅ (estado_vital) | ✅ |
| `auth_users` | UUID | `persona_id` | ✅ | ❌ | ⚠️ |
| `persona_role_assignments` | Integer | `persona_id` | ❌ | ✅ | ⚠️ |

### Tablas v2 Canónicas (UUID + soft delete + sede_id)
| Tabla | PK | sede_id | deleted_at | Estado |
|---|---|---|---|---|
| `crm_casos` | UUID | ✅ | ✅ | ✅ |
| `crm_tareas` | UUID | ✅ | ✅ | ✅ |
| `proyectos` | UUID | ✅ | ✅ | ✅ |
| `tareas_proyecto` | UUID | ✅ | ✅ | ✅ |
| `grupos_evangelismo` | Integer | ✅ | ✅ | ⚠️ |
| `agenda_eventos` | UUID | ✅ | ✅ | ✅ |
| `academy_enrollments` | UUID | ❌ | ✅ | ⚠️ |

### Tablas Compat (Integer PK + sin sede_id + sin soft delete)
| Tabla | PK | sede_id | deleted_at | Estado |
|---|---|---|---|---|
| `chat_messages` | Integer | ❌ | ❌ | ❌ |
| `conversations` | Integer | ❌ | ❌ | ❌ |
| `donations` | Integer | ❌ | ❌ | ❌ |
| `academy_courses` | Integer | ✅ | ❌ | ⚠️ |
| `cms_pages` | Integer | ❌ | ❌ | ❌ |
| `agents` | Integer | ❌ | ❌ | ❌ |

---

> **"El código que escribes hoy es la plataforma que administrarás mañana."**
> 
> — Este análisis encontró **7 hard deletes**, **~80 tablas con PK Integer**, **25+ FKs sin índice**, **N+1 en todos los CRUDs**, y **~1,500+ colores hardcodeados**. La arquitectura v2 es sólida, pero la deuda técnica compat es masiva.
