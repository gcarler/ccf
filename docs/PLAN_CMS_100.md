# Plan de Trabajo para Llevar el CMS al 100%

## Objetivo

Cerrar el CMS hasta un nivel de evidencia suficiente para afirmar, sin ambigüedad, que:

- los contratos backend y frontend coinciden,
- los datos persistidos coinciden con los modelos,
- la publicación y el preview representan el mismo contenido esperado,
- las rutas públicas consumen el CMS canónico,
- los borrados suaves, el scope por sitio y la seguridad multi-tenant están cerrados,
- no quedan discrepancias conocidas entre capas.

## Definición Operativa de 100%

El CMS se considera al 100% solo si se cumplen todos los puntos siguientes:

- Base de datos, backend, panel CMS, preview y render público coinciden en los flujos auditados.
- No existen lecturas directas por `id` que salten el scope de sitio o el soft delete.
- No hay rutas públicas, menús o sitemaps apuntando a slugs viejos o no canónicos.
- No hay warnings funcionales en lint/typecheck relacionados con el CMS.
- Los tests de contrato, aislamiento, publicación, SEO y render público pasan.
- Cada hallazgo cerrado tiene regresión automatizada.
- `git status --short` queda limpio al cierre.

## Principios de Ejecución

- Una sola causa raíz por corrección.
- El arreglo debe vivir en la capa que posee el contrato.
- No ocultar defectos con defaults, fallback opacos o UI tolerante.
- Cada cambio estructural debe dejar una prueba de cierre.
- No mezclar frontend, backend y datos salvo que el contrato lo exija.

## Fase 0. Congelar Estado

### Tareas

- Guardar inventario del workspace relevante.
- Identificar cambios pendientes fuera del CMS.
- Registrar el estado actual de:
  - backend CMS,
  - frontend CMS,
  - render público,
  - rutas SEO,
  - migraciones y esquemas.
- Tomar como referencia la auditoría forense ya escrita.

### Salida

- Punto de partida inequívoco.
- Lista de módulos CMS vivos.

## Fase 1. Contratos Backend

### Tareas

- Revisar routers CMS v1/v2.
- Revisar CRUD CMS.
- Revisar schemas y modelos.
- Cerrar cualquier acceso por `id` que no valide:
  - `site_id`,
  - `sede_id`,
  - `deleted_at`,
  - `status`,
  - ownership.
- Validar endpoints de:
  - páginas,
  - secciones,
  - temas,
  - menús,
  - media,
  - SEO,
  - publicación,
  - versiones.

### Criterio de salida

- No quedan fugas de scope conocidas.
- Los wrappers legados están cerrados o revalidados.
- Cada endpoint crítico tiene contrato explícito.

## Fase 2. Integridad de Datos

### Tareas

- Comparar esquema real vs modelos.
- Revisar constraints, FKs e índices.
- Detectar columnas o tablas huérfanas.
- Revisar soft deletes y rehidratación accidental.
- Validar coherencia entre:
  - páginas,
  - versiones,
  - secciones,
  - recursos,
  - media,
  - slugs,
  - publicación.

### Criterio de salida

- No hay drift de esquema.
- No hay referencias rotas en los datos auditados.
- Las migraciones relevantes son consistentes con el runtime.

## Fase 3. Panel CMS

### Tareas

- Revisar páginas de listado, edición, versiones, preview, publicación, media, temas, menús y recursos.
- Validar estados vacíos y datos incompletos.
- Validar que la UI no permita estados que el backend no sostenga.
- Revisar acciones peligrosas:
  - archivar,
  - restaurar,
  - publicar,
  - revertir,
  - borrar.

### Criterio de salida

- La UI refleja el contrato real.
- No hay formularios o flujos que induzcan estados inválidos.

## Fase 4. Preview y Render Público

### Tareas

- Comparar preview con contenido publicado.
- Comparar render público con la última versión publicada.
- Revisar secciones, bloques, media y fallbacks.
- Revisar canonical, robots, JSON-LD y breadcrumb.
- Revisar rutas públicas canónicas y slugs.

### Criterio de salida

- Preview, publicado y público coinciden.
- No hay rutas públicas desalineadas.
- No hay contenido CMS “fantasma” visible por fallback incorrecto.

## Fase 5. SEO, Sitemap y Rutas Canónicas

### Tareas

- Validar que el SEO manager mapee las rutas reales.
- Validar sitemap con rutas canónicas reales.
- Revisar enlaces internos del footer, banners y llamadas a acción.
- Revisar slugs que tengan variantes históricas.

### Criterio de salida

- Un solo path canónico por contenido público.
- No quedan enlaces rotos ni variantes muertas.

## Fase 6. Seguridad y Multi-Tenant

### Tareas

- Revisar aislamiento por `site_id` y `sede_id`.
- Revisar lectura y mutación cross-site.
- Revisar borrado suave y rehidratación.
- Revisar recursos públicos sensibles.
- Revisar wrappers legacy que resuelven por `id`.

### Criterio de salida

- No hay IDOR, cross-site mutation ni exposición de registros borrados.

## Fase 7. Contract Tests y Regresiones

### Tareas

- Consolidar pruebas de:
  - aislamiento,
  - publicación,
  - scheduling,
  - SEO,
  - preview,
  - render público,
  - media,
  - sections,
  - themes,
  - menus.
- Añadir regresión por cada hallazgo cerrado.
- Separar pruebas de contrato de pruebas de cobertura masiva.

### Criterio de salida

- La prueba falla antes del fix y pasa después.
- El backend CMS, el frontend CMS y el render público tienen cobertura suficiente para detectar drift.

## Fase 8. Calidad Estática

### Tareas

- Resolver warnings funcionales de lint en archivos CMS.
- Ejecutar `ruff` sobre backend CMS.
- Ejecutar `eslint` sobre frontend CMS y render público.
- Ejecutar `typecheck` en frontend.

### Criterio de salida

- Sin errores.
- Sin warnings relevantes ligados al CMS.

## Fase 9. Validación Final de Runtime

### Tareas

- Levantar backend.
- Levantar frontend.
- Validar health checks.
- Validar páginas públicas clave.
- Validar rutas CMS clave.
- Validar preview.

### Criterio de salida

- Todo responde 200 donde debe responder 200.
- Los 404/403 esperados se comportan como contrato, no como accidente.

## Fase 10. Cierre

### Tareas

- Repetir la auditoría forense de extremo a extremo.
- Marcar hallazgos cerrados y residuales.
- Confirmar que no quedan cambios sin commit.
- Guardar evidencia final.

### Criterio de salida

- Se puede declarar “100%” con respaldo verificable.

## Orden Recomendado de Ejecución

1. Congelar estado.
2. Cerrar backend.
3. Cerrar datos.
4. Cerrar panel CMS.
5. Cerrar preview y render público.
6. Cerrar SEO y rutas canónicas.
7. Cerrar seguridad y multi-tenant.
8. Cerrar pruebas de regresión.
9. Cerrar calidad estática.
10. Cerrar runtime.
11. Emitir informe final.

## Entregables

- Mapa de contratos.
- Lista de hallazgos.
- Cambios aplicados.
- Tests agregados.
- Evidencia de runtime.
- Estado final de cierre.

## Prompt de Ejecución

> Ejecuta el plan CMS 100% en este orden:
> 1. congelar estado
> 2. cerrar backend
> 3. cerrar datos
> 4. cerrar panel CMS
> 5. cerrar preview y render público
> 6. cerrar SEO y rutas canónicas
> 7. cerrar seguridad y multi-tenant
> 8. cerrar pruebas de regresión
> 9. cerrar calidad estática
> 10. cerrar runtime
> 11. emitir informe final
>
> Reglas:
> - No ocultar defectos.
> - Corregir la causa raíz.
> - Cada hallazgo debe cerrar con evidencia.
> - No declarar 100% sin cobertura de extremo a extremo.
