export type PermissionChecker = (permission: string) => boolean;

/** Mirrors DELETE /api/projects/{project_id}, guarded by academy:manage. */
export function canDeleteProject(hasPermission: PermissionChecker): boolean {
  return hasPermission('academy:manage');
}

/** PMI §4.6 — Gestionar la línea base del proyecto (baseline). */
export function canManageProjectBaseline(hasPermission: PermissionChecker): boolean {
  return hasPermission('academy:manage') || hasPermission('projects:baseline:manage');
}

/** PMI §2.4 — Aprobar hitos de gobernanza (stage-gates). */
export function canApproveStageGate(hasPermission: PermissionChecker): boolean {
  return hasPermission('academy:manage') || hasPermission('projects:governance:approve');
}

/** PMI §4.1 — Editar el acta de constitución del proyecto (charter). */
export function canEditProjectCharter(hasPermission: PermissionChecker): boolean {
  return hasPermission('academy:manage') || hasPermission('projects:charter:edit');
}
