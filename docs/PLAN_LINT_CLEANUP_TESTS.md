# Plan: Clean Up Lint Debt in `tests/*.py`

## Contexto

El proyecto tiene un `per-file-ignores` en `pyproject.toml` que silencia reglas de lint para todos los tests:

```toml
"tests/*.py" = ["E701", "E702", "F811", "F821", "F841"]
```

Sin ese ignore, `ruff check tests/` reporta **391 errores** distribuidos principalmente en archivos de cobertura masiva y gap coverage.

## Objetivo

Eliminar el `per-file-ignores` de `tests/*.py` en `pyproject.toml` y dejar que `ruff check backend/ tests/` pase sin errores, sin perder cobertura ni romper tests funcionales.

## Estado actual

- **Errores totales sin ignore**: 391
- **Top 10 archivos**:
  - `tests/test_fast_coverage.py` — 84
  - `tests/test_every_crud.py` — 62
  - `tests/test_evangelism_module_coverage.py` — 50
  - `tests/test_cms_v2_gap_coverage.py` — 37
  - `tests/test_massive_coverage.py` — 16
  - `tests/test_pastoral_coverage.py` — 14
  - `tests/test_flow_tests.py` — 13
  - `tests/factories_projects.py` — 13
  - `tests/test_final_coverage.py` — 11
  - `tests/test_pastoral_deep_coverage.py` — 10

- **Top reglas**:
  - `F841` — Local variable assigned but never used
  - `E702` — Multiple statements on one line (semicolon)
  - `E701` — Multiple statements on one line (colon)
  - `F811` — Redefinition of unused name
  - `F821` — Undefined name

## Fases de trabajo

### Paso previo — Auto-fixes con ruff

Antes de empezar la limpieza manual, ejecutar una pasada automática para reducir el volumen de errores:

```bash
./venv/bin/ruff check tests/ --fix --select E701,E702,F841
```

- `E701` y `E702` son casi siempre auto-fixables.
- `F841` también tiene fix automático, pero **debe revisarse manualmente** para no perder side effects.
- Después de esta pasada, ejecutar `ruff check tests/ --select E701,E702,F841` para ver lo que queda por arreglar a mano.

## Fases de trabajo

### Fase 1 — Redefiniciones (F811)

- **Regla**: `F811`
- **Esfuerzo**: Medio
- **Prioridad**: Alta (debe hacerse antes que F841/E701/E702)
- **Acciones**:
  - Identificar clases/funciones de test con nombres duplicados (e.g., `TestCategoryValidation` aparece dos veces en `test_cms_v2_gap_coverage.py`).
  - Renombrarlas con un sufijo descriptivo o unirlas en una sola clase.
  - **Importante**: al renombrar se exponen tests que antes quedaban ocultos (sobreescritos por la última definición). Ejecutar `pytest` sobre esos archivos para verificar que los tests recién expuestos pasen.
- **Comando de validación**:
  ```bash
  ./venv/bin/ruff check tests/ --select F811
  pytest tests/test_cms_v2_gap_coverage.py tests/test_massive_coverage.py
  ```
- **Criterio de éxito**: 0 errores F811 y los tests expuestos pasan

### Fase 2 — Auto-fixes seguros (E701, E702)

- **Reglas**: `E701`, `E702`
- **Esfuerzo**: Bajo (mayoría mecanizable)
- **Acciones**:
  - Reemplazar `;` por líneas separadas.
  - Convertir comprensiones/listas con statements inline a bloques multilinea.
  - Ejemplo: `db_session.add(x); lista.append(x)` → dos líneas.
- **Comando de validación**:
  ```bash
  ./venv/bin/ruff check tests/ --select E701,E702
  ```
- **Criterio de éxito**: 0 errores de E701/E702 en tests/

### Fase 3 — Variables no usadas (F841)

- **Regla**: `F841`
- **Esfuerzo**: Medio-Alto (requiere revisión manual)
- **Acciones**:
  - Eliminar asignaciones a variables que no se usan.
  - **¡Cuidado!** Si el lado derecho tiene side effects (crear una fila en BD, etc.), no eliminar la llamada; solo eliminar la asignación a variable.
  - Ejemplo: `user = create_user(...)` si `user` no se usa → `create_user(...)`.
  - En algunos casos la variable se usa para legibilidad o debugging; en vez de eliminarla, considerar renombrarla a `_` o usar un comentario.
- **Comando de validación**:
  ```bash
  ./venv/bin/ruff check tests/ --select F841
  ```
- **Criterio de éxito**: 0 errores F841 en tests/

### Fase 4 — Nombres indefinidos (F821)

- **Regla**: `F821`
- **Esfuerzo**: Bajo
- **Archivo principal**: `tests/factories_projects.py`
- **Acciones**:
  - Agregar `from __future__ import annotations` al tope del archivo, o
  - Usar forward references entre comillas en anotaciones de tipo (e.g., `-> "Project"`).
- **Comando de validación**:
  ```bash
  ./venv/bin/ruff check tests/ --select F821
  ```
- **Criterio de éxito**: 0 errores F821 en tests/

### Fase 5 — Limpiar `pyproject.toml`

- **Acciones**:
  - Remover la línea `"tests/*.py" = ["E701", "E702", "F811", "F821", "F841"]`.
  - Ejecutar `scripts/run_ci.sh` completo.
- **Criterio de éxito**:
  - `ruff check backend/ tests/` pasa sin errores.
  - `scripts/run_ci.sh` pasa los 10 pasos.

## Validación por fase

Después de cada fase (especialmente F811 y F841), ejecutar:

```bash
./venv/bin/ruff check tests/ --select <REGLA>
./venv/bin/python -m pytest tests/ -q --tb=short
```

Esto detecta temprano tests expuestos que fallan o side effects perdidos.

## Coordinación con el equipo

Mientras dure el cleanup:

1. **No agregar nuevos tests que violen E701/E702/F811/F821/F841**.
2. Favorecer commits pequeños y granulares por fase.
3. Comunicar cuando se expongan tests ocultos por F811 para evitar sorpresas en coverage.

## Seguimiento de progreso en CI

Opcionalmente, agregar un job temporal en `.github/workflows/ci.yml` que corra:

```bash
./venv/bin/ruff check tests/ --select E701,E702,F811,F821,F841
```

Este job puede correr sin bloquear merge, sirviendo como métrica de deuda técnica hasta que se complete la limpieza.

## Estrategia de commits

Para mantener el historial limpio y revisable, usar commits granulares por fase (o por archivo si un archivo tiene muchos cambios):

1. `test(lint): fix E701/E702 formatting rules in tests`
2. `test(lint): fix F841 unused variables in tests`
3. `test(lint): fix F811 redefined test names in tests`
4. `test(lint): fix F821 undefined names in factories`
5. `chore(lint): remove tests per-file-ignores from pyproject.toml`

## Mitigación de riesgos

| Riesgo | Mitigación |
|--------|------------|
| Perder side effects al eliminar asignaciones F841 | Revisar manualmente cada caso. No borrar llamadas a factories ni setups. |
| Exponer tests fallidos al renombrar F811 | Ejecutar `pytest` después de cada archivo con redefiniciones. |
| Merge conflicts masivos | Trabajar por fases y en PRs pequeños. Evitar un solo commit gigante. |
| Romper CI a media limpieza | Actualizar `pyproject.toml` temporalmente con ignores más específicos por archivo mientras se avanza. |

## Mantener CI verde durante la transición

Mientras no se haya completado todo, se puede restringir el `per-file-ignores` a solo las reglas/archivos pendientes:

```toml
"tests/test_fast_coverage.py" = ["F841"]
"tests/test_every_crud.py" = ["E701", "E702"]
# ... etc
```

Esto permite mergear progreso sin romper `run_ci.sh`.

## Definición de terminado

1. `ruff check backend/ tests/` reporta **0 errores**.
2. El `per-file-ignores` de `tests/*.py` fue eliminado de `pyproject.toml`.
3. `pytest tests/` sigue pasando (sin reducir cobertura funcional).
4. `scripts/run_ci.sh` completo pasa localmente.

## Estimación aproximada

- Fase 1 (E701/E702): 2-3 horas
- Fase 2 (F841): 4-6 horas (revisión manual cuidadosa)
- Fase 3 (F811): 2-3 horas
- Fase 4 (F821): 30 minutos
- Fase 5 (validación final y limpieza): 1 hora
- **Total estimado**: 1-2 días de trabajo enfocado

## Notas adicionales

- La mayor parte del trabajo es mecánico pero tedioso; conviene dedicar bloques de tiempo sin distracciones para no perder side effects.
- Se recomienda correr `pytest` al final de cada fase para detectar regresiones temprano.
