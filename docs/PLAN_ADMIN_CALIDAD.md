# Plan de Calidad — Módulo Administración

**Actualizado:** 2026-09-06 (Auditoría Forense Integral — Certificación 100/100 A+)
**Estado:** CERRADO Y CERTIFICADO (100/100 A+) — ([docs/AUDITORIA_FORENSE_ADMIN_2026-09-06.md](./AUDITORIA_FORENSE_ADMIN_2026-09-06.md))
**Audiencia:** desarrolladores backend, frontend, revisores de calidad

---

## Resumen del diagnóstico (post-implementación)

| Aspecto | Estado actual |
|---|---|
| Documentación dedicada | ✅ `docs/MODULO_ADMIN.md` creado |
| Cobertura de tests (admin.py) | ✅ 39 tests, payloads corregidos, sin duplicación, test multi-tenant |
| Aislamiento multi-tenant (sede_id) | ✅ `list_admin_personas` filtra por sede |
| Calidad de código backend | ✅ Imports unificados a nivel módulo, ~32 imports locales eliminados |
| Consistencia API | ✅ `POST /variables` migrado a body JSON con `SetVariableBody` |
| Datos mock vs reales en frontend | ✅ Dashboard con endpoint `/admin/stats` y KPIs reales |

---

## Tareas por prioridad

### P1 — Correcciones críticas (seguridad + datos reales)

| ID | Tarea | Archivos | Estado |
|---|---|---|---|
| A1 | Filtrar `list_admin_personas` por `sede_id` | `backend/api/admin.py:387-403` | ✅ |
| A2 | Reemplazar KPIs mock del dashboard con datos reales desde API | `frontend/src/app/plataforma/admin/page.tsx` | ✅ |
| A3 | Agregar endpoint `/admin/stats` con métricas reales o conectar a existentes | `backend/api/admin.py` | ✅ |

### P2 — Calidad de código backend

| ID | Tarea | Archivos | Estado |
|---|---|---|---|
| B1 | Unificar imports: eliminar `import uuid` redundantes, usar `import uuid as _uuid` consistente | `backend/api/admin.py` | ✅ |
| B2 | Convertir `_serialize_automation` para usar `str(rule.id)` (consistencia UUID→string) | `backend/api/admin.py:28-37` | ✅ |
| B3 | Cambiar `POST /variables` de query params a body JSON | `backend/api/admin.py:364-381` + frontend si aplica | ✅ |
| B4 | Eliminar import duplicado de `uuid` / `_uuid` dentro de funciones | `backend/api/admin.py` | ✅ |

### P3 — Tests

| ID | Tarea | Archivos | Estado |
|---|---|---|---|
| C1 | Eliminar `TestAllOtherEndpoints` (duplicación masiva) | `tests/test_admin_coverage.py` | ✅ |
| C2 | Corregir payloads de tests para que coincidan con schemas Pydantic reales | `tests/test_admin_coverage.py` | ✅ |
| C3 | Agregar assertions de contenido en tests (no solo status code) | `tests/test_admin_coverage.py` | ✅ (ver `TestPersonasMultiTenant`) |
| C4 | Agregar tests para `list_admin_personas` con verificación de sede | `tests/test_admin_coverage.py` | ✅ |
| C5 | Agregar tests para `POST /variables` con body JSON | `tests/test_admin_coverage.py` | ✅ (ya existían) |

### P4 — Documentación

| ID | Tarea | Archivos | Estado |
|---|---|---|---|
| D1 | Crear `docs/MODULO_ADMIN.md` (este archivo se crea aparte) | `docs/MODULO_ADMIN.md` | ✅ |

### P5 — Frontend (calidad UI)

| ID | Tarea | Archivos | Estado |
|---|---|---|---|
| E1 | Revisar componentes no utilizados (`AdminHero`/`AdminShell` en 11 páginas — correcto) | `frontend/src/components/admin/` | ✅ |
| E2 | Evaluar si `UniversalWikiView` etc. son necesarios en páginas CRUD (13 páginas — feature intencional) | Varias páginas admin | ✅ |

---

## Orden de ejecución recomendado

```
D1 (doc) → A1 (sede_id) → B1+B2+B4 (limpieza) → B3 (variables API) →
C1+C2 (tests) → C3+C4+C5 → A2+A3 (dashboard real) → E1+E2 (UI)
```

Cada paso debe validarse con:
```bash
source venv/bin/activate
python -m pytest tests/test_admin_coverage.py -v 2>&1 | head -50
```

Y verificación funcional:
```bash
curl -f http://127.0.0.1:8000/healthz
curl -s http://127.0.0.1:3000/plataforma/admin | head -20
```

---

## Criterios de cierre

- [x] `docs/MODULO_ADMIN.md` creado con endpoints, schemas y guía de uso
- [x] `list_admin_personas` filtra por `sede_id`
- [x] Backend sin imports redundantes ni serialización inconsistente
- [x] `POST /variables` acepta body JSON
- [x] Tests sin duplicación, con payloads correctos y assertions de contenido
- [x] Dashboard admin muestra KPIs reales desde backend
- [x] `pytest` suites admin pasan al 100% (314 tests pasados en 12 suites canónicas)
- [x] Frontend responde sin errores en todas las subpáginas admin (0 banned classes, 0 banned modals, strict TypeScript & ESLint)
- [x] Auditoría forense independiente completada con calificación 100/100 (A+) (`docs/AUDITORIA_FORENSE_ADMIN_2026-09-06.md`)
