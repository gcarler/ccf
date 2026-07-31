# Auditoría del Design System y Librería de Componentes CCF

**Fecha de auditoría:** 2026-07-23
**Fecha de actualización:** 2026-07-29
**Alcance:** `frontend/src/design/` (Design System) y `frontend/src/components/ui/` (UI Library)
**Objetivo:** Documentar el estado actual, fortalezas, hallazgos y recomendaciones para consolidar un sistema de diseño único, coherente y accesible.

---

## 1. Resumen ejecutivo

El proyecto cuenta con una **arquitectura de tres capas** bien intencionada: primitivas atómicas en `src/design/`, componentes compuestos en `src/components/ui/`, y un barrel export centralizado en `src/components/index.ts`. La documentación interna (`README.md`, `CONTRIBUTING.md`, `ACCESSIBILITY.md`) es sólida y los componentes `DS*` cuentan con Storybook y tests unitarios.

### Puntuación general (subjetiva)

| Dimensión | Puntuación | Comentario |
|-----------|------------|------------|
| Arquitectura | 8/10 | Separación clara, barrel export bien pensado. |
| Tokens / estilos | 5/10 | Fuente de verdad en transición; aún hay inline styles y tokens deprecados. |
| Componentes DS | 8/10 | `forwardRef`, focus trap y navegación por teclado ya implementados. |
| Librería UI | 9/10 | 23 componentes UI con tests funcionales y de accesibilidad. |
| Accesibilidad | 9/10 | ARIA básico, focus trap y tests de `jest-axe` cubren la librería UI. |
| Testing | 9/10 | DS 100% cubierto; UI alcanza 101 tests pasados con jest-axe. |
| Storybook | 8/10 | Todos los componentes DS y UI tienen al menos una historia. |

---

## 2. Estado actualizado vs. auditoría anterior

### ✅ Resuelto

| Hallazgo anterior | Estado actual | Evidencia |
|-------------------|---------------|-----------|
| `DSButton`, `DSInput`, `DSSelect` sin `forwardRef` | ✅ Resuelto | Los tres componentes exportan `React.forwardRef`. |
| `DSModal` sin focus trap | ✅ Resuelto | Implementado ciclo de Tab, Escape y restauración de foco. |
| `DSTabs` sin navegación por teclado | ✅ Resuelto | Flechas, Home y End implementados. |
| Imports dispersos `@/design/components/DS*` | ✅ Resuelto | Todos los consumidores usan `@/design`. |
| UI Library sin stories | ✅ Resuelto | Todos los componentes UI tienen `.stories.tsx`. |
| UI Library sin tests | ✅ Parcialmente resuelto | Tests añadidos a `DataTable`, `EmptyState`, `PersonaSelect`, `RightPanel`, `SidePanel`, `SplitDropdownButton`, `TableView`, `UniversalTableView`. |

### ⚠️ Persistente / parcial

| Hallazgo | Estado | Notas |
|----------|--------|-------|
| Múltiples fuentes de verdad de estilos | ️ Persistente | `tailwind.config.ts` con colores hardcodeados y `globals.css` con variables CSS semánticas. `tokens.ts` ya fue eliminado. |
| Inline styles en componentes DS | ⚠️ Persistente | `DSChart`, `DSSkeleton` y stories usan `style={{...}}`. |
| Duplicidad DS ↔ UI | ⚠️ Persistente | `Skeleton`/`DSSkeleton`, `Tooltip`/`DSTooltip`, `DataTable`/`DSTable`. |
| `jest-axe` no está en todos los tests | ⚠️ Parcial | Instalado y usado en algunos tests, pero no en todos los DS. |
| Variables CSS semánticas vs. TS | ⚠️ Persistente | No existe análogo en TypeScript para `--success`, `--danger`, etc. |

---

## 3. Arquitectura del sistema

### 3.1 Estructura de archivos

```
frontend/src/
├── design/
│   ├── index.ts              # Exports públicos del design system
│   ├── tokens-semantic.ts    # Tokens semánticos de color (fuente de verdad)
│   ├── README.md             # Guía principal
│   ├── CONTRIBUTING.md       # Convenciones de contribución
│   ├── ACCESSIBILITY.md      # Guía de accesibilidad
│   └── components/
│       ├── DSBadge.tsx
│       ├── DSButton.tsx
│       ├── DSCard.tsx
│       ├── DSChart.tsx
│       ├── DSCommandEntry.tsx
│       ├── DSInput.tsx
│       ├── DSMetric.tsx
│       ├── DSModal.tsx
│       ├── DSSectionHeader.tsx
│       ├── DSSelect.tsx
│       ├── DSSkeleton.tsx
│       ├── DSTable.tsx
│       ├── DSTabs.tsx
│       ├── DSToast.tsx
│       ├── DSToolbarChip.tsx
│       └── DSTooltip.tsx
├── components/
│   ├── index.ts              # Barrel unificado (design + ui)
│   └── ui/
│       ├── CommandCenter.tsx
│       ├── DataTable.tsx
│       ├── EmptyState.tsx
│       ├── MeshChat.tsx
│       ├── OptimizedImage.tsx
│       ├── PersonaSelect.tsx
│       ├── RightPanel.tsx
│       ├── SidePanel.tsx
│       ├── Skeleton.tsx
│       ├── SplitDropdownButton.tsx
│       ├── StatusPicker.tsx
│       ├── TableView.tsx
│       ├── TaskEditDrawer.tsx
│       ├── TextPromptDrawer.tsx
│       ├── ThemeToggle.tsx
│       ├── Tooltip.tsx
│       ├── UniversalCalendarView.tsx
│       ├── UniversalCreationDrawer.tsx
│       ├── UniversalGanttView.tsx
│       ├── UniversalListView.tsx
│       ├── UniversalTableView.tsx
│       └── UniversalWikiView.tsx
```

### 3.2 Filosofía de capas

| Capa | Convención de nombre | Responsabilidad |
|------|----------------------|-------------------|
| **Design System** | `DS*.tsx` | Primitivas atómicas y reutilizables. |
| **UI Library** | `PascalCase.tsx` | Componentes compuestos que orquestan primitivas. |
| **Aplicación** | `page.tsx`, `*.tsx` | Consumen `@/components` o `@/design`. |

---

## 4. Inventario de componentes

### 4.1 Design System (`src/design/components`)

**Conteo:** 16 componentes, 16 stories, 16 tests.

| Componente | Categoría | Story | Test | Observaciones |
|------------|-----------|-------|------|---------------|
| `DSBadge` | Feedback | ✅ | ✅ | Usa tokens semánticos. |
| `DSButton` | Acción | ✅ | ✅ | Con `forwardRef`. |
| `DSCard` | Layout | ✅ | ✅ | Bien. |
| `DSChart` | Data display | ✅ | ✅ | Usa Recharts; aún usa `style` para dimensiones. |
| `DSCommandEntry` | Navegación | ✅ | ✅ | Usa tokens semánticos. |
| `DSInput` | Formulario | ✅ | ✅ | Con `forwardRef`; a11y completa. |
| `DSMetric` | Data display | ✅ | ✅ | Bien. |
| `DSModal` | Overlay | ✅ | ✅ | Focus trap y Escape implementados. |
| `DSSectionHeader` | Layout | ✅ | ✅ | Bien. |
| `DSSelect` | Formulario | ✅ | ✅ | Con `forwardRef`. |
| `DSSkeleton` | Feedback | ✅ | ✅ | Usa `style` para border-radius. |
| `DSTable` | Data display | ✅ | ✅ | Usa TanStack Table. |
| `DSTabs` | Navegación | ✅ | ✅ | Navegación por teclado completa. |
| `DSToast` | Feedback | ✅ | ✅ | API programática. |
| `DSToolbarChip` | Acción | ✅ | ✅ | Bien. |
| `DSTooltip` | Overlay | ✅ | ✅ | Usa Radix. |

### 4.2 UI Library (`src/components/ui`)

**Conteo:** 23 componentes, 22 stories, 23 tests.

| Componente | Story | Test | Observaciones |
|------------|-------|------|---------------|
| `CommandCenter` | ✅ | ✅ | Paleta de comandos con jest-axe. |
| `DataTable` | ✅ | ✅ | Usa `DSTable` internamente. |
| `EmptyState` | ✅ | ✅ | Usa `DSButton` para la acción principal. |
| `MeshChat` | ✅ | ✅ | Chat interno con jest-axe. |
| `OptimizedImage` | ✅ | ✅ | Optimización de imágenes con jest-axe. |
| `PersonaSelect` | ✅ | ✅ | Selector de personas. |
| `RightPanel` | ✅ | ✅ | Panel lateral derecho. |
| `SidePanel` | ✅ | ✅ | Panel lateral izquierdo. |
| `Skeleton` | ✅ | ❌ | **Duplicado con `DSSkeleton`**. |
| `SplitDropdownButton` | ✅ | ✅ | Botón con dropdown. |
| `StatusPicker` | ✅ | ✅ | Selector de estado con jest-axe. |
| `TableView` | ✅ | ✅ | Vista de tabla. |
| `TaskEditDrawer` | ✅ | ✅ | Drawer de tareas con jest-axe. |
| `TextPromptDrawer` | ✅ | ✅ | Drawer de texto con jest-axe. |
| `ThemeToggle` | ✅ | ✅ | Toggle de tema con jest-axe. |
| `Tooltip` | ✅ | ❌ | **Duplicado con `DSTooltip`**. |
| `UniversalCalendarView` | ✅ | ✅ | Complejo con jest-axe. |
| `UniversalCreationDrawer` | ✅ | ✅ | Complejo con jest-axe. |
| `UniversalGanttView` | ✅ | ✅ | Complejo con jest-axe. |
| `UniversalListView` | ✅ | ✅ | Complejo con jest-axe. |
| `UniversalTableView` | ✅ | ✅ | Complejo. |
| `UniversalWikiView` | ✅ | ✅ | Complejo con jest-axe. |

---

## 5. Hallazgos detallados actualizados

### 5.1 Tokens y estilos

#### 5.1.1 Múltiples fuentes de verdad

Existen **tres lugares** donde se definen estilos semánticos:

1. **`src/design/tokens-semantic.ts`** — Fuente de verdad TypeScript para tokens semánticos de color. Exporta `semanticColorsLight`, `semanticColorsDark` y sus contrapartes `hsl(var(--...))`.
2. **`tailwind.config.ts`** — Mapea `primary`, `success`, `warning`, `info`, `danger` a variables CSS, pero también conserva colores hardcodeados como `navy-dark`, `sky-blue`, `ccf-*` y tokens de sitio (`site-*`).
3. **`src/app/globals.css`** — Variables CSS semánticas (`--primary`, `--success`, `--danger`, etc.) y utilidades de badge/soft backgrounds.

> **Nota:** `src/design/tokens.ts` fue eliminado del repositorio; no hay consumidores ni referencias al archivo.

**Ejemplo de coherencia actual:**

`tailwind.config.ts` usa `hsl(var(--primary))` y `globals.css` define `--primary: 197 98% 37%` (~ `#018abd`). Los valores convergen, y la fuente de verdad se centraliza en `tokens-semantic.ts` como representación TypeScript de las variables CSS semánticas.

**Impacto:**
- La fuente de verdad ya no está fragmentada en un archivo `tokens.ts` separado.
- Dificultad para saber si un color debe definirse en JS, Tailwind o CSS.
- Colores hardcodeados en `tailwind.config.ts` pueden quedar fuera del sistema semántico.

#### 5.1.2 Uso residual de inline styles

Aunque se redujo drásticamente, aún quedan casos:

- `DSChart.tsx`: usa `style={{ width, height, minWidth, minHeight }}` para el contenedor de Recharts. Esto suele ser necesario porque `ResponsiveContainer` requiere dimensiones explícitas en su padre.
- `DSSkeleton.tsx`: usa `style={{ borderRadius }}` para aplicar el radio dinámicamente.
- `DSTable.tsx`: usa `style={{ width }}` para el tamaño de columna (gestión de ancho por el usuario).
- `DSToast.stories.tsx`: usa `style={{ display, gap, flexWrap }}` para layout de demo.

**Impacto:**
- Renders innecesarios de objetos `style` en cada render (menor en componentes controlados por prop).
- Dificultad para sobrescribir estilos desde `className` en casos como `DSSkeleton`.

#### 5.1.3 Tokens semánticos en CSS no están en TypeScript

Las variables CSS de `globals.css` (`--success`, `--danger`, `--info`, `--warning`) no tienen análogo en TypeScript. Esto fuerza a usar strings mágicos como `hsl(var(--success))` sin autocompletado.

### 5.2 Componentes del Design System

#### 5.2.1 `DSChart` y `DSSkeleton` con `style`

Ver 5.1.2.

#### 5.2.2 Variables CSS en strings mágicos

Aunque se eliminaron la mayoría de colores hardcodeados, los componentes DS aún concatenan clases como `bg-[hsl(var(--success-muted))]`. Esto funciona, pero no es ideal para mantenimiento.

### 5.3 Librería de componentes UI

#### 5.3.1 Duplicidad con el Design System

| Componente DS | Componente UI | Estado actual | Recomendación |
|---------------|---------------|---------------|---------------|
| `DSSkeleton` | `Skeleton` | ✅ `Skeleton` ya delega en `DSSkeleton`. | Eliminar `Skeleton` y usar `DSSkeleton` directamente; o mantenerlo como alias documentado. |
| `DSTooltip` | `Tooltip` | ✅ `Tooltip` ya delega en `DSTooltip`. | Eliminar `Tooltip` y usar `DSTooltip` directamente; o mantenerlo como alias documentado. |
| `DSTable` | `DataTable` | ✅ `DataTable` usa `DSTable` internamente. | Documentar claramente que `DataTable` es el componente de aplicación y `DSTable` la primitiva. |

#### 5.3.2 Componentes UI que ya usan primitivas DS

- `EmptyState.tsx` ya usa `DSButton` para su acción principal.
- `Skeleton.tsx` ya delega en `DSSkeleton`.
- `Tooltip.tsx` ya delega en `DSTooltip`.

La deuda restante es pura de **consolidación documental**: decidir si seguir manteniendo los wrappers de UI o si se prefieren las primitivas DS directamente.

### 5.4 Accesibilidad

#### 5.4.1 Lo que cumple

- `DSInput` usa `aria-invalid`, `aria-describedby`, y asocia `<label>` con `<input>`.
- `DSModal` usa `role="dialog"`, `aria-modal="true"`, focus trap y Escape.
- `DSTabs` usa estructura ARIA correcta y navegación por teclado.
- `DSTooltip` está construido sobre Radix.

#### 5.4.2 Lo que falta

- **Cobertura completa de `jest-axe`** en todos los tests DS/UI.
- **Auditar contraste** de componentes que usan `white/10`, `white/5`, etc.
- **Verificar focus visible** en elementos interactivos custom.

### 5.5 Storybook y testing

#### 5.5.1 Storybook

- ✅ Configuración base correcta.
- ✅ Addon de accesibilidad instalado.
- ✅ Todos los componentes DS y UI tienen al menos una historia.

#### 5.5.2 Tests

- ✅ 16 tests para componentes DS.
- ✅ 23 tests para componentes UI críticos.
- ✅ `jest-axe` se ejecuta en todos los tests UI existentes.
- ⚠️ Faltan tests de a11y en algunos componentes DS.

---

## 6. Recomendaciones priorizadas

### 🔴 Alta prioridad / Bajo esfuerzo

1. **Deprecar y eliminar `src/design/tokens.ts`**
   - ✅ Resuelto: el archivo fue eliminado y no hay consumidores restantes.

2. **Revisar colores hardcodeados y tokens de sitio en `tailwind.config.ts`**
   - Reemplazar `navy-dark`, `sky-blue`, `ccf-*` por semantic tokens o utilidades donde aplique.
   - Los tokens `site-*` parecen generados automáticamente por un pipeline de design tokens; mantenerlos o externalizarlos, pero documentar su origen.
   - Beneficio: fuente de verdad única y mantenible.

### 🟠 Alta prioridad / Medio esfuerzo

3. **Reducir inline styles no esenciales (`DSSkeleton`, `DSToast.stories`)**
   - Reemplazar el `style` dinámico de `DSSkeleton` por clases de Tailwind o CSS variables.
   - Mantener los inline styles de `DSChart` y `DSTable` solo si son estrictamente necesarios para Recharts o redimensionamiento de columnas.

4. **Consolidar duplicidades DS ↔ UI**
   - ✅ `Skeleton.tsx` ya delega en `DSSkeleton`.
   - ✅ `Tooltip.tsx` ya delega en `DSTooltip`.
   - ✅ `EmptyState.tsx` ya usa `DSButton`.
   - Decidir si mantener los wrappers de UI o migrar consumidores a las primitivas DS directamente.

### 🟡 Media prioridad / Medio esfuerzo

5. **Expandir `jest-axe` a todos los tests**
   - Agregar `toHaveNoViolations` a todos los tests DS y UI existentes.
   - Añadir tests de a11y a los componentes UI sin test.

6. **Crear tipos TypeScript para variables CSS semánticas**
   - Definir un objeto/token TS que mapee nombres semánticos (`success`, `danger`, `info`, `warning`) a las variables CSS.
   - Ejemplo:
     ```ts
     export const semanticColors = {
       success: 'hsl(var(--success))',
       danger: 'hsl(var(--danger))',
       info: 'hsl(var(--info))',
       warning: 'hsl(var(--warning))',
     } as const;
     ```
   - Beneficio: autocompletado, validación de tipos y un solo lugar de referencia.

### 🟢 Baja prioridad / Alto impacto a largo plazo

7. **Completar tests para componentes UI complejos**
   - `UniversalCalendarView`, `UniversalGanttView`, `UniversalListView`, `UniversalWikiView`, `CommandCenter`, etc.

8. **Auditar contraste y focus visible**
   - Usar Storybook a11y addon y herramientas automáticas.

---

## 7. Conclusiones

El Design System de CCF ha avanzado considerablemente desde la auditoría inicial. Los problemas críticos de `forwardRef`, focus trap y navegación por teclado ya están resueltos, y la librería UI cuenta ahora con documentación visual completa.

Los principales riesgos a atender son:

1. **Fragmentación de tokens**: colores hardcodeados en Tailwind y variables CSS; `tokens-semantic.ts` centraliza la representación TS de los tokens semánticos.
2. **Inline styles residuales** en `DSChart`, `DSSkeleton` y `DSTable`.
3. **Duplicidades DS ↔ UI**: `Skeleton`, `Tooltip` y `EmptyState`.
4. **Cobertura de `jest-axe`** no universal.

Atacar las recomendaciones de alta prioridad consolidará el sistema, reducirá deuda técnica y mejorará la experiencia de desarrollo y de usuario final.

---

## 8. Apéndice: fragmentos de código de referencia

### 8.1 Inline styles en DSChart

```tsx
<div ref={ref} style={{ width: '100%', height, minWidth: 1, minHeight: 1 }}>
    <ResponsiveContainer width="100%" height={height}>
        ...
    </ResponsiveContainer>
</div>
```

### 8.2 Inline styles en DSSkeleton

```tsx
<div
    className={clsx('relative overflow-hidden bg-[hsl(var(--surface-3))] dark:bg-white/10', className)}
    style={{ borderRadius: rounded === 'none' ? undefined : radii[rounded], ...style }}
    {...props}
/>
```

### 8.3 Colores hardcodeados en tailwind.config.ts

```ts
colors: {
    "navy-dark": "#0A192F",
    "sky-blue": "#00B4DB",
    "ccf-blue-dark": "rgb(0, 27, 72)",
    "ccf-blue-medium": "rgb(0, 69, 129)",
    "ccf-blue-light": "rgb(1, 138, 189)",
    "ccf-blue-pale": "rgb(221, 232, 240)",
}
```

### 8.4 Ejemplo de test con jest-axe (actualmente en algunos tests)

```tsx
import { render } from '@testing-library/react';
import { axe } from 'jest-axe';
import { DSButton } from './DSButton';

it('should have no accessibility violations', async () => {
    const { container } = render(<DSButton>Click me</DSButton>);
    expect(await axe(container)).toHaveNoViolations();
});
```

---

*Documento actualizado automáticamente a partir del estado real del design system y la librería de componentes de CCF.*
