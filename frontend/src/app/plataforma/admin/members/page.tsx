"use client";

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { 
    UserPlus, 
    MoreHorizontal, 
    Users, 
    Shield, 
    Mail, 
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
import UniversalCalendarView from '@/components/ui/UniversalCalendarView';
import UniversalGanttView from '@/components/ui/UniversalGanttView';
import UniversalWikiView from '@/components/ui/UniversalWikiView';
import { ColumnDef } from '@tanstack/react-table';
import Skeleton from '@/components/ui/Skeleton';
import StatusPicker, { StatusOption } from '@/components/ui/StatusPicker';
import type { ViewType } from '@/components/ViewSwitcher';

const MEMBER_VIEWS: ViewType[] = ['table', 'list', 'grid', 'board', 'kanban', 'calendar', 'gantt', 'wiki'];

const ROLE_OPTIONS: StatusOption[] = [
    { label: 'ADMIN', value: 'admin', color: 'bg-rose-500', text: 'text-rose-600 dark:text-rose-400', bg: 'bg-rose-50 dark:bg-rose-900/20' },
    { label: 'STAFF', value: 'staff', color: 'bg-[hsl(var(--primary))]', text: 'text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))]', bg: 'bg-blue-50 dark:bg-blue-900/20' },
    { label: 'PASTOR', value: 'pastor', color: 'bg-sky-500', text: 'text-sky-600 dark:text-sky-400', bg: 'bg-sky-50 dark:bg-sky-900/20' },
    { label: 'MIEMBRO', value: 'estudiante', color: 'bg-slate-400', text: 'text-slate-500 dark:text-slate-400', bg: 'bg-slate-100 dark:bg-white/5' },
];

export default function AdminMembersPage() {
    const { token } = useAuth();
    const { addToast } = useToast();
    const [members, setMembers] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [viewType, setViewType] = useState<ViewType>('table');
    const [selectedMember, setSelectedMember] = useState<any>(null);
    const [isDrawerOpen, setIsDrawerOpen] = useState(false);
    const [isCreateOpen, setIsCreateOpen] = useState(false);
    const [newMember, setNewMember] = useState({ username: '', email: '', role: 'estudiante', password: '' });

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
            await apiFetch(`/admin/users/${id}/role`, { method: 'PATCH', token, body: { role: newRole } });
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
                    <div className="size-8 rounded-md bg-slate-100 dark:bg-white/5 flex items-center justify-center overflow-hidden border border-slate-200 dark:border-white/10 shrink-0">
                        <Image src={`https://ui-avatars.com/api/?name=${row.original.username}&background=random&color=fff`} alt="AV" width={32} height={32} unoptimized />
                    </div>
                    <div className="truncate flex-1">
                        <p className="font-semibold text-slate-800 dark:text-white leading-tight truncate">{row.original.username}</p>
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
                        <span className="flex items-center gap-1 font-semibold text-emerald-500 uppercase"><CheckCircle2 size={12} /> Activo</span>
                    ) : (
                        <span className="flex items-center gap-1 font-semibold text-rose-500 uppercase"><XCircle size={12} /> Bloqueado</span>
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
    const groupedMembers = useMemo(() => {
        const roles = ['admin', 'pastor', 'staff', 'estudiante'];
        return roles.map((role) => ({
            role,
            items: filtered.filter((member) => (member.role || 'estudiante') === role),
        })).filter((column) => column.items.length > 0 || ['admin', 'staff', 'estudiante'].includes(column.role));
    }, [filtered]);
    const calendarEvents = useMemo(() => filtered.map((member) => ({
        id: member.id,
        title: member.username,
        date: (member.created_at || new Date().toISOString()).slice(0, 10),
        color: member.is_active ? 'emerald' as const : 'rose' as const,
        location: member.role,
    })), [filtered]);
    const ganttItems = useMemo(() => filtered.map((member) => ({
        id: member.id,
        title: member.username,
        subtitle: member.role,
        start_date: (member.created_at || new Date().toISOString()).slice(0, 10),
        end_date: (member.updated_at || member.created_at || new Date().toISOString()).slice(0, 10),
        color: member.is_active ? 'emerald' as const : 'rose' as const,
        progress: member.is_active ? 100 : 30,
    })), [filtered]);

    const handleOpenMember = (member: any) => {
        setSelectedMember(member);
        setIsDrawerOpen(true);
    };

    const handleCreateMember = async () => {
        if (!newMember.username.trim() || !newMember.email.trim() || !newMember.password.trim()) return;
        try {
            const created = await apiFetch<any>('/admin/users', {
                method: 'POST',
                token,
                body: newMember,
            });
            setMembers((prev) => [created, ...prev]);
            setIsCreateOpen(false);
            setNewMember({ username: '', email: '', role: 'estudiante', password: '' });
            addToast('Usuario creado correctamente', 'success');
        } catch {
            addToast('No se pudo crear el usuario', 'error');
        }
    };

    return (
        <div className="flex flex-col h-full bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] overflow-hidden animate-fade-in">
            <WorkspaceToolbar 
                breadcrumbs={[{ label: 'Gestión Central', icon: Shield }, { label: 'Usuarios y Roles', icon: Users }]}
                viewType={viewType} setViewType={setViewType} availableViews={MEMBER_VIEWS} onSearch={setSearch}
                rightActions={
                    <button onClick={() => setIsCreateOpen(true)} className="flex items-center gap-2 px-4 py-1.5 bg-[hsl(var(--primary))] text-white rounded-lg text-[11px] font-semibold uppercase tracking-wide shadow-xl shadow-blue-500/20 active:scale-95 transition-all">
                        <UserPlus size={14} /> Añadir Usuario
                    </button>
                }
            />

            <main className="flex-1 overflow-auto scrollbar-thin">
                {loading ? (
                    <div className="p-4 space-y-4">
                        {[1,2,3,4,5,6].map(i => <Skeleton key={i} className="h-8 w-full rounded-lg" />)}
                    </div>
                ) : viewType === 'table' ? (
                    <DataTable data={filtered} columns={columns} onRowClick={handleOpenMember} />
                ) : viewType === 'list' ? (
                    <div className="divide-y divide-slate-100 p-3 dark:divide-white/5">
                        {filtered.map((member) => (
                            <button key={member.id} onClick={() => handleOpenMember(member)} className="flex w-full items-center justify-between gap-4 rounded-md px-4 py-1.5 text-left hover:bg-slate-50 dark:hover:bg-white/5">
                                <div>
                                    <p className="text-sm font-semibold text-slate-900 dark:text-white">{member.username}</p>
                                    <p className="text-xs font-semibold text-slate-400">{member.email}</p>
                                </div>
                                <span className="rounded-full bg-slate-100 px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-slate-500 dark:bg-white/10">{member.role}</span>
                            </button>
                        ))}
                    </div>
                ) : viewType === 'grid' ? (
                    <div className="grid grid-cols-1 gap-4 p-3 md:grid-cols-2 xl:grid-cols-4">
                        {filtered.map((member) => (
                            <button key={member.id} onClick={() => handleOpenMember(member)} className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-left dark:border-white/10 dark:bg-white/[0.03]">
                                <div className="mb-4 flex size-7 items-center justify-center rounded-md bg-[hsl(var(--primary))] text-sm font-semibold text-white">{member.username?.slice(0, 2).toUpperCase()}</div>
                                <p className="truncate text-sm font-semibold text-slate-900 dark:text-white">{member.username}</p>
                                <p className="truncate text-xs font-semibold text-slate-400">{member.email}</p>
                            </button>
                        ))}
                    </div>
                ) : viewType === 'board' || viewType === 'kanban' ? (
                    <div className="flex gap-4 overflow-x-auto p-3">
                        {groupedMembers.map((column) => (
                            <section key={column.role} className="w-80 shrink-0 rounded-lg border border-slate-200 bg-slate-50 p-3 dark:border-white/10 dark:bg-white/[0.03]">
                                <div className="mb-3 flex items-center justify-between px-1">
                                    <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">{column.role}</p>
                                    <span className="font-semibold text-slate-400">{column.items.length}</span>
                                </div>
                                <div className="space-y-2">
                                    {column.items.map((member) => (
                                        <button key={member.id} onClick={() => handleOpenMember(member)} className="w-full rounded-md border border-slate-200 bg-[hsl(var(--bg-primary))] p-3 text-left dark:border-white/10 dark:bg-white/5">
                                            <p className="text-xs font-semibold text-slate-900 dark:text-white">{member.username}</p>
                                            <p className="mt-1 truncate text-[10px] font-semibold text-slate-400">{member.email}</p>
                                        </button>
                                    ))}
                                </div>
                            </section>
                        ))}
                    </div>
                ) : viewType === 'calendar' ? (
                    <div className="h-[720px] p-3"><UniversalCalendarView events={calendarEvents} title="Calendario de usuarios" /></div>
                ) : viewType === 'gantt' ? (
                    <div className="h-[720px] p-3"><UniversalGanttView items={ganttItems} moduleName="Usuarios y roles" /></div>
                ) : (
                    <div className="p-3"><UniversalWikiView moduleName="Usuarios y roles" storageKey="wiki_admin_members" /></div>
                )}
            </main>

            <WorkspaceDrawer 
                isOpen={isDrawerOpen} onClose={() => setIsDrawerOpen(false)}
                title={selectedMember?.username || 'Detalles de Usuario'}
                subtitle="Configuración Técnica de Cuenta"
                actions={<><button className="px-4 py-2 text-[11px] font-bold text-rose-500">Bloquear Cuenta</button><button className="px-3 py-2 bg-slate-900 dark:bg-[hsl(var(--bg-primary))] text-white dark:text-slate-900 rounded-lg text-[11px] font-bold shadow-lg">Guardar Cambios</button></>}
            >
                <div className="space-y-3 animate-fade-in">
                    <section className="flex items-center gap-3">
                        <div className="size-8 rounded-lg bg-slate-100 dark:bg-white/5 border-2 border-slate-200 dark:border-white/10 flex items-center justify-center overflow-hidden shadow-xl">
                            <Image src={`https://ui-avatars.com/api/?name=${selectedMember?.username}&background=random&color=fff`} alt="AV" width={80} height={80} unoptimized />
                        </div>
                        <div className="space-y-1">
                            <h3 className="text-lg font-bold text-slate-800 dark:text-white tracking-tight">{selectedMember?.username}</h3>
                            <p className="text-sm text-slate-500 font-medium">{selectedMember?.email}</p>
                        </div>
                    </section>

                    <section className="grid grid-cols-2 gap-4">
                        <AdminStat label="Rol Actual" value={selectedMember?.role} icon={Shield} />
                        <AdminStat label="Verificación" value={selectedMember?.is_email_verified ? 'Completada' : 'Pendiente'} icon={Mail} />
                        <AdminStat label="Último Acceso" value="Hace 2 horas" icon={Clock} />
                        <AdminStat label="Dispositivo" value="Desktop (Win32)" icon={Smartphone} />
                    </section>

                    <section className="p-3 bg-blue-50 dark:bg-blue-900/10 rounded-lg border border-blue-100 dark:border-blue-900/30 flex items-center justify-between">
                        <div className="flex items-center gap-4">
                            <div className="size-7 rounded-lg bg-[hsl(var(--bg-primary))] dark:bg-white/10 flex items-center justify-center text-[hsl(var(--primary))] shadow-sm"><Fingerprint size={24} /></div>
                            <div>
                                <h4 className="text-[11px] font-semibold uppercase tracking-wide text-[hsl(var(--primary))]">Seguridad Biométrica / 2FA</h4>
                                <p className="text-xs text-slate-500">Forzar autenticación de dos factores.</p>
                            </div>
                        </div>
                        <div className="h-6 w-11 bg-slate-200 dark:bg-white/10 rounded-full relative cursor-pointer"><div className="absolute left-1 top-1 size-4 bg-[hsl(var(--bg-primary))] rounded-full" /></div>
                    </section>
                </div>
            </WorkspaceDrawer>

            <WorkspaceDrawer
                isOpen={isCreateOpen}
                onClose={() => setIsCreateOpen(false)}
                title="Nuevo Usuario"
                subtitle="Alta de cuenta y rol inicial"
                actions={
                    <>
                        <button onClick={() => setIsCreateOpen(false)} className="px-4 py-2 text-[11px] font-bold text-slate-500">Cancelar</button>
                        <button onClick={handleCreateMember} className="px-3 py-2 bg-[hsl(var(--primary))] text-white rounded-lg text-[11px] font-bold shadow-lg">Crear usuario</button>
                    </>
                }
            >
                <div className="space-y-4">
                    <input value={newMember.username} onChange={(e) => setNewMember((prev) => ({ ...prev, username: e.target.value }))} placeholder="Usuario" className="w-full rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-bold outline-none dark:border-white/10 dark:bg-white/5" />
                    <input value={newMember.email} onChange={(e) => setNewMember((prev) => ({ ...prev, email: e.target.value }))} placeholder="Correo" type="email" className="w-full rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-bold outline-none dark:border-white/10 dark:bg-white/5" />
                    <input value={newMember.password} onChange={(e) => setNewMember((prev) => ({ ...prev, password: e.target.value }))} placeholder="Contraseña inicial" type="password" className="w-full rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-bold outline-none dark:border-white/10 dark:bg-white/5" />
                    <select value={newMember.role} onChange={(e) => setNewMember((prev) => ({ ...prev, role: e.target.value }))} className="w-full rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-bold outline-none dark:border-white/10 dark:bg-white/5">
                        {ROLE_OPTIONS.map((role) => <option key={role.value} value={role.value}>{role.label}</option>)}
                    </select>
                </div>
            </WorkspaceDrawer>
        </div>
    );
}

function AdminStat({ label, value, icon: Icon }: any) {
    return (
        <div className="p-4 bg-slate-50 dark:bg-white/5 border border-slate-100 dark:border-white/5 rounded-lg group hover:border-blue-500/20 transition-all">
            <div className="flex items-center gap-2 mb-2">
                <Icon size={14} className="text-slate-400 group-hover:text-[hsl(var(--primary))]" />
                <span className="font-semibold text-slate-400 uppercase tracking-wide">{label}</span>
            </div>
            <p className="font-semibold text-slate-800 dark:text-white capitalize">{value}</p>
        </div>
    );
}

