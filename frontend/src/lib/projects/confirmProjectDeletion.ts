import { apiFetch } from '@/lib/http';
import { toast } from 'sonner';

export const PROJECT_DELETE_CONFIRMATION_DESCRIPTION =
  'El proyecto dejará de aparecer en las vistas activas. Es un borrado lógico: las tareas y demás registros asociados se conservan, no se purgan físicamente. No hay una opción para restaurarlo desde esta pantalla.';

export const PROJECT_ARCHIVE_CONFIRMATION_DESCRIPTION =
  'El proyecto pasará al archivo histórico de Activos de Procesos de la Organización (OPA PMI §4.7). Conservará su línea base, lecciones aprendidas y paquetes de trabajo para consulta y auditoría.';

/** Runs project deletion and only signals success after the server confirms it. */
export async function confirmProjectDeletion(
  projectId: string,
  token: string,
  onDeleted: () => void,
): Promise<void> {
  try {
    await apiFetch(`/projects/${projectId}`, { method: 'DELETE', token });
  } catch {
    toast.error('Error al eliminar proyecto');
    throw new Error('No se pudo eliminar el proyecto.');
  }
  toast.success('Proyecto eliminado');
  onDeleted();
}

/**
 * PMI §4.7 — Archiva el proyecto en el archivo histórico (OPA) vía PATCH
 * status=archived y notifica el resultado; lanza en fallo para que el
 * drawer de confirmación permanezca abierto.
 */
export async function confirmProjectArchival(
  projectId: string,
  token: string,
  onArchived: () => void,
): Promise<void> {
  try {
    await apiFetch(`/projects/${projectId}`, {
      method: 'PATCH',
      token,
      body: { status: 'archived' },
    });
  } catch {
    toast.error('Error al archivar proyecto');
    throw new Error('No se pudo archivar el proyecto.');
  }
  toast.success('Proyecto archivado en OPA');
  onArchived();
}
