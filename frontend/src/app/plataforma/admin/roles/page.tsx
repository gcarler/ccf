'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import AdminShell from '@/components/admin/AdminShell';
import AdminHero from '@/components/admin/AdminHero';
import ConfirmActionDrawer, { type ConfirmActionState } from '@/components/ConfirmActionDrawer';
import { Shield, Plus, Check, Save, Trash2 } from 'lucide-react';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';

interface Role {
    id: string;
    name: string;
    permissions: string[];
}

// Raw shape emitted by backend AdminRoleRead (schemas/admin.py:51-57).
// Key/value names are in Spanish; we normalize to the local Role form below.
interface AdminRoleRaw {
    id: string;
    nombre: string;
    permisos: Record<string, unknown> | string[] | null;
    users_count?: number;
}

export default function RolesPage() {
    const { token } = useAuth();
    const { addToast } = useToast();
    const [roles, setRoles] = useState<Role[]>([]);
    const [permissionsMap, setPermissionsMap] = useState<Record<string, string>>({});
    const [loading, setLoading] = useState(true);

    const [isDrawerOpen, setIsDrawerOpen] = useState(false);
    const [confirmAction, setConfirmAction] = useState<ConfirmActionState>(null);
    const [editingRole, setEditingRole] = useState<Partial<Role>>({
        name: '',
        permissions: []
    });

    const fetchData = useCallback(async (signal?: AbortSignal) => {
        setLoading(true);
        try {
            const [rolesRes, permsRes] = await Promise.all([
                apiFetch<{ items: AdminRoleRaw[]; total: number }>('/admin/roles', { token, signal }),
                apiFetch<Record<string, string>>('/admin/permissions', { token, signal })
            ]);
            const items = rolesRes?.items ?? [];
            const mapped = items.map((r: AdminRoleRaw) => ({
                id: r.id,
                name: r.nombre,
                permissions: r.permisos ? Object.keys(r.permisos) : [],
            }));
            setRoles(mapped);
            setPermissionsMap(permsRes || {});
        } catch (err: unknown) {
            if (err instanceof DOMException && err.name === 'AbortError') return;
            addToast("Error al cargar roles", "error");
        } finally {
            setLoading(false);
        }
    }, [token, addToast]);

    useEffect(() => {
        const controller = new AbortController();
        fetchData(controller.signal);
        return () => controller.abort();
    }, [fetchData]);

    const openCreateDrawer = () => {
        setEditingRole({ name: '', permissions: [] });
        setIsDrawerOpen(true);
    };

    const openEditDrawer = (role: Role) => {
        setEditingRole({ ...role });
        setIsDrawerOpen(true);
    };

    const togglePermission = (permKey: string) => {
        const current = editingRole.permissions || [];
        if (current.includes(permKey)) {
            setEditingRole({ ...editingRole, permissions: current.filter((p: string) => p !== permKey) });
        } else {
            setEditingRole({ ...editingRole, permissions: [...current, permKey] });
        }
    };

    const handleSaveRole = async () => {
        if (!editingRole.name) {
            addToast("El rol debe tener un nombre", "warning");
            return;
        }
        try {
            if (editingRole.id) {
                const permDict: Record<string, string> = {};
                for (const p of (editingRole.permissions || [])) {
                    permDict[p] = 'allow';
                }
                await apiFetch(`/admin/roles/${editingRole.id}`, {
                    method: 'PATCH',
                    token,
                    body: { permisos: permDict }
                });
                addToast("Rol actualizado", "success");
            } else {
                await apiFetch('/admin/roles', {
                    method: 'POST',
                    token,
                    body: { nombre: editingRole.name, permisos: {} }
                });
                addToast("Rol creado", "success");
            }
            setIsDrawerOpen(false);
            fetchData();
        } catch (e: unknown) {
            addToast(e instanceof Error ? e.message : "Error al guardar", "error");
        }
    };

    const handleDelete = async (e: React.MouseEvent, id: string) => {
        e.stopPropagation();
        setConfirmAction({
            title: 'Eliminar rol',
            description: 'Esta acción elimina la definición del rol y puede afectar permisos ya asignados.',
            destructive: true,
            confirmLabel: 'Eliminar rol',
            onConfirm: async () => {
                try {
                    await apiFetch(`/admin/roles/${id}`, {
                        method: 'DELETE',
                        token
                    });
                    addToast("Rol eliminado", "success");
                    fetchData();
                } catch (e: unknown) {
                    addToast(e instanceof Error ? e.message : "Error al eliminar", "error");
                }
            },
        });
    };

    // Agrupar permisos para UI
    const getGroupedPermissions = () => {
        const groups: Record<string, string[]> = {
            'Sistema': [],
            'Perfil': [],
            'CRM': [],
            'Academia': [],
            'CMS': [],
            'Finanzas': [],
            'Proyectos': [],
            'Otros': []
        };
        Object.keys(permissionsMap).forEach(key => {
            if (key.startsWith('system:')) groups['Sistema'].push(key);
            else if (key.startsWith('profile:')) groups['Perfil'].push(key);
            else if (key.startsWith('crm:')) groups['CRM'].push(key);
            else if (key.startsWith('academy:')) groups['Academia'].push(key);
            else if (key.startsWith('cms:')) groups['CMS'].push(key);
            else if (key.startsWith('finance:')) groups['Finanzas'].push(key);
            else if (key.startsWith('projects:')) groups['Proyectos'].push(key);
            else groups['Otros'].push(key);
        });
        return groups;
    };

    const groupedPerms = getGroupedPermissions();

    return (
        <AdminShell breadcrumbs={[{ label: 'Administración', href: '/plataforma/admin' }, { label: 'Roles', href: '/plataforma/admin/roles' }]}>
            <AdminHero 
                title="Gestión de Roles"
                description="Configura los permisos granulares (RBAC) para el sistema"
                primaryAction={{
                    label: "Crear Rol Personalizado",
                    icon: Plus,
                    onClick: openCreateDrawer,
                    variant: "primary"
                }}
            />

 <div className="w-full p-4 relative z-10 -mt-3">
                {loading ? (
                    <div className="flex items-center justify-center h-48">
                        <div className="animate-spin rounded-full h-8 w-12 border-b-2 border-[hsl(var(--border))]"></div>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                        {roles.map(role => (
                            <div 
                                key={role.id}
                                onClick={() => openEditDrawer(role)}
                                className="bg-[hsl(var(--bg-primary))] rounded-lg p-3 border border-[hsl(var(--border))] shadow-xl shadow-black/10/20 hover:shadow-2xl hover:-translate-y-1 transition-all cursor-pointer group"
                            >
                                <div className="flex items-center justify-between mb-4">
                                    <div className="flex items-center gap-3">
                                        <div className="w-10 h-10 rounded-md bg-blue-50 text-[hsl(var(--primary))] flex items-center justify-center">
                                            <Shield size={20} />
                                        </div>
                                        <h3 className="font-bold text-[hsl(var(--text-primary))]">{role.name}</h3>
                                    </div>
                                    <button onClick={(e) => handleDelete(e, role.id)} className="opacity-0 group-hover:opacity-100 p-2 text-[hsl(var(--text-secondary))] hover:text-rose-500 hover:bg-rose-50 rounded-lg transition-all">
                                        <Trash2 size={16} />
                                    </button>
                                </div>
                                <div className="space-y-3">
                                    <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                                        {role.permissions.length} Permisos Activos
                                    </p>
                                    <div className="flex flex-wrap gap-1.5">
                                        {role.permissions.slice(0, 5).map((p: string) => (
                                            <span key={p} className="px-2 py-1 bg-[hsl(var(--surface-1))] text-[hsl(var(--text-secondary))] rounded-md text-[10px] font-bold border border-[hsl(var(--border))]">
                                                {p}
                                            </span>
                                        ))}
                                        {role.permissions.length > 5 && (
                                            <span className="px-2 py-1 bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))] rounded-md text-[10px] font-bold">
                                                +{role.permissions.length - 5}
                                            </span>
                                        )}
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* ─── Drawer de Edición ─── */}
            <WorkspaceDrawer
                isOpen={isDrawerOpen}
                onClose={() => setIsDrawerOpen(false)}
                title={editingRole.id ? "Editar Rol" : "Nuevo Rol"}
                subtitle="Configura los alcances de este perfil"
                actions={
                    <button onClick={handleSaveRole} className="flex items-center gap-2 px-3 py-2 bg-[hsl(var(--bg-muted))] text-white rounded-lg text-xs font-bold uppercase tracking-wide hover:bg-[hsl(var(--surface-2))] active:scale-95 transition-all shadow-xl">
                        <Save size={14} /> Guardar Cambios
                    </button>
                }
            >
                <div className="space-y-3 p-1">
                    <div className="space-y-2">
                        <label className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] ml-2">Nombre del Rol</label>
                        <input 
                            type="text"
                            value={editingRole.name || ''}
                            onChange={e => setEditingRole({...editingRole, name: e.target.value})}
                            placeholder="Ej. Secretaria CRM"
                            className="w-full px-3 py-1.5 bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] rounded-lg outline-none focus:bg-[hsl(var(--bg-primary))] focus:ring-4 focus:ring-[hsl(var(--primary))]/10 focus:border-blue-500 font-bold text-[hsl(var(--text-primary))] transition-all"
                        />
                    </div>

                    <div className="space-y-3">
                        <div className="flex items-center gap-2 pb-2 border-b border-[hsl(var(--border))]">
                            <Shield size={16} className="text-[hsl(var(--primary))]" />
                            <h4 className="text-sm font-bold text-[hsl(var(--text-primary))]">Matriz de Permisos</h4>
                        </div>

                        {Object.entries(groupedPerms).map(([group, perms]) => {
                            if (perms.length === 0) return null;
                            return (
                                <div key={group} className="space-y-3">
                                    <h5 className="text-[11px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] bg-[hsl(var(--surface-1))] px-3 py-1.5 rounded-lg inline-block">{group}</h5>
                                    <div className="grid grid-cols-1 gap-2">
                                        {perms.map(p => {
                                            const isActive = editingRole.permissions?.includes(p);
                                            return (
                                                <div 
                                                    key={p} 
                                                    onClick={() => togglePermission(p)}
                                                    className={`flex items-start gap-4 p-4 rounded-md cursor-pointer border transition-all ${isActive ? 'bg-blue-50 border-blue-200' : 'bg-[hsl(var(--bg-primary))] border-[hsl(var(--border))] hover:border-[hsl(var(--border))] hover:bg-[hsl(var(--surface-1))]'}`}
                                                >
                                                    <div className={`mt-0.5 shrink-0 w-5 h-5 rounded flex items-center justify-center transition-all ${isActive ? 'bg-[hsl(var(--primary))] text-white shadow-md' : 'bg-[hsl(var(--surface-2))] text-transparent border border-[hsl(var(--border))]'}`}>
                                                        <Check size={12} strokeWidth={4} />
                                                    </div>
                                                    <div>
                                                        <p className={`text-sm font-bold ${isActive ? 'text-blue-900' : 'text-[hsl(var(--text-primary))]'}`}>{p}</p>
                                                        <p className="text-xs text-[hsl(var(--text-secondary))] mt-1">{permissionsMap[p]}</p>
                                                    </div>
                                                </div>
                                            );
                                        })}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            </WorkspaceDrawer>

            <ConfirmActionDrawer action={confirmAction} onClose={() => setConfirmAction(null)} />
        </AdminShell>
    );
}
