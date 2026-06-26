# Arquitectura Impecable CCF

**Fecha:** 2026-06-04
**Estado:** Hoja de ruta operativa
**Base obligatoria:** `docs/PROTOCOLO_CAMBIOS_SEGUROS_CCF.md`

---

## 1. Definicion Operativa

La arquitectura CCF se considera impecable cuando cumple simultaneamente:

1. La plataforma levanta con `./startccf` y se apaga con `./stopccf`.
2. El quality gate pasa completo.
3. Las reglas CCF pasan sin excepciones nuevas.
4. La deuda compat restante esta inventariada, protegida y asociada a una migracion o refactor reversible.
5. Ningun cambio funcional se mezcla con migraciones amplias, auth/RBAC o renombrados masivos.
6. Toda identidad de persona y toda entidad transaccional nueva usa UUID, no enteros.

---

## 1.1 Regla UUID Innegociable

La arquitectura objetivo de CCF usa UUID.

Reglas:

- `personas.id` es la identidad canonica de una persona.
- Todo `persona_id` representa un UUID y en TypeScript/Pydantic debe tratarse como `string`.
- Toda FK que represente una persona debe apuntar a `personas.id`.
- No se crean nuevas FKs a `users.id` para representar personas.
- No se crean nuevas PK `Integer` en entidades transaccionales.
- `users.id` entero solo puede existir como compatibilidad de autenticacion compat, no como identidad ministerial ni pastoral.

Las referencias actuales a enteros (`users.id`, `persona_id` como entero, PK/FK compat) son deuda temporal protegida. No son excepciones arquitectonicas permanentes.

Migrarlas requiere:

1. inventario de tablas y endpoints dependientes;
2. columna UUID temporal;
3. backfill con JOIN contra la relacion historica;
4. validacion de cero huerfanos;
5. cambio de constraints;
6. rollback documentado;
7. smoke test de login, perfiles y modulos afectados.

Prohibido eliminar una columna entera compat antes de completar y verificar el backfill UUID.

---

## 2. Gate Actual Obligatorio

Ejecutar antes de cerrar cualquier lote arquitectonico:

```bash
python3 scripts/auditing/quality_gate.py
```

El gate cubre:

- smoke/auth backend;
- tests de dominio academy/CRM;
- contratos estructurales;
- reglas CCF;
- typecheck frontend;
- indices logicos criticos;
- existencia de vistas principales;
- compilacion del motor de automatizacion.

---

## 3. Estado Medido Inicial

Auditoria del 2026-06-04 — commit `31774b6` (rama `main`, working tree con cambios en curso):

| Area | Resultado |
|---|---:|
| `tests/test_structural_contracts.py` + `tests/test_reglas_plataforma.py` | PASS |
| `scripts/auditing/quality_gate.py` | PASS (commit base) |
| Referencias `db.delete(` en backend | 0 ✔️ erradicado |
| datetime.utcnow() erradicado | 0 |
| `.replace(tzinfo=None)` en backend | 0 ✔️ erradicado |
| FKs compat a `users.id` | 31 (28 activas + 3 DEPRECATED en `models_crm.py`) |
| persona_id: int | 0 |
| `fetch(` directo en frontend sin excepcion | 0 ✔️ erradicado |
| Referencias `Dialog`/`Modal` en frontend | 0 ✔️ resuelto (solo nombres de variables) |
| Texto "MIEMBRO" en UI (debe ser "consolidado") | 0 ✔️ erradicado |

Estos numeros no autorizan correcciones masivas. Sirven para ordenar el saneamiento por puntos.

### Hallazgos resueltos en tanda 2026-06-04 (commit base `31774b6`)

| Hallazgo | Resuelto | Detalle |
|---|---|---|
| 9 tests con 403 en `test_crm_api.py` | ✅ Fix aplicado | `seed_admin_v2` y `seed_user_with_role_v2` ahora crean `auth_users.id == personas.id` |
| Hard delete en `admin.py:939` (`UsuarioRolModulo`) | ✅ Soft delete | `deleted_at` agregado al modelo + migración + filtro en query |
| `datetime.utcnow()` en backend | ✅ 11 reemplazos | 4 archivos: community, proyectos, projects, agenda |
| `fetch()` directo → `apiFetch()` | ✅ 4 reemplazos | useTableView, useAirTable, web-vitals, TaskDetailPanel |
| Métricas documentales desactualizadas | ✅ Actualizadas | FKs 32→31, persona_id:int 0, Dialog/Modal 0 |
| Migracion `deleted_at` para `auth_user_module_roles` | ✅ Creada | `20260604_add_deleted_at_auth_user_module_roles` |
| `_utcnow()` devolviendo datetime naive (viola §2.D) | ✅ 5 arreglados | crud/dashboard, core/permissions, analytics/proactive_ia, api/projects, crud/_utils |
| `.replace(tzinfo=None)` en APIs y CRUDs | ✅ 9 arreglados | finance (2), crud/audit, auth_v3, evangelism_shared, cms, evangelism, crm/_shared, crm/pastoral |
| Texto "MIEMBRO" en UI | ✅ 2 reemplazos | `admin/members/page.tsx` (label), `crm/my-card/page.tsx` (nombre tarjeta) |

### Hallazgos resueltos en tanda 2026-06-04 (bis — post-split evangelism.py)

| Hallazgo | Resuelto | Detalle |
|---|---|---|
| `evangelism.py` monolítico (1080+ líneas) | ✅ Split completado | Estrategias → `evangelism_main/main_estrategias.py`, Roles/Excusas → `main_roles.py`, utils → `main_utils.py`. Endpoints viejos reemplazados por comentario. 4 sub-routers montados. |
| Scanner token sin validación real | ✅ SHA-256 + timing-safe | `/scanner/generate/{persona_id}` con `secrets.compare_digest`. Fix UUID parsing (`.removeprefix` en vez de `.split("-")`). |
| `startccf` sin setsid ni limpiza de PIDs | ✅ `_launch_detached()` | Fallback setsid → double-fork + disown. `trap cleanup_exit EXIT INT TERM`. `.started_pids` file. |
| `stopccf` no verificaba muerte de procesos | ✅ `_kill_with_verify()` | Espera 10s, SIGKILL si persiste. `timeout 3` en lsof. |
| Tests xfail con `strict=True` | ✅ 0 restantes | Todos los xfail tienen `strict=False` o fueron removidos. |
| Tests `test_crm_api.py` 403 en evangelismo/eventos | ✅ Resuelto (en tanda anterior) | Verificado: seeds alineados a `auth_users.id == personas.id`. |

---

## 4. Orden de Saneamiento

### Fase A: Guardrails

- Mantener verde `quality_gate.py`.
- Agregar tests solo cuando bloqueen regresiones nuevas.
- No reducir allowlists sin corregir primero el modulo afectado.

### Fase B: Frontend Seguro

- Reemplazar `fetch()` directo por `apiFetch()` modulo por modulo.
- Separar excepciones validas: rutas Next internas, public register, analytics beacon y uploads form-data.
- Convertir modales reales de crear/editar/ver detalle a drawers.
- No renombrar rutas `members`, `academy`, `evangelism` sin plan de redireccion.

### Fase C: Backend Seguro

- Eliminar hard deletes restantes solo donde exista `deleted_at` o estado equivalente.
- Mantener en cero `persona_id: int` / `person_id: int` en endpoints y schemas.
- Cerrar queries sin `sede_id` solamente cuando el contexto de usuario ya este disponible.

### Fase D: Migraciones Mayores

- FKs compat a `users.id`.
- PK Integer a UUID.
- Alias compat `Member`, `CellGroup`, `Enrollment`, `Project`.
- Rutas ingles/espanol.

Estas tareas requieren inventario, backfill, migracion reversible, smoke test y aprobacion explicita.

Meta de la fase: retirar la dependencia de enteros en identidad ministerial sin perdida de datos y sin romper autenticacion.

---

## 5. Regla de Cierre

Ningun lote arquitectonico se declara terminado sin:

```bash
python3 scripts/auditing/quality_gate.py
./startccf
curl -f http://127.0.0.1:8000/healthz
curl -f http://127.0.0.1:8000/api/system/health
curl -f http://127.0.0.1:3000/
./stopccf
```

Si un comando no puede ejecutarse, se reporta como `NO EJECUTADO` con causa concreta.
