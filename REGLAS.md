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
| Academy | `academy_core` |
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
rg -n "ForeignKey\\(\"users\\.id\"\\)|personas\\.user_id|models\\.Persona|models_personas|backend\\.auth" backend docs scripts REGLAS.md

source venv/bin/activate
python -m pytest -q -o addopts='' tests/test_structural_contracts.py tests/test_smoke.py
alembic upgrade head

curl -f http://127.0.0.1:8000/healthz
curl -f http://127.0.0.1:3000/plataforma
```
