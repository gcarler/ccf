import React from 'react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { axe } from 'jest-axe';
import AppearanceDrawer from './AppearanceDrawer';
import { SidebarLayerProvider } from '@/context/SidebarLayerContext';
import { ThemeProvider } from '@/app/plataforma/theme/ThemeContext';

vi.mock('@/lib/http', () => ({
    apiFetch: vi.fn().mockResolvedValue({}),
}));

function renderWithProviders(ui: React.ReactElement) {
    return render(
        <SidebarLayerProvider>
            <ThemeProvider>
                {ui}
            </ThemeProvider>
        </SidebarLayerProvider>
    );
}

describe('AppearanceDrawer Component', () => {
    beforeEach(() => {
        localStorage.clear();
        document.documentElement.className = '';
        vi.clearAllMocks();
    });

    it('does not render content when closed (isOpen=false)', () => {
        renderWithProviders(
            <AppearanceDrawer isOpen={false} onClose={() => {}} />
        );

        expect(screen.queryByTestId('appearance-drawer-content')).not.toBeInTheDocument();
        expect(screen.queryByText('Personalización de Apariencia')).not.toBeInTheDocument();
    });

    it('renders header, micro-summary and PaletteSelector when open (isOpen=true)', () => {
        renderWithProviders(
            <AppearanceDrawer isOpen={true} onClose={() => {}} />
        );

        expect(screen.getByText('Personalización de Apariencia')).toBeInTheDocument();
        expect(screen.getByText(/Ambiente visual, escala de interfaz y paleta de acentos ministeriales/i)).toBeInTheDocument();
        expect(screen.getByTestId('appearance-drawer-content')).toBeInTheDocument();

        // Header summary note
        expect(screen.getByRole('note', { name: /Resumen de configuración visual activa/i })).toBeInTheDocument();
        expect(screen.getByText(/WCAG AA Conforme/i)).toBeInTheDocument();

        // Palette selector sections
        expect(screen.getByText('Ambiente Visual')).toBeInTheDocument();
        expect(screen.getByText('Densidad de Interfaz')).toBeInTheDocument();
        expect(screen.getByText('Zoom de Pantalla y Texto')).toBeInTheDocument();
        expect(screen.getByText('Acento Ministerial')).toBeInTheDocument();
        expect(screen.getByText('Previsualización en Vivo')).toBeInTheDocument();
    });

    it('supports open prop as an alias for isOpen', () => {
        renderWithProviders(
            <AppearanceDrawer open={true} onClose={() => {}} />
        );

        expect(screen.getByText('Personalización de Apariencia')).toBeInTheDocument();
    });

    it('calls onClose when close button is clicked', () => {
        const handleClose = vi.fn();
        renderWithProviders(
            <AppearanceDrawer isOpen={true} onClose={handleClose} />
        );

        const closeBtn = screen.getByLabelText('Cerrar panel');
        fireEvent.click(closeBtn);
        expect(handleClose).toHaveBeenCalledTimes(1);
    });

    it('allows changing visual options from within the drawer', () => {
        renderWithProviders(
            <AppearanceDrawer isOpen={true} onClose={() => {}} />
        );

        const nightBtn = screen.getByRole('radio', { name: /Modo Noche/i });
        act(() => {
            fireEvent.click(nightBtn);
        });

        expect(nightBtn).toHaveAttribute('aria-checked', 'true');
        expect(document.documentElement.classList.contains('dark')).toBe(true);

        const emeraldBtn = screen.getByRole('radio', { name: /Esmeralda/i });
        act(() => {
            fireEvent.click(emeraldBtn);
        });

        expect(emeraldBtn).toHaveAttribute('aria-checked', 'true');
    });

    it('passes automated accessibility audit with zero violations', async () => {
        const { container } = renderWithProviders(
            <AppearanceDrawer isOpen={true} onClose={() => {}} />
        );

        const results = await axe(container);
        expect(results.violations).toHaveLength(0);
    });
});
