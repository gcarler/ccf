"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import CrmShell from '@/components/crm/CrmShell';
import { DSCard } from '@/design/components/DSCard';
import { Settings, Plus, Edit2, Trash2, Save } from 'lucide-react';
import { toast } from 'sonner';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';

type RoleDef = {
    id: number;
    name: string;
    color: string;
    is_leadership: boolean;
};

export default function RolesSettingsPage() {
    const { token } = useAuth();
    const [roles, setRoles] = useState<RoleDef[]>([]);
    const [loading, setLoading] = useState(true);

    const [isEditing, setIsEditing] = useState<RoleDef | null>(null);
    const [isDeleting, setIsDeleting] = useState<RoleDef | null>(null);
    const [fallbackId, setFallbackId] = useState<number | ''>('');

    const loadRoles = useCallback(async () => {
        try {
            setLoading(true);
            const data = await apiFetch<RoleDef[]>('/crm/roles', { token });
            setRoles(data);
        } catch (err) {
            toast.error("Error al cargar los roles");
        } finally {
            setLoading(false);
        }
    }, [token]);

    useEffect(() => {
        if (token) loadRoles();
    }, [token, loadRoles]);

    const handleSave = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!token || !isEditing) return;
        
        try {
            if (isEditing.id === 0) {
                // Create
                await apiFetch('/crm/roles', {
                    method: 'POST',
                    token,
                    body: { name: isEditing.name, color: isEditing.color, is_leadership: isEditing.is_leadership }
                });
                toast.success("Rol creado exitosamente");
            } else {
                // Update
                await apiFetch(`/crm/roles/${isEditing.id}`, {
                    method: 'PUT',
                    token,
                    body: { name: isEditing.name, color: isEditing.color, is_leadership: isEditing.is_leadership }
                });
                toast.success("Rol actualizado exitosamente");
            }
            setIsEditing(null);
            loadRoles();
        } catch (err: any) {
            toast.error(err.message || "Error al guardar el rol");
        }
    };

    const handleDelete = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!token || !isDeleting || fallbackId === '') return;
        
        try {
            await apiFetch(`/crm/roles/${isDeleting.id}?fallback_id=${fallbackId}`, {
                method: 'DELETE',
                token
            });
            toast.success("Rol eliminado y miembros transferidos");
            setIsDeleting(null);
            setFallbackId('');
            loadRoles();
        } catch (err: any) {
            toast.error(err.message || "Error al eliminar el rol");
        }
    };

    return (
        <CrmShell breadcrumbs={[{ label: 'Ajustes', icon: Settings, href: '/settings' }, { label: 'Configuración de Roles' }]}>
            <main className="flex-1 overflow-y-auto p-8 lg:p-12">
                <div className="max-w-4xl mx-auto space-y-10">
                    <header className="flex items-center justify-between">
                        <div>
                            <h1 className="text-3xl font-black text-slate-900 dark:text-white uppercase tracking-tight">Ministerios y Tipos de Asistencia</h1>
                            <p className="text-sm font-medium text-slate-500 mt-2">Configura los roles de la iglesia. Esto afectará los perfiles y el CRM.</p>
                        </div>
                        <button 
                            onClick={() => setIsEditing({ id: 0, name: '', color: 'text-slate-600 bg-slate-100', is_leadership: false })}
                            className="px-6 py-3 bg-blue-600 text-white rounded-2xl text-[10px] font-black uppercase tracking-widest hover:scale-105 transition-all flex items-center gap-2"
                        >
                            <Plus size={16}/> Nuevo Rol
                        </button>
                    </header>

                    <DSCard>
                        {loading ? (
                            <div className="py-20 text-center animate-pulse text-slate-400 font-bold">Cargando roles...</div>
                        ) : (
                            <div className="divide-y divide-slate-100 dark:divide-white/5">
                                {roles.map(role => (
                                    <div key={role.id} className="py-4 flex items-center justify-between group">
                                        <div className="flex items-center gap-4">
                                            <span className={`px-4 py-2 rounded-xl text-xs font-black uppercase tracking-widest ${role.color}`}>
                                                {role.name}
                                            </span>
                                            {role.is_leadership && (
                                                <span className="px-2 py-1 bg-amber-50 dark:bg-amber-900/20 text-amber-600 text-[9px] font-black uppercase tracking-widest rounded-lg">
                                                    Suma a Liderazgo
                                                </span>
                                            )}
                                        </div>
                                        <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-all">
                                            <button onClick={() => setIsEditing(role)} className="p-2 text-slate-400 hover:text-blue-600 bg-slate-50 dark:bg-white/5 rounded-xl">
                                                <Edit2 size={16}/>
                                            </button>
                                            <button onClick={() => setIsDeleting(role)} className="p-2 text-slate-400 hover:text-red-500 bg-slate-50 dark:bg-white/5 rounded-xl">
                                                <Trash2 size={16}/>
                                            </button>
                                        </div>
                                    </div>

                                ))}
                            </div>
                        )}
                    </DSCard>
                </div>
            </main>

            {/* DRAWER Editar/Crear */}
            <WorkspaceDrawer
                isOpen={!!isEditing}
                onClose={() => setIsEditing(null)}
                title={isEditing?.id === 0 ? 'Crear Nuevo Rol' : 'Editar Rol'}
                subtitle="Configura el nombre y color de este rol"
                actions={
                    <>
                        <button type="button" onClick={() => setIsEditing(null)} className="px-4 py-2 text-[11px] font-bold text-slate-500 hover:text-slate-700 transition-colors">
                            Cancelar
                        </button>
                        <button type="button" onClick={handleSave as any} className="flex items-center gap-2 px-8 py-2 bg-blue-600 text-white rounded-lg text-[11px] font-black uppercase tracking-widest shadow-lg shadow-blue-500/30 hover:bg-blue-700 active:scale-95 transition-all">
                            <Save size={16}/> Guardar
                        </button>
                    </>
                }
            >
                {isEditing && (
                    <div className="space-y-6 mt-4">
                        <div className="space-y-1.5">
                            <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 block">Nombre del Rol</label>
                            <input required autoFocus value={isEditing.name} onChange={e => setIsEditing({...isEditing, name: e.target.value})} className="w-full px-4 py-3 bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl text-sm outline-none" />
                        </div>
                        <div className="space-y-1.5">
                            <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 block">Clases de Color (Tailwind)</label>
                            <input required value={isEditing.color} onChange={e => setIsEditing({...isEditing, color: e.target.value})} className="w-full px-4 py-3 bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl text-sm outline-none font-mono" />
                            <div className="mt-3 p-4 bg-slate-50 dark:bg-white/5 rounded-xl flex justify-center border border-slate-200 dark:border-white/10">
                                <span className={`px-4 py-2 rounded-xl text-xs font-black uppercase tracking-widest ${isEditing.color}`}>Previsualización</span>
                            </div>
                        </div>
                        <div className="flex items-center gap-3 mt-4">
                            <input type="checkbox" id="is_leadership" checked={isEditing.is_leadership} onChange={e => setIsEditing({...isEditing, is_leadership: e.target.checked})} className="size-5 rounded border-slate-300 text-blue-600 focus:ring-blue-500" />
                            <label htmlFor="is_leadership" className="text-sm font-bold text-slate-700 dark:text-slate-300 cursor-pointer">
                                Pertenece al Liderazgo <span className="block text-[10px] text-slate-400 font-medium">Sus asistencias se agruparán en &ldquo;Liderazgo&rdquo;</span>
                            </label>
                        </div>
                    </div>
                )}
            </WorkspaceDrawer>

            {/* DRAWER Eliminar */}
            <WorkspaceDrawer
                isOpen={!!isDeleting}
                onClose={() => setIsDeleting(null)}
                title="Eliminar Rol"
                subtitle={`Reemplazo obligatorio para "${isDeleting?.name}"`}
                actions={
                    <>
                        <button type="button" onClick={() => setIsDeleting(null)} className="px-4 py-2 text-[11px] font-bold text-slate-500 hover:text-slate-700 transition-colors">
                            Cancelar
                        </button>
                        <button type="button" onClick={handleDelete as any} className="flex items-center gap-2 px-8 py-2 bg-red-600 text-white rounded-lg text-[11px] font-black uppercase tracking-widest shadow-lg shadow-red-500/30 hover:bg-red-700 active:scale-95 transition-all">
                            <Trash2 size={16}/> Confirmar Eliminación
                        </button>
                    </>
                }
            >
                {isDeleting && (
                    <div className="space-y-6 mt-4">
                        <div className="bg-red-50 dark:bg-red-900/20 border border-red-100 dark:border-red-900/30 text-red-600 p-4 rounded-xl text-sm font-bold">
                            Estás a punto de eliminar el rol &ldquo;{isDeleting.name}&rdquo;.
                            Es obligatorio transferir a las personas que actualmente tienen este rol hacia otro distinto.
                        </div>
                        <div className="space-y-1.5">
                            <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 block">Rol de Reemplazo (Fallback)</label>
                            <select required value={fallbackId} onChange={e => setFallbackId(Number(e.target.value))} className="w-full px-4 py-3 bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl text-sm outline-none font-bold">
                                <option value="" disabled>Seleccione un rol...</option>
                                {roles.filter(r => r.id !== isDeleting.id).map(r => (
                                    <option key={r.id} value={r.id}>{r.name}</option>
                                ))}
                            </select>
                        </div>
                    </div>
                )}
            </WorkspaceDrawer>
        </CrmShell>
    );
}
