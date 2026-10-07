import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
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
