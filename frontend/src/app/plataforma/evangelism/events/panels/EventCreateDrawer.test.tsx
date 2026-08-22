import React from 'react';
import { describe, it, expect, vi, beforeEach, type Mock } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import EventCreateDrawer, { type EventCreateForm, type AudiencePresetData } from './EventCreateDrawer';
import type { Persona, RoleDefinition } from '@/app/plataforma/evangelism/types';

interface MockDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  actions?: React.ReactNode;
  children?: React.ReactNode;
}

vi.mock('@/components/WorkspaceDrawer', () => ({
  default: ({ isOpen, onClose, title, actions, children }: MockDrawerProps) =>
    isOpen ? (
      <div data-testid="ws-drawer">
        <h2>{title}</h2>
        <button onClick={onClose}>ws-close</button>
        <div data-testid="ws-actions">{actions}</div>
        {children}
      </div>
    ) : null,
}));

vi.mock('@/components/ErrorBoundary', () => ({ default: ({ children }: { children?: React.ReactNode }) => <>{children}</> }));

const DEFAULT_FORM: EventCreateForm = {
  name: '', sede_id: '', description: '', event_type: 'PERMANENT',
  target_audience: 'ALL', target_role_id: '', target_role_ids: [],
  target_persona_ids: [], day_of_week: '0', month_day: '', fixed_date: '',
  start_time: '', end_time: '',
};

const ROLES: RoleDefinition[] = [{ id: 'r1', name: 'Lider' }, { id: 'r2', name: 'Ujier' }];
const PERSONAS: Persona[] = [
  { id: 'p1', nombre_completo: 'Juan Perez', email: 'j@x.com', church_role: 'Lider' },
];

type CreateProps = React.ComponentProps<typeof EventCreateDrawer>;
function makeProps(over: Partial<CreateProps> = {}): CreateProps {
  return {
    isOpen: true,
    onClose: vi.fn(),
    saving: false,
    onSubmit: vi.fn(),
    form: DEFAULT_FORM,
    setForm: vi.fn() as unknown as Mock,
    roles: ROLES,
    presets: [],
    onApplyPreset: vi.fn(),
    onDeletePreset: vi.fn(),
    onAddSuggestions: vi.fn(),
    onSavePreset: vi.fn(),
    manualSearch: '',
    setManualSearch: vi.fn(),
    manualPersonas: PERSONAS,
    ...over,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe('EventCreateDrawer', () => {
  it('no renderiza cuando isOpen=false', () => {
    render(<EventCreateDrawer {...makeProps({ isOpen: false })} />);
    expect(screen.queryByTestId('ws-drawer')).toBeNull();
  });

  it('renderiza título y campos principales del formulario', () => {
    render(<EventCreateDrawer {...makeProps()} />);
    expect(screen.getByText('Nuevo Evento')).toBeInTheDocument();
    expect(screen.getByLabelText(/Nombre del Evento/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Tipo de Evento/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Universo Esperado/i)).toBeInTheDocument();
  });

  it('cambiar nombre dispara setForm con el nuevo valor', () => {
    const props = makeProps();
    render(<EventCreateDrawer {...props} />);
    fireEvent.change(screen.getByLabelText(/Nombre del Evento/i), { target: { value: 'Culto Joven' } });
    expect(props.setForm).toHaveBeenCalledWith(expect.objectContaining({ name: 'Culto Joven' }));
  });

  it('seleccionar tipo PERMANENT mantiene visible el select de día de la semana', () => {
    render(<EventCreateDrawer {...makeProps({ form: { ...DEFAULT_FORM, event_type: 'PERMANENT' } })} />);
    expect(screen.getByLabelText(/Día de la Semana/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/Fecha Exacta/i)).toBeNull();
  });

  it('seleccionar tipo ONCE muestra el input de fecha exacta y oculta día de la semana', () => {
    render(<EventCreateDrawer {...makeProps({ form: { ...DEFAULT_FORM, event_type: 'ONCE' } })} />);
    expect(screen.getByLabelText(/Fecha Exacta/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/Día de la Semana/i)).toBeNull();
  });

  it('cambiar universo a ROLE habilita el multiselect de roles', () => {
    render(<EventCreateDrawer {...makeProps({ form: { ...DEFAULT_FORM, target_audience: 'ROLE' } })} />);
    const rolesSelect = screen.getByLabelText(/Roles esperados/i);
    expect(rolesSelect).not.toBeDisabled();
    fireEvent.change(rolesSelect, { target: { value: ['r1'] } });
    expect(screen.getByText('Lider')).toBeInTheDocument();
  });

  it('universo MANUAL renderiza el buscador de personas y la lista', () => {
    render(<EventCreateDrawer {...makeProps({
      form: { ...DEFAULT_FORM, target_audience: 'MANUAL' },
      manualPersonas: PERSONAS,
    })} />);
    expect(screen.getByPlaceholderText(/Buscar por nombre, correo o rol/i)).toBeInTheDocument();
    expect(screen.getByText('Juan Perez')).toBeInTheDocument();
  });

  it('click en persona del listado MANUAL dispara setForm con toggle de id', () => {
    const props = makeProps({ form: { ...DEFAULT_FORM, target_audience: 'MANUAL' } });
    render(<EventCreateDrawer {...props} />);
    const personaBtn = screen.getByText('Juan Perez').closest('button')!;
    fireEvent.click(personaBtn);
    expect(props.setForm).toHaveBeenCalledWith(expect.objectContaining({
      target_persona_ids: ['p1'], // empieza vacío → agrega
    }));
  });

  it('presets vacíos muestra mensaje y no lista items', () => {
    render(<EventCreateDrawer {...makeProps({ presets: [] })} />);
    expect(screen.getByText(/Aun no hay plantillas guardadas/i)).toBeInTheDocument();
  });

  it('presets populados renderiza cada item con sus acciones', () => {
    const presets: AudiencePresetData[] = [{ id: 'pr1', name: 'Jóvenes', target_audience: 'ROLE', target_role_ids: ['r1'], target_persona_ids: [] }];
    render(<EventCreateDrawer {...makeProps({ presets })} />);
    expect(screen.getByText('Jóvenes')).toBeInTheDocument();
    fireEvent.click(screen.getByText('Aplicar'));
    // el primer botón "Aplicar" visible
  });

  it('el botón Sugerencias dispara onAddSuggestions', () => {
    const props = makeProps();
    render(<EventCreateDrawer {...props} />);
    fireEvent.click(screen.getByText('Sugerencias'));
    expect(props.onAddSuggestions).toHaveBeenCalled();
  });
});
