import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { SidebarLayerProvider } from '@/context/SidebarLayerContext';
import AcademyAdminConsole from './page';
import { apiFetch } from '@/lib/http';
import type { AcademicProgram, AcademicPeriod, GradingScheme, StudyPlan, PeriodOffering } from '@/types/academy';

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

vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({
    token: 'test-token',
    isAuthenticated: true,
    user: { id: 'user-1' },
    hasModuleAccess: vi.fn(() => true),
  }),
}));

const mockApiFetch = vi.mocked(apiFetch);

function makeProgram(overrides: Partial<AcademicProgram> = {}): AcademicProgram {
  return {
    id: 'prog-1',
    code: 'CUR-001',
    name: 'Curso de Fundamentos',
    description: 'Curso introductorio de la plataforma',
    program_type: 'curso',
    total_duration_type: 'semanas',
    total_duration_units: 8,
    total_credits: 0,
    modality: 'virtual',
    has_teachers: true,
    teachers_can_grade: true,
    min_passing_grade: 70,
    grading_scale_max: 100,
    min_attendance_percent: 70,
    is_active: true,
    ...overrides,
  };
}

function makePeriod(overrides: Partial<AcademicPeriod> = {}): AcademicPeriod {
  return {
    id: 'period-1',
    code: '2026-II',
    name: 'Semestre 2026-II',
    period_type: 'semestral',
    start_date: '2026-08-01',
    end_date: '2026-12-15',
    status: 'open',
    is_active: true,
    ...overrides,
  };
}

function makeScheme(overrides: Partial<GradingScheme> = {}): GradingScheme {
  return {
    id: 'scheme-1',
    name: 'Semestral Canónico',
    scale_max: 100,
    passing_grade: 70,
    is_default: true,
    is_active: true,
    cuts: [
      { name: 'Primer Corte', order_index: 1, weight_percent: 30 },
      { name: 'Segundo Corte', order_index: 2, weight_percent: 30 },
      { name: 'Examen Final', order_index: 3, weight_percent: 40 },
    ],
    ...overrides,
  };
}

function makePlan(overrides: Partial<StudyPlan> = {}): StudyPlan {
  return {
    id: 'plan-1',
    program_id: 'prog-1',
    code: 'PEN-001',
    name: 'Pensum Fundamentos',
    total_credits: 0,
    total_levels: 1,
    level_type: 'semestre',
    is_active: true,
    subjects: [],
    ...overrides,
  };
}

function makeOffering(overrides: Partial<PeriodOffering> = {}): PeriodOffering {
  return {
    id: 'off-1',
    academic_period_id: 'period-1',
    subject_id: 'subj-1',
    grading_scheme_id: 'scheme-1',
    group_name: 'Grupo A',
    quota_max: 40,
    credits: 3,
    status: 'open',
    subject_name: 'Fundamentos de la Fe',
    enrolled_count: 12,
    ...overrides,
  };
}

function renderConsole() {
  return render(
    <SidebarLayerProvider>
      <AcademyAdminConsole />
    </SidebarLayerProvider>,
  );
}

describe('AcademyAdminConsole', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockApiFetch.mockImplementation((url: string) => {
      if (typeof url !== 'string') return Promise.resolve([]);
      if (url.includes('/programs')) return Promise.resolve([makeProgram()]);
      if (url.includes('/periods')) return Promise.resolve([makePeriod()]);
      if (url.includes('/grading-schemes')) return Promise.resolve([makeScheme()]);
      if (url.includes('/study-plans')) return Promise.resolve([makePlan()]);
      if (url.includes('/offerings')) return Promise.resolve([makeOffering()]);
      return Promise.resolve([]);
    });
  });

  it('carga los datos en paralelo y muestra el programa en el tab inicial', async () => {
    renderConsole();

    await waitFor(() => {
      expect(screen.getByText('Curso de Fundamentos')).toBeInTheDocument();
    });
    expect(mockApiFetch).toHaveBeenCalledTimes(5);
    expect(mockApiFetch.mock.calls[0][0]).toContain('/academy/admin/programs');
  });

  it('filtra programas por búsqueda y muestra estado vacío de cero coincidencias', async () => {
    renderConsole();
    await screen.findByText('Curso de Fundamentos');

    fireEvent.change(screen.getByPlaceholderText('Buscar por código, nombre o docente...'), {
      target: { value: 'zzz-sin-resultados' },
    });

    expect(screen.getByText('Cero coincidencias')).toBeInTheDocument();
    expect(screen.queryByText('Curso de Fundamentos')).not.toBeInTheDocument();
  });

  it('cambia al tab de períodos y lista el período semestral', async () => {
    renderConsole();
    await screen.findByText('Curso de Fundamentos');

    fireEvent.click(screen.getByRole('button', { name: /Períodos & Semestres/ }));
    await waitFor(() => {
      expect(screen.getByText('Semestre 2026-II')).toBeInTheDocument();
    });
    expect(screen.getByText('open')).toBeInTheDocument();
  });

  it('cambia al tab de esquemas y muestra el esquema canónico con su escala', async () => {
    renderConsole();
    await screen.findByText('Curso de Fundamentos');

    fireEvent.click(screen.getByRole('button', { name: /Esquemas de Cortes/ }));
    expect(await screen.findByText('Semestral Canónico')).toBeInTheDocument();
    expect(screen.getByText('Escala 0 - 100 (Aprobatoria: 70)')).toBeInTheDocument();
  });

  it('muestra el estado vacío del tab de esquemas cuando no hay esquemas', async () => {
    mockApiFetch.mockImplementation((url: string) => {
      if (typeof url !== 'string') return Promise.resolve([]);
      if (url.includes('/grading-schemes')) return Promise.resolve([]);
      return Promise.resolve([makeProgram()]);
    });
    renderConsole();
    await screen.findByText('Curso de Fundamentos');

    fireEvent.click(screen.getByRole('button', { name: /Esquemas de Cortes/ }));
    expect(await screen.findByText('No hay esquemas de calificación')).toBeInTheDocument();
  });
});
