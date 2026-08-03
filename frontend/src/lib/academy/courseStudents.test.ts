import { describe, expect, it } from 'vitest';
import { studentsEmptyMessage, type CourseDetails } from './courseStudents';

function makeCourse(overrides: Partial<CourseDetails> = {}): CourseDetails {
    return {
        id: 'course-1',
        title: 'Curso de Prueba',
        code: 'CUR-001',
        modality: 'capacitacion',
        cohort_name: 'Cohorte 2026-I',
        lesson_count: 4,
        // sede_id NULL = curso global legítimo (H-01); con valor = curso de sede.
        sede_id: 'sede-1',
        ...overrides,
    };
}

const globalCourse = makeCourse({ sede_id: null });
const sedeCourse = makeCourse({ sede_id: 'sede-1' });

describe('studentsEmptyMessage', () => {
    it('caso 1 — error retryable: error real (500/timeout) con curso cargado', () => {
        const result = studentsEmptyMessage('', sedeCourse, true);
        expect(result.title).toBe('No se pudieron cargar los estudiantes');
        // Sin instrucción colgada de "Reintenta" (sólo la vista grid tiene botón).
        expect(result.description).toBe('Esto no significa que la lista esté vacía.');
        expect(result.description).not.toMatch(/reintenta/i);
    });

    it('caso 2 — curso no disponible: error con curso inaccesible (404 cross-sede / fuera de sede)', () => {
        const result = studentsEmptyMessage('', null, true);
        expect(result.title).toBe('Curso no disponible');
        expect(result.description).toBe('Este curso no está disponible o está fuera de tu sede.');
    });

    it('caso 3 — cero coincidencias: búsqueda activa sin resultados, sin error', () => {
        const result = studentsEmptyMessage('juan perez', sedeCourse, false);
        expect(result.title).toBe('Cero coincidencias');
        expect(result.description).toBe('Prueba con otros terminos de busqueda.');
    });

    it('caso 4 — curso global: 200+vacío legítimo para un Manager con sede (sede_id NULL)', () => {
        const result = studentsEmptyMessage('', globalCourse, false);
        expect(result.title).toBe('Sin estudiantes inscritos');
        expect(result.description).toMatch(/global/i);
        expect(result.description).toMatch(/intencional/i);
        // No debe usar el título del error retryable (la descripción sí puede
        // mencionar "no un error" para tranquilizar al gestor).
        expect(result.title).not.toBe('No se pudieron cargar los estudiantes');
        expect(result.title).not.toBe('Curso no disponible');
    });

    it('fallback — curso de sede sin estudiantes inscritos', () => {
        const result = studentsEmptyMessage('', sedeCourse, false);
        expect(result.title).toBe('Sin estudiantes inscritos');
        expect(result.description).toBe('Aun no hay estudiantes inscritos en este curso.');
    });

    it('precedencia — el error gana sobre la búsqueda', () => {
        const result = studentsEmptyMessage('juan', sedeCourse, true);
        expect(result.title).toBe('No se pudieron cargar los estudiantes');
    });

    it('precedencia — la búsqueda sin resultados gana sobre el curso global', () => {
        const result = studentsEmptyMessage('juan', globalCourse, false);
        expect(result.title).toBe('Cero coincidencias');
    });
});
