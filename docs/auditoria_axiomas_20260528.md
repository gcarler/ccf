# Auditoría de Axiomas CCF — Reporte Final

## Axioma 1: Person-Centric Kernel ✅
- `personas.id` = UUID (migrado, 968 registros)
- 95 FKs activas, 0 huérfanas
- 0 Integer FKs a personas.id en modelos Python
- `auth_users.id` comparte UUID con `personas.id`; no se debe recrear una columna inversa en `personas`.

## Axioma 2: Identidad Tridimensional ✅
- `PersonaRoleAssignment` en Kernel (platform_role, ministry_office, church_role)
- `church_role_effective` property implementada (fallback a columna compat)
- `ChurchRoleDefinition` + `ChurchRoleGrant` para roles ministeriales
- `ModulePermissionPolicy` para permisos por módulo
- ⚠️ `personas.church_role` columna compat marcada DEPRECADO

## Axioma 3: Aislamiento Multi-Tenant ✅
- `sede_id` en todas las tablas v2
- 5 endpoints públicos sellados (admin.py)
- ⚠️ ~35 endpoints compat sin filtro sede_id (módulos no migrados)

## UUIDs — 100% en tablas v2 ✅
- CRM Core: CasoCRM.id UUID, persona_id UUID
- Academy Core: Matricula.id UUID, persona_id UUID
- Agenda: EventoAgenda.id UUID, persona_id UUID
- Proyectos: Proyecto.id UUID, creado_por_id UUID

## Soft Delete ✅
- `agenda_eventos.deleted_at` implementado
- `personas.estado_vital = 'INACTIVO'` en endpoints CRM
- CRUD delete_persona usa soft-delete

## Timezones ⚠️
- `agenda_eventos` usa DateTime(timezone=True) ✅
- `_utcnow()` en models_shared.py NO incluye timezone ❌
  → Afecta 40+ columnas DateTime en modelos compat
  → Fix: actualizar _utcnow() para incluir tzinfo
