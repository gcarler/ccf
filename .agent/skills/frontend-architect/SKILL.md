---
name: frontend-architect
description: Actúa como el arquitecto de frontend de la plataforma CCF. Conoce en profundidad la arquitectura de capas (S1/S2/S3/RIGHT), el sistema de layout, los patrones de interacción sin modales, la gestión de espacios, los componentes reutilizables y el stack tecnológico. Es OBLIGATORIO usarlo cuando se cree, modifique o refactorice cualquier componente, página o lógica de navegación del frontend.
---

# CCF Platform — Arquitectura de Frontend & UI

Este skill convierte al agente en el **arquitecto de frontend** de la plataforma CCF. Aquí se documenta **cómo funciona la interfaz gráfica por dentro**: su estructura, sus reglas de composición, sus patrones de interacción y su stack tecnológico. Todo agente que trabaje en el frontend DEBE leer y respetar este skill.

---

## Stack Tecnológico

| Capa | Tecnología |
|------|-----------|
| Framework | **Next.js 14** (App Router, `"use client"` explícito) |
| Lenguaje | **TypeScript** estricto |
| Estilos | **Tailwind CSS v3** + clsx para condicionales |
| Animaciones | **Framer Motion** (`motion.div`, `AnimatePresence`, `layoutId`) |
| Íconos | **Lucide React** (único, sin emojis en la UI de workspace) |
| Componentes headless | **Radix UI** (`@radix-ui/react-popover`, `@radix-ui/react-dialog`) |
| Fuente | **Manrope** / Inter — `font-display` en `tailwind.config` |
| Estado global | **React Context** (AuthContext, SidebarLayerContext, CreationContext, CommandCenterContext) |
| HTTP | Helper `apiFetch` en `@/lib/http` — token siempre desde `useAuth()` |
| Notificaciones | **Sonner** (`toast.success / .error / .info`) |
| Búsqueda global | **cmdk** (`CommandCenter.tsx`) |

---

## 1. Arquitectura de Capas — El Sistema de Layout

La plataforma usa un sistema de **4 capas laterales apiladas en el eje X**, orquestadas por `SidebarLayerContext`. Cada capa tiene un `z-index` fijo y un rol específico.

```
┌───┬──────────┬──────────┬────────────────────┬──────────┐
│S1 │    S2    │    S3    │  CONTENIDO PRINCIPAL│  RIGHT   │
│60 │  288px   │  280px   │  toolbar + content  │  320px   │
│px │ módulo   │ contexto │  flex-1 dinámico    │  detail  │
│z50│   z40    │   z30    │       z10           │   z25/35 │
└───┴──────────┴──────────┴────────────────────┴──────────┘
```

### Reglas fundamentales del sistema de capas

- **S1 siempre visible** (`layers.S1 = true` en casi todos los casos). Solo se puede ocultar con `closeLayer('S1')` y restaurar con su botón flotante.
- **S2 tiene 3 estados**: `full` (w-72) → `mini` (w-16, solo íconos) → `hidden` (w-0). Se cicla con `cycleS2()` en `WorkspaceLayout`.
- **S3** es opcional: panel de contexto profundo (ej: detalle de un proyecto dentro de la sidebar). Se abre programáticamente con `openLayer('S3')`.
- **RIGHT** es opcional: panel de detalle/actividad a la derecha del contenido. Puede ser `push` (empuja el contenido) u `overlay` (se superpone). Se controla con `setRightMode('push' | 'overlay')`.
- **ESC** cierra la capa superior abierta en orden: `RIGHT → S3 → S2`.

### Cómo se comunica el layout

```tsx
// En cualquier componente hijo dentro del WorkspaceLayout:
import { useSidebarLayers } from '@/context/SidebarLayerContext';

const { layers, openLayer, closeLayer, toggleLayer, rightMode, setRightMode } = useSidebarLayers();

// Abrir el panel de contexto (S3)
openLayer('S3');

// Abrir panel de detalle derecho
setRightMode('push'); // o 'overlay'
openLayer('RIGHT');

// Cerrar panel derecho
closeLayer('RIGHT');
```

---

## 2. Componente Raíz: `WorkspaceLayout`

**Archivo:** `@/components/WorkspaceLayout.tsx`

Es el wrapper obligatorio de **todas las páginas del workspace** (todo lo que requiere autenticación y pertenece a la app interna). Es quien monta y orquesta S1, S2, la toolbar del header, el inbox, el chat MESH y el botón flotante de IA.

### Props de WorkspaceLayout

```tsx
<WorkspaceLayout
  sidebarTitle="Título del módulo"   // Texto del header (opcional, se infiere de la ruta)
  sidebarSections={[...]}            // Secciones del S2 (opcional, se infiere del moduleConfig)
  allowedRoles={['admin', 'pastor']} // RBAC — si no se pasa, cualquier rol autenticado
  depth={1}                           // 1 = página raíz, >1 = sub-página (muestra botón atrás)
  onBack={() => router.back()}        // Callback del botón atrás (solo si depth > 1)
  customSidebar={<MiSidebarPersonalizada />} // Reemplaza WorkspaceMainSidebar completo
>
  {/* Contenido de la página */}
</WorkspaceLayout>
```

### Qué renderiza WorkspaceLayout por defecto

1. **Barra de progreso de carga** — `motion.div` de 2px en azul al tope, siempre animada al entrar.
2. **S1** — `WorkspaceMiniSidebar` (icono-rail de 64px).
3. **S2** — `WorkspaceMainSidebar` con secciones según la ruta activa.
4. **Header Toolbar** — `h-14`, con: botón toggle S2, `ThemeToggle`, campana de notificaciones y chip de usuario.
5. **Área de contenido** — `flex-1 overflow-hidden`, donde van los `{children}`.
6. **`WorkspaceInbox`** — drawer de notificaciones deslizable desde abajo.
7. **`MeshChat`** — chat con la IA MESH, panel flotante.
8. **Botón flotante MESH AI** — `fixed bottom-8 right-8`, `Bot` de Lucide, gradiente violeta-índigo.

### Inferencia automática de módulo (moduleConfig)

`WorkspaceLayout` detecta el módulo activo por la primera parte de la ruta (`pathname.split('/')[1]`). La configuración está en `MODULE_CONFIGS` dentro del componente:

| Ruta raíz | Título S2 | Secciones cargadas |
|-----------|-----------|-------------------|
| `/projects` | "Portfolio" | Gestión: Portfolio, Mis Tareas, Equipo; Herramientas: Calendario, Automatizaciones |
| `/tasks` | "Productividad" | Mis espacios: Todas las tareas, Calendario |
| `/crm` | "Comunidad" | Directorios: Miembros, Casas de Gloria |
| `/academy` | "Academia" | Estudio: Inicio, Cursos, Mi cuenta |
| `/finances` | "Finanzas" | Reportes: Resumen, Transparencia |
| `/inbox` | "Bandeja" | Filtros: Todo, Menciones, Tareas, MESH AI |
| `/cms` | "Sitio Web" | Contenido: Inicio CMS, Páginas, Menús, Testimonios, Landing Hero, Eventos |
| `/wiki` | "Conocimiento" | Espacios: Inicio Wiki, Documentos, Base Pastoral |
| `/groups` | "Comunidad" | Células: Casas de Bendición, Núcleos Familiares, Directorio CRM |
| `/calendar` | "Calendario" | Vistas: Por Mes |
| `/spiritual-life` | "Vida Espiritual" | Mi Caminar: Panel Espiritual, Línea de Tiempo, Mis Certificados; Formación: Academia CCF |

---

## 3. Componente S1: `WorkspaceMiniSidebar`

**Archivo:** `@/components/WorkspaceMiniSidebar.tsx`

Rail vertical de 64px siempre visible. Fondo: `bg-white dark:bg-black`. Bordes redondeados: `rounded-[2rem]`. Shadow pronunciada.

### Estructura interna de S1

1. **Botón `+` Global** — `size-10`, `bg-blue-600`, `rounded-2xl`. Abre `UniversalCreationModal` con `openModal('task')` desde `CreationContext`.
2. **Items primarios** (workspace): Proyectos (`Target`), Mis Tareas (`Layout`), Calendario (`CalendarDays`).
3. **Separador** — línea de 1px.
4. **Items de módulos**: Academia (`GraduationCap`), Comunidad (`Users`), Finanzas (`DollarSign`), Sitio Web (`Globe`), Vida Espiritual (`Heart`).
5. **Separador**.
6. **Inbox** con badge de notificaciones.
7. **Footer**: Ajustes (`Settings`), botón de colapsar S1 (`PanelLeftClose`).

Cada ítem usa `Tooltip` de Radix anclado a la derecha. El estado activo se indica con fondo `bg-blue-600/10 dark:bg-white/10` e ícono `text-blue-500`.

---

## 4. Componente S2: `WorkspaceMainSidebar`

**Archivo:** `@/components/WorkspaceMainSidebar.tsx`

Sidebar secundaria de módulo. Ancho: `288px` (full), `64px` (mini), `0` (hidden). Fondo: `bg-white dark:bg-[#1e1f21]`.

### Modos de S2

- **`full`**: Muestra título del módulo + secciones con sus ítems etiquetados.
- **`mini`**: Solo íconos, sin labels. Equivale al comportamiento de S1.
- **`hidden`**: Colapsado totalmente (width 0, overflow hidden).

### Props que recibe

```tsx
<WorkspaceMainSidebar
  title="Nombre del módulo"
  sections={[
    {
      title: "Sección",
      items: [
        { id: 'unique-id', label: 'Label', href: '/ruta', icon: LucideIcon }
      ]
    }
  ]}
  isMini={false}
  onToggle={cycleS2}
  isCollapsed={false}
/>
```

---

## 5. Componente S3: `Sidebar3`

**Archivo:** `@/components/ui/Sidebar3.tsx`

Panel de contexto profundo. Se abre **dentro** del área de contenido principal, empujando el `flex-1` hacia la derecha. Útil para: detalle de un proyecto, perfil de un miembro en el CRM (dentro de la sidebar), árbol de items, etc.

```tsx
import Sidebar3 from '@/components/ui/Sidebar3';
import { useSidebarLayers } from '@/context/SidebarLayerContext';

// Para abrirlo:
const { openLayer } = useSidebarLayers();
openLayer('S3');

// Renderizarlo (en el mismo componente de layout de la página):
<div className="flex h-full">
  <Sidebar3 title="Detalle" subtitle="PROYECTO" width={280}>
    {/* contenido del panel de contexto */}
  </Sidebar3>
  <div className="flex-1 overflow-auto">
    {/* contenido principal */}
  </div>
</div>
```

- Anima desde la izquierda (`x: -300 → 0`), duración `0.28s`.
- `z-index: 30` — debajo de S2 (z40) y S1 (z50).
- Box-shadow pronunciada en borde derecho para efecto de profundidad.
- Foco automático al primer elemento interactivo al abrirse (accesibilidad).

---

## 6. Componente RIGHT: `RightPanel`

**Archivo:** `@/components/ui/RightPanel.tsx`

Panel de detalle/actividad a la derecha del área de contenido. Dos modos:

| Modo | Comportamiento | Z-index | Cuándo usarlo |
|------|---------------|---------|---------------|
| `push` | Se inserta en el flex como columna, empuja el contenido central | z-25 | Cuando el contenido puede reducirse sin perder contexto |
| `overlay` | Se superpone con backdrop semitransparente | z-35 | Vistas de tabla densa o kanban donde no se puede reducir |

```tsx
import RightPanel from '@/components/ui/RightPanel';
import { useSidebarLayers } from '@/context/SidebarLayerContext';

// Para abrirlo (desde cualquier componente hijo):
const { openLayer, setRightMode } = useSidebarLayers();
setRightMode('push'); // o 'overlay'
openLayer('RIGHT');

// Renderizarlo (en la página que lo necesita):
<div className="flex h-full overflow-hidden">
  <div className="flex-1 overflow-auto">
    {/* Tu lista o tabla */}
  </div>
  <RightPanel title="Actividad" width={360}>
    {/* Detalle del item seleccionado */}
  </RightPanel>
</div>
```

- Anima desde la derecha (`x: width → 0`), duración `0.28s`.
- El RightPanel se cierra con `closeLayer('RIGHT')` o con ESC.
- En modo `overlay`, incluye un backdrop con `onClick` para cerrar.

---

## 7. REGLA CRÍTICA: NO Modals Bloqueantes

**La plataforma NO usa modals de overlay que bloqueen toda la UI para acciones de detalle o edición.**

### ✅ Usa en su lugar

| Necesidad | Solución |
|-----------|----------|
| Ver/editar detalle de un item | `RightPanel` (push u overlay) |
| Panel de contexto de proyecto/módulo | `Sidebar3` |
| Formulario de creación de entidades nuevas | `UniversalCreationModal` (centrado, máx 600px, NO fullscreen) |
| Confirmación destructiva (eliminar) | Mini popover centrado `max-w-sm` via Radix `Dialog` |
| Dropdown de opciones anclado a botón | `Popover.Root` de Radix (sin overlay de fondo) |

### ❌ Evitar absolutamente

```tsx
// PROHIBIDO: modal fullscreen bloqueante
<div className="fixed inset-0 bg-black/50 z-[9999] flex items-center justify-center">
  <div>Mi formulario de detalle</div>
</div>
```

### La única excepción — `UniversalCreationModal`

Existe un modal de creación rápida (`@/components/ui/UniversalCreationModal.tsx`) que SÍ usa un overlay. Pero tiene reglas:
- **Tamaño limitado**: `max-w-[600px]`, nunca fullscreen.
- **Solo para creación desde cero** (Tarea, Documento, Recordatorio, Pizarra, Panel).
- Se abre **exclusivamente** desde el botón `+` de S1 o desde `useCreation().openModal(type)`.
- Tiene tabs animados con `layoutId="modalActiveTab"`.
- Footer con botón de submit + split-button para opciones adicionales.

---

## 8. Gestión de Espacios y Vistas

En módulos con múltiples entidades (Proyectos, Tareas, CRM), siempre se ofrecen múltiples **vistas intercambiables** a través de un `ViewSwitcher`:

| Vista | Ícono Lucide | Componente | Descripción |
|-------|-------------|-----------|-------------|
| Lista | `List` | inline | Agrupada por estado, inline quick-add sticky arriba |
| Tablero | `KanbanSquare` | inline | Columnas DnD (dnd-kit) con quick-add por columna |
| Calendario | `Calendar` | inline | Grid mensual con items por fecha |
| Gantt | `BarChart3` | inline | Timeline con barras coloreadas |
| Tabla | `Table2` | `UniversalTableView` | Spreadsheet ordenable, sticky quick-add |
| Wiki | `BookOpen` | Tiptap | Editor rich-text con autosave |

**Quick-add unificado:** Todas las vistas deben tener una barra de creación rápida — preferiblemente una **barra sticky violeta en la parte superior** del área de contenido que aparece/muestra al activarse. NO se usa un botón flotante `+` dentro del área de contenido para creación rápida (eso es del S1 global).

### `UniversalTableView`

**Archivo:** `@/components/ui/UniversalTableView.tsx`

Componente de tabla premium reutilizable para cualquier módulo. Features:
- Columnas configurables con sticky header (`sticky top-0 z-10 backdrop-blur-sm`)
- Sort por columna (click en header)
- Filtros por chips
- Estados vacíos con ícono + mensaje + CTA
- Color-coded status chips
- Row hover con `hover:bg-slate-50/70 dark:hover:bg-white/[0.02]`
- Quick-add sticky en el tope

---

## 9. Barra de Herramientas del Header (Toolbar)

Cada página dentro del `WorkspaceLayout` recibe automáticamente un **header de 56px** (`h-14`) con:

- **Izquierda**: Botón `<` si `depth > 1`, título del módulo en `text-[12px] font-black uppercase tracking-[0.2em]`.
- **Derecha**: Toggle S2 (`PanelLeft`/`PanelLeftOpen`/`PanelLeftClose`), `ThemeToggle`, campana de notificaciones con dot rojo, separador, chip de usuario con avatar.

Las **sub-toolbars de página** (breadcrumbs, tabs de vista, acciones contextuales) van **dentro del contenido** en `children`, nunca duplicando el header del layout. Patrón típico:

```tsx
// Dentro de la página (children de WorkspaceLayout)
<div className="flex flex-col h-full">
  {/* Sub-toolbar */}
  <div className="flex items-center gap-2 px-4 py-2 border-b border-slate-100 dark:border-white/5 shrink-0 h-11">
    {/* Breadcrumbs, view tabs, action buttons */}
  </div>
  {/* Contenido scrolleable */}
  <div className="flex-1 overflow-auto">
    {/* Lista, tabla, kanban, etc. */}
  </div>
</div>
```

---

## 10. Inbox, Notificaciones y Chat MESH

### `WorkspaceInbox`

**Archivo:** `@/components/WorkspaceInbox.tsx`

Drawer de notificaciones que aparece desde la parte inferior del área principal. Se abre al hacer clic en la campana (`Bell`) del header. Estado controlado por `showInbox` en `WorkspaceLayoutInner`.

### `MeshChat`

**Archivo:** `@/components/ui/MeshChat.tsx`

Panel flotante del chat con la IA MESH (el cerebro del ecosistema). Se abre al clicar el **botón flotante** `fixed bottom-8 right-8` (Bot de Lucide, gradiente purple-indigo, indicador verde de online). Estado controlado por `showChat` en `WorkspaceLayoutInner`.

### `CommandCenter`

**Archivo:** `@/components/ui/CommandCenter.tsx`

Paleta de comandos global activable con `Ctrl+K` / `Cmd+K`. Permite búsqueda real (API `/system/search?q=`) y acceso rápido a módulos, acciones y configuración. Se renderiza en `layout.tsx` globalmente.

---

## 11. Contextos de Estado Global

| Contexto | Archivo | Propósito |
|----------|---------|-----------|
| `AuthContext` | `@/context/AuthContext.tsx` | Usuario autenticado, token JWT, logout |
| `SidebarLayerContext` | `@/context/SidebarLayerContext.tsx` | Control de capas S1/S2/S3/RIGHT |
| `CreationContext` | `@/context/CreationContext.tsx` | Apertura global del `UniversalCreationModal` |
| `CommandCenterContext` | `@/context/CommandCenterContext.tsx` | Comandos contextuales del módulo activo |
| `ThemeContext` | `@/app/theme/ThemeContext.tsx` | Tema light/dark, clase `dark` en `<html>` |

### Cómo abrir el modal de creación desde cualquier componente

```tsx
import { useCreation } from '@/context/CreationContext';
const { openModal } = useCreation();

// Abrir para crear una tarea:
openModal('task');
// Tipos disponibles: 'task' | 'doc' | 'reminder' | 'whiteboard' | 'panel'
```

---

## 12. Componentes de UI Reutilizables

Todos en `@/components/ui/`:

| Componente | Uso |
|-----------|-----|
| `Tooltip` | Tooltips anclados, `side="right/top/bottom"`, via Radix |
| `EmptyState` | Estado vacío con ícono + mensaje + CTA. Siempre usarlo en listas vacías |
| `Skeleton` | Placeholder de carga. Usar mientras se cargan datos |
| `InlineEdit` | Edición inline de texto en tablas/listas, click-to-edit |
| `StatusPicker` | Selector de estado con colores semánticos |
| `UserPicker` | Selector de usuario con búsqueda, avatar y nombre |
| `HoverCard` | Card con más info al hacer hover, sin clic/navegación |
| `SplitDropdownButton` | Botón principal + dropdown de opciones secundarias |
| `MetricCard` | Card de métrica con valor, cambio y tendencia |
| `SectionHeader` | Header de sección con título + acción derecha |
| `ThemeToggle` | Toggle light/dark, variante `pill` (header) o `icon` |
| `DataTable` | Tabla simple para datos no-complejos |
| `DatePicker` | Selector de fecha |
| `OmniCreateModal` | Modal extendido de creación (alternativa rica a UniversalCreationModal) |

---

## 13. Convenciones de Código

### Estructura de un archivo de página

```tsx
"use client";

import WorkspaceLayout from '@/components/WorkspaceLayout';
// ... otros imports

export default function MiModuloPage() {
  // 1. Hooks (auth, router, state)
  // 2. Data fetching (useEffect + apiFetch)
  // 3. Handlers
  return (
    <WorkspaceLayout sidebarTitle="Mi Módulo" allowedRoles={['admin']}>
      <div className="flex flex-col h-full">
        {/* Sub-toolbar */}
        <div className="shrink-0 h-11 border-b border-slate-100 dark:border-white/5 flex items-center px-4 gap-2">
          {/* breadcrumbs, tabs de vista, botones */}
        </div>
        {/* Contenido principal */}
        <div className="flex-1 overflow-auto">
          {/* lista / tabla / kanban */}
        </div>
      </div>
    </WorkspaceLayout>
  );
}
```

### Skeleton de carga

```tsx
if (loading) return (
  <WorkspaceLayout sidebarTitle="Cargando...">
    <div className="p-6 space-y-3">
      {[...Array(5)].map((_, i) => (
        <Skeleton key={i} className="h-12 w-full rounded-xl" />
      ))}
    </div>
  </WorkspaceLayout>
);
```

### Estado vacío

```tsx
import EmptyState from '@/components/ui/EmptyState';

<EmptyState
  icon={Users}
  title="No hay miembros aún"
  description="Registra el primer miembro de la comunidad."
  action={{ label: "Añadir Miembro", onClick: () => openModal('task') }}
/>
```

---

## 14. Rutas de Archivos Clave

```
frontend/src/
├── app/
│   ├── layout.tsx            ← Root layout (CommandCenter global, fonts, ThemeProvider)
│   ├── globals.css           ← Variables CSS base
│   ├── theme/ThemeContext.tsx ← Dark/light mode
│   ├── projects/page.tsx     ← Módulo de proyectos
│   ├── crm/page.tsx          ← Módulo de CRM pastoral
│   ├── academy/              ← Módulo de academia
│   ├── cms/                  ← Módulo de gestión de contenido web
│   ├── finances/             ← Módulo financiero
│   ├── wiki/                 ← Wiki / base de conocimiento
│   └── spiritual-life/       ← Vida espiritual y certificados
├── components/
│   ├── WorkspaceLayout.tsx   ← ⭐ Wrapper raíz de toda la app autenticada
│   ├── WorkspaceMiniSidebar.tsx ← S1 (rail de 64px)
│   ├── WorkspaceMainSidebar.tsx ← S2 (nav de módulo)
│   ├── WorkspaceInbox.tsx    ← Drawer de notificaciones
│   ├── ViewSwitcher.tsx      ← Tabs de vista (lista/kanban/tabla/etc.)
│   └── ui/
│       ├── Sidebar3.tsx      ← S3 (panel de contexto)
│       ├── RightPanel.tsx    ← Panel derecho de detalle
│       ├── UniversalTableView.tsx ← Tabla premium reutilizable
│       ├── UniversalCreationModal.tsx ← Modal de creación global
│       ├── CommandCenter.tsx ← Paleta Ctrl+K
│       ├── MeshChat.tsx      ← Chat IA MESH
│       └── ...               ← Otros componentes UI
├── context/
│   ├── SidebarLayerContext.tsx ← Orquestación de capas S1/S2/S3/RIGHT
│   ├── CreationContext.tsx   ← Control del modal de creación
│   ├── CommandCenterContext.tsx
│   └── AuthContext.tsx
├── design/
│   ├── tokens.ts             ← Design tokens (colores, tipografía, sombras)
│   ├── README.md             ← Documentación completa del UI Kit
│   ├── CONTRIBUTING.md       ← Guías de contribución
│   ├── ACCESSIBILITY.md      ← Guías de accesibilidad
│   └── components/           ← Componentes del design system
│       ├── DSButton.tsx      ← Botones (primary, secondary, ghost)
│       ├── DSBadge.tsx       ← Badges (slate, blue, emerald, amber)
│       ├── DSCard.tsx        ← Cards (light, dark, glass)
│       ├── DSMetric.tsx      ← Métricas/KPIs
│       ├── DSChart.tsx       ← Gráficos (line, area, bar)
│       ├── DSInput.tsx       ← Inputs con label, error, icon
│       ├── DSSelect.tsx      ← Selects nativos estilizados
│       ├── DSModal.tsx       ← Modales con backdrop
│       ├── DSTable.tsx       ← Tablas con sorting (TanStack)
│       ├── DSTabs.tsx        ← Navegación por tabs
│       ├── DSTooltip.tsx     ← Tooltips con Radix
│       ├── DSToast.tsx       ← Notificaciones toast
│       ├── DSSkeleton.tsx    ← Skeletons de carga
│       ├── DSSectionHeader.tsx ← Headers de sección
│       ├── DSToolbarChip.tsx ← Chips de toolbar/filtros
│       └── DSCommandEntry.tsx ← Entradas de command palette
└── lib/
    └── http.ts               ← apiFetch helper
```

---

## 15. Checklist antes de entregar cualquier cambio de frontend

- [ ] ¿La página usa `WorkspaceLayout` como wrapper?
- [ ] ¿El módulo infiere correctamente su `MODULE_CONFIG` por ruta, o se pasan `sidebarTitle/sidebarSections`?
- [ ] ¿Se usó `RightPanel` o `Sidebar3` en lugar de un modal fullscreen para detalles?
- [ ] ¿Los datos se obtienen con `apiFetch` y el `token` de `useAuth()`?
- [ ] ¿Se muestra `Skeleton` mientras cargan los datos?
- [ ] ¿Se muestra `EmptyState` cuando la lista está vacía?
- [ ] ¿Todas las clases tienen su par `dark:` definido?
- [ ] ¿Los íconos son de Lucide React (NO emojis en la UI de workspace)?
- [ ] ¿El quick-add es una barra sticky, no un input enterrado dentro de la lista?
- [ ] ¿La vista con múltiples entidades ofrece al menos 2 modos (lista + otro)?
- [ ] ¿Los textos de la UI están en español (excepto código/keys técnicas)?
- [ ] ¿`active:scale-95 transition-all` en los botones primarios?

## Resources & Integration

- **Aesthetic Expert:** Este skill puede complementarse con `aesthetic-expert` para reglas visuales detalladas (colores, tipografía, animaciones).
- **Mesh Architect:** Para entender cómo el frontend se conecta con los agentes del ecosistema, usar `mesh-architect`.
- **CRM Manager:** Para páginas del módulo de comunidad/miembros, consultar `crm-manager`.
- **LMS Coordinator:** Para páginas del módulo de academia, consultar `lms-coordinator`.
