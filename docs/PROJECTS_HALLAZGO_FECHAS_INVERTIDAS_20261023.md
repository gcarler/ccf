# Hallazgo / Ticket — 500 y estado corrupto con fechas invertidas de proyecto

**Fecha:** 2026-10-23 · **Módulo:** Projects (backend, FastAPI + SQLAlchemy) · **Estado:** REPARADO

## Resumen

La API permitía crear y actualizar proyectos con `start_date` posterior a `target_date`.
Ese estado invertido de la línea base temporal degrada semánticamente el motor EVM
(PV = 0 → SPI = 2.0 falsamente favorable; ES con horizonte forzado a 30 días) y quedó
documentado en la sesión del 2026-10-23 ligado a respuestas 500 en
`GET /api/projects/{id}` (atrapado en flagrante con el fixture de Biblioteca Digital CCF).

## Reproducción

- `POST /api/projects` con `start_date` a +5 días y `target_date` a −10 días: se aceptaba (201),
  cuando el mismo contrato para **tareas** ya lo bloquea con
  `422 start_date no puede ser posterior a due_date` (`backend/schemas/projects.py:337`).
- Proyecto de prueba en ambiente vivo: `PRUEBA-500-FECHAS-INVERTIDAS` (creado y limpiado).

## Causa raíz

`ProjectBase` / `ProjectUpdate` no validaban el orden temporal (asimetría con las tareas).
En el camino del GET de detalle la respuesta se responde vía `schemas.Project`
(hereda de `ProjectBase`): dejar el guard en la base compartida **reproduciría**
`ResponseValidationError → 500` para proyectos legacy invertidos, volviendo irrecuperable
el detalle desde la API. Verificado en tests (`tests/test_projects_inverted_dates.py::*200_with_inverted_dates`).

## Reparación

1. `ProjectCreate._dates_order` — guard **solo en el modelo de entrada**: `422 start_date no puede ser posterior a target_date del proyecto`.
2. `ProjectUpdate._dates_order_partial` — mismo guard cuando ambas fechas viajan en el PATCH.
3. `PATCH /api/projects/{id}` (`update_project`) — cross-check contra los **valores efectivos finales**
   (fechas faltantes resueltas con las persistidas), normalizando naive/aware a UTC
   (SQLite devuelve datetimes naive). Anti-regresión: si el proyecto ya está invertido
   en BD no se bloquea el remate (no lo empeora), solo se impide *introducir* el desorden.
4. Legibilidad en el motor: `calculate_project_evm` y `calculate_earned_schedule` ya
   guardaban `target <= start` (sin cambios necesarios).

## Regresión

`tests/test_projects_inverted_dates.py` (4 tests):
- create invertido → **422**
- PATCH que introduce el desorden → **422**
- GET detalle con proyecto legacy invertido → **200** (el guard no vive en el response model)
- GET execution-matrix con fechas invertidas → **200**

## Deuda derivada (no automática)

- Migración de normalización para proyectos heredados con `start_date > target_date`
  (reversible, per protocolo §4: nueva migración, no tocar migraciones cerradas).
- Considerar guard equivalente a nivel de DB (`CHECK`) al aplicar esa migración.
