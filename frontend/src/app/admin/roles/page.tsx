'use client';

import React, { useState, useEffect } from 'react';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import AdminShell from '@/components/admin/AdminShell';
import AdminHero from '@/components/admin/AdminHero';
import { Shield, Plus, Check, Save, Trash2 } from 'lucide-react';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';

interface Role {
    role_id: number;
    name: string;
    permissions: string[];
}

export default function RolesPage() {
    const { token } = useAuth();
    const { addToast } = useToast();
    const [roles, setRoles] = useState<Role[]>([]);
    const [permissionsMap, setPermissionsMap] = useState<Record<string, string>>({});
    const [loading, setLoading] = useState(true);

    const [isDrawerOpen, setIsDrawerOpen] = useState(false);
    const [editingRole, setEditingRole] = useState<Partial<Role>>({
        name: '',
        permissions: []
    });

    const fetchData = async () => {
        setLoading(true);
        try {
            const [rolesRes, permsRes] = await Promise.all([
                apiFetch<Role[]>('/admin/roles', { token }),
                apiFetch<Record<string, string>>('/admin/permissions', { token })
            ]);
            setRoles(rolesRes || []);
            setPermissionsMap(permsRes || {});
        } catch {
            addToast("Error al cargar roles", "error");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [token]);

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
            setEditingRole({ ...editingRole, permissions: current.filter(p => p !== permKey) });
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
            if (editingRole.role_id) {
                await apiFetch(`/admin/roles/${editingRole.role_id}`, {
                    method: 'PATCH',
                    token,
                    body: { permissions: editingRole.permissions }
                });
                addToast("Rol actualizado", "success");
            } else {
                await apiFetch('/admin/roles', {
                    method: 'POST',
                    token,
                    body: editingRole
                });
                addToast("Rol creado", "success");
            }
            setIsDrawerOpen(false);
            fetchData();
        } catch (e: any) {
            addToast(e.message || "Error al guardar", "error");
        }
    };

    const handleDelete = async (e: React.MouseEvent, id: number) => {
        e.stopPropagation();
        if (!window.confirm("¿Seguro que deseas eliminar este rol?")) return;
        try {
            await apiFetch(`/admin/roles/${id}`, {
                method: 'DELETE',
                token
            });
            addToast("Rol eliminado", "success");
            fetchData();
        } catch (e: any) {
            addToast(e.message || "Error al eliminar", "error");
        }
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
        <AdminShell breadcrumbs={[{ label: 'Administración', href: '/admin' }, { label: 'Roles', href: '/admin/roles' }]}>
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
                        <div className="animate-spin rounded-full h-8 w-12 border-b-2 border-slate-900"></div>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                        {roles.map(role => (
                            <div 
                                key={role.role_id}
                                onClick={() => openEditDrawer(role)}
                                className="bg-white rounded-lg p-3 border border-slate-100 shadow-xl shadow-slate-200/20 hover:shadow-2xl hover:-translate-y-1 transition-all cursor-pointer group"
                            >
                                <div className="flex items-center justify-between mb-4">
                                    <div className="flex items-center gap-3">
                                        <div className="w-10 h-10 rounded-md bg-blue-50 text-blue-600 flex items-center justify-center">
                                            <Shield size={20} />
                                        </div>
                                        <h3 className="font-bold text-slate-800">{role.name}</h3>
                                    </div>
                                    <button onClick={(e) => handleDelete(e, role.role_id)} className="opacity-0 group-hover:opacity-100 p-2 text-slate-300 hover:text-rose-500 hover:bg-rose-50 rounded-lg transition-all">
                                        <Trash2 size={16} />
                                    </button>
                                </div>
                                <div className="space-y-3">
                                    <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                                        {role.permissions.length} Permisos Activos
                                    </p>
                                    <div className="flex flex-wrap gap-1.5">
                                        {role.permissions.slice(0, 5).map(p => (
                                            <span key={p} className="px-2 py-1 bg-slate-50 text-slate-500 rounded-md text-[10px] font-bold border border-slate-100">
                                                {p}
                                            </span>
                                        ))}
                                        {role.permissions.length > 5 && (
                                            <span className="px-2 py-1 bg-slate-100 text-slate-600 rounded-md text-[10px] font-bold">
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
                title={editingRole.role_id ? "Editar Rol" : "Nuevo Rol"}
                subtitle="Configura los alcances de este perfil"
                actions={
                    <button onClick={handleSaveRole} className="flex items-center gap-2 px-3 py-2 bg-slate-900 text-white rounded-lg text-xs font-bold uppercase tracking-wide hover:bg-slate-800 active:scale-95 transition-all shadow-xl">
                        <Save size={14} /> Guardar Cambios
                    </button>
                }
            >
                <div className="space-y-3 p-1">
                    <div className="space-y-2">
                        <label className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 ml-2">Nombre del Rol</label>
                        <input 
                            type="text"
                            value={editingRole.name || ''}
                            onChange={e => setEditingRole({...editingRole, name: e.target.value})}
                            placeholder="Ej. Secretaria CRM"
                            className="w-full px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg outline-none focus:bg-white focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 font-bold text-slate-800 transition-all"
                        />
                    </div>

                    <div className="space-y-3">
                        <div className="flex items-center gap-2 pb-2 border-b border-slate-100">
                            <Shield size={16} className="text-blue-500" />
                            <h4 className="text-sm font-bold text-slate-800">Matriz de Permisos</h4>
                        </div>

                        {Object.entries(groupedPerms).map(([group, perms]) => {
                            if (perms.length === 0) return null;
                            return (
                                <div key={group} className="space-y-3">
                                    <h5 className="text-[11px] font-semibold uppercase tracking-wide text-slate-400 bg-slate-50 px-3 py-1.5 rounded-lg inline-block">{group}</h5>
                                    <div className="grid grid-cols-1 gap-2">
                                        {perms.map(p => {
                                            const isActive = editingRole.permissions?.includes(p);
                                            return (
                                                <div 
                                                    key={p} 
                                                    onClick={() => togglePermission(p)}
                                                    className={`flex items-start gap-4 p-4 rounded-md cursor-pointer border transition-all ${isActive ? 'bg-blue-50 border-blue-200' : 'bg-white border-slate-100 hover:border-slate-200 hover:bg-slate-50'}`}
                                                >
                                                    <div className={`mt-0.5 shrink-0 w-5 h-5 rounded flex items-center justify-center transition-all ${isActive ? 'bg-blue-600 text-white shadow-md' : 'bg-slate-100 text-transparent border border-slate-200'}`}>
                                                        <Check size={12} strokeWidth={4} />
                                                    </div>
                                                    <div>
                                                        <p className={`text-sm font-bold ${isActive ? 'text-blue-900' : 'text-slate-700'}`}>{p}</p>
                                                        <p className="text-xs text-slate-500 mt-1">{permissionsMap[p]}</p>
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
        </AdminShell>
    );
}
