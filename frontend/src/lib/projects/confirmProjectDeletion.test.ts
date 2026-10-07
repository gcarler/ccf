import { beforeEach, describe, expect, it, vi } from 'vitest';
import { apiFetch } from '@/lib/http';
import { toast } from 'sonner';
import {
  confirmProjectDeletion,
  PROJECT_DELETE_CONFIRMATION_DESCRIPTION,
} from './confirmProjectDeletion';

vi.mock('@/lib/http', () => ({ apiFetch: vi.fn() }));
vi.mock('sonner', () => ({ toast: { error: vi.fn(), success: vi.fn() } }));

describe('confirmProjectDeletion', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('explains soft-delete behavior and the lack of an in-screen restore action', () => {
    expect(PROJECT_DELETE_CONFIRMATION_DESCRIPTION).toContain('borrado lógico');
    expect(PROJECT_DELETE_CONFIRMATION_DESCRIPTION).toContain('se conservan');
    expect(PROJECT_DELETE_CONFIRMATION_DESCRIPTION).toContain('no se purgan físicamente');
    expect(PROJECT_DELETE_CONFIRMATION_DESCRIPTION).toContain(
      'No hay una opción para restaurarlo desde esta pantalla',
    );
  });

  it('navigates only after the API confirms deletion', async () => {
    const onDeleted = vi.fn();
    vi.mocked(apiFetch).mockResolvedValue({ ok: true, deleted: 'project-1' });

    await confirmProjectDeletion('project-1', 'token', onDeleted);

    expect(apiFetch).toHaveBeenCalledWith('/projects/project-1', {
      method: 'DELETE',
      token: 'token',
    });
    expect(toast.success).toHaveBeenCalledWith('Proyecto eliminado');
    expect(onDeleted).toHaveBeenCalledOnce();
  });

  it('notifies and rejects a failed delete so the confirmation drawer remains open', async () => {
    const onDeleted = vi.fn();
    vi.mocked(apiFetch).mockRejectedValue(new Error('offline'));

    await expect(confirmProjectDeletion('project-1', 'token', onDeleted))
      .rejects.toThrow('No se pudo eliminar el proyecto.');

    expect(toast.error).toHaveBeenCalledWith('Error al eliminar proyecto');
    expect(toast.success).not.toHaveBeenCalled();
    expect(onDeleted).not.toHaveBeenCalled();
  });
});
