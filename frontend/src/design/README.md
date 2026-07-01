# CCF Design System - UI Kit

Sistema de diseño y componentes UI para la plataforma CCF. Basado en la filosofía "Clean Productivity".

## Instalación

Los componentes están en `src/design/` y se importan directamente:

```tsx
import { DSButton, DSCard, DSMetric } from '@/design';
```

## Componentes Disponibles

| Componente | Descripción | Docs |
|------------|-------------|------|
| `DSButton` | Botones con variantes primary, secondary, ghost | [Story](../components/DSButton.stories.tsx) |
| `DSBadge` | Insignias de estado (slate, blue, emerald, amber) | [Story](../components/DSBadge.stories.tsx) |
| `DSCard` | Contenedores (light, dark, glass) | [Story](../components/DSCard.stories.tsx) |
| `DSChart` | Gráficos (line, area, bar) con Recharts | [Story](../components/DSChart.stories.tsx) |
| `DSCommandEntry` | Entradas de command palette | [Story](../components/DSCommandEntry.stories.tsx) |
| `DSInput` | Inputs con label, error, icon | [Story](../components/DSInput.stories.tsx) |
| `DSMetric` | KPIs para dashboards | [Story](../components/DSMetric.stories.tsx) |
| `DSModal` | Modales con backdrop | [Story](../components/DSModal.stories.tsx) |
| `DSSelect` | Selects nativos estilizados | [Story](../components/DSSelect.stories.tsx) |
| `DSSectionHeader` | Headers de sección | [Story](../components/DSSectionHeader.stories.tsx) |
| `DSSkeleton` | Skeletons de carga | [Story](../components/DSSkeleton.stories.tsx) |
| `DSTable` | Tablas con sorting (TanStack Table) | [Story](../components/DSTable.stories.tsx) |
| `DSTabs` | Navegación por tabs | [Story](../components/DSTabs.stories.tsx) |
| `DSToolbarChip` | Filtros tipo chip | [Story](../components/DSToolbarChip.stories.tsx) |
| `DSTooltip` | Tooltips con Radix | [Story](../components/DSTooltip.stories.tsx) |
| `DSToast` | Notificaciones toast | [Story](../components/DSToast.stories.tsx) |

## Tokens de Diseño

Definidos en `tokens.ts`:

- **colors**: primary, emerald, amber, blue, slate, danger
- **radii**: sm (4px), md (6px), lg (8px), xl (12px), pill (9999px)
- **shadows**: soft, card, dropdown, inner
- **typography**: Manrope, 6 tamaños (11-18px), 5 pesos
- **spacing**: xs (4px), sm (6px), md (8px), lg (12px), xl (16px)
- **motion**: 3 duraciones, 2 easing curves

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

## Storybook

Para ver todos los componentes:

```bash
npm run storybook
```

## Contribución

Ver [CONTRIBUTING.md](./CONTRIBUTING.md) para guías de contribución.

## Accesibilidad

Ver [ACCESSIBILITY.md](./ACCESSIBILITY.md) para guías de a11y.
