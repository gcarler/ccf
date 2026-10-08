# Auditoría del Módulo de Evangelismo — 07/10/2026

**Alcance:** `/api/evangelism/*` (backend FastAPI) y `/plataforma/evangelism` (frontend Next.js 15)
**Método:** Auditoría estática de código + verificación de reglas canónicas CCF + ejecución dinámica de suites de pruebas y linters.
**Superficie auditada:** ~14.700 líneas de backend (24 archivos) + 68 archivos frontend (páginas, drawers, hooks, tests).

---

## 1. Resumen Ejecutivo

El módulo de Evangelismo está en un estado **sólido y maduro**: guards de permisos consistentes, soft deletes, UTC consciente, Kernel de Personas respetado, frontend 100% sobre `apiFetch` con tokens semánticos y Drawers. Las suites de pruebas pasan al 100% y el linter/typecheck están limpios.

Sin embargo, la auditoría detectó **2 vulnerabilidades críticas de aislamiento multi-tenant (Axioma 3)** en los endpoints de cohortes de eventos (`/cohorts/matrix` y `/cohorts/export`), donde el `sede_id` se acepta del cliente sin validación de rol del actor, permitiendo lectura y exportación de datos de otras sedes. Además se detectan 1 hallazgo alto, 3 medios y 4 menores.

| Severidad | Cantidad | Hallazgos |
|-----------|----------|-----------|
| 🔴 Crítico | 2 | Bypass Axioma 3 en `/cohorts/matrix` y `/cohorts/export` |
| 🟠 Alto | 1 | Ranking inter-sedes expuesto a usuarios de solo lectura |
| 🟡 Medio | 3 | Drift de meses en matriz temporal; inconsistencia de valores de `estado`; N+1 en análisis multi-sede |
| 🔵 Menor | 4 | Columna duplicada `is_public`; property stub `season`; `err: any` ×5; estructura `groups/groups/` redundante |

---

## 2. Verificación de Reglas Canónicas (Resultado)

### 2.1 Backend (FastAPI + SQLAlchemy)

| Regla | Resultado | Evidencia |
|-------|-----------|-----------|
| Fechas UTC (`datetime.now(timezone.utc)`) | ✅ Cumple | Cero usos de `datetime.utcnow()` naive en el backend de evangelismo. Los archivos definen helpers conscientes (`backend/api/evangelism_events/events_checkin.py:223` → `datetime.datetime.now(datetime.timezone.utc)`; modelo usa `_utcnow` de `backend/models_shared.py:31` que retorna aware). |
| Borrado físico (`db.delete(`) | ✅ Cumple | **0** llamadas en `backend/api/evangelism*` y `backend/crud/evangelism.py`. Los deletes son soft (`deleted_at = _utcnow()`, ej. `crud/evangelism.py:317,454,578,859,939`). |
| Actor UUID obligatorio | ✅ Cumple | Toda mutación exige actor autenticado vía guards; auditoría con `LogAuditoria.usuario_id` FK a `personas.id`. |
| Axioma 3 (sede del actor) | ⚠️ Parcial | **Cumple en el core** (grupos, sesiones, asistencias, estrategias, scanner). **Falló en cohortes** → Hallazgos F-01/F-02/F-03. |
| Axioma 1 (Kernel de Personas) | ✅ Cumple | `lider_persona_id`, `asistente_persona_id`, `anfitrion_persona_id`, `ParticipanteGrupo.persona_id`, `HistorialEmbudo.persona_id` — todos FK a `personas.id`. Cero tablas paralelas de personas. |
| PKs UUIDv4 | ✅ Cumple | Todas las tablas de `models_evangelism.py` usan `Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)`. |
| Columnas `DateTime(timezone=True)` | ✅ Cumple | Todas las columnas temporales del modelo llevan `timezone=True`. |
| Guards de permisos | ✅ Cumple | 100% de los endpoints auditados usan `require_evangelism_read` / `require_evangelism_manage` / `require_module_access` (22+ dependencias verificadas en `evangelism_events/`, `evangelism_grupos/`, `evangelism_main/`, analytics, rankings, reports, notifications). |
| Scanner QR | ✅ Cumple | `backend/api/evangelism.py`: scoping estricto por sede con 404 anti-enumeración (`_get_scoped_scanner_persona`), token con hash SHA-256 y comparación `secrets.compare_digest`, expiración verificada. |

### 2.2 Frontend (Next.js 15 + React 19)

| Regla | Resultado | Evidencia |
|-------|-----------|-----------|
| `apiFetch` obligatorio | ✅ Cumple | 154+ llamadas vía `apiFetch`/`apiFetchBlob`. **0** usos de `fetch()` crudo en `/plataforma/evangelism`. |
| Tokens semánticos (prohibido color hardcodeado) | ✅ Cumple | **0** matches de clases Tailwind hardcodeadas (`bg-blue-500`, `text-gray-400`, etc.) en los 68 archivos del módulo. |
| Drawers, NO modals | ✅ Cumple | **0** usos de `AlertDialog`, `window.confirm` ni `alert()`. Flujos destrutivos con `ConfirmActionDrawer`, `EventDeleteDrawer`, y paneles laterales (`GroupAddAttendeeDrawer`, `PersonaManagementDrawer`, etc.). |
| Rutas `/plataforma/...` | ✅ Cumple | Todas las páginas bajo `src/app/plataforma/evangelism/`. |
| TypeScript estricto (cero `any`) | ⚠️ Parcial | 5 usos de `catch (err: any)` en `events/[id]/tabs/FollowupTab.tsx` (líneas 75, 107, 148, 184, 217) → Hallazgo F-10. |
| Estados de UI (loader/empty/toast) | ✅ Cumple | Estados de carga y vacíos presentes en las vistas principales auditadas. |

### 2.3 Ejecución Dinámica (evidencia cuantitativa)

| Suite | Resultado |
|-------|-----------|
| Cobertura profunda `tests/test_evangelism_module_coverage.py` | **225 passed** (168.9s), 0 fallos |
| Smoke canónico `scripts/test_evangelism_quality.py` | **7/7 suites passed**, 0 fallos |
| Regresiones Triple 7 / CRM Bridge / Reports / Cálculo Sesiones | **Verdes** (20 passed, 1 xpassed en la última cola; 0 fallos) |
| `npx eslint` (módulo evangelism, `--max-warnings 0`) | **0 errores, 0 warnings** |
| `npx tsc --noEmit` (filtrado a evangelism) | **0 errores** |

---

## 3. Hallazgos Detallados

### 🔴 F-01 (CRÍTICO — Axioma 3) Bypass de tenant en `GET /api/evangelism/events/cohorts/matrix`

**Archivo:** `backend/api/evangelism_events/events_cohorts.py:65-81`

```python
sede_id: Optional[UUID] = Query(None, description="Filtrar por sede específica"),
...
effective_sede = sede_id                      # ← sede del CLIENTE se acepta tal cual
if not effective_sede and getattr(current_user, "sede_id", None):
    if not is_superuser and church_role != "Pastor General":
        effective_sede = current_user.sede_id # ← solo se fuerza si el cliente NO envió sede_id
```

**Problema:** El forzado de la sede del actor solo ocurre cuando el cliente **no** envía `sede_id`. Si un usuario regular (no superuser, no Pastor General) de la sede A envía explícitamente `?sede_id=<id de sede B>`, el endpoint le devuelve la matriz de retención de cohortes de la sede B: **fuga de datos inter-sede**.

**Remediación sugerida:** Resolver la sede SIEMPRE del actor (`require_user_sede_id(db, current_user)`) y usar el parámetro del cliente solo si el actor es superuser/Pastor General; en caso contrario, ignorarlo o responder 403.

---

### 🔴 F-02 (CRÍTICO — Axioma 3) Export CSV de cohortes ignora la sede y exporta TODAS las sedes

**Archivos:** `backend/api/evangelism_events/events_cohorts.py:84-99` y `backend/services/event_cohort_retention_service.py:651-663, 325-443`

```python
# API — sede_id directo del cliente, sin validación de rol:
sede_id: Optional[UUID] = Query(None, description="Filtrar por sede"),
...
csv_content = export_cohort_pastoral_report_csv(db, requesting_sede_id=sede_id)
```

```python
# Servicio — el parámetro se recibe pero JAMÁS se usa:
def calculate_multi_sede_cohort_analysis(db, requesting_user_sede_id=None):
    sedes = db.query(Sede).filter(Sede.es_activa.is_(True), ...).all()  # ← todas las sedes, siempre
```

**Problema doble:**
1. `requesting_sede_id`/`requesting_user_sede_id` se reciben pero nunca filtran nada: el ranking inter-sedes y los KPIs globales se calculan sobre **todas** las sedes.
2. El guard es `require_evangelism_manage` (no `require_pastor_or_admin`), por lo que cualquier coordinador con permiso de gestión de la sede A puede exportar el informe ejecutivo completo con métricas, tamaños de cohorte y retención de **todas** las sedes de la organización.

**Remediación sugerida:** (a) aplicar el filtro de sede del actor dentro de `calculate_multi_sede_cohort_analysis` cuando el actor no sea superuser/Pastor General; (b) elevar el guard a `require_pastor_or_admin` para el alcance multi-sede.

---

### 🟠 F-03 (ALTO) Ranking pastoral inter-sedes expuesto a usuarios de solo lectura

**Archivos:** `backend/api/evangelism_events/events_cohorts.py:52-62` y servicio `event_cohort_retention_service.py:325+`

`GET /cohorts/multi-sede` está protegido solo con `require_evangelism_read`. Expone el ranking de eficiencia pastoral, tasas de bautismo, madurez espiritual y tamaños de cohorte de **todas las sedes** a cualquier usuario con lectura de evangelismo (p. ej., líderes de célula). El parámetro `requesting_user_sede_id` se pasa pero el servicio lo ignora (mismo defecto que F-02, punto 1).

**Remediación sugerida:** Guard `require_pastor_or_admin`, o filtrar la respuesta a la sede del actor.

---

### 🟡 F-04 (MEDIO) Drift de ventanas mensuales en la matriz temporal de cohortes

**Archivo:** `backend/services/event_cohort_retention_service.py:458`

```python
month_dt = (now.replace(day=1) - timedelta(days=i * 30)).replace(day=1)
```

**Problema:** Retroceder en pasos de 30 días y luego recortar al día 1 produce **meses omitidos o duplicados** cuando el desvío acumulado cruza límites de mes (ej.: desde el 1 de marzo, −30 días cae en el 30 de enero → se salta febrero). Con `months_count ≥ 9` (el endpoint acepta hasta 24) la matriz pierde meses reales y reporta cohortes inexistentes. Con el default de 6 meses el desvío es tolerable, pero el bug es latente.

**Remediación sugerida:** Aritmética de calendario real (ej. `dateutil.relativedelta(months=i)` o cálculo año/mes explícito sin `timedelta(days=30)`).

---

### 🟡 F-05 (MEDIO) Valores de `estado` en `Asistencia` inconsistentes con el enum canónico

**Archivo:** `backend/models_evangelism.py:480-510` (setters `status`/`attended`) vs. `EstadoAsistenciaEnum` (líneas 75-79)

`EstadoAsistenciaEnum` define `ASISTIO | FALTO | EXCUSA`, pero los setters escriben un abanico mixto:
- `status` setter: `"FALTO"`, `"primera_vez"` (¡minúsculas, fuera del enum!), `"EXCUSA"`, `"Presente"`.
- `attended` setter: `"Presente"` / `"Ausente"`.

**Problema:** Cualquier consulta SQL que filtre por `estado == 'ASISTIO'` (o `'FALTO'`) no matcheará filas escritas como `"Presente"`/`"Ausente"`, y viceversa. El getter normaliza en Python, pero el dato persistido es heterogéneo → riesgo de métricas divergentes entre reportes que lean la columna cruda (dashboards SQL en `crud/dashboard.py` filtran `ge.activo` y conteos por joins, sensibles a la normalización).

**Remediación sugerida:** Normalizar escritura a los valores del enum (o a un único set canónico documentado) + migración de normalización de datos existentes.

---

### 🟡 F-06 (MEDIO) N+1 severo en el análisis multi-sede de cohortes

**Archivo:** `backend/services/event_cohort_retention_service.py:340-395`

`calculate_multi_sede_cohort_analysis` itera todas las sedes y, por cada sede, consulta **todos** sus eventos y recalcula la retención completa por evento (`calculate_event_cohort_retention(db, ev)`), que a su vez ejecuta más consultas por evento. Con crecimiento de datos (10 sedes × 50 eventos), esto escala a cientos/miles de queries por request, y tanto `/cohorts/multi-sede` como `/cohorts/export` lo invocan.

**Remediación sugerida:** Agregar límite temporal (ej. últimos 24 meses), caché corto, o precomputar métricas agregadas por evento.

---

### 🔵 F-07 (MENOR) Columna `is_public` definida dos veces en `EstrategiaEvangelismo`

**Archivo:** `backend/models_evangelism.py:177` y `:196`

La segunda definición silencia silenciosamente a la primera. No rompe en runtime (SQLAlchemy mapea la última), pero es un código ambiguo que debe limpiarse dejando una sola declaración (idealmente con `index=True` si se consulta por ella en `evangelism_public.py:108,225`).

---

### 🔵 F-08 (MENOR) Property stub `SesionGrupo.season` siempre retorna `None`

**Archivo:** `backend/models_evangelism.py:437-438`

Existe la FK `season_id → campaign_seasons.id`, pero `season` es un `@property` stub que retorna `None` en vez de una `relationship`. Cualquier código que acceda a `sesion.season` recibe silenciosamente `None`.

**Remediación sugerida:** Reemplazar por `relationship("CampaignSeason")` o eliminar el property.

---

### 🔵 F-09 (MENOR) 5 usos de `catch (err: any)` en `FollowupTab.tsx`

**Archivo:** `frontend/src/app/plataforma/evangelism/events/[id]/tabs/FollowupTab.tsx:75,107,148,184,217`

Viola la regla de TypeScript estricto ("cero `any` injustificado"). El resto del módulo usa `ApiError` de `@/lib/http`.

**Remediación sugerida:** Tipar como `catch (err)` + narrowing con `err instanceof ApiError`, siguiendo el patrón del resto de tabs.

---

### 🔵 F-10 (MENOR) Estructura de rutas redundante `evangelism/groups/groups/`

**Archivos:** `frontend/src/app/plataforma/evangelism/groups/groups/*` (page, useGroupsPage, panels)

Anidamiento `groups/groups/` que sugiere una migración incompleta de la página de listado de grupos. Funcional pero confuso para mantenimiento.

**Remediación sugerida:** Mover `groups/groups/*` un nivel arriba (o renombrar el segmento) en un refactor dedicado.

---

## 4. Fortalezas Destacadas

1. **Scanner QR robusto** (`backend/api/evangelism.py`): scoping por sede con 404 que no filtra existencia (anti-BOLA), hash SHA-256 del secreto, comparación en tiempo constante, expiración verificada con normalización tz-defensiva.
2. **Puente CRM Evangelismo → CRM** (`backend/services/evangelism_crm_bridge.py`): uso correcto de `SAVEPOINT` (`db.begin_nested()`) para race conditions en creación de pipelines/etapas, introspección de columnas vivas para compatibilidad de esquema, SLA de 48h en casos nuevos, y contrato `commit=True/False` para transacciones compuestas.
3. **Soft delete consistente** en todo el modelo con `deleted_at` + filtros `is_(None)` en lecturas.
4. **Defensa en profundidad en asistencias**: el endpoint valida la sesión → grupo → sede del actor antes de mutar (`grupos_asistencias.py:400-410`), con snapshot del grupo para auditoría y triggers de automatización + bridge post-commit.

---

## 5. Veredicto

| Dimensión | Calificación |
|-----------|--------------|
| Integridad operativa (grupos, sesiones, asistencias, estrategias) | 🟢 A |
| Seguridad de scanner y guards base | 🟢 A |
| Aislamiento multi-tenant (Axioma 3) | 🔴 **D** (por F-01/F-02/F-03 en cohortes) |
| Calidad de frontend (reglas UI/HTTP/TS) | 🟢 A− (F-09) |
| Pruebas automatizadas | 🟢 A+ (250+ tests verdes) |
| **Global** | **B+ → potencial A+ tras cerrar F-01/F-02/F-03** |

**Prioridad de remediación:** F-01 y F-02 son vulnerabilidades de fuga de datos entre sedes y deben cerrarse **antes** de cualquier despliegue nuevo. F-03 y F-04 en el mismo ciclo. El resto puede agendarse como deuda técnica normal.

---

*Generado por auditoría automatizada el 07/10/2026. Evidencia: ejecución real de suites pytest (225 + 7 suites + regresiones), ESLint 0/0, tsc limpio, y análisis de código con rutas y líneas exactas.*
