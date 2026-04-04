---
name: aesthetic-expert
description: Actúa como un experto en estética UI/UX para la plataforma CCF, aplicando el Design System "Clean Productivity" — inspirado en ClickUp 3.0 y Linear — para crear interfaces premium, consistentes y altamente funcionales. Este skill es OBLIGATORIO al crear o modificar cualquier componente de UI.
---

# CCF Platform — Design System "Clean Productivity"

Este skill define los **parámetros inamovibles** del sistema visual de la plataforma CCF. Toda IA que trabaje en el frontend DEBE seguir estas especificaciones sin excepción.

---

## 1. Arquitectura de Layout (OBLIGATORIO)

La plataforma usa un sistema de **3 capas laterales apiladas** en el eje X:

```
┌──┬────────────────┬──────────────────────────────────────────┐
│S1│      S2        │            CONTENIDO PRINCIPAL            │
│60│    300px       │   toolbar + scrollable content area      │
│px│  contextual    │                                          │
└──┴────────────────┴──────────────────────────────────────────┘
```

### S1 — Navegación Primaria
- Ancho fijo: **~60px**
- Fondo: `bg-white dark:bg-[#1e1f21]`
- Sombra derecha sutil: `shadow-[2px_0_8px_rgba(0,0,0,0.04)]`
- Contenido:
  - Botón `+` (acción global): `bg-blue-600`, circular, `size-9`, siempre visible
  - Íconos de módulos: Lucide, `size={18}`, color `text-slate-400` → `text-blue-600` activo
  - Al fondo: toggle dark mode, ajustes, panel de soporte
- Usa el componente `WorkspaceLayout` como wrapper envolvente

### S2 — Navegación Secundaria / Contextual
- Ancho fijo: **~300px**
- Muestra secciones con `title` y `items[]` del módulo activo
- Cambia según la ruta (`moduleConfig` en `WorkspaceLayout.tsx`)
- Footer: toggle "Modo Claro/Oscuro" + "Ajustes"
- Se colapsa con toggle — siempre debe tener esa opción

### Contenido Principal
- `flex-1`, `min-w-0`, `overflow-auto`
- Sub-toolbar horizontal en la parte alta (breadcrumbs + acciones + tabs de vista)
- Contenido scrolleable con `scrollbar-thin`

---

## 2. Paleta de Colores (INAMOVIBLE)

### Fondos
| Uso | Light | Dark |
|-----|-------|------|
| Principal | `#FFFFFF` | `#1E1F21` |
| Secundario / Cards | `#F8F9FB` | `#252528` |
| Sidebar / Drawer | `#FFFFFF` | `#1E1F21` |
| Input / Table row hover | `#F1F5F9` (slate-100) | `rgba(255,255,255,0.03)` |

### Acentos
| Uso | Color | Tailwind |
|-----|-------|----------|
| Acción primaria / CTA | `#2563EB` | `blue-600` |
| Acción secundaria / hover | `#7C3AED` | `violet-600` |
| CTA degradado | `from-violet-600 to-indigo-600` | gradient |
| Éxito / completado | `#10B981` | `emerald-500` |
| Advertencia / en curso | `#F59E0B` | `amber-500` |
| Error / bloqueado | `#EF4444` | `rose-500` |
| Info / neutral | `#64748B` | `slate-500` |

### Texto
| Uso | Light | Dark |
|-----|-------|------|
| Título principal | `#0F172A` (slate-900) | `#F8FAFC` (slate-50) |
| Texto cuerpo | `#334155` (slate-700) | `#CBD5E1` (slate-300) |
| Texto secundario | `#94A3B8` (slate-400) | `#64748B` (slate-500) |
| Placeholder | `#CBD5E1` (slate-300) | `rgba(255,255,255,0.2)` |

### Bordes
- Default: `border-slate-200 dark:border-white/[0.06]`
- Activo/focus: `border-blue-400` o `ring-2 ring-blue-500/30`
- Separator: `border-slate-100 dark:border-white/5`

---

## 3. Tipografía

- **Fuente principal:** `font-display` → Inter, Outfit, o similar sans-serif moderna
- **Jerarquía de tamaños:**

| Uso | Size | Weight | Extra |
|-----|------|--------|-------|
| Labels de sección / columnas | `text-[10px]` | `font-black` | `uppercase tracking-[0.15em]` |
| Metadatos / badges | `text-[11px]` | `font-bold` | `uppercase tracking-widest` |
| Cuerpo de tabla / lista | `text-[12px]` | `font-medium` | — |
| Título de ítem | `text-[13px]` | `font-semibold` | — |
| Título de card | `text-[15px]` | `font-bold` | — |
| Título de módulo | `text-xl` | `font-black` | — |

---

## 4. Componentes — Reglas de construcción

### Botones

```tsx
// Primario (acción principal de la vista)
className="flex items-center gap-2 px-4 py-1.5 bg-blue-600 text-white rounded-lg text-[11px] font-black uppercase tracking-widest shadow-xl shadow-blue-500/20 hover:bg-blue-700 active:scale-95 transition-all"

// CTA gradiente (Ask AI, acciones de impacto)
className="bg-gradient-to-r from-violet-600 to-indigo-600 text-white px-3 py-1.5 rounded-lg text-[11px] font-bold hover:opacity-90 transition-all"

// Ghost / secundario
className="flex items-center gap-1 px-2 py-1 rounded-md text-[11px] font-medium text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-white/5 transition-colors"

// Destructivo
className="text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-900/20 rounded-lg px-3 py-1.5 text-[12px] font-bold"
```

### Cards

```tsx
className="group relative bg-white dark:bg-[#252528] rounded-2xl border border-slate-200/70 dark:border-white/5 p-6 shadow-sm hover:shadow-xl hover:shadow-slate-200/60 dark:hover:shadow-black/30 transition-all duration-300 cursor-pointer overflow-hidden active:scale-[0.99]"
```
- Siempre: acento de color en borde superior (`h-[3px]` con `background: linear-gradient`)
- Íconos/avatares con fondo de color sólido, `rounded-xl`, texto `text-white font-black`

### Badges / Pills de estado

```tsx
// Activo
className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-400"

// En Curso
className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-violet-100 dark:bg-violet-900/20 text-violet-700 dark:text-violet-400"

// Bloqueado
className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-100 dark:bg-rose-900/20 text-rose-600 dark:text-rose-400"
```

### Inputs / Forms

```tsx
className="w-full px-3 py-2 text-[13px] font-medium bg-white dark:bg-[#252528] border border-slate-200 dark:border-white/10 rounded-xl outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-400 transition-all placeholder:text-slate-400"
```

### Tablas (List / Table views)

- Header sticky: `sticky top-0 z-10 bg-slate-50/90 dark:bg-[#18191b]/90 backdrop-blur-sm`
- Columnas: `text-[10px] font-black uppercase tracking-[0.15em] text-slate-400`
- Filas con hover: `hover:bg-slate-50/70 dark:hover:bg-white/[0.02]`
- Separador: `border-b border-slate-100 dark:border-white/[0.04]`

---

## 5. Patrón de Interacción — NO Modals, SÍ Panels

**REGLA CRÍTICA:** La plataforma NO usa modals de overlay bloqueantes para acciones de detalle/edición. En su lugar:

### ✅ Patrón Correcto: Side Panel (Detail Window)

```
┌──┬────────┬───────────────────┬──────────────────────┐
│S1│  S2    │   LISTA TAREAS    │   DETALLE TAREA       │
│  │        │   → Tarea activa ─┤  Título               │
│  │        │   ─ Tarea B       │  Descripción          │
│  │        │   ─ Tarea C       │  Comentarios          │
│  │        │                   │  Actividad            │
└──┴────────┴───────────────────┴──────────────────────┘
```

- El panel de detalle **desliza desde la derecha** sin oscurecer el fondo
- `position: fixed/absolute`, `right-0`, ancho `400-600px`
- Animación: `x: 400 → 0`, `opacity: 0 → 1`, duración `0.25s ease-out`
- La lista de fondo permanece **visible e interactuable parcialmente**
- Debe tener: botón de cerrar (`X`), navegación entre ítems (↑↓), enlace a vista completa (`⤢`)
- Usa el componente `RightPanel.tsx` existente o el mismo patrón

### ✅ Excepciones donde SÍ se usan overlays
- **Popovers anclados a botones** (ej: dropdown "Añadir Tarea") — `Popover.Root` de Radix
- **Confirmación de acciones destructivas** — mini overlay pequeño centrado (`max-w-sm`, no fullscreen)
- **Creación de entidades nuevas desde cero** — `ProjectCreationModal` con posicionamiento junto al botón trigger

### ❌ Evitar absolutamente
- Modals con `fixed inset-0 bg-black/50` que bloquean toda la UI
- Dialogs centrados que no permiten ver el contexto
- Formularios que interrumpen el flujo sin anclaje visual

---

## 6. Animaciones y Micro-interacciones

| Elemento | Patrón |
|----------|--------|
| Tab activo | `layoutId="activeTab"` con Framer Motion (underline deslizante) |
| Entrada de listas | `opacity: 0→1, y: 16→0`, `delay: index * 0.04s` |
| Quick-add bar | `height: 0→auto, opacity: 0→1`, `duration: 0.15s` |
| Barra de progreso | `initial width: 0%`, `animate: width: X%`, `duration: 0.8s ease-out` |
| Hover cards | `hover:shadow-xl`, `active:scale-[0.99]` |
| Drag fantasma | `rotate-1 opacity-90` en DragOverlay |
| Botones | `active:scale-95 transition-all` |
| Sidebar collapse | `width: 300px→0`, suave |

**Librería:** Framer Motion (`motion.div`, `AnimatePresence`, `layoutId`)

---

## 7. Vistas — Tipos y Comportamiento

En módulos con múltiples entidades (Proyectos, Tareas, CRM), SIEMPRE ofrecer múltiples vistas:

| Vista | Ícono Lucide | Descripción |
|-------|-------------|-------------|
| Lista | `List` | Agrupada por estado, con inline quick-add sticky |
| Tablero | `KanbanSquare` | Columnas drag-and-drop con quick-add por columna |
| Calendario | `Calendar` | Grid mensual con tareas por fecha límite |
| Gantt | `BarChart3` | Timeline con barras coloreadas por estado/prioridad |
| Tabla | `Table2` | Spreadsheet ordenable, sticky quick-add |
| Wiki | `BookOpen` | Editor Tiptap rich-text con autosave |

**Quick-add unificado:** Toda vista debe tener un mecanismo de creación rápida — preferiblemente una **barra sticky violeta en el tope** del área de contenido que aparece al activarse.

---

## 8. Modo Oscuro

- Toda clase CSS debe tener su par `dark:` definido
- Fondos never pure black — usar `#1E1F21` o `#252528`
- Bordes en dark: `dark:border-white/[0.06]` (muy tenues)
- Sombras en dark: `dark:shadow-black/30` (más pronunciadas)
- Textos en dark: nunca pure white — usar `dark:text-slate-100` o `dark:text-slate-200`

---

## 9. Íconos

- **Librería única:** [Lucide React](https://lucide.dev/)
- **Tamaño estándar:** `size={13}` en toolbars, `size={16}` en botones, `size={18}` en S1
- **Estilo:** lineal, `strokeWidth` default (2)
- NO usar emojis como íconos de navegación
- Las iniciales en avatares/badges son alternativa válida: `'AB'` en `font-black text-white`

---

## 10. Checklist antes de entregar cualquier cambio de UI

- [ ] ¿Usa `WorkspaceLayout` como wrapper?
- [ ] ¿Tiene dark mode completo (`dark:` en cada color)?
- [ ] ¿Los botones primarios tienen `active:scale-95 transition-all`?
- [ ] ¿Las listas tienen animación de entrada escalonada?
- [ ] ¿Los estados vacíos tienen un diseño con ícono + mensaje + CTA?
- [ ] ¿Se usó Side Panel en lugar de Modal para vistas de detalle?
- [ ] ¿El quick-add aparece como barra sticky, no inline enterrada?
- [ ] ¿Los badges usan colores semánticos del sistema?
- [ ] ¿Los textos de interfaz están en español?
- [ ] ¿La vista se ve premium en mobile (responsive)?
