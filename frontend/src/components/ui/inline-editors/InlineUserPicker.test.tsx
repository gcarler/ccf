import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { InlineUserPicker } from './InlineUserPicker';
import * as AuthContext from '@/context/AuthContext';
import * as HttpModule from '@/lib/http';

const mockApiFetch = vi.spyOn(HttpModule, 'apiFetch');

describe('InlineUserPicker', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockApiFetch.mockResolvedValue([]);
    vi.spyOn(AuthContext, 'useAuth').mockReturnValue({
      token: 'test-token',
    } as Partial<AuthContext.AuthContextType> as AuthContext.AuthContextType);
    vi.spyOn(AuthContext, 'useOptionalAuth').mockReturnValue({
      token: 'test-token',
    } as Partial<AuthContext.AuthContextType> as AuthContext.AuthContextType);
  });

  it('uses the supplied Projects endpoint and server-side search parameter', async () => {
    mockApiFetch.mockImplementation(async (_endpoint, options) => {
      if (options?.query?.search === 'Lucía') {
        return [{ id: 'persona-uuid', nombre_completo: 'Lucía Ramírez' }] as never;
      }
      return [] as never;
    });
    const onChange = vi.fn();

    render(
      <InlineUserPicker
        endpoint="/projects/assignee-candidates"
        value={null}
        onChange={onChange}
      />
    );
    fireEvent.click(screen.getByRole('button', { name: 'Selector de persona asignada' }));
    const input = await screen.findByRole('textbox', { name: 'Buscar persona asignable' });
    fireEvent.change(input, { target: { value: 'Lucía' } });

    const candidate = await screen.findByRole('button', { name: /Lucía Ramírez/ }, { timeout: 2000 });

    expect(mockApiFetch).toHaveBeenCalledWith(
      '/projects/assignee-candidates',
      expect.objectContaining({
        token: 'test-token',
        query: { search: 'Lucía', limit: 1000, skip: 0 },
      })
    );
    expect(mockApiFetch).not.toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({ query: expect.objectContaining({ q: 'Lucía' }) })
    );
    fireEvent.click(candidate);
    expect(onChange).toHaveBeenCalledWith('persona-uuid', 'Lucía Ramírez');
  });

  it('recovers from candidate search failure with an explicit retry', async () => {
    mockApiFetch
      .mockRejectedValueOnce(new Error('Offline'))
      .mockResolvedValueOnce([{ id: 'persona-uuid', nombre_completo: 'Lucía Ramírez' }] as never);

    render(
      <InlineUserPicker
        endpoint="/projects/assignee-candidates"
        value={null}
        onChange={vi.fn()}
      />
    );
    fireEvent.click(screen.getByRole('button', { name: 'Selector de persona asignada' }));

    const retry = await screen.findByRole('button', { name: 'Reintentar' });
    fireEvent.click(retry);

    expect(await screen.findByRole('button', { name: /Lucía Ramírez/ })).toBeInTheDocument();
  });

  it('shows an empty state when the server returns no matching candidates', async () => {
    render(
      <InlineUserPicker
        endpoint="/projects/assignee-candidates"
        value={null}
        onChange={vi.fn()}
      />
    );
    fireEvent.click(screen.getByRole('button', { name: 'Selector de persona asignada' }));

    expect(await screen.findByText('Sin resultados')).toBeInTheDocument();
  });

  it('keeps the clear-assignment action available when search has no results', async () => {
    mockApiFetch.mockImplementation(async (endpoint) => {
      if (endpoint.endsWith('/persona-uuid')) {
        return { id: 'persona-uuid', nombre_completo: 'Lucía Ramírez' } as never;
      }
      return [] as never;
    });
    const onChange = vi.fn();

    render(
      <InlineUserPicker
        endpoint="/projects/assignee-candidates"
        value="persona-uuid"
        onChange={onChange}
      />
    );
    fireEvent.click(screen.getByRole('button', { name: 'Selector de persona asignada' }));

    const clearButton = await screen.findByRole('button', { name: 'Quitar asignación' });
    expect(screen.getByText('Sin resultados')).toBeInTheDocument();
    fireEvent.click(clearButton);

    expect(onChange).toHaveBeenCalledWith(null, null);
  });

  it('resolves a selected persona through the supplied scoped endpoint', async () => {
    mockApiFetch.mockImplementation(async (endpoint) => {
      if (endpoint === '/projects/assignee-candidates/persona-uuid') {
        return { id: 'persona-uuid', nombre_completo: 'Lucía Ramírez' } as never;
      }
      return [] as never;
    });

    render(
      <InlineUserPicker
        endpoint="/projects/assignee-candidates"
        value="persona-uuid"
        onChange={vi.fn()}
      />
    );

    await waitFor(() => expect(screen.getByTitle('Asignado a Lucía Ramírez')).toBeInTheDocument());
    expect(mockApiFetch).toHaveBeenCalledWith(
      '/projects/assignee-candidates/persona-uuid',
      expect.objectContaining({ method: 'GET', token: 'test-token' })
    );
  });

  it('appends the next page when clicking "Cargar más personas"', async () => {
    const pageOne = Array.from({ length: 1000 }, (_, i) => ({
      id: `p1-${i}`,
      first_name: `Lucía${i}`,
      last_name: 'Ramírez',
    }));
    const pageTwo = [{ id: 'p2-0', first_name: 'Etzel', last_name: 'Iriarte' }];
    mockApiFetch.mockImplementation(async (_endpoint, options) => {
      if (options?.query?.skip === 1000) return pageTwo as never;
      return pageOne as never;
    });

    render(<InlineUserPicker endpoint="/projects/assignee-candidates" value={null} onChange={vi.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: 'Selector de persona asignada' }));

    const loadMore = await screen.findByTestId('userpicker-load-more');
    fireEvent.click(loadMore);

    await waitFor(() => expect(screen.getByText('Etzel Iriarte')).toBeInTheDocument());
    expect(screen.getByText('Lucía0 Ramírez')).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByTestId('userpicker-load-more')).not.toBeInTheDocument());
  });

  it('does not offer pagination when the listing is shorter than a full page', async () => {
    mockApiFetch.mockResolvedValueOnce([{ id: 'persona-uuid', nombre_completo: 'Lucía Ramírez' }] as never);

    render(<InlineUserPicker endpoint="/projects/assignee-candidates" value={null} onChange={vi.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: 'Selector de persona asignada' }));

    await screen.findByRole('button', { name: /Lucía Ramírez/ });
    expect(screen.queryByTestId('userpicker-load-more')).not.toBeInTheDocument();
  });

  it('automatically loads next page when scrolling near the bottom of the list container', async () => {
    const pageOne = Array.from({ length: 1000 }, (_, i) => ({
      id: `p1-${i}`,
      first_name: `Persona${i}`,
      last_name: 'Test',
    }));
    const pageTwo = [{ id: 'p2-0', first_name: 'Lucía', last_name: 'Scroll' }];
    mockApiFetch.mockImplementation(async (_endpoint, options) => {
      if (options?.query?.skip === 1000) return pageTwo as never;
      return pageOne as never;
    });

    render(<InlineUserPicker endpoint="/projects/assignee-candidates" value={null} onChange={vi.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: 'Selector de persona asignada' }));

    await waitFor(() => expect(screen.getByText('Persona0 Test')).toBeInTheDocument());

    const loadMoreBtn = await screen.findByTestId('userpicker-load-more');
    const scrollContainer = loadMoreBtn.parentElement as HTMLDivElement;
    Object.defineProperty(scrollContainer, 'scrollHeight', { value: 1000, configurable: true });
    Object.defineProperty(scrollContainer, 'clientHeight', { value: 200, configurable: true });
    Object.defineProperty(scrollContainer, 'scrollTop', { value: 760, configurable: true });
    fireEvent.scroll(scrollContainer);

    await waitFor(() => expect(screen.getByText('Lucía Scroll')).toBeInTheDocument());
    expect(mockApiFetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        query: expect.objectContaining({ skip: 1000 }),
      })
    );
  });

  it('prioritizes names starting with L or Ca on client search without displacing by last names', async () => {
    const candidates = [
      { id: '1', nombre_completo: 'Ana López' },
      { id: '2', nombre_completo: 'Carlos Alba' },
      { id: '3', nombre_completo: 'Laura Zapata' },
      { id: '4', nombre_completo: 'Mila Ospina' },
    ];
    mockApiFetch.mockResolvedValue(candidates as never);

    render(<InlineUserPicker endpoint="/projects/assignee-candidates" value={null} onChange={vi.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: 'Selector de persona asignada' }));

    await waitFor(() => expect(screen.getByText('Laura Zapata')).toBeInTheDocument());
    const input = screen.getByRole('textbox', { name: 'Buscar persona asignable' });

    fireEvent.change(input, { target: { value: 'l' } });

    await waitFor(() => {
      const buttons = screen.getAllByRole('button');
      const texts = buttons.map((b) => b.textContent ?? '');
      const lauraIndex = texts.findIndex((t) => t.includes('Laura Zapata'));
      const anaIndex = texts.findIndex((t) => t.includes('Ana López'));
      const milaIndex = texts.findIndex((t) => t.includes('Mila Ospina'));
      expect(lauraIndex).toBeGreaterThan(-1);
      expect(lauraIndex).toBeLessThan(anaIndex);
      expect(anaIndex).toBeLessThan(milaIndex);
    });
  });
});
