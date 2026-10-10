import React from 'react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { axe } from 'jest-axe';
import PaletteSelector from './PaletteSelector';
import { ThemeProvider } from './ThemeContext';

vi.mock('@/lib/http', () => ({
    apiFetch: vi.fn().mockResolvedValue({}),
}));

describe('PaletteSelector Component', () => {
    beforeEach(() => {
        localStorage.clear();
        document.documentElement.className = '';
        vi.clearAllMocks();
    });

    it('renders ambient mode options, scale options, accent options and preview', () => {
        render(
            <ThemeProvider>
                <PaletteSelector />
            </ThemeProvider>
        );

        expect(screen.getByText('Ambiente Visual')).toBeInTheDocument();
        expect(screen.getByText('Escala de Interfaz y Densidad')).toBeInTheDocument();
        expect(screen.getByText('Acento Ministerial')).toBeInTheDocument();
        expect(screen.getByText('Previsualización en Vivo')).toBeInTheDocument();

        // 2 theme modes
        expect(screen.getByText('Modo Día')).toBeInTheDocument();
        expect(screen.getByText('Modo Noche')).toBeInTheDocument();

        // 4 scales
        expect(screen.getByText('Compacto')).toBeInTheDocument();
        expect(screen.getByText('Normal')).toBeInTheDocument();
        expect(screen.getByText('Cómodo')).toBeInTheDocument();
        expect(screen.getByText('Grande')).toBeInTheDocument();

        // 6 accents
        expect(screen.getByText('Azul CCF')).toBeInTheDocument();
        expect(screen.getByText('Esmeralda')).toBeInTheDocument();
        expect(screen.getByText('Índigo')).toBeInTheDocument();
        expect(screen.getByText('Borgoña')).toBeInTheDocument();
        expect(screen.getByText('Ámbar')).toBeInTheDocument();
        expect(screen.getByText('Océano')).toBeInTheDocument();
    });

    it('allows changing visual ambient mode to Night', () => {
        render(
            <ThemeProvider>
                <PaletteSelector />
            </ThemeProvider>
        );

        const nightBtn = screen.getByRole('radio', { name: /Modo Noche/i });
        act(() => {
            fireEvent.click(nightBtn);
        });

        expect(nightBtn).toHaveAttribute('aria-checked', 'true');
        expect(document.documentElement.classList.contains('dark')).toBe(true);
    });

    it('allows selecting interface scale and updates UI accordingly', () => {
        render(
            <ThemeProvider>
                <PaletteSelector />
            </ThemeProvider>
        );

        const comfortableBtn = screen.getByRole('radio', { name: /Cómodo/i });
        act(() => {
            fireEvent.click(comfortableBtn);
        });

        expect(comfortableBtn).toHaveAttribute('aria-checked', 'true');
        expect(document.documentElement.style.getPropertyValue('--ui-scale')).toBe('1.15');
    });

    it('allows selecting ministerial accent palette and updates primary token', () => {
        render(
            <ThemeProvider>
                <PaletteSelector />
            </ThemeProvider>
        );

        const indigoBtn = screen.getByRole('radio', { name: /Índigo/i });
        act(() => {
            fireEvent.click(indigoBtn);
        });

        expect(indigoBtn).toHaveAttribute('aria-checked', 'true');
        expect(document.documentElement.getAttribute('data-accent')).toBe('indigo');
    });

    it('resets all preferences to default when clicking reset button', () => {
        render(
            <ThemeProvider>
                <PaletteSelector />
            </ThemeProvider>
        );

        // Change mode, scale, accent
        act(() => {
            fireEvent.click(screen.getByRole('radio', { name: /Modo Noche/i }));
            fireEvent.click(screen.getByRole('radio', { name: /Grande/i }));
            fireEvent.click(screen.getByRole('radio', { name: /Esmeralda/i }));
        });

        expect(document.documentElement.classList.contains('dark')).toBe(true);
        expect(document.documentElement.getAttribute('data-accent')).toBe('emerald');

        // Click reset
        const resetBtn = screen.getByRole('button', { name: /Restablecer valores predeterminados/i });
        act(() => {
            fireEvent.click(resetBtn);
        });

        expect(document.documentElement.classList.contains('dark')).toBe(false);
        expect(document.documentElement.getAttribute('data-accent')).toBe('ccf-blue');
        expect(document.documentElement.getAttribute('data-ui-scale')).toBe('normal');
    });

    it('passes automated accessibility audit with zero axe-core violations', async () => {
        const { container } = render(
            <ThemeProvider>
                <PaletteSelector />
            </ThemeProvider>
        );

        const results = await axe(container);
        expect(results).toHaveNoViolations();
    });
});
