# Auditoría Forense — UI Frontend del Módulo de Proyectos (CCF)

**Fecha:** 2026-10-09
**Alcance:** `frontend/src/components/projects/` (107 archivos, 26.721 líneas) + `frontend/src/app/plataforma/projects/`
**Motivo:** Reporte del usuario: *"el frontend no está respetando las reglas de UI… hay texto en negrilla que no son títulos, algo no está bien"*.
**Referencias canónicas:** `AGENTS.md` (regla de Tokens Semánticos), `frontend/src/design/README.md`, `frontend/src/app/globals.css` (escala tipográfica y pesos), `frontend/tailwind.config.ts`, `frontend/src/design/revisionui-proyectos.md` (auditoría previa 2026-07-23).

---

## 1. Resumen Ejecutivo

El módulo de proyectos **sí cumple** las reglas estructurales del Design System: cero modals violando la regla Drawers, cero `fetch()` crudo, cero clases de color Tailwind hardcodeadas (`bg-blue-500` etc.), todas las rutas bajo `/plataforma/...` y colores de acento vía `hsl(var(--*))`.

El problema que percibe el usuario es **tipográfico, no cromático**, y tiene una causa raíz medible: el módulo inventó una "jerga tipográfica" propia que **no existe en el sistema de diseño**:

1. **245 clases `text-3xs` muertas** — el tamaño no existe en la escala de Tailwind; el texto cae a un tamaño heredado impredecible.
2. **79 usos de `font-black` (peso 900)** — el sistema de pesos canónico define 5 pesos (400–800); 900 está fuera del sistema y CRM/evangelismo no lo usan (0 y 50 respectivamente).
3. **Jerarquía invertida** — los headings reales (`h1–h6`) se renderizan en `semibold` (600, correcto por el reset global), pero las micro-etiquetas alrededor usan `font-bold`/`font-black` + `uppercase` (286 veces `uppercase`, ~150 micro-labels "gritados"). Resultado: **las etiquetas gritan más que los títulos**, que es exactamente lo que reporta el usuario ("hay texto en negrilla y no son títulos").

**Puntuación tipográfica estimada: 4/10** (estructura 9/10, tipografía 4/10).

---

## 2. Hallazgos

### F-01 🔴 Crítico — 245 clases `text-3xs` muertas (tamaño inexistente)

**Evidencia:**
- `tailwind.config.ts` (bloque `fontSize`, líneas 108–122) define la escala semántica: `2xs, xs, sm, base, md, lg, xl, 2xl, 3xl, 4xl`. **No existe `3xs`.**
- `globals.css` define los tokens `--text-2xs` (10px) hasta `--text-4xl` (32px). No hay `--text-3xs`.
- 377 usos en todo `src/`; **245 de ellos en el módulo de proyectos**:

| Archivo | Usos de `text-3xs` |
|---|---|
| `ProjectMasterView.tsx` | 55 |
| `ProjectIndicatorsDrawer.tsx` | 47 |
| `ProjectEVMDrawer.tsx` | 21 |
| `app/plataforma/projects/[id]/indicators/page.tsx` | 20 |
| `ProjectAutomationsDrawer.tsx` | 19 |
| `ProjectTemplateCatalogDrawer.tsx` | 17 |
| `ProjectFileViewerDrawer.tsx` | 12 |
| `ProjectDriveDrawer.tsx` | 10 |
| Otros (9 archivos) | 44 |

**Impacto:** Tailwind no genera CSS para una clase inexistente → el elemento hereda el `font-size` del padre (13px body, o el que sea). Es decir, ~245 etiquetas/badges del módulo tienen un **tamaño impredecible** que depende del contenedor. Esto degrada la percepción visual de forma generalizada y silenciosa.

**Comparativo:** `crm`: 0 · `academy`: 0 · `evangelism`: 40 · `finances`: 3. Projects es el epicentro.

**Corrección:** migrar `text-3xs` → `text-2xs` (10px, el mínimo canónico para micro-labels/badges según el comentario del propio `globals.css`). Alternativa (mejor a futuro): añadir el token `--text-3xs` a globals + escala si de verdad se necesita un escalón menor, pero la corrección alineada al DS actual es la sustitución.

---

### F-02 🔴 Crítico — `font-black` (peso 900) fuera del sistema de pesos

**Evidencia:**
- `globals.css` (líneas 133–137) define el sistema canónico de 5 pesos: `--weight-normal: 400`, `medium: 500`, `semibold: 600`, `bold: 700`, `extrabold: 800`. **No hay 900.**
- Usos de `font-black` en el módulo: **79** (69 en `components/projects` + 10 en `app/plataforma/projects`).
- Comparativo: **CRM: 0** · evangelismo: 50 (también fuera de norma, pero projects es el mayor deudor).

**Impacto:** contraste tipográfico exagerado e inexistente en el resto de la plataforma; el texto a 900 con `tracking-tight` a 10–13px se ve comprimido y "tosco".

**Corrección:** `font-black` → `font-extrabold` (800, existe en el sistema) o `font-bold` según jerarquía. Los números KPI grandes (`text-lg font-black` en tarjetas de métricas de `ProjectMasterView.tsx`) pueden bajar a `font-extrabold` sin pérdida de protagonismo.

---

### F-03 🟠 Alto — Jerarquía invertida: micro-etiquetas más pesadas que los títulos

**Evidencia:**
- El reset global (`globals.css`, líneas 224–228) fuerza `h1–h6` a `font-weight: var(--weight-semibold)` (600). Correcto.
- Pero el módulo usa **679 negritas en componentes** (402 `font-bold` + 208 `font-semibold` + 69 `font-black`) de las cuales solo **69 recaen sobre headings**. Las demás (**610**) están sobre `<span>` (127 con bold/black solo en la muestra), `<p>` (35), `<label>` (50) y botones.
- **~150 micro-labels** con el patrón `text-2xs/3xs font-bold uppercase` (p. ej. `ProjectMasterView.tsx:413,422,431,440,449,458`: "Motor", "Plantilla", "Auto", "Reporte", "EVM", "EDT").

**Impacto:** el usuario escribe un título (heading, semibold 600) y a su alrededor ve spans/labels en 700–900. La vista percibe "texto en negrilla que no es título" — coincide literalmente con el reporte.

**Corrección:** regla de pesos por rol:
- Headings/c título de tarjeta: `font-semibold` (600).
- Labels de campo/metadatos: `font-medium` (500), sin `uppercase` (o solo los canónicos del DS).
- Valores numéricos KPI: `font-bold` (700) máximo.
- Badges/estados: `font-semibold` (600).

---

### F-04 🟠 Alto — "Grito tipográfico": 286 `uppercase` compitiendo por atención

**Evidencia:** 286 clases `uppercase` en componentes no-test del módulo; combinadas con F-01 (tamaño heredado) y F-02/F-03 (pesos 700–900), producen muros de texto pequeño, en mayúsculas y negrita que no jerarquizan nada.

**Corrección:** reservar `uppercase tracking-wide` exclusivamente para las etiquetas de sección canónicas del DS (p. ej. estilo `DSSectionHeader`); el resto del contenido en sentence case.

---

### F-05 🟡 Medio — Utilidades de espaciado no estándar (`py-0.2`)

**Evidencia:** 10 usos de `py-0.2` en 9 archivos (`ProjectDriveDrawer`, `ProjectGanttView`, `ProjectKanbanBoard`, `ProjectListView`, `ProjectMasterView`, `ProjectTableView`, `ProjectWorkloadDrawer`, `TaskTableView`, `TaskTimeTrackingSection`). La escala de espaciado de Tailwind no incluye `0.2` (el paso previo es `0.5` = `0.125rem` salvo extensión); probables clases muertas al igual que `text-3xs`.

**Corrección:** sustituir por `py-px` o `py-0.5` según densidad deseada, y verificar visualmente.

---

### F-06 🟡 Medio — Hex hardcodeados heredados (AG Grid / dark-mode)

**Evidencia:** la auditoría previa `frontend/src/design/revisionui-proyectos.md` (2026-07-23) documentó 31 ocurrencias hex (`#ffffff`, `#1e293b`, `#e2e8f0`, `#6366f1` en temas AG Grid de `ProjectTableView.tsx`/`TaskTableView.tsx`; fondos dark `#1e1f21`, `#1a1b1d`, `#25262b` en chat/kanban/lista/feed/gantt/detalle). En la verificación de hoy **no se detectan clases Tailwind de color hardcodeadas** (0 ocurrencias de `bg-blue-500` etc.), y los hex restantes en `ProjectComponentDrawer.tsx:56-66` son **paletas de selección de color de usuario** (datos, no estilos de UI → legítimos).

**Corrección:** tematizar AG Grid con `hsl(var(--*))` (ya existe `design/agGridTheme.ts` como punto de integración); sustituir los fondos dark por `hsl(var(--surface-1/2/3))`.

---

### F-07 🟢 Bajo — Duplicaciones históricas ya remediadas (cierre)

La auditoría 2026-07-23 señalaba `STATUS_OPTIONS`/`PRIORITY_OPTIONS` duplicados 3+ veces. Hoy el código consume `getStatusOption()` de `lib/projects/constants.ts` (verificado en `TaskDetailHeader.tsx:20`). **Marcar como cerrado**, con verificación puntual de restos en `TaskTableView.tsx` y `TaskDetailPanel.tsx` al ejecutar la corrección.

---

## 3. Cumplimientos verificados (lo que SÍ está bien)

| Regla CCF | Resultado |
|---|---|
| Drawers, no modals | ✅ 0 `DialogContent`/`AlertDialog` en el módulo |
| Tokens semánticos de color | ✅ 0 clases `text|bg|border-{color}-{n}` hardcodeadas |
| `apiFetch` (no fetch crudo) | ✅ 0 `fetch()` directo |
| Rutas `/plataforma/...` | ✅ 0 hrefs fuera del prefijo |
| Hex en UI | ⚠️ Solo paletas de selección de color de usuario (legítimo) + AG Grid (F-06) |

---

## 4. Plan de Corrección Propuesto (por orden)

| # | Acción | Esfuerzo | Riesgo de regresión visual |
|---|---|---|---|
| 1 | `text-3xs` → `text-2xs` (245 reemplazos mecánicos en el módulo) | Bajo | Bajo — normaliza a tamaño mínimo canónico |
| 2 | `font-black` → `font-extrabold`/`font-bold` (79) | Bajo | Bajo |
| 3 | Degradar labels `font-bold uppercase` → `font-medium` sentence-case (~150, criterio por archivo, empezando por `ProjectMasterView.tsx`) | Medio | Medio — requiere revisión visual |
| 4 | `py-0.2` → `py-0.5`/`py-px` (10) | Bajo | Mínimo |
| 5 | Tematizar AG Grid y fondos dark con tokens (F-06) | Medio | Medio |

La corrección 1+2+4 es mecánica y verificable con tests/lint; la 3 requiere criterio de diseño por pantalla.

---

## 5. Conclusión

La intuición del usuario es correcta y es medible: **el módulo de proyectos viola el sistema tipográfico del Design System en tres frentes** (tamaños inexistentes, pesos fuera de escala, jerarquía invertida etiqueta>título), mientras que su cumplimiento estructural (drawers, tokens de color, apiFetch, rutas) es ejemplar. El efecto combinado de 245 clases muertas + 79 pesos 900 + 286 mayúsculas produce exactamente la sensación reportada: "texto en negrilla que no son títulos" y una vista que "no se ve como se debe".

---

*Documento generado el 2026-10-09 a partir de auditoría estática del frontend del módulo de Proyectos CCF.*
