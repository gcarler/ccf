import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { toast } from 'sonner';
import { SidebarLayerProvider } from '@/context/SidebarLayerContext';
import AssessmentDrawer from './AssessmentDrawer';
import { apiFetch } from '@/lib/http';

vi.mock('@/lib/http', () => ({
  apiFetch: vi.fn(),
}));

vi.mock('framer-motion', () => ({
  AnimatePresence: ({ children }: { children?: React.ReactNode }) => <>{children}</>,
  motion: {
    div: ({ children, ...props }: React.HTMLAttributes<HTMLDivElement>) => <div {...props}>{children}</div>,
  },
}));

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  },
}));

const mockApiFetch = vi.mocked(apiFetch);
const toastError = vi.mocked(toast.error);

const mockAssessment = {
  id: 'assessment-uuid-1',
  title: 'Evaluación de Teología',
  min_score: 70,
  max_attempts: 3,
  cooldown_minutes: 60,
  questions: [
    {
      id: 'q-1',
      question_text: '¿Quién escribió el Pentateuco?',
      question_type: 'multiple_choice',
      points: 10,
      options: [
        { id: 'opt-1', option_text: 'Moisés' },
        { id: 'opt-2', option_text: 'David' },
      ],
    },
  ],
};

const mockAttemptStatusNormal = {
  assessment_id: 'assessment-uuid-1',
  max_attempts: 3,
  attempts_count: 1,
  attempts_remaining: 2,
  cooldown_minutes: 60,
  in_cooldown: false,
  cooldown_remaining_seconds: 0,
  cooldown_until: null,
  can_attempt: true,
  last_attempt_score: 50.0,
  passed: false,
};

const mockAttemptStatusCooldown = {
  assessment_id: 'assessment-uuid-1',
  max_attempts: 3,
  attempts_count: 1,
  attempts_remaining: 2,
  cooldown_minutes: 60,
  in_cooldown: true,
  cooldown_remaining_seconds: 2400,
  cooldown_until: '2026-10-07T05:00:00Z',
  can_attempt: false,
  last_attempt_score: 40.0,
  passed: false,
};

const mockAttemptStatusExhausted = {
  assessment_id: 'assessment-uuid-1',
  max_attempts: 3,
  attempts_count: 3,
  attempts_remaining: 0,
  cooldown_minutes: 60,
  in_cooldown: false,
  cooldown_remaining_seconds: 0,
  cooldown_until: null,
  can_attempt: false,
  last_attempt_score: 55.0,
  passed: false,
};

function renderDrawer(props: Partial<React.ComponentProps<typeof AssessmentDrawer>> = {}) {
  return render(
    <SidebarLayerProvider>
      <AssessmentDrawer
        assessmentId={props.assessmentId ?? 'assessment-uuid-1'}
        enrollmentId={props.enrollmentId ?? 'enrollment-uuid-1'}
        token={props.token ?? 'test-token'}
        onClose={props.onClose ?? vi.fn()}
        onSuccess={props.onSuccess ?? vi.fn()}
      />
    </SidebarLayerProvider>,
  );
}

describe('AssessmentDrawer — Políticas de Reintento y Cooldown', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('muestra las políticas de evaluación (máx intentos y cooldown) y permite iniciar si está habilitado', async () => {
    mockApiFetch.mockImplementation(async (url: string) => {
      if (url.includes('/attempt-status')) return mockAttemptStatusNormal;
      return mockAssessment;
    });

    renderDrawer();

    await waitFor(() => {
      expect(screen.getByText('Instrucciones de Evaluación')).toBeInTheDocument();
    });

    expect(screen.getByText('1 / 3 intentos')).toBeInTheDocument();
    expect(screen.getByText('60 min de enfriamiento')).toBeInTheDocument();
    const startButton = screen.getByRole('button', { name: /iniciar examen/i });
    expect(startButton).toBeEnabled();
  });

  it('bloquea el inicio y muestra alerta cuando la ventana de enfriamiento está activa', async () => {
    mockApiFetch.mockImplementation(async (url: string) => {
      if (url.includes('/attempt-status')) return mockAttemptStatusCooldown;
      return mockAssessment;
    });

    renderDrawer();

    await waitFor(() => {
      expect(screen.getByText(/período de enfriamiento activo/i)).toBeInTheDocument();
    });

    const startButton = screen.getByRole('button', { name: /enfriamiento activo/i });
    expect(startButton).toBeDisabled();
  });

  it('bloquea el inicio cuando se ha alcanzado el límite máximo de intentos', async () => {
    mockApiFetch.mockImplementation(async (url: string) => {
      if (url.includes('/attempt-status')) return mockAttemptStatusExhausted;
      return mockAssessment;
    });

    renderDrawer();

    await waitFor(() => {
      expect(screen.getByText(/has alcanzado el límite máximo de 3 intentos/i)).toBeInTheDocument();
    });

    const startButton = screen.getByRole('button', { name: /intentos agotados/i });
    expect(startButton).toBeDisabled();
  });

  it('permite avanzar preguntas, seleccionar opción y enviar la evaluación exitosa', async () => {
    mockApiFetch.mockImplementation(async (url: string, opts?: { method?: string }) => {
      if (url.includes('/attempt-status')) return mockAttemptStatusNormal;
      if (url.includes('/submit') && opts?.method === 'POST') {
        return { passed: true, score: 100 };
      }
      return mockAssessment;
    });

    const onSuccess = vi.fn();
    renderDrawer({ onSuccess });

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /iniciar examen/i })).toBeEnabled();
    });

    fireEvent.click(screen.getByRole('button', { name: /iniciar examen/i }));

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: '¿Quién escribió el Pentateuco?' })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('radio', { name: /moisés/i }));

    const finishButton = screen.getByRole('button', { name: /finalizar examen/i });
    expect(finishButton).toBeEnabled();
    fireEvent.click(finishButton);

    await waitFor(() => {
      expect(screen.getByText('¡Felicidades, Siervo!')).toBeInTheDocument();
      expect(onSuccess).toHaveBeenCalledWith(100);
    });
  });

  it('muestra toast de error cuando submit falla por cooldown o límite de intentos', async () => {
    mockApiFetch.mockImplementation(async (url: string, opts?: { method?: string }) => {
      if (url.includes('/attempt-status')) return mockAttemptStatusNormal;
      if (url.includes('/submit') && opts?.method === 'POST') {
        throw new Error('Período de enfriamiento activo. Debes esperar 40 minuto(s)');
      }
      return mockAssessment;
    });

    renderDrawer();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /iniciar examen/i })).toBeEnabled();
    });

    fireEvent.click(screen.getByRole('button', { name: /iniciar examen/i }));

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: '¿Quién escribió el Pentateuco?' })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('radio', { name: /moisés/i }));
    fireEvent.click(screen.getByRole('button', { name: /finalizar examen/i }));

    await waitFor(() => {
      expect(toastError).toHaveBeenCalledWith(expect.stringContaining('Período de enfriamiento activo'));
    });
  });
});
