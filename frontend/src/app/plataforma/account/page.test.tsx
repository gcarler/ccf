import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { axe } from 'jest-axe';
import { filterMotionProps } from '@/test-utils/filter-motion-props';
import AccountSettingsPage from './page';
import { ThemeProvider } from '@/app/plataforma/theme/ThemeContext';
import { SidebarLayerProvider } from '@/context/SidebarLayerContext';

vi.mock('framer-motion', () => ({
    motion: {
        div: React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(function MockMotionDiv({ children, ...props }, ref) {
            return <div ref={ref} {...filterMotionProps(props as Record<string, unknown>)}>{children}</div>;
        }),
    },
    AnimatePresence: ({ children }: { children?: React.ReactNode }) => <>{children}</>,
}));

vi.mock('@/components/WorkspaceLayout', () => ({
    default: ({ children }: { children: React.ReactNode }) => (
        <div data-testid="mock-workspace-layout">{children}</div>
    ),
}));

vi.mock('@/context/AuthContext', () => ({
    useAuth: () => ({
        user: {
            id: 'user-pastor-1',
            username: 'pastor.carlos',
            email: 'pastor.carlos@ccf.org',
            name: 'Pastor Carlos Gómez',
        },
        logout: vi.fn(),
        refresh: vi.fn(),
    }),
}));

vi.mock('@/context/ToastContext', () => ({
    useToast: () => ({
        addToast: vi.fn(),
    }),
}));

vi.mock('@/components/admin/TwoFactorDrawer', () => ({
    default: () => <div data-testid="mock-2fa-drawer" />,
}));

vi.mock('@/components/messaging/PushNotificationManager', () => ({
    default: () => <div data-testid="mock-push-manager" />,
}));

vi.mock('@/lib/http', () => ({
    apiFetch: vi.fn().mockImplementation((url: string) => {
        if (url.includes('/crm/personas/me/profile')) {
            return Promise.resolve({
                first_name: 'Carlos',
                last_name: 'Gómez',
                phone: '+57 300 1234567',
                bio_short: 'Pastor principal de Comunidad Cristiana de Fe',
            });
        }
        if (url.includes('/v3/auth/2fa/status')) {
            return Promise.resolve({ is_mfa_enabled: false });
        }
        return Promise.resolve({});
    }),
}));

function renderPage() {
    return render(
        <SidebarLayerProvider>
            <ThemeProvider>
                <AccountSettingsPage />
            </ThemeProvider>
        </SidebarLayerProvider>
    );
}

describe('AccountSettingsPage — Appearance & Accessibility Tab', () => {
    beforeEach(() => {
        localStorage.clear();
        document.documentElement.className = '';
        vi.clearAllMocks();
    });

    it('navigates to "Apariencia" tab and renders PaletteSelector and dynamic summary', async () => {
        renderPage();

        // Switch to Apariencia tab
        const appearanceTab = screen.getByTestId('tab-appearance');
        fireEvent.click(appearanceTab);

        // Dynamic summary
        expect(screen.getByText('Personalización de Apariencia')).toBeInTheDocument();
        expect(screen.getByText(/Ambiente visual:/i)).toBeInTheDocument();
        expect(screen.getByText(/Escala:/i)).toBeInTheDocument();
        expect(screen.getByText(/Acento:/i)).toBeInTheDocument();

        // PaletteSelector sections
        expect(screen.getByText('Ambiente Visual')).toBeInTheDocument();
        expect(screen.getByText('Densidad de Interfaz')).toBeInTheDocument();
        expect(screen.getByText('Zoom de Pantalla y Texto')).toBeInTheDocument();
        expect(screen.getByText('Acento Ministerial')).toBeInTheDocument();
        expect(screen.getByText('Previsualización en Vivo')).toBeInTheDocument();
    });

    it('opens AppearanceDrawer when clicking "Abrir en panel lateral"', async () => {
        renderPage();

        const appearanceTab = screen.getByTestId('tab-appearance');
        fireEvent.click(appearanceTab);

        const openDrawerBtn = screen.getByRole('button', { name: /Abrir en panel lateral/i });
        fireEvent.click(openDrawerBtn);

        // Check AppearanceDrawer presence
        expect(screen.getByText(/Ambiente visual, escala de interfaz y paleta de acentos ministeriales/i)).toBeInTheDocument();
        expect(screen.getByRole('note', { name: /Resumen de configuración visual activa/i })).toBeInTheDocument();
    });

    it('allows changing visual modes and scales from within the account page', async () => {
        renderPage();

        const appearanceTab = screen.getByTestId('tab-appearance');
        fireEvent.click(appearanceTab);

        // Switch to Night mode
        const nightModeRadio = screen.getAllByRole('radio', { name: /Modo Noche/i })[0];
        act(() => {
            fireEvent.click(nightModeRadio);
        });

        expect(document.documentElement.classList.contains('dark')).toBe(true);

        // Switch density to Compacta
        const compactRadio = screen.getAllByRole('radio', { name: /Densidad Compacta/i })[0];
        act(() => {
            fireEvent.click(compactRadio);
        });

        expect(document.documentElement.getAttribute('data-ui-density')).toBe('compact');
        expect(document.documentElement.style.getPropertyValue('--density-row-h')).toBe('36px');
    });

    it('passes automated accessibility audit with 0 violations', async () => {
        const { container } = renderPage();

        const appearanceTab = screen.getByTestId('tab-appearance');
        fireEvent.click(appearanceTab);

        const results = await axe(container);
        expect(results.violations).toHaveLength(0);
    });
});
