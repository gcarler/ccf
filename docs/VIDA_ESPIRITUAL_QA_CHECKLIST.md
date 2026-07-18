# QA Checklist — Módulo Vida Espiritual

**Fecha:** 2026-07-18
**Módulo:** Spiritual Life (`backend/api/spiritual_life.py`)

---

## Backend

### Smoke mínimo
- [ ] `GET /api/spiritual-life/milestones` retorna 200 con lista de hitos
- [ ] `POST /api/spiritual-life/milestones` crea un hito (rol manager)
- [ ] `GET /api/spiritual-life/milestones/{id}` retorna detalle de hito
- [ ] `PATCH /api/spiritual-life/milestones/{id}` actualiza hito
- [ ] `DELETE /api/spiritual-life/milestones/{id}` elimina hito (soft delete)

### Permisos RBAC
- [ ] Editor puede actualizar pero no crear hitos (403 en POST)
- [ ] Lector puede leer pero no crear (403 en POST)
- [ ] Manager puede crear, leer, actualizar, eliminar

### Multi-tenant (Axioma 3)
- [ ] Hitos creados en sede A no son visibles desde sede B
- [ ] Actualización de hito de otra sede retorna 404
- [ ] Eliminación de hito de otra sede retorna 404

### Validaciones
- [ ] Tipo de hito inválido retorna 422/400
- [ ] Persona inexistente retorna 404
- [ ] Persona de otra sede retorna 404

---

## Frontend

- [ ] Página `spiritual-life/` carga sin errores
- [ ] Timeline de hitos espirituales se renderiza
- [ ] Certificados se muestran correctamente

---

## Tests automatizados

- [ ] `test_spiritual_life_api.py` pasa 10/10
- [ ] Cobertura del router >= 80%
