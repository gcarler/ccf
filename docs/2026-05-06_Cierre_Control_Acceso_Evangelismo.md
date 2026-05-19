# Cierre Control de Acceso Evangelismo

Fecha: 6 de mayo de 2026

## Objetivo

Dejar consistente el control de acceso a Evangelismo en tres capas:

1. Backend (autorización real).
2. Frontend por URL (guardia de pantalla).
3. Frontend por navegación (ocultar entradas no autorizadas).

## Backend (fuente de verdad)

Protección principal:
- `require_pastor_or_admin` para operaciones ministeriales.
- `require_admin` para configuración sensible.
- `require_active_user` solo en casos específicos con validación adicional.

Endpoints clave protegidos:
- Eventos y asistencia:
  - `/api/evangelism/events/*`
  - `/api/evangelism/attendance*`
  - `/api/evangelism/events/*/sessions/*`
- Faro:
  - `/api/evangelism/glory-houses*`
  - `/api/evangelism/faro/*`
- Scanner:
  - `/api/evangelism/scanner/validate/{token}`
- Settings:
  - `/api/evangelism/settings*` (`admin`).

Evidencia de pruebas:
- `pytest tests/test_crm_api.py -k "evangelism or scanner" -q`
- Resultado: `6 passed`.

## Frontend por URL (guardia de pantalla)

Implementado en:
- `frontend/src/components/evangelism/EvangelismShell.tsx`

Regla:
- Solo roles `admin` y `pastor`.
- Si no autorizado: render de “Acceso restringido”.

Resultado:
- Aunque un usuario no permitido escriba la URL de Evangelismo, no ve el módulo.

## Frontend por navegación (entradas UI)

### 1) Mini Sidebar

Implementado en:
- `frontend/src/components/WorkspaceMiniSidebar.tsx`

Regla:
- El ítem `Evangelismo` se oculta si el rol no es `admin`/`pastor`.

### 2) Sidebars basados en configuración de módulos

Implementado en:
- `frontend/src/components/WorkspaceLayout.tsx`

Regla global:
- Para roles no permitidos, se filtran items cuyo `href` inicie con `/evangelism`.

Resultado:
- Cubre accesos indirectos que provienen de `moduleConfigs`.

### 3) Acceso rápido en Calendario

Implementado en:
- `frontend/src/app/calendar/page.tsx`

Regla:
- Botón rápido “Evangelismo” visible solo para `admin`/`pastor`.

## Estado de calidad técnica

- `npm run typecheck`: OK.
- Limpieza de mojibake en Eventos/Scanner: completada.
- Flujos críticos con estados de guardado/bloqueo mejorados: completado.

## Checklist de validación QA final

1. Usuario `estudiante`:
- No ve Evangelismo en mini sidebar.
- No ve accesos evangelismo en sidebars de módulo.
- No ve botón rápido Evangelismo en Calendario.
- Si entra por URL a `/evangelism/*`: ve “Acceso restringido”.
- Si fuerza llamada API: backend responde `403`.

2. Usuario `pastor` o `admin`:
- Ve accesos de Evangelismo.
- Navega sin bloqueos UI.
- API responde `200` en operaciones autorizadas.

## Resultado final

Control de acceso alineado end-to-end:
- Backend correcto y verificado.
- Frontend consistente por URL y por navegación.
- Riesgo de bypass por UI reducido a mínimo operativo.
