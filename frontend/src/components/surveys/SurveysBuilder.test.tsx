import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import CreateSurveyDrawer from './CreateSurveyDrawer';
import QuestionEditorCard from './QuestionEditorCard';
import FormSettingsTab from './FormSettingsTab';
import { EncuestaFormulario, EncuestaPregunta } from '@/types/surveys';

// Mock de Next.js router
vi.mock('next/navigation', () => ({
    useRouter: () => ({
        push: vi.fn(),
        replace: vi.fn(),
        back: vi.fn(),
    }),
    useSearchParams: () => new URLSearchParams(),
}));

// Mock de apiFetch
vi.mock('@/lib/http', () => ({
    apiFetch: vi.fn(),
}));

describe('CreateSurveyDrawer (Zero-Modals)', () => {
    it('no renderiza cuando isOpen es false', () => {
        render(<CreateSurveyDrawer isOpen={false} onClose={() => {}} />);
        expect(screen.queryByText(/Nueva Encuesta Dinámica/i)).not.toBeInTheDocument();
    });

    it('renderiza inputs, plantillas y botón de crear cuando isOpen es true', () => {
        render(<CreateSurveyDrawer isOpen onClose={() => {}} />);
        expect(screen.getByText(/Nueva Encuesta Dinámica/i)).toBeInTheDocument();
        expect(screen.getByPlaceholderText(/Censo de Voluntarios CCF 2026/i)).toBeInTheDocument();
        expect(screen.getByText(/Formulario en Blanco/i)).toBeInTheDocument();
        expect(screen.getByText(/Satisfacción del Servicio/i)).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Crear Encuesta/i })).toBeInTheDocument();
    });
});

describe('QuestionEditorCard (Google Forms Parity Drag & Drop)', () => {
    const mockPregunta: EncuestaPregunta = {
        id: 'q-test-1',
        titulo: '¿Cuál es tu ministerio preferido?',
        descripcion: 'Selecciona una sola opción',
        tipo_pregunta: 'OPCION_MULTIPLE',
        orden: 0,
        es_requerida: true,
        opciones: [
            { id: 'opt-1', label: 'Alabanza' },
            { id: 'opt-2', label: 'Medios' },
        ],
        filas: [],
        columnas: [],
        escala_min: 1,
        escala_max: 5,
        archivo_tipos_permitidos: [],
        archivo_max_mb: 10,
        archivo_max_archivos: 1,
        configuracion: {},
    };

    it('renderiza título, tipo y opciones de selección múltiple', () => {
        render(
            <QuestionEditorCard
                pregunta={mockPregunta}
                index={0}
                availableQuestions={[mockPregunta]}
                isSelected={true}
                onSelect={() => {}}
                onChange={() => {}}
                onDuplicate={() => {}}
                onDelete={() => {}}
            />
        );

        expect(screen.getByDisplayValue('¿Cuál es tu ministerio preferido?')).toBeInTheDocument();
        expect(screen.getByDisplayValue('Alabanza')).toBeInTheDocument();
        expect(screen.getByDisplayValue('Medios')).toBeInTheDocument();
        expect(screen.getAllByText(/Obligatoria/i).length).toBeGreaterThan(0);
    });

    it('emite evento onChange cuando se modifica el título o se activa obligatoria', () => {
        const handleChange = vi.fn();
        render(
            <QuestionEditorCard
                pregunta={mockPregunta}
                index={0}
                availableQuestions={[mockPregunta]}
                isSelected={true}
                onSelect={() => {}}
                onChange={handleChange}
                onDuplicate={() => {}}
                onDelete={() => {}}
            />
        );

        const titleInput = screen.getByDisplayValue('¿Cuál es tu ministerio preferido?');
        fireEvent.change(titleInput, { target: { value: 'Nuevo Título de Pregunta' } });
        expect(handleChange).toHaveBeenCalledWith(
            expect.objectContaining({ titulo: 'Nuevo Título de Pregunta' })
        );
    });

    it('permite configurar visibilidad condicionada a una respuesta anterior', () => {
        const source: EncuestaPregunta = {
            ...mockPregunta,
            id: 'q-source',
            titulo: '¿Necesitas apoyo?',
            orden: 0,
            opciones: [{ id: 'yes', label: 'Sí' }, { id: 'no', label: 'No' }],
        };
        const dependent = { ...mockPregunta, id: 'q-dependent', orden: 1, configuracion: {} };
        const handleChange = vi.fn();
        render(
            <QuestionEditorCard
                pregunta={dependent}
                index={1}
                availableQuestions={[source, dependent]}
                isSelected={false}
                onSelect={() => {}}
                onChange={handleChange}
                onDuplicate={() => {}}
                onDelete={() => {}}
            />
        );

        fireEvent.change(screen.getByRole('combobox', { name: `Pregunta que controla ${dependent.titulo}` }), { target: { value: source.id } });
        expect(handleChange).toHaveBeenCalledWith(expect.objectContaining({
            configuracion: { visible_if: { pregunta_id: source.id, operador: 'igual_a', opcion_id: 'yes' } },
        }));
    });

    it('permite dirigir una opción a una sección concreta', () => {
        const section: EncuestaPregunta = {
            ...mockPregunta,
            id: 'section-next',
            titulo: 'Sección siguiente',
            tipo_pregunta: 'SECCION_SALTO',
            orden: 1,
            opciones: [],
        };
        const handleChange = vi.fn();
        render(
            <QuestionEditorCard
                pregunta={mockPregunta}
                index={0}
                availableQuestions={[mockPregunta, section]}
                isSelected={false}
                onSelect={() => {}}
                onChange={handleChange}
                onDuplicate={() => {}}
                onDelete={() => {}}
            />
        );

        fireEvent.change(screen.getByRole('combobox', { name: 'Destino de Alabanza' }), { target: { value: section.id } });
        expect(handleChange).toHaveBeenCalledWith(expect.objectContaining({
            opciones: expect.arrayContaining([expect.objectContaining({ id: 'opt-1', salto_seccion_id: section.id })]),
        }));
    });

    it('renderiza campos numéricos cuando es de tipo ESCALA_LINEAL', () => {
        const scalePregunta: EncuestaPregunta = {
            ...mockPregunta,
            tipo_pregunta: 'ESCALA_LINEAL',
            escala_min: 1,
            escala_max: 5,
            escala_min_etiqueta: 'Bajo',
            escala_max_etiqueta: 'Alto',
        };

        render(
            <QuestionEditorCard
                pregunta={scalePregunta}
                index={1}
                availableQuestions={[mockPregunta, scalePregunta]}
                isSelected={false}
                onSelect={() => {}}
                onChange={() => {}}
                onDuplicate={() => {}}
                onDelete={() => {}}
            />
        );

        expect(screen.getByDisplayValue('Bajo')).toBeInTheDocument();
        expect(screen.getByDisplayValue('Alto')).toBeInTheDocument();
    });
});

describe('FormSettingsTab', () => {
    const mockSurvey: EncuestaFormulario = {
        id: 'survey-123',
        titulo: 'Encuesta General',
        slug: 'encuesta-general',
        estado: 'PUBLICADO',
        es_publico: true,
        requiere_autenticacion: false,
        limitar_una_respuesta: true,
        permitir_editar_respuesta: false,
        mostrar_barra_progreso: true,
        mensaje_confirmacion: '¡Gracias por responder!',
        total_respuestas: 10,
        config_visual: {
            tema: 'light',
            color_primario: '#0284c7',
            fuente: 'Inter',
        },
        ajustes: {},
        is_active: true,
        created_at: '2026-09-30T00:00:00Z',
        updated_at: '2026-09-30T00:00:00Z',
        preguntas: [],
    };

    it('renderiza enlace público, opciones de estado y botones de guardado', () => {
        render(<FormSettingsTab survey={mockSurvey} onSurveyUpdated={() => {}} />);
        expect(screen.getByText(/Enlace Público para Encuestados/i)).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Copiar Enlace/i })).toBeInTheDocument();
        expect(screen.getByDisplayValue('¡Gracias por responder!')).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Guardar Ajustes/i })).toBeInTheDocument();
    });
});
