# Deprecación de Alias CRM en Evangelismo

Fecha: 2026-05-19  
Estado: Activo (fase de observabilidad)

## Objetivo

Retirar gradualmente endpoints CRM expuestos bajo `/api/evangelism/*` y consolidar consumo en `/api/crm/*`.

## Regla

- **Canónico** para CRM: `/api/crm/*`
- `/api/evangelism/*` solo para dominio Evangelismo (eventos, asistencia, faro, scanner)

## Matriz de alias (deprecados)

- `/api/evangelism/counseling/*` -> `/api/crm/counseling/*`
- `/api/evangelism/prayer-requests/*` -> `/api/crm/prayer-requests*`
- `/api/evangelism/messaging/*` -> `/api/crm/messaging/*`
- `/api/evangelism/tasks*` -> `/api/crm/tasks*`
- `/api/evangelism/volunteers*` -> `/api/crm/volunteers*`
- `/api/evangelism/settings` -> `/api/crm/settings`
- `/api/evangelism/analytics` -> `/api/crm/analytics`

## Implementación actual

- Se agregó `warning` en backend cuando se usa un alias deprecado, una vez por endpoint/proceso.
- Archivo: `backend/api/evangelism.py`

## Plan de retiro

1. Medir en logs uso de alias por 2 ciclos de release.
2. Migrar clientes restantes a `/api/crm/*`.
3. Cambiar warnings por `410 Gone` detrás de feature flag.
4. Eliminar alias en release mayor.
