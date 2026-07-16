# QA Checklist — Messaging / Community

## 1. Antes de tocar codigo

- Leer `ESTADO_MESSAGING_COMMUNITY.md`.
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
- `PEND-MESSAGING-RBAC-001`
- `PEND-CHAT-CONTRACT-001`
