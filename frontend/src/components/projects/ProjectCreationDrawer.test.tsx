import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { axe } from 'jest-axe';
import { describe, expect, it, vi } from 'vitest';
import ProjectCreationDrawer from './ProjectCreationDrawer';

vi.mock('@/context/AuthContext', () => ({
    useAuth: () => ({ token: null }),
}));

// Mantener ligeramente el mock de selección de responsable para poder evaluar
// el criterio PMI "Patrocinador / Director de Proyecto" sin backend.
vi.mock('@/components/ui/PersonaSelect', () => ({
    default: function PersonaSelectMock({
        value,
        onChange,
    }: {
        value: string | null;
        onChange: (personaId: string | null) => void;
    }) {
        return (
            <div>
                <button type="button" onClick={() => onChange('persona-1')}>
                    Seleccionar responsable mock
                </button>
                {value && <span>Responsable mock: {value}</span>}
            </div>
        );
    },
}));

describe('ProjectCreationDrawer accessibility', () => {
    it('associates labels with fields and names selectable controls', () => {
        render(<ProjectCreationDrawer isOpen onClose={vi.fn()} onSubmit={vi.fn()} />);

        expect(screen.getByRole('textbox', { name: 'Título del proyecto' })).toBeInTheDocument();
        expect(screen.getByRole('textbox', { name: 'Descripción (opcional)' })).toBeInTheDocument();
        expect(screen.getByRole('group', { name: 'Estado inicial' })).toBeInTheDocument();
        expect(screen.getByRole('group', { name: 'Color del proyecto' })).toBeInTheDocument();
        expect(screen.getByRole('group', { name: 'Asignar responsable' })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Color Azul ministerial' })).toHaveAttribute('aria-pressed', 'true');
    });

    it('has no axe accessibility violations while open', async () => {
        const { container } = render(<ProjectCreationDrawer isOpen onClose={vi.fn()} onSubmit={vi.fn()} />);
        const results = await axe(container);

        expect(results.violations).toEqual([]);
    });
});

describe('ProjectCreationDrawer PMI §4.1 charter readiness', () => {
    it('evalúa el puntaje X/4 Criterios PMI de forma reactiva', () => {
        render(<ProjectCreationDrawer isOpen onClose={vi.fn()} onSubmit={vi.fn()} />);

        const readiness = screen.getByTestId('project-creation-pmi-readiness');
        const score = screen.getByTestId('project-creation-pmi-score');
        expect(readiness).toBeInTheDocument();
        // Con estado inicial por defecto ('planning') solo 1 criterio se cumple.
        expect(score).toHaveTextContent('1/4 Criterios PMI');
        expect(score).toHaveTextContent('Gobernanza Parcial');

        // Nombre definido → 2/4
        fireEvent.change(screen.getByRole('textbox', { name: 'Título del proyecto' }), {
            target: { value: 'Escuela de Liderazgo 2026' },
        });
        expect(score).toHaveTextContent('2/4 Criterios PMI');

        // Justificación / Caso de Negocio (>= 20 caracteres) → 3/4
        fireEvent.change(screen.getByRole('textbox', { name: 'Descripción (opcional)' }), {
            target: { value: 'Formar líderes con caso de negocio documentado' },
        });
        expect(score).toHaveTextContent('3/4 Criterios PMI');
        expect(score).toHaveTextContent('Gobernanza Parcial');

        // Patrocinador / Director de Proyecto asignado → 4/4 y Alistamiento Completo
        fireEvent.click(screen.getByRole('button', { name: 'Seleccionar responsable mock' }));
        expect(score).toHaveTextContent('4/4 Criterios PMI');
        expect(score).toHaveTextContent('Alistamiento Completo');
    });

    it('inserta o anexa plantillas de Objetivo / Caso de Negocio PMI en la descripción', () => {
        render(<ProjectCreationDrawer isOpen onClose={vi.fn()} onSubmit={vi.fn()} />);

        expect(screen.getByTestId('project-creation-pmi-templates')).toBeInTheDocument();

        const descriptionArea = screen.getByRole('textbox', { name: 'Descripción (opcional)' });
        expect(descriptionArea).toHaveValue('');        // Inserta sobre descripción vacía
        fireEvent.click(screen.getByTestId('project-template-predictive'));
        expect(descriptionArea).toHaveValue(
            '[Predictivo PMI]\nObjetivo: \nAlcance Inicial: \nCriterio de Exito: '
        );

        // Anexa cuando ya hay contenido preservado
        fireEvent.change(descriptionArea, { target: { value: 'Caso de negocio inicial documentado.' } });
        fireEvent.click(screen.getByTestId('project-template-hybrid'));
        expect(descriptionArea).toHaveValue(
            'Caso de negocio inicial documentado.\n\n[Hibrido Stage-Gate]\nValor Incremental: \nHito de Control 1: \nHito de Control 2: '
        );

        fireEvent.click(screen.getByTestId('project-template-agile'));
        const value = (descriptionArea as HTMLTextAreaElement).value;
        expect(value).toContain('\n\n[Adaptativo / Agil]\nVision de Producto: \nEntregables Iterativos: ');
    });

    it('crea el proyecto con los datos del formulario y cierra el drawer', async () => {
        const onClose = vi.fn();
        const onSubmit = vi.fn().mockResolvedValue(undefined);
        render(<ProjectCreationDrawer isOpen onClose={onClose} onSubmit={onSubmit} />);

        fireEvent.change(screen.getByRole('textbox', { name: 'Título del proyecto' }), {
            target: { value: 'Escuela de Liderazgo 2026' },
        });
        fireEvent.change(screen.getByRole('textbox', { name: 'Descripción (opcional)' }), {
            target: { value: 'Objetivo documentario con caso de negocio inicial.' },
        });
        fireEvent.click(screen.getByRole('button', { name: 'Seleccionar responsable mock' }));

        fireEvent.click(screen.getByRole('button', { name: 'Crear Proyecto' }));

        await waitFor(() => {
            expect(onSubmit).toHaveBeenCalledTimes(1);
        });
        expect(onSubmit).toHaveBeenCalledWith({
            title: 'Escuela de Liderazgo 2026',
            description: 'Objetivo documentario con caso de negocio inicial.',
            status: 'planning',
            owner_id: 'persona-1',
            color: '#2563eb',
        });
        expect(onClose).toHaveBeenCalledTimes(1);
    });
});
