# AUDITORÍA DE HILARIDAD — HALLAZGOS CRÍTICOS

**Fecha:** 2026-05-29  
**Auditor:** Sistema Automatizado de Calidad CCF

---

## 🔴 HALLAZGO CRÍTICO #1: personas.id INTEGER vs UUID

| Componente | Tipo | Estado |
|---|---|---|
| **PostgreSQL** | `personas.id` | `INTEGER` |
| **SQLAlchemy Model** | `Persona.id` | `UUID(as_uuid=True)` |
| **Pydantic Schema** | `PersonaResponse.id` | `str` |
| Registros | Count | 30 |

**Impacto:** El modelo dice UUID pero la BD tiene INTEGER. Cada JOIN que involucra `personas.id` genera un error de tipo `uuid = integer` en PostgreSQL → **500 Internal Server Error en cascada**.

**Causa:** La migración UUID planificada en `scripts/migrations/uuid_migration.sql` NUNCA se ejecutó contra esta base de datos.

---

## 🔴 HALLAZGO CRÍTICO #2: 37 FKs tipo NUMERIC/INTEGER → personas.id

Todas las FKs a personas.id son NUMERIC/INTEGER en PostgreSQL. Los modelos declaran UUID. Cada query con JOIN falla.

| Tipo FK | Cantidad | Tablas |
|---|---|---|
| NUMERIC | 33 | asistencias, consolidation_*, crm_tasks, donations, grupos_evangelismo, etc. |
| INTEGER | 4 | cell_group_attendance, cell_group_members, counseling_tickets |

---

## 🟡 HALLAZGO #3: 12 tablas legacy con 1,132 registros

Tablas que debieron ser eliminadas pero aún existen:
- cell_group_attendance (860 rows)
- cell_group_sessions (120 rows)  
- cell_group_members (86 rows)
- enrollments (20 rows)
- consolidation_cases (20 rows)
- project_tasks (20 rows)
- courses (6 rows)
- projects (4 rows)
- + 4 tablas vacías

---

## 🟢 HALLAZGO #4: 678 endpoints API registrados

| Módulo | Endpoints |
|---|---|
| evangelism | 106 |
| crm | 87 |
| cms | 65 |
| auth | 57 |
| Otros (30 módulos) | 363 |

---

## 🎯 PLAN DE REMEDIACIÓN INMEDIATA

1. **Ejecutar migración UUID** (`uuid_migration.sql` → personas.id INTEGER→UUID + 37 FKs)
2. **Dropear 12 tablas legacy** con respaldo
3. **Verificar 0 type mismatches** post-migración
4. **Probar 10 endpoints críticos** (CRM, Evangelism, Agents, Auth)

¿Ejecuto la remediación AHORA?
