/* eslint-disable @typescript-eslint/no-explicit-any */
import React from 'react';
import { render, act } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import ProjectsClient from './ProjectsClient';
import { createMockProject } from '@/test-utils/factories';
import { PROJECTS_LIST_ANCHOR } from './projectsLinks';

// Captura el onAnimationComplete del motion.div para dispararlo en el test
// (reemplaza el flujo real de AnimatePresence mode="wait" + animación de entrada).
let capturedAnimationComplete: (() => void) | null = null;

vi.mock('framer-motion', () => ({
  AnimatePresence: ({ children }: any) => <>{children}</>,
  motion: {
    div: ({ children, onAnimationComplete, _initial, _animate, _exit, ...props }: any) => {
      capturedAnimationComplete = onAnimationComplete ?? null;
      return <div {...props}>{children}</div>;
    },
  },
}));

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock('next/link', () => ({
  default: ({ href, children }: any) => <a href={href}>{children}</a>,
}));

vi.mock('next/dynamic', () => ({
  __esModule: true,
  default: () => {
    const Dummy = () => <div />;
    return Dummy;
  },
}));

vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({ token: 'test-token' }),
}));

vi.mock('@/context/CommandCenterContext', () => ({
  useRegisterCommands: vi.fn(),
}));

vi.mock('@/hooks/useProjects', () => ({
  useProjects: () => ({ updateProject: vi.fn(), deleteProject: vi.fn() }),
}));

vi.mock('@/lib/http', () => ({
  apiFetch: vi.fn().mockResolvedValue({ cards: [], workload_distribution: [], delayed_tasks_count: 0 }),
}));

vi.mock('@/design', () => ({
  DSCard: ({ children }: any) => <div>{children}</div>,
  DSChart: () => <div />,
  DSMetric: () => <div />,
}));

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

vi.mock('@/components/projects/ProjectsShell', () => ({
  default: ({ children }: any) => <div>{children}</div>,
}));

vi.mock('@/components/projects/ProjectCreationDrawer', () => ({
  default: () => null,
}));

vi.mock('./views/ProjectsGridView', () => ({ default: () => <div>grid</div> }));
vi.mock('./views/ProjectsListView', () => ({ default: () => <div>list</div> }));
vi.mock('./views/ProjectsTableView', () => ({ default: () => <div>table</div> }));
vi.mock('./views/ProjectsBoardView', () => ({ default: () => <div>board</div> }));

describe('ProjectsClient scroll-to-list (fix carrera 100ms vs ~300ms)', () => {
  const project = createMockProject({ id: 'p1', title: 'Proyecto Alpha', description: 'Desc' });

  beforeEach(() => {
    capturedAnimationComplete = null;
    vi.clearAllMocks();
  });

  it('dispara scrollIntoView cuando viewType=list y el anchor está montado', async () => {
    const scrollSpy = vi.spyOn(HTMLElement.prototype, 'scrollIntoView').mockImplementation(() => {});
    try {
      const { container } = render(
        <ProjectsClient initialProjects={[project]} initialViewType="list" />,
      );
      // Flush del useEffect del dashboard (apiFetch async) para evitar
      // warnings de act() con el setState fuera de act.
      await act(async () => {});

      // El wrapper del listado con el id del anchor debe existir en el DOM.
      expect(container.querySelector(`#${PROJECTS_LIST_ANCHOR}`)).toBeTruthy();
      expect(capturedAnimationComplete).toBeTruthy();

      // Simula la finalización de la animación de entrada (el momento en que
      // AnimatePresence mode="wait" ya montó la vista y el ref está poblado).
      act(() => {
        capturedAnimationComplete?.();
      });

      expect(scrollSpy).toHaveBeenCalledWith({ behavior: 'smooth', block: 'start' });
    } finally {
      scrollSpy.mockRestore();
    }
  });

  it('no dispara scrollIntoView en vista grid (guard viewType !== list)', async () => {
    const scrollSpy = vi.spyOn(HTMLElement.prototype, 'scrollIntoView').mockImplementation(() => {});
    try {
      render(<ProjectsClient initialProjects={[project]} initialViewType="grid" />);
      await act(async () => {});

      expect(capturedAnimationComplete).toBeTruthy();
      act(() => {
        capturedAnimationComplete?.();
      });

      expect(scrollSpy).not.toHaveBeenCalled();
    } finally {
      scrollSpy.mockRestore();
    }
  });

  it('scrollea solo una vez por transición a la vista list (guard scrollTriggeredViewRef)', async () => {
    const scrollSpy = vi.spyOn(HTMLElement.prototype, 'scrollIntoView').mockImplementation(() => {});
    try {
      render(<ProjectsClient initialProjects={[project]} initialViewType="list" />);
      await act(async () => {});

      act(() => {
        capturedAnimationComplete?.();
      });
      act(() => {
        capturedAnimationComplete?.();
      });

      expect(scrollSpy).toHaveBeenCalledTimes(1);
    } finally {
      scrollSpy.mockRestore();
    }
  });

  it('no scrollea cuando filtered está vacío (sin anchor ni ref montado)', async () => {
    const scrollSpy = vi.spyOn(HTMLElement.prototype, 'scrollIntoView').mockImplementation(() => {});
    try {
      // Forzamos lista vacía para el caso empty (sin wrapper del listado).
      render(<ProjectsClient initialProjects={[]} initialViewType="list" />);
      await act(async () => {});

      act(() => {
        capturedAnimationComplete?.();
      });

      // Sin wrapper del listado, el ref es null -> no-op seguro.
      expect(scrollSpy).not.toHaveBeenCalled();
    } finally {
      scrollSpy.mockRestore();
    }
  });
});
