/* eslint-disable @typescript-eslint/no-explicit-any */
import React from 'react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { axe } from 'jest-axe';
import DensityZoomSelector from './DensityZoomSelector';
import { ThemeProvider } from './ThemeContext';

vi.mock('@/lib/http', () => ({
    apiFetch: vi.fn().mockResolvedValue({}),
}));

describe('DensityZoomSelector Component', () => {
    beforeEach(() => {
        localStorage.clear();
        document.documentElement.className = '';
        document.documentElement.removeAttribute('data-ui-density');
        document.documentElement.style.fontSize = '';
        document.documentElement.style.removeProperty('--ui-scale');
        document.documentElement.style.removeProperty('--ui-density-ratio');
        vi.clearAllMocks();
    });

    it('renders all 4 density options with accessible roles and labels', () => {
        render(
            <ThemeProvider>
                <DensityZoomSelector />
            </ThemeProvider>
        );

        expect(screen.getByText('Densidad de Interfaz')).toBeInTheDocument();
        expect(screen.getByRole('radio', { name: /^Densidad Ultra compacta:/i })).toBeInTheDocument();
        expect(screen.getByRole('radio', { name: /^Densidad Compacta:/i })).toBeInTheDocument();
        expect(screen.getByRole('radio', { name: /^Densidad Cómoda:/i })).toBeInTheDocument();
        expect(screen.getByRole('radio', { name: /^Densidad Espaciosa:/i })).toBeInTheDocument();
    });

    it('allows selecting different interface density levels and reflects in DOM and state', () => {
        render(
            <ThemeProvider>
                <DensityZoomSelector />
            </ThemeProvider>
        );

        const ultraCompactBtn = screen.getByRole('radio', { name: /^Densidad Ultra compacta:/i });
        act(() => {
            fireEvent.click(ultraCompactBtn);
        });

        expect(ultraCompactBtn).toHaveAttribute('aria-checked', 'true');
        expect(document.documentElement.getAttribute('data-ui-density')).toBe('ultra-compact');
        expect(document.documentElement.style.getPropertyValue('--ui-density-ratio')).toBe('0.75');

        const spaciousBtn = screen.getByRole('radio', { name: /^Densidad Espaciosa:/i });
        act(() => {
            fireEvent.click(spaciousBtn);
        });

        expect(spaciousBtn).toHaveAttribute('aria-checked', 'true');
        expect(document.documentElement.getAttribute('data-ui-density')).toBe('spacious');
        expect(document.documentElement.style.getPropertyValue('--ui-density-ratio')).toBe('1.25');
    });

    it('renders manual zoom controls including slider, presets and +/- buttons', () => {
        render(
            <ThemeProvider>
                <DensityZoomSelector />
            </ThemeProvider>
        );

        expect(screen.getByText('Zoom de Pantalla y Texto')).toBeInTheDocument();
        expect(screen.getByTestId('zoom-percentage-badge')).toHaveTextContent('100%');
        expect(screen.getByRole('button', { name: /Disminuir zoom/i })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Aumentar zoom/i })).toBeInTheDocument();
        expect(screen.getByRole('slider', { name: /Ajuste de zoom continuo/i })).toBeInTheDocument();

        // Check presets exist
        expect(screen.getByRole('button', { name: /Establecer zoom a 90%/i })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Establecer zoom a 100%/i })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Establecer zoom a 115%/i })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Establecer zoom a 133%/i })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Establecer zoom a 200%/i })).toBeInTheDocument();
    });

    it('updates zoom percentage via quick presets and reflects in style properties', () => {
        render(
            <ThemeProvider>
                <DensityZoomSelector />
            </ThemeProvider>
        );

        const preset125 = screen.getByRole('button', { name: /Establecer zoom a 125%/i });
        act(() => {
            fireEvent.click(preset125);
        });

        expect(screen.getByTestId('zoom-percentage-badge')).toHaveTextContent('125%');
        expect(document.documentElement.style.fontSize).toBe('125%');
        expect(document.documentElement.style.getPropertyValue('--ui-scale')).toBe('1.25');

        const preset200 = screen.getByRole('button', { name: /Establecer zoom a 200%/i });
        act(() => {
            fireEvent.click(preset200);
        });

        expect(screen.getByTestId('zoom-percentage-badge')).toHaveTextContent('200%');
        expect(document.documentElement.style.fontSize).toBe('200%');
        expect(document.documentElement.style.getPropertyValue('--ui-scale')).toBe('2');
    });

    it('updates zoom percentage via increment (+) and decrement (-) buttons', () => {
        render(
            <ThemeProvider>
                <DensityZoomSelector />
            </ThemeProvider>
        );

        const zoomInBtn = screen.getByRole('button', { name: /Aumentar zoom/i });
        act(() => {
            fireEvent.click(zoomInBtn);
        });

        // 100 -> next preset 110
        expect(screen.getByTestId('zoom-percentage-badge')).toHaveTextContent('110%');
        expect(document.documentElement.style.fontSize).toBe('110%');

        const zoomOutBtn = screen.getByRole('button', { name: /Disminuir zoom/i });
        act(() => {
            fireEvent.click(zoomOutBtn);
        });

        // 110 -> prev preset 100
        expect(screen.getByTestId('zoom-percentage-badge')).toHaveTextContent('100%');
        expect(document.documentElement.style.fontSize).toBe('100%');
    });

    it('updates zoom percentage via continuous slider', () => {
        render(
            <ThemeProvider>
                <DensityZoomSelector />
            </ThemeProvider>
        );

        const slider = screen.getByRole('slider', { name: /Ajuste de zoom continuo/i });
        act(() => {
            fireEvent.change(slider, { target: { value: '118' } });
        });

        expect(screen.getByTestId('zoom-percentage-badge')).toHaveTextContent('118%');
        expect(document.documentElement.style.fontSize).toBe('118%');
        expect(document.documentElement.style.getPropertyValue('--ui-scale')).toBe('1.18');
    });

    it('allows resetting zoom to 100% with reset button', () => {
        render(
            <ThemeProvider>
                <DensityZoomSelector />
            </ThemeProvider>
        );

        const preset130 = screen.getByRole('button', { name: /Establecer zoom a 130%/i });
        act(() => {
            fireEvent.click(preset130);
        });

        expect(screen.getByTestId('zoom-percentage-badge')).toHaveTextContent('130%');

        const resetBtn = screen.getByRole('button', { name: /Restablecer zoom a 100%/i });
        act(() => {
            fireEvent.click(resetBtn);
        });

        expect(screen.getByTestId('zoom-percentage-badge')).toHaveTextContent('100%');
        expect(document.documentElement.style.fontSize).toBe('100%');
    });

    it('passes automated accessibility audit with zero axe-core violations', async () => {
        const { container } = render(
            <ThemeProvider>
                <DensityZoomSelector />
            </ThemeProvider>
        );

        const results = await axe(container);
        expect(results.violations).toHaveLength(0);
    });
});
