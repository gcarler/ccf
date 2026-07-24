"use client";

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { SITE_NAME } from '@/lib/site-config';
import {
  Shield,
  Users,
  Lock,
  ChevronRight,
  Plus,
  XCircle,
  Eye,
  Edit3,
  Settings,
  Layout,
  BookOpen,
  ClipboardList,
  AlertCircle,
  UserCircle,
  Loader2,
  Save,
  Undo2,
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import type { ViewType } from '@/components/ViewSwitcher';
import UniversalCalendarView from '@/components/ui/UniversalCalendarView';
import UniversalGanttView from '@/components/ui/UniversalGanttView';
import UniversalWikiView from '@/components/ui/UniversalWikiView';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';
import { DataTable } from '@/components/ui/DataTable';
import { ColumnDef } from '@tanstack/react-table';
import { DSSkeleton } from '@/design';
import { motion } from 'framer-motion';
import clsx from 'clsx';
import type {
  AdminRoleRead,
  AdminUserRead,
  AdminUserPermissionsRead,
  AdminPermissionsTaxonomy,
  AdminModuleLevel,
  ModulePermissionMap,
} from '@/types/admin';

const ACCESS_VIEWS: ViewType[] = ['table', 'list', 'grid', 'board', 'kanban', 'calendar', 'gantt', 'wiki'];

// Static metadata for rendering; the canonical list of modules and levels
// is fetched from /api/admin/permissions.
const MODULE_META: Record<
  string,
  { label: string; icon: React.ElementType; color: string }
> = {
  crm: { label: 'CRM Pastoral', icon: Users, color: 'text-[hsl(var(--primary))]' },
  academy: { label: 'Academia CCF', icon: BookOpen, color: 'text-[hsl(var(--success))]' },
  projects: { label: 'Proyectos', icon: ClipboardList, color: 'text-[hsl(var(--primary))]' },
  finance: { label: 'Finanzas', icon: Lock, color: 'text-[hsl(var(--warning))]' },
  cms: { label: 'Sitio Web', icon: Layout, color: 'text-[hsl(var(--primary))]' },
  messaging: { label: 'Mensajería', icon: Edit3, color: 'text-[hsl(var(--domain-cyan)/90%)]' },
  evangelism: { label: 'Evangelismo', icon: Users, color: 'text-[hsl(var(--warning))]' },
  community: { label: 'Comunidad', icon: Users, color: 'text-[hsl(var(--domain-teal)/90%)]' },
  spiritual_life: { label: 'Vida Espiritual', icon: BookOpen, color: 'text-[hsl(var(--destructive))]' },
  wiki: { label: 'Wiki', icon: BookOpen, color: 'text-[hsl(var(--info))]' },
};const LEVEL_LABELS: Record<AdminModuleLevel, string> = {
  none: 'Bloqueado',
  read: 'Lector',
  study: 'Estudiante',
  edit: 'Editor',
  manage: 'Gestor',
};

const DEFAULT_NEW_USER_ROLE = 'MIEMBRO';

/** Convert a flat backend permission dict (e.g. { "crm:read": "allow" }) into a module -> level map. */
function toModuleLevelMap(perms: Record<string, unknown>): ModulePermissionMap {
  if (!perms || typeof perms !== 'object') return {};
  const result: ModulePermissionMap = {};
  for (const key of Object.keys(perms)) {
    if (!perms[key]) continue;
    const [mod, lvl] = key.split(':');
    if (!mod || !lvl) continue;
    const current = result[mod];
    const order: Record<string, number> = { none: 0, read: 1, study: 2, edit: 3, manage: 4 };
    if (!current || (order[lvl] ?? 0) > (order[current] ?? 0)) {
      result[mod] = lvl as AdminModuleLevel;
    }
  }
  return result;
}

/** Convert a module -> level map into the expanded backend permission dict for roles. */
function expandModuleMapToBackend(
  moduleMap: ModulePermissionMap,
  taxonomy?: AdminPermissionsTaxonomy | null
): Record<string, string> {
  const flat: Record<string, string> = {};
  for (const [mod, level] of Object.entries(moduleMap)) {
    if (!level || level === 'none') continue;
    // Prefer taxonomy from backend; fallback to local hierarchy.
    const levels = taxonomy?.levels ?? {
      read: ['read'],
      study: ['read', 'study'],
      edit: ['read', 'edit'],
      manage: ['read', 'edit', 'manage'],
    };
    const expanded = levels[level] ?? [level];
    for (const lvl of expanded) {
      flat[`${mod}:${lvl}`] = 'allow';
    }
  }
  return flat;
}

interface AccessRow {
  id: string;
  name?: string;
  username?: string;
  email?: string;
  role?: string;
  roleId?: string | null;
  users_count?: number;
  permissions?: Record<string, string>;
  is_active?: boolean;
  created_at?: string;
  updated_at?: string;
}

export default function AccessManagementPage() {
  const { token, isAuthenticated } = useAuth();
  const { addToast } = useToast();
  const [activeTab, setActiveTab] = useState<'roles' | 'users'>('roles');
  const [roles, setRoles] = useState<AccessRow[]>([]);
  const [users, setUsers] = useState<AccessRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedEntity, setSelectedEntity] = useState<AccessRow | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [isSaving, setIsAssigning] = useState(false);
  const [viewType, setViewType] = useState<ViewType>('table');
  const [search, setSearch] = useState('');
  const [taxonomy, setTaxonomy] = useState<AdminPermissionsTaxonomy | null>(null);

  // Effective permissions come from the platform role + modular roles.
  // Override permissions are the explicit overrides edited in this UI.
  const [effectivePermissions, setEffectivePermissions] = useState<ModulePermissionMap>({});
  const [overridePermissions, setOverridePermissions] = useState<ModulePermissionMap>({});
  const [userModuleRoles, setUserModuleRoles] = useState<Array<{ module: string; role_id: string }>>([]);

  const fetchData = useCallback(
    async (signal?: AbortSignal) => {
      if (!token) return;
      setLoading(true);
      try {
        const [rolesData, usersData, taxonomyData] = await Promise.all([
          apiFetch<{ items: AdminRoleRead[]; total: number }>('/admin/roles', {
            token,
            cache: 'no-store',
            signal,
          }),
          apiFetch<{ items: AdminUserRead[]; total: number }>('/admin/users', {
            token,
            cache: 'no-store',
            signal,
          }),
          apiFetch<AdminPermissionsTaxonomy>('/admin/permissions', {
            token,
            cache: 'no-store',
            signal,
          }).catch(() => null),
        ]);
        if (signal?.aborted) return;

        const rolesItems = rolesData?.items ?? [];
        const usersItems = usersData?.items ?? [];

        const mappedRoles: AccessRow[] = rolesItems.map((r) => ({
          id: r.id,
          name: r.nombre,
          permissions: r.permisos || {},
          users_count: r.users_count ?? 0,
        }));

        const mappedUsers: AccessRow[] = usersItems.map((u) => ({
          id: u.id,
          username: u.username,
          email: u.email,
          role: u.role_name || u.role || '—',
          roleId: u.rol_plataforma_id,
          is_active: u.is_active,
        }));

        setRoles(mappedRoles);
        setUsers(mappedUsers);
        if (taxonomyData) setTaxonomy(taxonomyData);
      } catch (err: unknown) {
        if (err instanceof Error && err.name === 'AbortError') return;
        console.error(err);
        addToast('Error al cargar configuraciones de acceso', 'error');
      } finally {
        if (!signal?.aborted) setLoading(false);
      }
    },
    [token, addToast]
  );

  useEffect(() => {
    if (!isAuthenticated) return;
    const controller = new AbortController();
    fetchData(controller.signal);
    return () => controller.abort();
  }, [isAuthenticated, fetchData]);

  const loadUserPermissions = useCallback(async (entity: AccessRow) => {
    if (!token) return;
    try {
      const permData = await apiFetch<AdminUserPermissionsRead>(
        `/admin/users/${entity.id}/permissions`,
        { token }
      );
      setEffectivePermissions(toModuleLevelMap(permData.effective_permissions || {}));
      setOverridePermissions(toModuleLevelMap(permData.override_permissions || {}));
      setUserModuleRoles(permData.module_roles || []);
    } catch {
      addToast('Error al cargar permisos del usuario', 'error');
      setEffectivePermissions({});
      setOverridePermissions({});
      setUserModuleRoles([]);
    }
  }, [token, addToast]);

  const handleOpenEntity = async (entity: AccessRow) => {
    setSelectedEntity(entity);

    if (activeTab === 'users' && token) {
      await loadUserPermissions(entity);
    } else {
      setEffectivePermissions({});
      setOverridePermissions(toModuleLevelMap(entity.permissions || {}));
      setUserModuleRoles([]);
    }

    setIsDrawerOpen(true);
  };

  const handleSavePermissions = async () => {
    if (!selectedEntity || !token) return;
    setIsAssigning(true);
    try {
      if (activeTab === 'roles') {
        const flatPerms = expandModuleMapToBackend(overridePermissions, taxonomy);
        await apiFetch(`/admin/roles/${selectedEntity.id}`, {
          method: 'PATCH',
          token,
          body: { permisos: flatPerms },
        });
        addToast('Permisos del rol actualizados', 'success');
        setIsDrawerOpen(false);
        fetchData();
      } else {
        // Send only explicit overrides; omit modules set to 'none'.
        const levelMap: Record<string, string> = {};
        for (const [module, level] of Object.entries(overridePermissions)) {
          if (level && level !== 'none') {
            levelMap[module] = level;
          }
        }
        await apiFetch(`/admin/users/${selectedEntity.id}/permissions`, {
          method: 'PUT',
          token,
          body: levelMap,
        });
        addToast('Permisos de usuario actualizados', 'success');
        // Refresh effective permissions so the UI immediately reflects inherited role permissions
        await loadUserPermissions(selectedEntity);
        fetchData();
      }
    } catch {
      addToast('Error al guardar cambios', 'error');
    } finally {
      setIsAssigning(false);
    }
  };

  const roleColumns = useMemo<ColumnDef<AccessRow>[]>(
    () => [
      {
        accessorKey: 'name',
        header: 'Nombre del Rol',
        cell: (info) => (
          <div className="flex items-center gap-3">
            <div className="size-8 rounded-lg bg-info-soft dark:bg-[hsl(var(--info))]/20 flex items-center justify-center text-[hsl(var(--primary))] shadow-sm">
              <Shield size={16} />
            </div>
            <span className="font-semibold text-[hsl(var(--text-primary))] dark:text-white uppercase tracking-tight">
              {String(info.getValue())}
            </span>
          </div>
        ),
      },
      {
        accessorKey: 'users_count',
        header: 'Usuarios',
        cell: (info) => (
          <div className="flex items-center gap-2">
            <div className="flex -space-x-2">
              {[1, 2, 3]
                .slice(0, (info.getValue() as number) || 0)
                .map((i) => (
                  <div
                    key={i}
                    className="size-6 rounded-full border-2 border-white dark:border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] flex items-center justify-center text-[8px] font-bold text-[hsl(var(--text-secondary))] uppercase"
                  >
                    U
                  </div>
                ))}
            </div>
            <span className="text-[11px] font-bold text-[hsl(var(--text-secondary))] ml-2">
              {Number(info.getValue())} vinculados
            </span>
          </div>
        ),
      },
      {
        id: 'actions',
        header: '',
        cell: () => (
          <button className="p-2 hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 rounded-md text-[hsl(var(--text-secondary))] opacity-0 group-hover:opacity-100 transition-all">
            <ChevronRight size={18} />
          </button>
        ),
      },
    ],
    []
  );

  const userColumns = useMemo<ColumnDef<AccessRow>[]>(
    () => [
      {
        accessorKey: 'username',
        header: 'Usuario',
        cell: (info) => (
          <div className="flex items-center gap-3">
            <div className="size-8 rounded-full bg-[hsl(var(--surface-2))] dark:bg-white/5 flex items-center justify-center text-[hsl(var(--text-secondary))] border border-[hsl(var(--border))] dark:border-white/10 shadow-inner">
              <UserCircle size={18} />
            </div>
            <div className="flex flex-col">
              <span className="text-[13px] font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">
                {String(info.getValue())}
              </span>
              <span className="text-[10px] text-[hsl(var(--text-secondary))] font-medium">
                #{info.row.original.id}
              </span>
            </div>
          </div>
        ),
      },
      {
        accessorKey: 'email',
        header: 'Email',
        cell: (info) => (
          <span className="text-[12px] text-[hsl(var(--text-secondary))]">{String(info.getValue())}</span>
        ),
      },
      {
        accessorKey: 'role',
        header: 'Rol Asignado',
        cell: (info) => (
          <span className="px-3 py-1 bg-info-soft dark:bg-[hsl(var(--info))]/20 text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))] rounded-lg text-[9px] font-semibold uppercase tracking-wide border border-[hsl(var(--info)/20%)] dark:border-[hsl(var(--info)/100%)]">
            {String(info.getValue())}
          </span>
        ),
      },
      {
        accessorKey: 'is_active',
        header: 'Estado',
        cell: (info) => (
          <div className="flex items-center gap-2">
            <div
              className={clsx(
                'size-2 rounded-full',
                info.getValue()
                  ? 'bg-[hsl(var(--success))] shadow-[0_0_8px_var(--success)]'
                  : 'bg-[hsl(var(--surface-2))]'
              )}
            />
            <span className="text-[10px] font-semibold uppercase text-[hsl(var(--text-secondary))] tracking-wide">
              {info.getValue() ? 'Activo' : 'Inactivo'}
            </span>
          </div>
        ),
      },
    ],
    []
  );

  const handleCreateEntity = useCallback(() => {
    if (activeTab === 'roles') {
      const name = prompt('Nombre del nuevo rol de plataforma:');
      if (!name?.trim()) return;
      setIsAssigning(true);
      apiFetch('/admin/roles', {
        method: 'POST',
        token,
        body: { nombre: name.trim(), permisos: {} },
      })
        .then(() => {
          addToast(`Rol "${name.trim()}" creado`, 'success');
          fetchData();
        })
        .catch(() => addToast('Error al crear rol', 'error'))
        .finally(() => setIsAssigning(false));
    } else {
      const username = prompt('Nombre de usuario:');
      if (!username?.trim()) return;
      const email = prompt('Correo electrónico:');
      if (!email?.trim()) return;
      const password = prompt('Contraseña (mínimo 6 caracteres):');
      if (!password || password.length < 6) {
        addToast('La contraseña debe tener al menos 6 caracteres', 'warning');
        return;
      }
      setIsAssigning(true);
      apiFetch<{ items: Array<{ id: string; username: string; email: string }>; total: number }>(
        '/admin/users',
        {
          method: 'POST',
          token,            body: {
              username: username.trim(),
              email: email.trim(),
              password,
              role: DEFAULT_NEW_USER_ROLE,
            },
        }
      )
        .then(() => {
          addToast(`Usuario "${username.trim()}" creado`, 'success');
          fetchData();
        })
        .catch(() => addToast('Error al crear usuario', 'error'))
        .finally(() => setIsAssigning(false));
    }
  }, [activeTab, token, addToast, fetchData]);

  const currentRows = (activeTab === 'roles' ? roles : users).filter((row) => {
    const term = search.trim().toLowerCase();
    if (!term) return true;
    return `${row.name || ''} ${row.username || ''} ${row.email || ''} ${row.role || ''}`
      .toLowerCase()
      .includes(term);
  });

  const groupedRows =
    activeTab === 'roles'
      ? [
          {
            id: 'admin',
            label: 'Administración',
            rows: currentRows.filter((row) =>
              `${row.name || ''}`.toLowerCase().includes('admin')
            ),
          },
          {
            id: 'ministry',
            label: 'Ministeriales',
            rows: currentRows.filter(
              (row) => !`${row.name || ''}`.toLowerCase().includes('admin')
            ),
          },
        ]
      : [
          {
            id: 'active',
            label: 'Activos',
            rows: currentRows.filter((row) => row.is_active !== false),
          },
          {
            id: 'inactive',
            label: 'Inactivos',
            rows: currentRows.filter((row) => row.is_active === false),
          },
        ];

  const calendarEvents = currentRows.map((row, index) => ({
    id: row.id || index,
    title:
      activeTab === 'roles'
        ? row.name || `Rol #${row.id}`
        : row.username || row.email || `Usuario #${row.id}`,
    date: (row.created_at || row.updated_at || new Date().toISOString()).split('T')[0],
    color:
      activeTab === 'roles'
        ? ('blue' as const)
        : row.is_active === false
          ? ('rose' as const)
          : ('emerald' as const),
    location: activeTab === 'roles' ? `${row.users_count || 0} usuarios` : row.role,
  }));

  const ganttItems = currentRows.map((row, index) => {
    const start = row.created_at || row.updated_at || new Date().toISOString();
    return {
      id: row.id || index,
      title:
        activeTab === 'roles'
          ? row.name || `Rol #${row.id}`
          : row.username || row.email || `Usuario #${row.id}`,
      subtitle: activeTab === 'roles' ? `${row.users_count || 0} usuarios` : row.role || row.email,
      start_date: start,
      end_date: row.updated_at || start,
      color:
        activeTab === 'roles'
          ? ('blue' as const)
          : row.is_active === false
            ? ('rose' as const)
            : ('emerald' as const),
      progress: activeTab === 'roles' ? 80 : row.is_active === false ? 20 : 100,
    };
  });

  const renderAccessCards = (mode: 'grid' | 'list') => (
    <div
      className={clsx(
        mode === 'grid'
          ? 'grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3'
          : 'space-y-4'
      )}
    >
      {currentRows.map((row) => {
        const title = activeTab === 'roles' ? row.name : row.username || row.email;
        const subtitle =
          activeTab === 'roles'
            ? `${row.users_count || 0} usuarios vinculados`
            : `${row.email || 'Sin email'} · ${row.role || 'Sin rol'}`;
        return (
          <button
            key={row.id || title}
            onClick={() => handleOpenEntity(row)}
            className={clsx(
              'text-left bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/5 rounded-lg p-3 hover:border-[hsl(var(--info)/30%)] hover:shadow-xl transition-all',
              mode === 'list' && 'flex items-center justify-between gap-4'
            )}
          >
            <div className="flex items-center gap-4">
              <div className="size-7 rounded-lg bg-info-soft dark:bg-[hsl(var(--info))]/20 text-[hsl(var(--primary))] flex items-center justify-center">
                {activeTab === 'roles' ? <Shield size={22} /> : <UserCircle size={22} />}
              </div>
              <div>
                <h3 className="text-sm font-semibold text-[hsl(var(--text-primary))] dark:text-white uppercase tracking-tight leading-none mb-1">
                  {title}
                </h3>
                <p className="mt-1 text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">
                  {subtitle}
                </p>
              </div>
            </div>
            {mode === 'list' && <ChevronRight size={18} className="text-[hsl(var(--text-secondary))]" />}
          </button>
        );
      })}
    </div>
  );

  const renderAccessBoard = () => (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
      {groupedRows.map((group) => (
        <section
          key={group.id}
          className="rounded-lg bg-[hsl(var(--surface-1))] dark:bg-white/[0.03] border border-[hsl(var(--border))] dark:border-white/10 p-3"
        >
          <div className="flex items-center justify-between mb-5">
            <span className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
              {group.label}
            </span>
            <span className="font-semibold text-[hsl(var(--text-secondary))]">{group.rows.length}</span>
          </div>
          <div className="space-y-3">
            {group.rows.map((row) => (
              <button
                key={row.id || row.name || row.username}
                onClick={() => handleOpenEntity(row)}
                className="w-full text-left bg-[hsl(var(--bg-primary))] dark:bg-white/[0.05] border border-[hsl(var(--border))] dark:border-white/5 rounded-lg p-4 hover:border-[hsl(var(--info)/30%)] transition-all"
              >
                <p className="text-sm font-semibold text-[hsl(var(--text-primary))] dark:text-white uppercase tracking-tight">
                  {activeTab === 'roles' ? row.name : row.username || row.email}
                </p>
                <p className="mt-2 text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">
                  {activeTab === 'roles' ? `${row.users_count || 0} usuarios` : row.role}
                </p>
              </button>
            ))}
          </div>
        </section>
      ))}
    </div>
  );

  const VALID_LEVELS: AdminModuleLevel[] = ['none', 'read', 'study', 'edit', 'manage'];

  // Build module list from taxonomy if available, fallback to local metadata.
  // Each entry carries the levels supported by the backend for that module.
  const moduleEntries = useMemo(() => {
    const source = taxonomy?.modules ? Object.keys(taxonomy.modules) : Object.keys(MODULE_META);
    const fallbackLevels: Record<string, AdminModuleLevel[]> = {
      academy: ['read', 'study', 'edit', 'manage'],
      messaging: ['read', 'edit'],
      wiki: ['read', 'edit'],
      default: ['read', 'edit', 'manage'],
    };
    return source.map((id) => {
      const meta = MODULE_META[id] || { label: id, icon: Shield, color: 'text-[hsl(var(--text-secondary))]' };
      const rawLevels = taxonomy?.modules?.[id] || fallbackLevels[id] || fallbackLevels.default;
      const levels = rawLevels
        .filter((lvl): lvl is AdminModuleLevel => VALID_LEVELS.includes(lvl as AdminModuleLevel))
        .filter((lvl) => lvl !== 'none');
      return { id, ...meta, levels };
    });
  }, [taxonomy]);

  return (
    <div className="flex flex-col h-full bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-1))] overflow-hidden animate-fade-in font-display">
      <style jsx global>{`
        .permission-card {
          transition: all 0.4s cubic-bezier(0.23, 1, 0.32, 1);
        }
        .permission-card:hover {
          transform: translateY(-2px);
          box-shadow: 0 20px 40px rgba(0, 0, 0, 0.03);
        }
      `}</style>

      <WorkspaceToolbar
        breadcrumbs={[
          { label: SITE_NAME, icon: Settings },
          { label: 'Seguridad y Accesos', icon: Lock },
        ]}
        viewType={viewType}
        setViewType={setViewType}
        availableViews={ACCESS_VIEWS}
        onSearch={setSearch}
        rightActions={
          <button
            onClick={handleCreateEntity}
            className="flex items-center gap-2 px-3 py-2 bg-[hsl(var(--primary))] text-white rounded-md text-[11px] font-semibold uppercase tracking-wide shadow-xl shadow-[hsl(var(--info)/20%)] active:scale-95 transition-all hover:bg-[hsl(var(--primary))]"
          >
            <Plus size={14} /> Crear Nuevo
          </button>
        }
      />

      {/* Cinematic Tab Navigation */}
      <div className="flex px-4 border-b border-[hsl(var(--border))] dark:border-white/5 bg-[hsl(var(--surface-1))]/50 dark:bg-white/5 shrink-0 relative overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_hsl(var(--primary)/0.05)_0%,_transparent_50%)] pointer-events-none" />
        <button
          onClick={() => setActiveTab('roles')}
          className={clsx(
            'px-4 py-2 text-[11px] font-semibold uppercase tracking-wide transition-all border-b-2 relative z-10',
            activeTab === 'roles'
              ? 'text-[hsl(var(--primary))] border-[hsl(var(--info)/100%)]'
              : 'text-[hsl(var(--text-secondary))] border-transparent hover:text-[hsl(var(--text-secondary))] hover:bg-white/50'
          )}
        >
          Roles Ministeriales
        </button>
        <button
          onClick={() => setActiveTab('users')}
          className={clsx(
            'px-4 py-2 text-[11px] font-semibold uppercase tracking-wide transition-all border-b-2 relative z-10',
            activeTab === 'users'
              ? 'text-[hsl(var(--primary))] border-[hsl(var(--info)/100%)]'
              : 'text-[hsl(var(--text-secondary))] border-transparent hover:text-[hsl(var(--text-secondary))] hover:bg-white/50'
          )}
        >
          Auditoría de Usuarios
        </button>
      </div>

      <main className="flex-1 overflow-y-auto scrollbar-thin p-3 lg:p-4">
        <div className="w-full">
          {loading ? (
            <div className="space-y-3">
              {[1, 2, 3, 4, 5, 6].map((i) => (
                <DSSkeleton key={i} className="h-8 w-full rounded-lg" />
              ))}
            </div>
          ) : currentRows.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-1.5 text-center">
              <div className="size-8 rounded-lg bg-[hsl(var(--surface-1))] dark:bg-white/5 flex items-center justify-center mb-3 border border-[hsl(var(--border))] dark:border-white/10">
                <Shield size={32} className="text-[hsl(var(--text-secondary))]" />
              </div>
              <h3 className="text-lg font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide mb-2">
                {activeTab === 'roles' ? 'Sin roles ministeriales' : 'Sin usuarios'}
              </h3>
              <p className="text-xs text-[hsl(var(--text-secondary))] font-medium max-w-md">
                {activeTab === 'roles'
                  ? 'Crea un nuevo rol ministerial para comenzar a gestionar permisos.'
                  : 'No hay usuarios registrados en la plataforma.'}
              </p>
            </div>
          ) : viewType === 'grid' ? (
            renderAccessCards('grid')
          ) : viewType === 'list' ? (
            renderAccessCards('list')
          ) : viewType === 'board' || viewType === 'kanban' ? (
            renderAccessBoard()
          ) : viewType === 'calendar' ? (
            <UniversalCalendarView
              events={calendarEvents}
              title={activeTab === 'roles' ? 'Calendario de roles' : 'Calendario de usuarios'}
              onEventClick={(event) => {
                const row = currentRows.find((entry, index) => (entry.id || index) === event.id);
                if (row) handleOpenEntity(row);
              }}
            />
          ) : viewType === 'gantt' ? (
            <UniversalGanttView
              items={ganttItems}
              moduleName={activeTab === 'roles' ? 'Roles y permisos' : 'Usuarios y accesos'}
              onItemClick={(item) => {
                const row = currentRows.find((entry, index) => (entry.id || index) === item.id);
                if (row) handleOpenEntity(row);
              }}
            />
          ) : viewType === 'wiki' ? (
            <UniversalWikiView moduleName="Seguridad y accesos" storageKey={`wiki_admin_access_${activeTab}`} />
          ) : (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-[hsl(var(--bg-primary))] dark:bg-white/5 rounded-lg border border-[hsl(var(--border))] dark:border-white/5 overflow-hidden shadow-sm"
            >
              <DataTable
                data={currentRows}
                columns={activeTab === 'roles' ? roleColumns : userColumns}
                onRowClick={handleOpenEntity}
              />
            </motion.div>
          )}
        </div>
      </main>

      <WorkspaceDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        title={selectedEntity?.name || selectedEntity?.username || 'Configurar Acceso'}
        subtitle={
          activeTab === 'roles'
            ? 'Matriz de Privilegios por Módulo'
            : 'Control de Identidad Individual'
        }
        actions={
          <div className="flex gap-3">
            <button
              className="px-3 py-2.5 bg-[hsl(var(--surface-2))] dark:bg-white/5 text-[hsl(var(--text-secondary))] rounded-md text-[11px] font-semibold uppercase tracking-wide hover:bg-[hsl(var(--surface-3))] transition-all"
              onClick={() => setIsDrawerOpen(false)}
            >
              Cerrar
            </button>
            <button
              disabled={isSaving}
              className="px-4 py-2.5 bg-[hsl(var(--primary))] text-white rounded-md text-[11px] font-semibold uppercase tracking-wide shadow-xl shadow-[hsl(var(--info)/20%)] flex items-center gap-2 hover:bg-[hsl(var(--primary))] active:scale-95 transition-all"
              onClick={handleSavePermissions}
            >
              {isSaving ? (
                <Loader2 className="animate-spin" size={14} />
              ) : (
                <Save size={14} />
              )}{' '}
              Guardar Cambios
            </button>
          </div>
        }
      >
        <div className="space-y-3 animate-in fade-in slide-in-from-right-4 duration-500">
          {/* Module Permission Matrix */}
          <section className="space-y-3">
            <div className="flex items-center justify-between px-2">
              <h4 className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide flex items-center gap-3">
                <Layout size={16} className="text-[hsl(var(--primary))]" /> Matriz de Operaciones
              </h4>
              <div className="flex items-center gap-2 px-3 py-1 bg-warning-soft dark:bg-[hsl(var(--warning))]/20 rounded-lg border border-[hsl(var(--warning)/20%)] dark:border-[hsl(var(--warning)/100%)]">
                <Shield size={10} className="text-warning-text" />
                <span className="font-semibold text-warning-text uppercase">Seguridad v3.9</span>
              </div>
            </div>

            {activeTab === 'users' && selectedEntity?.roleId && (
              <div className="px-2 flex items-center gap-2">
                <span className="text-xs text-[hsl(var(--text-secondary))]">Rol de plataforma:</span>
                <span className="text-xs font-semibold uppercase tracking-wide text-[hsl(var(--primary))]">
                  {roles.find((r) => r.id === selectedEntity.roleId)?.name || selectedEntity.role || 'Desconocido'}
                </span>
              </div>
            )}

            <div className="grid grid-cols-1 gap-4">
              {moduleEntries.map((mod) => (
                <PermissionRow
                  key={mod.id}
                  moduleId={mod.id}
                  label={mod.label}
                  icon={mod.icon}
                  color={mod.color}
                  availableLevels={mod.levels as AdminModuleLevel[]}
                  showReset={activeTab === 'users'}
                  effectiveLevel={effectivePermissions[mod.id] || 'none'}
                  overrideLevel={overridePermissions[mod.id] || 'none'}
                  onChange={(newLevel: AdminModuleLevel) =>
                    setOverridePermissions({ ...overridePermissions, [mod.id]: newLevel })
                  }
                />
              ))}
            </div>
          </section>

          {/* Industrial Disclaimer */}
          {/* Modular roles read-only section for users */}
          {activeTab === 'users' && userModuleRoles.length > 0 && (
            <section className="p-4 bg-[hsl(var(--surface-1))] dark:bg-white/5 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 space-y-3">
              <div className="flex items-center gap-2 text-[hsl(var(--text-secondary))] font-semibold uppercase tracking-wide text-[10px]">
                <Shield size={14} className="text-[hsl(var(--primary))]" /> Roles Modulares Asignados
              </div>
              <ul className="space-y-2">
                {userModuleRoles.map((mr) => {
                  const modularRole = roles.find((r) => r.id === mr.role_id);
                  return (
                    <li
                      key={mr.module}
                      className="flex items-center justify-between text-xs text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] bg-[hsl(var(--bg-primary))] dark:bg-black/20 rounded-md px-3 py-2"
                    >
                      <span className="font-semibold uppercase tracking-wide">{mr.module}</span>
                      <span className="text-[10px] text-[hsl(var(--text-secondary))]">
                        {modularRole?.name || mr.role_id}
                      </span>
                    </li>
                  );
                })}
              </ul>
            </section>
          )}

          <section className="p-4 bg-[hsl(var(--bg-muted))] rounded-lg text-white relative overflow-hidden group shadow-2xl">
            <div className="absolute top-0 right-0 p-3 opacity-10 group-hover:rotate-12 transition-transform duration-1000">
              <Lock size={80} />
            </div>
            <div className="relative z-10 space-y-4">
              <div className="flex items-center gap-3 text-[hsl(var(--primary))] font-semibold uppercase tracking-wide text-[10px]">
                <AlertCircle size={14} /> Protocolo de Seguridad
              </div>
              <p className="text-xs text-[hsl(var(--text-secondary))] leading-relaxed font-medium">
                {activeTab === 'roles'
                  ? 'Los cambios realizados en esta matriz afectarán inmediatamente el acceso de todos los usuarios vinculados a este rol. Asegúrese de validar el impacto antes de confirmar la misión.'
                  : 'Los permisos asignados aquí sobrescriben los del rol del usuario. Los niveles jerárquicos implican permisos inferiores (gestor incluye editor y lector).'}
              </p>
            </div>
          </section>
        </div>
      </WorkspaceDrawer>
    </div>
  );
}

interface PermissionRowProps {
  moduleId: string;
  label: string;
  icon: React.ElementType;
  color: string;
  availableLevels: AdminModuleLevel[];
  showReset: boolean;
  effectiveLevel: AdminModuleLevel;
  overrideLevel: AdminModuleLevel;
  onChange: (level: AdminModuleLevel) => void;
}

function PermissionRow({
  moduleId,
  label,
  icon: Icon,
  color,
  availableLevels,
  showReset,
  effectiveLevel,
  overrideLevel,
  onChange,
}: PermissionRowProps) {
  const activeLevel: AdminModuleLevel = overrideLevel !== 'none' ? overrideLevel : effectiveLevel;
  const hasOverride = overrideLevel !== 'none';

  const levelBtn = (level: AdminModuleLevel, icon: React.ElementType, tooltip: string) => {
    if (!availableLevels.includes(level) && level !== 'none') return null;
    return (
      <LevelBtn
        key={level}
        active={activeLevel === level}
        icon={icon}
        tooltip={tooltip}
        onClick={() => onChange(level)}
      />
    );
  };

  return (
    <div className="permission-card p-3 bg-[hsl(var(--surface-1))] dark:bg-white/5 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 flex items-center justify-between group">
      <div className="flex items-center gap-3">
        <div
          className={clsx(
            'size-7 rounded-[1.25rem] flex items-center justify-center bg-[hsl(var(--bg-primary))] dark:bg-black/40 shadow-sm border border-[hsl(var(--border))] dark:border-white/5 transition-all group-hover:scale-110 group-hover:rotate-3',
            color
          )}
        >
          <Icon size={24} strokeWidth={1.5} />
        </div>
        <div>
          <p className="text-sm font-semibold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] uppercase tracking-tight leading-none mb-1">
            {label}
          </p>
          <p className="text-[10px] text-[hsl(var(--text-secondary))] font-bold uppercase tracking-wide">
            Efectivo:{' '}
            <span className="text-[hsl(var(--primary))]">
              {LEVEL_LABELS[effectiveLevel] || effectiveLevel}
            </span>{' '}
            {hasOverride && (
              <span className="text-[hsl(var(--warning))]">
                (Override: {LEVEL_LABELS[overrideLevel] || overrideLevel})
              </span>
            )}
          </p>
        </div>
      </div>
      <div className="flex items-center gap-2">
        {showReset && hasOverride && (
          <button
            title="Restablecer al rol de plataforma"
            aria-label="Restablecer al rol de plataforma"
            onClick={() => onChange('none')}
            className="p-2 rounded-md text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] transition-colors"
          >
            <Undo2 size={16} />
          </button>
        )}
        <div className="flex bg-[hsl(var(--bg-primary))] dark:bg-black/40 p-1.5 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 shadow-inner">
          {levelBtn('none', XCircle, 'Sin Acceso')}
          {levelBtn('read', Eye, 'Solo Lectura')}
          {moduleId === 'academy' && levelBtn('study', BookOpen, 'Estudiante')}
          {levelBtn('edit', Edit3, 'Escritura')}
          {levelBtn('manage', Shield, 'Administrador')}
        </div>
      </div>
    </div>
  );
}

interface LevelBtnProps {
  active: boolean;
  icon: React.ElementType;
  tooltip: string;
  onClick: () => void;
}

function LevelBtn({ active, icon: Icon, tooltip, onClick }: LevelBtnProps) {
  return (
    <button
      title={tooltip}
      onClick={onClick}
      className={clsx(
        'p-2 rounded-md transition-all duration-300 relative group/btn',
        active
          ? 'bg-[hsl(var(--bg-muted))] dark:bg-[hsl(var(--bg-primary))] text-white dark:text-[hsl(var(--text-primary))] shadow-xl scale-110'
          : 'text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-secondary))] dark:hover:text-[hsl(var(--text-secondary))]'
      )}
    >
      <Icon size={16} />
      {active && (
        <motion.div
          layoutId="level-indicator"
          className="absolute -bottom-1 left-1/2 -translate-x-1/2 w-1 h-1 bg-current rounded-full"
        />
      )}
    </button>
  );
}
