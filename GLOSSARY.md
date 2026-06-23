# Glosario Oficial de Términos — Plataforma CCF

**Versión:** 1.0
**Propósito:** Unificar el lenguaje entre backend, frontend, DBAs y agentes de IA.
**Regla de oro:** Si un término no está aquí, usa el que está en la tabla `personas` o pregunta al arquitecto.

---

## 📌 Términos Prohibidos y Sus Reemplazos

| ❌ No usar | ✅ Usar | Razón |
|---|---|---|
| miembro / member (para referirse a una persona) | persona, integrante, participante | Axioma 1: el kernel es de personas, no de membresía |
| usuario (para referirse a un ser humano) | persona | `users` es solo para autenticación; la persona es la entidad real |
| estudiante / alumno (como tabla) | persona con rol B en academy | Axioma 1: no hay tabla `estudiantes`, hay `personas` con enrollment |
| líder (como tabla separada) | persona con rol B de "LIDER" | Axioma 1: el liderazgo es un rol, no una entidad separada |
| Cell Group / Célula | Grupo de Evangelismo | Estandarización del lenguaje |
| Consolidation Case | Caso CRM | Migración v2 completada |
| Project (tabla) | Proyecto | Migración v2 completada |

## 🧍 Personas (El Kernel)

### ¿Qué es una persona?
Cualquier ser humano registrado en el sistema. Su ficha vive en la tabla `personas` con UUID como PK.

### ¿Qué NO es una persona?
- Un `user` (es solo para login — tabla `users` con PK Integer, FK opcional a `personas.id`)
- Un "miembro" (término eliminado)
- Un "estudiante" (es un rol, no una entidad)

### Las 3 Dimensiones de Identidad

| Dimensión | Qué representa | Tabla | Ejemplos |
|---|---|---|---|
| **A — Ministerio** | Llamado espiritual | `persona_ministries` | Pastor, Maestro, Evangelista |
| **B — Rol Iglesia** | Nivel en el embudo | `persona_church_roles` / `persona_role_assignments` | Líder, Servidor, Miembro, Visitante |
| **C — Rol Plataforma** | Permisos de software | `auth_roles` / `auth_user_module_roles` | ADMINISTRADOR, GESTOR, EDITOR, LECTOR |

## 🏠 Grupos y Casas de Gloria

### Grupo de Evangelismo
- **DB:** `grupos_evangelismo`
- **Propósito:** Reunión semanal de discipulado y evangelismo
- **Liderazgo:** `leader_persona_id`, `assistant_persona_id` (FK a `personas.id`)
- **Sesiones:** `sesiones_grupo`

### Grupo Pequeño / Grupo Comunitario
- **DB:** No tiene tabla separada; se maneja como una categoría de `grupos_evangelismo`
- **Propósito:** Comunidad, acompañamiento, crecimiento
- **UI:** Aparece en `/plataforma/community/grupos`

### Casa de Gloria
- **Uso permitido:** Etiqueta pública o pastoral para grupos de evangelismo.
- **Código:** Usar siempre `grupos`, `grupos_evangelismo` o `sesiones_grupo`.

## 🗺️ Rutas de API

| Endpoint | Propósito |
|---|---|
| `/api/grupos` | CRUD de grupos de evangelismo |
| `/api/grupos/mine` | Grupos del usuario autenticado |
| `/api/faro` | Alias compat para `/api/grupos` |
| `/api/faro/mine` | Alias compat para `/api/grupos/mine` |
| `/api/sesiones` | Sesiones de grupos |
| `/api/asistencias` | Asistencias a sesiones |

## 🔄 Mapeo Compat → v2

| Compat (❌) | v2 (✅) |
|---|---|
| `cell_groups` | `grupos_evangelismo` |
| `cell_group_sessions` | `sesiones_grupo` |
| `consolidation_cases` | `crm_casos` |
| `courses` | `academy_courses` |
| `enrollments` | `academy_enrollments` |
| `projects` | `proyectos` |
| `project_tasks` | `tareas_proyecto` |
| `users.id` (como FK de persona) | `personas.id` (UUID) |

## 🏛️ Sedes (Multi-Tenant)

| Término | Significado |
|---|---|
| `sede` | Campus físico o virtual de la iglesia |
| `sede_id` | Filtro obligatorio en toda query (extraído del JWT) |
| Multi-tenant | Los datos de una sede NUNCA se mezclan con otra |

## 🔐 Roles de Plataforma

| Rol | Permisos |
|---|---|
| `ADMINISTRADOR` | Acceso total a todas las sedes y módulos |
| `GESTOR` | Acceso completo a un módulo específico |
| `EDITOR` | Puede crear y editar contenido |
| `LECTOR` | Solo lectura; puede crear/editar sus propios recursos (Owner-Only) |

---

> **"Si no está en el glosario, no lo inventes. Pregunta al kernel."**
> — Arquitectura CCF
