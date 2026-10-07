import { describe, expect, it, vi } from 'vitest';
import { canDeleteProject } from './access';

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
