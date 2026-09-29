# Matriz RBAC — Vida Espiritual y Discipulado CCF

**Actualizado:** 2026-09-06 (Auditoría Forense Integral — Certificación 100/100 A+)  
**Estado:** 100% IMPLEMENTADO Y CERTIFICADO ([`docs/AUDITORIA_FORENSE_VIDA_ESPIRITUAL_2026-09-06.md`](./AUDITORIA_FORENSE_VIDA_ESPIRITUAL_2026-09-06.md))

> **Objetivo:** fijar la matriz RBAC operativa del módulo Vida Espiritual y Discipulado contra el código implementado y validado en suites canónicas.

---

## 1. Taxonomía canónica

| Módulo | Acción | Permission key |
|---|---|---|
| `spiritual_life` | `read` | `spiritual_life:read` |
| `spiritual_life` | `edit` | `spiritual_life:edit` |
| `spiritual_life` | `manage` | `spiritual_life:manage` |

Jerarquía:
- `manage → edit → read`
- `edit → read`

---

## 2. Roles canónicos

| Rol | Permisos efectivos en Vida Espiritual |
|---|---|
| `Administrador` | `spiritual_life:manage` (acceso total de gestión y configuración) |
| `Gestor` | `spiritual_life:manage` (acceso total de creación, edición, eliminación y lectura) |
| `Editor` | `spiritual_life:edit` (lectura, actualización y eliminación lógica) |
| `Lector` | `spiritual_life:read` (solo lectura de hitos y progresos) |
| `Miembro` | Acceso a su propia línea de tiempo y certificados (`/spiritual-life/milestones/{user.id}`) |

---

## 3. Matriz por superficie Backend

| Ruta | Guard implementado | Axioma 3 (Sede Isolation) | Observación |
|---|---|---|---|
| `GET /api/spiritual-life/milestones` | `spiritual_life:read` | Filtro por `actor.sede_id` | ✅ Lista hitos de la sede |
| `GET /api/spiritual-life/milestones/{persona_id}` | `spiritual_life:read` | `_assert_persona_in_sede` (404 neutro) | ✅ Detalle de hitos por persona |
| `POST /api/spiritual-life/milestones` | `spiritual_life:manage` | `_assert_persona_in_sede` (404 neutro) | ✅ Creación de hitos canónicos |
| `GET /api/spiritual-life/milestone/{milestone_id}` | `spiritual_life:read` | `_assert_milestone_in_sede` (404 neutro) | ✅ Consulta individual de hito |
| `PATCH /api/spiritual-life/milestone/{milestone_id}` | `spiritual_life:edit` | `_assert_milestone_in_sede` (404 neutro) | ✅ Mutación parcial de hito |
| `DELETE /api/spiritual-life/milestone/{milestone_id}` | `spiritual_life:edit` | `_assert_milestone_in_sede` (404 neutro) | ✅ Soft delete (`deleted_at`) |
| `GET /api/admin/milestones` | `require_active_user` | Filtro por `actor.sede_id` | ✅ Resumen de insignias |
| `POST /api/admin/milestones/award` | `require_admin` | `_assert_persona_in_sede` | ✅ Otorgamiento de insignias |

---

## 4. Frontend

| Ruta | Permiso mínimo | Mecanismo de Control |
|---|---|---|
| `/plataforma/spiritual-life` | `spiritual_life:read` | Protegido por `WorkspaceLayout` y `workspaceAccess.ts` |
| `/plataforma/spiritual-life/timeline` | `spiritual_life:read` | Protegido por layout y control de permisos |
| `/plataforma/spiritual-life/certificates` | `spiritual_life:read` | Protegido por layout y proxy a Academia |
| `/plataforma/admin/spiritual-life/milestones` | `spiritual_life:manage` | Protegido en navegación y API backend |

---

## 5. Invariantes de Seguridad y Diseño

1. **Aislamiento Multi-Tenant Estricto (Axioma 3):** Ningún actor de la sede A puede acceder a información de la sede B. Peticiones cross-sede retornan HTTP 404 neutro (BOLA safe, sin fugas de existencia).
2. **Taxonomía Canónica:** Todo endpoint de mutación y creación responde a `spiritual_life:*`. `require_admin` se reserva estrictamente para endpoints globales del sistema.
3. **Soft Delete Universal:** Ningún registro de hito espiritual se borra físicamente de la base de datos (`0 db.delete(`). Se establece marca de tiempo UTC en `deleted_at`.
4. **Fechas UTC:** Cero uso de `datetime.utcnow()` naive. Todas las fechas y auditorías usan `_utcnow()` con zona horaria estricta.

---

## 6. Estado de Implementación

| Aspecto | Estado | Veredicto |
|---|---|---|
| Guard GET | `spiritual_life:read` | ✅ Implementado y verificado |
| Guard POST | `spiritual_life:manage` | ✅ Implementado y verificado |
| Guard PATCH | `spiritual_life:edit` | ✅ Implementado y verificado |
| Guard DELETE | `spiritual_life:edit` | ✅ Implementado y verificado |
| Frontend admin | `spiritual_life:manage` | ✅ Implementado y verificado |
| Tests de RBAC | 100% aprobados en `test_spiritual_life_api.py` | ✅ Certificado |
