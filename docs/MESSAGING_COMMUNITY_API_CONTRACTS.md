# Contratos API — Messaging / Community

## 1. Alcance

Este documento cubre cuatro superficies distintas:

- inbox y notificaciones internas: `/api/messaging/*`
- chat directo: `/api/chat/*`
- hub comunitario publico: `/api/community/*`
- bridge CRM por persona: `/api/crm/messaging/*`

## 2. Reglas de contrato

- Frontend plataforma debe usar `apiFetch`.
- `messaging` y `chat` son autenticados.
- `community` mezcla endpoints publicos y editables; no asumir auth uniforme.
- Cuando hay `Persona`, aplica `sede_id` salvo que el endpoint publico declare la excepcion de forma explicita.

Referencia RBAC:

- `docs/MESSAGING_COMMUNITY_RBAC_MATRIX.md`

## 3. `/api/messaging/*`

Archivo: `backend/api/messaging.py`.

| Metodo | Ruta | Permiso esperado |
|---|---|---|
| `GET` | `/messaging/presence/{room}` | `messaging:read` |
| `POST` | `/messaging/notifications` | `messaging:read` |
| `GET` | `/messaging/notifications` | `messaging:read` |
| `PATCH` | `/messaging/notifications/{notification_id}` | `messaging:read` + ownership |
| `POST` | `/messaging/notifications/mark-all-read` | `messaging:read` |
| `GET` | `/messaging/history` | `messaging:read` |
| `POST` | `/messaging/send` | `messaging:edit` |

Invariantes:

- `GET /messaging/history` filtra por sede del actor.
- `POST /messaging/send` no puede enviar a una persona cross-sede.
- `PATCH /messaging/notifications/{id}` no puede mutar notificaciones ajenas.

## 4. `/api/chat/*`

Archivo: `backend/api/chat.py`.

| Metodo | Ruta | Permiso esperado |
|---|---|---|
| `GET` | `/chat/users/search` | `messaging:read` |
| `GET` | `/chat/conversations` | `messaging:read` |
| `POST` | `/chat/conversations` | `messaging:edit` |
| `GET` | `/chat/conversations/{conv_id}/messages` | `messaging:read` |
| `POST` | `/chat/conversations/{conv_id}/messages` | `messaging:edit` |
| `POST` | `/chat/conversations/{conv_id}/read` | `messaging:read` |
| `DELETE` | `/chat/messages/{message_id}` | `messaging:edit` |

Invariantes:

- solo participantes pueden leer o mutar la conversacion
- el contrato endurecido usa `404` uniforme para varios rechazos existence-leak-safe
- lectura cross-sede o cross-user no debe fugar mensajes privados
- borrar mensaje es self-only

## 5. `/api/community/*`

Archivo: `backend/api/community.py`.

| Metodo | Ruta | Auth |
|---|---|---|
| `GET` | `/community/cards` | publica |
| `POST` | `/community/cards` | publica hoy |
| `DELETE` | `/community/cards/{card_id}` | publica hoy |
| `GET` | `/community/grupos` | publica |
| `GET` | `/community/events` | publica |
| `POST` | `/community/grupos` | `community:edit` |

Notas:

- `cards`, `grupos` y `events` publicos son una excepcion intencional del contrato general Axioma 3.
- `POST/DELETE` en cards hoy no tienen gate explicito; si se endurecen, debe abrirse migracion contractual y cobertura de frontend.

## 6. `/api/crm/messaging/*`

Archivo: `backend/api/crm/pastoral.py`.

| Metodo | Ruta | Uso |
|---|---|---|
| `POST` | `/crm/messaging/send` | enviar a persona/caso desde CRM |
| `GET` | `/crm/messaging/history` | historial filtrado por persona / CRM |
| `GET` | `/crm/messaging/history/{log_id}` | detalle puntual con scope por persona/sede |

No mezclar:

- `/api/messaging/history` = inbox interno del modulo messaging
- `/api/crm/messaging/history` = historial pastoral por persona/caso

## 7. Pendientes de contrato

- `PEND-CHAT-CONTRACT-001`
- `PEND-MESSAGING-RBAC-001` cerrada el `2026-07-16` en `MESSAGING_COMMUNITY_RBAC_MATRIX.md`
- endurecimiento explicito de `community/cards`

## 8. Notas RBAC actuales

- `messaging/history` y `messaging/send` no usan `messaging:*`; usan `require_staff_or_admin` (`academy:manage`).
- `chat.py` sí separa `messaging:read` y `messaging:edit`.
- `community/cards` mantiene create/delete públicos en la firma actual.
- ver `MESSAGING_COMMUNITY_RBAC_MATRIX.md` para la matriz completa y el drift activo.
