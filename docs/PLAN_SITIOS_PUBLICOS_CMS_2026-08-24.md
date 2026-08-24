# Plan estructural: CMS y sitios públicos

**Fecha:** 2026-08-24  
**Estado:** aprobado para ejecución por fases  
**Rama propuesta:** `modulo/sitios-publicos`

## 1. Objetivo

Garantizar que el CMS sea la fuente única y verificable de los sitios públicos:

`CMS → API pública → Next.js → página pública → SEO/caché`

Ningún contenido editorial, imagen, menú, pastor, URL canónica o configuración
debe reaparecer desde respaldos codificados ni desde una segunda fuente cuando
el CMS lo haya eliminado, despublicado o reemplazado.

## 2. Decisiones de arquitectura

1. El contenido editorial pertenece al CMS.
2. El backend público solo expone contenido publicado y su snapshot publicado.
3. El frontend público renderiza la respuesta del CMS; sus valores por defecto
   se limitan a estados vacíos, carga y error, nunca a contenido editorial real.
4. El equipo pastoral se sirve desde el contrato pastoral canónico basado en
   `Persona`; el bloque editorial de la página solo contiene textos de interfaz
   y plantilla.
5. El `site_key`, el dominio público y las rutas canónicas se resuelven desde
   configuración centralizada; no se usarán `default` ni dominios de respaldo.
6. La caché pública se invalida en cada mutación que afecte una página, sección,
   menú, tema o perfil pastoral.

## 3. Hallazgos que se remediarán

| ID | Hallazgo | Capa propietaria | Prioridad |
|---|---|---|---|
| PUB-01 | Sitemap usa dominio y `site_key` incorrectos | Frontend/SEO | Crítica |
| PUB-02 | Imágenes fijas reaparecen en `/nosotros` cuando faltan en CMS | Frontend/CMS | Crítica |
| PUB-03 | Pastores tienen fallback entre bloque CMS y endpoint Persona | Contrato/API/Frontend | Crítica |
| PUB-04 | Página publicada sin snapshot puede leer secciones actuales | Backend/publicación | Crítica |
| PUB-05 | Bootstrap silencia páginas CMS inexistentes | Frontend/CMS | Alta |
| PUB-06 | Búsqueda y estadísticas usan `fetch` directo | Frontend/contrato HTTP | Media |
| PUB-07 | Footer vuelve a agregar enlaces eliminados del CMS | Frontend/CMS | Media |
| PUB-08 | Validar caché e invalidación de cada superficie pública | Backend/operación | Alta |

## 4. Orden de ejecución

### Fase 0 — Preparación y contrato

- Crear `modulo/sitios-publicos` desde el `origin/main` más reciente.
- Registrar el contrato de ownership de la rama.
- Congelar el inventario de páginas, menús, temas y perfiles pastorales.
- Definir una matriz CMS → endpoint → consumidor → ruta pública.
- No modificar todavía contenido productivo.

**Salida:** inventario reproducible y rama limpia.

### Fase 1 — Fuente única de contenido

- Eliminar las imágenes fijas de `/nosotros`; si CMS no entrega imágenes,
  mostrar un estado vacío visual, no fotografías históricas.
- Eliminar los fallback editoriales del footer; conservar solo fallback técnico
  mínimo para evitar una página rota.
- Retirar el fallback de pastores desde el bloque CMS.
- Mantener en el bloque `pastors` únicamente configuración visual: títulos,
  etiquetas, textos y plantilla de detalle.
- Validar que una persona pastoral no publicada o eliminada no aparezca en el
  sitio público.

**Criterio de aceptación:** eliminar o despublicar un contenido en CMS cambia
el sitio público sin que reaparezca una copia local.

### Fase 2 — Contrato backend de publicación

- Cambiar `public_page` para que una página marcada como publicada sin snapshot
  responda con estado de publicación incompleta o no publique secciones actuales.
- Garantizar que solo el snapshot publicado alimente el render público.
- Confirmar que `publish`, `unpublish`, `archive` y `rollback` invaliden la
  página, listado, SEO y búsqueda relacionados.
- Auditar y completar filtros de publicación/soft delete del equipo pastoral.
- Mantener códigos HTTP semánticos y sin cambios destructivos.

**Criterio de aceptación:** editar un borrador no cambia la página pública hasta
que exista una publicación válida.

### Fase 3 — Configuración multi-sitio y SEO

- Sustituir `default` por `SITE_KEY` centralizado en sitemap.
- Sustituir dominios fallback por `SITE_URL` obligatorio en producción.
- Generar sitemap únicamente con páginas publicadas del sitio activo.
- Excluir páginas internas de CMS como `footer` si no son rutas públicas.
- Verificar canonical, Open Graph, JSON-LD, breadcrumbs y sitemap contra el
  dominio real `https://ministerioselfaro.org`.
- Confirmar rutas especiales como `/aniversario40`.

**Criterio de aceptación:** ningún `loc`, canonical u Open Graph publicado
apunta a `ccfministerio.com`, `ccf.org`, `elfarocc.tech` o al sitio `default`.

### Fase 4 — Contrato HTTP y resiliencia frontend

- Migrar estadísticas y búsqueda interna a `apiFetch`.
- Documentar y aislar explícitamente las excepciones de formularios externos.
- Revisar estados loading, empty y error en páginas públicas.
- Evitar que errores silenciosos conviertan contenido ausente en contenido
  inventado.
- Mantener SSR/bootstrap consistente con el cliente.

**Criterio de aceptación:** todos los consumidores internos usan el contrato
HTTP común y muestran estados honestos cuando el CMS no responde.

### Fase 5 — Calidad y verificación pública

- Añadir pruebas de contrato CMS → público para páginas, secciones, menús,
  temas, pastores, caché y sitemap.
- Añadir pruebas negativas: borrado/archivo, draft sin snapshot, slug ausente,
  site key incorrecto y contenido vacío.
- Ejecutar TypeScript, ESLint, pruebas frontend, pruebas backend CMS y smoke
  público.
- Verificar producción de forma read-only:
  - `/api/cms/v2/public/sites/ccf/theme`
  - menús principal/móvil
  - páginas CMS
  - `/sitemap.xml`
  - `/nosotros`, `/pastores`, `/aniversario40`

## 5. Estrategia de commits y ramas

Cada hallazgo tendrá un commit independiente en `modulo/sitios-publicos`:

1. `fix(cms): eliminar respaldos editoriales del sitio público`
2. `fix(cms): exigir snapshot publicado en páginas públicas`
3. `fix(cms): unificar equipo pastoral con fuente canónica`
4. `fix(cms): corregir sitemap y configuración multi-sitio`
5. `fix(cms): normalizar consumidores HTTP públicos`
6. `fix(cms): cubrir contrato cms y sitios públicos`

Después de validar la rama propietaria:

1. Crear `integration/public-sites-<fecha>` desde `origin/main`.
2. Integrar únicamente `modulo/sitios-publicos`.
3. Ejecutar contrato de rama, lint, pruebas y build/validación proporcional.
4. Publicar solo la rama de integración.
5. Fusionar a `main` únicamente con todos los checks verdes.
6. Archivar la rama temporal bajo `archive/merged/` después del merge.

## 6. Rollback

- Cada commit revierte una sola intención.
- No se editarán migraciones históricas cerradas.
- Los cambios de publicación se revierten por commit y se conserva el último
  snapshot válido.
- Si el sitemap o el render público falla, se revierte primero el commit de la
  capa afectada sin tocar el contenido del CMS.
- No se eliminarán medios ni registros productivos como parte de esta fase.

## 7. Gate de cierre

El plan solo se declara completo cuando:

- el CMS es la única fuente editorial pública;
- no reaparecen imágenes, pastores ni enlaces eliminados;
- los borradores no se muestran públicamente;
- sitemap y metadata usan el dominio y sitio correctos;
- caché e invalidación fueron verificadas;
- frontend y backend pasan sus gates;
- el smoke público confirma las rutas principales y `/aniversario40`;
- la integración está fusionada a `main` y la rama temporal archivada.
