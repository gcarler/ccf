import React from 'react';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ProjectTemplateCatalogDrawer } from './ProjectTemplateCatalogDrawer';

const mocks = vi.hoisted(() => ({ apiFetch: vi.fn(), addToast: vi.fn() }));
const template = {
  id: 'template-1',
  name: 'Plan de proyecto',
  description: 'Base reutilizable',
  category: 'general',
  default_budget: 0,
  structure: { phases: [], tasks: [] },
  is_public: true,
  sede_id: 'sede-1',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

vi.mock('next/navigation', () => ({ useRouter: () => ({ push: vi.fn() }) }));
vi.mock('@/context/AuthContext', () => ({ useAuth: () => ({ token: 'test-token' }) }));
vi.mock('@/context/ToastContext', () => ({ useToast: () => ({ addToast: mocks.addToast }) }));
vi.mock('@/lib/http', () => ({ apiFetch: mocks.apiFetch }));
vi.mock('@/components/ui/RightPanel', () => ({
  RightPanel: ({ isOpen, children }: React.PropsWithChildren<{ isOpen: boolean }>) => isOpen ? <div>{children}</div> : null,
}));

describe('ProjectTemplateCatalogDrawer deletion', () => {
  beforeEach(() => {
    mocks.apiFetch.mockReset().mockImplementation((path: string, options?: { method?: string }) => {
      if (options?.method === 'DELETE') return Promise.resolve({ ok: true });
      if (path.startsWith('/projects/templates')) return Promise.resolve([template]);
      return Promise.resolve([]);
    });
    mocks.addToast.mockClear();
  });

  it('cancels template deletion without mutating the catalog', async () => {
    render(<ProjectTemplateCatalogDrawer isOpen onClose={vi.fn()} />);
    expect(await screen.findByText('Plan de proyecto')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Eliminar plantilla Plan de proyecto' }));
    expect(await screen.findByRole('complementary', { name: 'Eliminar plantilla' })).toBeInTheDocument();
    expect(mocks.apiFetch.mock.calls.some(([, options]) => options?.method === 'DELETE')).toBe(false);

    fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }));
    await waitFor(() => expect(screen.queryByRole('complementary', { name: 'Eliminar plantilla' })).not.toBeInTheDocument());
    expect(screen.getByText('Plan de proyecto')).toBeInTheDocument();
    expect(mocks.apiFetch.mock.calls.some(([, options]) => options?.method === 'DELETE')).toBe(false);
  });

  it('deletes only after confirmation and refreshes the catalog', async () => {
    let listCalls = 0;
    mocks.apiFetch.mockImplementation((path: string, options?: { method?: string }) => {
      if (options?.method === 'DELETE') return Promise.resolve({ ok: true });
      if (path.startsWith('/projects/templates')) {
        listCalls += 1;
        return Promise.resolve(listCalls === 1 ? [template] : []);
      }
      return Promise.resolve([]);
    });
    render(<ProjectTemplateCatalogDrawer isOpen onClose={vi.fn()} />);
    expect(await screen.findByText('Plan de proyecto')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Eliminar plantilla Plan de proyecto' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Eliminar plantilla' }));

    await waitFor(() => expect(mocks.apiFetch).toHaveBeenCalledWith(
      '/projects/templates/template-1',
      expect.objectContaining({ method: 'DELETE', token: 'test-token' }),
    ));
    await waitFor(() => expect(screen.getByText('No se encontraron plantillas')).toBeInTheDocument());
  });

  it('keeps the template and confirmation drawer available after a failed delete', async () => {
    mocks.apiFetch.mockImplementation((path: string, options?: { method?: string }) => {
      if (options?.method === 'DELETE') return Promise.reject(new Error('offline'));
      if (path.startsWith('/projects/templates')) return Promise.resolve([template]);
      return Promise.resolve([]);
    });
    render(<ProjectTemplateCatalogDrawer isOpen onClose={vi.fn()} />);
    expect(await screen.findByText('Plan de proyecto')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Eliminar plantilla Plan de proyecto' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Eliminar plantilla' }));

    await waitFor(() => expect(mocks.addToast).toHaveBeenCalledWith('Error al eliminar la plantilla', 'error'));
    expect(screen.getByText('Plan de proyecto')).toBeInTheDocument();
    expect(screen.getByRole('complementary', { name: 'Eliminar plantilla' })).toBeInTheDocument();
  });
});

const predictiveTemplate = {
  ...template,
  id: 'template-predictive',
  name: 'Retiro Espiritual (Predictivo)',
  default_budget: 12000,
  structure: {
    phases: [
      { name: 'Preparación', order_index: 0 },
      { name: 'Ejecución', order_index: 1 },
      { name: 'Cierre', order_index: 2 },
    ],
    tasks: [
      { title: 'Logística inicial', duration_days: 5, day_offset: 0 },
      { title: 'Retiro en montaña', duration_days: 10, day_offset: 7 },
      { title: 'Informe final', duration_days: 15, day_offset: 20 },
    ],
  },
};

const hybridTemplate = {
  ...template,
  id: 'template-hybrid',
  name: 'Formación Catequesis (Híbrida)',
  default_budget: 0,
  structure: {
    phases: [
      { name: 'Diseño', order_index: 0 },
      { name: 'Piloto', order_index: 1 },
    ],
    tasks: [
      { title: 'Encuestas iniciales', duration_days: 6, day_offset: 0 },
      { title: 'Piloto paralelo', duration_days: 6, day_offset: 0 },
    ],
  },
};

const adaptiveTemplate = {
  ...template,
  id: 'template-adaptive',
  name: 'Base Mínima (Adaptativa)',
  default_budget: 0,
  structure: { phases: [], tasks: [] },
};

describe('ProjectTemplateCatalogDrawer — OPA y Tailoring PMI', () => {
  beforeEach(() => {
    mocks.apiFetch.mockReset().mockImplementation((path: string, options?: { method?: string }) => {
      if (options?.method === 'DELETE') return Promise.resolve({ ok: true });
      if (path.startsWith('/projects/templates')) return Promise.resolve([predictiveTemplate, hybridTemplate, adaptiveTemplate]);
      return Promise.resolve([]);
    });
    mocks.addToast.mockClear();
  });

  it('clasifica el enfoque PMI por plantilla (Predictivo, Híbrido, Adaptativo)', async () => {
    render(<ProjectTemplateCatalogDrawer isOpen onClose={vi.fn()} />);

    await waitFor(() => expect(screen.getByTestId('template-pmi-tailoring-template-predictive')).toBeInTheDocument());

    const predictiveCard = screen.getByTestId('template-pmi-tailoring-template-predictive');
    expect(predictiveCard).toHaveTextContent('Predictivo (Cascada / Fase-Compuerta)');
    expect(screen.getByTestId('template-pmi-tailoring-template-hybrid')).toHaveTextContent(
      'Híbrido (Iterativo por Fases)',
    );
    expect(screen.getByTestId('template-pmi-tailoring-template-adaptive')).toHaveTextContent(
      'Adaptativo (Ágil / Flujo Continuo)',
    );
  });

  it('muestra la madurez OPA (3/3 listo vs incompleto) y la duración estimada del ciclo', async () => {
    render(<ProjectTemplateCatalogDrawer isOpen onClose={vi.fn()} />);

    await screen.findByText('Retiro Espiritual (Predictivo)');

    // Predictiva: fases + paquetes + BAC → OPA 3/3 · Listo para PMB; ciclo = 20+15 = 35 días
    const predictiveCardText = () =>
      screen.getByTestId('template-pmi-tailoring-template-predictive').textContent ?? '';
    expect(predictiveCardText()).toContain('OPA 3/3 · Listo para PMB');
    expect(screen.getByTestId('template-pmi-tailoring-template-predictive')).toHaveTextContent('35 días');

    // Híbrida: sin BAC → 2/3 pilares; base vacía: 0/3 pilares con aviso de calibración
    expect(screen.getByTestId('template-pmi-tailoring-template-hybrid')).toHaveTextContent(
      'OPA Incompleto · Requiere Calibración (2/3)',
    );
    expect(screen.getByTestId('template-pmi-tailoring-template-adaptive')).toHaveTextContent(
      'OPA Incompleto · Requiere Calibración (0/3)',
    );
  });

  it('filtra el catálogo por enfoque de desarrollo PMI con template-tailoring-filter', async () => {
    render(<ProjectTemplateCatalogDrawer isOpen onClose={vi.fn()} />);

    await screen.findByText('Retiro Espiritual (Predictivo)');

    // Todos: 3 tarjetas visibles
    expect(screen.getByTestId('template-pmi-tailoring-template-predictive')).toBeInTheDocument();
    expect(screen.getByTestId('template-pmi-tailoring-template-hybrid')).toBeInTheDocument();
    expect(screen.getByTestId('template-pmi-tailoring-template-adaptive')).toBeInTheDocument();

    // Filtrar solo Predictivo
    fireEvent.click(within(screen.getByTestId('template-tailoring-filter')).getByRole('button', { name: 'Predictivo' }));
    expect(screen.getByTestId('template-pmi-tailoring-template-predictive')).toBeInTheDocument();
    expect(screen.queryByTestId('template-pmi-tailoring-template-hybrid')).not.toBeInTheDocument();
    expect(screen.queryByTestId('template-pmi-tailoring-template-adaptive')).not.toBeInTheDocument();

    // Filtrar Adaptativo: solo la plantilla base (fases = 0 ≤ 1)
    fireEvent.click(within(screen.getByTestId('template-tailoring-filter')).getByRole('button', { name: 'Adaptativo' }));
    expect(screen.queryByTestId('template-pmi-tailoring-template-predictive')).not.toBeInTheDocument();
    expect(screen.getByTestId('template-pmi-tailoring-template-adaptive')).toBeInTheDocument();

    // Volver a Todos
    fireEvent.click(within(screen.getByTestId('template-tailoring-filter')).getByRole('button', { name: 'Todos' }));
    expect(screen.getAllByTestId(/^template-pmi-tailoring-/)).toHaveLength(3);
  });
});
