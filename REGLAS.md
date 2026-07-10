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

Prohibido crear nuevas tablas paralelas para representar personas como estudiantes, integrantes, lideres, donantes o usuarios ministeriales.

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

### 4.1 Política estricta de ownership y sede

Toda mutación pastoral, administrativa o de contenido exige un actor UUID
canónico. La ausencia, malformación o inexistencia del actor responde 401 y
nunca desactiva los controles multi-tenant.

| Caso | Política |
|---|---|
| Actor ausente o desconocido | REJECT 401 |
| Creator/author no resoluble | REJECT 409 |
| Creator/author sin sede | REJECT 409 |
| Creator/author de otra sede | REJECT 404 |
| UGC con owner o sede NULL | Prohibido por NOT NULL |
| Superadministrador sin sede | Puede leer global; no puede crear UGC sin tenant atribuible |

Workers, seeds e importadores deben ejecutar con una persona de servicio
canónica provista de sede. No existe bypass actor_user_id=None.

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

### 9.1.1 Historia inmutable y runtime limpio

Las migraciones cerradas de mayo de 2026 conservan texto SQL del contrato
retirado porque forman parte de la cadena Alembic desplegada. No se importan,
ejecutan ni consultan desde runtime.

La migración 20260701_0002_eradicate_runtime_legacy.py elimina de bases
rezagadas las funciones y tablas paralelas, normaliza tokens/outcomes antiguos,
purga UGC sin ownership verificable, normaliza etiquetas/prioridades de proyectos,
renombra físicamente `personas.baptism_date` y endurece columnas obligatorias.
El código activo no admite aliases, IDs enteros de persona, payloads dict sin
schema ni bypasses sin actor.
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
