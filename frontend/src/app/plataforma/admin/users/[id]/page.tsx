"use client";

import React, { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import { 
    User, 
    Shield, 
    Mail, 
    Clock, 
    LayoutDashboard,
    Lock,
    X,
    Check
} from 'lucide-react';
import { DSCard } from '@/design/components/DSCard';
import { DSBadge } from '@/design/components/DSBadge';
import { toast } from 'sonner';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';

export default function UserDetailPage() {
    const params = useParams();
    const id = params?.id as string;
    const { token, user: currentUser } = useAuth();
    
    const [user, setUser] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    
    // Drawer state
    const [isPasswordModalOpen, setPasswordModalOpen] = useState(false);
    const [newPassword, setNewPassword] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);

    // Edit States
    const [editEmail, setEditEmail] = useState('');
    const [isEditingEmail, setIsEditingEmail] = useState(false);
    
    // Roles
    const [roles, setRoles] = useState<any[]>([]);
    const [editRoleId, setEditRoleId] = useState<string | null>(null);
    const [isEditingRole, setIsEditingRole] = useState(false);

    useEffect(() => {
        if (token && id) {
            const loadUser = async () => {
                try {
                    const [userData, rolesData] = await Promise.all([
                        apiFetch<any>(`/admin/users/${id}`, { token }),
                        apiFetch<any[]>('/admin/roles', { token })
                    ]);
                    setUser(userData);
                    setEditEmail(userData.email);
                    setRoles(rolesData || []);
                    setEditRoleId(userData.rol_plataforma_id || null);
                } catch (err) {
                    toast.error('Error al cargar perfil de usuario');
                } finally {
                    setLoading(false);
                }
            };

            loadUser();
        }
    }, [id, token]);

    const toggleStatus = async () => {
        try {
            setIsSubmitting(true);
            const updated = await apiFetch<any>(`/admin/users/${id}`, {
                method: 'PATCH',
                token,
                body: { is_active: !user.is_active }
            });
            setUser(updated);
            toast.success(`Cuenta ${updated.is_active ? 'activada' : 'suspendida'} correctamente`);
        } catch (err: any) {
            toast.error(err.message || 'Error al cambiar estado');
        } finally {
            setIsSubmitting(false);
        }
    };

    const handlePasswordReset = async (e: React.FormEvent) => {
        e.preventDefault();
        if (newPassword.length < 6) {
            toast.error('La contraseña debe tener al menos 6 caracteres');
            return;
        }
        try {
            setIsSubmitting(true);
            await apiFetch<any>(`/admin/users/${id}`, {
                method: 'PATCH',
                token,
                body: { password: newPassword }
            });
            toast.success('Contraseña actualizada exitosamente');
            setPasswordModalOpen(false);
            setNewPassword('');
        } catch (err: any) {
            toast.error(err.message || 'Error al actualizar contraseña');
        } finally {
            setIsSubmitting(false);
        }
    };

    const saveRole = async () => {
        try {
            setIsSubmitting(true);
            const updated = await apiFetch<any>(`/admin/users/${id}`, {
                method: 'PATCH',
                token,
                body: { rol_plataforma_id: editRoleId }
            });
            setUser(updated);
            toast.success('Rol actualizado');
            setIsEditingRole(false);
        } catch (err: any) {
            toast.error(err.message || 'Error al actualizar rol');
        } finally {
            setIsSubmitting(false);
        }
    };

    const saveEmail = async () => {
        if (!editEmail || editEmail === user.email) {
            setIsEditingEmail(false);
            return;
        }
        try {
            setIsSubmitting(true);
            const updated = await apiFetch<any>(`/admin/users/${id}`, {
                method: 'PATCH',
                token,
                body: { email: editEmail }
            });
            setUser(updated);
            toast.success('Correo actualizado');
            setIsEditingEmail(false);
        } catch (err: any) {
            toast.error(err.message || 'Error al actualizar correo');
        } finally {
            setIsSubmitting(false);
        }
    };

    if (loading) return <div className="p-4 text-center animate-pulse font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Consultando base de datos de usuarios...</div>;
    if (!user) return <div className="p-4 text-center font-semibold uppercase tracking-wide text-rose-500">Usuario no encontrado</div>;

    return (
        <div className="flex flex-col h-full bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--bg-primary))] overflow-hidden">
            <WorkspaceToolbar
                breadcrumbs={[
                    { label: 'Administración', icon: LayoutDashboard, href: '/plataforma/admin' },
                    { label: 'Usuarios', icon: User, href: '/plataforma/admin/users' },
                    { label: user.username, icon: User },
                ]}
                rightActions={
                    <div className="flex items-center gap-3">
                        {String(currentUser?.id) !== id && (
                            <button 
                                onClick={toggleStatus}
                                disabled={isSubmitting}
                                className={`px-3 py-2.5 rounded-md text-[10px] font-semibold uppercase tracking-wide transition-all shadow-sm border ${
                                    user.is_active 
                                    ? 'bg-[hsl(var(--bg-primary))] dark:bg-white/5 border-rose-200 dark:border-rose-500/30 text-rose-600 hover:bg-rose-50' 
                                    : 'bg-emerald-50 dark:bg-emerald-500/10 border-emerald-200 dark:border-emerald-500/30 text-emerald-600 hover:bg-emerald-100'
                                }`}
                            >
                                {user.is_active ? 'Suspender Cuenta' : 'Reactivar Cuenta'}
                            </button>
                        )}
                    </div>
                }
            />

            <main className="flex-1 overflow-y-auto p-3 lg:p-4">
 <div className="w-full grid grid-cols-1 lg:grid-cols-12 gap-3">
                    {/* Left Column - Main Info */}
                    <div className="lg:col-span-8 space-y-3">
                        {/* Profile Header */}
                        <div className="p-4 bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-1))] rounded-lg border border-[hsl(var(--border))] dark:border-white/5 shadow-xl shadow-black/10/20 dark:shadow-none flex flex-col md:flex-row items-center gap-3 relative overflow-hidden">
                            <div className="absolute top-0 right-0 w-64 h-48 bg-gradient-to-bl from-blue-500/10 to-transparent pointer-events-none rounded-bl-full" />
                            
                            <div className="size-10 rounded-full bg-[hsl(var(--surface-1))] dark:bg-black/20 flex items-center justify-center border-4 border-white dark:border-[#15171c] shadow-xl relative z-10">
                                <User size={48} className="text-[hsl(var(--text-secondary))]" strokeWidth={1.5} />
                                {user.is_active && <div className="absolute bottom-2 right-2 size-4 bg-emerald-500 border-2 border-white dark:border-[#15171c] rounded-full" />}
                            </div>
                            
                            <div className="space-y-3 text-center md:text-left relative z-10 flex-1">
                                <h1 className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tight">{user.username}</h1>
                                <div className="flex flex-wrap items-center justify-center md:justify-start gap-3">
                                    <DSBadge tone={user.role === 'admin' ? 'blue' : 'blue'} label={user.role.toUpperCase()} />
                                    <DSBadge tone={user.is_active ? 'emerald' : 'amber'} label={user.is_active ? 'ACTIVO' : 'SUSPENDIDO'} />
                                    <span className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide bg-[hsl(var(--surface-1))] dark:bg-white/5 px-3 py-1 rounded-full">
                                        ID: {user.id}
                                    </span>
                                </div>
                            </div>
                        </div>

                        {/* Account Details */}
                        <DSCard>
                            <h3 className="text-[11px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-3 flex items-center gap-2">
                                <Shield size={14} className="text-[hsl(var(--primary))]"/> Detalles de la Cuenta
                            </h3>
                            <div className="space-y-4">
                                <div className="flex flex-col sm:flex-row sm:items-center justify-between p-3 rounded-lg bg-[hsl(var(--surface-1))] dark:bg-black/20 border border-[hsl(var(--border))] dark:border-white/5 gap-4">
                                    <div className="flex items-center gap-4">
                                        <div className="size-10 rounded-md bg-blue-100 dark:bg-blue-500/20 text-[hsl(var(--primary))] flex items-center justify-center"><Shield size={18} /></div>
                                        <div>
                                            <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1">Rol Asignado (Permisos Granulares)</p>
                                            {isEditingRole ? (
                                                <select 
                                                    value={editRoleId || ''} 
                                                    onChange={e => setEditRoleId(e.target.value || null)}
                                                    className="bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--bg-primary))] border border-blue-500/50 rounded-lg px-3 py-1.5 text-sm font-bold text-[hsl(var(--text-primary))] dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 min-w-[200px]"
                                                >
                                                    <option value="">Sin rol asignado</option>
                                                    {roles.map(r => (
                                                        <option key={r.id} value={r.id}>{r.name}</option>
                                                    ))}
                                                </select>
                                            ) : (
                                                <span className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-white">
                                                    {user.rol_plataforma_id ? roles.find(r => r.id === user.rol_plataforma_id)?.name : (user.role_name || user.role || 'Sin rol')}
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                    {isEditingRole ? (
                                        <div className="flex items-center gap-2">
                                            <button onClick={() => setIsEditingRole(false)} className="p-2 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-secondary))] transition-colors bg-[hsl(var(--bg-primary))] dark:bg-white/5 rounded-lg shadow-sm"><X size={16}/></button>
                                            <button onClick={saveRole} disabled={isSubmitting} className="p-2 text-white bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))] transition-colors rounded-lg shadow-md"><Check size={16}/></button>
                                        </div>
                                    ) : (
                                        <button onClick={() => setIsEditingRole(true)} className="px-4 py-2 bg-[hsl(var(--bg-primary))] dark:bg-white/5 text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] rounded-md text-[10px] font-semibold uppercase tracking-wide hover:bg-blue-50 hover:text-[hsl(var(--primary))] transition-colors shadow-sm">
                                            Cambiar Rol
                                        </button>
                                    )}
                                </div>
                                <div className="flex flex-col sm:flex-row sm:items-center justify-between p-3 rounded-lg bg-[hsl(var(--surface-1))] dark:bg-black/20 border border-[hsl(var(--border))] dark:border-white/5 gap-4">
                                    <div className="flex items-center gap-4">
                                        <div className="size-10 rounded-md bg-blue-100 dark:bg-blue-500/20 text-[hsl(var(--primary))] flex items-center justify-center"><Mail size={18} /></div>
                                        <div>
                                            <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1">Correo Electrónico</p>
                                            {isEditingEmail ? (
                                                <input 
                                                    type="email" 
                                                    value={editEmail} 
                                                    onChange={e => setEditEmail(e.target.value)}
                                                    className="bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--bg-primary))] border border-blue-500/50 rounded-lg px-3 py-1.5 text-sm font-bold text-[hsl(var(--text-primary))] dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                                                    autoFocus
                                                />
                                            ) : (
                                                <span className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-white">{user.email || 'No asignado'}</span>
                                            )}
                                        </div>
                                    </div>
                                    {isEditingEmail ? (
                                        <div className="flex items-center gap-2">
                                            <button onClick={() => setIsEditingEmail(false)} className="p-2 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-secondary))] transition-colors bg-[hsl(var(--bg-primary))] dark:bg-white/5 rounded-lg shadow-sm"><X size={16}/></button>
                                            <button onClick={saveEmail} disabled={isSubmitting} className="p-2 text-white bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))] transition-colors rounded-lg shadow-md"><Check size={16}/></button>
                                        </div>
                                    ) : (
                                        <button onClick={() => setIsEditingEmail(true)} className="px-4 py-2 bg-[hsl(var(--bg-primary))] dark:bg-white/5 text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] rounded-md text-[10px] font-semibold uppercase tracking-wide hover:bg-blue-50 hover:text-[hsl(var(--primary))] transition-colors shadow-sm">
                                            Cambiar Email
                                        </button>
                                    )}
                                </div>
                            </div>
                        </DSCard>
                    </div>

                    {/* Right Column - Actions & Activity */}
                    <div className="lg:col-span-4 space-y-3">
                        <DSCard>
                            <h3 className="text-[11px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-3 flex items-center gap-2">
                                <Lock size={14} className="text-amber-500"/> Seguridad
                            </h3>
                            <button 
                                onClick={() => setPasswordModalOpen(true)}
                                className="w-full py-1.5 bg-[hsl(var(--bg-muted))] dark:bg-[hsl(var(--bg-primary))] text-white dark:text-[hsl(var(--text-primary))] rounded-lg text-[11px] font-semibold uppercase tracking-wide shadow-xl hover:scale-105 active:scale-95 transition-all flex items-center justify-center gap-2"
                            >
                                <Lock size={16} /> Resetear Password
                            </button>
                            <p className="text-[11px] font-medium text-[hsl(var(--text-secondary))] mt-4 leading-relaxed text-center">
                                Al resetear, la contraseña será cambiada de forma inmediata. Asegúrate de comunicársela al usuario por un canal seguro.
                            </p>
                        </DSCard>

                        <div className="p-4 rounded-lg border-2 border-dashed border-[hsl(var(--border))] dark:border-white/10 flex flex-col items-center justify-center text-center gap-4">
                            <Clock size={24} className="text-[hsl(var(--text-secondary))]" />
                            <div>
                                <p className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Actividad Reciente</p>
                                <p className="text-sm font-bold text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] mt-1">
                                    No hay registros recientes para este perfil.
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
            </main>

            {/* DRAWER Password Reset */}
            <WorkspaceDrawer
                isOpen={isPasswordModalOpen}
                onClose={() => !isSubmitting && setPasswordModalOpen(false)}
                title="Nueva Contraseña"
                subtitle={`Para ${user.username}`}
                actions={
                    <>
                        <button type="button" onClick={() => !isSubmitting && setPasswordModalOpen(false)} className="px-4 py-2 text-[11px] font-bold text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] transition-colors">
                            Cancelar
                        </button>
                        <button 
                            type="button" 
                            onClick={handlePasswordReset}
                            disabled={isSubmitting || newPassword.length < 6}
                            className="flex items-center gap-2 px-4 py-2 bg-amber-500 text-white rounded-lg text-[11px] font-semibold uppercase tracking-wide shadow-lg shadow-amber-500/20 hover:bg-amber-600 active:scale-95 transition-all disabled:opacity-50"
                        >
                            <Lock size={16} /> {isSubmitting ? 'Procesando...' : 'Confirmar Cambio'}
                        </button>
                    </>
                }
            >
                <div className="space-y-3 mt-4">
                    <div className="space-y-1.5">
                        <label className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] ml-2 block">Escribe la nueva clave</label>
                        <input 
                            type="text" 
                            value={newPassword}
                            onChange={e => setNewPassword(e.target.value)}
                            placeholder="Min. 6 caracteres..."
                            className="w-full bg-[hsl(var(--surface-1))] dark:bg-black/20 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg px-3 py-1.5 text-sm font-bold text-[hsl(var(--text-primary))] dark:text-white focus:outline-none focus:ring-2 focus:ring-amber-500/50"
                            autoFocus
                        />
                    </div>
                </div>
            </WorkspaceDrawer>
        </div>
    );
}
