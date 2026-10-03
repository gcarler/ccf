# CCF Design System - UI Kit

Sistema de diseño y componentes UI para la plataforma CCF. Basado en la filosofía "Clean Productivity".

## Arquitectura del Sistema de Componentes

El frontend de CCF tiene **tres capas** de componentes:

```
src/
├── design/                          ← Sistema de diseño (primitivas atómicas)
│   ├── tokens-semantic.ts           ← Tokens semánticos (fuente de verdad TS)
│   ├── components/                  ← Componentes base (DS*)
│   └── README.md                    ← Esta documentación
│
└── components/
    ├── ui/                          ← Componentes UI reutilizables
    │   ├── DataTable.tsx            ← Tabla interactiva (TanStack)
    │   ├── RightPanel.tsx           ← Panel lateral derecho (drawer)
    │   ├── inline-editors/          ← Editores inline para edición directa
    │   └── ...
    └── Workspace*.tsx               ← Componentes de layout del workspace
```

## Instalación

Los componentes de diseño se importan directamente:

```tsx
import { DSButton, DSCard, DSMetric } from '@/design';
```

Los componentes UI se importan desde `@/components`:

```tsx
import { DataTable, DSSkeleton, PersonaSelect } from '@/components';
import TaskEditDrawer from '@/components/ui/TaskEditDrawer';
```

## Sistema de Diseño (Primitivas)

### Componentes Disponibles

| Componente | Descripción | Docs |
|------------|-------------|------|
| `DSButton` | Botones con variantes primary, secondary, ghost | [Story](../../design/components/DSButton.stories.tsx) |
| `DSBadge` | Insignias de estado (slate, blue, emerald, amber) | [Story](../../design/components/DSBadge.stories.tsx) |
| `DSCard` | Contenedores (light, dark, glass) | [Story](../../design/components/DSCard.stories.tsx) |
| `DSChart` | Gráficos (line, area, bar) con Recharts | [Story](../../design/components/DSChart.stories.tsx) |
| `DSCommandEntry` | Entradas de command palette | [Story](../../design/components/DSCommandEntry.stories.tsx) |
| `DSInput` | Inputs con label, error, icon | [Story](../../design/components/DSInput.stories.tsx) |
| `DSMetric` | KPIs para dashboards | [Story](../../design/components/DSMetric.stories.tsx) |
| `DSModal` | Modales con backdrop | [Story](../../design/components/DSModal.stories.tsx) |
| `DSSelect` | Selects nativos estilizados | [Story](../../design/components/DSSelect.stories.tsx) |
| `DSSectionHeader` | Headers de sección | [Story](../../design/components/DSSectionHeader.stories.tsx) |
| `DSSkeleton` | Skeletons de carga | [Story](../../design/components/DSSkeleton.stories.tsx) |
| `DSTable` | Tablas con sorting (TanStack Table) | [Story](../../design/components/DSTable.stories.tsx) |
| `DSTabs` | Navegación por tabs | [Story](../../design/components/DSTabs.stories.tsx) |
| `DSToolbarChip` | Filtros tipo chip | [Story](../../design/components/DSToolbarChip.stories.tsx) |
| `DSTooltip` | Tooltips con Radix | [Story](../../design/components/DSTooltip.stories.tsx) |
| `DSToast` | Notificaciones toast | [Story](../../design/components/DSToast.stories.tsx) |
| `DSTypography` | Primitivo tipográfico (familia, tamaño, peso, tracking) | [Story](../../design/components/DSTypography.stories.tsx) |

### Tokens de Diseño

Definidos en `tokens.ts`:

- **colors**: primary, emerald, amber, blue, slate, danger
- **radii**: sm (4px), md (6px), lg (8px), xl (12px), pill (9999px)
- **shadows**: soft, card, dropdown, inner
- **typography**: familias semánticas Outfit (display/headline), Inter (body/label) y JetBrains Mono (mono), vía `next/font/google` (ver `layout.tsx` y `globals.css`); escala de 10 tamaños (`--text-2xs` 10px → `--text-4xl` 32px), 5 pesos (`--weight-*`), 5 tracking (`--tracking-*`) y 4 line-heights (`--leading-*`). `DSTypography` consume estos tokens directamente (tamaños vía `text-*` de `tailwind.config.ts` y tracking vía `tracking-[var(--tracking-*)]`).
- **spacing**: xs (4px), sm (6px), md (8px), lg (12px), xl (16px)
- **motion**: 3 duraciones, 2 easing curves

## Biblioteca de Componentes UI

### Componentes Disponibles

| Componente | Descripción | Storybook |
|------------|-------------|-----------|
| `CommandCenter` | Paleta de comandos (Ctrl+K) | [Story](../ui/CommandCenter.stories.tsx) |
| `DataTable` | Tabla interactiva con sorting | [Story](../ui/DataTable.stories.tsx) |
| `EmptyState` | Estado vacío con icono y acción | [Story](../ui/EmptyState.stories.tsx) |
| `PersonaSelect` | Selector de personas con búsqueda | [Story](../ui/PersonaSelect.stories.tsx) |
| `RightPanel` | Panel lateral derecho (push/overlay) | [Story](../ui/RightPanel.stories.tsx) |
| `SidePanel` | Panel lateral izquierdo con navegación | [Story](../ui/SidePanel.stories.tsx) |
| `AgGridTable` | Tabla empresarial AG Grid tematizada | [Story](../ui/AgGridTable.stories.tsx) |
| `SplitDropdownButton` | Botón dividido con dropdown | [Story](../ui/SplitDropdownButton.stories.tsx) |
| `StatusPicker` | Selector de estado personalizado | [Story](../ui/StatusPicker.stories.tsx) |
| `TextPromptDrawer` | Drawer para entrada de texto | [Story](../ui/TextPromptDrawer.stories.tsx) |
| `ThemeToggle` | Cambio de tema claro/oscuro (icon/pill/row) | [Story](../ui/ThemeToggle.stories.tsx) |
| `OptimizedImage` | Imagen con carga optimizada | [Story](../ui/OptimizedImage.stories.tsx) |
| `UniversalCalendarView` | Vista calendario de eventos | [Story](../ui/UniversalCalendarView.stories.tsx) |
| `UniversalCreationDrawer` | Drawer universal de creación | [Story](../ui/UniversalCreationDrawer.stories.tsx) |
| `UniversalListView` | Vista lista genérica | [Story](../ui/UniversalListView.stories.tsx) |
| `UniversalWikiView` | Editor wiki con TipTap | [Story](../ui/UniversalWikiView.stories.tsx) |

### Editores Inline

| Componente | Descripción | Storybook |
|------------|-------------|-----------|
| `InlineTextInput` | Input inline editable | [Story](../ui/inline-editors/inline-editors.stories.tsx) |
| `InlineTextArea` | Textarea inline editable | [Story](../ui/inline-editors/inline-editors.stories.tsx) |
| `InlineStatusPicker` | Selector de estado inline | [Story](../ui/inline-editors/inline-editors.stories.tsx) |
| `InlinePriorityPicker` | Selector de prioridad inline | [Story](../ui/inline-editors/inline-editors.stories.tsx) |

## Uso Básico

### Botones
```tsx
import { DSButton } from '@/design';

<DSButton variant="primary">Guardar</DSButton>
<DSButton variant="secondary" loading>Procesando</DSButton>
<DSButton variant="ghost" disabled>Deshabilitado</DSButton>
```

### Cards
```tsx
import { DSCard } from '@/design';

<DSCard tone="light" padding="md">
  <h3>Contenido</h3>
</DSCard>
```

### Inputs
```tsx
import { DSInput } from '@/design';

<DSInput
  label="Email"
  placeholder="correo@ejemplo.com"
  error="Email requerido"
/>
```

### Modales
```tsx
import { DSModal } from '@/design';

<DSModal open={isOpen} onClose={() => setIsOpen(false)} title="Confirmar">
  <p>¿Estás seguro?</p>
</DSModal>
```

### Toasts
```tsx
import { toast } from '@/design';

toast.success('Guardado correctamente');
toast.error('Error al guardar');
```

### Tipografía
```tsx
import { DSTypography } from '@/design';

<DSTypography as="h2" family="headline" size="xl" weight="semibold" tracking="tight">
  Título de página
</DSTypography>
<DSTypography family="label" size="2xs" weight="bold" tracking="widest" uppercase>
  Etiqueta de sección
</DSTypography>
```

## Librería de Badges del Módulo de Proyectos

El módulo de Proyectos consume badges canónicos (en `components/projects/badges.tsx`)
construidos sobre las configs visuales compartidas de `@/lib/projects/constants`:

| Badge | Uso |
|-------|-----|
| `TaskStatusBadge` | Estado de tarea (canónico o slug de fase dinámica, con `dotStyle`) |
| `TaskPriorityBadge` | Prioridad de tarea (`low` → `urgent`) |
| `ProjectStatusBadge` | Estado de proyecto (enum de 5 valores, soporta label custom) |
| `TaskNodeBadge` | Nodo operativo de la tarea (F2) |

```tsx
import { TaskStatusBadge, ProjectStatusBadge } from '@/components/projects/badges';

<TaskStatusBadge value={task.status} />
<ProjectStatusBadge value={project.status} label="En Marcha" />
```

## Storybook

Para ver todos los componentes documentados:

```bash
npm run storybook
```

Storybook contiene historias para:
- **Design/**: 18 componentes del sistema de diseño (incluye el specímen de tipografía)
- **UI/**: 22 componentes de la biblioteca de componentes
- **Projects/**: badges, tarjetas Kanban, timeline de actividad, árbol de rutas, metadatos de tarea y secciones de detalle
- **Example/**: Componentes básicos de ejemplo (Button, Header, Page)

## Mejores Prácticas

### Cuándo crear un componente en design/ vs ui/

- **`design/`**: Crear primitivas atómicas (botones, inputs, selects) que serán la base de toda la UI y deben ser 100% reutilizables.
- **`components/ui/`**: Crear componentes compuestos (drawers, tablas, calendars) que orquestan múltiples primitivas del sistema de diseño para resolver un patrón UI específico.

### Reglas

1. Todo componente nuevo debe tener su historia en Storybook
2. Usar tokens de diseño (`tokens.ts` / variables CSS `hsl(var(--*))`) en lugar de valores hardcodeados
3. Los componentes UI deben construirse sobre primitivas del sistema de diseño (DSButton en lugar de `<button>`)
4. Importar desde `@/design` para primitivas, desde `@/components/ui/` para compuestos

## Contribución

Ver [CONTRIBUTING.md](./CONTRIBUTING.md) para guías de contribución.

## Accesibilidad

Ver [ACCESSIBILITY.md](./ACCESSIBILITY.md) para guías de a11y.
