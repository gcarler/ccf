# QA Checklist — Módulo Kernel

**Fecha:** 2026-07-18

---

## Backend

- [ ] Endpoints de identidad retornan datos correctos
- [ ] Temas visuales se pueden leer/actualizar
- [ ] `personas.id` es la identidad canónica en todas las operaciones
- [ ] Sin rutas legacy ni UUIDs enteros

---

## Tests

- [ ] Smoke script `scripts/test_kernel_quality.py` pasa
