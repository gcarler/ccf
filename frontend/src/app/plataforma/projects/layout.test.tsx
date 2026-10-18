import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi, afterEach } from 'vitest';
import type { ProjectSummaryPageResponse } from '@/types/projects';

const { cookiesMock, serverApiFetchMock, layoutClientSpy, consoleErrorSpy } = vi.hoisted(() => ({
  cookiesMock: vi.fn(),
  serverApiFetchMock: vi.fn(),
  layoutClientSpy: vi.fn(),
  consoleErrorSpy: vi.fn(),
}));

vi.mock('next/headers', () => ({
  cookies: cookiesMock,
}));

vi.mock('@/lib/serverApi', () => ({
  serverApiFetch: serverApiFetchMock,
}));

vi.mock('./ProjectsLayoutClient', () => ({
  default: ({ initialProjectPage, children }: { initialProjectPage: ProjectSummaryPageResponse | null; children: React.ReactNode }) => {
    layoutClientSpy({ initialProjectPage });
    return (
      <section data-testid="projects-layout-client-mock">
        {children}
      </section>
    );
  },
}));

import ProjectsLayout, { dynamic } from './layout';

function withCookie(hasCookie: boolean) {
  cookiesMock.mockResolvedValue({ has: (name: string) => name === 'mesh_access' && hasCookie });
}

describe('ProjectsLayout — arranque SSR del portafolio', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    cookiesMock.mockReset();
    serverApiFetchMock.mockReset();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('declara el modo de render dinámico', () => {
    expect(dynamic).toBe('force-dynamic');
  });

  it('sin cookie mesh_access: no llama a serverApiFetch y pasa initialProjectPage null', async () => {
    withCookie(false);

    render(await ProjectsLayout({ children: <p>Portal infantil</p> }));

    expect(cookiesMock).toHaveBeenCalledOnce();
    expect(serverApiFetchMock).not.toHaveBeenCalled();
    expect(layoutClientSpy).toHaveBeenCalledWith({ initialProjectPage: null });
    expect(screen.getByTestId('projects-layout-client-mock')).toBeInTheDocument();
    expect(screen.getByText('Portal infantil')).toBeInTheDocument();
  });

  it('con cookie mesh_access: obtiene la página resumen y la pasa como initialProjectPage', async () => {
    withCookie(true);
    const summaryPage: ProjectSummaryPageResponse = {
      items: [],
      total: 0,
      skip: 0,
      limit: 100,
    };
    serverApiFetchMock.mockResolvedValueOnce(summaryPage);

    render(await ProjectsLayout({ children: <p>Portal autenticado</p> }));

    expect(serverApiFetchMock).toHaveBeenCalledWith('/projects/summary-page?offset=0&limit=100');
    expect(layoutClientSpy).toHaveBeenLastCalledWith({ initialProjectPage: summaryPage });
    expect(screen.getByText('Portal autenticado')).toBeInTheDocument();
  });

  it('ante error de serverApiFetch registra en console.error y degrade a initialProjectPage null sin caer', async () => {
    withCookie(true);
    const originalConsoleError = console.error;
    console.error = consoleErrorSpy;
    serverApiFetchMock.mockRejectedValueOnce(new Error('offline'));

    try {
      render(await ProjectsLayout({ children: <p>Portal en degradación</p> }));

      expect(serverApiFetchMock).toHaveBeenCalledWith('/projects/summary-page?offset=0&limit=100');
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        '[ProjectsLayout] Failed to load projects for sidebar',
        expect.any(Error),
      );
      expect(layoutClientSpy).toHaveBeenLastCalledWith({ initialProjectPage: null });
      expect(screen.getByText('Portal en degradación')).toBeInTheDocument();
    } finally {
      console.error = originalConsoleError;
    }
  });
});
