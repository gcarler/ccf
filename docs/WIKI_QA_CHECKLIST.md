# QA Checklist — Módulo Wiki

**Fecha:** 2026-07-18

---

## Backend

### CRUD
- [ ] `POST /wiki/pages/{key}` — crear página → 201
- [ ] `POST /wiki/pages/{key}` — duplicado → 409
- [ ] `GET /wiki/pages/{key}` — página existente → 200 con contenido
- [ ] `GET /wiki/pages/{key}` — página inexistente → 200 (virtual page)
- [ ] `GET /wiki/pages/{key}` — página eliminada → 404
- [ ] `PATCH /wiki/pages/{key}` — actualizar → 200, incrementa versión
- [ ] `DELETE /wiki/pages/{key}` — soft delete → 204
- [ ] `GET /wiki/pages` — listar con paginación
- [ ] `GET /wiki/pages?search=` — filtrar por texto
- [ ] `GET /wiki/pages?category=` — filtrar por categoría
- [ ] `GET /wiki/pages/count` — contar páginas

### Versionado
- [ ] Cada PATCH crea una versión
- [ ] `GET /wiki/pages/{key}/versions` — lista historial
- [ ] Versiones retienen contenido anterior

### Multi-tenant
- [ ] Páginas de sede A no visibles desde sede B
- [ ] Operaciones cross-sede retornan 404

### Permisos
- [ ] `wiki:read` para GET
- [ ] `wiki:edit` para POST/PATCH/DELETE
- [ ] Sin auth → 401

---

## Frontend

- [ ] Página `wiki/` carga sin errores
- [ ] Editor de wiki funciona
- [ ] Listado de documentos se renderiza

---

## Tests

- [ ] `test_wiki.py` — 30/30 passed
- [ ] `scripts/test_wiki_quality.py` — all gates pass
