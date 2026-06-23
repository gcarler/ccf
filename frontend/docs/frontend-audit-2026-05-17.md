# Auditoria frontend 2026-05-17

## Alcance

- `205` archivos `page.tsx` y `24` `layout.tsx` inspeccionados en `src/app`.
- Revision de shells principales, navegacion, centro de comandos, rutas publicas, modulos internos y senales de deuda tecnica.
- Validaciones ejecutadas durante la revision: `npm run typecheck`, `npm test`, `npm run build`, `npm run lint`.

## Hallazgos prioritarios

1. El boton "Ocultar barra" de la navegacion principal no hacia nada porque `WorkspaceMiniSidebar` recibia un callback vacio desde `WorkspaceLayout`.
2. El estado global `SidebarLayerContext` cerraba `S2` con `Esc`, pero `WorkspaceLayout` ignoraba `layers.S2`; por eso la UI podia decir "cerrado" sin ocultar el panel real.
3. El `CommandCenterProvider` si recibia comandos dinamicos de modulos como proyectos, soporte, grafo y tareas CRM, pero `CommandCenter` nunca los renderizaba. Esos comandos estaban implementados pero inutilizados.
4. La barra superior mostraba acciones de `Columnas`, `Agrupar` y `Mas opciones` aunque no hubiera handlers conectados, generando affordances falsas.
5. El build de produccion fallaba por una variable `layers` sin uso en `evangelism/faro/[id]`.
6. La analitica CRM y el resumen del dashboard mezclaban KPIs simulados con datos reales ya disponibles en `/evangelism/analytics`.
7. `support/contact` generaba un numero de caso aleatorio y `support/tickets` era una maqueta estatica pese a existir API real de tickets.
8. Las wikis embebidas persistian por navegador en `localStorage`, aunque ya existia infraestructura de contenido compartido.
9. `admin/mission-impact` mostraba contadores fijos aunque `/finance/impact` ya entregaba metricas reales.
10. La bandeja global y `community/notifications` mostraban listas falsas aunque existia `/messaging/notifications`.
11. `admin/intelligence` reemplazaba errores reales por datos inventados y tenia acciones visibles sin efecto.
12. `evangelism/events` anunciaba ocho vistas en el selector, pero solo tenia desarrolladas `grid` y `list`.
13. Los componentes universales de calendario y gantt mostraban botones sin handler (`+` y `Optimus Brain`).
14. `whiteboard` global listaba siempre vacio y la pantalla de edicion era una maqueta, aunque ya se creaban registros locales.

## Cambios aplicados

- Se conecto la visibilidad real de `S1` y `S2` con el contexto global de capas.
- Se agrego `modo enfoque` persistente por modulo para ocultar ambas barras y trabajar en fullscreen.
- Se registraron comandos globales para alternar modo enfoque y paneles laterales desde el centro de comandos.
- Se integraron los comandos dinamicos registrados por cada modulo dentro de `CommandCenter`.
- Se reemplazo el comando muerto de "Atajos de Teclado" por una hoja funcional de atajos.
- Se ocultaron controles de toolbar que no tienen callback real.
- Se elimino el bloqueo de build por lint.
- Se reemplazaron los KPIs simulados de CRM por el endpoint real de analitica y se reutiliza la misma fuente en `grid`, `list`, `table`, `board`, `calendar` y `gantt`.
- Se cambio la tarjeta ficticia de "Estudiantes Activos" por "Miembros Activos" con conteo real.
- Se conectaron `support/contact` y `support/tickets` con `/support/`; ahora crear y listar tickets usa persistencia real.
- Se habilito contenido libre para claves wiki en `/content`, se agrego `useWikiDocument` y se migraron las wikis embebidas a persistencia compartida con migracion automatica desde `localStorage`.
- Se conectaron las metricas principales de `admin/mission-impact` con `/finance/impact` y se diferencio visualmente la bitacora editorial de los datos operativos.
- Se agrego una capa compartida de notificaciones (`useNotifications`) y se conectaron `inbox` y `community/notifications` con `/messaging/notifications`, incluyendo marcar una o todas como leidas.
- Se retiro el fallback ficticio de `admin/intelligence`; ahora muestra degradacion real, reconoce insights contra backend y permite crear tareas manuales.
- Se eliminaron los datos de demostracion del historial de mensajeria CRM cuando falla la carga.
- Se completaron las vistas faltantes de `evangelism/events`: `table`, `board`, `kanban`, `calendar`, `gantt` y `wiki`, manteniendo persistencia compartida para notas.
- Se ocultaron los botones de calendario y gantt cuando no existe una accion real asociada.
- Se retiro el mock de `CrmViewPlaceholder`; ahora solo renderiza datos reales recibidos o estados vacios honestos.
- Se convirtio `whiteboard` global en una experiencia local funcional: listado de pizarras, canvas editable con Fabric, capas reales, autoguardado, exportacion y borrado.
- Se reemplazo el editor JSON visible de `cms/content` por un editor visual: campos normales para bloques estructurados y editor enriquecido para claves de texto/HTML.
- Se amplio el backend de testimonios para gestionar medios asociados (`image_url`, `video_url`, `podcast_url`, `media_type`, `media_url`) con migracion Alembic.
- Se conecto la administracion de testimonios para editar texto, categoria, publicacion en home y medio asociado desde el panel lateral.
- Se amplio `cms/media` para tratar audio como podcast, aceptar `audio/*` y previsualizar imagen, video y audio.
- Se renderizan medios de testimonios en la pagina publica de FARO y en el detalle publico.
- `admin/content` ya no muestra tablero con datos simulados: redirige al editor CMS real.
- Se retiro el fallback `PREMIUM_TESTIMONIALS`; la pagina publica y el detalle de testimonios ahora dependen del endpoint real del CMS y muestran estados vacios honestos.
- Se agrego selector directo de biblioteca media en creacion y edicion de testimonios para no copiar/pegar URLs manualmente.
- `admin/testimonials` ya no conserva un panel compat sin multimedia: redirige a `/cms/testimonials`.
- El detalle `/cms/testimonials/[id]` muestra imagen, video o audio asociado y usa `status` real para aprobar, archivar y restaurar.
- El dashboard CMS incorpora metricas de media total, imagenes, videos y podcasts.
- Se retiro el editor de "JSON avanzado" del builder visual y se agregaron controles visuales para `video_hero`, columnas, countdown, popup, stats, team, pricing y testimonios manuales.
- El renderer publico del builder dejo de inventar cards, FAQ, testimonios, metricas, equipo, pricing, imagenes y videos de ejemplo cuando el CMS no tiene contenido real.
- La subida de media desde el builder envia `section`, `alt_text` y `tags` como `FormData`, consistente con el backend de media.

## Deuda funcional restante

- Existen rutas publicas con copy de "Proximamente" y dependencias de CMS que no siempre tienen contenido publicado.
- Algunos modulos CRM aun no tienen vistas especializadas para perspectivas poco usadas; el placeholder ya no simula datos.
- El modulo global de `whiteboard` ya es funcional local-first, pero no sincroniza entre usuarios ni dispositivos porque no existe contrato backend global equivalente al whiteboard por proyecto.
- La bitacora de hitos de `admin/mission-impact` sigue siendo editorial porque no existe un contrato backend especifico para milestones misioneros.
- La cobertura automatizada sigue siendo baja para el tamano del frontend: solo hay pruebas unitarias basicas y smoke tests aislados.
- La gestion de media cubre metadatos/URLs y subida de archivos, pero aun no incluye recorte, transformaciones, CDN externo ni transcodificacion.
- Persisten datos estaticos de cursos/libros fuera del CMS (`src/lib/data/cursos.ts`); no bloquean el CMS, pero conviene migrarlos si la meta es contenido 100% administrable.

## Estado posterior esperado

- Shell interno mas cercano al patron ClickUp: mas compacto, paneles colapsables de verdad y modo de concentracion.
- Comandos de modulo accesibles desde `Ctrl/Cmd + K`.
- Menos UI enganosa por botones sin efecto.
- `lint`, `typecheck`, `test` y `build` quedaron en verde tras verificar el lote.
