# Estado del Módulo Chat y Mensajería

**Actualizado:** 2026-09-06 (Auditoría Forense Integral — Certificación 100/100 A+)

---

## Resumen

Módulo de mensajería interna, notificaciones y chat directo de la plataforma. Permite conversaciones 1-a-1 y grupales entre usuarios con aislamiento multi-tenant por sede (Axioma 3), @menciones, adjuntos de archivos con validación de tipo/seguridad, notificaciones y WebSocket en tiempo real.

**Consolidación canónica:** Las rutas legacy `/plataforma/inbox/messages` y `/plataforma/community/messages` redirigen a la ruta canónica unificada `/plataforma/messages`.

| Métrica | Valor |
|---|---|
| Router DM / Chat | `backend/api/chat.py` (1,363 LOC) |
| Router interno / Notificaciones | `backend/api/messaging.py` (542 LOC) |
| Gateway outbound | `backend/services/messaging.py` (415 LOC) |
| Registro de resultados | `backend/services/messaging_outcomes.py` (74 LOC) |
| Schemas chat | `backend/schemas/chat.py` (100 LOC) |
| Schemas notificaciones | `backend/schemas/notifications.py` (66 LOC) |
| Superficie Backend Total | **2,560 LOC** (15 endpoints) |
| Frontend canónico | `frontend/src/app/plataforma/messages/` + `inbox/` (**5,329 LOC** en 27 archivos) |
| Tests backend | **177 passed** (8 suites, 100% pass rate) |
| Tests frontend | **134 passed** (11 archivos vitest, 100% pass rate) |
| E2E Playwright | 5 specs en `frontend/tests/e2e/messaging/` |
| Veredicto de Calidad | **100/100 (A+) — CERTIFICADO** |

---

## Contrato canónico

- Conversaciones identificadas por UUID
- Participantes referencian `personas.id`
- Aislamiento multi-tenant via `get_user_sede_id()` (Axioma 3)
- Defense-in-depth: TOCTOU protection, existence-leak safe 404, magic-byte verification en uploads
- Soft delete en mensajes (`is_deleted` o borrado lógico; 0 `db.delete(`)
- Zonas horarias UTC canónicas (0 `datetime.utcnow`, 100% `timezone.utc`)
- WebSocket en tiempo real via `mesh_websockets.manager`
- @menciones con notificaciones in-app via `notify_mention`
- File attachments con validación de magic bytes y tenant isolation
- Frontend 100% `apiFetch`, 0 modales banned (uso de Drawer e inbox fluido)

---

## Backend

| Aspecto | Detalle |
|---|---|
| Router DM | `backend/api/chat.py` |
| Router interno / notifs | `backend/api/messaging.py` |
| Gateway de despacho | `backend/services/messaging.py` |
| Resultados | `backend/services/messaging_outcomes.py` |
| Schemas | `backend/schemas/chat.py`, `backend/schemas/notifications.py` |
| Modelos | `backend/models_conversation.py`, `backend/models_auth.py` (Notification) |
| CRUD | `backend/crud/crm_/extended.py` |

### Endpoints principales

1. `GET /messaging/notifications` — Obtención de notificaciones del usuario autenticado
2. `PATCH /messaging/notifications/{notification_id}` — Actualización de estado de lectura/archivo
3. `POST /messaging/notifications/mark-all-read` — Marcado global de lectura
4. `GET /messaging/history` — Historial de envíos masivos con filtro de sede
5. `POST /messaging/send` — Enviar mensaje masivo / broadcast
6. `GET /chat/users/search` — Búsqueda de usuarios protegida por sede con normalización NFD
7. `GET /chat/conversations` — Listar conversaciones del usuario
8. `POST /chat/conversations` — Crear conversación directa o resolver existente
9. `GET /chat/conversations/{id}/messages` — Historial de mensajes (paginado)
10. `POST /chat/conversations/{id}/messages` — Enviar mensaje (con @menciones + adjuntos)
11. `GET /chat/my-messages` — Consulta de mensajes propios
12. `GET /chat/mentions` — Consulta de menciones directas
13. `POST /chat/conversations/{id}/read` — Marcar conversación como leída
14. `DELETE /chat/messages/{id}` — Soft-delete de mensaje propio
15. `GET /chat/attachments/{conv_id}/{sede_bucket}/{filename}` — Descarga autenticada de adjuntos

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

## Auditoría Forense y Tests (2026-09-05)

| Métrica | Valor |
|---|---|
| Backend Inbox y Notificaciones | `tests/test_messaging.py`, `test_messaging_api.py`, `test_messaging_security_gaps.py`, `test_messaging_audit_phase1.py`, `test_messaging_100pct.py` (55 passed) |
| Backend Aislamiento y Ownership | `tests/test_messaging_sede_isolation.py`, `test_messaging_fase4_owner_and_crud_layer.py` (18 passed) |
| Backend Chat Directo | `tests/test_chat_sede_isolation.py`, `test_chat_100pct_coverage.py`, `test_chat_api.py`, `test_chat_gap.py`, `test_chat_extended.py` (96 passed) |
| Backend Cobertura Adicional | `tests/test_messaging_100pct_coverage.py` (8 passed) |
| Frontend Vitest | 11 archivos de test (134 passed, 100%) |
| Última ejecución total | **311 tests passed (177 backend + 134 frontend), 0 failed** |

### Corrección aplicada durante la auditoría (2026-09-05):
- **Ajuste en `toPersonaBusqueda`:** Se corrigió en `useUserSearch.ts` y `MessageInput.tsx` el mapeo de personas para incluir fallback defensivo (`nombre_completo: user.name || user.username || null`). Esto garantiza que cuentas sin nombre de pila cargado puedan buscarse directamente por `username` sin requerir anteponer `@`. Con esto, la suite de pruebas Vitest pasó de 133/134 a **134/134 aprobadas al 100%**.

---

## Documentación relacionada

- `docs/AUDITORIA_FORENSE_MENSAJERIA_2026-09-06.md` (Certificación 100/100 A+)
- `docs/PLAN_CHAT_CALIDAD.md`
- `docs/AUDITORIA_FORENSE_CHAT.md`
- `docs/AUDITORIA_FORENSE_MENSAJERIA.md`
- `docs/AUDITORIA_FORENSE_MENSAJERIA_2026-09-05.md`
- `docs/CHAT_API_CONTRACTS.md`
- `docs/CHAT_QA_CHECKLIST.md`
- `docs/CHAT_RBAC_MATRIX.md`
- `scripts/test_chat_quality.py`
- `scripts/test_messaging_quality.py`

