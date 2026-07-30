import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { axe } from 'jest-axe';
import { NewConversationDrawer } from './NewConversationDrawer';
import type { SearchedUser } from '../_hooks/useUserSearch';

const sampleUsers: SearchedUser[] = [
    { id: 'u1', username: 'ana', email: 'ana@test.com', avatar_url: null },
    { id: 'u2', username: 'beto', email: 'beto@test.com', avatar_url: null },
];

function renderDrawer(props: Partial<React.ComponentProps<typeof NewConversationDrawer>> = {}) {
    return render(
        <NewConversationDrawer
            isOpen={true}
            onClose={vi.fn()}
            query=""
            onQueryChange={vi.fn()}
            results={[]}
            loading={false}
            error={null}
            creating={false}
            onCreate={vi.fn()}
            {...props}
        />
    );
}

describe('NewConversationDrawer', () => {
    it('renders title and search input', () => {
        renderDrawer();
        expect(screen.getByText('Nueva conversación')).toBeInTheDocument();
        expect(screen.getByLabelText('Buscar usuario para nueva conversación')).toBeInTheDocument();
    });

    it('shows loading state', () => {
        renderDrawer({ loading: true });
        expect(screen.getByText('Buscando...')).toBeInTheDocument();
    });

    it('shows error message', () => {
        renderDrawer({ error: 'Error al buscar usuarios' });
        expect(screen.getByText('Error al buscar usuarios')).toBeInTheDocument();
    });

    it('shows prompt when query is below minimum length', () => {
        renderDrawer({ query: 'a' });
        expect(screen.getByText('Escribe para buscar')).toBeInTheDocument();
        expect(screen.getByText('Mínimo 2 caracteres')).toBeInTheDocument();
    });

    it('shows no results when query is long enough but results are empty', () => {
        renderDrawer({ query: 'zzz' });
        expect(screen.getByText('Sin resultados')).toBeInTheDocument();
    });

    it('renders user results and calls onCreate when a result is clicked', () => {
        const onCreate = vi.fn();
        renderDrawer({ results: sampleUsers, onCreate });
        fireEvent.click(screen.getByLabelText('Iniciar conversación con ana'));
        expect(onCreate).toHaveBeenCalledWith('u1');
    });

    it('disables result buttons while creating', () => {
        renderDrawer({ results: sampleUsers, creating: true });
        const button = screen.getByLabelText('Iniciar conversación con ana');
        expect(button).toBeDisabled();
    });

    it('calls onQueryChange when typing in search input', () => {
        const onQueryChange = vi.fn();
        renderDrawer({ onQueryChange });
        const input = screen.getByLabelText('Buscar usuario para nueva conversación');
        fireEvent.change(input, { target: { value: 'ana' } });
        expect(onQueryChange).toHaveBeenCalledWith('ana');
    });

    it('calls onClose when close button is clicked', () => {
        const onClose = vi.fn();
        renderDrawer({ onClose });
        fireEvent.click(screen.getByLabelText('Cerrar'));
        expect(onClose).toHaveBeenCalled();
    });

    it('shows spinner on each result while creating', () => {
        renderDrawer({ results: sampleUsers, creating: true });
        expect(screen.getAllByTestId('creating-conversation-spinner')).toHaveLength(2);
    });

    it('calls onClose when the backdrop is clicked', () => {
        const onClose = vi.fn();
        renderDrawer({ onClose });
        const backdrop = screen.getByTestId('workspace-drawer-backdrop');
        fireEvent.click(backdrop);
        expect(onClose).toHaveBeenCalled();
    });

    it('does not render when isOpen is false', () => {
        const { container } = renderDrawer({ isOpen: false });
        expect(container.firstChild).toBeNull();
    });

    it('has no accessibility violations in loading state', async () => {
        const { container } = renderDrawer({ loading: true });
        expect(await axe(container)).toHaveNoViolations();
    });

    it('has no accessibility violations in error state', async () => {
        const { container } = renderDrawer({ error: 'Error al buscar usuarios' });
        expect(await axe(container)).toHaveNoViolations();
    });

    it('has no accessibility violations with results', async () => {
        const { container } = renderDrawer({ results: sampleUsers });
        expect(await axe(container)).toHaveNoViolations();
    });

    it('has no accessibility violations in prompt state', async () => {
        const { container } = renderDrawer({ query: 'a' });
        expect(await axe(container)).toHaveNoViolations();
    });
});
