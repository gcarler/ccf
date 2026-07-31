# Estado del Módulo Chat

**Actualizado:** 2026-07-31

---

## Resumen

Módulo de mensajería interna de la plataforma. Permite conversaciones entre usuarios con aislamiento multi-tenant, @menciones, file attachments y WebSocket en tiempo real.

**Consolidación (2026-07-31):** Las rutas legacy `/plataforma/inbox/messages` y `/plataforma/community/messages` redirigen a la ruta canónica unificada `/plataforma/messages`.

| Métrica | Valor |
|---|---|
| Router DM | `backend/api/chat.py` (1,076 L) |
| Router interno | `backend/api/messaging.py` (353 L) |
| Gateway outbound | `backend/services/messaging.py` (396 L) |
| Modelos | `backend/models_conversation.py` (66 L) |
| Schemas | `backend/schemas/chat.py` (100 L) |
| Frontend canónico | `frontend/src/app/plataforma/messages/` (2,625 L) |
| Tests backend | 63 (7 archivos) |
| Tests frontend | 100 (9 archivos) |
| E2E Playwright | 5 specs en `frontend/tests/e2e/messaging/` |

---

## Contrato canónico

- Conversaciones identificadas por UUID
- Participantes referencian `personas.id`
- Aislamiento multi-tenant via `get_user_sede_id()` (Axioma 3)
- Defense-in-depth: TOCTOU protection, existence-leak safe 404, magic-byte verification en uploads
- Soft delete en mensajes
- WebSocket en tiempo real via `mesh_websockets.manager`
- @menciones con notificaciones in-app via `notify_mention`
- File attachments con validación de magic bytes y tenant isolation

---

## Backend

| Aspecto | Detalle |
|---|---|
| Router DM | `backend/api/chat.py` |
| Router interno | `backend/api/messaging.py` |
| Schemas | `backend/schemas/chat.py` |
| Modelos | `backend/models_conversation.py` |
| CRUD | `backend/crud/crm_/extended.py` |

### Endpoints principales

- `POST /chat/conversations` — Crear conversación
- `GET /chat/conversations` — Listar conversaciones del usuario
- `GET /chat/conversations/{id}/messages` — Historial de mensajes (paginado)
- `POST /chat/conversations/{id}/messages` — Enviar mensaje (con @mentions + attachments)
- `POST /chat/conversations/{id}/read` — Marcar como leído
- `DELETE /chat/messages/{id}` — Soft-delete mensaje propio
- `POST /chat/upload-attachment` — Subir archivo (magic-byte verified, tenant isolated)
- `GET /chat/users/search` — Buscar usuarios para @menciones
- `GET /messaging/history` — Historial de comunicaciones (CRM)
- `POST /messaging/send` — Enviar mensaje interno (CRM)

---

## Frontend

| Componente | Archivo |
|---|---|
| Página principal | `frontend/src/app/plataforma/messages/page.tsx` |
| Sidebar conversaciones | `_components/ConversationSidebar.tsx` |
| Burbuja de mensaje | `_components/MessageBubble.tsx` |
| Input de mensaje | `_components/MessageInput.tsx` |
| Lista de mensajes | `_components/MessageList.tsx` |
| Nuevo chat drawer | `_components/NewConversationDrawer.tsx` |
| Hook chat thread | `_hooks/useChatThread.ts` |
| Hook conversaciones | `_hooks/useConversations.ts` |
| Hook búsqueda usuarios | `_hooks/useUserSearch.ts` |
| Tipos | `frontend/src/types/directMessages.ts` |

---

## Tests

| Métrica | Valor |
|---|---|
| Backend | `tests/test_messaging*.py` (7 archivos, 63 tests) |
| Frontend | `frontend/src/app/plataforma/messages/_components/*.test.tsx` + `_hooks/*.test.ts` (9 archivos, 100 tests) |
| E2E | `frontend/tests/e2e/messaging/` (5 specs) |
| Última ejecución | 163 passed (63 backend + 100 frontend) |

---

## Documentación relacionada

- `docs/PLAN_CHAT_CALIDAD.md`
- `docs/AUDITORIA_FORENSE_CHAT.md`
- `docs/CHAT_API_CONTRACTS.md`
- `docs/CHAT_QA_CHECKLIST.md`
- `docs/CHAT_RBAC_MATRIX.md`
- `scripts/test_chat_quality.py`
- `docs/ESTADO_MESSAGING_COMMUNITY.md`
- `docs/PLAN_MESSAGING_CALIDAD.md`
- `docs/MESSAGING_COMMUNITY_API_CONTRACTS.md`
