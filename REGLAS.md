# Reglas de Arquitectura - Plataforma CCF

**Actualizado:** 2026-06-26
**Audiencia:** agentes, desarrolladores backend, frontend y DBAs.

La plataforma CCF se rige por un Kernel de Personas. Cualquier cambio debe preservar identidad UUID, aislamiento por sede, integridad historica y operacion estable.

## 1. Kernel de Personas

`personas.id` es la unica identidad canonica para seres humanos en la plataforma.

```python
# Correcto
persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"))
```

Prohibido crear nuevas tablas paralelas para representar personas como estudiantes, miembros, lideres, donantes o usuarios ministeriales.

## 2. Auth v3

- `auth_users.id` usa el mismo UUID de `personas.id`.
- La autenticacion no se modela como identidad ministerial.
- No se recrean columnas inversas entre personas y autenticacion.
- Los permisos se resuelven por roles de plataforma y roles por modulo.

## 3. Roles

Una persona puede tener simultaneamente:

| Dimension | Tabla |
|---|---|
| Ministerios/oficios | `persona_ministries` |
| Roles de iglesia | `persona_role_assignments` |
| Roles de plataforma | `auth_roles`, `auth_user_module_roles` |

Ninguna dimension reemplaza a otra.

## 4. Aislamiento por Sede

Toda consulta pastoral, ministerial, administrativa o de reporte debe filtrar por `sede_id` cuando el dato pertenezca a una sede.

```python
sede_id = get_user_sede_id(db, current_user.id)
rows = db.query(Persona).filter(Persona.sede_id == sede_id).all()
```

No se acepta confiar en un `sede_id` enviado por el cliente cuando el usuario autenticado ya define su sede.

### 4.1 Politica Orphan — fallback y persona sin sede

El CRUD-layer debe distinguir dos edge cases de "ausencia de sede" y aplicar
politicas explicitas. Cualquier cambio a esta politica debe actualizar
`docs/CIERRE_ARQUITECTURA_CCF.md` y `tests/test_cms_sede_isolation.py` (y
suites equivalentes en messaging) sincronizados.

| Caso | Definicion | Politica | Razon |
|---|---|---|---|
| **Orphan-fallback** (LENIENT) | `resolve_persona_id_for_user(actor) is None` Y `payload.author_persona_id is None` | Heredar `actor_sede` como `row.sede_id`. NO levanta error. | Back-compat con callers legacy (workers async, scripts de seeding, bulk imports) que propagan `actor_user_id` sin FK creator resoluble. |
| **Orphan-persona** (STRICT) | `author_persona_id` resuelve a una `Persona` concreta con `Persona.sede_id is None` | `HTTPException(404)`. NO fallback. | Una `Persona` sin sede es una inconsistencia de datos, no un caso de uso legitimo. Fallback haria el contrato ambiguo entre "persona sin sede" y "actor en sede". |
| **Doble orphan** | actor sin sede (`get_user_sede_id is None`) Y creator FK None | Crear con `row.sede_id = NULL`. Visible solo a superadmins sin sede. | Consistente con `TareaCRM` orphan-guard: sin actor con sede resoluble no hay forma de inferir la sede legitima. |

**Test contractual:** `tests/test_cms_sede_isolation.py::test_crud_create_testimonial_blocks_when_fk_resolves_to_persona_without_sede`
y `test_crud_create_announcement_inherits_actor_sede_for_orphan_fk`
codifican las dos ramas; cualquier regresion aqui es un compromiso de
seguridad multi-tenant.

## 4.2 Cobertura de Sede por Modulo

La columna `sede_id` debe existir toda entidad User-Generated Content (UGC)
expuesta por API admin. Las entidades globales del site faro (CmsSite,
CmsPage, CmsSection, CmsTheme, CmsMenu) son la unica excepcion legitima:
son contenido editorial compartido cross-sede por diseno.

Modulos cubiertos en el cierre v3.0.1: ver tabla en
`docs/ESTADO_ARQUITECTURA_CCF.md` seccion "Cobertura Axioma 3 (Multi-Tenant)".

## 5. Identificadores

- Entidades transaccionales expuestas por API: UUID.
- Catalogos pequenos y cerrados: pueden usar enteros si no representan personas ni recursos transaccionales.
- Ninguna API nueva debe aceptar enteros para identificar personas.

## 6. Datos Protegidos

- No hacer hard delete en `personas` ni entidades pastorales/transaccionales.
- Usar `deleted_at`, `estado`, `is_active` o estados equivalentes.
- Las fechas persistidas usan `DateTime(timezone=True)` o `TIMESTAMP WITH TIME ZONE`.
- El backend persiste en UTC.

## 7. Modulos Canonicos

| Area | Contrato actual |
|---|---|
| Personas | `personas` |
| Auth | `auth_v3`, `auth_users` |
| Academy | tablas `academy_*`, modelo `models_academy_core.py`, API `/api/academy` |
| CRM | `crm_casos` y modelos actuales |
| Evangelismo | `grupos_evangelismo`, `sesiones_grupo`, `asistencias` |
| Proyectos | modelos UUID actuales |
| CMS | page builder y publicaciones actuales |

## 8. Frontend

- Usar `apiFetch` para llamadas al backend de plataforma.
- No crear pantallas espejo para nombres antiguos.
- La UI visible debe usar lenguaje del dominio: personas, participantes, estudiantes, lideres, administradores, segun contexto.
- Los formularios que editan datos personales deben operar sobre el perfil de la persona autenticada o la persona seleccionada con permiso explicito.

## 9. Migraciones

- Una migracion, una intencion.
- Toda migracion debe ser reversible salvo decision documentada y aprobada.
- No recrear columnas retiradas para resolver errores de runtime.
- Ejecutar `alembic upgrade head` antes del despliegue.
- Eliminar scripts manuales de migracion que ya no sean parte del flujo operativo.

### 9.1 Inmutabilidad de Migraciones Cerradas

Las migraciones ya mergeadas a `main` y desplegadas son **memoria historica
inmutable**. NO se editan bajo ninguna circunstancia salvo descubrimiento
de un bug critico con aprobacion explicita del arquitecto y un nuevo
migration que corrija (sin tocar los archivos previos).

### 9.1.1 Calout firmado del cierre v3.0.1

**ESTA ES LA UNICA DEUDA LEGACY TOLERADA EN EL PROYECTO A PARTIR DEL
CIERRE v3.0.1 (2026-07-01).** Las migraciones:

- `alembic/versions/20260524_0024_prod_hardening3.py`
- `alembic/versions/20260524_0025_prod_final.py`

contienen la cadena `CCF-MBR-*` en tokens generados durante el backfill
de mayo-2026. Esa cadena es **memoria del pasado**, no uso vivo del
concepto. La regla REGLAS §1 (personas por UUID) SI se cumple en el
sistema **activo**:

- Ningun modelo, schema, CRUD, fixture, test o endpoint activo usa
  `CCF-MBR-`. Auditado por `tests/test_arquitectura_100pct.py::test_no_legacy_ccf_mbr_in_live_code`.
- Los identificadores `personas.id` son UUID puros en runtime (ver
  `tests/test_structural_contracts.py`).
- Los tokens `CCF-MBR-*` emitidos durante el backfill son columnas
  legacy de **filas historicas no activas**; ya no alimentan endpoints
  ni autenticacion. Auditarlas requeriria correr `alembic` historico
  en una DB de archivo (no en produccion).

**Justificacion de la tolerancia:** reescribir las dos migraciones para
eliminar la cadena `CCF-MBR-` romperia la cadena de migrations que ya
esta deployed en produccion. La alternativa correcta — una migration
correctiva que remplace los tokens en filas activas — no es rentable:
los tokens legacy no son semanticos, no se consultan, no aparecen en
outputs de usuario, y reemplazarlos solo trasladaria la deuda de nombre.

**Reglas derivadas:**

- Cualquier NUEVO uso de `CCF-MBR-` en codigo vivo, tests, fixtures o
  migraciones futuras es **violacion de REGLAS §1** (Kernel de Personas).
  Auditado por `tests/test_arquitectura_100pct.py::test_no_legacy_ccf_mbr_in_live_code`.
- El gate `rg -g '!alembic/versions/*.py'` debe ejecutarse en cada CI run.
- El archivo `tests/test_arquitectura_100pct.py` codifica este check
  como test pytest ejecutable.

### 9.1.2 Procedencia de la quitacion

Para cerrar la queja del usuario ("nada de legacy") en el futuro, si en
algun momento el proyecto decide eliminar incluso este rastro historico,
la ruta correcta es:

1. Crear una nueva migration de **limpieza** (no edita las previas):
   ```sql
   -- 2099-12-31_0001_drop_legacy_member_token_columns
   ALTER TABLE personas_legacy_tokens DROP COLUMN token_ccf_mbr;
   -- (o un equivalente que aplique al modelo de tu epoca)
   ```
2. Crear un script de validacion bajo `tests/` (no bajo `scripts/` —
   ver 9.2) que verifique la ausencia de columnas o datos huérfanos.
3. Una vez deployed y verificado, eliminar las dos migraciones legacy
   de `alembic/versions/` solo si la cadena de migrations no las usa
   (análisis de impacto obligatorio antes).

Esta es la **ruta para eliminar definitivamente** la deuda CCF-MBR. Por
ahora queda firmada como excepcion explicita en el cierre v3.0.1.

### 9.2 Scripts Manuales y Operacionales

Prohibido mantener en `scripts/` archivos cuyo proposito sea validacion
manual, debug one-shot, auditoria ad-hoc, validacion de backfill on
Postgres scratch, etc. Prefijos vetados: `_tmp_`, `_scratch_`,
`_validate_legacy_`. Si surge la necesidad se hace via test pytest o
comando documentado en `docs/RUNBOOK_PRODUCCION.md`.

Cleanup del cierre v3.0.1:
- `scripts/_tmp_validate_backfill_pg.py` → borrado (validacion operacional one-shot).
- `scripts/_tmp_list_routes.py` → borrado (mapeo de paths para test rotation).

Si reaparece un `_tmp_*` el commit debe rechazarse (ver
`tests/test_arquitectura_100pct.py`).

## 10. Checklist Antes de Commit

- [ ] La identidad de personas usa `personas.id`.
- [ ] No se introducen identidades enteras para personas.
- [ ] `sede_id` esta aplicado donde corresponde.
- [ ] No hay hard delete en entidades protegidas.
- [ ] Las fechas persistidas son timezone-aware.
- [ ] Las rutas nuevas usan contratos v3.
- [ ] La prueba proporcional fue ejecutada.
- [ ] La plataforma responde despues del cambio si se toco runtime.

## 11. Verificacion Recomendada

```bash
# 1. Identidad canonica — personas por UUID.
rg -n "ForeignKey\\(.users\\.id.\\)|personas\\.user_id" \
  backend frontend/src tests scripts docs REGLAS.md \
  -g '!alembic/versions/*.py'

# 2. CCF-MBR fuera de migraciones legacy (vigilancia de regresion).
rg -n "CCF-MBR" \
  backend frontend/src tests scripts docs REGLAS.md \
  -g '!alembic/versions/*.py'

# 3. Sin scripts legacy _tmp_ en scripts/.
find scripts -name '_tmp_*' -o -name '_scratch_*'

# 4. Conteo de cobertura multi-tenant — debe ser >= 190 refs.
rg -c 'get_user_sede_id|_scope_|_get_scoped_' backend 2>/dev/null \
  | awk -F: '{s+=$2} END {print s}'

# 5. Validacion funcional minima.
source venv/bin/activate
python -m pytest -q -o addopts='' \
  tests/test_structural_contracts.py \
  tests/test_smoke.py \
  tests/test_cms_sede_isolation.py

alembic upgrade head

curl -f http://127.0.0.1:8000/healthz
curl -f http://127.0.0.1:3000/plataforma
```
