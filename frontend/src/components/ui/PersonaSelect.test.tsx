import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { axe } from 'jest-axe';
import PersonaSelect from './PersonaSelect';
import * as AuthContext from '@/context/AuthContext';
import * as HttpModule from '@/lib/http';
import { createMockPersonaSelectOption } from '@/test-utils/factories';

const mockApiFetch = vi.spyOn(HttpModule, 'apiFetch');

describe('PersonaSelect (Reactive Server-side Search QA-002)', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockApiFetch.mockResolvedValue([]);
        vi.spyOn(AuthContext, 'useAuth').mockReturnValue({
            token: 'test-token',
        } as Partial<AuthContext.AuthContextType> as AuthContext.AuthContextType);
    });

    it('renders placeholder when no value is selected and queries initial personas', async () => {
        render(<PersonaSelect value={null} onChange={() => {}} />);
        await waitFor(() => expect(screen.getByText('Sin asignar')).toBeInTheDocument());
        await waitFor(() =>
            expect(mockApiFetch).toHaveBeenCalledWith('/crm/personas?limit=1000&skip=0', { token: 'test-token' })
        );
    });

    it('opens dropdown and displays personas after fetching', async () => {
        mockApiFetch.mockResolvedValueOnce([
            createMockPersonaSelectOption({ id: '1', first_name: 'Juan', last_name: 'Pérez', church_role: 'Pastor' }),
            createMockPersonaSelectOption({ id: '2', first_name: 'María', last_name: 'Gómez' }),
        ]);

        render(<PersonaSelect value={null} onChange={() => {}} />);
        fireEvent.click(screen.getByRole('button', { name: /sin asignar/i }));

        await waitFor(() => {
            expect(screen.getByText('Juan Pérez')).toBeInTheDocument();
            expect(screen.getByText('María Gómez')).toBeInTheDocument();
            expect(screen.getByText('Pastor')).toBeInTheDocument();
        });
    });

    it('calls onChange with the selected persona id', async () => {
        mockApiFetch.mockResolvedValueOnce([
            createMockPersonaSelectOption({ id: '1', first_name: 'Juan', last_name: 'Pérez' }),
        ]);
        const handleChange = vi.fn();

        render(<PersonaSelect value={null} onChange={handleChange} />);
        fireEvent.click(screen.getByRole('button', { name: /sin asignar/i }));

        await waitFor(() => expect(screen.getByText('Juan Pérez')).toBeInTheDocument());
        fireEvent.click(screen.getByText('Juan Pérez'));

        expect(handleChange).toHaveBeenCalledWith('1');
        expect(handleChange).toHaveBeenCalledTimes(1);
    });

    it('executes server-side search with debounce querying /crm/personas?search=...&limit=1000', async () => {
        // Initial list
        mockApiFetch.mockImplementation(async (endpoint: string) => {
            if (endpoint.includes('search=Laury')) {
                return [
                    createMockPersonaSelectOption({
                        id: 'laury-uuid',
                        first_name: 'Laury',
                        last_name: 'Méndez',
                        church_role: 'Líder',
                    }),
                ];
            }
            return [
                createMockPersonaSelectOption({ id: '1', first_name: 'Alberto', last_name: 'Álvarez' }),
                createMockPersonaSelectOption({ id: '2', first_name: 'Beatriz', last_name: 'Bravo' }),
            ];
        });

        render(<PersonaSelect value={null} onChange={() => {}} />);
        fireEvent.click(screen.getByRole('button', { name: /sin asignar/i }));

        await waitFor(() => expect(screen.getByText('Alberto Álvarez')).toBeInTheDocument());

        const input = screen.getByPlaceholderText('Buscar persona...');
        fireEvent.change(input, { target: { value: 'Laury' } });

        // Server-side debounced search should be called with encoded query
        await waitFor(
            () => {
                expect(mockApiFetch).toHaveBeenCalledWith(
                    '/crm/personas?limit=1000&skip=0&search=Laury',
                    { token: 'test-token' }
                );
            },
            { timeout: 1500 }
        );

        // Results should render Laury Méndez from server-side query
        await waitFor(() => {
            expect(screen.getByText('Laury Méndez')).toBeInTheDocument();
            expect(screen.queryByText('Alberto Álvarez')).not.toBeInTheDocument();
        });
    });

    it('displays subtle loading spinner inside search input while fetching', async () => {
        let resolveSearch: (val: unknown) => void = () => {};
        const searchPromise = new Promise<unknown>((resolve) => {
            resolveSearch = resolve;
        });

        mockApiFetch.mockImplementation((endpoint: string) => {
            if (endpoint.includes('search=Carlos')) {
                return searchPromise;
            }
            return Promise.resolve([]);
        });

        render(<PersonaSelect value={null} onChange={() => {}} />);
        fireEvent.click(screen.getByRole('button', { name: /sin asignar/i }));

        const input = screen.getByPlaceholderText('Buscar persona...');
        fireEvent.change(input, { target: { value: 'Carlos' } });

        await waitFor(
            () => {
                expect(screen.getByTestId('persona-search-spinner')).toBeInTheDocument();
            },
            { timeout: 1500 }
        );

        // Resolve search promise
        await act(async () => {
            resolveSearch([
                createMockPersonaSelectOption({ id: '3', first_name: 'Carlos', last_name: 'Castillo' }),
            ]);
        });

        await waitFor(() => {
            expect(screen.queryByTestId('persona-search-spinner')).not.toBeInTheDocument();
            expect(screen.getByText('Carlos Castillo')).toBeInTheDocument();
        });
    });

    it('fetches and preserves selected persona details when value is not in initial list', async () => {
        // Initial list has other people
        mockApiFetch.mockImplementation(async (endpoint: string) => {
            if (endpoint === '/crm/personas/laury-uuid') {
                return createMockPersonaSelectOption({
                    id: 'laury-uuid',
                    first_name: 'Laury',
                    last_name: 'Méndez',
                    church_role: 'Pastora',
                });
            }
            return [
                createMockPersonaSelectOption({ id: '1', first_name: 'Alberto', last_name: 'Álvarez' }),
            ];
        });

        render(<PersonaSelect value="laury-uuid" onChange={() => {}} />);

        // Button should display Laury Méndez even if she was not in the initial 50 list
        await waitFor(() => {
            expect(screen.getByText('Laury Méndez')).toBeInTheDocument();
        });
    });

    it('allows clearing selection back to placeholder with "Sin asignar"', async () => {
        const handleChange = vi.fn();
        mockApiFetch.mockResolvedValueOnce([
            createMockPersonaSelectOption({ id: '1', first_name: 'Juan', last_name: 'Pérez' }),
        ]);

        render(<PersonaSelect value="1" onChange={handleChange} />);
        await waitFor(() => expect(screen.getByText('Juan Pérez')).toBeInTheDocument());

        fireEvent.click(screen.getByRole('button', { name: /juan pérez/i }));
        await waitFor(() => expect(screen.getByText('Sin asignar')).toBeInTheDocument());

        fireEvent.click(screen.getByText('Sin asignar'));
        expect(handleChange).toHaveBeenCalledWith(null);
    });

    it('handles offline or network failure gracefully without crashing', async () => {
        const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
        mockApiFetch.mockRejectedValueOnce(new Error('Network error / offline'));

        render(<PersonaSelect value={null} onChange={() => {}} />);
        fireEvent.click(screen.getByRole('button', { name: /sin asignar/i }));

        await waitFor(() => {
            expect(screen.getByText('No se encontraron personas')).toBeInTheDocument();
        });
        consoleError.mockRestore();
    });

    it('has no accessibility violations', async () => {
        mockApiFetch.mockResolvedValueOnce([
            createMockPersonaSelectOption({ id: '1', first_name: 'Juan', last_name: 'Pérez' }),
        ]);
        const { container } = render(<PersonaSelect value={null} onChange={() => {}} />);
        const results = await axe(container);
        expect(results.violations).toHaveLength(0);
    });

    it('keeps search controls outside a named listbox when the picker is open', async () => {
        mockApiFetch.mockResolvedValueOnce([
            createMockPersonaSelectOption({ id: '1', first_name: 'Juan', last_name: 'Pérez' }),
        ]);
        const { container } = render(<PersonaSelect value={null} onChange={() => {}} />);
        fireEvent.click(screen.getByRole('button', { name: /sin asignar/i }));

        const listbox = await screen.findByRole('listbox', { name: 'Personas disponibles' });
        expect(await screen.findByText('Juan Pérez')).toBeInTheDocument();
        expect(listbox).not.toContainElement(screen.getByRole('textbox', { name: 'Buscar persona' }));
        expect(screen.getByRole('button', { name: /sin asignar/i })).toHaveAttribute('aria-controls', 'persona-select-options');
        expect((await axe(container)).violations).toEqual([]);
    });

    it('consumes Escape, restores trigger focus, and supports selecting by Tab and Enter', async () => {
        const onChange = vi.fn();
        const user = userEvent.setup();
        render(<PersonaSelect value={null} onChange={onChange} />);

        const trigger = screen.getByRole('button', { name: /sin asignar/i });
        await user.click(trigger);
        const search = screen.getByRole('textbox', { name: 'Buscar persona' });
        expect(search).toHaveFocus();

        await user.keyboard('{Escape}');
        expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
        expect(trigger).toHaveFocus();

        await user.click(trigger);
        await screen.findByRole('option', { name: /sin asignar/i });
        await user.tab();
        expect(screen.getByRole('option', { name: /sin asignar/i })).toHaveFocus();
        await user.keyboard('{Enter}');

        expect(onChange).toHaveBeenCalledWith(null);
        expect(trigger).toHaveFocus();
        expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
    });

    it('appends the next page when clicking "Cargar más personas" instead of replacing results', async () => {
        const pageOne = Array.from({ length: 1000 }, (_, i) =>
            createMockPersonaSelectOption({ id: `p1-${i}`, first_name: `Alonso${i}`, last_name: 'Zapata' })
        );
        const pageTwo = [
            createMockPersonaSelectOption({ id: 'p2-0', first_name: 'Lucía', last_name: 'Ramírez' }),
            createMockPersonaSelectOption({ id: 'p2-1', first_name: 'Etzel', last_name: 'Iriarte' }),
        ];
        mockApiFetch.mockImplementation(async (endpoint: string) => {
            if (endpoint.includes('skip=1000')) return pageTwo;
            return pageOne;
        });

        render(<PersonaSelect value={null} onChange={() => {}} />);
        fireEvent.click(screen.getByRole('button', { name: /sin asignar/i }));

        await waitFor(() => expect(mockApiFetch).toHaveBeenCalledWith('/crm/personas?limit=1000&skip=0', { token: 'test-token' }));

        const loadMore = await screen.findByTestId('persona-load-more');
        fireEvent.click(loadMore);

        await waitFor(() =>
            expect(mockApiFetch).toHaveBeenCalledWith('/crm/personas?limit=1000&skip=1000', { token: 'test-token' })
        );
        await waitFor(() => {
            expect(screen.getByText('Lucía Ramírez')).toBeInTheDocument();
            expect(screen.getByText('Etzel Iriarte')).toBeInTheDocument();
            // Las personas de la página 1 siguen visibles tras el append
            expect(screen.getByText('Alonso0 Zapata')).toBeInTheDocument();
        });
        // La segunda página es corta: el botón de paginación desaparece
        await waitFor(() => expect(screen.queryByTestId('persona-load-more')).not.toBeInTheDocument());
    }, 15000);

    it('shows the load-more button only when the server reports a full page', async () => {
        mockApiFetch.mockResolvedValueOnce([
            createMockPersonaSelectOption({ id: '1', first_name: 'Juan', last_name: 'Pérez' }),
        ]);

        render(<PersonaSelect value={null} onChange={() => {}} />);
        fireEvent.click(screen.getByRole('button', { name: /sin asignar/i }));

        await waitFor(() => expect(screen.getByText('Juan Pérez')).toBeInTheDocument());
        expect(screen.queryByTestId('persona-load-more')).not.toBeInTheDocument();
    });

    it('falls back to /projects/assignee-candidates when the primary listing fails', async () => {
        const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
        mockApiFetch.mockImplementation(async (endpoint: string) => {
            if (endpoint.startsWith('/crm/personas?')) {
                throw new Error('500 upstream');
            }
            if (endpoint.startsWith('/projects/assignee-candidates?')) {
                return [createMockPersonaSelectOption({ id: 'fb-1', first_name: 'Lucía', last_name: 'Ramírez' })];
            }
            return [];
        });

        render(<PersonaSelect value={null} onChange={() => {}} />);
        fireEvent.click(screen.getByRole('button', { name: /sin asignar/i }));

        await waitFor(() =>
            expect(mockApiFetch).toHaveBeenCalledWith('/projects/assignee-candidates?limit=1000', { token: 'test-token' })
        );
        expect(await screen.findByText('Lucía Ramírez')).toBeInTheDocument();
        expect(screen.queryByTestId('persona-load-error')).not.toBeInTheDocument();
        consoleError.mockRestore();
    });

    it('shows the retriable error state when both the listing and the fallback fail', async () => {
        const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
        mockApiFetch.mockRejectedValue(new Error('Offline'));

        render(<PersonaSelect value={null} onChange={() => {}} />);
        fireEvent.click(screen.getByRole('button', { name: /sin asignar/i }));

        await screen.findByRole('button', { name: 'Reintentar' });
        mockApiFetch.mockResolvedValueOnce([
            createMockPersonaSelectOption({ id: 'retry-1', first_name: 'Etzel', last_name: 'Iriarte' }),
        ]);
        // Se re-consulta el botón para actuar sobre el nodo vivo: el panel de
        // error se recrea en cada render y el nodo obtenido puede quedar
        // desmontado (isConnected=false) en el momento del click.
        fireEvent.click(screen.getByRole('button', { name: 'Reintentar' }));

        await waitFor(() => expect(screen.getByText('Etzel Iriarte')).toBeInTheDocument());
        expect(screen.queryByTestId('persona-load-error')).not.toBeInTheDocument();
        consoleError.mockRestore();
    });

    it('prioritizes people whose name starts with the search term on the client', async () => {
        // El servidor devuelve el orden alfabético plano; con el término 'LUC'
        // 'Lucía Ramírez' (Tier 0) encabeza antes que 'Ana Lucas' (Tier 1) y 'Mila De Lucas' (Tier 2).
        const serverOrder = [
            createMockPersonaSelectOption({ id: 'c3', first_name: 'Ana', last_name: 'Lucas' }),
            createMockPersonaSelectOption({ id: 'c1', first_name: 'Lucía', last_name: 'Ramírez' }),
            createMockPersonaSelectOption({ id: 'c2', first_name: 'Mila', last_name: 'De Lucas' }),
        ];
        mockApiFetch.mockImplementation(async () => serverOrder);

        render(<PersonaSelect value={null} onChange={() => {}} />);
        fireEvent.click(screen.getByRole('button', { name: /sin asignar/i }));

        await waitFor(() => expect(screen.getByText('Lucía Ramírez')).toBeInTheDocument());
        const input = screen.getByRole('textbox', { name: 'Buscar persona' });
        fireEvent.change(input, { target: { value: 'LUC' } });

        // El backend ya ordena por prefijo; el cliente lo re-afirma para términos
        // compuestos. 'LUC' (case-insensitive) empieza en 'Lucía Ramírez'.
        await waitFor(() => {
            const options = screen.getAllByRole('option');
            expect(options.length).toBeGreaterThanOrEqual(4); // "Sin asignar" + 3 personas
            const names = options.map((o) => o.textContent ?? '');
            expect(names[1]).toContain('Lucía Ramírez'); // [0] es "Sin asignar"
            expect(names[2]).toContain('Ana Lucas');
            expect(names[3]).toContain('Mila De Lucas');
        });
    });

    it('automatically loads next page when scrolling near the bottom of the options container', async () => {
        const pageOne = Array.from({ length: 1000 }, (_, i) =>
            createMockPersonaSelectOption({ id: `scroll-p1-${i}`, first_name: `Persona${i}`, last_name: 'Test' })
        );
        const pageTwo = [
            createMockPersonaSelectOption({ id: 'scroll-p2-0', first_name: 'Lucía', last_name: 'Scroll' }),
        ];
        mockApiFetch.mockImplementation(async (endpoint: string) => {
            if (endpoint.includes('skip=1000')) return pageTwo;
            return pageOne;
        });

        render(<PersonaSelect value={null} onChange={() => {}} />);
        fireEvent.click(screen.getByRole('button', { name: /sin asignar/i }));

        await waitFor(() => expect(screen.getByText('Persona0 Test')).toBeInTheDocument());

        const listbox = screen.getByRole('listbox', { name: 'Personas disponibles' });
        Object.defineProperty(listbox, 'scrollHeight', { value: 1000, configurable: true });
        Object.defineProperty(listbox, 'clientHeight', { value: 200, configurable: true });
        Object.defineProperty(listbox, 'scrollTop', { value: 760, configurable: true });
        fireEvent.scroll(listbox);

        await waitFor(() => expect(screen.getByText('Lucía Scroll')).toBeInTheDocument());
        expect(mockApiFetch).toHaveBeenCalledWith(
            expect.stringContaining('skip=1000'),
            expect.objectContaining({ token: 'test-token' })
        );
    }, 15000);

    it('prioritizes names starting with L or Ca without allowing last names like Lopez to displace them', async () => {
        const mixed = [
            createMockPersonaSelectOption({ id: '1', first_name: 'Ana', last_name: 'López' }),
            createMockPersonaSelectOption({ id: '2', first_name: 'Carlos', last_name: 'Alba' }),
            createMockPersonaSelectOption({ id: '3', first_name: 'Laura', last_name: 'Zapata' }),
            createMockPersonaSelectOption({ id: '4', first_name: 'Mila', last_name: 'Ospina' }),
        ];
        mockApiFetch.mockResolvedValue(mixed);

        render(<PersonaSelect value={null} onChange={() => {}} />);
        fireEvent.click(screen.getByRole('button', { name: /sin asignar/i }));

        await waitFor(() => expect(screen.getByText('Laura Zapata')).toBeInTheDocument());
        const input = screen.getByRole('textbox', { name: 'Buscar persona' });

        // Al buscar 'l', Laura Zapata (Tier 0) debe encabezar antes que Ana López (Tier 1) y Mila Ospina (Tier 2)
        fireEvent.change(input, { target: { value: 'l' } });

        await waitFor(() => {
            const options = screen.getAllByRole('option');
            const texts = options.map((o) => o.textContent ?? '');
            const lauraIndex = texts.findIndex((t) => t.includes('Laura Zapata'));
            const anaIndex = texts.findIndex((t) => t.includes('Ana López'));
            const milaIndex = texts.findIndex((t) => t.includes('Mila Ospina'));
            expect(lauraIndex).toBeGreaterThan(0);
            expect(lauraIndex).toBeLessThan(anaIndex);
            expect(anaIndex).toBeLessThan(milaIndex);
        });
    });
});
