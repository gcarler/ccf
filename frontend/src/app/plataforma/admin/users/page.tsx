"use client";

import React, { useState, useEffect } from 'react';
import {
    Users, Shield, UserPlus,
    ShieldCheck, Zap,
    Trash2, CheckCircle2, XCircle,
    Key, Star, Loader2
} from 'lucide-react';
import { motion } from 'framer-motion';
import clsx from 'clsx';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';
import ConfirmActionDrawer, { type ConfirmActionState } from '@/components/ConfirmActionDrawer';
import { useRouter } from 'next/navigation';

export default function AdminUsersPage() {
    const { token } = useAuth();
    const router = useRouter();
    const { addToast } = useToast();
    const [users, setUsers] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [provisioning, setProvisioning] = useState(false);
    const [searchTerm, setSearchTerm] = useState('');
    const [selectedUser, setSelectedUser] = useState<any | null>(null);
    const [isDrawerOpen, setIsDrawerOpen] = useState(false);
    const [confirmAction, setConfirmAction] = useState<ConfirmActionState>(null);

    const fetchUsers = async (signal?: AbortSignal) => {
        setLoading(true);
        try {
            const data = await apiFetch<{ items: any[]; total: number }>('/admin/users', { token, signal });
            setUsers(data?.items ?? []);
        } catch (err: any) {
            if (err?.name === 'AbortError') return;
            addToast("Error al cargar lista de usuarios", "error");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        const controller = new AbortController();
        fetchUsers(controller.signal);
        return () => controller.abort();
    }, [token]);

    const handleBulkProvision = async () => {
        setProvisioning(true);
        try {
            const result = await apiFetch<any>('/admin/provision-accounts', {
                method: 'POST',
                token,
            });
            addToast(result.message, "success");
            fetchUsers();
        } catch (err) {
            addToast("Error al provisionar cuentas", "error");
        } finally {
            setProvisioning(false);
        }
    };

    const handleUpdateUser = async (userId: string, payload: any) => {
        try {
            const updated = await apiFetch(`/admin/users/${userId}`, {
                method: 'PATCH',
                token,
                body: payload
            });
            addToast("Usuario actualizado con éxito", "success");
            if (selectedUser?.id === userId) setSelectedUser(updated);
            fetchUsers();
        } catch (err) {
            addToast("Error al actualizar usuario", "error");
        }
    };

    const handleDeleteUser = async (userId: string) => {
        setConfirmAction({
            title: 'Eliminar acceso ministerial',
            description: 'Se revocará este acceso de forma permanente y el usuario deberá solicitar uno nuevo.',
            destructive: true,
            confirmLabel: 'Revocar acceso',
            onConfirm: async () => {
                try {
                    await apiFetch(`/admin/users/${userId}`, { method: 'DELETE', token });
                    addToast("Acceso revocado permanentemente", "success");
                    fetchUsers();
                } catch (err) {
                    addToast("Error al eliminar acceso", "error");
                }
            },
        });
    };

    const filteredUsers = users.filter(u => 
        u.username.toLowerCase().includes(searchTerm.toLowerCase()) ||
        u.email.toLowerCase().includes(searchTerm.toLowerCase())
    );

    const containerVariants = {
        hidden: { opacity: 0 },
        show: { opacity: 1, transition: { staggerChildren: 0.05 } }
    };

    const itemVariants = {
        hidden: { opacity: 0, y: 10 },
        show: { opacity: 1, y: 0, transition: { type: 'spring', stiffness: 300, damping: 24 } }
    };

    return (
        <div className="flex flex-col h-full bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--bg-primary))] overflow-hidden font-sans relative">
            <WorkspaceToolbar 
                breadcrumbs={[{ label: 'Administración', icon: Shield }, { label: 'Gestión de Accesos', icon: Users }]}
                onSearch={setSearchTerm}
                rightActions={
                    <div className="flex items-center gap-2">
                        <button
                            onClick={handleBulkProvision}
                            disabled={provisioning}
                            className="flex items-center gap-2 px-3 py-2.5 bg-emerald-600 text-white rounded-md text-[11px] font-semibold uppercase tracking-wide shadow-xl shadow-emerald-500/20 hover:bg-emerald-500 active:scale-95 transition-all disabled:opacity-50"
                        >
                            {provisioning ? <Loader2 size={14} className="animate-spin" /> : <Zap size={14} />}
                            {provisioning ? 'Provisionando...' : 'Provisionar Todos'}
                        </button>
                        <button className="flex items-center gap-2 px-3 py-2.5 bg-[hsl(var(--primary))] text-white rounded-md text-[11px] font-semibold uppercase tracking-wide shadow-xl shadow-blue-500/20 active:scale-95 transition-all">
                            <UserPlus size={14} /> Nuevo Acceso
                        </button>
                    </div>
                }
            />

            <main className="flex-1 overflow-y-auto scrollbar-thin p-3 lg:p-4 relative z-10">
                <motion.div 
                    variants={containerVariants} initial="hidden" animate="show"
 className="w-full space-y-3"
                >
                    {/* Header */}
                    <motion.div variants={itemVariants} className="space-y-2">
                        <h1 className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tighter">Usuarios <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-sky-600">Ministeriales.</span></h1>
                        <p className="text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] font-medium">Control total sobre roles, permisos y estados de cuenta del staff y la congregación.</p>
                    </motion.div>

                    {/* Users Table */}
                    <motion.div variants={itemVariants} className="bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-1))] rounded-lg border border-[hsl(var(--border))] dark:border-white/5 shadow-xl shadow-black/10/20 dark:shadow-none overflow-hidden relative">
                        <div className="overflow-x-auto">
                            <table className="w-full text-left border-collapse">
                                <thead>
                                    <tr className="bg-[hsl(var(--surface-1))]/50 dark:bg-black/20 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                                        <th className="px-4 py-2">Identidad</th>
                                        <th className="px-4 py-2">Rol Ministerial</th>
                                        <th className="px-4 py-2">Reputación (XP)</th>
                                        <th className="px-4 py-2">Estado</th>
                                        <th className="px-4 py-2 text-right">Acciones</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-[hsl(var(--border))] dark:divide-white/5">
                                    {loading ? (
                                        [...Array(6)].map((_, i) => (
                                            <tr key={i}><td colSpan={5} className="px-4 py-2"><div className="h-8 w-full bg-[hsl(var(--surface-2))] dark:bg-white/5 rounded-lg animate-pulse" /></td></tr>
                                        ))
                                    ) : filteredUsers.map((user) => (
                                        <tr 
                                            key={user.id} 
                                            className="group hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 transition-all cursor-pointer" 
                                            onClick={() => { setSelectedUser(user); setIsDrawerOpen(true); }}
                                        >
                                            <td className="px-4 py-2">
                                                <div className="flex items-center gap-4">
                                                    <div className="size-10 rounded-lg bg-gradient-to-tr from-blue-600 to-sky-600 flex items-center justify-center text-white font-semibold shadow-lg">
                                                        {user.username.substring(0, 2).toUpperCase()}
                                                    </div>
                                                    <div>
                                                        <p className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-white group-hover:text-[hsl(var(--primary))] transition-colors">{user.username}</p>
                                                        <p className="text-[11px] font-medium text-[hsl(var(--text-secondary))]">{user.email}</p>
                                                    </div>
                                                </div>
                                            </td>
                                            <td className="px-4 py-2">
                                                <span className={clsx(
                                                    "inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-[9px] font-semibold uppercase tracking-wide",
                                                    user.role === 'admin' ? "bg-sky-50 text-sky-600 dark:bg-sky-500/10 dark:text-sky-400" :
                                                    user.role === 'pastor' ? "bg-blue-50 text-[hsl(var(--primary))] dark:bg-blue-500/10 dark:text-[hsl(var(--primary))]" :
                                                    "bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))] dark:bg-white/5 dark:text-[hsl(var(--text-secondary))]"
                                                )}>
                                                    <Shield size={10} /> {user.role}
                                                </span>
                                            </td>
                                            <td className="px-4 py-2">
                                                <div className="flex items-center gap-2">
                                                    <Star size={14} className="text-amber-400 fill-amber-400" />
                                                    <span className="text-sm font-semibold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">{user.xp || 0} XP</span>
                                                </div>
                                            </td>
                                            <td className="px-4 py-2">
                                                <div className="flex items-center gap-2">
                                                    <div className={clsx("size-2 rounded-full", user.is_active ? "bg-emerald-500 animate-pulse" : "bg-[hsl(var(--surface-2))]")} />
                                                    <span className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{user.is_active ? 'Activo' : 'Suspendido'}</span>
                                                </div>
                                            </td>
                                            <td className="px-4 py-2 text-right">
                                                <div className="flex items-center justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                                    <button onClick={(e) => { e.stopPropagation(); handleUpdateUser(user.id, { is_active: !user.is_active }); }} className="p-2 hover:bg-[hsl(var(--bg-primary))] dark:hover:bg-white/10 rounded-md transition-all text-[hsl(var(--text-secondary))]">
                                                        {user.is_active ? <XCircle size={18} /> : <CheckCircle2 size={18} />}
                                                    </button>
                                                    <button onClick={(e) => { e.stopPropagation(); handleDeleteUser(user.id); }} className="p-2 hover:bg-rose-50 dark:hover:bg-rose-500/10 rounded-md transition-all text-[hsl(var(--text-secondary))] hover:text-rose-500">
                                                        <Trash2 size={18} />
                                                    </button>
                                                </div>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </motion.div>
                </motion.div>
            </main>

            {/* User Control Drawer */}
            <WorkspaceDrawer 
                isOpen={isDrawerOpen} onClose={() => setIsDrawerOpen(false)}
                title={selectedUser?.username || 'Control de Acceso'}
                subtitle="Ajustes de Seguridad y Rol"
                actions={
                    <div className="flex items-center gap-2">
                        {selectedUser && (
                            <button
                                className="px-3 py-2.5 text-[11px] font-bold text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] transition-colors"
                                onClick={() => {
                                    router.push(`/plataforma/admin/users/${selectedUser.id}`);
                                    setIsDrawerOpen(false);
                                }}
                            >
                                Ver detalle
                            </button>
                        )}
                        <button className="px-3 py-2.5 text-[11px] font-bold text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] transition-colors" onClick={() => setIsDrawerOpen(false)}>Cancelar</button>
                    </div>
                }
            >
                {selectedUser && (
                    <div className="space-y-3 p-2 animate-fade-in">
                        <section className="space-y-4">
                            <h4 className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide flex items-center gap-2"><Shield size={14} className="text-[hsl(var(--primary))]" /> Cambio de Rango Ministerial</h4>
                            <div className="grid grid-cols-1 gap-2">
                                {['admin', 'pastor', 'docente', 'lider', 'estudiante'].map((role) => (
                                    <button 
                                        key={role}
                                        onClick={() => handleUpdateUser(selectedUser.id, { role })}
                                        className={clsx(
                                            "flex items-center justify-between p-3 rounded-lg border-2 transition-all group",
                                            selectedUser.role === role 
                                                ? "bg-[hsl(var(--primary))] border-blue-600 text-white shadow-xl shadow-blue-500/20" 
                                                : "bg-[hsl(var(--surface-1))] dark:bg-white/5 border-[hsl(var(--border))] dark:border-white/5 text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] hover:border-blue-500/30"
                                        )}
                                    >
                                        <span className="text-[12px] font-semibold uppercase tracking-wide">{role}</span>
                                        {selectedUser.role === role && <ShieldCheck size={18} />}
                                    </button>
                                ))}
                            </div>
                        </section>

                        <section className="space-y-4">
                            <h4 className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide flex items-center gap-2"><Key size={14} className="text-[hsl(var(--primary))]" /> Seguridad de Cuenta</h4>
                            <button className="w-full p-3 bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/5 rounded-lg text-[11px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] transition-all flex items-center justify-center gap-3">
                                <Zap size={16} className="text-amber-500" /> Resetear Contraseña (Forzar)
                            </button>
                        </section>
                    </div>
                )}
            </WorkspaceDrawer>

            <ConfirmActionDrawer action={confirmAction} onClose={() => setConfirmAction(null)} />
        </div>
    );
}
