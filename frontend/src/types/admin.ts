/**
 * Shared TypeScript types for the Admin module.
 *
 * These types mirror the canonical backend schemas from
 * backend/schemas/admin.py and the permission taxonomy in
 * backend/core/permissions.py.
 */

/** A platform role as returned by /api/admin/roles */
export interface AdminRoleRead {
  id: string;
  nombre: string;
  permisos: Record<string, string>;
  users_count?: number;
}

/** A user row as returned by /api/admin/users */
export interface AdminUserRead {
  id: string;
  username: string;
  email: string;
  role: string;
  is_active: boolean;
  rol_plataforma_id?: string | null;
  role_name?: string | null;
  permissions?: Record<string, string>;
}

/** Response from /api/admin/users/{id}/permissions */
export interface AdminUserPermissionsRead {
  user_id: string;
  username: string;
  email: string;
  role: string;
  role_permissions: Record<string, string>;
  override_permissions: Record<string, string>;
  module_roles: Array<{ module: string; role_id: string }>;
  effective_permissions: Record<string, string>;
}

/** Response from /api/admin/permissions */
export interface AdminPermissionsTaxonomy {
  permissions: Record<string, { label: string; description: string }>;
  modules: Record<string, string[]>;
  levels: Record<string, string[]>;
}

/** Canonical module levels used by the backend */
export type AdminModuleLevel = 'read' | 'edit' | 'manage' | 'study' | 'none';

/** A module entry rendered in the permission matrix */
export interface AdminPermissionModule {
  id: string;
  label: string;
  levels: AdminModuleLevel[];
}

/** Internal state of the permission matrix */
export type ModulePermissionMap = Record<string, AdminModuleLevel>;
