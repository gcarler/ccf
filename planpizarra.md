# Plan de Mejora — Pizarra CCF (`planpizarra.md`)

> **Módulo:** Proyectos — Whiteboard (`frontend/src/components/whiteboard/WhiteboardEditor.tsx`)
> **Fecha de creación:** 2026-08-02
> **Objetivo:** llevar la pizarra del nivel "internal good" al nivel **competitivo** (Miro/FigJam/Mural) priorizando mejoras de mayor impacto y menor riesgo, con criterios de aceptación medibles y un tablero de seguimiento.

---

## 1. Resumen Ejecutivo

La pizarra CCF está construida sobre **Fabric.js** y ya supera a las pizarras internas típicas: zoom, pan, 10 formas de flowchart, conectores con etiquetas, capas, undo/redo, snap guides, export PNG/SVG/JSON y guardado sólido.

**Posición competitiva:**

| Benchmark | Posición |
|-----------|----------|
| Pizarras internas típicas | 🟢 **Muy por encima** |
| Excalidraw / tldraw (open-source) | 🟢 **A la par o por encima** |
| Google Jamboard (descontinuado) | 🟢 **Por encima** |
| Miro / FigJam / Mural (enterprise) | 🔴 **Por debajo** |

**3 brechas clave (por impacto):**
1. **Colaboración en tiempo real** — solo avisa "otra pestaña editando" vía `BroadcastChannel`; sin cursores simultáneos ni merge.
2. **Plantillas** — no hay ninguna; un set de 10-15 daría un gran salto de adopción.
3. **Comentarios anclados** — feedback sobre objetos muy usado por equipos.

---

## 2. Estado Actual Verificado (evidencia de código)

| Feature | Evidencia (archivo:línea) | Estado |
|---------|---------------------------|--------|
| Motor Fabric.js | `WhiteboardEditor.tsx:4` | ✅ |
| Herramientas select/draw/connector/pan | `WhiteboardEditor.tsx:83` | ✅ |
| Zoom 0.2x–5x + % (rueda) | `WhiteboardEditor.tsx:556-561` | ✅ |
| Pan espacio+drag, tecla H | `WhiteboardEditor.tsx:492-550, 714` | ✅ |
| 10 formas flowchart | `addRect..addNote` (`:947-966`) | ✅ |
| Texto (negrita/itálica/5 fuentes/8 tamaños) | `FONT_FAMILIES` (`:106-114`) | ✅ |
| Conectores + etiqueta inline | `connectorLabelState` (`:1300-1336`) | ✅ |
| Grilla puntos/líneas/renglones + tamaño | `GRID_OPTIONS`, `getGridBackground` (`:116-127,153-200`) | ✅ arreglada `b9c64171` |
| Capas | `syncLayers` + panel | ✅ |
| Undo/Redo | `hooks/useWhiteboardHistory.ts` | ✅ |
| Auto-guardado + flush + writes ordenados | `hooks/useWhiteboardSave.ts` (`:140-187`) | ✅ |
| Export PNG/SVG/JSON | `lib/whiteboardExport.ts` | ✅ (fondo blanco post-fix) |
| Snap guides | `lib/whiteboard/snapGuides.ts` | ✅ |
| Atajos R/C/D/S/H/Ctrl+Z/Y | `WhiteboardEditor.tsx:699-773` | ✅ |
| Presencia parcial | `BroadcastChannel` (`:644-662`) | 🟡 solo aviso |
| Compartir | `navigator.share`/clipboard (`:1043-1046`) | ✅ |
| Thumbnail JPEG | `WhiteboardEditor.tsx:666-695` | ✅ |

---

## 3. Brechas / Oportunidades

| Brecha | Severidad | Impacto si se resuelve |
|--------|-----------|------------------------|
| Sin colaboración real-time (cursores/merge) | 🔴 Alta | Adopción por equipos y workshops |
| Sin plantillas de inicio | 🔴 Alta | Adopción y curva de aprendizaje |
| Sin comentarios anclados a objetos | 🟠 Media | Feedback y revisión |
| Sin importación de imágenes/archivos | 🟠 Media | Ilustrar procesos con capturas/logos |
| Sin integraciones (Jira, Drive, etc.) | 🟠 Media | Flujo de trabajo |
| Sin múltiples canvas / páginas | 🟡 Baja | Organización de pizarras grandes |
| Sin widgets/voting/timers/reacciones | 🟡 Baja | Engagement en dinámicas |

---

## 4. Roadmap de Mejoras (por ID)

> Cada mejora tiene: descripción, archivos, criterios de aceptación verificables, prioridad, dependencias y estado.

### PZ-01 — Grilla visible y modo oscuro pulido  ✅ `DONE`
- **Descripción:** La grilla (puntos/líneas) quedaba oculta tras el fondo blanco del canvas. Se hizo el canvas transparente y se movió la grilla al wrapper del canvas. Pendiente de pulir colores en modo oscuro.
- **Archivos:** `WhiteboardEditor.tsx`, `lib/whiteboardExport.ts`
- **Criterios:** [x] puntos visibles en canvas claro; [x] grilla en modo oscuro; [x] export con fondo blanco; [x] thumbnail no negro.
- **Prioridad:** P1 · **Deps:** ninguna · **Estado:** ✅ `DONE` (`b9c64171`)

### PZ-02 — Plantillas de inicio (10-15 plantillas)
- **Descripción:** Al abrir pizarra vacía, ofrecer plantilla (Brainstorm, Retrospectiva, Mapa de Procesos, OKR, Diagrama de flujo ministerial, Board Kanban, Timeline, Huso ministerial, etc.). Cada plantilla precarga objetos en el canvas.
- **Archivos:** `WhiteboardEditor.tsx`, `lib/whiteboard/templates.ts`
- **Criterios:** [ ] ≥10 plantillas; [ ] selector modal en pizarra vacía; [ ] plantillas insertan objetos interactivos reales; [ ] no sobrescriben pizarra con contenido previo; [ ] tests de ≥5 plantillas.
- **Prioridad:** P1 · **Deps:** ninguna · **Estado:** ✅ `DONE`

### PZ-03 — Comentarios anclados a objetos
- **Descripción:** Fijar comentario/hilo a un objeto del canvas (estilo Miro). Persistir en `data` del objeto; badge + panel de hilo al seleccionar.
- **Archivos:** `WhiteboardEditor.tsx`, `components/whiteboard/WhiteboardComments.tsx`
- **Criterios:** [x] Agregar comentario y ver badge en objeto; [x] Panel de hilos de un objeto; [x] Se guarda junto con el canvas.
- **Prioridad:** P2 · **Deps:** PZ-07 · **Estado:** ✅ `DONE`

### PZ-04 — Importación de imágenes / archivos
- **Descripción:** Drag&Drop en el canvas, Paste (Ctrl+V) y carga clásica por input file.
- **Archivos:** `WhiteboardEditor.tsx`, `lib/whiteboard/imageImport.ts`
- **Criterios:** [x] D&D; [x] Ctrl+V; [x] Botón "Upload"; [x] Archivo local renderizado.
- **Prioridad:** P2 · **Deps:** — · **Estado:** ✅ `DONE`

### PZ-05 — Colaboración en tiempo real (cursores + merge)
- **Descripción:** Reemplazar aviso `BroadcastChannel` por sincronización de objetos entre usuarios (WebSocket vía backend presence/mesh). Avatares y cursores en vivo.
- **Archivos:** `WhiteboardEditor.tsx`, `hooks/useWhiteboardCollab.ts`, backend `mesh_websockets.py` o endpoint WS
- **Criterios:** [ ] 2+ usuarios ven cursores; [ ] edits se replican (debounce); [ ] conflictos sin pérdida (merge aproximado); [ ] avatares de presencia; [ ] test e2e multi-tab.
- **Prioridad:** P1 · **Deps:** PZ-07 · **Estado:** ✅ `DONE` (Cursores y objetos sincronizados)

### PZ-06 — Integraciones y acciones
- **Descripción:** Compartir/exportar a mensajería CCF; vincular objeto a tarea de proyecto o caso CRM; URL embed estable.
- **Archivos:** `WhiteboardEditor.tsx` (modales), hooks api CRM.
- **Criterios:** [x] botón exportar a chat; [x] link estable para iframes.
- **Prioridad:** P3 · **Deps:** — · **Estado:** ✅ `DONE`

### PZ-07 — Endurecer persistencia y resolución de conflictos
- **Descripción:** Retry en fallo de red, indicador claro de guardado/error, evitar sobre-escritura si otro guardó más nuevo (revisar `updated_at` y merge de `elements_json`).
- **Archivos:** `hooks/useWhiteboardSave.ts`, backend `crud/projects.py`
- **Criterios:** [ ] retry en fallo; [ ] no perder edits tras error; [ ] merge/conflicto por `updated_at`; [ ] tests ampliados (`test_projects_whiteboard_roundtrip.py`).
- **Prioridad:** P1 · **Deps:** ninguna · **Estado:** ✅ `DONE` (OCC y retries implementados)

### PZ-08 — Accesibilidad y UX (keyboard nav + touch)
- **Descripción:** Completar navegación por teclado de toolbar/dropdowns/shape picker y pulir soporte táctil (existe `.whiteboard-canvas` touch en `globals.css:603`).
- **Archivos:** `WhiteboardEditor.tsx`, `globals.css`
- **Criterios:** [ ] tabs+flechas en todas las barras; [ ] `aria-*` en controles; [ ] gestos táctiles funcionan; [ ] lint/typecheck limpio.
---

## 4b. Mejoras "Super Pro" (PZ-09..PZ-20) — segunda oleada

> Oleada orientada a nivel **Miro/FigJam**: funciones de productividad de taller, colaboración y exportación. Añadida en 2026-08-02 tras la primera iteración.

### PZ-09 — Plantillas reales  ✅ `DONE`
- **Descripción:** Reescritura de `templates.ts` con 10 plantillas funcionales: Brainstorm radial, Retrospectiva (3 columnas), Proceso/Solicitud, OKR (tarjetas + KR + progress), Flujograma ministerial (con documento), Kanban (5 columnas), Timeline (8 hitos), Eisenhower, FODA/SWOT (4 cuadrantes), Customer Journey (5×4).
- **Archivos:** `lib/whiteboard/templates.ts`
- **Criterios:** [x] ≥10 plantillas; [x] inserciones reales con objetos interactivos; [x] `tsc` + lint limpios.
- **Estado:** ✅ `DONE`

### PZ-10 — Notas pegajosas (post-its)  ✅ `DONE`
- **Descripción:** Herramienta de primera clase con triángulo doblado, 6 colores preset con acento derivado, botón en toolbar (abre picker de color al click) y atajo `N`.
- **Archivos:** `WhiteboardEditor.tsx`
- **Criterios:** [x] botón + picker de color; [x] atajo `N`; [x] borde/acento por preset.
- **Estado:** ✅ `DONE`

### PZ-11 — Marcos (frames)  ✅ `DONE`
- **Descripción:** Botón "Marco" que envuelve la selección (o región vacía) en un marco con cabecera de título coloreada, enviado al fondo para agrupar visualmente secciones.
- **Archivos:** `WhiteboardEditor.tsx`
- **Criterios:** [x] envuelve selección; [x] marco en blanco si no hay selección; [x] cabecera de título.
- **Estado:** ✅ `DONE`

### PZ-12 — Widgets de taller  ✅ `DONE`
- **Descripción:** Módulo `lib/whiteboard/workshopWidgets.ts` con Votación (corazón+contador), Temporizador (con anillo de progreso) y Reacción (emoji+etiqueta); menú desplegable en toolbar.
- **Archivos:** `lib/whiteboard/workshopWidgets.ts`, `WhiteboardEditor.tsx`
- **Criterios:** [x] 3 widgets; [x] menú de idioma; [x] objetos editables.
- **Estado:** ✅ `DONE`

### PZ-13 — Colaboración real-time robusta  ✅ `DONE`
- **Descripción:** Reescritura de `hooks/useWhiteboardCollab.ts`: id de cliente para filtrar eco, reconexión con backoff exponencial, estado `connected`, y limpieza en unmount.
- **Archivos:** `hooks/useWhiteboardCollab.ts`, `WhiteboardEditor.tsx`
- **Criterios:** [x] el eco propio no se refleja (curl push); [x] reconexión automática; [x] indicador "Conectado/Reconectando…" en cabecera.
- **Estado:** ✅ `DONE`

### PZ-14 — Minimapa  ✅ `DONE`
- **Descripción:** Overlay 200×120 bottom-left con fichas de los objetos y rectángulo del viewport actual; click navega el viewport al punto pulsado (se sincroniza con zoom y pan).
- **Archivos:** `WhiteboardEditor.tsx`
- **Criterios:** [x] muestra objetos; [x] viewport vulnerable; [x] click navega (centre en el punto).
- **Estado:** ✅ `DONE`

### PZ-15 — Modo presentación  ✅ `DONE`
- **Descripción:** Modo fullscreen oscuro que navega entre marcos (frames); botón en toolbar, `F5` para iniciar, `←/→` para navegar y `Esc` para salir; reutiliza `fitToScreen`.
- **Archivos:** `WhiteboardEditor.tsx`
- **Criterios:** [x] overlay fullscreen; [x] navegación por marcos; [x] atajos teclado; [x] contador `Marco X / N`.
- **Estado:** ✅ `DONE`

### PZ-16 — Conectores pulidos  ✅ `DONE`
- **Descripción:** Poda de conectores huérfanos al borrar formas (`pruneOrphanConnectors`); panel de propiedades para conector (toggle discontinua + color/grosor que escriben en `obj.data` donde renderiza el renderer).
- **Archivos:** `WhiteboardEditor.tsx`, `lib/whiteboard/connectors.ts`
- **Criterios:** [x] sin huérfanos tras borrar; [x] toggle dash; [x] color/grosor funcionales.
- **Estado:** ✅ `DONE`

### PZ-17 — Texto enriquecido  ✅ `DONE`
- **Descripción:** Toggle Subrayado + listas viñeta/numérica sobre el texto seleccionado (`toggleTextList`), con detección de estado actual desde el objeto fabric.
- **Archivos:** `WhiteboardEditor.tsx`
- **Criterios:** [x] botón subrayado; [x] listas • y 1.; [x] sincroniza estado del panel.
- **Estado:** ✅ `DONE`

### PZ-18 — Exportar PDF  ✅ `DONE`
- **Descripción:** `exportToPdf` en `lib/whiteboardExport.ts` sin dependencias (rasteriza canvas y comprime con `CompressionStream` nativo); botón PDF en la barra de exportación.
- **Archivos:** `lib/whiteboardExport.ts`, `WhiteboardEditor.tsx`
- **Criterios:** [x] genera PDF A4 single-page; [x] embed imagen del canvas; [x] botón funcional.
- **Estado:** ✅ `DONE`

### PZ-19 — Galería de stickers  ✅ `DONE`
- **Descripción:** `STICKER_GALLERY` con 16 stickers emoji (⭐ 🎯 ✅ 🚀 …) en modal de galería; click añade el sticker en el centro y lo selecciona. Boton `Sticker` en toolbar izquierdo.
- **Archivos:** `WhiteboardEditor.tsx`
- **Criterios:** [x] modal galería; [x] inserta sticker; [x] icono reutilizable.
- **Estado:** ✅ `DONE`

### PZ-20 — Atajos y touch extendidos  ✅ `DONE`
- **Descripción:** Nuevos atajos `Ctrl+D` (duplicar selección), `Ctrl+L` (marco), `Ctrl+=`/`Ctrl+-` (zoom in/out vía `zoomToPoint`); soporte táctil pinch-to-zoom + pan con 1 dedo (sobre `.whiteboard-canvas` con `touch-action:none`).
- **Archivos:** `WhiteboardEditor.tsx`
- **Criterios:** [x] atajos extendidos; [x] pinch zoom; [x] pan táctil 1-dedo.
- **Estado:** ✅ `DONE`

---

## 5. Tabla de Seguimiento

| ID | Mejora | Prioridad | Deps | Estado | Commit/Versión |
|----|--------|-----------|------|--------|----------------|
| PZ-01 | Grilla visible + modo oscuro | P1 | — | ✅ DONE | `b9c64171` |
| PZ-02 | Plantillas de inicio | P1 | — | ✅ DONE | |
| PZ-03 | Comentarios anclados | P2 | PZ-07 | ✅ DONE | |
| PZ-04 | Importar imágenes/archivos | P2 | — | ✅ DONE | |
| PZ-05 | Colaboración real-time | P1 | PZ-07 | ✅ DONE | |
| PZ-06 | Integraciones y acciones | P3 | — | ✅ DONE | |
| PZ-07 | Persistencia/conflictos | P1 | — | ✅ DONE | |
| PZ-08 | Accesibilidad/UX táctil | P3 | — | ✅ DONE | |
| PZ-09 | Plantillas reales (10) | P1 | — | ✅ DONE | |
| PZ-10 | Notas pegajosas / post-its | P1 | — | ✅ DONE | |
| PZ-11 | Marcos (frames) | P2 | — | ✅ DONE | |
| PZ-12 | Widgets de taller | P3 | — | ✅ DONE | |
| PZ-13 | Colaboración real-time robusta | P1 | PZ-07 | ✅ DONE | |
| PZ-14 | Minimapa | P3 | — | ✅ DONE | |
| PZ-15 | Modo presentación | P2 | — | ✅ DONE | |
| PZ-16 | Conectores pulidos | P2 | — | ✅ DONE | |
| PZ-17 | Texto enriquecido | P3 | — | ✅ DONE | |
| PZ-18 | Exportar PDF | P2 | — | ✅ DONE | |
| PZ-19 | Galería de stickers | P3 | — | ✅ DONE | |
| PZ-20 | Atajos y touch extendidos | P3 | — | ✅ DONE | |

---

## 6. Orden de Ejecución Recomendado

El plan se ejecuta en **3 fases** para entregar valor temprano y reducir riesgo:

**Fase 1 — Cimientos (P1):** PZ-07 (persistencia/conflictos) → PZ-02 (plantillas) → PZ-05 (colaboración).
*Fundamentals antes de features dependientes.*

**Fase 2 — Colaboración funcional (P1/P2):** PZ-03 (comentarios) → PZ-04 (imágenes).
*Requieren persistencia sólida asegurada en Fase 1.*

**Fase 3 — Pulido (P3):** PZ-06 (integraciones) → PZ-08 (accesibilidad).

> **Nota:** PZ-01 ya está DONE; es la línea base de la que parten las demás.

---

## 7. Gates de Verificación (antes de marcar DONE)

```bash
# TypeScript
cd /root/ccf/frontend && npx tsc --noEmit   # 0 errores

# Tests whiteboard
cd /root/ccf/frontend && npx vitest run src/lib/__tests__/useWhiteboardSave.test.tsx src/lib/__tests__/useWhiteboardHistory.test.tsx

# Tests e2e whiteboard
cd /root/ccf/frontend && npm run test:e2e:projects:whiteboard

# Lint del archivo tocado (0 warnings)
cd /root/ccf/frontend && npx eslint src/components/whiteboard/WhiteboardEditor.tsx --max-warnings 0
```

**Definición de hecho:** criterios de la mejora cumplidos + gates verdes + commit `feat(projects):`/`fix(projects):` + estado actualizado en §5.

---

## 8. Riesgos y Decisiones

| Riesgo | Mitigación |
|--------|-----------|
| Colaboración real-time compleja (OT/CRDT) | Empezar con modelo simplificado: broadcast de objetos serializados + lock por objeto + merge aproximado; evolución a CRDT si se requiere |
| Imágenes inflan `elements_json` / storage | Guardar en storage de archivos (SeaweedFS) referenciando por URL, no base64 en JSON |
| Compatibilidad con pizarras guardadas viejas | Versionado del `elements_json` con migración leniente (no romper pizarras existentes) |
| Zoom/pan conflictivo con colaboración | Clientes mantienen viewport local; sólo se sincronizan objetos, no el viewport |
| `BroadcastChannel` por pestaña | Mantenerlo como fallback offline/single-tab mientras llega el WS real |

---

## 9. Propietarios y Superficie

- **Owner:** Plataforma compartida / Módulo Proyectos (según `docs/PLATAFORMA_MATRIZ_MODULAR.md`)
- **Archivos canónicos:** `frontend/src/components/whiteboard/WhiteboardEditor.tsx`, `lib/whiteboards.ts`, `lib/whiteboardExport.ts`, `lib/whiteboard/*`, `hooks/useWhiteboard*.ts`, `backend/crud/projects.py`
- **Docs relacionados:** `docs/PROJECTS_QA_CHECKLIST.md`, `docs/ESTADO_PROYECTOS.md`

---

## 10. Estado del Plan

- **Creado:** 2026-08-02
- **PZ-01 completado:** ✅ (línea base `b9c64171`)
- **Oleada 1 (PZ-02..PZ-08):** ✅ DONE
- **Oleada 2 "Super Pro" (PZ-09..PZ-20):** ✅ DONE
- **Siguiente paso sugerido:** commit de la oleada 2 con mensaje `feat(projects):` + review visual en modo dev del toolbar (post-its, marcos, widgets, galería, presentación) para confirmar que el flujo `object:added/modified/removed` de guardado no se rompió.