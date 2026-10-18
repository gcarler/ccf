import { describe, expect, it, vi } from 'vitest';
import {
  canDeleteProject,
  canManageProjectBaseline,
  canApproveStageGate,
  canEditProjectCharter,
  type PermissionChecker,
} from './access';

describe('canDeleteProject', () => {
  it('uses the exact permission required by the backend delete route', () => {
    const hasPermission = vi.fn(
      (permission: string) => permission === 'academy:manage'
    );

    expect(canDeleteProject(hasPermission)).toBe(true);
    expect(hasPermission).toHaveBeenCalledTimes(1);
    expect(hasPermission).toHaveBeenCalledWith('academy:manage');
  });

  it('does not infer delete access from unrelated system configuration permission', () => {
    const hasPermission = vi.fn(
      (permission: string) => permission === 'system:config'
    );

    expect(canDeleteProject(hasPermission)).toBe(false);
    expect(hasPermission).toHaveBeenCalledTimes(1);
    expect(hasPermission).toHaveBeenCalledWith('academy:manage');
  });
});

function checkerWith(...granted: string[]): PermissionChecker {
  const grantedSet = new Set(granted);
  return (permission: string) => grantedSet.has(permission);
}

const PMI_GUARDS = [
  { name: 'canManageProjectBaseline', fn: canManageProjectBaseline, granular: 'projects:baseline:manage' },
  { name: 'canApproveStageGate', fn: canApproveStageGate, granular: 'projects:governance:approve' },
  { name: 'canEditProjectCharter', fn: canEditProjectCharter, granular: 'projects:charter:edit' },
] as const;

describe('PMI gobernanza (§4.6 / §2.4) — guardas RBAC', () => {
  it.each(PMI_GUARDS)('$name concede con academy:manage', ({ fn }) => {
    expect(fn(checkerWith('academy:manage'))).toBe(true);
  });

  it.each(PMI_GUARDS)('$name concede con el permiso granular $granular', ({ fn, granular }) => {
    expect(fn(checkerWith(granular))).toBe(true);
  });

  it.each(PMI_GUARDS)('$name no infere acceso desde permisos ajenos', ({ fn }) => {
    expect(fn(checkerWith('system:config'))).toBe(false);
    expect(fn(checkerWith('projects:baseline:read'))).toBe(false);
    expect(fn(checkerWith('projects:status:edit'))).toBe(false);
  });

  it.each(PMI_GUARDS)('$name deniega sin ningún permiso', ({ fn, granular }) => {
    expect(fn(checkerWith())).toBe(false);
    const probe = vi.fn(checkerWith());
    fn(probe);
    expect(probe).toHaveBeenCalledWith('academy:manage');
    expect(probe).toHaveBeenCalledWith(granular);
  });

  it('canDeleteProject mantiene su contrato exclusivo con academy:manage', () => {
    expect(canDeleteProject(checkerWith('academy:manage'))).toBe(true);
    expect(canDeleteProject(checkerWith('projects:baseline:manage'))).toBe(false);
  });
});
