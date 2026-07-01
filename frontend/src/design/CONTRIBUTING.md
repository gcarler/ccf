# Guía de Contribución - CCF Design System

## Estructura de Archivos

```
src/design/
├── index.ts              # Exports públicos
├── tokens.ts             # Tokens de diseño
├── README.md             # Documentación principal
├── CONTRIBUTING.md       # Esta guía
├── ACCESSIBILITY.md      # Guías de a11y
└── components/
    ├── DS[Componente].tsx
    ├── DS[Componente].stories.tsx
    └── DS[Componente].test.tsx  (opcional)
```

## Convenciones de Nomenclatura

### Archivos
- **Componentes**: `DSNombreComponente.tsx` (PascalCase con prefijo DS)
- **Stories**: `DSNombreComponente.stories.tsx`
- **Tests**: `DSNombreComponente.test.tsx`

### Componentes
```tsx
// interfaces.ts o inline
interface DSNombreComponenteProps {
    // Props requeridas primero
    label: string;
    value: string;
    
    // Props opcionales
    variant?: 'primary' | 'secondary';
    disabled?: boolean;
    
    // Eventos
    onChange?: (value: string) => void;
    
    // Extienden de HTML si es necesario
} extends React.HTMLAttributes<HTMLDivElement> {
```

### Exportación
```tsx
export function DSNombreComponente({ 
    label, 
    variant = 'primary', 
    className,
    ...props 
}: DSNombreComponenteProps) {
    return (
        <div className={clsx('base-classes', className)} {...props}>
            {label}
        </div>
    );
}
```

## Crear un Nuevo Componente

### 1. Crear el componente

```tsx
// src/design/components/DSNuevo.tsx
"use client";

import React from 'react';
import clsx from 'clsx';
import { radii, typography } from '../tokens';

interface DSNuevoProps {
    label: string;
    variant?: 'default' | 'alternative';
}

export function DSNuevo({ 
    label, 
    variant = 'default', 
    className,
    ...props 
}: DSNuevoProps) {
    return (
        <div 
            className={clsx('base-classes', className)}
            style={{ fontFamily: typography.family }}
            {...props}
        >
            {label}
        </div>
    );
}
```

### 2. Crear el story

```tsx
// src/design/components/DSNuevo.stories.tsx
import type { Meta, StoryObj } from '@storybook/react-webpack5';
import { DSNuevo } from './DSNuevo';

const meta: Meta<typeof DSNuevo> = {
    title: 'Design/Nuevo',
    component: DSNuevo,
    args: {
        label: 'Ejemplo',
    },
    parameters: { layout: 'centered' },
};

export default meta;
type Story = StoryObj<typeof DSNuevo>;

export const Default: Story = {};
export const Alternative: Story = { args: { variant: 'alternative' } };
```

### 3. Agregar exports

```tsx
// src/design/index.ts
export * from './components/DSNuevo';
```

### 4. Crear test (opcional pero recomendado)

```tsx
// src/design/components/DSNuevo.test.tsx
import { render, screen } from '@testing-library/react';
import { DSNuevo } from './DSNuevo';

describe('DSNuevo', () => {
    it('renders with label', () => {
        render(<DSNuevo label="Test" />);
        expect(screen.getByText('Test')).toBeInTheDocument();
    });
});
```

## Reglas de Estilo

### Usar Tokens
```tsx
// ✅ Correcto
import { radii, colors, typography } from '../tokens';

<div style={{ borderRadius: radii.md }} />
<div style={{ backgroundColor: colors.primary[600] }} />

// ❌ Incorrecto
<div style={{ borderRadius: '6px' }} />
<div style={{ backgroundColor: '#004581' }} />
```

### Clases CSS
```tsx
// ✅ Correcto - usar clsx para condicionales
import clsx from 'clsx';

<div className={clsx(
    'base-classes',
    isActive && 'active-classes',
    disabled && 'disabled-classes',
    className  // siempre al final para override
)} />

// ❌ Incorrecto
<div className={`base-classes ${isActive ? 'active' : ''}`} />
```

### Tailwind
- Usar clases de Tailwind existentes
- No agregar estilos inline a menos que sea con tokens
- Colores: usar `hsl(var(--primary))` en lugar de `blue-500`

## Accesibilidad

- Agregar `aria-label` o `aria-labelledby` a elementos interactivos
- Usar `role` cuando sea necesario
- Soportar navegación por teclado
- Probar con screen readers

Ver [ACCESSIBILITY.md](./ACCESSIBILITY.md) para más detalles.

## Testing

### Ejecutar tests
```bash
npm run test
```

### Tipos de test
1. **Unit**: Render, props, eventos
2. **Integration**: Comportamiento con otros componentes
3. **Visual**: Stories de Storybook

### Cobertura mínima
- Todos los componentes DS deben tener tests unitarios
- Tests de accesibilidad con jest-axe

## Pull Request

1. Crear branch `feature/ds-nombre-componente`
2. Implementar componente + stories + tests
3. Actualizar README.md si es necesario
4. Ejecutar `npm run lint` y `npm run typecheck`
5. Crear PR con descripción clara
