# Contratos API — Módulo Wiki

**Actualizado:** 2026-07-18
**Base path:** `/api/wiki`
**Router:** `backend/api/wiki.py`

---

## Páginas

### `GET /api/wiki/pages`
Lista páginas activas de la sede actual.

**Query params:** `search?`, `category?`, `limit=50`, `offset=0`

**Respuesta:** `[{ id, page_key, title, content, version, category, tags, sede_id, author_id, created_at, updated_at }]`

### `GET /api/wiki/pages/count`
Retorna el conteo total de páginas.

### `GET /api/wiki/pages/{page_key}`
Obtiene una página por key. Si no existe, retorna una página virtual (200 con content="" y version=0). Si fue eliminada, retorna 404.

### `POST /api/wiki/pages/{page_key}`
Crea una nueva página.

**Body:** `WikiPageCreate { page_key, title, content, category?, tags? }`

**Respuesta:** 201 + WikiPageRead

**Errores:** 409 si la página ya existe

### `PATCH /api/wiki/pages/{page_key}`
Actualiza una página existente. Incrementa `version` automáticamente y crea un snapshot en `WikiPageVersion`.

**Body:** `WikiPageUpdate { title?, content?, category?, tags? }`

### `DELETE /api/wiki/pages/{page_key}`
Soft delete. Retorna 204. GET posterior retorna 404.

---

## Versiones

### `GET /api/wiki/pages/{page_key}/versions`
Lista el historial de versiones de una página.

---

## Categorías

### `GET /api/wiki/categories`
Lista las categorías disponibles en la sede.
