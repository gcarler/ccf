# Proyecto CCF — mapa técnico

> La guía principal y actualizada está en [`docs/GUIA_GENERAL_CCF.md`](docs/GUIA_GENERAL_CCF.md). Este archivo resume la estructura técnica del proyecto y conserva el mapa de componentes principales.

## Arquitectura

- **Frontend:** Next.js 15.5.18 con App Router, React y TypeScript en `frontend/src/`.
  - Constructor CMS: `frontend/src/components/cms/builder/`.
  - Secciones públicas: `frontend/src/components/public/cms/sections/`.
  - Renderizador público: `frontend/src/components/public/cms/PublicSectionRenderer.tsx`.
  - Navegación CMS: `frontend/src/components/cms/CmsModuleNav.tsx`.
  - Workspace autenticado: `frontend/src/app/plataforma/`.
- **Backend:** FastAPI, SQLAlchemy y PostgreSQL en producción; SQLite para desarrollo/pruebas.
  - API CMS: `backend/api/cms_v2/` y `backend/api/cms/`.
  - Modelos CMS: `backend/models_cms.py`.
  - Registro de routers: `backend/app.py`.
  - Auth y permisos: `backend/api/auth_v3.py` y `backend/core/permissions.py`.
  - Identidad y tenant: `backend/models_kernel.py` y `backend/core/tenant.py`.
- **Migraciones:** Alembic en `alembic/canonical_versions/`.
- **Pruebas:** pytest en `tests/`, Vitest en `frontend/src/` y Playwright en `frontend/tests/e2e/`.

## Componentes CMS registrados

El CMS está organizado en tres superficies que deben mantenerse separadas:

1. **CMS v1:** compatibilidad de media, optimización y métricas.
2. **CMS v2:** sitios, páginas, versiones, secciones, temas, menús, posts, categorías, tags, preview y publicación.
3. **Enterprise CMS:** auditoría, permisos de contenido, notificaciones, webhooks, tipos personalizados, búsqueda, sesiones, carpetas, redirecciones y enlaces rotos.

## Hitos históricos del constructor CMS

| Hito | Alcance | Estado documentado |
|---|---|---|
| R1 | Bloques `animated_counter`, `video_embed`, `gallery_masonry` y `map_embed` | Completado |
| R2 | Presencia en tiempo real mediante WebSocket y barra de avatares | Completado |
| R3 | Pruebas A/B | Implementado según el router y la navegación actuales; verificar el contrato CMS antes de ampliar |
| R4 | Comentarios de publicaciones | Implementado según el router y la navegación actuales |
| R5 | Búsqueda de texto completo | Implementada en la superficie Enterprise CMS |
| Final | Verificación E2E, typecheck y gates de calidad | Validar mediante `scripts/test_cms_quality.py` y los comandos frontend |

Los estados detallados y la evidencia vigente están en `docs/ESTADO_CMS.md`, `docs/ARQUITECTURA_CMS.md` y `docs/CMS_QA_CHECKLIST.md`.

## Archivos backend de referencia

- `backend/api/cms_v2/`
- `backend/api/cms/`
- `backend/api/enterprise_cms.py`
- `backend/api/auth_v3.py`
- `backend/api/crm/`
- `backend/api/evangelism.py`
- `backend/api/academy.py`
- `backend/api/projects.py`
- `backend/models_cms.py`
- `backend/models_kernel.py`
- `backend/core/permissions.py`
- `backend/core/tenant.py`

## Páginas y componentes frontend de referencia

- `frontend/src/components/cms/builder/constants.ts`
- `frontend/src/components/cms/builder/BuilderSectionInspector.tsx`
- `frontend/src/components/public/cms/PublicSectionRenderer.tsx`
- `frontend/src/components/cms/CmsModuleNav.tsx`
- `frontend/src/components/WorkspaceLayout.tsx`
- `frontend/src/components/ProtectedRoute.tsx`
- `frontend/src/lib/http.ts`
- `frontend/src/context/AuthContext.tsx`
- `frontend/src/app/plataforma/cms/`
- `frontend/src/app/plataforma/crm/`
- `frontend/src/app/plataforma/academy/`
- `frontend/src/app/plataforma/evangelism/`
- `frontend/src/app/plataforma/projects/`

## Reglas de mantenimiento

1. Leer `docs/GUIA_GENERAL_CCF.md` antes de trabajar en un área desconocida.
2. Consultar el contrato API y la matriz RBAC del módulo afectado.
3. Tratar cambios en `personas.id`, `sede_id`, Auth, permisos, `apiFetch` o componentes del workspace como cambios de plataforma compartida.
4. No crear entidades paralelas para personas, cursos, grupos o contenido si ya existe un contrato canónico.
5. No editar migraciones ya desplegadas; crear una nueva migración correctiva.
6. Ejecutar el gate proporcional y actualizar la documentación cuando cambie un contrato.
