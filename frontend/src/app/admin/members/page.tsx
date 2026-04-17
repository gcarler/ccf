"use client";

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { 
    Search, 
    UserPlus, 
    MoreHorizontal, 
    Edit3, 
    Loader2, 
    Users, 
    Shield, 
    Lock, 
    Mail, 
    ChevronRight,
    Filter,
    Layout,
    Settings,
    CheckCircle2,
    XCircle,
    Fingerprint,
    Smartphone,
    Clock
} from 'lucide-react';
import Image from 'next/image';
import { apiFetch } from '@/lib/http';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';
import { DataTable } from '@/components/ui/DataTable';
import { ColumnDef } from '@tanstack/react-table';
import Skeleton from '@/components/ui/Skeleton';
import StatusPicker, { StatusOption } from '@/components/ui/StatusPicker';
import InlineEdit from '@/components/ui/InlineEdit';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';

const ROLE_OPTIONS: StatusOption[] = [
    { label: 'ADMIN', value: 'admin', color: 'bg-rose-500', text: 'text-rose-600 dark:text-rose-400', bg: 'bg-rose-50 dark:bg-rose-900/20' },
    { label: 'STAFF', value: 'staff', color: 'bg-blue-500', text: 'text-blue-600 dark:text-blue-400', bg: 'bg-blue-50 dark:bg-blue-900/20' },
    { label: 'PASTOR', value: 'pastor', color: 'bg-purple-500', text: 'text-purple-600 dark:text-purple-400', bg: 'bg-purple-50 dark:bg-purple-900/20' },
    { label: 'MIEMBRO', value: 'estudiante', color: 'bg-slate-400', text: 'text-slate-500 dark:text-slate-400', bg: 'bg-slate-100 dark:bg-white/5' },
];

export default function AdminMembersPage() {
    const { token } = useAuth();
    const { addToast } = useToast();
    const [members, setMembers] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [selectedMember, setSelectedMember] = useState<any>(null);
    const [isDrawerOpen, setIsDrawerOpen] = useState(false);
    const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

    const fetchUsers = useCallback(async () => {
        if (!token) return;
        setLoading(true);
        try {
            const res = await apiFetch<any[]>('/auth/user-list', { token, cache: 'no-store' });
            setMembers(Array.isArray(res) ? res : []);
        } catch (e) { console.error(e); }
        finally { setLoading(false); }
    }, [token]);

    useEffect(() => { fetchUsers(); }, [fetchUsers]);

    const updateRole = useCallback(async (id: number, newRole: string) => {
        setMembers(prev => prev.map(m => m.id === id ? { ...m, role: newRole } : m));
        try {
            await apiFetch(`/auth/users/${id}/role`, { method: 'PATCH', token, body: { role: newRole } });
            addToast('Rol actualizado correctamente', 'success');
        } catch (e) { addToast('Error al actualizar rol', 'error'); }
    }, [token, addToast]);

    const columns = useMemo<ColumnDef<any>[]>(() => [
        {
            accessorKey: 'username',
            header: 'Usuario / Cuenta',
            size: 300,
            cell: ({ row }) => (
                <div className="flex items-center gap-3">
                    <div className="size-8 rounded-xl bg-slate-100 dark:bg-white/5 flex items-center justify-center overflow-hidden border border-slate-200 dark:border-white/10 shrink-0">
                        <Image src={`https://ui-avatars.com/api/?name=${row.original.username}&background=random&color=fff`} alt="AV" width={32} height={32} unoptimized />
                    </div>
                    <div className="truncate flex-1">
                        <p className="text-[13px] font-black text-slate-800 dark:text-white leading-tight truncate">{row.original.username}</p>
                        <p className="text-[10px] text-slate-400 font-medium truncate">{row.original.email}</p>
                    </div>
                </div>
            )
        },
        {
            accessorKey: 'role',
            header: 'Rol de Sistema',
            cell: ({ row }) => (
                <div onClick={(e) => e.stopPropagation()}>
                    <StatusPicker currentValue={row.original.role} options={ROLE_OPTIONS} onSelect={(val) => updateRole(row.original.id, val)} />
                </div>
            )
        },
        {
            accessorKey: 'is_active',
            header: 'Estado',
            cell: info => (
                <div className="flex items-center gap-1.5">
                    {info.getValue() ? (
                        <span className="flex items-center gap-1 text-[10px] font-black text-emerald-500 uppercase"><CheckCircle2 size={12} /> Activo</span>
                    ) : (
                        <span className="flex items-center gap-1 text-[10px] font-black text-rose-500 uppercase"><XCircle size={12} /> Bloqueado</span>
                    )}
                </div>
            )
        },
        {
            id: 'actions',
            header: '',
            size: 50,
            cell: () => <button className="p-1.5 hover:bg-slate-100 dark:hover:bg-white/5 rounded-lg text-slate-400"><MoreHorizontal size={16} /></button>
        }
    ], [updateRole]);

    const filtered = members.filter(m => 
        m.username.toLowerCase().includes(search.toLowerCase()) || 
        m.email.toLowerCase().includes(search.toLowerCase())
    );

    const handleOpenMember = (member: any) => {
        setSelectedMember(member);
        setIsDrawerOpen(true);
    };

    return (
        <div className="flex flex-col h-full bg-white dark:bg-[#1e1f21] overflow-hidden animate-fade-in">
            <WorkspaceToolbar 
                breadcrumbs={[{ label: 'Gestión Central', icon: Shield }, { label: 'Usuarios y Roles', icon: Users }]}
                viewType="table" setViewType={() => {}} onSearch={setSearch}
                rightActions={
                    <button onClick={() => setIsCreateModalOpen(true)} className="flex items-center gap-2 px-4 py-1.5 bg-blue-600 text-white rounded-lg text-[11px] font-black uppercase tracking-widest shadow-xl shadow-blue-500/20 active:scale-95 transition-all">
                        <UserPlus size={14} /> Añadir Usuario
                    </button>
                }
            />

            <main className="flex-1 overflow-auto scrollbar-thin">
                {loading ? (
                    <div className="p-8 space-y-4">
                        {[1,2,3,4,5,6].map(i => <Skeleton key={i} className="h-14 w-full rounded-2xl" />)}
                    </div>
                ) : (
                    <DataTable data={filtered} columns={columns} onRowClick={handleOpenMember} />
                )}
            </main>

            <WorkspaceDrawer 
                isOpen={isDrawerOpen} onClose={() => setIsDrawerOpen(false)}
                title={selectedMember?.username || 'Detalles de Usuario'}
                subtitle="Configuración Técnica de Cuenta"
                actions={<><button className="px-4 py-2 text-[11px] font-bold text-rose-500">Bloquear Cuenta</button><button className="px-6 py-2 bg-slate-900 dark:bg-white text-white dark:text-slate-900 rounded-lg text-[11px] font-bold shadow-lg">Guardar Cambios</button></>}
            >
                <div className="space-y-10 animate-fade-in">
                    <section className="flex items-center gap-6">
                        <div className="size-20 rounded-[2rem] bg-slate-100 dark:bg-white/5 border-2 border-slate-200 dark:border-white/10 flex items-center justify-center overflow-hidden shadow-xl">
                            <Image src={`https://ui-avatars.com/api/?name=${selectedMember?.username}&background=random&color=fff`} alt="AV" width={80} height={80} unoptimized />
                        </div>
                        <div className="space-y-1">
                            <h3 className="text-2xl font-black text-slate-800 dark:text-white tracking-tight">{selectedMember?.username}</h3>
                            <p className="text-sm text-slate-500 font-medium">{selectedMember?.email}</p>
                        </div>
                    </section>

                    <section className="grid grid-cols-2 gap-4">
                        <AdminStat label="Rol Actual" value={selectedMember?.role} icon={Shield} />
                        <AdminStat label="Verificación" value={selectedMember?.is_email_verified ? 'Completada' : 'Pendiente'} icon={Mail} />
                        <AdminStat label="Último Acceso" value="Hace 2 horas" icon={Clock} />
                        <AdminStat label="Dispositivo" value="Desktop (Win32)" icon={Smartphone} />
                    </section>

                    <section className="p-6 bg-blue-50 dark:bg-blue-900/10 rounded-[2.5rem] border border-blue-100 dark:border-blue-900/30 flex items-center justify-between">
                        <div className="flex items-center gap-4">
                            <div className="size-12 rounded-2xl bg-white dark:bg-white/10 flex items-center justify-center text-blue-600 shadow-sm"><Fingerprint size={24} /></div>
                            <div>
                                <h4 className="text-[11px] font-black uppercase tracking-widest text-blue-600">Seguridad Biométrica / 2FA</h4>
                                <p className="text-xs text-slate-500">Forzar autenticación de dos factores.</p>
                            </div>
                        </div>
                        <div className="h-6 w-11 bg-slate-200 dark:bg-white/10 rounded-full relative cursor-pointer"><div className="absolute left-1 top-1 size-4 bg-white rounded-full" /></div>
                    </section>
                </div>
            </WorkspaceDrawer>
        </div>
    );
}

function AdminStat({ label, value, icon: Icon }: any) {
    return (
        <div className="p-4 bg-slate-50 dark:bg-white/5 border border-slate-100 dark:border-white/5 rounded-2xl group hover:border-blue-500/20 transition-all">
            <div className="flex items-center gap-2 mb-2">
                <Icon size={14} className="text-slate-400 group-hover:text-blue-500" />
                <span className="text-[9px] font-black text-slate-400 uppercase tracking-widest">{label}</span>
            </div>
            <p className="text-[13px] font-black text-slate-800 dark:text-white capitalize">{value}</p>
        </div>
    );
}

