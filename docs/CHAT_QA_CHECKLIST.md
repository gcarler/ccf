# QA Checklist — Módulo Chat

**Fecha:** 2026-07-18

---

## Backend

### CRUD básico
- [ ] Enviar mensaje en conversación existente
- [ ] Listar mensajes de una conversación
- [ ] Marcar mensaje como leído
- [ ] Eliminar mensaje (soft delete)

### Multi-tenant
- [ ] Conversaciones de sede A no visibles desde sede B
- [ ] Mensajes cross-sede retornan 404

### Permisos
- [ ] Usuario sin acceso a conversación recibe 403/404
- [ ] Admin puede ver todas las conversaciones de su sede

---

## Tests

- [ ] `test_chat_api.py` pasa completo
- [ ] `test_chat_sede_isolation.py` pasa completo
- [ ] `scripts/test_chat_quality.py` — all gates pass
