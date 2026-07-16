# Plan de Calidad — Modulo de Messaging / Community CCF

> **Objetivo:** cerrar mensajeria y comunidad como modulo operativo propio, separando inbox interno, chat directo, superficies publicas y bridge CRM para evitar regresiones cruzadas.

## 1. Regla de trabajo

- No mezclar fixes de `messaging`, `chat`, `community` y `crm bridge` sin identificar primero el owner real del fallo.
- Cada cambio debe mapearse a un ID estable de `docs/ESTADO_MESSAGING_COMMUNITY.md`.
- Si el cambio toca auth, `apiFetch`, `WorkspaceLayout`, `personas.id` o `sede_id`, tratarlo como plataforma compartida.
- No endurecer endpoints publicos de community como “parche de seguridad” sin migracion contractual y validacion de frontend.
- Si se toca chat directo, dejar evidencia de ownership, isolation y paginacion.

## 2. Fase 0 — Diagnostico base

**ID:** `MSG-FASE0-DIAG`

Comandos:

```bash
cd /root/ccf
cat docs/ESTADO_MESSAGING_COMMUNITY.md
grep -nE "PARCIAL-|PEND-" docs/ESTADO_MESSAGING_COMMUNITY.md
./venv/bin/python scripts/test_messaging_quality.py
```

Validacion minima ampliada:

```bash
cd /root/ccf
./venv/bin/python -m pytest -q -o addopts='' \
  tests/test_messaging.py \
  tests/test_messaging_api.py \
  tests/test_messaging_sede_isolation.py \
  tests/test_chat_sede_isolation.py
```

Criterio de salida:

- El fallo queda clasificado como `notifications`, `chat`, `community`, `crm bridge`, `RBAC`, `sede isolation` o `frontend state`.
- No se toca UI antes de confirmar si el contrato backend ya esta roto.

## 3. Fase 1 — Inbox interno y notificaciones

**IDs:** `PEND-MESSAGING-SMOKE-001`, `PARCIAL-MESSAGING-SPLIT-001`

Orden:

1. Validar `GET /api/messaging/notifications`.
2. Validar `PATCH /api/messaging/notifications/{id}` con ownership.
3. Validar `POST /api/messaging/notifications/mark-all-read`.
4. Validar `GET /api/messaging/history` con filtro por sede.
5. Validar `POST /api/messaging/send` sin envio cross-sede.

Criterio de salida:

- Ningun usuario puede leer o mutar notificaciones ajenas.
- Historial y envio respetan `sede_id`.
- La UI de bandeja no depende de un contrato no documentado.

## 4. Fase 2 — Chat directo

**IDs:** `PEND-CHAT-CONTRACT-001`, `PEND-FRONTEND-DEEP-MESSAGING-001`

Orden:

1. Cerrar contrato de `/api/chat/users/search`.
2. Cerrar listado y creacion de conversaciones.
3. Definir contrato de paginacion/carga incremental para mensajes.
4. Confirmar `404` uniforme para rechazos que no deben filtrar existencia.
5. Confirmar delete self-only y lectura solo para participantes.

Comando minimo:

```bash
cd /root/ccf
./venv/bin/python -m pytest -q -o addopts='' tests/test_chat_sede_isolation.py
```

Cobertura frontend vigente:

```bash
cd /root/ccf/frontend
npm run test:e2e:messaging
npm run test:e2e:messaging:deep
```

Criterio de salida:

- Chat directo queda documentado por permiso, ownership y paginacion.
- No hay fugas cross-user ni cross-sede.

## 5. Fase 3 — Community publica y mutaciones autenticadas

**IDs:** `PARCIAL-COMMUNITY-PUBLIC-001`, `PEND-MESSAGING-RBAC-001`

Orden:

1. Separar claramente endpoints publicos y autenticados.
2. Confirmar contrato de `cards`, `grupos` y `events`.
3. Decidir si `POST/DELETE /community/cards` siguen publicos o migran con rollout.
4. Si se endurece auth, actualizar frontend y docs en el mismo cambio.

Criterio de salida:

- No se rompe la experiencia publica por hardening improvisado.
- La firma real coincide con `MESSAGING_COMMUNITY_API_CONTRACTS.md` y `MESSAGING_COMMUNITY_RBAC_MATRIX.md`.

## 6. Fase 4 — Bridge CRM

**ID:** `MSG-CRM-BRIDGE-001`

Orden:

1. Validar `/api/crm/messaging/send`.
2. Validar `/api/crm/messaging/history`.
3. Confirmar scope por persona y sede.
4. Verificar que CRM no duplique logica de `/api/messaging/*`.

Criterio de salida:

- El historial pastoral sigue siendo distinto del inbox interno.
- El owner del bug queda definido entre CRM y Messaging antes de tocar dos modulos.

## 7. Fase 5 — Smoke frontend dedicado

**ID:** `MSG-FASE5-FRONTEND`

Rutas minimas:

- `/plataforma/inbox/messages`
- `/plataforma/messages`
- `/plataforma/community`
- `/plataforma/community/events`

Smoke frontend dedicado:

```bash
cd /root/ccf/frontend
npm run test:e2e:messaging
```

Checks manuales complementarios:

- consola limpia de `401`, `403`, `404`, `500`
- no hay `_next/static` rotos
- bandeja carga historial controlado
- chat no fuga conversaciones ajenas
- community publica carga sin romper layout

Criterio de salida:

- Existe smoke frontend dedicado y el checklist manual queda como cobertura complementaria.

## 8. Fase 6 — QA final y release

**ID:** `MSG-FASE6-QA`

Comandos minimos:

```bash
cd /root/ccf
./venv/bin/python scripts/test_messaging_quality.py
./venv/bin/python -m pytest -q -o addopts='' \
  tests/test_messaging.py \
  tests/test_messaging_api.py \
  tests/test_messaging_sede_isolation.py \
  tests/test_chat_sede_isolation.py
```

Si se toca community publica o bridge CRM:

```bash
cd /root/ccf
./venv/bin/python -m pytest -q -o addopts='' \
  tests/test_api_integration.py \
  tests/test_structural_contracts.py
```

Criterio de salida:

- `docs/ESTADO_MESSAGING_COMMUNITY.md` se actualiza si cambia backlog o estado.
- El cambio queda en la capa propietaria.
- No se aprueba regresion de auth, isolation o chat privado por arreglar una sola vista.
