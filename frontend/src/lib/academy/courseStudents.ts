// Módulo puro (sin React/next) con la lógica de estados "sin lista de
// estudiantes" de las consolas de administración de cursos. Extraído de
// manage/page.tsx para poder testearlo unitariamente (F-02).

export interface CourseDetails {
    id: string;
    title: string;
    code: string;
    modality: string;
    cohort_name: string;
    // F-02 (2026-08-02): el serializador emite ``lesson_count`` (singular) — no
    // ``lessons_count`` ni ``students_count``. La página no lo renderiza hoy,
    // pero el tipo refleja el contract real del backend (antes declaraba
    // ``lessons_count``, un campo que nunca llega).
    lesson_count: number;
    // H-01 (cierre 2026-07-24): el contract read expone sede_id — NULL = curso
    // global legítimo. Se usa para explicar el 200+lista vacía en consolas admin
    // (F-02: un Manager con sede no ve estudiantes de cursos globales).
    sede_id: string | null;
}

// F-02 (2026-08-02): texto único para los estados "sin lista" de las tres vistas
// (grid/list/table). Distingue: error real (500/timeout) con curso cargado →
// retry; curso inaccesible (404 cross-sede / fuera de sede) → sin retry;
// búsqueda sin coincidencias; curso global (sede_id NULL) + Manager con sede →
// 200+[] legítimo; y curso sin estudiantes. Evita que un Manager confunda el
// 200+lista vacía de un curso global con un error.
export function studentsEmptyMessage(
    search: string,
    course: CourseDetails | null,
    studentsError: boolean,
): { title: string; description: string } {
    if (studentsError) {
        return course
            ? {
                  title: 'No se pudieron cargar los estudiantes',
                  // Sin "Reintenta" aquí: sólo la vista grid ofrece botón de retry;
                  // en list/table la frase quedaría como instrucción colgada.
                  description: 'Esto no significa que la lista esté vacía.',
              }
            : {
                  title: 'Curso no disponible',
                  description: 'Este curso no está disponible o está fuera de tu sede.',
              };
    }
    if (search) {
        return { title: 'Cero coincidencias', description: 'Prueba con otros terminos de busqueda.' };
    }
    if (course?.sede_id == null) {
        return {
            title: 'Sin estudiantes inscritos',
            description:
                'Este curso es global: sus estudiantes no aparecen en esta consola para gestores con sede. La lista vacía es intencional, no un error.',
        };
    }
    return { title: 'Sin estudiantes inscritos', description: 'Aun no hay estudiantes inscritos en este curso.' };
}
