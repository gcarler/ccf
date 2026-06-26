# Migración Compat → v2

## Script principal

`scripts/migrate_compat_to_v2.py`

Script Python standalone que migra datos de tablas compat (PK Integer) a tablas v2 (PK UUID) preservando integridad, relaciones e idempotencia.

---

## Tablas migradas

| Compat               | v2                    | Notas                                           |
|----------------------|-----------------------|-------------------------------------------------|
| `projects`           | `proyectos`           | Genera código WBS; usa DEFAULT_SEDE_ID          |
| `courses`            | `academy_courses`     | Mapeo directo de campos académicos              |
| `enrollments`        | `academy_enrollments` | Resuelve FK `course_id` vía `compat_id_mapping` |
| `users`              | `auth_users`          | PK = `personas.id`; requiere persona canonica previa |
| `roles`              | `auth_roles`          | Mapeo directo nombre → nombre, permisos         |
| `consolidation_cases`| `crm_casos`           | Requiere pipeline por defecto en `crm_pipelines`|
| `cell_groups`        | `grupos_evangelismo`  | Nota: tabla `crm_celulas` no existe en models   |
| `cell_group_sessions`| `sesiones_grupo`      | Nota: tabla `crm_sesiones` no existe en models  |
| `agenda_events`      | `eventos_agenda`      | Rellena campos obligatorios con defaults         |

> **Nota sobre tablas CRM evangelismo:**
> El requerimiento original mencionaba `crm_celulas` y `crm_sesiones` como destino v2, pero dichas tablas/models no existen en el código actual. El script utiliza las tablas canónicas del módulo evangelismo: **`grupos_evangelismo`** y **`sesiones_grupo`** (definidas en `backend/models_evangelism.py`).

---

## Requisitos previos

1. PostgreSQL accesible vía `DATABASE_URL`.
2. Tablas v2 ya creadas (ejecutar migraciones Alembic antes).
3. Tabla `personas` poblada (requerida para migrar `users` → `auth_users`).
4. Al menos un pipeline en `crm_pipelines` con etapas en `crm_etapas_pipeline` (requerido para `consolidation_cases`).
5. Extension `uuid-ossp` o `pgcrypto` disponible en PostgreSQL (para `gen_random_uuid()`).

---

## Variables de entorno

| Variable              | Default                                      | Descripción                              |
|-----------------------|----------------------------------------------|------------------------------------------|
| `DATABASE_URL`        | — (obligatorio)                              | URL de conexión PostgreSQL               |
| `DEFAULT_SEDE_ID`     | `00000000-0000-0000-0000-000000000001`       | UUID de sede para registros sin sede     |
| `DEFAULT_PERSONA_ID`  | `00000000-0000-0000-0000-000000000001`       | UUID de persona para campos obligatorios |
| `DEFAULT_PIPELINE_NAME`| `NUEVOS_VISITANTES`                          | Tipo de pipeline para casos CRM          |

---

## Uso

### Migración en producción

```bash
export DATABASE_URL="postgresql://user:pass@localhost:5432/ccf"
export DEFAULT_SEDE_ID="a1b2c3d4-e5f6-7890-abcd-ef1234567890"
export DEFAULT_PERSONA_ID="b2c3d4e5-f6a7-8901-bcde-f23456789012"

python scripts/migrate_compat_to_v2.py
```

### Modo dry-run (previsualización)

```bash
python scripts/migrate_compat_to_v2.py --dry-run
```

### Batch size personalizado

```bash
python scripts/migrate_compat_to_v2.py --batch-size 500
```

---

## Idempotencia

El script crea automáticamente la tabla **`compat_id_mapping`**:

```sql
CREATE TABLE compat_id_mapping (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tabla VARCHAR(64) NOT NULL,
    compat_id INTEGER NOT NULL,
    v2_id TEXT NOT NULL,
    migrated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    UNIQUE(tabla, compat_id)
);
```

> `v2_id` se define como `TEXT` (no `UUID` estricto) para soportar tablas v2 que aún conserven PK Integer (p. ej. `grupos_evangelismo`, `sesiones_grupo`).

Antes de procesar cada registro, el script consulta esta tabla. Si ya existe un mapeo, el registro se salta. Esto permite ejecutar el script múltiples veces sin duplicar datos.

---

## Manejo de errores

- Si falla un registro individual, se loguea el error y se continúa con el siguiente.
- Al finalizar se imprime un reporte con: total, migrados, fallidos y tablas completadas.
- Las relaciones (FKs) se resuelven a través de `compat_id_mapping` en tiempo de migración.

---

## Dependencias entre tablas

El script ejecuta las migraciones en orden topológico para respetar FKs:

1. `roles` → `auth_roles`
2. `users` → `auth_users`
3. `courses` → `academy_courses`
4. `enrollments` → `academy_enrollments`
5. `projects` → `proyectos`
6. `consolidation_cases` → `crm_casos`
7. `cell_groups` → `grupos_evangelismo`
8. `cell_group_sessions` → `sesiones_grupo`
9. `agenda_events` → `eventos_agenda`

---

## Verificación de sintaxis

```bash
python -m py_compile scripts/migrate_compat_to_v2.py
```

---

## Consideraciones especiales

### `users` → `auth_users`

`auth_users.id` es FK a `personas.id` (ON DELETE CASCADE). Por tanto, el script **no genera un UUID aleatorio** para cada usuario; en su lugar usa una persona canonica existente con el mismo UUID. Si no existe persona vinculada, el usuario se omite con un warning.

### `consolidation_cases` → `crm_casos`

`crm_casos` requiere obligatoriamente `pipeline_id` y `etapa_actual_id`. El script busca el primer pipeline cuyo `tipo` coincida con `DEFAULT_PIPELINE_NAME` (por defecto `NUEVOS_VISITANTES`) y toma su primera etapa. Si no hay pipelines, todos los casos se omiten.

### Soft deletes

Si una tabla compat tiene campo `is_active=False` y la tabla v2 tiene `deleted_at`, el script asigna `deleted_at = now()`. En la práctica, esto se refleja en tablas como `users` y en el flag `activo` → `deleted_at` de `grupos_evangelismo`.

---

## Limpieza post-migración

Una vez verificada la migración, las tablas compat pueden renombrarse (no eliminar de inmediato) para evitar que el ORM las registre accidentalmente:

```sql
ALTER TABLE projects RENAME TO _compat_projects;
ALTER TABLE courses RENAME TO _compat_courses;
ALTER TABLE enrollments RENAME TO _compat_enrollments;
ALTER TABLE users RENAME TO _compat_users;
ALTER TABLE roles RENAME TO _compat_roles;
ALTER TABLE consolidation_cases RENAME TO _compat_consolidation_cases;
ALTER TABLE cell_groups RENAME TO _compat_cell_groups;
ALTER TABLE cell_group_sessions RENAME TO _compat_cell_group_sessions;
ALTER TABLE agenda_events RENAME TO _compat_agenda_events;
```

> En test/dev esto ya lo maneja la migración Alembic `20260602_rename_compat`.
