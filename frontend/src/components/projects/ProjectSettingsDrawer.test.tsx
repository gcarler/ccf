import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'jest-axe';
import { describe, expect, it, vi } from 'vitest';
import { useState, type ReactNode } from 'react';
import type { ProjectRecord } from '@/types/projects';
import { SidebarLayerProvider } from '@/context/SidebarLayerContext';
import ProjectSettingsDrawer from './ProjectSettingsDrawer';

vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({ token: null }),
}));

const project: ProjectRecord = {
  id: 'project-1',
  title: 'Plan anual',
  description: 'Planificación ministerial',
  status: 'planning',
  color: '#2563eb',
  created_at: '2026-10-01T10:00:00Z',
};

function renderWithProvider(ui: ReactNode) {
  return render(<SidebarLayerProvider>{ui}</SidebarLayerProvider>);
}

describe('ProjectSettingsDrawer accessibility', () => {
  it('names the drawer and every editable control', () => {
    renderWithProvider(
      <ProjectSettingsDrawer
        project={project}
        isOpen
        onClose={vi.fn()}
        onSave={vi.fn()}
      />
    );

    expect(
      screen.getByRole('dialog', { name: 'Editar proyecto' })
    ).toHaveAttribute('aria-modal', 'true');
    expect(
      screen.getByRole('button', { name: 'Cerrar panel' })
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: 'Título del proyecto' })
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: 'Descripción del proyecto' })
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: 'Cambiar estado del proyecto' })
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: 'Selector de persona asignada' })
    ).toBeInTheDocument();
    expect(screen.getByLabelText('Color del proyecto')).toBeInTheDocument();
  });

  it('has no axe accessibility violations while open', async () => {
    const { container } = renderWithProvider(
      <ProjectSettingsDrawer
        project={project}
        isOpen
        onClose={vi.fn()}
        onSave={vi.fn()}
      />
    );
    const results = await axe(container);

    expect(results.violations).toEqual([]);
  });

  it('traps keyboard focus, closes with Escape, and restores focus to the opener', async () => {
    const offsetParentSpy = vi
      .spyOn(HTMLElement.prototype, 'offsetParent', 'get')
      .mockImplementation(function (this: HTMLElement) {
        return this.parentElement;
      });
    function Harness() {
      const [isOpen, setIsOpen] = useState(false);
      return (
        <>
          <button type="button" onClick={() => setIsOpen(true)}>
            Abrir edición
          </button>
          <ProjectSettingsDrawer
            project={project}
            isOpen={isOpen}
            onClose={() => setIsOpen(false)}
            onSave={vi.fn()}
          />
        </>
      );
    }

    try {
      renderWithProvider(<Harness />);
      const user = userEvent.setup();
      const trigger = screen.getByRole('button', { name: 'Abrir edición' });
      await user.click(trigger);
      const closeButton = screen.getByRole('button', { name: 'Cerrar panel' });
      const saveButton = screen.getByRole('button', {
        name: 'Guardar Cambios',
      });
      expect(closeButton).toHaveFocus();

      await user.keyboard('{Shift>}{Tab}{/Shift}');
      expect(saveButton).toHaveFocus();

      await user.keyboard('{Escape}');

      await waitFor(() => expect(trigger).toHaveFocus());
      await waitFor(() => {
        expect(
          screen.queryByRole('dialog', { name: 'Editar proyecto' })
        ).not.toBeInTheDocument();
      });
    } finally {
      offsetParentSpy.mockRestore();
    }
  });
});
