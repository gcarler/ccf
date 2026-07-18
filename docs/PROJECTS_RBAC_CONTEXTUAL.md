# RFC — RBAC Contextual por Proyecto

> **Estado:** Propuesta / Visión de futuro.  
> **Relación con el sistema actual:** Este documento **NO** reemplaza `docs/PROJECTS_RBAC_MATRIX.md` ni `docs/PROJECTS_API_CONTRACTS.md`. Esos documentos siguen siendo la fuente de verdad del comportamiento desplegado hoy. Este RFC describe el modelo de permisos objetivo para el módulo Proyectos una vez que el producto decida migrar de un RBAC de plataforma a un RBAC contextual por proyecto.

---

## 1. Motivación

Hoy el módulo Proyectos hereda roles de **plataforma** (`Administrador`, `Gestor`, `Editor`, `Miembro`) y los mapea a tres permisos de módulo: `projects:read`, `projects:edit`, `projects:manage`.

Esto funciona para una iglesia pequeña, pero escala mal cuando:

- Una misma persona puede ser **Director** en un proyecto y **Participante** en otro.
- Queremos que un **Consultor externo** vea solo los proyectos que se le asignan, sin tener un rol de plataforma.
- Un **Participante** debe poder editar **sus propias tareas** pero no las ajenas.
- El rol en la iglesia (`pastor`, `coordinador`, `miembro`) no debe determinar automáticamente qué puede hacer dentro de un proyecto específico.

> **Principio rector:** En el módulo Proyectos, **no importa el rol en la iglesia, sino la persona y su rol dentro del proyecto**.

---

## 2. Roles contextuales por proyecto

| Rol | Alcance | Descripción |
|---|---|---|
| **Administrador del Sistema** | Global | Superusuario. Acceso total a todos los proyectos y configuraciones. Mantiene el bypass administrativo actual. |
| **Director de Proyecto** | Por proyecto | Dueño de la ejecución del proyecto. Control casi total *dentro* del proyecto asignado. |
| **Participante de Proyecto** | Por proyecto | Ejecutor. Su enfoque es completar el trabajo asignado. |
| **Auditor / Consultor** | Por proyecto | Visor externo. Puede observar y comentar, pero no modificar la estructura principal. |

### 2.1 Diferencia clave con el modelo actual

| Aspecto | Modelo actual (plataforma) | Modelo propuesto (contextual) |
|---|---|---|
| Rol determinado por | `RolPlataforma` del usuario | Membresía en `project_members` |
| Permiso de ejemplo | `projects:edit` | `editar_tarea` sobre tareas propias o asignadas |
| Un usuario puede tener... | Un rol en toda la plataforma | Distintos roles en distintos proyectos |
| Asignación de tareas | Por `persona_id` | Por `persona_id` + validación de permisos contextuales |

---

## 3. Matriz granular de permisos

**Leyenda:** `Sí` = permitido; `No` = denegado; `Propio` = solo registros propios o asignados explícitamente.

| Entidad / Acción | Permiso específico | Administrador | Director | Participante | Auditor/Consultor |
|---|---|:---:|:---:|:---:|:---:|
| **Proyecto** | `crear_proyecto` | Sí | No | No | No |
| | `eliminar_proyecto` | Sí | No | No | No |
| | `ver_proyecto` | Sí | Sí | Sí | Sí |
| | `editar_configuracion` | Sí | Sí | No | No |
| **Equipo** | `gestionar_equipo` | Sí | Sí | No | No |
| **Tareas** | `crear_tarea` | Sí | Sí | No | No |
| | `ver_tareas` | Sí | Sí | Sí | Sí |
| | `editar_tarea` | Sí | Sí | Propio | No |
| | `eliminar_tarea` | Sí | Sí | No | No |
| | `aprobar_tarea` | Sí | Sí | No | No |
| **Documentos** | `subir_documento` | Sí | Sí | Sí | No |
| | `ver_documentos` | Sí | Sí | Sí | Sí |
| | `borrar_documento` | Sí | Sí | Propio | No |
| **Finanzas** | `ver_presupuesto` | Sí | Sí | No | No |
| **Comentarios** | `crear_comentario` | Sí | Sí | Sí | Sí (opcional) |

### 3.1 Notas sobre permisos "Propio"

- `editar_tarea` para un **Participante** significa: puede editar tareas donde él/ella sea `assignee_id` o `created_by`.
- `borrar_documento` para un **Participante** significa: puede borrar documentos que él/ella haya subido.
- La lógica de "Propio" se implementa en **ABAC** (Attribute-Based Access Control) sobre el recurso, no solo en el rol.

---

## 4. Cambios arquitectónicos requeridos

### 4.1 Esquema de base de datos

Se requiere al menos una nueva tabla de membresía por proyecto:

```sql
CREATE TABLE project_members (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES projects(id),
    persona_id UUID NOT NULL REFERENCES personas(id),
    project_role VARCHAR(50) NOT NULL,  -- 'director', 'participant', 'auditor'
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    deleted_at TIMESTAMP,
    UNIQUE(project_id, persona_id)
);
```

Opcionalmente, para soportar permisos granulares extensibles:

```sql
CREATE TABLE project_role_permissions (
    project_role VARCHAR(50) NOT NULL,
    permission VARCHAR(100) NOT NULL,
    PRIMARY KEY (project_role, permission)
);
```

### 4.2 Cambios en el backend

1. **Nuevos guards contextuales:**
   - `require_project_permission(permission: str, project_id: UUID)`
   - `require_project_role(project_id: UUID, allowed_roles: set[str])`
   - `require_owner_or(project_id: UUID, permission: str)` para el patrón "Propio".

2. **Migración de guards actuales:**
   - Reemplazar progresivamente `require_module_access("projects", "read/edit/manage")` por los nuevos guards contextuales.
   - Mantener un **modo compatibilidad** mientras dure la transición.

3. **Nuevos endpoints (propuesta):**
   - `POST /projects/{id}/members` — agregar miembro con rol.
   - `PATCH /projects/{id}/members/{persona_id}` — cambiar rol.
   - `DELETE /projects/{id}/members/{persona_id}` — remover miembro.

### 4.3 Cambios en el frontend

- El `ProjectUpdateContext` debe exponer el rol del usuario **dentro del proyecto actual**.
- Los componentes deben evaluar permisos granulares (`can("editar_tarea")`) en lugar de `hasPermission("projects:edit")`.
- Ocultar/deshabilitar acciones no permitidas en lugar de depender del rol de plataforma.

---

## 5. Plan de transición sugerido

| Fase | Descripción | ID tentativo |
|---|---|---|
| 1. Diseño | Aprobar este RFC, definir ABAC y tablas. | `PEND-RBAC-CONTEXTUAL-001` |
| 2. Modelo de datos | Crear `project_members` y seed de roles. | `PEND-RBAC-CONTEXTUAL-002` |
| 3. Guards contextuales | Implementar helpers de permisos sin activarlos. | `PEND-RBAC-CONTEXTUAL-003` |
| 4. Migración suave | Asignar automáticamente `director` a `Project.owner_id` existentes. | `PEND-RBAC-CONTEXTUAL-004` |
| 5. Activación | Reemplazar guards de plataforma por contextuales en endpoints críticos. | `PEND-RBAC-CONTEXTUAL-005` |
| 6. Deprecación | Eliminar modo compatibilidad y actualizar tests. | `PEND-RBAC-CONTEXTUAL-006` |

---

## 6. Relación con la documentación vigente

| Documento | Rol hoy | Acción recomendada |
|---|---|---|
| `docs/PROJECTS_RBAC_MATRIX.md` | Fuente de verdad del código desplegado | Mantener intacto hasta que se active la Fase 5 |
| `docs/PROJECTS_API_CONTRACTS.md` | Contratos API actuales | Mantener intacto; agregar nuevos endpoints en su momento |
| `docs/PLAN_PROYECTOS_CALIDAD.md` | Plan operativo | Referenciar este RFC como fase futura |
| `docs/ESTADO_PROYECTOS.md` | Estado vivo del módulo | Incluir `PEND-RBAC-CONTEXTUAL-001` en backlog |

---

## 7. Preguntas abiertas

1. ¿El rol **Director de Proyecto** debe poder eliminar el proyecto o solo archivarlo?
2. ¿El permiso `crear_proyecto` debe ser global (solo Admin) o también por sede?
3. ¿El rol **Auditor/Consultor** puede comentar? ¿Puede ver documentos?
4. ¿Cómo se maneja la herencia con roles de plataforma durante la transición?
5. ¿Se requiere audit log de cambios de rol en `project_members`?

---

## 8. Conclusión

Este RFC propone un modelo de RBAC contextual por proyecto que alinea los permisos con la realidad operativa del módulo: **la autoridad en un proyecto depende del rol dentro del proyecto, no del rol en la iglesia**. La implementación es un esfuerzo transversal que afecta backend, frontend, base de datos y tests, por lo que debe ejecutarse por fases y mantener compatibilidad con el modelo actual hasta su completitud.
