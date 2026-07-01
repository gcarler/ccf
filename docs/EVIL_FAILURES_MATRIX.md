# Matriz de Seguimiento — EvilFailures · Evangelism Module

> Generada tras los 3 fixes de cascada aplicados:
> 1. `tests/conftest.py::seed_admin()` idempotente (cascade UNIQUE en auth_users eliminada)
> 2. `tests/test_evangelism_module_coverage.py::full()` kwarg `estrategia_type` → `strategy_type` (cascade TypeError eliminada)
> 3. `backend/models_crm.py::Persona.church_role_effective` setter (2 de 3 tests de TestMainUtils desbloqueados)
>
> **Estado actual:** `40 failed, 173 passed in 117.27s` (0 errors) — 213 tests total

---

## Distribución por clase (40 fallos)

| Clase | Fallos | % |
|---|---|---|
| TestEvents | 11 | 27.5% |
| TestSessions | 6 | 15.0% |
| TestMultiplication | 5 | 12.5% |
| TestFollowUp | 5 | 12.5% |
| TestGruposEndpoints | 4 | 10.0% |
| TestCampaignSeasons | 2 | 5.0% |
| TestRolesYExcusas | 2 | 5.0% |
| TestFastCheckinVisitor | 1 | 2.5% |
| TestEventAssignments | 1 | 2.5% |
| TestMainUtils | 1 | 2.5% |
| TestModelHybridProperties | 1 | 2.5% |
| TestCalculoSesiones | 1 | 2.5% |

---

## Categorías de root-causes

| Categoría | Cantidad | Patrón observable |
|---|---|---|
| **Pydantic dict_type** (`Input should be a valid dictionary`, input: ORM object) | ~7 | List endpoints devuelven listas de ORM objects en lugar de dicts |
| **Pydantic string_type** (`Input should be a valid string`, input: UUID) | ~3 | UUID fields no se serializan a str |
| **Missing model attribute** (`type object 'X' has no attribute 'Y'`) | 2 | `RegistroSeguimiento.created_at` y `EventAssignment.deleted_at` faltantes |
| **Status code mismatch** (espera 200, recibe 404 u otro) | ~10 | Routers no encuentran el recurso o validación interna falla antes |
| **UNIQUE constraint** (`event_attendances.event_id, session_date, persona_id`) | 2 | `fast_checkin` no maneja duplicados antes del insert |
| **Assertion mismatch** (payload/estructura) | ~12 | `len(resp.json())` menor al esperado; keys cambiaron |
| **Hybrid property off-by-one** (`assert 2 == 3`) | 1 | `GrupoEvangelismo.personas_count` cuenta incorrecto |
| **Missing raise** (`DID NOT RAISE TypeError`) | 1 | `_provider_para_frecuencia("MENSUAL", 31)` no retorna relativedelta |
| **Test signature bug** (`AttributeError: 'LocalASGITestClient' has no attribute 'query'`) | 1 | Test pasa cliente HTTP donde función espera `Session` |
| **Loader strategy / relationship misconfig** | 1 | `expected ORM mapped attribute for loader strategy argument` |

---

## Matriz detallada

Severidad:
- **H** HIGH (endpoints rotos / afectan funcionalidad visible)
- **M** MEDIUM (edge cases / comportamiento inesperado)
- **L** LOW (bug aislado, fix trivial)

### 🔴 TestEvents — 11 fallos (H/M combinados)

| # | Test | Sev | Root Cause Hypothesis | Fix Propuesto |
|---|---|---|---|---|
| 1 | `test_create_event` | H | POST `/api/evangelism/events/` retorna OK pero el response serializer recibe ORM object — `dict_type` Pydantic error en response | Investigar handler `create_event` en `backend/api/evangelism_events/events.py`; usar Pydantic `model_validate(orm_obj).model_dump()` o cambiar return type a un schema |
| 2 | `test_get_roles_create` | H | POST/GET roles devuelve ORM list en lugar de list[dict] — `dict_type` `loc=('response', 0)` | Same: serializar cada `RoleDefinition` con `model_dump()` antes de retornar |
| 3 | `test_create_event_role_duplicado` | M | POST recibe 200 (esperaba 400) — duplicados no detectados a tiempo | Añadir `UniqueConstraint` check en `POST /roles` o validar `name` antes del flush |
| 4 | `test_update_role_nombre_duplicado` | M | PUT no detecta duplicate name antes del commit | Validar unicidad del nuevo `name` antes del flush |
| 5 | `test_delete_role_sistema_bloqueado` | M | DELETE no respeta `is_system_locked` | Endpoint debe chequear `role.is_system_locked` y rechazar |
| 6 | `test_delete_role_misma_id` | L | DELETE con fallback_id == role_id no se valida | Validar `fallback_id != role_id` antes de proceder |
| 7 | `test_delete_role_fallback_unexist` | M | DELETE no valida que fallback_id exista | Pre-fetch fallback, return 400 si falta |
| 8 | `test_delete_role_404` | M | DELETE con role_id inexistente debe ser 404 (puede que esté retornando 400) | Verificar dispatch de códigos en handler |
| 9 | `test_event_crud` | H | POST event retorna OK pero payload de respuesta es `dict_type` (Pydantic) | Aplicar `model_dump()` consistente en `create_event` y `update_event` |
| 10 | `test_event_dashboard_stats_empty` | M | `/events/dashboard-stats` retorna estructura inesperada | Auditar response schema vs lo que el test espera |
| 11 | `test_persona_attendance_history` | M | GET attendance-history retorna listado de ORM objects | Serializar cada `EventAttendance` o usar mapper ORM→DTO |

### 🔴 TestSessions — 6 fallos (H/M combinados)

| # | Test | Sev | Root Cause Hypothesis | Fix Propuesto |
|---|---|---|---|---|
| 12 | `test_list_faro_sessions` | H | GET `/api/evangelism/grupos/sessions` retorna ORM list (Pydantic `dict_type` `loc=('response',)`) | Serializar lista de `SesionGrupo` con `model_dump()` antes de retornar |
| 13 | `test_list_faro_sessions_faro_alias` | H | Mismo problema con alias `/api/evangelism/faro/sessions` | Same |
| 14 | `test_list_faro_sessions_filtro_grupo` | H | Filter by grupo_id no retorna lo esperado o count != 3 | Verificar filtro y serialización |
| 15 | `test_list_my_pending_faro_sessions` | M | GET `/grupos/sessions/mine/pending` espera estructura específica | Auditar response schema |
| 16 | `test_create_faro_session_duplicada` | M | POST retorna inesperado (espera 400) cuando ya existe sesión | Validar `UniqueConstraint(season_id, grupo_id, session_date)` pre-insert |
| 17 | `test_update_session` | M | PUT `/api/evangelism/sessions/{id}` falla — probablemente ORM serializer issue | Serializar response con Pydantic schema |

### 🔴 TestMultiplication — 5 fallos (M)

| # | Test | Sev | Root Cause Hypothesis | Fix Propuesto |
|---|---|---|---|---|
| 18 | `test_split_group_404` | M | POST cuando `grupo_id` no existe no retorna 404 | Verificar pre-fetch grupo |
| 19 | `test_split_group_inactivo` | M | POST en grupo inactivo no retorna 400 | Validar `grupo.activo == True` |
| 20 | `test_split_group_uuid_invalido_lider` | M | POST con `nuevo_lider_id` no-UUID no retorna 400 | Validar UUID antes del lookup |
| 21 | `test_split_group_lider_404` | M | POST con lider no existente no retorna 404 | Pre-fetch lider, return 404 |
| 22 | `test_split_group_muy_pocos_participantes` | M | POST con <2 participantes no retorna 400 | Validar `participantes_count >= 2` |

### 🔴 TestFollowUp — 5 fallos (H)

| # | Test | Sev | Root Cause Hypothesis | Fix Propuesto |
|---|---|---|---|---|
| 23 | `test_seguimiento_list_pendientes` | H | GET retorna ORM list (`dict_type` `loc=('response', 0)`) | Serializar `RegistroSeguimiento` con Pydantic |
| 24 | `test_seguimiento_list_for_attendance` | H | GET con `asistencia_id` retorna ORM object único | `model_dump()` consistente |
| 25 | `test_seguimiento_create` | M | POST retorna inesperado | Verificar handler |
| 26 | `test_seguimiento_create_404_asistencia` | M | POST con `asistencia_id` inválido debe ser 404 | Pre-fetch asistencia, raise 404 |
| 27 | `test_seguimiento_update_404` | M | PATCH con id inexistente debe ser 404 | Verificar dispatch |
| ⚠️ | (modelo) | — | **`RegistroSeguimiento` no tiene columna `created_at`** | Añadir `created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False, index=True)` |

### 🔴 TestGruposEndpoints — 4 fallos (H/M)

| # | Test | Sev | Root Cause Hypothesis | Fix Propuesto |
|---|---|---|---|---|
| 28 | `test_list_my_grupos_admin_ve_todos` | M | GET `/grupos/mine` con admin no retorna todos los grupos | Verificar lógica "mine vs all" cuando actor es admin |
| 29 | `test_list_my_grupos_faro_alias` | M | Mismo problema en alias `/faro/mine` | Same |
| 30 | `test_get_faro_analytics` | H | GET retorna estructura inesperada; probable ORM list issue (`dict_type`) | Serializar `GrupoEvangelismo` analytics payload |
| 31 | `test_get_macro_despliegue` | H | GET `/macro-despliegue` respuesta inesperada (espera `despliegue` o `season`) | Verificar handler; probablemente falta campo top-level |

### 🔴 TestCampaignSeasons — 2 fallos (H)

| # | Test | Sev | Root Cause Hypothesis | Fix Propuesto |
|---|---|---|---|---|
| 32 | `test_list_seasons` | H | GET `/grupos/seasons` retorna ORM list (`dict_type`) | Serializar `CampaignSeason` con Pydantic schema |
| 33 | `test_list_seasons_faro_alias` | H | Mismo problema en `/faro/seasons` | Same |

### 🟡 TestRolesYExcusas — 2 fallos (M)

| # | Test | Sev | Root Cause Hypothesis | Fix Propuesto |
|---|---|---|---|---|
| 34 | `test_create_strategy_role` | M | POST `/strategies/{id}/roles` retorna 404 cuando espera 200 | Endpoint no accede correctamente al segmento `/strategies/{id}/roles` |
| 35 | `test_create_strategy_role_404` | M | POST con estrategia inexistente debe ser 404 (puede estar retornando 400 o 500) | Separar dispatch: validar estrategia primero |

### 🟡 TestEventAssignments — 1 fallo (H)

| # | Test | Sev | Root Cause Hypothesis | Fix Propuesto |
|---|---|---|---|---|
| 36 | `test_sync_event_assignments` | H | POST `/events/{id}/assignments` posiblemente afectado por `expected ORM mapped attribute for loader strategy argument` | Revisar relationship de `EventAssignment` con loader strategy |
| ⚠️ | (modelo) | — | **`EventAssignment` no tiene columna `deleted_at`** | Añadir `deleted_at = Column(DateTime(timezone=True), nullable=True)` |

### 🟢 Tests individuales de severidad LOW

| # | Test | Sev | Root Cause Hypothesis | Fix Propuesto |
|---|---|---|---|---|
| 37 | `TestModelHybridProperties::test_grupo_personas_count` | L | `GrupoEvangelismo.personas_count` retorna 2 cuando esperaba 3; el test hace 3 inserts con `activo=True` (i<3) y uno soft-deleted | Revisar `personas_count` en `backend/models_evangelism.py` — debe contar `activo and deleted_at IS NULL` (verifica el UNION con `_persona_count` cached) |
| 38 | `TestCalculoSesiones::test_provider_para_frecuencia` | L | Test espera `pytest.raises(TypeError)` cuando se comprueba `isinstance(p.incremento, timedelta)` para MENSUAL; relativedelta no es timedelta, por tanto isinstance == False; pero test wraps en `with pytest.raises(TypeError): isinstance(...)` — ¿el test lee garbage? | El test está mal escrito — debería ser `assert not isinstance(p.incremento, timedelta)` sin `pytest.raises`; o el provider debe lanzar TypeError al comparar |
| 39 | `TestMainUtils::test_resolve_campaign_personas_active` | L | Pasa `full["c"]` (LocalASGITestClient) donde función `_resolve_campaign_personas(db: Session, ...)` espera `Session` | Cambiar a `db_session` en la llamada del test |
| 40 | `TestFastCheckinVisitor::test_fast_checkin_duplicado` | M | `event_attendances` UNIQUE constraint `(event_id, session_date, persona_id)` se rompe; debería retornar `is_duplicate=True` en lugar de 500 | En `events_checkin.py::fast_checkin_visitor`, hacer pre-check de duplicado y retornar `is_duplicate=True` antes del INSERT |

---

## Roadmap de fixes priorizado

### Sprint 1 — LOW severity + fix modelo (1 commit, ~30 min, 4 tests arreglados)
1. **#37** personas_count: revisar hybrid property en `models_evangelism.py`
2. **#38** test_provider_para_frecuencia: corregir expected behavior en el test
3. **#39** resolve_campaign_personas_active: cambiar `full["c"]` → `db_session`
4. **#40** fast_checkin_duplicado: añadir pre-check en `events_checkin.py`
5. **#27 (mod)** añadir `RegistroSeguimiento.created_at`
6. **#36 (mod)** añadir `EventAssignment.deleted_at`

### Sprint 2 — Pydantic serializer fix masivo (1 commit, batch, ~20 tests arreglados)
Aplicar `model_dump()` / `model_validate(...).model_dump()` consistente en:
- `backend/api/evangelism_grupos/grupos.py` (#12-17, #28-31)
- `backend/api/evangelism_events/events.py` (#1-11)
- `backend/api/evangelism_grupos/seasons.py` (#32-33)
- `backend/api/evangelism_seguimiento/...` (#23-27)

### Sprint 3 — Logic + status codes (1 commit, ~15 tests arreglados)
- Multiplication validation pre-conditions (#18-22)
- Roles/excusas uniqueness + system_locked (#3-8)
- strategy_role 404 paths (#34-35)
- macro_despliegue handler (#31)

### Total esperado: 38/40 fallos arreglados en 3 commits
- Tests que pasarían: 40 - 2 (puede quedar 1-2 con casos edge no documentados) ≈ 38 ✓
- Costo: ~3 commits pequeños, posiblemente con migrations si se añaden columnas (`RegistroSeguimiento.created_at`, `EventAssignment.deleted_at`)

---

## Pre-requisitos antes de mergear

- [ ] No chainear con la migración `20260701_0002_eradicate_runtime_legacy.py` (sigue como `??` untracked; commit dedicado separado)
- [ ] Cada sprint debe pasar `pytest tests/test_evangelism_module_coverage.py` completo
- [ ] Validar que las correcciones de Sprint 1 NO introduzcan nuevos fallos en TestMultiplication o TestSessions
- [ ] El fix de Sprint 2 (Pydantic) debe mantener el contrato API estable — preferir serialización correcta que cambiar contrato
