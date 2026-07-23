import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { axe } from 'jest-axe';
import PersonaSelect from './PersonaSelect';
import * as AuthContext from '@/context/AuthContext';
import * as HttpModule from '@/lib/http';

const mockApiFetch = vi.spyOn(HttpModule, 'apiFetch');

describe('PersonaSelect', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockApiFetch.mockResolvedValue([]);
        vi.spyOn(AuthContext, 'useAuth').mockReturnValue({
            token: 'test-token',
        } as any);
    });

    it('renders placeholder when no value is selected', async () => {
        render(<PersonaSelect value={null} onChange={() => {}} />);
        await waitFor(() => expect(screen.getByText('Sin asignar')).toBeInTheDocument());
        await waitFor(() => expect(mockApiFetch).toHaveBeenCalledWith('/crm/personas', { token: 'test-token' }));
    });

    it('opens dropdown and displays personas after fetching', async () => {
        mockApiFetch.mockResolvedValueOnce([
            { id: '1', first_name: 'Juan', last_name: 'Pérez', church_role: 'Pastor' },
            { id: '2', first_name: 'María', last_name: 'Gómez' },
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
        mockApiFetch.mockResolvedValueOnce([{ id: '1', first_name: 'Juan', last_name: 'Pérez' }]);
        const handleChange = vi.fn();

        render(<PersonaSelect value={null} onChange={handleChange} />);
        fireEvent.click(screen.getByRole('button', { name: /sin asignar/i }));

        await waitFor(() => expect(screen.getByText('Juan Pérez')).toBeInTheDocument());
        fireEvent.click(screen.getByText('Juan Pérez'));

        expect(handleChange).toHaveBeenCalledWith('1');
        expect(handleChange).toHaveBeenCalledTimes(1);
    });

    it('filters personas when typing in the search input', async () => {
        mockApiFetch.mockResolvedValueOnce([
            { id: '1', first_name: 'Juan', last_name: 'Pérez' },
            { id: '2', first_name: 'María', last_name: 'Gómez' },
        ]);

        render(<PersonaSelect value={null} onChange={() => {}} />);
        fireEvent.click(screen.getByRole('button', { name: /sin asignar/i }));

        await waitFor(() => expect(screen.getByText('Juan Pérez')).toBeInTheDocument());

        const input = screen.getByPlaceholderText('Buscar persona...');
        fireEvent.change(input, { target: { value: 'maría' } });

        await waitFor(() => {
            expect(screen.queryByText('Juan Pérez')).not.toBeInTheDocument();
            expect(screen.getByText('María Gómez')).toBeInTheDocument();
        });
    });

    it('shows the selected persona name when a value is provided', async () => {
        mockApiFetch.mockResolvedValueOnce([{ id: '1', first_name: 'Juan', last_name: 'Pérez' }]);
        render(<PersonaSelect value="1" onChange={() => {}} />);

        await waitFor(() => expect(screen.getByText('Juan Pérez')).toBeInTheDocument());
    });

    it('has no accessibility violations', async () => {
        mockApiFetch.mockResolvedValueOnce([{ id: '1', first_name: 'Juan', last_name: 'Pérez' }]);
        const { container } = render(<PersonaSelect value={null} onChange={() => {}} />);
        const results = await axe(container);
        expect(results.violations).toHaveLength(0);
    });
});
