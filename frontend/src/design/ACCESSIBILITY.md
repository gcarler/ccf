# Guía de Accesibilidad - CCF Design System

## Principios

1. **Perceivable**: La información debe ser perceptible para todos
2. **Operable**: Los componentes deben ser operables por teclado
3. **Understandable**: La información y operación deben ser comprensibles
4. **Robust**: El contenido debe ser interpretado por tecnologías asistivas

## Reglas por Componente

### DSButton
```tsx
// ✅ Correcto
<DSButton 
    onClick={handleClick}
    aria-label="Guardar cambios"
    disabled={isDisabled}
>
    Guardar
</DSButton>

// Si es icono sin texto
<DSButton aria-label="Cerrar">
    <X size={14} />
</DSButton>
```

### DSInput
```tsx
// ✅ Correcto
<DSInput 
    label="Correo electrónico"
    aria-required="true"
    aria-invalid={hasError}
    aria-describedby="email-error"
/>
<p id="email-error" role="alert">
    {errorMessage}
</p>
```

### DSModal
```tsx
// ✅ Correcto
<DSModal 
    open={isOpen}
    onClose={handleClose}
    title="Confirmar acción"
>
    {/* El modal ya tiene: */}
    {/* - role="dialog" */}
    {/* - aria-modal="true" */}
    {/* - aria-labelledby apuntando al título */}
    {/* - Focus trap */}
    {/* - Cierre con Escape */}
</DSModal>
```

### DSTabs
```tsx
// ✅ Correcto - ya implementado
<DSTabs tabs={tabs}>
    {/* Maneja automáticamente: */}
    {/* - role="tablist" */}
    {/* - role="tab" */}
    {/* - aria-selected */}
    {/* - role="tabpanel" */}
    {/* - Navegación con flechas */}
</DSTabs>
```

### DSTable
```tsx
// ✅ Correcto
<DSTable 
    data={data}
    columns={columns}
    aria-label="Lista de usuarios"
/>

// Para tablas complejas
<table aria-describedby="table-description">
    ...
</table>
<p id="table-description" className="sr-only">
    Mostrando {count} registros
</p>
```

### DSTooltip
```tsx
// ✅ Correcto
<DSTooltip content="Información adicional">
    <button aria-describedby="tooltip-info">
        Info
    </button>
</DSTooltip>
```

### DSToast
```tsx
// ✅ Correcto - ya implementado
// Los toasts tienen role="alert" y aria-live="polite"
toast.success('Operación exitosa');
```

## Colores y Contraste

### Relaciones de contraste mínimas
- Texto normal: 4.5:1
- Texto grande: 3:1
- Componentes UI: 3:1

### Tokens de color accesibles
```tsx
// ✅ Correcto - usar tokens con contraste verificado
text-[hsl(var(--text-primary))]      // Alto contraste
text-[hsl(var(--text-secondary))]    // Contraste medio

// ❌ Incorrecto - bajo contraste
text-gray-400  // No cumple 4.5:1
```

## Navegación por Teclado

### Tab Order
- Todos los elementos interactivos deben ser tabbles
- Orden lógico (arriba-abajo, izquierda-derecha)
- Focus visible siempre

### Atajos de Teclado
```tsx
// Ejemplo: Modal
useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
        if (e.key === 'Escape') onClose();
    };
    
    if (open) {
        document.addEventListener('keydown', handleEscape);
        // Focus trap
    }
    
    return () => document.removeEventListener('keydown', handleEscape);
}, [open, onClose]);
```

### Focus Management
```tsx
// Al abrir modal, enfocar primer elemento
useEffect(() => {
    if (open) {
        firstButtonRef.current?.focus();
    }
}, [open]);

// Al cerrar, restaurar focus
const handleClose = () => {
    onClose();
    triggerRef.current?.focus();
};
```

## Screen Readers

### ARIA Labels
```tsx
// Botones con solo icono
<button aria-label="Eliminar">
    <Trash size={14} />
</button>

// Campos con label visible
<input aria-label="Buscar" />

// Campos con label oculto
<label className="sr-only">Email</label>
<input />
```

### Live Regions
```tsx
// Para actualizaciones dinámicas
<div aria-live="polite" aria-atomic="true">
    {notification}
</div>

// Para errores
<p role="alert">{errorMessage}</p>
```

### Roles ARIA
```tsx
// Tablas
<table role="grid">

// Listas
<ul role="listbox">

// Menús
<div role="menu">

// Diálogos
<div role="dialog" aria-modal="true">
```

## Testing de Accesibilidad

### Con Storybook
El addon `@storybook/addon-a11y` ya está instalado.

```bash
npm run storybook
```

En Storybook, ir a la pestaña "Accessibility" para ver violations.

### Con Jest
```bash
npm install --save-dev jest-axe @testing-library/jest-dom
```

```tsx
import { render } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';

expect.extend(toHaveNoViolations);

it('should have no accessibility violations', async () => {
    const { container } = render(<MyComponent />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
});
```

### Checklist Manual
- [ ] Navegación completa con Tab
- [ ] Focus visible en todos los elementos
- [ ] Escape cierra modales/dropdowns
- [ ] Labels asociados a inputs
- [ ] Contrast ratio ≥ 4.5:1 para texto
- [ ] Imágenes tienen alt text
- [ ] Iconos tienen aria-label

## Recursos

- [WCAG 2.1](https://www.w3.org/TR/WCAG21/)
- [ARIA Authoring Practices](https://www.w3.org/WAI/ARIA/apd/)
- [Radix UI Accessibility](https://www.radix-ui.com/primitives/docs/overview/accessibility)
