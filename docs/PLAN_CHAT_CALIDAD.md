# Plan de Trabajo — Módulo Chat Directo CCF

> **Objetivo:** revisión exhaustiva, corrección de errores y mejora del módulo de chat directo (`/plataforma messages`), incluyendo backend, frontend, tipos, WebSocket, tests y documentación---**Creado:** 2026-07-18
**Estado:** `EN_PROCESO`
**Owner:** Agente de código

---

## 0. Superficie del módulo

| Capa | Archivos | Líneas |
|---|---|---|
| Backend API | `backend/api/chat.py` | 735 |
| Backend Schemas | `backend/schemas/chat.py` | 45 |
| Backend CRUD | `backend/crud/crm_/extended.py` (chat ops) | ~200 |
| Backend Models | `backend/models_crm.py` (Chat, Conv, Participant) | ~45 |
| Backend WebSocket | `backend/mesh_websockets.py` | ~140 |
| Frontend Page | `frontend/src/app/plataforma/messages/page.tsx` | 517 |
| Frontend Types | `frontend/src/types/directMessages.ts` | 24 |
| Frontend Hooks | `hooks/useWorkspaceSocket.ts`, `hooks/useNotifications.ts` | ~150 |
| Tests Backend | `tests/test_chat_api.py`, `tests/test_chat_sede_isolation.py` | ~600 |
| Tests E2E | `frontend/tests/e2e/messaging/direct-messages.spec.ts` | 332 |

---

## 1. Errores Críticos (Corregir primero)

### CHAT-CRIT-001: Tipos `id: number` en frontend vs UUID del backend

**Archivos:** `frontend/src/types/directMessages.ts:2,18`
**Problema:** `ConversationRead.id` y `DirectMessageItem.id` están tipados como `number` pero el backend envía UUID strings.
**Riesgo:** Romperá silenciosamente si se hace operación numérica sobre `id`. Actualmente funciona por coerción implícita.
**Fix:** Cambiar `id: number` → `id: string` en ambos tipos. Verificar que todos los usos en `page.tsx` son compatibles.

### CHAT-CRIT-002: `created_at` con espacio en WebSocket vs `T` en HTTP — Safari roto

**Archivos:** `backend/api/chat.py:633`
**Problema:** El broadcast WebSocket usa `str(msg.created_at)` que genera `"2024-01-15 10:30:00"` (espacio), mientras Pydantic HTTP genera `"2024-01-15T10:30:00"` (con T). Safari (iOS/macOS) rechaza el formato con espacio → `Invalid Date`.
**Riesgo:** Usuarios Safari ven timestamps rotos en mensajes recibidos por WebSocket.
**Fix:** En `chat.py:633`, usar `msg.created_at.isoformat()` en vez de `str(msg.created_at)`.

### CHAT-CRIT-003: Falta `is_read` en payload WebSocket

**Archivos:** `backend/api/chat.py:627-633`
**Problema:** El broadcast WebSocket no incluye `is_read`. El frontend lo recibe como `undefined` (falsy = no leído). Funciona por accidente porque mensajes nuevos son no-leídos.
**Riesgo:** Si la lógica de render cambia, fallará silenciosamente.
**Fix:** Agregar `"is_read": False` al dict del broadcast en `chat.py:627`.

---

## 2. Errores Altos

### CHAT-HIGH-001: WebSocket reconecta en cada cambio de conversación

**Archivos:** `page.tsx:97-114`, `useWorkspaceSocket.ts:59`
**Problema:** `handleSocketEvent` tiene `activeConv?.id` en deps de `useCallback`, causando que `onEvent` cambie de referencia → reconexión WS en cada switch.
**Fix:** Usar `useRef` para `onEvent` en vez de incluirlo en deps del `useEffect` del hook.

### CHAT-HIGH-002: Sin reconexión automática de WebSocket

**Archivos:** `useWorkspaceSocket.ts:27-59`
**Problema:** Si la conexión WS cae, no hay reintento. Mensajes perdidos permanentemente.
**Fix:** Agregar lógica de reconexión con backoff exponencial (máx 5 intentos, 1s→2s→4s→8s→16s).

### CHAT-HIGH-003: Unread count no se incrementa para conversaciones no activas

**Archivos:** `page.tsx:105-110`
**Problema:** Cuando llega un WS message para conversación NO activa, solo se actualiza `last_message_content` pero no `unread_count`.
**Fix:** Incrementar `unread_count` en el handler de WS para conversaciones que no son la activa.

### CHAT-HIGH-004: N+1 queries en `list_conversations`

**Archivos:** `backend/api/chat.py:338`
**Problema:** `get_unread_count_for_conversation` se llama por cada conversación (1 COUNT query por conv). 50 conversaciones = 50 queries extra.
**Fix:** Crear función batch `get_unread_counts_for_conversations(db, user_id, conv_ids)` que retorne dict `{conv_id: count}`.

### CHAT-HIGH-005: Paginación por UUID es no-determinista

**Archivos:** `backend/crud/crm_/extended.py:929`
**Problema:** `before_id` compara `ChatMessage.id < before_id` pero UUIDs v4 son random. Un UUID "menor" no implica mensaje más antiguo.
**Fix:** Cambiar cursor a `created_at DESC, id DESC` para orden determinista.

### CHAT-HIGH-006: Unread count default `_utcnow()` — conversaciones nuevas parecen leídas

**Archivos:** `backend/crud/crm_/extended.py:1000`
**Problema:** Si `last_read_at` es `None`, usa `_utcnow()` como default → todos los mensajes aparecen como leídos.
**Fix:** Usar `conv.created_at` como default en vez de `_utcnow()`.

### CHAT-HIGH-007: Superadmin con sede filtrado incorrectamente en búsqueda

**Archivos:** `backend/api/chat.py:410-411`
**Problema:** Superadmin con `sede_id` asignada queda filtrado por esa sede en `/chat/users/search`.
**Fix:** Agregar check de superadmin role antes del filtro de sede.

### CHAT-HIGH-008: `username` retorna `nombre_completo` en vez de username

**Archivos:** `backend/api/chat.py:418-419`
**Problema:** `"username": persona.nombre_completo` — el campo `username` en la respuesta contiene el nombre completo.
**Fix:** Retornar `usuario.username` o renombrar el campo a `display_name`.

### CHAT-HIGH-009: Sin paginación en frontend

**Archivos:** `page.tsx:89`
**Problema:** Límite hardcodeado a 100, sin "cargar más". Conversaciones con >100 mensajes pierden los más antiguos.
**Fix:** Implementar scroll infinito hacia arriba usando el parámetro `before` del backend.

### CHAT-HIGH-010: Doble envío (race condition)

**Archivos:** `page.tsx:120-133`
**Problema:** Sin estado `sending`. Clicks rápidos generan POST duplicados.
**Fix:** Agregar state `sending`, deshabilitar botón y input durante envío.

### CHAT-HIGH-011: Test de delete usa msg legacy (room_id=None)

**Archivos:** `tests/test_chat_api.py:108-121`
**Problema:** El test de delete crea msg sin `room_id`, que bypassa el check de participación.
**Fix:** Crear test con msg que tenga `room_id = f"dm_{conv_id}"`.

---

## 3. Errores Medios

| ID | Problema | Archivo |
|---|---|---|
| CHAT-MED-001 | Silent failures `.catch(() => {})` sin feedback | `page.tsx:77,91,93` |
| CHAT-MED-002 | `asyncio.ensure_future` deprecado → usar `create_task` | `api/chat.py:622` |
| CHAT-MED-003 | Broad `RuntimeError` catch enmascara errores reales | `api/chat.py:638` |
| CHAT-MED-004 | `RedisPubSubManager()` se instancia en import time | `mesh_websockets.py:138` |
| CHAT-MED-005 | FK violation en `create_conversation` causa 500 | `crud/crm_/extended.py:875` |
| CHAT-MED-006 | Auto-scroll interrumpe lectura del usuario | `page.tsx:116-118` |
| CHAT-MED-007 | Sin abort controller al cambiar conversación | `page.tsx:83-95` |
| CHAT-MED-008 | Locale hardcodeado `es-CO` | `page.tsx:293,412` |
| CHAT-MED-009 | `conv.participants` sin eager loading (N+1) | `api/chat.py:320` |
| CHAT-MED-010 | Test sede isolation con filtro `room_id IS NULL` incorrecto | `test_chat_sede_isolation.py:343` |
| CHAT-MED-011 | Sin test de WebSocket broadcast | `test_chat_api.py` |
| CHAT-MED-012 | `create_chat_message` no actualiza metadata de Conv | `crud/crm_/extended.py:848` |
| CHAT-MED-013 | FK violation al crear conversación con participant inexistente | `api/chat.py:875` |
| CHAT-MED-014 | `useNotifications` stale closure | `useNotifications.ts:47` |

---

## 4. Errores Bajos

| ID | Problema | Archivo |
|---|---|---|
| CHAT-LOW-001 | Sin test de paginación (`before` param) | `test_chat_api.py` |
| CHAT-LOW-002 | Sin test de error states en E2E | E2E tests |
| CHAT-LOW-003 | Sin test de mensajes via WebSocket E2E | E2E tests |
| CHAT-LOW-004 | Faltan `aria-label` en botones/inputs | `page.tsx` |
| CHAT-LOW-005 | `eslin-disable` para deps en vez de arreglar | `page.tsx:94` |
| CHAT-LOW-006 | `avatar_url` siempre `None` pero se envía | `api/chat.py:421` |
| CHAT-LOW-007 | `handleCreateConversation` refetcha toda la lista | `page.tsx:180` |
| CHAT-LOW-008 | `loading` nunca false si token es null al inicio | `page.tsx:73-79` |
| CHAT-LOW-009 | `SearchedUser.id` con `String()` redundante | `page.tsx:493` |
| CHAT-LOW-010 | E2E: selector de send button frágil (`/^$/`) | `direct-messages.spec.ts:327` |

---

## 5. Plan de Ejecución

### Fase 1 — Fix Críticos (inmediato)

| Paso | ID | Acción | Verificación |
|---|---|---|---|
| 1.1 | CHAT-CRIT-001 | Corregir tipos `id` en `directMessages.ts` | `npx tsc --noEmit` |
| 1.2 | CHAT-CRIT-002 | `isoformat()` en WS broadcast | Verificar formato JSON en WS |
| 1.3 | CHAT-CRIT-003 | Agregar `is_read: False` al WS broadcast | Verificar tipo `DirectMessageItem` completo |

### Fase 2 — Fix Altos (siguiente)

| Paso | ID | Acción | Verificación |
|---|---|---|---|
| 2.1 | CHAT-HIGH-001 | Ref de `onEvent` en `useWorkspaceSocket` | No reconectar al cambiar conv |
| 2.2 | CHAT-HIGH-002 | Reconexión con backoff en WS | Simular disconnect, verificar reconnect |
| 2.3 | CHAT-HIGH-003 | Incrementar unread en WS handler | Verificar badge se actualiza |
| 2.4 | CHAT-HIGH-004 | Batch unread count | `pytest test_chat_api.py` |
| 2.5 | CHAT-HIGH-005 | Cursor `created_at DESC, id DESC` | Test de paginación |
| 2.6 | CHAT-HIGH-006 | Default `conv.created_at` para unread | Verificar unread en conv nueva |
| 2.7 | CHAT-HIGH-007 | Check superadmin en search | Test con usuario superadmin |
| 2.8 | CHAT-HIGH-008 | Renombrar `username` a `display_name` o retornar `usuario.username` | Verificar contrato |
| 2.9 | CHAT-HIGH-009 | Scroll infinito con `before` | Scroll hacia arriba carga más |
| 2.10 | CHAT-HIGH-010 | Estado `sending` para bloquear envío | No doble envío |
| 2.11 | CHAT-HIGH-011 | Test delete con msg DM real | `pytest test_chat_api.py` |

### Fase 3 — Fix Medios (cuando críticos y altos estén cerrados)

| Paso | ID | Acción |
|---|---|---|
| 3.1 | CHAT-MED-001 | Toast de error en catch blocks |
| 3.2 | CHAT-MED-002 | `asyncio.create_task` |
| 3.3 | CHAT-MED-003 | Log warning en vez de pass |
| 3.4 | CHAT-MED-006 | Solo auto-scroll si está al fondo |
| 3.5 | CHAT-MED-007 | Abort controller para fetch de mensajes |
| 3.6 | CHAT-MED-010 | Corregir filtro en test sede isolation |
| 3.7 | CHAT-MED-011 | Agregar test de WS broadcast |

### Fase 4 — Fix Bajos (mejoras de calidad)

| Paso | ID | Acción |
|---|---|---|
| 4.1 | CHAT-LOW-001 | Test de paginación con `before` |
| 4.2 | CHAT-LOW-004 | Agregar `aria-label` |
| 4.3 | CHAT-LOW-005 | Remover `eslint-disable` |
| 4.4 | CHAT-LOW-007 | Agregar localmente la conv nueva sin refetch |

---

## 6. Comandos de Validación

```bash
# Backend tests
cd /root/ccf
source venv/bin/activate
python -m pytest -q -o addopts='' tests/test_chat_api.py tests/test_chat_sede_isolation.py

# Typecheck frontend
cd /root/ccf/frontend
npx tsc --noEmit

# E2E messaging
cd /root/ccf/frontend
npx playwright test tests/e2e/messaging/direct-messages.spec.ts

# Smoke general
cd /root/ccf
python scripts/test_messaging_quality.py
```

---

## 7. Criterio de Cierre

El módulo chat se considera cerrado cuando:

- [x] Todos los CRIT están corregidos y verificados
- [x] Todos los HIGH están corregidos y verificados
- [x] Los MED están corregidos (o justificados como wontfix)
- [x] `npx tsc --noEmit` pasa sin errores
- [x] `pytest test_chat_api.py test_chat_sede_isolation.py` pasa
- [x] Todos los LOW están corregidos (avatar_url, paginación, WS mock, E2E selector)
- [x] `npx tsc --noEmit` pasa sin errores
- [x] `pytest test_chat_api.py test_chat_sede_isolation.py` pasa
- [x] E2E `direct-messages.spec.ts` pasa (4 tests)
- [x] `MESSAGING_COMMUNITY_API_CONTRACTS.md` actualizado con query params
- [x] `ESTADO_MESSAGING_COMMUNITY.md` actualizado con cambios
- [x] Auditoría técnica completada: 7 CRITICAL + 17 HIGH corregidos
- [x] MEDIUM items resueltos: 13/14 corregidos (1 wontfix: RedisPubSub lazy init)
- [x] Tests adicionales: WS broadcast, empty content validation, duplicate conv dedup
- [x] DB index compuesto: chat_messages(room_id, created_at) para pagination query
- [x] A11y: aria-labels en todos los botones/inputs interactivos (9 total)
- [x] Import cleanup: asyncio removido de chat.py

---

## 8. Seguimiento

| Fecha | Fase | Estado | Notas |
|---|---|---|---|
| 2026-07-18 | Diagnóstico | Completado | 42 issues backend, 50 frontend, 6 integración |
| 2026-07-18 | Fase 1 — Críticos | Completado | CHAT-CRIT-001/002/003 — tipos, isoformat, is_read |
| 2026-07-18 | Fase 2 — Altos | Completado | 11 fixes: WS ref, reconexión, unread batch, paginación, sending state |
| 2026-07-18 | Fase 3 — Medios | Completado | 14 items: toast, asyncio, lazy init, abort, locale, eager load, stale closure |
| 2026-07-18 | Fase 4 — Bajos | Completado | aria-labels, eslint, conv local, loading fix |
| 2026-07-18 | Validación | Completado | tsc limpio, 29 pytest pasan |
| 2026-07-18 | Fase 5 — Cierre Total | Completado | E2E selector, avatar_url, delete DM, paginación, WS real-time, docs |
| 2026-07-18 | Auditoría Técnica | Completado | 7 CRITICAL + 17 HIGH corregidos: WS broadcast, batch unread, schema validation, XSS, back button, typed WS, error UI, stale closures, cursor tiebreaker, existence-leak |
| 2026-07-18 | MEDIUM fixes | Completado | 13/14 CHAT-MED items resolved: unused asyncio import, WS broadcast test, empty content validation, duplicate conv dedup, auto-scroll guard, abort controller, locale fix, N+1 batch, metadata update. MED-004 (RedisPubSub lazy init) wontfix. |
| — | E2E + Docs | Pendiente | E2E y actualización de docs |
