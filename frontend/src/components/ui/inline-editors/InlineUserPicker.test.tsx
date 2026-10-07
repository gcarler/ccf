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
        query: { search: 'Lucía', limit: 50 },
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
});
