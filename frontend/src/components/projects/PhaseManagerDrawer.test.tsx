import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { axe } from 'jest-axe';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { ReactNode } from 'react';

const mocks = vi.hoisted(() => ({
  tasks: [] as Array<{ id: string; title: string; status: string }>,
  addToast: vi.fn(),
}));

vi.mock('@/components/ui/RightPanel', () => ({
  RightPanel: ({ children }: { children: ReactNode }) => <div>{children}</div>,
}));
vi.mock('@/context/AuthContext', () => ({ useAuth: () => ({ token: 'token', loading: false }) }));
vi.mock('@/context/ToastContext', () => ({ useToast: () => ({ addToast: mocks.addToast }) }));
vi.mock('@/lib/http', () => ({ apiFetch: vi.fn() }));
vi.mock('@/context/ProjectUpdateContext', () => ({
  useProjectUpdate: () => ({
    phases: [
      { slug: 'planning', name: 'Planificación', color: 'hsl(var(--primary))', order_index: 0 },
      { slug: 'active', name: 'En marcha', color: 'hsl(var(--success))', order_index: 1 },
    ],
    tasks: mocks.tasks,
    reloadProject: vi.fn(),
  }),
}));

import { PhaseManagerDrawer } from './PhaseManagerDrawer';

describe('PhaseManagerDrawer accessibility', () => {
  beforeEach(() => {
    mocks.tasks = [];
    mocks.addToast.mockClear();
  });

  it('names reorder and delete actions and keeps deletion reachable on touch and focus', async () => {
    const { container } = render(<PhaseManagerDrawer projectId="project-1" onClose={vi.fn()} />);

    expect(screen.getByRole('button', { name: 'Mover fase Planificación arriba' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Mover fase Planificación abajo' })).toBeEnabled();
    const deleteButton = screen.getByRole('button', { name: 'Eliminar fase Planificación' });
    expect(deleteButton).toHaveClass('opacity-100', 'md:group-focus-within:opacity-100');
    expect((await axe(container)).violations).toEqual([]);
  });

  it('confirms removing an empty phase from the draft and keeps it unchanged on cancel', async () => {
    render(<PhaseManagerDrawer projectId="project-1" onClose={vi.fn()} />);

    fireEvent.click(screen.getByRole('button', { name: 'Eliminar fase Planificación' }));
    const confirmDrawer = await screen.findByRole('complementary', { name: 'Eliminar fase del borrador' });
    expect(confirmDrawer).toBeInTheDocument();
    expect(screen.getByRole('textbox', { name: 'Nombre de fase Planificación' })).toBeInTheDocument();

    fireEvent.click(within(confirmDrawer).getByRole('button', { name: 'Cancelar' }));
    await waitFor(() => expect(screen.queryByRole('complementary', { name: 'Eliminar fase del borrador' })).not.toBeInTheDocument());
    expect(screen.getByRole('textbox', { name: 'Nombre de fase Planificación' })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Eliminar fase Planificación' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Eliminar fase' }));
    expect(screen.queryByRole('textbox', { name: 'Nombre de fase Planificación' })).not.toBeInTheDocument();
    expect(screen.getByRole('textbox', { name: 'Nombre de fase En marcha' })).toBeInTheDocument();
  });

  it('blocks removing a phase that still owns tasks and explains how to proceed', () => {
    mocks.tasks = [{ id: 'task-1', title: 'Preparar reunión', status: 'planning' }];
    render(<PhaseManagerDrawer projectId="project-1" onClose={vi.fn()} />);

    fireEvent.click(screen.getByRole('button', { name: 'Eliminar fase Planificación' }));

    expect(mocks.addToast).toHaveBeenCalledWith('Mueve la tarea de esta fase antes de eliminarla.', 'error');
    expect(screen.getByRole('textbox', { name: 'Nombre de fase Planificación' })).toBeInTheDocument();
    expect(screen.queryByRole('complementary', { name: 'Eliminar fase del borrador' })).not.toBeInTheDocument();
  });
});
