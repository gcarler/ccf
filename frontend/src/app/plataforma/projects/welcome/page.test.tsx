import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const { apiFetchMock, pushMock, toastErrorMock } = vi.hoisted(() => ({
  apiFetchMock: vi.fn(),
  pushMock: vi.fn(),
  toastErrorMock: vi.fn(),
}));

vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({ token: 'test-token', loading: false }),
}));

vi.mock('@/lib/http', () => ({ apiFetch: apiFetchMock }));

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: pushMock }),
}));

vi.mock('@/components/projects/ProjectsShell', () => ({
  default: ({ children }: { children: ReactNode }) => <div>{children}</div>,
}));

vi.mock('sonner', () => ({ toast: { error: toastErrorMock } }));

import ProjectsWelcomePage from './page';

describe('ProjectsWelcomePage PMI §4.1 initiation onboarding', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders PMI §4.1 lifecycle banner, pre-fills drawer from Charter template, and submits POST /projects', async () => {
    apiFetchMock.mockResolvedValueOnce({ id: 'project-pmi-1', title: 'Iniciativa Ministerial — Línea Base PMI' });

    render(<ProjectsWelcomePage />);

    const banner = screen.getByTestId('projects-welcome-pmi-banner');
    expect(banner).toHaveTextContent('1. Acta de Constitución (Project Charter §4.1)');
    expect(banner).toHaveTextContent('2. Estructura de Desglose del Trabajo (WBS 0/50/100 §5.4)');
    expect(banner).toHaveTextContent('3. Control de Valor Ganado (EVM CPI×SPI §7.4)');

    fireEvent.click(screen.getByTestId('welcome-template-charter'));

    const input = screen.getByLabelText('Nombre del proyecto');
    expect(input).toHaveValue('Iniciativa Ministerial — Línea Base PMI');

    fireEvent.click(screen.getByRole('button', { name: 'Crear' }));

    await waitFor(() =>
      expect(apiFetchMock).toHaveBeenCalledWith('/projects', {
        method: 'POST',
        token: 'test-token',
        body: {
          title: 'Iniciativa Ministerial — Línea Base PMI',
          description: 'Creado desde la vista Welcome de Proyectos.',
          status: 'planning',
        },
      }),
    );
    expect(pushMock).toHaveBeenCalledWith('/plataforma/projects/project-pmi-1?view=list');
  });
});
