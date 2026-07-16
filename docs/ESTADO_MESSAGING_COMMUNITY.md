# Estado del Modulo Messaging / Community — CCF

> **TL;DR (una linea):** Messaging / Community cubre notificaciones, inbox interno, chat directo, tablero comunitario, grupos publicos y eventos comunitarios. Comparte runtime con CRM, evangelismo, agenda y auth; no debe corregirse desde otros modulos sin probar primero el contrato propio.

**Proposito.** Handover canonico para trabajar mensajeria y comunidad como unidad funcional, sin mezclar fixes de CRM, evangelismo o plataforma compartida cuando el fallo real vive en `messaging`, `chat` o `community`.

**Regla de uso.**

- Actualizar este doc al cerrar trabajo, no antes.
- Si el cambio toca `apiFetch`, `WorkspaceLayout`, auth, permisos, `personas.id` o `sede_id`, tratarlo como cambio de plataforma compartida.
- `Community` tiene endpoints publicos deliberados; no aplicar tenant isolation ciega sin revisar contrato.

---

## 1. Leer primero (cualquier agente)

```bash
cat /root/ccf/docs/ESTADO_MESSAGING_COMMUNITY.md
cat /root/ccf/docs/MESSAGING_COMMUNITY_API_CONTRACTS.md
cat /root/ccf/docs/MESSAGING_COMMUNITY_QA_CHECKLIST.md
cat /root/ccf/docs/PLAN_ARQUITECTURA_MODULAR_CCF.md
```

## 2. Verificar entorno

```bash
python3 --version && node --version
```

## 3. Recontar superficie vigente (por si drift)

```bash
wc -l /root/ccf/backend/api/messaging.py /root/ccf/backend/api/chat.py /root/ccf/backend/api/community.py /root/ccf/backend/services/messaging.py /root/ccf/backend/schemas/notifications.py /root/ccf/backend/api/crm/pastoral.py | tail -1
wc -l /root/ccf/frontend/src/app/plataforma/community/**/*.tsx /root/ccf/frontend/src/app/plataforma/community/*.tsx /root/ccf/frontend/src/app/plataforma/messages/page.tsx /root/ccf/frontend/src/app/plataforma/inbox/messages/page.tsx /root/ccf/frontend/src/components/community/*.tsx /root/ccf/frontend/src/components/WorkspaceInbox.tsx 2>/dev/null | tail -1
```

Referencia observada el **2026-07-16**:

- Superficie frontend contada por archivos: **25**
- Superficie backend contada por archivos: **6**

## 4. Smoke test canonico

```bash
cd /root/ccf
./venv/bin/python scripts/test_messaging_quality.py
```

Smoke ampliado, si se toca chat directo, CRM bridge o vistas publicas:

```bash
cd /root/ccf
./venv/bin/python -m pytest -q -o addopts='' \
  tests/test_chat_sede_isolation.py \
  tests/test_api_integration.py \
  tests/test_structural_contracts.py
```

## 5. Ownership tecnico

| Area | Archivos | Responsabilidad |
|---|---|---|
| Inbox / notificaciones | `backend/api/messaging.py` | presencia, notificaciones, historial, envio interno |
| Chat directo | `backend/api/chat.py` | conversaciones privadas y mensajes directos |
| Community publico | `backend/api/community.py` | cards, grupos publicos, eventos publicos |
| CRM bridge | `backend/api/crm/pastoral.py` | historial y envio por persona desde CRM |
| Gateway | `backend/services/messaging.py` | stub / provider real y logging de outcome |
| UI comunidad | `frontend/src/app/plataforma/community/**` | hub comunitario, grupos, eventos, prayer, testimonios |
| UI inbox/mensajes | `frontend/src/app/plataforma/inbox/**`, `frontend/src/app/plataforma/messages/page.tsx` | bandeja, historial y chat |

## 6. Contratos vigentes

- Prefijo frontend interno: `apiFetch('/messaging/...')`, `apiFetch('/community/...')`, `apiFetch('/chat/...')`.
- `GET /api/messaging/history` ya filtra por `sede_id`; el caso historico sin filtro queda cubierto por `tests/test_messaging_sede_isolation.py`.
- `POST /api/messaging/send` valida target local por sede antes de persistir log.
- `PATCH /api/messaging/notifications/{id}` debe respetar ownership del usuario.
- `GET /api/community/cards`, `GET /api/community/grupos` y `GET /api/community/events` son publicos por diseno; no forzar auth sin migracion de contrato.
- CRM usa un bridge propio en `/api/crm/messaging/*`; no reemplaza al router `/api/messaging/*`.

## 7. Dependencias compartidas criticas

- Auth v3 y token browser
- `backend/core/permissions.py`
- `personas.id == auth_users.id`
- `sede_id` y Axioma 3
- `apiFetch` y refresh automatico
- `WorkspaceLayout`

## 8. Riesgos estructurales activos

1. **Publico vs autenticado** `[PARCIAL-COMMUNITY-PUBLIC-001]` — `community.py` mezcla endpoints publicos y autenticados; cualquier hardening debe separar contratos antes de meter auth global.
2. **Mensajeria repartida** `[PARCIAL-MESSAGING-SPLIT-001]` — inbox, chat y CRM bridge viven en routers distintos; documentar mejor ownership para evitar fixes cruzados.

## 9. Pendientes formales

1. **Script canonico del modulo** `[PEND-MESSAGING-SMOKE-001]` — cerrada el 2026-07-16 con `scripts/test_messaging_quality.py`; agrupa inbox/notificaciones, isolation/ownership y chat directo.
2. **Matriz RBAC por superficie** `[PEND-MESSAGING-RBAC-001]` — documentar admin / gestor / editor / miembro sobre inbox, chat, community publica y community admin.
3. **Contrato de chat directo** `[PEND-CHAT-CONTRACT-001]` — endurecer y cerrar contrato por rol y paginacion, aunque la superficie ya quedó mapeada.

## 10. Archivos a revisar primero si falla

1. `backend/api/messaging.py`
2. `backend/api/chat.py`
3. `backend/api/community.py`
4. `backend/services/messaging.py`
5. `frontend/src/app/plataforma/community/page.tsx`
6. `frontend/src/app/plataforma/inbox/messages/page.tsx`
7. `frontend/src/app/plataforma/messages/page.tsx`
