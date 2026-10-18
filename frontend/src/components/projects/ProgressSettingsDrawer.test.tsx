import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const mocks = vi.hoisted(() => ({
  apiFetch: vi.fn(),
  addToast: vi.fn(),
}));

vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({ token: 'test-token', loading: false }),
}));

vi.mock('@/context/ToastContext', () => ({
  useToast: () => ({ addToast: mocks.addToast }),
}));

vi.mock('@/lib/http', () => ({
  apiFetch: (...args: unknown[]) => mocks.apiFetch(...args),
}));

import { ProgressSettingsDrawer } from './ProgressSettingsDrawer';

describe('ProgressSettingsDrawer PMI EVMT Advisor & Governance', () => {
  beforeEach(() => {
    mocks.apiFetch.mockReset();
    mocks.addToast.mockReset();
  });

  it('displays dynamic PMI EVMT technique diagnostics for each progress mode', () => {
    render(
      <ProgressSettingsDrawer
        projectId="proj-100"
        isOpen={true}
        onClose={vi.fn()}
        currentMode="auto_tasks"
      />,
    );

    const evmtCard = screen.getByTestId('progress-settings-pmi-evmt-card');
    expect(evmtCard).toHaveTextContent('Unidades Completadas / Fórmula Fija (0/50/100)');
    expect(evmtCard).toHaveTextContent('Nivel de Objetividad: Alta');
    expect(screen.queryByTestId('progress-settings-pmi-override-warning')).not.toBeInTheDocument();

    // Switch to milestones mode
    fireEvent.click(screen.getByText('Automático por Hitos'));
    expect(evmtCard).toHaveTextContent('Hitos Ponderados (Weighted Milestones)');
    expect(evmtCard).toHaveTextContent('Nivel de Objetividad: Alta');
    expect(screen.queryByTestId('progress-settings-pmi-override-warning')).not.toBeInTheDocument();

    // Switch to manual mode
    fireEvent.click(screen.getByText('Manual'));
    expect(evmtCard).toHaveTextContent('Porcentaje Estimado / Juicio de Experto');
    expect(evmtCard).toHaveTextContent('Nivel de Objetividad: Media-Baja');
    expect(screen.getByTestId('progress-settings-pmi-override-warning')).toBeInTheDocument();
  });

  it('shows PMI governance override warning when healthOverride is set even in auto_tasks mode', () => {
    render(
      <ProgressSettingsDrawer
        projectId="proj-100"
        isOpen={true}
        onClose={vi.fn()}
        currentMode="auto_tasks"
        currentHealthOverride={null}
      />,
    );

    expect(screen.queryByTestId('progress-settings-pmi-override-warning')).not.toBeInTheDocument();

    fireEvent.click(screen.getByText('En Riesgo (Ámbar)'));

    const warning = screen.getByTestId('progress-settings-pmi-override-warning');
    expect(warning).toBeInTheDocument();
    expect(warning).toHaveTextContent(/CPI \/ SPI/i);
  });

  it('submits PATCH /projects/:id with manual progress and health override via apiFetch', async () => {
    mocks.apiFetch.mockResolvedValueOnce({});
    const onClose = vi.fn();
    const onSaved = vi.fn();

    render(
      <ProgressSettingsDrawer
        projectId="proj-777"
        isOpen={true}
        onClose={onClose}
        onSaved={onSaved}
        currentMode="auto_tasks"
        manualProgress={25}
        currentHealthOverride={null}
      />,
    );

    fireEvent.click(screen.getByText('Manual'));
    const slider = screen.getByRole('slider');
    fireEvent.change(slider, { target: { value: '65' } });
    fireEvent.click(screen.getByText('En Camino (Verde)'));

    fireEvent.click(screen.getByRole('button', { name: /Aplicar Cambios/i }));

    await waitFor(() => {
      expect(mocks.apiFetch).toHaveBeenCalledWith(
        '/projects/proj-777',
        expect.objectContaining({
          method: 'PATCH',
          token: 'test-token',
          body: {
            progress_mode: 'manual',
            manual_progress: 65,
            health_override: 'on_track',
          },
        }),
      );
    });
    expect(onSaved).toHaveBeenCalled();
    expect(onClose).toHaveBeenCalled();
  });
});
