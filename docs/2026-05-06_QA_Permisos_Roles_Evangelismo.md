# QA Permisos y Roles - Evangelismo

Fecha: 6 de mayo de 2026

## Resumen ejecutivo

- Seguridad backend en módulo Evangelismo centralizada en:
  - `require_pastor_or_admin` para operaciones ministeriales.
  - `require_active_user` para casos acotados de consulta propia.
  - `require_admin` para configuración sensible.
- Validación de autorización negativa y positiva:
  - Rol `estudiante` recibe `403` en endpoints críticos.
  - Rol `pastor` accede a endpoints permitidos.
- Frontend alineado por rol (`admin`/`pastor`) en guardia de página y navegación.

## Matriz de acceso (backend)

Referencia:
- `backend/auth.py`
- `backend/api/evangelism.py`
- `backend/api/evangelism_events.py`
- `backend/api/evangelism_faro.py`

### 1) Eventos y asistencia

- `GET /api/evangelism/events/`: `require_pastor_or_admin`
- `POST /api/evangelism/events/`: `require_pastor_or_admin`
- `PUT /api/evangelism/events/{id}`: `require_pastor_or_admin`
- `DELETE /api/evangelism/events/{id}`: `require_pastor_or_admin`
- `GET /api/evangelism/events/{id}`: `require_pastor_or_admin`
- `GET /api/evangelism/events/{id}/attendance`: `require_pastor_or_admin`
- `POST /api/evangelism/attendance`: `require_pastor_or_admin`
- `POST /api/evangelism/attendance/bulk`: `require_pastor_or_admin`
- `GET /api/evangelism/events/{id}/sessions/{date}`: `require_pastor_or_admin`
- `POST /api/evangelism/events/{id}/assignments`: `require_pastor_or_admin`
- `GET /api/evangelism/events/{id}/sessions/{date}/export`: `require_pastor_or_admin`
- `GET /api/evangelism/members/{member_id}/attendance-history`: `require_active_user` + validación de dueño o staff.

### 2) Faro

- `GET /api/evangelism/glory-houses`: `require_pastor_or_admin`
- `POST /api/evangelism/glory-houses`: `require_pastor_or_admin`
- `PUT /api/evangelism/glory-houses/{id}`: `require_pastor_or_admin`
- `GET /api/evangelism/faro/seasons`: `require_pastor_or_admin`
- `POST /api/evangelism/faro/seasons`: `require_pastor_or_admin`
- `PATCH /api/evangelism/faro/seasons/{id}`: `require_pastor_or_admin`
- `GET /api/evangelism/faro/sessions`: `require_pastor_or_admin`
- `POST /api/evangelism/faro/sessions`: `require_pastor_or_admin`
- `GET /api/evangelism/faro/sessions/{id}/attendance`: `require_pastor_or_admin`
- `POST /api/evangelism/faro/sessions/{id}/attendance`: `require_pastor_or_admin`
- `GET /api/evangelism/faro/analytics`: `require_pastor_or_admin`

### 3) Scanner

- `POST /api/evangelism/scanner/validate/{token}`: `require_pastor_or_admin`

### 4) Configuración

- `GET /api/evangelism/settings`: `require_admin`
- `POST /api/evangelism/settings`: `require_admin`

## Evidencia de pruebas

Comando:

```powershell
python -m pytest tests/test_crm_api.py -k "evangelism or scanner" -q
```

Resultado:
- `8 passed, 12 deselected`

Pruebas de permisos agregadas:
- `test_evangelism_events_requires_pastor_or_admin`
- `test_evangelism_scanner_requires_pastor_or_admin`
- `test_evangelism_events_allows_pastor_role`
- `test_evangelism_scanner_allows_pastor_role`

## Frontend aplicado (alineación UX)

- Guardia de pantalla:
  - `frontend/src/components/evangelism/EvangelismShell.tsx`
- Ocultamiento en mini sidebar:
  - `frontend/src/components/WorkspaceMiniSidebar.tsx`
- Filtro global de links `/evangelism` en sidebars por configuración:
  - `frontend/src/components/WorkspaceLayout.tsx`
- Ocultamiento de acceso rápido en calendario:
  - `frontend/src/app/calendar/page.tsx`

## Hallazgos y brechas

1. Backend: correcto y probado.
2. Frontend: correcto y alineado por rol en URL + navegación.
3. Riesgo residual: bajo, limitado a futuros enlaces hardcodeados fuera de componentes base.

## Recomendación operativa

- Mantener estas pruebas de permisos en CI.
- Exigir en PR checklist de seguridad para cualquier ruta nueva `/evangelism/*`.
