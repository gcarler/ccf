/* eslint-disable @typescript-eslint/no-explicit-any */
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { axe } from 'jest-axe';
import { filterMotionProps } from '@/test-utils/filter-motion-props';
import UniversalCreationDrawer from './UniversalCreationDrawer';

vi.mock('framer-motion', () => ({
    motion: {
        div: ({ children, ...props }: any) => <div {...filterMotionProps(props)}>{children}</div>,
        aside: ({ children, ...props }: any) => <aside {...filterMotionProps(props)}>{children}</aside>,
        p: ({ children, ...props }: any) => <p {...filterMotionProps(props)}>{children}</p>,
    },
    AnimatePresence: ({ children }: any) => <>{children}</>,
}));

vi.mock('@/context/AuthContext', () => ({
    useAuth: () => ({ token: 'test-token', user: { id: '1', username: 'test' } }),
}));

vi.mock('@/context/CreationContext', () => ({
    useCreation: () => ({ initialData: null }),
}));

vi.mock('./RightPanel', () => ({
    RightPanel: ({ children, title, onClose, open }: any) => (
        open ? (
            <div data-testid="right-panel">
                <div data-testid="right-panel-title">{title}</div>
                <button aria-label="Cerrar" onClick={onClose}>×</button>
                {children}
            </div>
        ) : null
    ),
}));

vi.mock('@/lib/http', () => ({
    apiFetch: vi.fn().mockResolvedValue([]),
}));

vi.mock('sonner', () => ({
    toast: { error: vi.fn(), info: vi.fn(), success: vi.fn() },
}));

vi.mock('@/lib/cms/v2', () => ({
    createCmsPage: vi.fn().mockResolvedValue({}),
}));

describe('UniversalCreationDrawer', () => {
    it('does not render when closed', () => {
        const { container } = render(
            <UniversalCreationDrawer isOpen={false} onClose={vi.fn()} initialType="task" />
        );
        expect(container.querySelector('[data-testid="right-panel"]')).not.toBeInTheDocument();
    });

    it('renders the drawer with task creation form when open', () => {
        render(<UniversalCreationDrawer isOpen onClose={vi.fn()} initialType="task" />);
        expect(screen.getByTestId('right-panel')).toBeInTheDocument();
        expect(screen.getByText('Crear nuevo')).toBeInTheDocument();
        expect(screen.getByPlaceholderText(/Escribe el nombre de Tarea/i)).toBeInTheDocument();
    });

    it('switches to event form when the event tab is clicked', () => {
        render(<UniversalCreationDrawer isOpen onClose={vi.fn()} initialType="task" />);
        fireEvent.click(screen.getByText('Evento'));
        expect(screen.getByPlaceholderText(/Añade un título a la reunión/i)).toBeInTheDocument();
    });

    it('switches to project form when the project tab is clicked', () => {
        render(<UniversalCreationDrawer isOpen onClose={vi.fn()} initialType="task" />);
        fireEvent.click(screen.getByText('Proyecto'));
        expect(screen.getByPlaceholderText(/Nombre del proyecto/i)).toBeInTheDocument();
    });

    it('calls onClose when the drawer close button is clicked', () => {
        const onClose = vi.fn();
        render(<UniversalCreationDrawer isOpen onClose={onClose} initialType="task" />);
        fireEvent.click(screen.getByLabelText('Cerrar drawer'));
        expect(onClose).toHaveBeenCalledTimes(1);
    });

    it('has no accessibility violations when open', async () => {
        const { container } = render(<UniversalCreationDrawer isOpen onClose={vi.fn()} initialType="task" />);
        const results = await axe(container);
        expect(results.violations).toHaveLength(0);
    });

    it.each([
        'task',
        'event',
        'project',
        'doc',
        'reminder',
        'whiteboard',
        'panel',
    ] as const)('has no accessibility violations on the %s tab', async (tabType) => {
        const { container } = render(<UniversalCreationDrawer isOpen onClose={vi.fn()} initialType={tabType} />);
        const results = await axe(container);
        expect(results.violations).toHaveLength(0);
    });
});
