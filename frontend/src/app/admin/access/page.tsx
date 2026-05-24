"use client";

import React, { useState, useEffect, useMemo, useCallback } from 'react';
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
import Skeleton from '@/components/ui/Skeleton';
import { motion } from 'framer-motion';
import clsx from 'clsx';

const ACCESS_VIEWS: ViewType[] = ['table', 'list', 'grid', 'board', 'kanban', 'calendar', 'gantt', 'wiki'];

const MODULES = [
    { id: 'crm', label: 'CRM Pastoral', icon: Users, color: 'text-blue-500' },
    { id: 'academy', label: 'Academia Faro', icon: BookOpen, color: 'text-emerald-500' },
    { id: 'projects', label: 'Proyectos', icon: ClipboardList, color: 'text-indigo-500' },
    { id: 'finance', label: 'Finanzas', icon: Lock, color: 'text-amber-500' },
    { id: 'cms', label: 'Sitio Web', icon: Layout, color: 'text-purple-500' },
    { id: 'messaging', label: 'Mensajería', icon: Edit3, color: 'text-cyan-500' },
];

// Maps UI level names → backend level names and vice versa
const UI_LEVEL_MAP: Record<string, string> = {
    admin: 'manage',
    write: 'edit',
    read: 'read',
    study: 'study',
    manage: 'admin',
    edit: 'write',
};
const BACKEND_LEVELS: Record<string, number> = {
    manage: 3, edit: 2, study: 2, read: 1,
};

// Module → backend levels → expanded permission keys
const PERMISSION_SCOPE: Record<string, Record<string, string[]>> = {
    crm:      { read: ['crm:read'], edit: ['crm:read', 'crm:edit'], manage: ['crm:read', 'crm:edit', 'crm:manage'] },
    finance:  { read: ['finance:read'], edit: ['finance:read', 'finance:edit'], manage: ['finance:read', 'finance:edit', 'finance:manage'] },
    projects: { read: ['projects:read'], edit: ['projects:read', 'projects:edit'], manage: ['projects:read', 'projects:edit', 'projects:manage'] },
    cms:      { read: ['cms:read'], edit: ['cms:read', 'cms:edit'], manage: ['cms:read', 'cms:edit', 'cms:manage'] },
    academy:  { read: ['academy:read'], study: ['academy:read', 'academy:study'], edit: ['academy:read', 'academy:study', 'academy:edit'], manage: ['academy:read', 'academy:study', 'academy:edit', 'academy:manage'] },
    messaging: { read: ['messaging:read'], edit: ['messaging:read', 'messaging:edit'] },
};

/** Convert any permission format (array of strings, flat dict, module dict) to module→UI-level map */
function toModuleLevelMap(perms: unknown): Record<string, string> {
    if (!perms || typeof perms !== 'object') return {};
    const result: Record<string, string> = {};
    if (Array.isArray(perms)) {
        for (const p of perms) {
            if (typeof p !== 'string') continue;
            const [mod, lvl] = p.split(':');
            if (!mod || !lvl) continue;
            const weight = BACKEND_LEVELS[lvl] ?? 0;
            const current = BACKEND_LEVELS[result[mod] as keyof typeof BACKEND_LEVELS] ?? -1;
            if (weight > current) {
                result[mod] = UI_LEVEL_MAP[lvl] || lvl;
            }
        }
    } else {
        const dict = perms as Record<string, unknown>;
        for (const [key, val] of Object.entries(dict)) {
            if (key.includes(':')) {
                // "crm:read" → "manage"  or  "crm:read" → true
                const [mod, lvl] = key.split(':');
                if (!mod || !lvl) continue;
                const backendLevel = typeof val === 'string' ? val : lvl;
                const weight = BACKEND_LEVELS[backendLevel as keyof typeof BACKEND_LEVELS] ?? 0;
                const current = BACKEND_LEVELS[result[mod] as keyof typeof BACKEND_LEVELS] ?? -1;
                if (weight > current) {
                    result[mod] = UI_LEVEL_MAP[backendLevel] || backendLevel;
                }
            } else {
                // Module-level: "crm" → "manage" (backend format) or "crm" → "admin" (UI format)
                const backendLevel = typeof val === 'string' ? val : '';
                if (!backendLevel) continue;
                result[key] = UI_LEVEL_MAP[backendLevel] || backendLevel;
            }
        }
    }
    return result;
}

/** Convert UI module-level map to flat permission keys for role storage */
function flattenModuleMap(moduleMap: Record<string, string>): Record<string, string> {
    const flat: Record<string, string> = {};
    for (const [mod, uiLevel] of Object.entries(moduleMap)) {
        if (!uiLevel || uiLevel === 'none') continue;
        const backendLevel = UI_LEVEL_MAP[uiLevel] || uiLevel;
        const scope = PERMISSION_SCOPE[mod];
        if (!scope) continue;
        const perms = scope[backendLevel];
        if (!perms) continue;
        for (const p of perms) {
            flat[p] = backendLevel;
        }
    }
    return flat;
}

export default function AccessManagementPage() {
    const { token, isAuthenticated } = useAuth();
    const { addToast } = useToast();
    const [activeTab, setActiveTab] = useState<'roles' | 'users'>('roles');
    const [roles, setRoles] = useState<any[]>([]);
    const [users, setUsers] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedEntity, setSelectedEntity] = useState<any>(null);
    const [isDrawerOpen, setIsDrawerOpen] = useState(false);
    const [isSaving, setIsAssigning] = useState(false);
    const [viewType, setViewType] = useState<ViewType>('table');
    const [search, setSearch] = useState('');

    // State for local permission editing
    const [localPermissions, setLocalPermissions] = useState<Record<string, string>>({});

    const fetchData = useCallback(async () => {
        if (!token) return;
        setLoading(true);
        try {
            const [rolesData, usersData] = await Promise.all([
                apiFetch<any[]>('/admin/roles', { token, cache: 'no-store' }),
                apiFetch<any[]>('/admin/users', { token, cache: 'no-store' })
            ]);
            setRoles(Array.isArray(rolesData) ? rolesData : []);
            setUsers(Array.isArray(usersData) ? usersData : []);
        } catch (err) { 
            console.error(err);
            addToast("Error al cargar configuraciones de acceso", "error");
        } finally { 
            setLoading(false); 
        }
    }, [token, addToast]);

    useEffect(() => {
        if (isAuthenticated) fetchData();
    }, [isAuthenticated, fetchData]);

    const handleOpenEntity = async (entity: any) => {
        setSelectedEntity(entity);

        if (activeTab === 'users' && token) {
            try {
                const permData = await apiFetch<any>(`/admin/users/${entity.id}/permissions`, { token });
                const overrides = permData?.override_permissions || {};
                setLocalPermissions(toModuleLevelMap(overrides));
            } catch {
                addToast("Error al cargar permisos del usuario", "error");
                setLocalPermissions(toModuleLevelMap(entity.permissions));
            }
        } else {
            setLocalPermissions(toModuleLevelMap(entity.permissions));
        }

        setIsDrawerOpen(true);
    };

    const handleSavePermissions = async () => {
        if (!selectedEntity || !token) return;
        setIsAssigning(true);
        try {
            if (activeTab === 'roles') {
                const flatPerms = flattenModuleMap(localPermissions);
                await apiFetch(`/admin/roles/${selectedEntity.id}`, {
                    method: 'PATCH',
                    token,
                    body: { permissions: flatPerms },
                });
                addToast("Permisos del rol actualizados", "success");
            } else {
                // Map UI levels (admin→manage, write→edit) to backend module permissions
                const levelMap: Record<string, string> = {};
                for (const [module, level] of Object.entries(localPermissions)) {
                    if (level === 'none' || !level) continue;
                    const mappedLevel = level === 'admin' ? 'manage' : level === 'write' ? 'edit' : level;
                    levelMap[module] = mappedLevel;
                }
                await apiFetch(`/admin/users/${selectedEntity.id}/permissions`, {
                    method: 'PUT',
                    token,
                    body: levelMap,
                });
                addToast("Permisos de usuario actualizados", "success");
            }
            setIsDrawerOpen(false);
            fetchData();
        } catch {
            addToast("Error al guardar cambios", "error");
        } finally {
            setIsAssigning(false);
        }
    };

    const roleColumns = useMemo<ColumnDef<any>[]>(() => [
        { 
            accessorKey: 'name', 
            header: 'Nombre del Rol', 
            cell: info => (
                <div className="flex items-center gap-3">
                    <div className="size-8 rounded-lg bg-blue-50 dark:bg-blue-900/20 flex items-center justify-center text-blue-600 shadow-sm">
                        <Shield size={16} />
                    </div>
                    <span className="font-semibold text-slate-800 dark:text-white uppercase tracking-tight">{info.getValue() as string}</span>
                </div>
            ) 
        },
        { 
            accessorKey: 'users_count', 
            header: 'Usuarios', 
            cell: info => (
                <div className="flex items-center gap-2">
                    <div className="flex -space-x-2">
                        {[1,2,3].slice(0, info.getValue() as number).map(i => (
                            <div key={i} className="size-6 rounded-full border-2 border-white dark:border-slate-800 bg-slate-100 flex items-center justify-center text-[8px] font-bold text-slate-400 uppercase">U</div>
                        ))}
                    </div>
                    <span className="text-[11px] font-bold text-slate-500 ml-2">{info.getValue() as number} vinculados</span>
                </div>
            ) 
        },
        { 
            id: 'actions', 
            header: '', 
            cell: () => <button className="p-2 hover:bg-slate-100 dark:hover:bg-white/5 rounded-md text-slate-400 opacity-0 group-hover:opacity-100 transition-all"><ChevronRight size={18} /></button> 
        }
    ], []);

    const userColumns = useMemo<ColumnDef<any>[]>(() => [
        { 
            accessorKey: 'username', 
            header: 'Usuario', 
            cell: info => (
                <div className="flex items-center gap-3">
                    <div className="size-8 rounded-full bg-slate-100 dark:bg-white/5 flex items-center justify-center text-slate-400 border border-slate-200 dark:border-white/10 shadow-inner">
                        <UserCircle size={18} />
                    </div>
                    <div className="flex flex-col">
                        <span className="text-[13px] font-bold text-slate-800 dark:text-slate-100">{info.getValue() as string}</span>
                        <span className="text-[10px] text-slate-400 font-medium">#{info.row.original.id}</span>
                    </div>
                </div>
            ) 
        },
        { accessorKey: 'email', header: 'Email', cell: info => <span className="text-[12px] text-slate-500">{info.getValue() as string}</span> },
        { 
            accessorKey: 'role', 
            header: 'Rol Asignado', 
            cell: info => (
                <span className="px-3 py-1 bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 rounded-lg text-[9px] font-semibold uppercase tracking-wide border border-blue-100 dark:border-blue-800">
                    {info.getValue() as string}
                </span>
            ) 
        },
        { 
            accessorKey: 'is_active', 
            header: 'Estado', 
            cell: info => (
                <div className="flex items-center gap-2">
                    <div className={clsx("size-2 rounded-full", info.getValue() ? "bg-emerald-500 shadow-[0_0_8px_#10b981]" : "bg-slate-300")} />
                    <span className="text-[10px] font-semibold uppercase text-slate-400 tracking-wide">{info.getValue() ? 'Activo' : 'Inactivo'}</span>
                </div>
            ) 
        }
    ], []);

    const handleCreateEntity = useCallback(() => {
        if (activeTab === 'roles') {
            const name = prompt('Nombre del nuevo rol ministerial:');
            if (!name?.trim()) return;
            setIsAssigning(true);
            apiFetch('/admin/roles', {
                method: 'POST',
                token,
                body: { name: name.trim(), permissions: {} },
            }).then(() => {
                addToast(`Rol "${name.trim()}" creado`, 'success');
                fetchData();
            }).catch(() => addToast('Error al crear rol', 'error'))
            .finally(() => setIsAssigning(false));
        } else {
            addToast('Usa el panel de administración de usuarios', 'info');
        }
    }, [activeTab, token, addToast, fetchData]);

    const currentRows = (activeTab === 'roles' ? roles : users).filter((row) => {
        const term = search.trim().toLowerCase();
        if (!term) return true;
        return `${row.name || ''} ${row.username || ''} ${row.email || ''} ${row.role || ''}`.toLowerCase().includes(term);
    });

    const groupedRows = activeTab === 'roles'
        ? [
            { id: 'admin', label: 'Administración', rows: currentRows.filter(row => `${row.name || ''}`.toLowerCase().includes('admin')) },
            { id: 'ministry', label: 'Ministeriales', rows: currentRows.filter(row => !`${row.name || ''}`.toLowerCase().includes('admin')) },
        ]
        : [
            { id: 'active', label: 'Activos', rows: currentRows.filter(row => row.is_active !== false) },
            { id: 'inactive', label: 'Inactivos', rows: currentRows.filter(row => row.is_active === false) },
        ];

    const calendarEvents = currentRows.map((row, index) => ({
        id: row.id || index,
        title: activeTab === 'roles' ? row.name || `Rol #${row.id}` : row.username || row.email || `Usuario #${row.id}`,
        date: (row.created_at || row.updated_at || new Date().toISOString()).split('T')[0],
        color: activeTab === 'roles' ? 'blue' as const : row.is_active === false ? 'rose' as const : 'emerald' as const,
        location: activeTab === 'roles' ? `${row.users_count || 0} usuarios` : row.role,
    }));

    const ganttItems = currentRows.map((row, index) => {
        const start = row.created_at || row.updated_at || new Date().toISOString();
        return {
            id: row.id || index,
            title: activeTab === 'roles' ? row.name || `Rol #${row.id}` : row.username || row.email || `Usuario #${row.id}`,
            subtitle: activeTab === 'roles' ? `${row.users_count || 0} usuarios` : row.role || row.email,
            start_date: start,
            end_date: row.updated_at || start,
            color: activeTab === 'roles' ? 'blue' as const : row.is_active === false ? 'rose' as const : 'emerald' as const,
            progress: activeTab === 'roles' ? 80 : row.is_active === false ? 20 : 100,
        };
    });

    const renderAccessCards = (mode: 'grid' | 'list') => (
        <div className={clsx(mode === 'grid' ? 'grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3' : 'space-y-4')}>
            {currentRows.map((row) => {
                const title = activeTab === 'roles' ? row.name : row.username || row.email;
                const subtitle = activeTab === 'roles' ? `${row.users_count || 0} usuarios vinculados` : `${row.email || 'Sin email'} · ${row.role || 'Sin rol'}`;
                return (
                    <button
                        key={row.id || title}
                        onClick={() => handleOpenEntity(row)}
                        className={clsx(
                            'text-left bg-white dark:bg-white/5 border border-slate-100 dark:border-white/5 rounded-lg p-3 hover:border-blue-300 hover:shadow-xl transition-all',
                            mode === 'list' && 'flex items-center justify-between gap-4'
                        )}
                    >
                        <div className="flex items-center gap-4">
                            <div className="size-7 rounded-lg bg-blue-50 dark:bg-blue-900/20 text-blue-600 flex items-center justify-center">
                                {activeTab === 'roles' ? <Shield size={22} /> : <UserCircle size={22} />}
                            </div>
                            <div>
                                <h3 className="text-sm font-semibold text-slate-900 dark:text-white uppercase tracking-tight">{title}</h3>
                                <p className="mt-1 text-[10px] font-bold text-slate-400 uppercase tracking-wide">{subtitle}</p>
                            </div>
                        </div>
                        {mode === 'list' && <ChevronRight size={18} className="text-slate-300" />}
                    </button>
                );
            })}
        </div>
    );

    const renderAccessBoard = () => (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
            {groupedRows.map((group) => (
                <section key={group.id} className="rounded-lg bg-slate-50 dark:bg-white/[0.03] border border-slate-200 dark:border-white/10 p-3">
                    <div className="flex items-center justify-between mb-5">
                        <span className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">{group.label}</span>
                        <span className="font-semibold text-slate-400">{group.rows.length}</span>
                    </div>
                    <div className="space-y-3">
                        {group.rows.map((row) => (
                            <button key={row.id || row.name || row.username} onClick={() => handleOpenEntity(row)} className="w-full text-left bg-white dark:bg-white/[0.05] border border-slate-100 dark:border-white/5 rounded-lg p-4 hover:border-blue-300 transition-all">
                                <p className="text-sm font-semibold text-slate-900 dark:text-white uppercase tracking-tight">{activeTab === 'roles' ? row.name : row.username || row.email}</p>
                                <p className="mt-2 text-[10px] font-bold text-slate-400 uppercase tracking-wide">{activeTab === 'roles' ? `${row.users_count || 0} usuarios` : row.role}</p>
                            </button>
                        ))}
                    </div>
                </section>
            ))}
        </div>
    );

    return (
        <div className="flex flex-col h-full bg-white dark:bg-[#1e1f21] overflow-hidden animate-fade-in font-display">
            <style jsx global>{`
                .permission-card {
                    transition: all 0.4s cubic-bezier(0.23, 1, 0.32, 1);
                }
                .permission-card:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 20px 40px rgba(0,0,0,0.03);
                }
            `}</style>

            <WorkspaceToolbar 
                breadcrumbs={[{ label: 'CCF Platform', icon: Settings }, { label: 'Seguridad y Accesos', icon: Lock }]}
                viewType={viewType}
                setViewType={setViewType}
                availableViews={ACCESS_VIEWS}
                onSearch={setSearch}
                rightActions={
                    <button onClick={handleCreateEntity} className="flex items-center gap-2 px-3 py-2 bg-blue-600 text-white rounded-md text-[11px] font-semibold uppercase tracking-wide shadow-xl shadow-blue-500/20 active:scale-95 transition-all hover:bg-blue-700">
                        <Plus size={14} /> Crear Nuevo
                    </button>
                }
            />

            {/* Cinematic Tab Navigation */}
            <div className="flex px-4 border-b border-slate-100 dark:border-white/5 bg-slate-50/50 dark:bg-white/5 shrink-0 relative overflow-hidden">
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_#1973f005_0%,_transparent_50%)] pointer-events-none" />
                <button onClick={() => setActiveTab('roles')} className={clsx("px-4 py-2 text-[11px] font-semibold uppercase tracking-wide transition-all border-b-2 relative z-10", activeTab === 'roles' ? "text-blue-600 border-blue-600" : "text-slate-400 border-transparent hover:text-slate-600 hover:bg-white/50")}>Roles Ministeriales</button>
                <button onClick={() => setActiveTab('users')} className={clsx("px-4 py-2 text-[11px] font-semibold uppercase tracking-wide transition-all border-b-2 relative z-10", activeTab === 'users' ? "text-blue-600 border-blue-600" : "text-slate-400 border-transparent hover:text-slate-600 hover:bg-white/50")}>Auditoría de Usuarios</button>
            </div>

            <main className="flex-1 overflow-y-auto scrollbar-thin p-3 lg:p-4">
                <div className="max-w-[1400px] mx-auto">
                    {loading ? (
                        <div className="space-y-3">
                            {[1,2,3,4,5,6].map(i => <Skeleton key={i} className="h-8 w-full rounded-lg" />)}
                        </div>
                    ) : currentRows.length === 0 ? (
                        <div className="flex flex-col items-center justify-center py-1.5 text-center">
                            <div className="size-8 rounded-lg bg-slate-50 dark:bg-white/5 flex items-center justify-center mb-3 border border-slate-200 dark:border-white/10">
                                <Shield size={32} className="text-slate-300" />
                            </div>
                            <h3 className="text-lg font-bold text-slate-400 uppercase tracking-wide mb-2">
                                {activeTab === 'roles' ? 'Sin roles ministeriales' : 'Sin usuarios'}
                            </h3>
                            <p className="text-xs text-slate-400 font-medium max-w-md">
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
                            className="bg-white dark:bg-white/5 rounded-lg border border-slate-100 dark:border-white/5 overflow-hidden shadow-sm"
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
                isOpen={isDrawerOpen} onClose={() => setIsDrawerOpen(false)}
                title={selectedEntity?.name || selectedEntity?.username || 'Configurar Acceso'}
                subtitle={activeTab === 'roles' ? 'Matriz de Privilegios por Módulo' : 'Control de Identidad Individual'}
                actions={
                    <div className="flex gap-3">
                        <button className="px-3 py-2.5 bg-slate-100 dark:bg-white/5 text-slate-500 rounded-md text-[11px] font-semibold uppercase tracking-wide hover:bg-slate-200 transition-all" onClick={() => setIsDrawerOpen(false)}>Cerrar</button>
                        <button 
                            disabled={isSaving}
                            className="px-4 py-2.5 bg-blue-600 text-white rounded-md text-[11px] font-semibold uppercase tracking-wide shadow-xl shadow-blue-500/20 flex items-center gap-2 hover:bg-blue-700 active:scale-95 transition-all" 
                            onClick={handleSavePermissions}
                        >
                            {isSaving ? <Loader2 className="animate-spin" size={14} /> : <Save size={14} />} Guardar Cambios
                        </button>
                    </div>
                }
            >
                <div className="space-y-3 animate-in fade-in slide-in-from-right-4 duration-500">
                    {/* Module Permission Matrix */}
                    <section className="space-y-3">
                        <div className="flex items-center justify-between px-2">
                            <h4 className="font-semibold text-slate-400 uppercase tracking-wide flex items-center gap-3">
                                <Layout size={16} className="text-blue-500" /> Matriz de Operaciones
                            </h4>
                            <div className="flex items-center gap-2 px-3 py-1 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-100 dark:border-amber-800">
                                <Shield size={10} className="text-amber-600" />
                                <span className="font-semibold text-amber-700 uppercase">Seguridad v3.9</span>
                            </div>
                        </div>
                        
                        <div className="grid grid-cols-1 gap-4">
                            {MODULES.map((mod) => (
                                <PermissionRow
                                    key={mod.id}
                                    moduleId={mod.id}
                                    label={mod.label}
                                    icon={mod.icon}
                                    color={mod.color}
                                    level={localPermissions[mod.id] || 'none'}
                                    onChange={(newLevel: string) => setLocalPermissions({ ...localPermissions, [mod.id]: newLevel })}
                                />
                            ))}
                        </div>
                    </section>

                    {/* Industrial Disclaimer */}
                    <section className="p-4 bg-slate-900 rounded-lg text-white relative overflow-hidden group shadow-2xl">
                        <div className="absolute top-0 right-0 p-3 opacity-10 group-hover:rotate-12 transition-transform duration-1000"><Lock size={80} /></div>
                        <div className="relative z-10 space-y-4">
                            <div className="flex items-center gap-3 text-blue-400 font-semibold uppercase tracking-wide text-[10px]">
                                <AlertCircle size={14} /> Protocolo de Seguridad
                            </div>
                            <p className="text-xs text-slate-300 leading-relaxed font-medium">
                                {activeTab === 'roles'
                                    ? 'Los cambios realizados en esta matriz afectarán inmediatamente el acceso de todos los usuarios vinculados a este rol. Asegúrese de validar el impacto antes de confirmar la misión.'
                                    : 'Los permisos asignados aquí sobrescriben los del rol del usuario. Los niveles jerárquicos implican permisos inferiores (gestor incluye editor y lector).'
                                }
                            </p>
                        </div>
                    </section>
                </div>
            </WorkspaceDrawer>
        </div>
    );
}

const LEVEL_LABELS: Record<string, string> = {
    none: 'Bloqueado', read: 'Lector', study: 'Estudiante', write: 'Editor', admin: 'Gestor',
};

function PermissionRow({ moduleId, label, icon: Icon, color, level, onChange }: any) {
    return (
        <div className="permission-card p-3 bg-slate-50 dark:bg-white/5 rounded-lg border border-slate-100 dark:border-white/10 flex items-center justify-between group">
            <div className="flex items-center gap-3">
                <div className={clsx("size-7 rounded-[1.25rem] flex items-center justify-center bg-white dark:bg-black/40 shadow-sm border border-slate-100 dark:border-white/5 transition-all group-hover:scale-110 group-hover:rotate-3", color)}>
                    <Icon size={24} strokeWidth={1.5} />
                </div>
                <div>
                    <p className="text-sm font-semibold text-slate-800 dark:text-slate-100 uppercase tracking-tight leading-none mb-1">{label}</p>
                    <p className="text-[10px] text-slate-400 font-bold uppercase tracking-wide">Estado: <span className="text-blue-500">{LEVEL_LABELS[level] || level}</span></p>
                </div>
            </div>
            <div className="flex bg-white dark:bg-black/40 p-1.5 rounded-lg border border-slate-200 dark:border-white/10 shadow-inner">
                <LevelBtn active={level === 'none'} icon={XCircle} tooltip="Sin Acceso" onClick={() => onChange('none')} />
                <LevelBtn active={level === 'read'} icon={Eye} tooltip="Solo Lectura" onClick={() => onChange('read')} />
                {moduleId === 'academy' && <LevelBtn active={level === 'study'} icon={BookOpen} tooltip="Estudiante" onClick={() => onChange('study')} />}
                <LevelBtn active={level === 'write'} icon={Edit3} tooltip="Escritura" onClick={() => onChange('write')} />
                <LevelBtn active={level === 'admin'} icon={Shield} tooltip="Administrador" onClick={() => onChange('admin')} />
            </div>
        </div>
    );
}

function LevelBtn({ active, icon: Icon, tooltip, onClick }: any) {
    return (
        <button 
            title={tooltip}
            onClick={onClick}
            className={clsx(
                "p-2 rounded-md transition-all duration-300 relative group/btn",
                active ? "bg-slate-900 dark:bg-white text-white dark:text-slate-900 shadow-xl scale-110" : "text-slate-300 hover:text-slate-600 dark:hover:text-slate-200"
            )}
        >
            <Icon size={16} />
            {active && <motion.div layoutId="level-indicator" className="absolute -bottom-1 left-1/2 -translate-x-1/2 w-1 h-1 bg-current rounded-full" />}
        </button>
    );
}

