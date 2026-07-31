# Deuda Técnica del Backend CMS

> **Auditoría realizada:** 2026-07-29
> **Alcance:** APIs, CRUD, modelos, esquemas y servicios relacionados con CMS en el backend.

## Resumen Ejecutivo

El backend CMS presenta una **alta concentración de deuda estructural**: archivos monolíticos, duplicación de lógica entre la API v1 (`cms.py`) y la API v2 (`cms_v2/`), y patrones de consulta que pueden degenerar en N+1. La separación física entre v1 y v2 es positiva, pero el paquete `cms_v2` aún no está completamente desacoplado de `crud/cms.py`, y ambos contienen funciones muy largas.

## Métricas generales

| Módulo | Líneas | Observación |
|--------|--------|-------------|
| `backend/crud/cms.py` | 2,806 | Monolito CRUD; múltiples responsabilidades mezcladas. |
| `backend/api/cms_v2/__init__.py` | 2,606 | Router principal v2; contiene lógica de negocio, rendering y utilidades. |
| `backend/api/enterprise_cms.py` | 1,296 | Enterprise CMS; también mezcla endpoints de dominios muy distintos. |
| `backend/schemas/cms.py` | 820 | Esquemas extensos; validaciones potencialmente duplicadas con `cms_v2_sections`. |
| `backend/schemas/cms_v2_sections.py` | 744 | Esquemas de secciones v2; solapamiento con el anterior. |
| `backend/models_cms.py` | 637 | Modelos base del CMS; el resto vive en `models_enterprise.py`. |
| `backend/api/cms.py` | 689 | API v1 para testimonios, anuncios y media. |
| `backend/services/public_contact_tracking.py` | 206 | Servicio acoplado a publicaciones y contactos. |
| `backend/crud/cms_pastors_sync.py` | 303 | Sincronización pastoral; depende de CmsSite/CmsPage. |

**Total estimado:** ~11.200 líneas de backend CMS.

## Hallazgos por severidad

### 🔴 Alta

#### 1. Monolitos de código
- **`backend/crud/cms.py` (2.806 líneas)** y **`backend/api/cms_v2/__init__.py` (2.606 líneas)** concentran demasiadas responsabilidades: gestión de sitios, páginas, secciones, versiones, menús, temas, media, posts, publicaciones, SEO, redirecciones, analytics y render público.
- **Riesgo:** difícil de testear, de revisar en PR y de mantener. Un cambio menor puede impactar flujos no relacionados.
- **Recomendación:** dividir en módulos por dominio (`pages.py`, `sections.py`, `sites.py`, `media.py`, `themes.py`, `menus.py`) y mover helpers a `utils/`.

#### 2. Duplicación de lógica entre v1 y v2
- Manejo de **concurrent create unique-key conflict** aparece en:
  - `backend/crud/cms.py`
  - `backend/api/cms_v2/_shared.py`
- Existe `backend/api/cms.py` (v1) y `backend/api/cms_v2/__init__.py` (nueva). Ambos gestionan conceptos similares (testimoniales, anuncios, media) con contratos distintos.
- **Riesgo:** parches en un lado no se aplican en el otro; inconsistencias de contrato.
- **Recomendación:** consolidar helpers en `crud/cms_helpers.py` y deprecar endpoints v1 con un plan de migración documentado.

#### 3. Patrón de carga de autores (no N+1, pero acoplado)
- En `backend/api/cms_v2/__init__.py:2291` se resuelven autores de posts con `db.query(models.Persona).filter(models.Persona.id.in_(author_ids)).all()` antes del bucle, lo cual evita el N+1.
- **Riesgo:** la lógica de enriquecimiento de posts vive directamente en el router, acoplando serialización y base de datos.
- **Recomendación:** mover la carga de autores y el enriquecimiento a un servicio o serializer dedicado (ej. `_enrich_posts`).

###  Media

#### 4. Defaults hardcodeados en la API
- En `backend/api/cms_v2/__init__.py` se encuentra texto por defecto inline ("Te invitamos a ser parte de nuestra familia...").
- **Riesgo:** contenido no administrable sin desplegar código; difícil de localizar y traducir.
- **Recomendación:** mover defaults a `content_defaults.py` o configuración por sitio.

#### 5. Solapamiento de esquemas
- `backend/schemas/cms.py` y `backend/schemas/cms_v2_sections.py` pueden tener validaciones duplicadas para secciones.
- **Riesgo:** inconsistencias de validación entre creación y edición.
- **Recomendación:** auditar duplicación y extraer esquemas base reutilizables.

#### 6. `public.py` acoplado a lógica de creación de entidades
- `backend/api/public.py` crea una `Persona` y `Sede` por defecto durante la carga de documentos públicos si no existen.
- **Riesgo:** side effects inesperados en endpoints públicos; difícil de reproducir y testear.
- **Recomendación:** mover la garantía de existencia de `Persona`/`Sede` al contexto de autenticación o a un seed inicial, no a un endpoint público.

#### 7. Backend tests fragmentados
- Existen numerosos tests backend (`tests/test_cms_*.py`, `tests/test_enterprise_cms*.py`, `tests/test_crud_all_modules.py`, etc.), pero están dispersos en muchos archivos con nombres similares (`test_massive_coverage.py`, `test_fast_coverage.py`, `test_final_coverage.py`, etc.).
- **Riesgo:** dificulta saber qué cubre cada suite; posible duplicación de escenarios y confusión al agregar pruebas nuevas.
- **Recomendación:** consolidar en suites por dominio (`tests/cms/test_pages.py`, `tests/cms/test_crud.py`) y eliminar archivos de cobertura masiva redundantes.

### 🟢 Baja

#### 7. Comentarios de contexto dispersos
- Se observan referencias a `errorescms.md` y anotaciones tipo `# F-05` en varios archivos.
- **Riesgo:** sin la documentación vinculante, los comentarios son difíciles de mantener.
- **Recomendación:** convertir notas en docstrings o tickets, y vincular con tests.

#### 8. Modelos CMS divididos en dos archivos
- `models_cms.py` y `models_enterprise.py` contienen tablas CMS.
- **Riesgo:** dificulta ver el modelo de datos completo del CMS.
- **Recomendación:** considerar un solo módulo `models/cms.py` o al menos documentar la relación.

## Oportunidades de refactorización inmediata

1. **Extraer helpers de `_shared.py`** a un módulo de negocio reutilizable.
2. **Crear paquete `backend/services/cms/`** con servicios por dominio (páginas, secciones, media).
3. **Aplicar carga temprana (`selectinload`)** en endpoints de listado público.
4. **Unificar esquemas** de secciones v1 y v2.
5. **Consolidar tests backend del CMS** en `tests/cms/` y deprecar archivos de cobertura masiva.

## Métricas de deuda estimadas

| Indicador | Valor aproximado | Nota |
|-----------|------------------|------|
| Archivos monolíticos (>1.000 líneas) | 3 (`crud/cms.py`, `api/cms_v2/__init__.py`, `api/enterprise_cms.py`) | Alto riesgo de cambio. |
| Bloques de lógica duplicada | 2+ confirmados | Manejo de conflict y permisos. |
| Consultas dentro de bucles | 1 confirmado | N+1 en autores de posts. |
| Defaults hardcodeados | 1+ confirmado | Texto de bienvenida. |
| Backend tests del CMS | Múltiples suites dispersas | Consolidar y eliminar redundancia. |

## Próximos pasos recomendados

1. **Priorizar la eliminación del N+1** y la división de `api/cms_v2/__init__.py` en routers por dominio.
2. **Escribir tests backend** para `crud/cms.py` usando fixtures de base de datos.
3. **Crear un plan de consolidación v1 → v2** con cronograma de deprecación.

---

> **Generado automáticamente a partir del análisis de archivos backend.**
> Para regenerar o actualizar, revisar los archivos listados en la sección *Métricas generales*.
