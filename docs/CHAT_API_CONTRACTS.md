# Contratos API — Módulo Chat

**Actualizado:** 2026-07-18
**Router:** `backend/api/chat.py`

---

## Conversaciones

### `GET /api/chat/conversations`
Lista conversaciones del usuario autenticado.

### `POST /api/chat/conversations`
Crea una nueva conversación.

**Body:** `{ participant_ids: [uuid], subject?: string }`

### `GET /api/chat/conversations/{id}`
Detalle de conversación con mensajes.

---

## Mensajes

### `POST /api/chat/conversations/{id}/messages`
Envía un mensaje.

**Body:** `{ content: string }`

### `PATCH /api/chat/messages/{id}/read`
Marca como leído.

### `DELETE /api/chat/messages/{id}`
Elimina mensaje (soft delete).
