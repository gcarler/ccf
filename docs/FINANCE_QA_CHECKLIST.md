# QA Checklist — Módulo Finance

**Fecha:** 2026-07-18

---

## Backend

### Transacciones
- [ ] `GET /api/finance/transactions` lista transacciones
- [ ] `GET /api/finance/summary` retorna resumen financiero
- [ ] Las transacciones se filtran por sede del usuario

### Donaciones
- [ ] `GET /api/donation-categories` lista categorías
- [ ] `POST /api/donation-categories` crea categoría
- [ ] Las donaciones están asociadas a una sede

### Multi-tenant
- [ ] ⚠️ Transacciones de sede A no visibles desde sede B
- [ ] ⚠️ Resúmenes financieros consideran sede

---

## Tests

- [ ] `test_finance_api.py` pasa
- [ ] `scripts/test_finance_quality.py` pasa
