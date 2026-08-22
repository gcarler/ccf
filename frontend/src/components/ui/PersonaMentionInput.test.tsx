import React, { useState } from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import PersonaMentionInput from './PersonaMentionInput';
import type { PersonaBusqueda } from '@/lib/filtroAPersonas';

const PERSONAS: PersonaBusqueda[] = [
    { id: 'p1', username: 'luisricardo', nombre_completo: 'Luis Ricardo Meza', email: 'luis.meza@ccf.org', church_role: 'Pastor' },
    { id: 'p2', username: 'mariagomez', nombre_completo: 'Ana María Gómez', email: 'ana@ccf.org', church_role: 'Líder de Grupo' },
    { id: 'p3', username: 'mariadelcarmen', nombre_completo: 'María Del Carmen López', email: 'maria.lopez@ccf.org' },
    { id: 'p4', nombre_completo: 'Juan Pérez', email: 'juan@ccf.org' }, // sin cuenta → nunca aparece con @
];

function setup(overrides: Partial<React.ComponentProps<typeof PersonaMentionInput>> = {}) {
    const onChange = vi.fn();
    function Harness() {
        const [value, setValue] = useState('');
        return (
            <PersonaMentionInput
                personas={PERSONAS}
                value={value}
                onChange={(v, m) => {
                    setValue(v);
                    onChange(v, m);
                }}
                {...overrides}
            />
        );
    }
    render(<Harness />);
    const textarea = screen.getByRole('textbox');
    return { onChange, textarea };
}

function type(textarea: HTMLElement, value: string) {
    fireEvent.change(textarea, { target: { value, selectionStart: value.length, selectionEnd: value.length } });
}

describe('PersonaMentionInput', () => {
    it('opens the dropdown when typing @ and matches by username', async () => {
        const { textarea } = setup();
        type(textarea, '@luis');
        await waitFor(() => expect(screen.getByRole('listbox')).toBeInTheDocument());
        expect(screen.getByText('@luisricardo')).toBeInTheDocument();
        expect(screen.queryByText('@mariagomez')).not.toBeInTheDocument();
        // Personas sin cuenta no aparecen en menciones.
        expect(screen.queryByText('Juan Pérez')).not.toBeInTheDocument();
    });

    it('matches username by prefix', async () => {
        const { textarea } = setup();
        type(textarea, '@mariadel');
        await waitFor(() => expect(screen.getByRole('listbox')).toBeInTheDocument());
        expect(screen.getByText('@mariadelcarmen')).toBeInTheDocument();
    });

    it('does NOT match by name when typing @', async () => {
        const { textarea } = setup();
        type(textarea, '@gomez');
        await waitFor(() => expect(screen.queryByRole('listbox')).not.toBeInTheDocument());
    });

    it('closes the dropdown when the query contains a space', async () => {
        const { textarea } = setup();
        type(textarea, '@luis ricardo');
        await waitFor(() => expect(screen.queryByRole('listbox')).not.toBeInTheDocument());
    });

    it('selects a result on click and inserts @username', async () => {
        const { textarea, onChange } = setup();
        type(textarea, 'Hola @luis');
        await waitFor(() => expect(screen.getByRole('listbox')).toBeInTheDocument());
        fireEvent.click(screen.getByText('@luisricardo'));
        expect(onChange).toHaveBeenLastCalledWith(
            'Hola @luisricardo ',
            [{ id: 'p1', username: 'luisricardo', nombre_completo: 'Luis Ricardo Meza', email: 'luis.meza@ccf.org', church_role: 'Pastor' }]
        );
        await waitFor(() => expect(screen.queryByRole('listbox')).not.toBeInTheDocument());
    });

    it('selects a result with Enter and navigates with arrows', async () => {
        const { textarea, onChange } = setup();
        type(textarea, '@ma');
        await waitFor(() => expect(screen.getByRole('listbox')).toBeInTheDocument());
        // Sin navegación: Enter selecciona el primero (mariagomez).
        fireEvent.keyDown(textarea, { key: 'Enter' });
        expect(onChange).toHaveBeenLastCalledWith(
            '@mariagomez ',
            [{ id: 'p2', username: 'mariagomez', nombre_completo: 'Ana María Gómez', email: 'ana@ccf.org', church_role: 'Líder de Grupo' }]
        );

        type(textarea, '@ma');
        await waitFor(() => expect(screen.getByRole('listbox')).toBeInTheDocument());
        // ArrowDown mueve al segundo (mariadelcarmen).
        fireEvent.keyDown(textarea, { key: 'ArrowDown' });
        fireEvent.keyDown(textarea, { key: 'Enter' });
        expect(onChange).toHaveBeenLastCalledWith(
            '@mariadelcarmen ',
            [
                { id: 'p2', username: 'mariagomez', nombre_completo: 'Ana María Gómez', email: 'ana@ccf.org', church_role: 'Líder de Grupo' },
                { id: 'p3', username: 'mariadelcarmen', nombre_completo: 'María Del Carmen López', email: 'maria.lopez@ccf.org' },
            ]
        );
    });

    it('closes the dropdown with Escape', async () => {
        const { textarea } = setup();
        type(textarea, '@luis');
        await waitFor(() => expect(screen.getByRole('listbox')).toBeInTheDocument());
        fireEvent.keyDown(textarea, { key: 'Escape' });
        await waitFor(() => expect(screen.queryByRole('listbox')).not.toBeInTheDocument());
    });

    it('deduplicates repeated mentions of the same user', async () => {
        const { textarea, onChange } = setup();
        type(textarea, '@luis');
        await waitFor(() => expect(screen.getByRole('listbox')).toBeInTheDocument());
        fireEvent.click(screen.getByText('@luisricardo'));
        type(textarea, '@luisricardo @luis');
        await waitFor(() => expect(screen.getByRole('listbox')).toBeInTheDocument());
        fireEvent.click(screen.getByText('@luisricardo'));
        const menciones = onChange.mock.calls.map((call) => call[1]);
        expect(menciones[menciones.length - 1].length).toBe(1);
        expect(menciones[menciones.length - 1][0].id).toBe('p1');
    });
});
