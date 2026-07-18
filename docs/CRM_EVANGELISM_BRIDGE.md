# CRM-Evangelism Bridge — Documentación

> **Fecha:** 2026-07-16
> **Estado:** Documentado y testeado con mocks
> **Owner del contrato:** Evangelismo (proveedor), CRM (consumidor)

## 1. Descripción

El módulo CRM consume APIs del módulo Evangelismo en la página de administración de grupos (`/plataforma/crm/groups/admin`). Esto permite que los líderes de grupo reporten asistencia semanal directamente desde CRM, sin cambiar de módulo.

## 2. Flujo de datos

```
CRM Groups Admin Page
    │
    ├── GET /api/community/grupos  ──────────────── CRM interno (lista de grupos)
    │
    ├── GET /api/evangelism/groups/seasons  ────── Evangelismo (temporadas activas)
    │
    ├── GET /api/evangelism/grupos/{groupId}  ──── Evangelismo (detalle + asistentes base)
    │
    ├── POST /api/evangelism/groups/sessions  ──── Evangelismo (crear sesión)
    │       body: { season_id, grupo_id, session_date }
    │
    └── POST /api/evangelism/groups/sessions/{sessionId}/attendance
            body: { persona_ids: [...] }
```

## 3. Contratos API consumidos

| # | Método | Ruta | Owner | Descripción |
|---|--------|------|-------|-------------|
| 1 | `GET` | `/api/evangelism/groups/seasons` | Evangelismo | Lista temporadas de reporte |
| 2 | `GET` | `/api/evangelism/grupos/{groupId}` | Evangelismo | Detalle del grupo con `base_attendees` |
| 3 | `POST` | `/api/evangelism/groups/sessions` | Evangelismo | Crea sesión de reporte semanal |
| 4 | `POST` | `/api/evangelism/groups/sessions/{sessionId}/attendance` | Evangelismo | Registra asistencia |

## 4. Llave foránea

- `grupo.id` conecta ambos módulos.
- Ambos módulos deben tener los mismos registros de grupo.
- Si evangelismo no tiene el grupo, el flujo de reporte falla.

## 5. Manejo de errores

- Si `GET /evangelism/groups/seasons` falla → toast de error: "No se pudo preparar el reporte"
- Si `GET /evangelism/grupos/{id}` falla → toast de error
- Si `POST /evangelism/groups/sessions` falla → toast de error
- La página no crashea; el usuario ve un toast y puede reintentar

## 6. Tests

| Archivo | Cobertura |
|---------|-----------|
| `frontend/tests/e2e/crm/groups-admin.spec.ts` | Carga de página, selección de grupo, error handling de evangelism API |

## 7. Riesgos

1. **Cambio en `/evangelism/grupos/{id}`**: rompe la carga de asistentes base
2. **Cambio en shape de `base_attendees`**: rompe el checklist de asistencia
3. **Cambio en temporadas**: rompe la selección de período de reporte
4. **Owner del fix**: siempre Evangelismo, ya que CRM es consumidor

## 8. Regla de cambio

Si se modifica cualquier contrato de evangelismo listado arriba:
1. Notificar al owner de CRM
2. Verificar que `groups-admin.spec.ts` sigue pasando
3. Actualizar este documento si cambia la shape
