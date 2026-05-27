# PLAN DE TRABAJO — Modelo de Evangelismo Super Pro

**Fecha:** 2026-05-27
**Objetivo:** Implementar el modelo de base de datos propuesto por el usuario, 
integrándolo con lo existente sin romper nada.

---

## ANÁLISIS GAP: Propuesto vs Existente

| Modelo Propuesto | Estado Actual | Acción Requerida |
|---|---|---|
| `Sede` (multi-tenant) | ❌ No existe | ✅ CREAR tabla nueva + migración |
| `LogAuditoria` (auditoría JSONB) | ⚠️ Existe AdminAuditLog pero sin JSONB | ✅ CREAR tabla nueva con JSONB |
| `CategoriaEstrategia` | ❌ No existe | ✅ CREAR tabla nueva + FK en Estrategias |
| `MotivoExcusa` | ✅ Ya existe en models_evangelism.py | ✅ VERIFICAR + migrar si necesario |
| `EstrategiaEvangelismo` | ✅ Existe como `EvangelismStrategy` | ✅ AGREGAR sede_id, categoria_id |
| `RolPersonalizadoEstrategia` | ✅ Ya existe | ✅ VERIFICAR compatibilidad |
| `GrupoEvangelismo` | ✅ Existe como `GloryHouse` | ✅ AGREGAR sede_id, lat/long Float |
| `ParticipanteGrupo` | ✅ Existe como `GloryHouseMember` | ✅ VERIFICAR compatibilidad |
| `SesionGrupo` | ✅ Existe como `GloryHouseSession` | ✅ VERIFICAR compatibilidad |
| `Asistencia` | ✅ Existe como `GloryHouseAttendance` | ✅ VERIFICAR compatibilidad |
| `RegistroSeguimiento` | ✅ Ya existe | ✅ VERIFICAR compatibilidad |
| `Persona` | ✅ Existe como `Member`/`Agent` | ✅ NO CREAR — usar existentes |
| `HistorialEmbudo` | ⚠️ Existe parcialmente `kernel_role_history` | ✅ CREAR tabla específica de embudo |
| Vistas materializadas | ❌ No existen | ✅ CREAR DDL para migración |

---

## FASES DE IMPLEMENTACIÓN

### FASE 1: Tablas Nuevas (Multi-Tenant + Config)
1. **sedes** — Campus/sedes de la CCF
2. **categorias_estrategia** — Clasificación de estrategias
3. **logs_auditoria** — Auditoría con JSONB (antes/después)

### FASE 2: Extender Tablas Existentes
4. Agregar `sede_id` a `evangelism_strategies`, `glory_houses`
5. Agregar `categoria_id` FK a `evangelism_strategies`
6. Verificar compatibilidad de enums existentes vs propuestos

### FASE 3: Motor de Velocidad del Embudo
7. **historial_embudo** — Métrica de velocidad (días entre estados)
8. Seed data de categorías y excusas del sistema

### FASE 4: OLAP — Vistas Materializadas
9. **mv_resumen_asistencia** — Dashboard de asistencia rápido
10. Trigger/función para refresh nocturno

### FASE 5: Seed Data + Verificación
11. Seed: sedes (Sede Principal, etc.)
12. Seed: categorías de estrategia
13. Seed: motivos de excusa del sistema
14. QC completa: imports, migraciones, endpoints existentes

---

## RIESGOS Y MITIGACIÓN

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Cambiar FK de `glory_houses` | Alto (rompe frontend) | Agregar columnas como nullable primero |
| Enums diferentes | Medio | Crear mapeo en código, no cambiar BD existente |
| UUID vs Integer para Persona | Alto | NO cambiar — Member usa Integer, usarlo |
| Migración grande | Medio | Dividir en 2-3 migraciones pequeñas |

---

## ORDEN DE EJECUCIÓN

```
F1 (sedes, categorias, auditoria)
  → F2 (extender tablas existentes)
    → F3 (historial embudo + seed)
      → F4 (vistas materializadas)
        → F5 (QC final)
```
