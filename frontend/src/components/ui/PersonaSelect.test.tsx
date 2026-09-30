import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
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
            expect(mockApiFetch).toHaveBeenCalledWith('/crm/personas?limit=50', { token: 'test-token' })
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

    it('executes server-side search with debounce querying /crm/personas?search=...&limit=50', async () => {
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
                    '/crm/personas?search=Laury&limit=50',
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
        let resolveSearch: (val: any) => void = () => {};
        const searchPromise = new Promise((resolve) => {
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
});
