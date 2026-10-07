import { apiFetch } from '@/lib/http';
import { toast } from 'sonner';

export const PROJECT_DELETE_CONFIRMATION_DESCRIPTION =
  'El proyecto dejará de aparecer en las vistas activas. Es un borrado lógico: las tareas y demás registros asociados se conservan, no se purgan físicamente. No hay una opción para restaurarlo desde esta pantalla.';

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
