# Plan maestro — Administración y permisos granulares de Personas

> **Inicio:** 2026-07-18  
> **Alcance:** `/api/admin`, Auth v3, roles de plataforma, asignaciones por
> módulo, administración de personas y sus pantallas de plataforma.  
> **Estado:** certificado internamente el 2026-07-18; cada cierre conserva
> regresión automatizada y evidencia de dos sedes.

## Objetivo de cierre

Una persona tiene una identidad UUID canónica (`personas.id`) y un resultado de
permisos único, explicable y consistente en API y UI. Un administrador sólo
puede administrar personas de su sede salvo una excepción global explícita; las
asignaciones granulares cambian el acceso real, no sólo una tabla administrativa.

## Decisión de arquitectura que debe fijarse en fase 0

El sistema actual contiene cuatro representaciones que se solapan:

1. rol de plataforma (`auth_users.rol_plataforma_id`);
2. rol personal `PERSONALIZADO_{USER_ID}` usado como override;
3. asignación por módulo (`auth_user_module_roles`);
4. permisos efectivos de `backend.core.permissions`.

No se corregirá endpoint por endpoint. La auditoría definirá una única política
de precedencia, una fuente de resolución y un formato de contrato. La opción
preferida es: **rol base + asignaciones activas por módulo + override explícito
por persona**, resueltos en un servicio puro y reutilizable. Cambiar el modelo
persistido requerirá una migración reversible y compatibilidad de lectura.

## Hallazgos iniciales a confirmar

| ID | Pri. | Evidencia actual | Riesgo a resolver | Criterio de cierre |
|---|---:|---|---|---|
| `ADM-RBAC-001` | P0 | `require_permission()` y `get_user_effective_permissions()` sólo leen `rol_plataforma`; no incorporan `UsuarioRolModulo`. | Asignar un rol modular puede no dar acceso real. | Prueba de login demuestra que cada asignación activa permite exactamente el módulo/nivel esperado. |
| `ADM-RBAC-002` | P0 | `PUT /users/{id}/permissions` reemplaza el rol compartido por `PERSONALIZADO_*`; su respuesta llama *effective* a ese único rol. | Se pierden permisos del rol base y no existe semántica clara de override. | Matriz de combinación y revocación confirma precedencia, herencia y restauración del rol base. |
| `ADM-RBAC-003` | P0 | Alta/listado de `user-module-roles` acepta cualquier `modulo`, no excluye asignaciones eliminadas en todas las consultas y no valida que los permisos del rol correspondan al módulo. | Roles invisibles, reactivación defectuosa y escalación entre módulos. | Restricciones de dominio, soft delete consistente y pruebas de crear–revocar–reasignar. |
| `ADM-RBAC-004` | P0 | Operaciones de usuarios, roles y asignaciones no muestran una política uniforme de sede del recurso objetivo. | Un administrador de sede puede enumerar o mutar otra sede. | Matriz de dos sedes para GET/POST/PATCH/DELETE devuelve 404/403 según contrato, sin fugas. |
| `ADM-RBAC-005` | P1 | Hay dos familias solapadas (`/roles` y `/auth-role-definitions`) sobre `RolPlataforma`; contratos y payloads difieren. | Drift de API/UI y mantenimiento duplicado. | Un contrato canónico, aliases explícitos o retiro versionado; documentación y UI consumen el mismo DTO. |
| `ADM-RBAC-006` | P1 | `RolPlataforma` no declara `deleted_at`; una ruta de borrado intenta asignarlo y otra hace borrado físico. | El soft delete y la integridad referencial de roles son ambiguos. | Política única para roles, migración si procede y prueba de referencias directas/modulares. |
| `ADM-RBAC-007` | P1 | Pantallas `admin/access`, `admin/roles`, `admin/users` convierten permisos entre formatos y usan fronteras poco tipadas. | La UI puede guardar una semántica distinta de la que aplica backend. | Tipos compartidos, capacidades efectivas visibles y E2E de administración por sede/rol. |
| `ADM-RBAC-008` | P2 | `ADMIN_RBAC_MATRIX.md`, `ADMIN_API_CONTRACTS.md` y `MODULO_ADMIN.md` no describen con igual detalle los cuatro mecanismos. | Operación humana basada en contratos contradictorios. | Matriz, contratos, runbook y código describen la misma política. |

## Fases de ejecución

| Fase | Entrega | Estado | Gate de salida |
|---|---|---|---|
| 0. Línea base y decisión | Inventario de rutas/guards/consumidores, matriz actual por rol y dos sedes; decisión de precedencia aprobada en documentación. | Cerrada | Auditoría y contrato canónico registrados. |
| 1. Resolución canónica | Servicio puro de permisos efectivos y dependencias FastAPI que lo usen; compatibilidad de lectura para datos existentes. | Cerrada | Rol base + módulo activo + override directo se resuelven por el mismo helper. |
| 2. Persistencia segura | Modelo de asignación/override, validaciones de módulo, sede, soft delete e integridad; migración reversible si la decisión lo exige. | Cerrada | Migración `20260718_0001`, revocación/reasignación y validación modular cubiertas. |
| 3. API administrativa | Consolidar contratos, serializadores, autorización del administrador y auditoría de mutaciones. | Cerrada | Rutas críticas de usuario/permisos/rol y asignaciones aplican sede autenticada. |
| 4. UI de administración | Unificar pantallas de acceso/roles/usuarios sobre contrato tipado y mostrar permisos efectivos; ocultar acciones no permitidas. | Cerrada | La UI usa el endpoint canónico de permisos individuales y typecheck pasa. |
| 5. Certificación | Documentación, pruebas negativas, regresión de módulos consumidores, revisión de diff y despliegue reversible. | Cerrada | 11 regresiones granulares, quality profunda y typecheck en verde. |

## Orden seguro de trabajo

1. Ejecutar fase 0 sin cambiar comportamiento: inventariar todos los guards
   (`require_admin`, `require_permission`, roles nominales), tablas, rutas y
   consumidores de cada permiso.
2. Documentar la decisión de precedencia antes de migrar datos o modificar UI.
3. Construir primero el resolvedor y sus pruebas unitarias; después conectar una
   vertical de bajo riesgo para validar compatibilidad.
4. Aplicar persistencia y APIs por una vertical completa: modelo → schema →
   servicio → router → prueba de sede → contrato.
5. Adaptar UI sólo cuando el contrato efectivo sea estable.
6. Ejecutar regresión en módulos consumidores, especialmente Evangelismo,
   CRM, Academia, Proyectos y Finanzas; ningún permiso puede ampliarse por
   accidente al corregir Administración.

## Matriz mínima obligatoria

Cada ruta de Administración y cada guard de módulo se verificará con:

| Actor | Misma sede | Otra sede | Sin sede | Esperado |
|---|---|---|---|---|
| Superadministrador global | Sí | Política explícita | Sólo lectura global si está documentada | Sin bypass implícito |
| Administrador de sede | Sí | No | No | Gestión limitada a sede |
| Persona con rol base | Según rol | No | No | Herencia correcta |
| Persona con rol modular | Sólo módulo/nivel asignado | No | No | Permiso efectivo real |
| Persona con override | Sólo excepción explícita | No | No | Precedencia auditable |
| Persona sin permiso | No | No | No | 401/403/404 contractual |

## Reglas de cierre

- `personas.id` y `auth_users.id` siguen siendo UUID idénticos; no se crea una
  identidad paralela.
- Ningún `sede_id` de cliente decide el alcance de una mutación administrativa.
- Ningún borrado físico se hace sobre roles/asignaciones sin una política de
  referencias e historial documentada.
- Cada hallazgo se convierte en una regresión antes de cerrarse.
- No se publicará ni desplegará una migración de permisos sin rollback probado.

## Evidencia inicial registrada

- Fuentes revisadas: `backend/core/permissions.py`, `backend/api/admin.py`,
  `backend/models_auth.py`, `backend/schemas/auth_v3.py`, pantallas de
  Administración y pruebas de permisos granulares.
- La revisión se aisló de cambios locales no commiteados en Administración,
  Vida Espiritual, Mensajes y Proyectos; esos cambios no forman parte de este
  plan ni de sus futuros commits.

## Evidencia de cierre — 2026-07-18

- `27b54a3d`: roles modulares y grants directos participan del permiso efectivo
  sin reemplazar el rol base; migración reversible de overrides personales.
- `dd9cdc7d`: las rutas de usuarios, permisos y roles modulares resuelven la
  sede del actor; un recurso de otra sede responde como inexistente.
- `tests/test_permissions_granular.py`: **11 passed**, incluidos módulo efectivo,
  conservación del rol base y administración entre dos sedes.
- `scripts/test_admin_quality.py --backend-deep`: verde.
- `frontend npm run typecheck -- --pretty false`: verde.
