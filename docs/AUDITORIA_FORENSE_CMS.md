# Auditoría Forense y Validación Cruzada del CMS

## Objetivo

Auditar el CMS de extremo a extremo para encontrar y cerrar discrepancias entre:

- base de datos
- backend
- admin CMS
- preview
- render público
- caché y publicación

La regla es simple: si un contenido existe en el CMS, debe poder trazarse con evidencia en todas sus capas. Si una capa muestra algo distinto, esa discrepancia se trata como un defecto de contrato, no como un detalle visual.

## Principios

- Una sola fuente de verdad por contrato.
- Primero descubrir, luego corregir.
- Corregir la causa raíz, no el síntoma.
- No introducir compatibilidad silenciosa para ocultar datos inconsistentes.
- Cada hallazgo debe cerrar con evidencia reproducible.
- El CMS editor y el renderer público se validan por separado.

## Alcance

Auditar al menos:

- páginas CMS
- secciones y tipos de bloque
- temas y tokens
- menús y navegación
- recursos reutilizables
- media y adjuntos
- SEO y metadatos
- versiones publicadas
- preview y borradores
- rutas públicas derivadas del CMS
- redirecciones y slugs

## Fase 0. Preparación del corte

### Tareas

- Registrar fecha y hora de inicio.
- Guardar `git status --short`.
- Identificar las rutas y módulos CMS vivos.
- Listar scripts, tests y endpoints de soporte.
- Congelar el estado de referencia:
  - contenidos publicados
  - páginas con versiones
  - recursos reutilizables
  - media asociados

### Salida esperada

- Punto de corte claro.
- Inventario inicial del CMS.
- Lista de activos a validar.

## Fase 1. Inventario estructural

### Tareas

- Enumerar todas las páginas CMS y sus slugs.
- Enumerar secciones por página.
- Enumerar tipos de sección soportados.
- Enumerar temas, tokens y recursos.
- Enumerar menús, categorías, tags y redirecciones.
- Enumerar media, thumbnails y assets asociados.
- Enumerar versiones publicadas y borradores.

### Validaciones

- No hay páginas huérfanas.
- No hay secciones sin tipo válido.
- No hay recursos sin consumidor.
- No hay assets sin referencia.
- No hay slugs duplicados dentro del mismo alcance.

### Salida esperada

- Tabla maestra de inventario.
- Lista de objetos huérfanos, duplicados o incompletos.

## Fase 2. Auditoría de base de datos

### Tareas

- Comparar el esquema real con los modelos CMS.
- Revisar columnas críticas:
  - `site_id`
  - `sede_id`
  - `slug`
  - `status`
  - `published_at`
  - `version`
  - `deleted_at`
  - timestamps
- Revisar constraints e índices.
- Revisar integridad referencial.
- Detectar filas huérfanas, soft-deleted visibles y referencias rotas.

### Validaciones

- El esquema coincide con el modelo canónico.
- Los borrados suaves no reaparecen en lecturas públicas.
- Las relaciones exigidas tienen integridad.
- Las migraciones relevantes son reversibles o tienen downgrade razonable.

### Salida esperada

- Lista de discrepancias de esquema y datos.
- Priorización por severidad.

## Fase 3. Auditoría de backend

### Tareas

- Revisar routers CMS.
- Revisar CRUD de páginas, secciones, recursos, media y temas.
- Revisar validaciones de permisos.
- Revisar aislamiento por sitio/sede.
- Revisar manejo de borrado suave.
- Revisar serialización de versiones y preview.
- Revisar helpers compartidos del CMS.

### Validaciones

- Ningún endpoint crítico resuelve por `id` sin filtros de contexto.
- Ningún CRUD permite lectura o mutación fuera del sitio correcto.
- Los contratos de salida coinciden con los schemas.
- Los borrados suaves no se filtran como activos.

### Salida esperada

- Mapa de endpoints y sus contratos reales.
- Lista de defectos de contrato backend.

## Fase 4. Auditoría del panel CMS

### Tareas

- Revisar páginas de listado, edición, preview y publicación.
- Revisar formularios y validaciones.
- Revisar navegación entre módulos CMS.
- Revisar comportamiento con datos incompletos.
- Revisar feedback de errores y estados vacíos.

### Validaciones

- El admin muestra lo mismo que el backend entrega.
- Los estados de publicación son comprensibles y consistentes.
- Los formularios no aceptan combinaciones inválidas que el backend no pueda sostener.

### Salida esperada

- Lista de desalineaciones UI vs contrato.
- Casos de reproducción en el editor.

## Fase 5. Auditoría de preview y render público

### Tareas

- Comparar preview con contenido publicado.
- Comparar contenido publicado con render público.
- Revisar rutas derivadas de slug y page mapping.
- Revisar fallback cuando falta contenido CMS.
- Revisar SEO head, metadata y enlaces internos.

### Validaciones

- El preview representa exactamente el borrador esperado.
- La versión publicada representa la última versión aprobada.
- El render público no depende de datos ausentes sin fallback.
- No hay assets rotos ni secciones en blanco por mapeo incompleto.

### Salida esperada

- Lista de diferencias preview vs publicado vs público.
- Evidencia visual o textual por ruta.

## Fase 6. Auditoría de publicación y versionado

### Tareas

- Revisar flujo de crear, editar, versionar, publicar y revertir.
- Revisar historial de versiones.
- Revisar timestamps y orden temporal.
- Revisar invalidación de caché al publicar.
- Revisar consistencia entre versión actual y render activo.

### Validaciones

- Una publicación produce un estado trazable.
- Un rollback restaura el contenido esperado.
- La caché no deja contenido obsoleto visible.
- Las versiones son distinguibles y recuperables.

### Salida esperada

- Línea de tiempo de publicación.
- Lista de fallos de sincronización.

## Fase 7. Auditoría de seguridad e aislamiento

### Tareas

- Verificar aislamiento por sitio/sede.
- Verificar permisos por rol.
- Verificar protección de soft delete.
- Verificar acceso a recursos y media.
- Verificar colisiones de slug y acceso cruzado.

### Validaciones

- Ningún contenido de otro sitio aparece por lectura directa.
- Ningún borrado suave se rehidrata por error.
- Ningún recurso queda expuesto fuera de su contexto.

### Salida esperada

- Lista de riesgos de seguridad CMS.
- Hallazgos con impacto multi-tenant.

## Fase 8. Evidencia y trazabilidad

### Tareas

- Registrar cada hallazgo con:
  - módulo
  - ruta
  - evidencia
  - causa raíz
  - impacto
  - severidad
  - decisión
- Guardar capturas, logs o respuestas de API cuando aplique.
- Mantener un registro único de correcciones y regresiones.

### Salida esperada

- Matriz forense de hallazgos.
- Evidencia reproducible por defecto.

## Fase 9. Corrección radical

### Orden de corrección

1. Esquema o migración, si el problema nace en la estructura de datos.
2. Backend, si el problema nace en contrato, permisos o filtros.
3. CMS admin, si el problema nace en edición o validación.
4. Renderer público, si el problema nace en consumo o fallback.
5. Scripts y herramientas, si el problema nace en validación u operación.

### Regla

- Cada corrección debe venir acompañada de una prueba nueva o ajustada.
- No se cierra un hallazgo sin regresión automatizada.

## Fase 10. Verificación final

### Criterios de cierre

- DB, backend, CMS admin, preview y render público coinciden.
- No hay secciones huérfanas ni assets rotos.
- No hay lecturas cruzadas por `id` sin scope.
- No hay publicación desincronizada.
- No hay borrados suaves visibles.
- `git status --short` queda limpio.

### Verificaciones recomendadas

- tests CMS específicos
- typecheck frontend
- audits de schema
- smoke tests de publicación y render público

## Entregables

- Inventario completo del CMS.
- Lista priorizada de discrepancias.
- Evidencia por hallazgo.
- Correcciones aplicadas.
- Pruebas nuevas o actualizadas.
- Estado final de cierre.

## Prompt para ejecutar desde otro Codex

> Ejecuta la auditoría forense del CMS en este orden:
> 1. preparación del corte
> 2. inventario estructural
> 3. auditoría de base de datos
> 4. auditoría de backend
> 5. auditoría del panel CMS
> 6. auditoría de preview y render público
> 7. auditoría de publicación y versionado
> 8. auditoría de seguridad e aislamiento
> 9. evidencia y trazabilidad
> 10. corrección radical
> 11. verificación final
>
> Reglas:
> - No ocultar inconsistencias con defaults.
> - Corregir la causa raíz.
> - Cada hallazgo debe cerrar con una prueba o audit.
> - No declarar cierre sin coincidencia entre DB, backend, admin y público.
