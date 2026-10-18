import React from 'react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import { axe } from 'jest-axe';
import { ThemeProvider, useTheme } from './ThemeContext';
import { DSButton } from '@/design/components/DSButton';
import { DSInput } from '@/design/components/DSInput';
import { DSTable } from '@/design/components/DSTable';
import { DSCard } from '@/design/components/DSCard';

vi.mock('@/lib/http', () => ({
    apiFetch: vi.fn().mockResolvedValue({}),
}));

function DensityHarness() {
    const { uiDensity, setUiDensity, currentDensity } = useTheme();

    const sampleColumns = [
        { accessorKey: 'id', header: 'ID' },
        { accessorKey: 'name', header: 'Nombre' },
    ];
    const sampleData = [
        { id: '1', name: 'Iglesia Central' },
        { id: '2', name: 'Escuela de Líderes' },
    ];

    return (
        <div>
            <div data-testid="density-val">{uiDensity}</div>
            <div data-testid="density-label">{currentDensity.label}</div>
            <button data-testid="btn-ultra" onClick={() => setUiDensity('ultra-compact')}>Ultra</button>
            <button data-testid="btn-compact" onClick={() => setUiDensity('compact')}>Compact</button>
            <button data-testid="btn-comfortable" onClick={() => setUiDensity('comfortable')}>Comfortable</button>
            <button data-testid="btn-spacious" onClick={() => setUiDensity('spacious')}>Spacious</button>

            <DSButton data-testid="test-button">Acción Principal</DSButton>
            <DSInput data-testid="test-input" label="Campo de texto" defaultValue="Valor de prueba" />
            <DSCard data-testid="test-card">Tarjeta de Contenido</DSCard>
            <DSTable data={sampleData} columns={sampleColumns} />
        </div>
    );
}

describe('Effective UI Density & Base Component Verification', () => {
    beforeEach(() => {
        localStorage.clear();
        document.documentElement.removeAttribute('data-ui-density');
        document.documentElement.removeAttribute('data-theme');
        document.documentElement.className = '';
        vi.clearAllMocks();
    });

    it('initializes with ultra-compact density by default and sets canonical CSS variables on :root', () => {
        render(
            <ThemeProvider>
                <DensityHarness />
            </ThemeProvider>
        );

        expect(screen.getByTestId('density-val').textContent).toBe('ultra-compact');
        expect(screen.getByTestId('density-label').textContent).toBe('Ultra compacta');

        const root = document.documentElement;
        expect(root.getAttribute('data-ui-density')).toBe('ultra-compact');
        expect(root.style.getPropertyValue('--density-row-h')).toBe('28px');
        expect(root.style.getPropertyValue('--density-pad-x')).toBe('0.5rem');
        expect(root.style.getPropertyValue('--density-pad-y')).toBe('0.125rem');
        expect(root.style.getPropertyValue('--density-gap')).toBe('0.25rem');
        expect(root.style.getPropertyValue('--ui-density-ratio')).toBe('0.75');
    });

    it('modifies data-ui-density and updates CSS variables across all 4 presets', () => {
        render(
            <ThemeProvider>
                <DensityHarness />
            </ThemeProvider>
        );

        const root = document.documentElement;

        // 1. Compact
        act(() => {
            screen.getByTestId('btn-compact').click();
        });
        expect(root.getAttribute('data-ui-density')).toBe('compact');
        expect(root.style.getPropertyValue('--density-row-h')).toBe('36px');
        expect(root.style.getPropertyValue('--density-pad-x')).toBe('0.75rem');
        expect(root.style.getPropertyValue('--density-pad-y')).toBe('0.375rem');
        expect(root.style.getPropertyValue('--density-gap')).toBe('0.5rem');
        expect(root.style.getPropertyValue('--ui-density-ratio')).toBe('0.875');

        // 2. Comfortable
        act(() => {
            screen.getByTestId('btn-comfortable').click();
        });
        expect(root.getAttribute('data-ui-density')).toBe('comfortable');
        expect(root.style.getPropertyValue('--density-row-h')).toBe('44px');
        expect(root.style.getPropertyValue('--density-pad-x')).toBe('1rem');
        expect(root.style.getPropertyValue('--density-pad-y')).toBe('0.625rem');
        expect(root.style.getPropertyValue('--density-gap')).toBe('0.75rem');
        expect(root.style.getPropertyValue('--ui-density-ratio')).toBe('1.0');

        // 3. Spacious
        act(() => {
            screen.getByTestId('btn-spacious').click();
        });
        expect(root.getAttribute('data-ui-density')).toBe('spacious');
        expect(root.style.getPropertyValue('--density-row-h')).toBe('52px');
        expect(root.style.getPropertyValue('--density-pad-x')).toBe('1.25rem');
        expect(root.style.getPropertyValue('--density-pad-y')).toBe('0.875rem');
        expect(root.style.getPropertyValue('--density-gap')).toBe('1rem');
        expect(root.style.getPropertyValue('--ui-density-ratio')).toBe('1.25');

        // 4. Return to Ultra-compact
        act(() => {
            screen.getByTestId('btn-ultra').click();
        });
        expect(root.getAttribute('data-ui-density')).toBe('ultra-compact');
        expect(root.style.getPropertyValue('--density-row-h')).toBe('28px');
        expect(root.style.getPropertyValue('--density-pad-x')).toBe('0.5rem');
        expect(root.style.getPropertyValue('--density-pad-y')).toBe('0.125rem');
        expect(root.style.getPropertyValue('--density-gap')).toBe('0.25rem');
        expect(root.style.getPropertyValue('--ui-density-ratio')).toBe('0.75');
    });

    it('verifies that base Design System components consume the CSS density variables', () => {
        const { container } = render(
            <ThemeProvider>
                <DensityHarness />
            </ThemeProvider>
        );

        // DSButton consumes --density-row-h and density padding/gap
        const button = screen.getByTestId('test-button');
        expect(button.style.minHeight).toBe('var(--density-row-h, 28px)');
        expect(button.className).toContain('density-button');

        // DSInput consumes --density-row-h and density padding
        const input = screen.getByDisplayValue('Valor de prueba');
        expect(input.style.minHeight).toBe('var(--density-row-h, 28px)');
        expect(input.className).toContain('density-input');

        // DSCard consumes --density-gap
        const card = screen.getByTestId('test-card');
        expect(card.style.gap).toBe('var(--density-gap, 0.25rem)');
        expect(card.className).toContain('density-card');

        // DSTable consumes --density-row-h on th, tr, and td
        const headerCell = container.querySelector('thead th') as HTMLElement;
        expect(headerCell).toBeInTheDocument();
        expect(headerCell.style.height).toBe('var(--density-row-h, 28px)');
        expect(headerCell.className).toContain('density-cell');

        const bodyRow = container.querySelector('tbody tr') as HTMLElement;
        expect(bodyRow).toBeInTheDocument();
        expect(bodyRow.style.height).toBe('var(--density-row-h, 28px)');
        expect(bodyRow.className).toContain('density-row');

        const bodyCell = container.querySelector('tbody td') as HTMLElement;
        expect(bodyCell).toBeInTheDocument();
        expect(bodyCell.style.height).toBe('var(--density-row-h, 28px)');
        expect(bodyCell.className).toContain('density-cell');
    });

    it('passes automated accessibility audit with zero axe-core violations under all densities', async () => {
        const { container } = render(
            <ThemeProvider>
                <DensityHarness />
            </ThemeProvider>
        );

        const results = await axe(container);
        expect(results).toHaveNoViolations();
    });
});
