import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { toast } from 'sonner';
import { SidebarLayerProvider } from '@/context/SidebarLayerContext';
import GradingSchemeDrawer from './GradingSchemeDrawer';
import { apiFetch } from '@/lib/http';
import type { GradingScheme } from '@/types/academy';

vi.mock('@/lib/http', () => ({
  apiFetch: vi.fn(),
}));

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  },
}));

const mockApiFetch = vi.mocked(apiFetch);
const toastSuccess = vi.mocked(toast.success);

function renderDrawer(props: Partial<React.ComponentProps<typeof GradingSchemeDrawer>> = {}) {
  return render(
    <SidebarLayerProvider>
      <GradingSchemeDrawer open {...props} onClose={props.onClose ?? vi.fn()} scheme={props.scheme ?? null} token={props.token ?? 't'} onSuccess={props.onSuccess ?? vi.fn()} />
    </SidebarLayerProvider>,
  );
}

function makeScheme(overrides: Partial<GradingScheme> = {}): GradingScheme {
  return {
    id: 'scheme-1',
    name: 'Esquema Canónico',
    scale_max: 100,
    passing_grade: 70,
    is_default: false,
    is_active: true,
    cuts: [
      { name: 'Primer Corte', order_index: 1, weight_percent: 30 },
      { name: 'Segundo Corte', order_index: 2, weight_percent: 30 },
      { name: 'Examen Final / Proyecto (40%)', order_index: 3, weight_percent: 40 },
    ],
    ...overrides,
  };
}

describe('GradingSchemeDrawer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockApiFetch.mockResolvedValue(makeScheme());
  });

  it('muestra los cortes del esquema en edición con suma 100% válida', () => {
    renderDrawer({ scheme: makeScheme() });

    expect(screen.getByDisplayValue('Esquema Canónico')).toBeInTheDocument();
    expect(screen.getByText('Cortes / Notas del Período (3)')).toBeInTheDocument();
    expect(screen.getByText('100% / 100%')).toBeInTheDocument();
    expect(screen.getAllByPlaceholderText('Nombre del corte (ej. Primer Corte)')).toHaveLength(3);
  });

  it('deshabilita Guardar y advierte cuando la suma de cortes excede 100%', () => {
    renderDrawer();

    // Peso del corte final por defecto: 40 → lo subimos a 60 (total 120).
    const finalCutWeight = screen.getAllByDisplayValue('40')[0];
    fireEvent.change(finalCutWeight, { target: { value: '60' } });

    expect(screen.getByText(/Excede por/)).toBeInTheDocument();
    expect(screen.getByText('120% / 100%')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Guardar Esquema/ })).toBeDisabled();
    expect(mockApiFetch).not.toHaveBeenCalled();
  });

  it('permite añadir un corte y recalcula el total', () => {
    renderDrawer();

    fireEvent.click(screen.getByRole('button', { name: /Añadir Corte/ }));

    // El corte adicional nace con peso 10 → 110% total (inválido hasta ajustar).
    expect(screen.getByText('Cortes / Notas del Período (4)')).toBeInTheDocument();
    expect(screen.getByText('110% / 100%')).toBeInTheDocument();
  });

  it('envía el payload y notifica éxito al crear un esquema', async () => {
    const onSuccess = vi.fn();
    const onClose = vi.fn();
    renderDrawer({ onSuccess, onClose });

    fireEvent.change(screen.getByPlaceholderText('Ej: Semestral Canónico CCF (30% - 30% - 40%)'), {
      target: { value: 'Esquema de Prueba' },
    });
    // jsdom no implementa el submit implícito por botón: disparamos el submit del form.
    const form = screen.getByRole('button', { name: /Guardar Esquema/ }).closest('form');
    expect(form).not.toBeNull();
    fireEvent.submit(form as HTMLFormElement);

    await waitFor(() => expect(onSuccess).toHaveBeenCalledTimes(1));
    expect(mockApiFetch).toHaveBeenCalledWith('/academy/admin/grading-schemes', {
      method: 'POST',
      token: 't',
      body: expect.objectContaining({ name: 'Esquema de Prueba' }),
    });
    expect(toastSuccess).toHaveBeenCalledWith('Esquema de calificación creado');
    expect(onClose).toHaveBeenCalled();
  });
});
