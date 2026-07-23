# Auditoría del Design System y Librería de Componentes CCF

**Fecha de auditoría:** 2026-07-23  
**Alcance:** `frontend/src/design/` (Design System) y `frontend/src/components/ui/` (UI Library)  
**Objetivo:** Documentar el estado actual, fortalezas, hallazgos y recomendaciones para consolidar un sistema de diseño único, coherente y accesible.

---

## 1. Resumen ejecutivo

El proyecto cuenta con una **arquitectura de tres capas** bien intencionada: primitivas atómicas en `src/design/`, componentes compuestos en `src/components/ui/`, y un barrel export centralizado en `src/components/index.ts`. La documentación interna (`README.md`, `CONTRIBUTING.md`, `ACCESSIBILITY.md`) es sólida y los componentes `DS*` cuentan con Storybook y tests unitarios.

Sin embargo, existen **inconsistencias importantes** entre fuentes de verdad de estilos (`tokens.ts`, `tailwind.config.ts`, `globals.css`), **duplicidad** entre primitivas y componentes UI, y **deuda de accesibilidad** en componentes críticos como `DSModal` y `DSTabs`.

### Puntuación general (subjetiva)

| Dimensión | Puntuación | Comentario |
|-----------|------------|------------|
| Arquitectura | 8/10 | Separación clara, barrel export bien pensado. |
| Tokens / estilos | 5/10 | Múltiples fuentes de verdad; inline styles dispersos. |
| Componentes DS | 7/10 | Buenos componentes, pero faltan `forwardRef` y patrones a11y. |
| Librería UI | 6/10 | Útil, pero con duplicidades y poca documentación visual. |
| Accesibilidad | 5/10 | ARIA básico presente; focus trap y navegación teclado ausentes. |
| Testing | 6/10 | Buena cobertura en DS; casi nula en UI. |
| Storybook | 7/10 | Configurado para DS; UI parcialmente documentado. |

---

## 2. Arquitectura del sistema

### 2.1 Estructura de archivos

```
frontend/src/
├── design/
│   ├── index.ts              # Exports públicos del design system
│   ├── tokens.ts             # Tokens de diseño (colores, tipografía, espaciado, etc.)
│   ├── README.md             # Guía principal
│   ├── CONTRIBUTING.md       # Convenciones de contribución
│   ├── ACCESSIBILITY.md      # Guía de accesibilidad
│   └── components/
│       ├── DSButton.tsx
│       ├── DSCard.tsx
│       ├── DSInput.tsx
│       ├── DSModal.tsx
│       ├── DSTable.tsx
│       ├── DSTabs.tsx
│       └── ... (16 componentes DS)
├── components/
│   ├── index.ts              # Barrel unificado (design + ui)
│   └── ui/
│       ├── CommandCenter.tsx
│       ├── DataTable.tsx
│       ├── EmptyState.tsx
│       ├── Skeleton.tsx
│       ├── SidePanel.tsx
│       └── ... (39 componentes UI)
```

### 2.2 Filosofía de capas

| Capa | Convención de nombre | Responsabilidad |
|------|----------------------|-------------------|
| **Design System** | `DS*.tsx` | Primitivas atómicas y reutilizables. |
| **UI Library** | `PascalCase.tsx` | Componentes compuestos que orquestan primitivas. |
| **Aplicación** | `page.tsx`, `*.tsx` | Consumen `@/components` o `@/design`. |

### 2.3 Fortalezas arquitectónicas

- **Separación de responsabilidades clara** entre primitivas y compuestos.
- **Barrel export** (`src/components/index.ts`) que simplifica el consumo.
- **Documentación proactiva** con guías de contribución y accesibilidad.
- **Storybook configurado** con addon de accesibilidad (`@storybook/addon-a11y`).
- **Testing base** con Vitest para componentes `DS*`.

---

## 3. Inventario de componentes

### 3.1 Design System (`src/design/components`)

**Conteo:** 16 componentes, 16 stories, 16 tests.

| Componente | Categoría | Story | Test | Observaciones |
|------------|-----------|-------|------|---------------|
| `DSBadge` | Feedback | ✅ | ✅ | Sin `forwardRef`. |
| `DSButton` | Acción | ✅ | ✅ | Sin `forwardRef`. |
| `DSCard` | Layout | ✅ | ✅ | Bien. |
| `DSChart` | Data display | ✅ | ✅ | Usa Recharts. |
| `DSCommandEntry` | Navegación | ✅ | ✅ | Colores hardcodeados. |
| `DSInput` | Formulario | ✅ | ✅ | Sin `forwardRef`. |
| `DSMetric` | Data display | ✅ | ✅ | Bien. |
| `DSModal` | Overlay | ✅ | ✅ | Sin focus trap. |
| `DSSectionHeader` | Layout | ✅ | ✅ | Bien. |
| `DSSelect` | Formulario | ✅ | ✅ | Sin `forwardRef`; select nativo. |
| `DSSkeleton` | Feedback | ✅ | ✅ | Bien. |
| `DSTable` | Data display | ✅ | ✅ | Usa TanStack Table. |
| `DSTabs` | Navegación | ✅ | ✅ | Sin navegación con flechas. |
| `DSToast` | Feedback | ✅ | ✅ | API programática básica. |
| `DSToolbarChip` | Acción | ✅ | ✅ | Bien. |
| `DSTooltip` | Overlay | ✅ | ✅ | Usa Radix. |

### 3.2 UI Library (`src/components/ui`)

**Conteo:** 39 componentes, 17 stories.

| Componente | Responsabilidad | Story | Observaciones |
|------------|-----------------|-------|---------------|
| `CommandCenter` | Paleta de comandos | ✅ | Usa contexto interno. |
| `DataTable` | Tabla interactiva | ✅ | Muy similar a `DSTable`. |
| `EmptyState` | Estado vacío | ✅ | Estilos inline, no usa DS. |
| `Skeleton` | Skeleton loader | ✅ | Duplicado con `DSSkeleton`. |
| `PersonaSelect` | Selector de personas | ❌ | Sin documentación visual. |
| `RightPanel` | Panel lateral derecho |  | Sin documentación visual. |
| `SidePanel` | Panel lateral izquierdo | ❌ | Sin documentación visual. |
| `StatusPicker` | Selector de estado | ❌ | Sin documentación visual. |
| `SplitDropdownButton` | Botón con dropdown | ❌ | Sin documentación visual. |
| `TextPromptDrawer` | Drawer de texto | ❌ | Sin documentación visual. |
| `ThemeToggle` | Toggle de tema | ✅ | Simple. |
| `Tooltip` | Tooltip | ❌ | Duplicado con `DSTooltip`. |
| `UniversalCalendarView` | Vista calendario | ✅ | Complejo. |
| `UniversalCreationDrawer` | Drawer universal | ✅ | Complejo. |
| `UniversalGanttView` | Vista Gantt | ✅ | Complejo. |
| `UniversalListView` | Vista lista | ✅ | Complejo. |
| `UniversalWikiView` | Editor wiki | ✅ | Complejo. |

---

## 4. Hallazgos detallados

### 4.1 Tokens y estilos

#### 4.1.1 Múltiples fuentes de verdad

Existen **tres lugares** donde se definen estilos semánticos:

1. **`src/design/tokens.ts`** — Colores HEX, radios, sombras, tipografía.
2. **`tailwind.config.ts`** — Colores Tailwind (`primary`, `navy-dark`, `sky-blue`) y familia de fuentes.
3. **`src/app/globals.css`** — Variables CSS (`--bg-primary`, `--text-primary`, `--success`, etc.).

**Ejemplo de conflicto:**

`tokens.ts` define `colors.primary[500] = '#018abd'`, mientras que `tailwind.config.ts` define `"primary": "#1973f0"`. Ambos representan el "azul principal" pero con valores distintos.

**Impacto:**
- Inconsistencia visual entre componentes que usan tokens vs. los que usan clases Tailwind.
- Dificultad para mantener la paleta a largo plazo.
- Riesgo de regresiones al actualizar colores.

#### 4.1.2 Uso excesivo de inline styles

Los componentes `DS*` mezclan Tailwind con inline styles:

```tsx
// DSButton.tsx
<button
    className={clsx('...rounded-md...', variantClasses[variant], className)}
    style={{ borderRadius: radii.md, ...variantStyles[variant] }}
>
```

Esto ocurre en:
- `DSButton`
- `DSCard`
- `DSInput`
- `DSSelect`
- `DSSkeleton`
- `DSToolbarChip`
- `DSSectionHeader`
- `DSToast`

**Impacto:**
- Renders innecesarios de objetos `style` en cada render.
- Dificultad para sobrescribir estilos desde `className`.
- No aprovecha la purga y optimización de Tailwind.

#### 4.1.3 Tokens semánticos en CSS no están en TypeScript

Las variables CSS de `globals.css` (`--success`, `--danger`, `--info`, `--warning`) no tienen análogo en `tokens.ts`. Esto fuerza a los componentes a usar strings mágicos como `hsl(var(--success))` sin autocompletado ni validación de tipos.

### 4.2 Componentes del Design System

#### 4.2.1 Falta de `forwardRef`

Componentes sin `forwardRef`:

- `DSButton`
- `DSInput`
- `DSSelect`

**Impacto:**
- No se pueden integrar con librerías como `react-hook-form` sin wrappers.
- Radix UI no puede asociar correctamente tooltips o dropdowns a estos elementos.
- Se rompen patrones de accesibilidad como devolver el foco a un trigger.

#### 4.2.2 `DSModal` sin focus trap

Aunque `DSModal` implementa `Escape` para cerrar y roles ARIA, **no existe focus trap**. Si un usuario navega con `Tab` dentro de un modal, el foco continúa por detrás del backdrop.

Además, el manejo del contador global `openModalsCount` puede desincronizarse si se abren varios modales.

#### 4.2.3 `DSTabs` sin navegación por teclado

`DSTabs` define correctamente `role="tablist"`, `aria-selected` y `aria-controls`, pero no implementa:

- Flechas izquierda/derecha para cambiar tabs.
- `Home` / `End` para ir al primer/último tab.
- Activación automática o manual según patrón ARIA.

#### 4.2.4 `DSCommandEntry` usa colores hardcodeados

```tsx
className={clsx(
    "...border-blue-500/40 bg-[hsl(var(--primary))] text-white...",
    "...border-[hsl(var(--border))]... hover:border-blue-300 hover:bg-blue-50"
)}
```

Usa `blue-500/40`, `blue-300` y `bg-blue-50` en lugar de los tokens semánticos del sistema.

### 4.3 Librería de componentes UI

#### 4.3.1 Duplicidad con el Design System

| Componente DS | Componente UI | Recomendación |
|---------------|---------------|---------------|
| `DSSkeleton` | `Skeleton` | Unificar en `DSSkeleton`; eliminar `Skeleton` o hacerlo wrapper. |
| `DSTable` | `DataTable` | Clarificar: `DataTable` podría ser el componente app-level; `DSTable` la primitiva. |
| `DSTooltip` | `Tooltip` | Unificar en `DSTooltip`; eliminar `Tooltip`. |

#### 4.3.2 Componentes UI no usan primitivas DS

Ejemplos:

- `EmptyState.tsx` define su propio botón con estilos inline en lugar de usar `DSButton`.
- `DataTable.tsx` no usa `DSTable` ni sus estilos base.
- `Skeleton.tsx` no usa `DSSkeleton`.

Esto contradice la propia guía de `CONTRIBUTING.md`, que indica que los componentes UI deben construirse sobre primitivas DS.

#### 4.3.3 Falta de documentación visual

De 39 componentes UI, solo 17 tienen stories. Componentes críticos como `PersonaSelect`, `RightPanel`, `SidePanel`, `StatusPicker` y `SplitDropdownButton` no están documentados en Storybook.

### 4.4 Accesibilidad

#### 4.4.1 Lo que cumple

- `DSInput` usa `aria-invalid`, `aria-describedby`, y asocia `<label>` con `<input>`.
- `DSModal` usa `role="dialog"` y `aria-modal="true"`.
- `DSTabs` usa estructura ARIA correcta.
- `DSTooltip` está construido sobre Radix.

#### 4.4.2 Lo que falta

- **Focus trap en `DSModal`**.
- **Navegación con teclado en `DSTabs`**.
- **`forwardRef` en inputs y botones**.
- **No hay pruebas automatizadas con `jest-axe`** en los tests actuales.
- **`EmptyState`** usa un `<button>` sin identificar tipo (`type="button"` por defecto), aunque esto es menor.

### 4.5 Storybook y testing

#### 4.5.1 Storybook

- ✅ Configuración base correcta con `@storybook/react-webpack5`.
- ✅ Addon de accesibilidad instalado.
- ️ Las historias UI son incompletas.

#### 4.5.2 Tests

- ✅ 16 tests para componentes DS.
- ️ No hay tests para componentes de `src/components/ui/`.
- ⚠️ No se verifica accesibilidad con `jest-axe`.

### 4.6 Imports y consistencia

Se detectaron importaciones inconsistentes:

```tsx
// Algunos archivos
import { DSCard } from '@/design/components/DSCard';

// Otros
import { DSCard } from '@/design';
```

Aunque ambas funcionan, la falta de convención única dificulta refactorizaciones y genera ruido en los diffs.

---

## 5. Recomendaciones priorizadas

### 🔴 Alta prioridad / Bajo esfuerzo

1. **Estandarizar imports a `@/design`**
   - Reemplazar `@/design/components/DS*` por `@/design` en todos los archivos de la aplicación.
   - Beneficio: consistencia y mantenibilidad.

2. **Agregar `forwardRef` a `DSButton`, `DSInput` y `DSSelect`**
   - Impacto directo en integración con formularios y accesibilidad.

### 🟠 Alta prioridad / Medio esfuerzo

3. **Implementar focus trap en `DSModal`**
   - Opción A: usar `@radix-ui/react-dialog`.
   - Opción B: usar librería especializada como `focus-trap-react`.
   - Restaurar foco al trigger al cerrar.

4. **Unificar fuentes de verdad de estilos**
   - Decidir si `tokens.ts` o `tailwind.config.ts` es el origen de verdad.
   - Mapear todos los tokens a Tailwind para eliminar inline styles.
   - Documentar variables CSS en `tokens.ts` o eliminarlas si son redundantes.

### 🟡 Media prioridad / Medio esfuerzo

5. **Eliminar o consolidar duplicidades**
   - `Skeleton` → delegar a `DSSkeleton`.
   - `Tooltip` → delegar a `DSTooltip`.
   - Documentar cuándo usar `DataTable` vs `DSTable`.

6. **Añadir navegación con teclado a `DSTabs`**
   - Implementar flechas direccionales.
   - Considerar usar `@radix-ui/react-tabs`.

7. **Crear tests para componentes UI críticos**
   - `DataTable`, `EmptyState`, `Skeleton`, `SidePanel`, `PersonaSelect`.

### 🟢 Baja prioridad / Alto impacto a largo plazo

8. **Completar documentación de Storybook**
   - Agregar stories para todos los componentes UI sin documentar.

9. **Auditar contraste y accesibilidad con herramientas automatizadas**
   - Integrar `jest-axe` en tests.
   - Ejecutar Storybook a11y addon regularmente.

---

## 6. Conclusiones

El Design System de CCF tiene una **base sólida y bien documentada**. La separación de capas es clara, las primitivas `DS*` son funcionales y la adopción en la aplicación es visible en dashboards y pantallas principales.

Los principales riesgos a atender son:

1. **Inconsistencia de tokens** entre `tokens.ts`, `tailwind.config.ts` y `globals.css`.
2. **Duplicidad** entre componentes DS y UI.
3. **Deuda de accesibilidad** en modal y tabs.
4. **Falta de `forwardRef`** en inputs y botones.

Atacar las recomendaciones de alta prioridad consolidará el sistema, reducirá deuda técnica y mejorará la experiencia de desarrollo y de usuario final.

---

## 7. Apéndice: fragmentos de código de referencia

### 7.1 Inline styles en DSButton

```tsx
<button
    className={clsx(
        'px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide transition-all active:scale-95 disabled:opacity-50 rounded-md',
        variantClasses[variant],
        className
    )}
    style={{ borderRadius: radii.md, ...variantStyles[variant] }}
    disabled={loading || props.disabled}
    {...props}
>
    {loading ? 'Cargando...' : children}
</button>
```

### 7.2 Variables CSS semánticas en globals.css

```css
:root {
  --success: 142 76% 36%;
  --warning: 38 92% 50%;
  --info: 197 98% 37%;
  --danger: 0 84.2% 60.2%;
}
```

### 7.3 DSModal sin focus trap

```tsx
if (!open) return null;

return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center">
        <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />
        <div ref={modalRef} ...>
            {/* Contenido */}
        </div>
    </div>
);
```

### 7.4 Duplicidad Skeleton / DSSkeleton

```tsx
// DSSkeleton.tsx
export function DSSkeleton({ rounded = 'md', className, style, ...props }: DSSkeletonProps) {
    return (
        <div
            className={clsx('relative overflow-hidden bg-[hsl(var(--surface-3))] dark:bg-white/10', className)}
            style={{ borderRadius: rounded === 'none' ? undefined : radii[rounded], ... }}
        />
    );
}

// Skeleton.tsx
export default function Skeleton({ className }: SkeletonProps) {
    return (
        <div className={clsx("relative overflow-hidden bg-[hsl(var(--surface-3))]...", className)}>
            <div className="absolute inset-0 -translate-x-full animate-[shimmer_2s_infinite]..." />
        </div>
    );
}
```

---

*Documento generado automáticamente a partir de la auditoría del design system y la librería de componentes de CCF.*
