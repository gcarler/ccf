"use client";

import React, { useState, useEffect, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import CrmShell from '@/components/crm/CrmShell';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    Users, 
    Plus, 
    Search,
    ChevronRight,
    LayoutDashboard,
    Filter,
    TrendingUp,
    CheckCircle2,
    Loader2,
    Send
} from 'lucide-react';
import { toast } from 'sonner';
import clsx from 'clsx';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';

interface Department {
    id: number;
    name: string;
    code: string;
}

interface City {
    id: number;
    department_id: number;
    name: string;
}



export default function MembersPage() {
    const { token } = useAuth();
    const router = useRouter();
    const [members, setMembers] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    

    const [roles, setRoles] = useState<any[]>([]);
    const [isCreateOpen, setIsCreateOpen] = useState(false);
    const [isSaving, setIsSaving] = useState(false);
    const [newMember, setNewMember] = useState({
        first_name: '',
        last_name: '',
        email: '',
        phone: '',
        church_role: 'Miembro',
        colombian_department_id: null as number | null,
        city: '',
    });
    const [departments, setDepartments] = useState<Department[]>([]);
    const [cities, setCities] = useState<City[]>([]);
    const [loadingCities, setLoadingCities] = useState(false);
    
    // Filters
    const [query, setQuery] = useState('');
    const [roleFilter, setRoleFilter] = useState('Todos');

    useEffect(() => {
        if (!token) return;

        const loadMembers = async () => {
            try {
                setLoading(true);
                const [membersData, rolesData, deptData] = await Promise.all([
                    apiFetch<any[]>('/crm/members', { token }).catch(() => []),
                    apiFetch<any[]>('/crm/roles', { token }).catch(() => []),
                    apiFetch<Department[]>('/crm/colombian-departments', { token }).catch(() => []),
                ]);
                setMembers(membersData);
                setRoles(rolesData);
                setDepartments(deptData);

            } catch (err) {
                toast.error('Error al cargar membresía');
            } finally {
                setLoading(false);
            }
        };
        loadMembers();
    }, [token]);

    useEffect(() => {
        if (!token || !newMember.colombian_department_id) {
            setCities([]);
            return;
        }
        setLoadingCities(true);
        apiFetch<City[]>(`/crm/colombian-departments/${newMember.colombian_department_id}/cities`, { token })
            .then(setCities)
            .catch(() => setCities([]))
            .finally(() => setLoadingCities(false));
    }, [token, newMember.colombian_department_id]);


    const getRoleColor = (roleName: string) => {
        const r = roles.find(x => roleName?.toLowerCase().includes(x.name.toLowerCase()));
        return r ? r.color : 'text-slate-600 bg-slate-100 dark:bg-white/10 dark:text-slate-400';
    };

    const stats = useMemo(() => {
        const total = members.length;
        const baptized = members.filter(m => m.baptism_date).length;
        const leaders = members.filter(m => 
            ['Apóstol','Profeta','Evangelista','Pastor','Maestro','Líder','Ministro de Culto'].some(r => 
                m.church_role?.includes(r)
            )
        ).length;
        const newThisMonth = members.filter(m => {
            const d = new Date(m.created_at);
            const now = new Date();
            return d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear();
        }).length;
        return { total, baptized, leaders, newThisMonth };
    }, [members]);

    const filteredMembers = useMemo(() => {
        let list = members;
        if (query) {
            const q = query.toLowerCase();
            list = list.filter(m => 
                `${m.first_name} ${m.last_name}`.toLowerCase().includes(q) ||
                m.email?.toLowerCase().includes(q) ||
                m.church_role?.toLowerCase().includes(q)
            );
        }
        if (roleFilter !== 'Todos') {
            list = list.filter(m => m.church_role === roleFilter);
        }
        return list;
    }, [members, query, roleFilter]);

    const handleCreateMember = async (event: React.FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        if (!token || !newMember.first_name.trim() || !newMember.last_name.trim()) return;

        setIsSaving(true);
        try {
            const created = await apiFetch<any>('/crm/members/', {
                method: 'POST',
                token,
                body: newMember,
            });
            setMembers(prev => [created, ...prev]);
            setNewMember({
                first_name: '',
                last_name: '',
                email: '',
                phone: '',
                church_role: 'Miembro',
                colombian_department_id: null,
                city: '',
            });
            setIsCreateOpen(false);
            toast.success('Miembro registrado');
        } catch {
            toast.error('No se pudo registrar el miembro');
        } finally {
            setIsSaving(false);
        }
    };

    return (
        <CrmShell
            breadcrumbs={[
                { label: 'CRM', icon: LayoutDashboard, href: '/plataforma/crm' },
                { label: 'Membresía', icon: Users },
            ]}
        >
            <main className="flex-1 overflow-y-auto scrollbar-thin">
                {/* Header Hero */}
                <div className="relative bg-gradient-to-br from-blue-600 via-indigo-600 to-blue-700 px-3 py-2 overflow-hidden">
                    <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_rgba(255,255,255,0.1)_0%,_transparent_60%)] pointer-events-none" />
                    <div className="absolute -bottom-8 -right-8 size-10 rounded-full bg-white/5 blur-2xl" />
                    <div className="relative z-10 flex flex-col md:flex-row md:items-end justify-between gap-4">
                        <div>
                            <p className="text-[10px] font-bold uppercase tracking-wide text-blue-200 mb-2">Consolidación</p>
                            <h1 className="text-lg font-bold text-white tracking-tight mb-1">Base de Membresía</h1>
                            <p className="text-blue-200 text-sm font-medium">Directorio completo de la comunidad CCF</p>
                        </div>
                        <button 
                            onClick={() => setIsCreateOpen(true)}
                            className="flex items-center gap-2 px-4 py-1.5 bg-white text-blue-700 rounded-lg text-[11px] font-bold uppercase tracking-wide shadow-xl hover:shadow-2xl hover:scale-105 transition-all active:scale-95 shrink-0"
                        >
                            <Plus size={16} /> Nuevo Miembro
                        </button>
                    </div>
                </div>

 <div className="p-4 lg:p-4 space-y-4 w-full">
                    {/* Metrics */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        {[
                            { label: 'Total Miembros', value: stats.total, icon: Users, color: 'text-blue-600', bg: 'bg-blue-50 dark:bg-blue-900/20' },
                            { label: 'Líderes Activos', value: stats.leaders, icon: CheckCircle2, color: 'text-emerald-600', bg: 'bg-emerald-50 dark:bg-emerald-900/20' },
                            { label: 'Bautizados', value: stats.baptized, icon: Filter, color: 'text-indigo-600', bg: 'bg-indigo-50 dark:bg-indigo-900/20' },
                            { label: 'Nuevos (Mes)', value: stats.newThisMonth, icon: TrendingUp, color: 'text-amber-600', bg: 'bg-amber-50 dark:bg-amber-900/20' },
                        ].map((s, i) => (
                            <div key={i} className="p-3 rounded-md border border-slate-100 dark:border-white/5 bg-white dark:bg-white/5 flex flex-col justify-between gap-4 shadow-sm hover:shadow-md transition-all">
                                <div className={clsx("size-8 rounded-md flex items-center justify-center", s.bg, s.color)}>
                                    <s.icon size={20} />
                                </div>
                                <div>
                                    <p className="text-xl font-bold text-slate-800 dark:text-white">{s.value}</p>
                                    <p className="text-[10px] font-bold uppercase tracking-wide text-slate-400 mt-1">{s.label}</p>
                                </div>
                            </div>
                        ))}
                    </div>

                    {/* Filters Toolbar */}
                    <div className="sticky top-0 z-10 bg-slate-50/80 dark:bg-[#121212]/80 backdrop-blur-xl py-2 flex flex-col md:flex-row gap-4">
                        <div className="relative flex-1">
                            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                            <input 
                                value={query}
                                onChange={(e) => setQuery(e.target.value)}
                                placeholder="Buscar por nombre, correo o ministerio..."
                                className="w-full bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg py-1.5 pl-12 pr-4 text-sm font-medium outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-all shadow-sm"
                            />
                        </div>
                        
                        <div className="flex items-center gap-2 overflow-x-auto pb-2 md:pb-0 scrollbar-none snap-x">
                            <button
                                onClick={() => setRoleFilter('Todos')}
                                className={clsx(
                                    "px-4 py-1.5 rounded-lg text-[11px] font-bold uppercase tracking-wide whitespace-nowrap transition-all shrink-0 snap-start",
                                    roleFilter === 'Todos' ? "bg-slate-800 text-white dark:bg-white dark:text-slate-900 shadow-md" : "bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 text-slate-500 hover:bg-slate-100 dark:hover:bg-white/10"
                                )}
                            >Todos</button>
                            {roles.map(role => (
                                <button
                                    key={role.id}
                                    onClick={() => setRoleFilter(role.name)}
                                    className={clsx(
                                        "px-4 py-1.5 rounded-lg text-[11px] font-bold uppercase tracking-wide whitespace-nowrap transition-all shrink-0 snap-start",
                                        roleFilter === role.name 
                                            ? "bg-slate-800 text-white dark:bg-white dark:text-slate-900 shadow-md"
                                            : "bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 text-slate-500 hover:bg-slate-100 dark:hover:bg-white/10"
                                    )}
                                >
                                    {role.name}
                                </button>
                            ))}
                        </div>

                    </div>

                    {/* Members List */}
                    {loading ? (
                        <div className="text-center py-1.5 animate-pulse font-bold uppercase tracking-wide text-slate-400">
                            Sincronizando base de datos...
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                            <AnimatePresence>
                                {filteredMembers.map(member => (
                                    <motion.div
                                        key={member.id}
                                        layout
                                        initial={{ opacity: 0, scale: 0.95 }}
                                        animate={{ opacity: 1, scale: 1 }}
                                        exit={{ opacity: 0, scale: 0.9 }}
                                        transition={{ duration: 0.2 }}
                                    >
                                        <div 
                                            onClick={() => router.push(`/crm/members/${member.id}`)}
                                            className="group p-3 bg-white dark:bg-[#1e1f21] border border-slate-200 dark:border-white/5 rounded-md hover:border-blue-500/30 hover:shadow-xl hover:shadow-blue-500/10 transition-all cursor-pointer flex items-center justify-between"
                                        >
                                            <div className="flex items-center gap-4">
                                                <div className="relative">
                                                    <div className="size-9 rounded-lg bg-gradient-to-br from-slate-100 to-slate-200 dark:from-white/5 dark:to-white/10 flex items-center justify-center text-slate-600 dark:text-slate-300 font-bold text-sm">
                                                        {member.first_name[0]}{member.last_name[0]}
                                                    </div>
                                                    <div className={clsx("absolute -bottom-1 -right-1 size-4 rounded-full border-2 border-white dark:border-[#1e1f21]", member.spiritual_health > 0.7 ? "bg-emerald-500" : member.spiritual_health > 0.4 ? "bg-amber-500" : "bg-red-500")} />
                                                </div>
                                                <div>
                                                    <h3 className="text-sm font-bold text-slate-900 dark:text-white uppercase truncate max-w-[150px]">{member.first_name} {member.last_name}</h3>
                                                    <div className="mt-1 flex items-center gap-2">
                                                        <span className={clsx(`px-2 py-0.5 rounded-md text-[9px] font-bold uppercase tracking-wide`, getRoleColor(member.church_role || ''))}>
                                                            {member.church_role || 'Miembro'}
                                                        </span>
                                                    </div>
                                                </div>
                                            </div>
                                            <div className="size-8 rounded-full bg-slate-50 dark:bg-white/5 flex items-center justify-center text-slate-400 group-hover:bg-blue-50 dark:group-hover:bg-blue-500/20 group-hover:text-blue-600 transition-all">
                                                <ChevronRight size={16} />
                                            </div>
                                        </div>
                                    </motion.div>
                                ))}
                            </AnimatePresence>
                            {filteredMembers.length === 0 && (
                                <div className="col-span-full py-1.5 text-center font-bold text-slate-400">
                                    No se encontraron miembros con esos filtros.
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </main>
            <WorkspaceDrawer
                isOpen={isCreateOpen}
                onClose={() => setIsCreateOpen(false)}
                title="Nuevo Miembro"
                subtitle="Registrar perfil en la base ministerial"
                actions={
                    <>
                        <button type="button" onClick={() => setIsCreateOpen(false)} className="px-4 py-2 text-[11px] font-bold text-slate-500 hover:text-slate-700">
                            Cancelar
                        </button>
                        <button form="create-member-form" type="submit" disabled={isSaving} className="flex items-center gap-2 rounded-lg bg-blue-600 px-3 py-2 text-[11px] font-bold uppercase tracking-wide text-white shadow-lg shadow-blue-500/20 transition-all hover:bg-blue-700 active:scale-95 disabled:opacity-60">
                            {isSaving ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
                            Registrar
                        </button>
                    </>
                }
            >
                <form id="create-member-form" onSubmit={handleCreateMember} className="space-y-2">
                    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                        <MemberField label="Nombre *" value={newMember.first_name} onChange={value => setNewMember(prev => ({ ...prev, first_name: value }))} placeholder="Juan" required />
                        <MemberField label="Apellido *" value={newMember.last_name} onChange={value => setNewMember(prev => ({ ...prev, last_name: value }))} placeholder="Pérez" required />
                    </div>
                    <MemberField label="Correo" type="email" value={newMember.email} onChange={value => setNewMember(prev => ({ ...prev, email: value }))} placeholder="correo@ejemplo.com" />
                    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                        <MemberField label="Teléfono" value={newMember.phone} onChange={value => setNewMember(prev => ({ ...prev, phone: value }))} placeholder="+57 300 000 0000" />
                        <div className="space-y-2">
                            <label className="text-[10px] font-bold uppercase tracking-wide text-slate-400">Rol</label>
                            <select value={newMember.church_role} onChange={event => setNewMember(prev => ({ ...prev, church_role: event.target.value }))} className="w-full rounded-lg border border-slate-200 bg-slate-50 px-4 py-1.5 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-white/10 dark:bg-black/20 dark:text-white">
                                <option value="Miembro">Miembro</option>
                                {roles.map(role => <option key={role.id} value={role.name}>{role.name}</option>)}
                            </select>
                        </div>
                    </div>
                    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                        <div className="space-y-2">
                            <label className="text-[10px] font-bold uppercase tracking-wide text-slate-400">Departamento</label>
                            <select
                                value={newMember.colombian_department_id ?? ''}
                                onChange={e => setNewMember(prev => ({ ...prev, colombian_department_id: e.target.value ? Number(e.target.value) : null, city: '' }))}
                                className="w-full rounded-lg border border-slate-200 bg-slate-50 px-4 py-1.5 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-white/10 dark:bg-black/20 dark:text-white"
                            >
                                <option value="">Seleccionar departamento</option>
                                {departments.map(d => (
                                    <option key={d.id} value={d.id}>{d.name}</option>
                                ))}
                            </select>
                        </div>
                        <div className="space-y-2">
                            <label className="text-[10px] font-bold uppercase tracking-wide text-slate-400">Ciudad</label>
                            <select
                                value={newMember.city}
                                onChange={e => setNewMember(prev => ({ ...prev, city: e.target.value }))}
                                disabled={!newMember.colombian_department_id || loadingCities}
                                className="w-full rounded-lg border border-slate-200 bg-slate-50 px-4 py-1.5 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500/20 disabled:opacity-50 disabled:cursor-not-allowed dark:border-white/10 dark:bg-black/20 dark:text-white"
                            >
                                <option value="">
                                    {loadingCities ? 'Cargando ciudades...' : 'Seleccionar ciudad'}
                                </option>
                                {cities.map(c => (
                                    <option key={c.id} value={c.name}>{c.name}</option>
                                ))}
                            </select>
                        </div>
                    </div>
                </form>
            </WorkspaceDrawer>
        </CrmShell>
    );
}

function MemberField({
    label,
    value,
    onChange,
    placeholder,
    type = 'text',
    required = false,
}: {
    label: string;
    value: string;
    onChange: (value: string) => void;
    placeholder: string;
    type?: string;
    required?: boolean;
}) {
    return (
        <div className="space-y-2">
            <label className="text-[10px] font-bold uppercase tracking-wide text-slate-400">{label}</label>
            <input required={required} type={type} value={value} onChange={event => onChange(event.target.value)} placeholder={placeholder} className="w-full rounded-lg border border-slate-200 bg-slate-50 px-4 py-1.5 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-white/10 dark:bg-black/20 dark:text-white" />
        </div>
    );
}
