"use client";

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import { 
    User, 
    Shield, 
    Mail, 
    Calendar, 
    Clock, 
    Settings, 
    ArrowLeft,
    CheckCircle2,
    XCircle,
    UserPlus,
    LayoutDashboard,
    Lock
} from 'lucide-react';
import { DSCard } from '@/design/components/DSCard';
import { DSBadge } from '@/design/components/DSBadge';
import { toast } from 'sonner';

const MOCK_ADMIN = {
    id: 1,
    username: 'admin_ccf',
    email: 'admin@ccf.org',
    role: 'admin',
    last_login: '2026-04-12 10:30',
    is_active: true
};

export default function UserDetailPage() {
    const params = useParams();
    const id = params?.id as string;
    const router = useRouter();
    const { token } = useAuth();
    
    const [user, setUser] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!token || !id) return;
        const loadUser = async () => {
            try {
                setLoading(true);
                const data = await apiFetch<any>(`/auth/users/${id}`, { token }).catch(() => MOCK_ADMIN);
                setUser(data);
            } catch (err) {
                toast.error('Error al cargar perfil de usuario');
            } finally {
                setLoading(false);
            }
        };
        loadUser();
    }, [id, token]);

    if (loading) return <div className="p-20 text-center animate-pulse font-black uppercase tracking-widest text-slate-400">Consultando base de datos de usuarios...</div>;

    return (
        <div className="flex flex-col h-full bg-[#f8fafc] dark:bg-[#0b0d11] overflow-hidden">
            <WorkspaceToolbar
                breadcrumbs={[
                    { label: 'Administración', icon: LayoutDashboard, href: '/admin' },
                    { label: 'Usuarios', icon: User, href: '/admin/users' },
                    { label: user.username, icon: User },
                ]}
                rightActions={
                    <div className="flex items-center gap-3">
                        <button className="px-4 py-2 text-slate-500 text-[10px] font-black uppercase tracking-widest hover:text-slate-700 transition-all">
                            Suspender Cuenta
                        </button>
                        <button className="px-6 py-2 bg-blue-600 text-white rounded-xl text-[10px] font-black uppercase tracking-widest shadow-lg shadow-blue-500/20 hover:scale-105 transition-all">
                            Guardar Cambios
                        </button>
                    </div>
                }
            />

            <main className="flex-1 overflow-y-auto p-8 lg:p-12">
                <div className="max-w-4xl mx-auto grid grid-cols-1 lg:grid-cols-3 gap-8">
                    <div className="lg:col-span-2 space-y-8">
                        <header className="flex items-center gap-6">
                            <div className="size-24 rounded-[2rem] bg-slate-100 dark:bg-white/5 flex items-center justify-center border-4 border-white dark:border-slate-900 shadow-xl">
                                <User size={48} className="text-slate-400" />
                            </div>
                            <div className="space-y-1">
                                <h1 className="text-3xl font-black text-slate-900 dark:text-white tracking-tight uppercase">{user.username}</h1>
                                <div className="flex items-center gap-2">
                                    <DSBadge tone={user.role === 'admin' ? 'violet' : 'blue'} label={user.role.toUpperCase()} />
                                    <DSBadge tone={user.is_active ? 'emerald' : 'slate'} label={user.is_active ? 'ACTIVO' : 'INACTIVO'} />
                                </div>
                            </div>
                        </header>

                        <DSCard>
                            <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-6">Detalles de la Cuenta</h3>
                            <div className="space-y-4">
                                <div className="flex items-center justify-between p-4 rounded-2xl bg-slate-50 dark:bg-white/5">
                                    <div className="flex items-center gap-3">
                                        <Mail size={18} className="text-slate-400" />
                                        <span className="text-sm font-bold">{user.email}</span>
                                    </div>
                                    <button className="text-[9px] font-black text-blue-600 uppercase tracking-widest">Cambiar</button>
                                </div>
                                <div className="flex items-center justify-between p-4 rounded-2xl bg-slate-50 dark:bg-white/5">
                                    <div className="flex items-center gap-3">
                                        <Shield size={18} className="text-slate-400" />
                                        <span className="text-sm font-bold">Permisos de {user.role}</span>
                                    </div>
                                    <button className="text-[9px] font-black text-blue-600 uppercase tracking-widest">Gestionar</button>
                                </div>
                            </div>
                        </DSCard>
                    </div>

                    <aside className="space-y-6">
                        <DSCard>
                            <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-6">Actividad</h3>
                            <div className="space-y-4 text-[11px] font-medium text-slate-500">
                                <p className="flex items-center gap-1.5"><Clock size={16} /> Último ingreso: {user.last_login}</p>
                                <p className="flex items-center gap-1.5"><Calendar size={16} /> Miembro desde: 2024-01-15</p>
                                <div className="h-px bg-slate-100 dark:bg-white/5" />
                                <button className="w-full py-3 border border-slate-200 dark:border-white/10 rounded-xl text-[10px] font-black uppercase tracking-widest hover:bg-slate-50 transition-all flex items-center justify-center gap-2">
                                    <Lock size={14} /> Resetear Password
                                </button>
                            </div>
                        </DSCard>
                    </aside>
                </div>
            </main>
        </div>
    );
}
