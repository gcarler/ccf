# QA Checklist — Messaging / Community

## 1. Antes de tocar codigo

- Leer `ESTADO_MESSAGING_COMMUNITY.md`.
- Leer `MESSAGING_COMMUNITY_RBAC_MATRIX.md`.
- Clasificar el cambio: `messaging`, `chat`, `community`, `crm bridge` o `plataforma`.
- Si toca auth, permisos, token refresh o `apiFetch`, tratarlo como plataforma compartida.

## 2. Validacion backend minima

```bash
cd /root/ccf
./venv/bin/python scripts/test_messaging_quality.py
```

## 3. Validacion ampliada segun cambio

- Si toca chat: `tests/test_chat_sede_isolation.py`
- Si toca contratos publicos o estructura general: `tests/test_structural_contracts.py`
- Si toca CRM bridge: pruebas de `/api/crm/messaging/*`

## 4. Checks manuales obligatorios

- `GET /plataforma/inbox/messages` carga sin 401/403/500.
- `GET /plataforma/messages` no fuga conversaciones ajenas.
- `GET /plataforma/community` carga cards y accesos sin romper consola.
- `GET /plataforma/community/events` lista eventos publicos o estado vacio controlado.
- `GET /plataforma/crm/messaging` mantiene historial por persona.

## 5. No aprobar si pasa esto

- historial global sin filtro por sede
- notificaciones editables por otro usuario
- envio a persona de otra sede
- cambio silencioso de endpoints publicos a privados
- `fetch()` directo nuevo en lugar de `apiFetch`

## 6. Backlog QA

- `PEND-MESSAGING-SMOKE-001` cerrada el 2026-07-16 con `scripts/test_messaging_quality.py`
- `PEND-MESSAGING-RBAC-001` cerrada el 2026-07-16 en `MESSAGING_COMMUNITY_RBAC_MATRIX.md`
- `PEND-FRONTEND-E2E-MESSAGING-001` cerrada el 2026-07-16 con `frontend/tests/e2e/messaging/smoke.spec.ts`
- `PEND-FRONTEND-DEEP-MESSAGING-001` cerrada el 2026-07-16 con `frontend/tests/e2e/messaging/direct-messages.spec.ts`
- `PEND-CHAT-CONTRACT-001`

## 7. Notas RBAC

- `messaging/history` y `messaging/send` dependen hoy de `academy:manage`, no de `messaging:*`
- `community/cards` sigue siendo público para create/delete en la firma actual
- no asumir que chat directo y bandeja interna comparten exactamente el mismo gate

## 8. Smoke frontend dedicado

```bash
cd /root/ccf/frontend
npm run test:e2e:messaging
npm run test:e2e:messaging:deep
```
