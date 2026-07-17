# Plan de Contenido Público del CMS CCF

> **Objetivo:** recuperar, normalizar y operar el contenido público del sitio desde el CMS como fuente canónica, sin depender de contenido accidental, snapshots de código ni fallbacks invisibles.

**Estado de ejecución:** fases 0 a 5 ejecutadas para el sitio `ccf` mediante `scripts/bootstrap_public_cms_content.py`. El bootstrap normaliza páginas canónicas, navegación, footer y contratos públicos sin depender del snapshot técnico de rescate.

## 1. Alcance

Este plan cubre el contenido público gestionado desde CMS para las rutas canónicas del sitio:

- `/`
- `/nosotros`
- `/pastores`
- `/conocer-a-jesus`
- `/eventos`
- `/predicas`
- `/cursos`
- `/sedes`
- `/boletin`
- `/testimonios`
- `/privacy`

También cubre los elementos compartidos que sostienen esas páginas:

- navegación pública,
- footer,
- SEO y canonical,
- tokens y branding del sitio,
- bloques reutilizables de CMS,
- preview y render público.

## 2. Fuente de verdad actual

Hoy el contenido público está repartido entre tres capas:

1. El CMS v2, que debe ser la fuente canónica.
2. El render público, que consume la versión publicada o usa fallback cuando falta data.
3. El snapshot de rescate en `frontend/src/lib/cms/blocks.ts`, que contiene semillas de contenido y no debe tratarse como contenido final.

El mapa de rutas y metadatos públicos vive además en:

- `frontend/src/components/public/cms/PublicSeoManager.tsx`
- `frontend/src/app/(public)/page.tsx`
- `frontend/src/components/public/cms/PublicSectionRenderer.tsx`

Hipótesis operativa:

- si el contenido "desapareció", puede estar archivado, no publicado, no sembrado o desplazado por un fallback que quedó más visible que el CMS;
- si el contenido existe en código pero no en la UI pública, la incidencia está en la publicación, el mapeo de rutas o el dataset del CMS, no en la copia editorial en sí.

## 3. Principios

- El CMS es la fuente canónica del contenido público.
- `blocks.ts` es solo snapshot de rescate o referencia de seed, no fuente final.
- No borrar fallback público hasta confirmar que el CMS publicado cubre el caso real.
- No mezclar recuperación editorial con rediseño visual.
- Cada página pública debe tener un owner de contenido y un criterio de publicación.

## 4. Diagnóstico de arranque

**Fecha:** `2026-07-17`

Hallazgo confirmado en base real:

- existen 2 sitios CMS en la base, `ccf` y `faro`;
- `ccf` tiene 28 páginas CMS registradas y todas las rutas públicas canónicas están publicadas;
- el contenido no desapareció por completo, pero quedó fragmentado entre páginas canónicas, aliases históricos y páginas internas;
- hay slugs duplicados por familia semántica, por ejemplo `home/inicio`, `about/nosotros`, `events/eventos`, `sermons/predicas`, `courses/cursos`, `locations/sedes`, `newsletter/boletin`, `privacy/privacidad`, `testimonials/testimonios`, `discover/conocer-a-jesus`, `pastors/pastores`;
- `faro` es un tenant distinto y no debe mezclarse con este plan de recuperación del sitio `ccf`.

Implicación operativa:

- la tarea no es “inventar contenido nuevo”, sino elegir qué slugs y versiones son canónicos y re-publicar la versión editorial correcta en cada ruta pública.
- el inventario de rescate debe partir de las páginas canónicas públicas, no de los aliases históricos ni del snapshot de `blocks.ts`.

## 5. Inventario editorial

### 4.1 Páginas núcleo

| Ruta | Rol editorial | Bloques/tema actuales |
|---|---|---|
| `/` | Home y entrada principal | hero, galería, feed, navegación, CTA |
| `/nosotros` | Identidad y misión | hero, historia, equipo/valores |
| `/pastores` | Liderazgo pastoral | hero, bios, retratos, contacto |
| `/conocer-a-jesus` | Onboarding espiritual | hero, pasos, CTA, recursos |
| `/eventos` | Agenda y campañas | hero, listado, vacíos, CTA |
| `/predicas` | Mensajes y archivo | hero, feed, búsqueda, canal |
| `/cursos` | Formación y Academia | hero, catálogo, rutas de inscripción |
| `/sedes` | Ubicaciones y horarios | hero, listado, mapa, horarios |
| `/boletin` | Suscripción y comunicación | hero, formulario, CTA |
| `/testimonios` | Historias y prueba social | hero, listado, estado vacío |
| `/privacy` | Política y cumplimiento | texto legal, secciones normativas |

### 4.2 Piezas compartidas

- `nav_items`
- `footer`
- `site_logo`
- `theme tokens`
- `SEO canonical`
- `breadcrumbs`

## 6. Fases

### Fase 0. Forense de pérdida

**ID:** `CMS-PUBLIC-FASE0-FORENSICA`

Tareas:

1. Levantar inventario de páginas publicadas, archivadas y borradores.
2. Revisar versiones, publish logs y estado actual de cada slug.
3. Comparar la data real con los snapshots de `frontend/src/lib/cms/blocks.ts`.
4. Confirmar si el contenido faltante fue eliminado, archivado, nunca sembrado o quedó oculto por un fallback.

Salida esperada:

- lista cerrada de páginas afectadas;
- explicación de por qué el contenido "faltó";
- punto de recuperación por ruta.

### Fase 1. Catálogo canónico

**ID:** `CMS-PUBLIC-FASE1-CATALOGO`

Tareas:

1. Definir el contenido canónico mínimo por ruta.
2. Separar contenido esencial de contenido decorativo.
3. Mapear cada página a sus bloques reutilizables del CMS.
4. Definir qué piezas deben vivir en CMS y cuáles deben seguir como fallback técnico.

Salida esperada:

- matriz editorial por ruta con campos obligatorios;
- lista de bloques reutilizables aprobados;
- lista de datos que no deben depender de hardcode.

### Fase 2. Recuperación por página

**ID:** `CMS-PUBLIC-FASE2-RECUPERACION`

Orden recomendado:

1. Home.
2. Nosotros.
3. Conocer a Jesús.
4. Eventos.
5. Prédicas.
6. Cursos.
7. Sedes.
8. Boletín.
9. Testimonios.
10. Privacy.
11. Pastores.

Tareas por página:

- recrear o restaurar el contenido desde el CMS,
- validar slugs y canonical,
- publicar una versión verificable,
- conservar fallback hasta confirmar render correcto.

Salida esperada:

- cada ruta tiene contenido publicado o un motivo explícito de ausencia;
- el render público deja de depender de texto accidental.

### Fase 3. Capas compartidas

**ID:** `CMS-PUBLIC-FASE3-SHARED`

Tareas:

1. Normalizar navegación pública y footer desde el CMS.
2. Revisar branding y tokens para que el contenido público no pierda identidad.
3. Confirmar que el SEO manager apunta al slug correcto de cada ruta.
4. Verificar que los bloques reutilizables tengan texto y defaults consistentes.

Salida esperada:

- navegación y footer quedan bajo control editorial claro;
- no hay divergencia entre metadata y página real.

### Fase 4. Preview y público

**ID:** `CMS-PUBLIC-FASE4-VALIDACION`

Tareas:

1. Comparar preview y publicado para cada ruta migrada.
2. Comparar render público con la última versión publicada.
3. Validar estados vacíos, cargas parciales y fallback.
4. Asegurar que no existan rutas canónicas rotas o contenido huérfano.

Salida esperada:

- preview, publicado y render público coinciden;
- el usuario ve contenido real, no solo placeholders.

### Fase 5. Cierre y mantenimiento

**ID:** `CMS-PUBLIC-FASE5-CIERRE100`

Tareas:

1. Documentar el owner de contenido por página.
2. Dejar checklist de publicación por ruta.
3. Convertir los snapshots de rescate en referencia, no en dependencia.
4. Añadir regresión por cada página o bloque recuperado.

Salida esperada:

- el contenido público queda operable por CMS;
- la pérdida de contenido no puede pasar silenciosamente otra vez.

## 7. Criterios de salida

El contenido público del CMS solo se considera estable cuando:

- todas las rutas públicas críticas tienen contenido canónico publicado o una ausencia justificada;
- `blocks.ts` ya no es la única fuente de texto relevante para páginas vivas;
- navegación, footer y SEO están sincronizados con el contenido publicado;
- preview y render público coinciden;
- existe regresión para el contenido recuperado;
- el plan de contenido público queda reflejado en `docs/ESTADO_CMS.md` y en `docs/CMS_QA_CHECKLIST.md`.

## 8. Ejecución actual

- Bootstrap implementado: `scripts/bootstrap_public_cms_content.py`
- Sitio objetivo: `ccf`
- Rutas canónicas verificadas y publicadas: home, nosotros, pastores, conocer a Jesús, eventos, prédicas, cursos, sedes, boletín, testimonios, privacy, footer y `_global`
- Estado operativo: el contenido público recuperado ya no depende solo del fallback de código para las rutas críticas

## 9. Riesgo principal

El mayor riesgo no es el diseño: es creer que el contenido sigue vivo cuando en realidad solo sigue existiendo como fallback técnico o snapshot de código.
