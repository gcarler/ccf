type PermissionChecker = (permission: string) => boolean;

/** Mirrors DELETE /api/projects/{project_id}, guarded by academy:manage. */
export function canDeleteProject(hasPermission: PermissionChecker): boolean {
  return hasPermission('academy:manage');
}
