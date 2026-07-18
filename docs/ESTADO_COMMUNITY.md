# Estado del Módulo Community

**Actualizado:** 2026-07-18

---

## Resumen

Módulo de comunidad. Gestiona descubrimiento de miembros, testimonios, eventos comunitarios, mensajes, grupos y oración.

| Métrica | Valor |
|---|---|
| Router | `backend/api/community.py` |
| CRUD | `backend/crud/crm_/community.py` |
| Frontend | `frontend/src/app/plataforma/community/` |
| Tests | Sin archivo dedicado |
| Docs | `docs/ESTADO_MESSAGING_COMMUNITY.md`, `docs/AUDITORIA_FORENSE_COMMUNITY.md` |

---

## Backend

| Endpoint | Propósito |
|---|---|
| `GET /api/community/discover` | Descubrimiento de miembros |
| `GET/POST /api/community/testimonies` | Testimonios |
| `GET/POST /api/community/events` | Eventos comunitarios |
| `GET/POST /api/community/groups` | Grupos |

---

## Multi-tenant

✅ 3 referencias a scope — correcto

---

## Tests

Sin archivo de tests dedicado. Cubierto por tests de Messaging/Community.
