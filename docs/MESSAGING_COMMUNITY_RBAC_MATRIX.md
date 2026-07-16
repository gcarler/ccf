# Matriz RBAC — Messaging / Community

## 1. Proposito

Este documento fija la matriz RBAC operativa de Messaging / Community contra el código actual. No describe una intención futura; documenta los guards reales y las asimetrías existentes.

La superficie se divide en cuatro bloques distintos:

- `backend/api/messaging.py`
- `backend/api/chat.py`
- `backend/api/community.py`
- bridge CRM en `backend/api/crm/pastoral.py`

## 2. Fuente de verdad inspeccionada

- `backend/api/messaging.py`
- `backend/api/chat.py`
- `backend/api/community.py`
- `backend/api/crm/pastoral.py`
- `backend/core/permissions.py`
- `backend/management/seed_user_permissions.py`

Fecha de lectura: `2026-07-16`

## 3. Permisos canónicos relevantes

Permisos canónicos:

- `messaging:read`
- `messaging:edit`
- `community:read`
- `community:edit`
- `community:manage`

Jerarquía efectiva:

- `community:manage` incluye `community:edit` y `community:read`
- `community:edit` incluye `community:read`
- `messaging:edit` incluye `messaging:read`

## 4. Capas reales de autorización

### 4.1. Roles persistidos sembrados (`RolPlataforma`)

Contrato observado en `seed_user_permissions.py`:

| Rol | Messaging efectivo esperado | Community efectivo esperado |
|---|---|---|
| `ADMINISTRADOR` | `messaging:edit` | `community:manage` |
| `GESTOR` | `messaging:edit` | `community:manage` |
| `EDITOR` | `messaging:edit` | `community:edit` |
| `LECTOR` | `messaging:read` | `community:read` |
| `MIEMBRO` | sin messaging | sin community |

### 4.2. Fallback runtime (`DEFAULT_ROLES`)

Contrato observado en `permissions.py`:

| Rol fallback | Messaging efectivo esperado | Community efectivo esperado |
|---|---|---|
| `Administrador` | `messaging:edit` | sin community explícito |
| `Gestor` | `messaging:edit` | sin community explícito |
| `Editor` | `messaging:edit` | sin community explícito |
| `Lector` | sin messaging | sin community |
| `Miembro` | sin messaging | sin community |

Asimetrías relevantes:

- `LECTOR` persistido sí tiene `messaging:read` y `community:read`
- `Lector` fallback runtime no tiene ninguno
- seed persistido sí otorga community a `GESTOR` y `EDITOR`
- fallback runtime no documenta community para esos roles

### 4.3. Allowance adicional por role fallback

`require_permission(...)` no define fallback especial para `messaging:*` ni `community:*`.

Implicación:

- Messaging y Community dependen mucho más del permiso granular persistido que Academy o CRM
- si el usuario no trae `RolPlataforma` persistido, el fallback runtime no le reconstruye community ni `messaging:read`

## 5. Matriz por superficie

### 5.1. `/api/messaging/*`

| Superficie | Guard observado | Roles que pasan hoy |
|---|---|---|
| `GET /messaging/presence/{room}` | `require_module_access("messaging", "read")` | `ADMINISTRADOR`, `GESTOR`, `EDITOR`, `LECTOR` persistido |
| `POST /messaging/notifications` | `require_module_access("messaging", "read")` | mismos que arriba |
| `GET /messaging/notifications` | `require_module_access("messaging", "read")` | mismos que arriba |
| `PATCH /messaging/notifications/{id}` | `require_module_access("messaging", "read")` + ownership | mismos que arriba, pero solo sobre notificaciones propias |
| `POST /messaging/notifications/mark-all-read` | `require_module_access("messaging", "read")` | mismos que arriba |
| `GET /messaging/history` | `require_staff_or_admin` (`academy:manage`) | no lo controla `messaging:*`; pasan quienes tengan `academy:manage` |
| `POST /messaging/send` | `require_staff_or_admin` (`academy:manage`) | igual que arriba |

Hallazgo crítico:

- la bandeja/historial interno (`history`, `send`) no está gateada por `messaging:*`
- depende del alias `require_staff_or_admin`, que hoy equivale a `academy:manage`

Implicación:

- un usuario con `messaging:read` puede ver notificaciones pero no necesariamente usar la bandeja interna
- un `GESTOR` puede pasar `history/send` por su `academy:manage`, aunque el contrato aparente hable de mensajería

### 5.2. `/api/chat/*`

Patrón observado:

- lectura de usuarios, conversaciones y mensajes: `messaging:read`
- creación de conversaciones, envío de mensajes y delete self-message: `messaging:edit`

| Superficie | Guard observado | Roles que pasan hoy |
|---|---|---|
| search users, list conversations, list messages, read markers | `require_module_access("messaging", "read")` | `ADMINISTRADOR`, `GESTOR`, `EDITOR`, `LECTOR` persistido |
| create conversation, send message, delete own message | `require_module_access("messaging", "edit")` | `ADMINISTRADOR`, `GESTOR`, `EDITOR` |

Segunda barrera:

- además del permiso, chat aplica participación, ownership y defensa cross-sede
- muchas denegaciones terminan como `404` existence-leak safe, no `403`

### 5.3. `/api/community/*`

| Superficie | Guard observado | Roles que pasan hoy |
|---|---|---|
| `GET /community/cards` | público | cualquiera |
| `POST /community/cards` | público hoy | cualquiera |
| `DELETE /community/cards/{card_id}` | público hoy | cualquiera |
| `GET /community/grupos` | público | cualquiera |
| `GET /community/events` | público | cualquiera |
| `POST /community/grupos` | `require_module_access("community", "edit")` | `ADMINISTRADOR`, `GESTOR`, `EDITOR` persistidos |

Hallazgo crítico:

- `community/cards` tiene create/delete públicos hoy, sin gate explícito
- cualquier endurecimiento aquí sería migración contractual, no bugfix local

### 5.4. `/api/crm/messaging/*`

El bridge CRM no usa `messaging:*`; vive dentro del contrato CRM.

| Superficie | Guard real |
|---|---|
| `/api/crm/messaging/send` | `crm:edit` vía router pastoral |
| `/api/crm/messaging/history*` | `crm:read` vía router pastoral |

No mezclar:

- RBAC de inbox/chat del módulo messaging
- RBAC del historial pastoral por persona dentro de CRM

## 6. Lectura correcta por rol

| Rol | Notifications | Chat directo | Messaging history/send | Community pública | Community mutación |
|---|---|---|---|---|---|
| `ADMINISTRADOR` | sí | sí | sí | sí | sí |
| `GESTOR` persistido | sí | sí | sí por `academy:manage` | sí | sí |
| `EDITOR` persistido | sí | sí | no | sí | sí |
| `LECTOR` persistido | sí | solo lectura | no | sí | no |
| `MIEMBRO` | no | no | no | sí | no |

## 7. Riesgos y drift documentados

1. `messaging/history` y `messaging/send` dependen de `academy:manage`, no de `messaging:*`.
2. `community/cards` tiene create/delete públicos hoy.
3. `LECTOR` persistido y `Lector` fallback runtime no son equivalentes.
4. community pública y community autenticada no deben tratarse como la misma política RBAC.

## 8. Reglas operativas para QA

Validar mínimo:

1. `ADMINISTRADOR` entra a toda la superficie interna
2. `GESTOR` puede operar inbox interno por `academy:manage`
3. `EDITOR` puede usar chat directo pero no necesariamente `messaging/history`
4. `LECTOR` solo lectura en notifications/chat list, no mutación de chat
5. comunidad pública debe seguir accesible si no se abre una migración contractual explícita

## 9. Estado

- `PEND-MESSAGING-RBAC-001` queda cerrada el `2026-07-16` como documentación del contrato actual
- queda deuda técnica visible sobre el gate heredado de inbox interno y la apertura pública de `community/cards`
