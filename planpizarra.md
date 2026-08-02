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
- **Prioridad:** P1 · **Deps:** ninguna · **Estado:** ⬜ Pendiente

### PZ-03 — Comentarios anclados a objetos
- **Descripción:** Fijar comentario/hilo a un objeto del canvas (estilo Miro). Persistir en `data` del objeto; badge + panel de hilo al seleccionar.
- **Archivos:** `WhiteboardEditor.tsx`, `lib/whiteboard/connectors.ts`, componente `CommentThread`
- **Criterios:** [ ] botón "comentar"; [ ] hilo persistido en `elements_json`; [ ] badge en objeto; [ ] hilos visibles tras recarga; [ ] test round-trip.
- **Prioridad:** P2 · **Deps:** PZ-07 · **Estado:** ⬜ Pendiente

### PZ-04 — Importación de imágenes / archivos
- **Descripción:** Insertar imagen (subida local o URL) y drag&drop. Subir a storage y renderizar `fabric.Image`.
- **Archivos:** `WhiteboardEditor.tsx`, `lib/whiteboards.ts`, backend upload
- **Criterios:** [ ] subir local → renderiza; [ ] por URL; [ ] drag&drop; [ ] persiste en `elements_json`; [ ] restaura tras recarga.
- **Prioridad:** P2 · **Deps:** ninguna · **Estado:** ⬜ Pendiente

### PZ-05 — Colaboración en tiempo real (cursores + merge)
- **Descripción:** Reemplazar aviso `BroadcastChannel` por sincronización de objetos entre usuarios (WebSocket vía backend presence/mesh). Avatares y cursores en vivo.
- **Archivos:** `WhiteboardEditor.tsx`, `hooks/useWhiteboardCollab.ts`, backend `mesh_websockets.py` o endpoint WS
- **Criterios:** [ ] 2+ usuarios ven cursores; [ ] edits se replican (debounce); [ ] conflictos sin pérdida (merge aproximado); [ ] avatares de presencia; [ ] test e2e multi-tab.
- **Prioridad:** P1 · **Deps:** PZ-07 · **Estado:** ⬜ Pendiente

### PZ-06 — Integraciones y acciones
- **Descripción:** Compartir/exportar a mensajería CCF; vincular objeto a tarea de proyecto o caso CRM; URL embed estable.
- **Archivos:** `WhiteboardEditor.tsx`, `lib/whiteboards.ts`
- **Criterios:** [ ] acción "vincular a tarea"; [ ] compartir a messaging; [ ] URL embed; [ ] tests.
- **Prioridad:** P3 · **Deps:** ninguna · **Estado:** ⬜ Pendiente

### PZ-07 — Endurecer persistencia y resolución de conflictos
- **Descripción:** Retry en fallo de red, indicador claro de guardado/error, evitar sobre-escritura si otro guardó más nuevo (revisar `updated_at` y merge de `elements_json`).
- **Archivos:** `hooks/useWhiteboardSave.ts`, backend `crud/projects.py`
- **Criterios:** [ ] retry en fallo; [ ] no perder edits tras error; [ ] merge/conflicto por `updated_at`; [ ] tests ampliados (`test_projects_whiteboard_roundtrip.py`).
- **Prioridad:** P1 · **Deps:** ninguna · **Estado:** ⬜ Pendiente

### PZ-08 — Accesibilidad y UX (keyboard nav + touch)
- **Descripción:** Completar navegación por teclado de toolbar/dropdowns/shape picker y pulir soporte táctil (ya existe `.whiteboard-canvas` touch en `globals.css:603`).
- **Archivos:** `WhiteboardEditor.tsx`, `globals.css`
- **Criterios:** [ ] tabs+flechas en todas las barras; [ ] `aria-*` en controles; [ ] gestos táctiles funcionan; [ ] lint/typecheck limpio.
---

## 5. Tabla de Seguimiento

| ID | Mejora | Prioridad | Deps | Estado | Commit/Versión |
|----|--------|-----------|------|--------|----------------|
| PZ-01 | Grilla visible + modo oscuro | P1 | — | ✅ DONE | `b9c64171` |
| PZ-02 | Plantillas de inicio | P1 | — | ⬜ Pendiente | |
| PZ-03 | Comentarios anclados | P2 | PZ-07 | ⬜ Pendiente | |
| PZ-04 | Importar imágenes/archivos | P2 | — | ⬜ Pendiente | |
| PZ-05 | Colaboración real-time | P1 | PZ-07 | ⬜ Pendiente | |
| PZ-06 | Integraciones y acciones | P3 | — | ⬜ Pendiente | |
| PZ-07 | Persistencia/conflictos | P1 | — | ⬜ Pendiente | |
| PZ-08 | Accesibilidad/UX táctil | P3 | — | ⬜ Pendiente | |

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
- **Pendientes:** PZ-02 → PZ-08
- **Siguiente paso sugerido:** ejecutar **PZ-07** (persistencia/conflictos) para cimentar y luego **PZ-02** (plantillas).