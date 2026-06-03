"use client";

import React, { useState, useEffect, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import CrmShell from '@/components/crm/CrmShell';
import ViewSwitcher, { ViewType } from '@/components/ViewSwitcher';
import { useViewType, FULL_VIEWS } from '@/hooks/useViewType';
import TableView, { TableColumn } from '@/components/ui/TableView';
import { useTableView } from '@/hooks/useTableView';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Plus,
    Search,
    ChevronRight,
    ChevronDown,
    LayoutDashboard,
    Loader2,
    Send,
    X,
    SlidersHorizontal,
    Fingerprint,
    Phone,
    Calendar,
    MapPin,
    VenetianMask,
    BookOpen,
    Users
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

const ID_TYPES = ['Cédula de Ciudadanía', 'Cédula de Extranjería', 'Pasaporte', 'Tarjeta de Identidad', 'NIT', 'Otro'];
const MARITAL_STATUSES = ['Soltero(a)', 'Casado(a)', 'Unión Libre', 'Divorciado(a)', 'Viudo(a)', 'Separado(a)'];
const SEX_OPTIONS = ['Masculino', 'Femenino'];
const EDUCATION_LEVELS = ['Primaria', 'Secundaria', 'Técnico', 'Tecnólogo', 'Universitario', 'Postgrado', 'Maestría', 'Doctorado'];
const EDUCATION_STATUSES = ['Cursando', 'Completado', 'Incompleto'];
const BLOOD_TYPES = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'];
const HOUSING_TYPES = ['Propia', 'Arriendo', 'Familiar', 'Otro'];
const MEMBERSHIP_TYPES = ['Activo', 'Inactivo', 'Transferido', 'Fallecido'];
const ATTENDANCE_TYPES = ['Regular', 'Constante', 'Irregular', 'Ausente'];

type MemberFormData = {
    first_name: string;
    last_name: string;
    email: string;
    phone: string;
    church_role: string;
    second_name: string;
    second_last_name: string;
    id_type: string;
    id_number: string;
    birth_country: string;
    sex: string;
    marital_status: string;
    birthday: string;
    landline_phone: string;
    other_phone: string;
    mobile_phone: string;
    address: string;
    housing_type: string;
    colombian_department_id: number | null;
    city: string;
    education_level: string;
    education_status: string;
    profession: string;
    economic_sector: string;
    blood_type: string;
    medical_notes: string;
    membership_type: string;
    attendance_type: string;
    group_name: string;
    campus: string;
    church_join_date: string;
    baptism_date: string;
    responsible_adult_name: string;
    responsible_adult_contact: string;
    guardian_name: string;
    guardian_contact: string;
    talents: string;
    spiritual_gifts: string;
    pastoral_notes: string;
    registration_reason: string;
    unregistration_reason: string;
    registration_date: string;
    unregistration_date: string;
    optional_info: string;
    last_group_attendance: string;
    last_meeting_attendance: string;
};

const INITIAL_MEMBER: MemberFormData = {
    first_name: '', last_name: '', email: '', phone: '', church_role: 'Miembro',
    second_name: '', second_last_name: '', id_type: '', id_number: '',
    birth_country: '', sex: '', marital_status: '', birthday: '',
    landline_phone: '', other_phone: '', mobile_phone: '', address: '', housing_type: '',
    colombian_department_id: null, city: '',
    education_level: '', education_status: '', profession: '', economic_sector: '',
    blood_type: '', medical_notes: '',
    membership_type: '', attendance_type: '', group_name: '', campus: '',
    church_join_date: '', baptism_date: '',
    responsible_adult_name: '', responsible_adult_contact: '', guardian_name: '', guardian_contact: '',
    talents: '', spiritual_gifts: '', pastoral_notes: '',
    registration_reason: '', unregistration_reason: '', registration_date: '', unregistration_date: '',
    optional_info: '', last_group_attendance: '', last_meeting_attendance: '',
};

// ─── Sub-components ───────────────────────────────────────────────────────────

function FormSection({ title, defaultOpen, children }: { title: string; defaultOpen?: boolean; children: React.ReactNode }) {
    const [open, setOpen] = useState(defaultOpen ?? false);
    return (
        <div className="border border-slate-100 dark:border-white/10 rounded-lg overflow-hidden">
            <button type="button" onClick={() => setOpen(!open)} className="w-full flex items-center justify-between px-3 py-2 bg-slate-50 dark:bg-white/5 text-[10px] font-bold uppercase tracking-wide text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 transition-colors">
                <span>{title}</span>
                <ChevronDown size={14} className={clsx("transition-transform", open && "rotate-180")} />
            </button>
            <AnimatePresence initial={false}>
                {open && (
                    <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.2 }} className="px-3 py-2 space-y-2">
                        {children}
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}

function SelectField({ label, value, onChange, options, placeholder }: { label: string; value: string; onChange: (v: string) => void; options: string[]; placeholder?: string }) {
    return (
        <div className="space-y-2">
            <label className="text-[10px] font-bold uppercase tracking-wide text-slate-400">{label}</label>
            <select value={value} onChange={e => onChange(e.target.value)} className="w-full rounded-lg border border-slate-200 bg-slate-50 px-4 py-1.5 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-white/10 dark:bg-black/20 dark:text-white">
                <option value="">{placeholder ?? 'Seleccionar...'}</option>
                {options.map(o => <option key={o} value={o}>{o}</option>)}
            </select>
        </div>
    );
}

function MemberField({ label, value, onChange, placeholder, type = 'text', required = false }: { label: string; value: string; onChange: (v: string) => void; placeholder: string; type?: string; required?: boolean }) {
    return (
        <div className="space-y-2">
            <label className="text-[10px] font-bold uppercase tracking-wide text-slate-400">{label}</label>
            <input required={required} type={type} value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder} className="w-full rounded-lg border border-slate-200 bg-slate-50 px-4 py-1.5 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-white/10 dark:bg-black/20 dark:text-white" />
        </div>
    );
}

// ─── Main Component ───────────────────────────────────────────────────────────

export default function MembersPage() {
    const { token } = useAuth();
    const router = useRouter();
    const { viewType, setViewType } = useViewType('crm_members', 'grid');
    const [members, setMembers] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    const [roles, setRoles] = useState<any[]>([]);
    const [isCreateOpen, setIsCreateOpen] = useState(false);
    const [isSaving, setIsSaving] = useState(false);
    const [newMember, setNewMember] = useState<MemberFormData>({ ...INITIAL_MEMBER });
    const [departments, setDepartments] = useState<Department[]>([]);
    const [cities, setCities] = useState<City[]>([]);
    const [loadingCities, setLoadingCities] = useState(false);

    const [query, setQuery] = useState('');
    const [roleFilter, setRoleFilter] = useState('Todos');
    const [idTypeFilter, setIdTypeFilter] = useState('');
    const [sexFilter, setSexFilter] = useState('');
    const [groupFilter, setGroupFilter] = useState('');
    const [membershipFilter, setMembershipFilter] = useState('');
    const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
    const [uniqueGroups, setUniqueGroups] = useState<string[]>([]);
    const [activeFilterCount, setActiveFilterCount] = useState(0);

    useEffect(() => {
        if (!token) return;
        const loadMembers = async () => {
            try {
                setLoading(true);
                const [membersData, rolesData, deptData] = await Promise.all([
                    apiFetch<any[]>('/crm/personas', { token }).catch(() => []),
                    apiFetch<any[]>('/crm/roles', { token }).catch(() => []),
                    apiFetch<Department[]>('/crm/colombian-departments', { token }).catch(() => []),
                ]);
                setMembers(membersData);
                setRoles(rolesData);
                setDepartments(deptData);
                // Extract unique group names for filter
                const groups = [...new Set(membersData.map((m: any) => m.group_name).filter(Boolean))] as string[];
                groups.sort();
                setUniqueGroups(groups);
            } catch {
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

    const filteredMembers = useMemo(() => {
        let list = members;
        if (query) {
            const q = query.toLowerCase();
            list = list.filter(m =>
                (m.nombre_completo || '').toLowerCase().includes(q) ||
                m.email?.toLowerCase().includes(q) ||
                m.church_role?.toLowerCase().includes(q) ||
                (m.id_number || '').toLowerCase().includes(q) ||
                (m.phone || '').toLowerCase().includes(q) ||
                (m.mobile_phone || '').toLowerCase().includes(q)
            );
        }
        if (roleFilter !== 'Todos') {
            list = list.filter(m => m.church_role === roleFilter);
        }
        if (idTypeFilter) {
            list = list.filter(m => m.id_type === idTypeFilter);
        }
        if (sexFilter) {
            list = list.filter(m => m.sex === sexFilter);
        }
        if (groupFilter) {
            list = list.filter(m => m.group_name === groupFilter);
        }
        if (membershipFilter) {
            list = list.filter(m => m.membership_type === membershipFilter);
        }
        // Count active filters
        const count = [idTypeFilter, sexFilter, groupFilter, membershipFilter].filter(Boolean).length
            + (roleFilter !== 'Todos' ? 1 : 0);
        setActiveFilterCount(count);
        return list;
    }, [members, query, roleFilter, idTypeFilter, sexFilter, groupFilter, membershipFilter]);

    const um = (key: keyof MemberFormData) => (value: string) => setNewMember(prev => ({ ...prev, [key]: value }));

    const handleCreateMember = async (event: React.FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        if (!token || !newMember.first_name.trim() || !newMember.last_name.trim()) return;

        setIsSaving(true);
        try {
            const body: any = { ...newMember };
            if (!body.colombian_department_id) body.colombian_department_id = null;
            // Convert empty date strings to null
            ['birthday','church_join_date','baptism_date','registration_date','unregistration_date','last_group_attendance','last_meeting_attendance'].forEach(k => {
                if (!body[k]) body[k] = null;
            });

            const created = await apiFetch<any>('/crm/personas/', {
                method: 'POST',
                token,
                body,
            });
            setMembers(prev => [created, ...prev]);
            setNewMember({ ...INITIAL_MEMBER });
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
                { label: 'Personas', icon: LayoutDashboard },
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
                            <h1 className="text-lg font-bold text-white tracking-tight mb-1">Directorio de Personas</h1>
                            <p className="text-blue-200 text-sm font-medium">Directorio completo de la comunidad CCF</p>
                        </div>
                        <button
                            onClick={() => setIsCreateOpen(true)}
                            className="flex items-center gap-2 px-4 py-1.5 bg-[hsl(var(--surface-1))] text-[hsl(var(--primary))] rounded-lg text-[11px] font-bold uppercase tracking-wide shadow-xl hover:shadow-2xl hover:scale-105 transition-all active:scale-95 shrink-0"
                        >
                            <Plus size={16} /> Nuevo Miembro
                        </button>
                    </div>
                </div>

                <div className="p-4 lg:p-4 space-y-4 w-full">
                    {/* Filters Toolbar */}
                    <div className="sticky top-0 z-10 bg-slate-50/80 dark:bg-[#121212]/80 backdrop-blur-xl pt-2 space-y-2">
                        {/* Search + Filter Toggle Row */}
                        <div className="flex flex-col md:flex-row gap-2">
                            <div className="relative flex-1">
                                <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                                <input
                                    value={query}
                                    onChange={e => setQuery(e.target.value)}
                                    placeholder="Buscar por nombre, documento, teléfono, email o ministerio..."
                                    className="w-full bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg py-1.5 pl-12 pr-4 text-sm font-medium outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-all shadow-sm"
                                />
                            </div>
                            <div className="flex items-center gap-2 shrink-0">
                                <button
                                    onClick={() => setShowAdvancedFilters(!showAdvancedFilters)}
                                    className={clsx(
                                        "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-bold uppercase tracking-wide transition-all shrink-0 border",
                                        showAdvancedFilters || activeFilterCount > 0
                                            ? "bg-ccf-blue text-white border-ccf-blue shadow-md"
                                            : "bg-[hsl(var(--surface-1))] dark:bg-white/5 border-slate-200 dark:border-white/10 text-slate-500 hover:bg-slate-100 dark:hover:bg-white/10"
                                    )}
                                >
                                    <SlidersHorizontal size={14} />
                                    Filtros
                                    {activeFilterCount > 0 && (
                                        <span className="ml-1 size-4 rounded-full bg-white text-ccf-blue text-[9px] font-bold flex items-center justify-center">
                                            {activeFilterCount}
                                        </span>
                                    )}
                                </button>
                                <ViewSwitcher viewType={viewType} setViewType={setViewType} availableViews={FULL_VIEWS} />
                            </div>
                        </div>

                        {/* Role Chips Row */}
                        <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-none snap-x">
                            <button onClick={() => setRoleFilter('Todos')} className={clsx("px-3 py-1 rounded-lg text-[10px] font-bold uppercase tracking-wide whitespace-nowrap transition-all shrink-0 snap-start", roleFilter === 'Todos' ? "bg-slate-800 text-white dark:bg-[hsl(var(--bg-primary))] dark:text-slate-900 shadow-md" : "bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-slate-200 dark:border-white/10 text-slate-500 hover:bg-slate-100 dark:hover:bg-white/10")}>Todos</button>
                            {roles.map(role => (
                                <button key={role.id} onClick={() => setRoleFilter(role.name)} className={clsx("px-3 py-1 rounded-lg text-[10px] font-bold uppercase tracking-wide whitespace-nowrap transition-all shrink-0 snap-start", roleFilter === role.name ? "bg-slate-800 text-white dark:bg-[hsl(var(--bg-primary))] dark:text-slate-900 shadow-md" : "bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-slate-200 dark:border-white/10 text-slate-500 hover:bg-slate-100 dark:hover:bg-white/10")}>{role.name}</button>
                            ))}
                        </div>

                        {/* Advanced Filters Panel */}
                        <AnimatePresence>
                            {showAdvancedFilters && (
                                <motion.div
                                    initial={{ height: 0, opacity: 0 }}
                                    animate={{ height: 'auto', opacity: 1 }}
                                    exit={{ height: 0, opacity: 0 }}
                                    transition={{ duration: 0.2 }}
                                    className="overflow-hidden"
                                >
                                    <div className="bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg p-3">
                                        <div className="flex items-center justify-between mb-2">
                                            <h4 className="text-[10px] font-bold uppercase tracking-wide text-slate-400">Filtros Avanzados</h4>
                                            <button
                                                onClick={() => {
                                                    setIdTypeFilter('');
                                                    setSexFilter('');
                                                    setGroupFilter('');
                                                    setMembershipFilter('');
                                                    setRoleFilter('Todos');
                                                }}
                                                className="flex items-center gap-1 text-[10px] font-bold uppercase tracking-wide text-red-400 hover:text-red-500 transition-colors"
                                            >
                                                <X size={12} /> Limpiar
                                            </button>
                                        </div>
                                        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                                            {/* Tipo de Identificación */}
                                            <div className="space-y-1">
                                                <label className="flex items-center gap-1 text-[9px] font-bold uppercase tracking-wide text-slate-400">
                                                    <Fingerprint size={11} /> Tipo ID
                                                </label>
                                                <select
                                                    value={idTypeFilter}
                                                    onChange={e => setIdTypeFilter(e.target.value)}
                                                    className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-black/20 px-2.5 py-1 text-[11px] font-semibold outline-none focus:ring-2 focus:ring-blue-500/20"
                                                >
                                                    <option value="">Todos</option>
                                                    <option value="Cédula De Ciudadanía">Cédula Ciudadanía</option>
                                                    <option value="Cédula De Extranjería">Cédula Extranjería</option>
                                                    <option value="Pasaporte">Pasaporte</option>
                                                    <option value="Tarjeta De Identidad">Tarjeta Identidad</option>
                                                    <option value="NIT">NIT</option>
                                                    <option value="Otro">Otro</option>
                                                </select>
                                            </div>

                                            {/* Sexo */}
                                            <div className="space-y-1">
                                                <label className="flex items-center gap-1 text-[9px] font-bold uppercase tracking-wide text-slate-400">
                                                    <VenetianMask size={11} /> Sexo
                                                </label>
                                                <select
                                                    value={sexFilter}
                                                    onChange={e => setSexFilter(e.target.value)}
                                                    className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-black/20 px-2.5 py-1 text-[11px] font-semibold outline-none focus:ring-2 focus:ring-blue-500/20"
                                                >
                                                    <option value="">Todos</option>
                                                    <option value="M">Masculino</option>
                                                    <option value="F">Femenino</option>
                                                </select>
                                            </div>

                                            {/* Grupo */}
                                            <div className="space-y-1">
                                                <label className="flex items-center gap-1 text-[9px] font-bold uppercase tracking-wide text-slate-400">
                                                    <MapPin size={11} /> Grupo
                                                </label>
                                                <select
                                                    value={groupFilter}
                                                    onChange={e => setGroupFilter(e.target.value)}
                                                    className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-black/20 px-2.5 py-1 text-[11px] font-semibold outline-none focus:ring-2 focus:ring-blue-500/20"
                                                >
                                                    <option value="">Todos</option>
                                                    {uniqueGroups.map(g => (
                                                        <option key={g} value={g}>{g}</option>
                                                    ))}
                                                </select>
                                            </div>

                                            {/* Tipo Membresía */}
                                            <div className="space-y-1">
                                                <label className="flex items-center gap-1 text-[9px] font-bold uppercase tracking-wide text-slate-400">
                                                    <BookOpen size={11} /> Membresía
                                                </label>
                                                <select
                                                    value={membershipFilter}
                                                    onChange={e => setMembershipFilter(e.target.value)}
                                                    className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-black/20 px-2.5 py-1 text-[11px] font-semibold outline-none focus:ring-2 focus:ring-blue-500/20"
                                                >
                                                    <option value="">Todos</option>
                                                    <option value="Activo">Activo</option>
                                                    <option value="Inactivo">Inactivo</option>
                                                    <option value="Visitante">Visitante</option>
                                                    <option value="Miembro">Miembro</option>
                                                    <option value="Transferido">Transferido</option>
                                                </select>
                                            </div>
                                        </div>
                                    </div>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>

                    {/* Members List */}
                    {loading ? (
                        <div className="text-center py-1.5 animate-pulse font-bold uppercase tracking-wide text-slate-400">Sincronizando base de datos...</div>
                    ) : viewType === 'list' ? (
                        <div className="space-y-1">
                            {filteredMembers.map(m => (
                                <div key={m.id} onClick={() => router.push(`/plataforma/crm/personas/${m.id}`)} className="flex items-center gap-3 p-3 rounded-lg hover:bg-slate-50 dark:hover:bg-white/5 cursor-pointer transition-all">
                                    <div className="w-8 h-8 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center shrink-0 text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))] font-bold text-xs">
                                        {(m.nombre_completo?.charAt(0) || '')}
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <p className="text-sm font-semibold text-slate-900 dark:text-white truncate">{m.nombre_completo || `${m.first_name ?? ''} ${m.last_name ?? ''}`.trim()}</p>
                                        <p className="text-xs text-slate-400">{m.church_role || 'Miembro'}{m.email ? ` · ${m.email}` : ''}</p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : viewType === 'table' ? (
                        <TableView
                            data={[]}
                            idAccessor="id"
                            storageKey="crm_members"
                            columns={[
                                { id: 'nombre_completo', name: 'Nombre Completo', type: 'text' },
                                { id: 'church_role', name: 'Rol', type: 'select', options: roles.map(r => ({ label: r.name, value: r.name, color: r.color })) },
                                { id: 'email', name: 'Email', type: 'email' },
                                { id: 'phone', name: 'Teléfono', type: 'phone' },
                                { id: 'membership_type', name: 'Membresía', type: 'select', options: [{ label: 'Activo', value: 'Activo' }, { label: 'Inactivo', value: 'Inactivo' }] },
                                { id: 'spiritual_health', name: 'Salud Espiritual', type: 'progress' },
                            ]}
                            serverSide={{
                                pageSize: 100,
                                getRows: ({ offset, limit, sortBy, sortDir, search }) => {
                                    const params = new URLSearchParams();
                                    params.set('offset', String(offset));
                                    params.set('limit', String(limit));
                                    if (sortBy) params.set('sort_by', sortBy);
                                    if (sortDir) params.set('sort_dir', sortDir);
                                    if (search) params.set('search', search);
                                    return apiFetch<{ items: any[]; total: number }>(
                                        `/crm/personas/paginated?${params.toString()}`,
                                        { token: token ?? undefined }
                                    ).then(res => ({ items: res.items ?? [], total: res.total ?? 0 }));
                                },
                            }}
                        />
                    ) : (
                        <div className="space-y-6">
                            {(() => {
                                const groups = [
                                    { key: 'Visitante', label: 'Visitantes', desc: 'Personas en proceso de conocer la iglesia', color: 'text-amber-600', bg: 'bg-amber-50 dark:bg-amber-900/20', border: 'border-amber-200 dark:border-amber-800/30' },
                                    { key: 'Activo', label: 'Miembros Activos', desc: 'Miembros activos y en cobertura', color: 'text-emerald-600', bg: 'bg-emerald-50 dark:bg-emerald-900/20', border: 'border-emerald-200 dark:border-emerald-800/30' },
                                    { key: 'Miembro', label: 'Miembros', desc: 'Miembros registrados sin estado específico', color: 'text-blue-600', bg: 'bg-blue-50 dark:bg-blue-900/20', border: 'border-blue-200 dark:border-blue-800/30' },
                                    { key: 'Inactivo', label: 'Inactivos', desc: 'Miembros que han dejado de asistir', color: 'text-slate-600', bg: 'bg-slate-50 dark:bg-slate-800/20', border: 'border-slate-200 dark:border-slate-700/30' },
                                    { key: 'Transferido', label: 'Transferidos', desc: 'Miembros transferidos a otra congregación', color: 'text-purple-600', bg: 'bg-purple-50 dark:bg-purple-900/20', border: 'border-purple-200 dark:border-purple-800/30' },
                                ];
                                const grouped = groups.map(g => ({
                                    ...g,
                                    items: filteredMembers.filter(m => (m.membership_type || '') === g.key),
                                }));
                                const sinMembresia = filteredMembers.filter(m => !m.membership_type);
                                return (
                                    <>
                                        {groups.map(group => {
                                            const groupMembers = filteredMembers.filter(m => (m.membership_type || '') === group.key);
                                            if (groupMembers.length === 0) return null;
                                            return (
                                                <div key={group.key}>
                                                    <div className="flex items-center gap-3 mb-3">
                                                        <div className={clsx("size-8 rounded-lg flex items-center justify-center", group.bg, group.color)}>
                                                            <Users size={16} />
                                                        </div>
                                                        <div>
                                                            <h3 className="text-sm font-bold text-slate-900 dark:text-white">{group.label}</h3>
                                                            <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">{group.desc} · {groupMembers.length} persona{groupMembers.length !== 1 ? 's' : ''}</p>
                                                        </div>
                                                    </div>
                                                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                                                        <AnimatePresence>
                                                            {groupMembers.map(member => (
                                                                <motion.div key={member.id} layout initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.9 }} transition={{ duration: 0.2 }}>
                                                                    <div onClick={() => router.push(`/plataforma/crm/personas/${member.id}`)} className="group p-3 bg-[hsl(var(--surface-1))] dark:bg-[#1e1f21] border border-slate-200 dark:border-white/5 rounded-md hover:border-blue-500/30 hover:shadow-xl hover:shadow-blue-500/10 transition-all cursor-pointer flex items-center justify-between">
                                                                        <div className="flex items-center gap-4">
                                                                            <div className="relative">
                                                                                <div className="size-9 rounded-lg bg-gradient-to-br from-slate-100 to-slate-200 dark:from-white/5 dark:to-white/10 flex items-center justify-center text-slate-600 dark:text-slate-300 font-bold text-sm">
                                                                                    {(member.nombre_completo?.charAt(0) || '')}
                                                                                </div>
                                                                                <div className={clsx("absolute -bottom-1 -right-1 size-4 rounded-full border-2 border-white dark:border-[#1e1f21]", member.spiritual_health > 0.7 ? "bg-emerald-500" : member.spiritual_health > 0.4 ? "bg-amber-500" : "bg-[hsl(var(--destructive))]")} />
                                                                            </div>
                                                                            <div>
                                                                                <h3 className="text-sm font-bold text-slate-900 dark:text-white uppercase truncate max-w-[150px]">{member.nombre_completo || `${member.first_name ?? ''} ${member.last_name ?? ''}`.trim()}</h3>
                                                                                <div className="mt-1 flex items-center gap-2">
                                                                                    <span className={clsx("px-2 py-0.5 rounded-md text-[9px] font-bold uppercase tracking-wide", getRoleColor(member.church_role || ''))}>{member.church_role || 'Miembro'}</span>
                                                                                </div>
                                                                            </div>
                                                                        </div>
                                                                        <div className="size-8 rounded-full bg-slate-50 dark:bg-white/5 flex items-center justify-center text-slate-400 group-hover:bg-blue-50 dark:group-hover:bg-blue-500/20 group-hover:text-[hsl(var(--primary))] transition-all">
                                                                            <ChevronRight size={16} />
                                                                        </div>
                                                                    </div>
                                                                </motion.div>
                                                            ))}
                                                        </AnimatePresence>
                                                    </div>
                                                </div>
                                            );
                                        })}
                                        {sinMembresia.length > 0 && (
                                            <div>
                                                <div className="flex items-center gap-3 mb-3">
                                                    <div className="size-8 rounded-lg flex items-center justify-center bg-slate-50 dark:bg-white/5 text-slate-400">
                                                        <Users size={16} />
                                                    </div>
                                                    <div>
                                                        <h3 className="text-sm font-bold text-slate-900 dark:text-white">Sin Membresía</h3>
                                                        <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Sin tipo de membresía asignado · {sinMembresia.length} persona{sinMembresia.length !== 1 ? 's' : ''}</p>
                                                    </div>
                                                </div>
                                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                                                    <AnimatePresence>
                                                        {sinMembresia.map(member => (
                                                            <motion.div key={member.id} layout initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.9 }} transition={{ duration: 0.2 }}>
                                                                <div onClick={() => router.push(`/plataforma/crm/personas/${member.id}`)} className="group p-3 bg-[hsl(var(--surface-1))] dark:bg-[#1e1f21] border border-slate-200 dark:border-white/5 rounded-md hover:border-blue-500/30 hover:shadow-xl hover:shadow-blue-500/10 transition-all cursor-pointer flex items-center justify-between">
                                                                    <div className="flex items-center gap-4">
                                                                        <div className="relative">
                                                                            <div className="size-9 rounded-lg bg-gradient-to-br from-slate-100 to-slate-200 dark:from-white/5 dark:to-white/10 flex items-center justify-center text-slate-600 dark:text-slate-300 font-bold text-sm">
                                                                                {(member.nombre_completo?.charAt(0) || '')}
                                                                            </div>
                                                                            <div className={clsx("absolute -bottom-1 -right-1 size-4 rounded-full border-2 border-white dark:border-[#1e1f21]", member.spiritual_health > 0.7 ? "bg-emerald-500" : member.spiritual_health > 0.4 ? "bg-amber-500" : "bg-[hsl(var(--destructive))]")} />
                                                                        </div>
                                                                        <div>
                                                                            <h3 className="text-sm font-bold text-slate-900 dark:text-white uppercase truncate max-w-[150px]">{member.nombre_completo || `${member.first_name ?? ''} ${member.last_name ?? ''}`.trim()}</h3>
                                                                            <div className="mt-1 flex items-center gap-2">
                                                                                <span className={clsx("px-2 py-0.5 rounded-md text-[9px] font-bold uppercase tracking-wide", getRoleColor(member.church_role || ''))}>{member.church_role || 'Miembro'}</span>
                                                                            </div>
                                                                        </div>
                                                                    </div>
                                                                    <div className="size-8 rounded-full bg-slate-50 dark:bg-white/5 flex items-center justify-center text-slate-400 group-hover:bg-blue-50 dark:group-hover:bg-blue-500/20 group-hover:text-[hsl(var(--primary))] transition-all">
                                                                        <ChevronRight size={16} />
                                                                    </div>
                                                                </div>
                                                            </motion.div>
                                                        ))}
                                                    </AnimatePresence>
                                                </div>
                                            </div>
                                        )}
                                        {filteredMembers.length === 0 && (
                                            <div className="text-center py-6 font-bold text-slate-400">No se encontraron personas con esos filtros.</div>
                                        )}
                                    </>
                                );
                            })()}
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
                        <button type="button" onClick={() => setIsCreateOpen(false)} className="px-4 py-2 text-[11px] font-bold text-slate-500 hover:text-slate-700">Cancelar</button>
                        <button form="create-member-form" type="submit" disabled={isSaving} className="flex items-center gap-2 rounded-lg bg-[hsl(var(--primary))] px-3 py-2 text-[11px] font-bold uppercase tracking-wide text-white shadow-lg shadow-blue-500/20 transition-all hover:bg-[hsl(var(--primary))] active:scale-95 disabled:opacity-60">
                            {isSaving ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
                            Registrar
                        </button>
                    </>
                }
            >
                <form id="create-member-form" onSubmit={handleCreateMember} className="space-y-2">
                    {/* ── Información Básica (siempre visible) ── */}
                    <div className="rounded-lg overflow-hidden">
                        <div className="px-3 py-2 space-y-2">
                            <div className="grid grid-cols-2 gap-3">
                                <MemberField label="Nombre *" value={newMember.first_name} onChange={um('first_name')} placeholder="Juan" required />
                                <MemberField label="Apellido *" value={newMember.last_name} onChange={um('last_name')} placeholder="Pérez" required />
                            </div>
                            <div className="grid grid-cols-2 gap-3">
                                <MemberField label="Segundo Nombre" value={newMember.second_name} onChange={um('second_name')} placeholder="José" />
                                <MemberField label="Segundo Apellido" value={newMember.second_last_name} onChange={um('second_last_name')} placeholder="García" />
                            </div>
                            <div className="grid grid-cols-2 gap-3">
                                <MemberField label="Correo" type="email" value={newMember.email} onChange={um('email')} placeholder="correo@ejemplo.com" />
                                <MemberField label="Teléfono" value={newMember.phone} onChange={um('phone')} placeholder="+57 300 000 0000" />
                            </div>
                            <div className="grid grid-cols-2 gap-3">
                                <SelectField label="Rol" value={newMember.church_role} onChange={um('church_role')} options={roles.map(r => r.name)} placeholder="Miembro" />
                                <SelectField label="Tipo de Membresía" value={newMember.membership_type} onChange={um('membership_type')} options={MEMBERSHIP_TYPES} placeholder="Seleccionar..." />
                            </div>
                        </div>
                    </div>

                    {/* ── Identificación ── */}
                    <FormSection title="Identificación">
                        <div className="grid grid-cols-2 gap-3">
                            <SelectField label="Tipo de ID" value={newMember.id_type} onChange={um('id_type')} options={ID_TYPES} />
                            <MemberField label="Número de ID" value={newMember.id_number} onChange={um('id_number')} placeholder="1234567890" />
                        </div>
                    </FormSection>

                    {/* ── Información Personal ── */}
                    <FormSection title="Información Personal">
                        <div className="grid grid-cols-2 gap-3">
                            <SelectField label="Sexo" value={newMember.sex} onChange={um('sex')} options={SEX_OPTIONS} />
                            <SelectField label="Estado Civil" value={newMember.marital_status} onChange={um('marital_status')} options={MARITAL_STATUSES} />
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <MemberField label="País de Nacimiento" value={newMember.birth_country} onChange={um('birth_country')} placeholder="Colombia" />
                            <MemberField label="Fecha de Nacimiento" type="date" value={newMember.birthday} onChange={um('birthday')} placeholder="" />
                        </div>
                    </FormSection>

                    {/* ── Contacto y Ubicación ── */}
                    <FormSection title="Contacto y Ubicación">
                        <div className="grid grid-cols-2 gap-3">
                            <MemberField label="Teléfono Fijo" value={newMember.landline_phone} onChange={um('landline_phone')} placeholder="+57 1 000 0000" />
                            <MemberField label="Otro Teléfono" value={newMember.other_phone} onChange={um('other_phone')} placeholder="+57 300 000 0000" />
                        </div>
                        <MemberField label="Dirección" value={newMember.address} onChange={um('address')} placeholder="Cra 1 # 2-3, Barrio..." />
                        <div className="grid grid-cols-2 gap-3">
                            <SelectField label="Tipo de Vivienda" value={newMember.housing_type} onChange={um('housing_type')} options={HOUSING_TYPES} />
                            <MemberField label="Celular" value={newMember.mobile_phone} onChange={um('mobile_phone')} placeholder="+57 300 000 0000" />
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <div className="space-y-2">
                                <label className="text-[10px] font-bold uppercase tracking-wide text-slate-400">Departamento</label>
                                <select value={newMember.colombian_department_id ?? ''} onChange={e => setNewMember(prev => ({ ...prev, colombian_department_id: e.target.value ? Number(e.target.value) : null, city: '' }))} className="w-full rounded-lg border border-slate-200 bg-slate-50 px-4 py-1.5 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-white/10 dark:bg-black/20 dark:text-white">
                                    <option value="">Seleccionar departamento</option>
                                    {departments.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
                                </select>
                            </div>
                            <div className="space-y-2">
                                <label className="text-[10px] font-bold uppercase tracking-wide text-slate-400">Ciudad</label>
                                <select value={newMember.city} onChange={e => setNewMember(prev => ({ ...prev, city: e.target.value }))} disabled={!newMember.colombian_department_id || loadingCities} className="w-full rounded-lg border border-slate-200 bg-slate-50 px-4 py-1.5 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500/20 disabled:opacity-50 disabled:cursor-not-allowed dark:border-white/10 dark:bg-black/20 dark:text-white">
                                    <option value="">{loadingCities ? 'Cargando ciudades...' : 'Seleccionar ciudad'}</option>
                                    {cities.map(c => <option key={c.id} value={c.name}>{c.name}</option>)}
                                </select>
                            </div>
                        </div>
                    </FormSection>

                    {/* ── Educación y Profesión ── */}
                    <FormSection title="Educación y Profesión">
                        <div className="grid grid-cols-2 gap-3">
                            <SelectField label="Nivel Educativo" value={newMember.education_level} onChange={um('education_level')} options={EDUCATION_LEVELS} />
                            <SelectField label="Estado Educativo" value={newMember.education_status} onChange={um('education_status')} options={EDUCATION_STATUSES} />
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <MemberField label="Profesión" value={newMember.profession} onChange={um('profession')} placeholder="Ingeniero, Abogado..." />
                            <MemberField label="Sector Económico" value={newMember.economic_sector} onChange={um('economic_sector')} placeholder="Salud, Educación..." />
                        </div>
                    </FormSection>

                    {/* ── Información Médica ── */}
                    <FormSection title="Información Médica">
                        <div className="grid grid-cols-2 gap-3">
                            <SelectField label="Tipo de Sangre" value={newMember.blood_type} onChange={um('blood_type')} options={BLOOD_TYPES} />
                            <input type="hidden" />
                        </div>
                        <MemberField label="Notas Médicas" value={newMember.medical_notes} onChange={um('medical_notes')} placeholder="Alergias, condiciones..." />
                    </FormSection>

                    {/* ── Iglesia ── */}
                    <FormSection title="Información de Iglesia">
                        <div className="grid grid-cols-2 gap-3">
                            <SelectField label="Tipo de Asistencia" value={newMember.attendance_type} onChange={um('attendance_type')} options={ATTENDANCE_TYPES} />
                            <MemberField label="Grupo" value={newMember.group_name} onChange={um('group_name')} placeholder="Grupo 1, Casa de Paz..." />
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <MemberField label="Campus / Sede" value={newMember.campus} onChange={um('campus')} placeholder="Principal, Norte..." />
                            <MemberField label="Fecha de Ingreso" type="date" value={newMember.church_join_date} onChange={um('church_join_date')} placeholder="" />
                        </div>
                        <MemberField label="Fecha de Bautismo" type="date" value={newMember.baptism_date} onChange={um('baptism_date')} placeholder="" />
                    </FormSection>

                    {/* ── Familiar ── */}
                    <FormSection title="Información Familiar">
                        <div className="grid grid-cols-2 gap-3">
                            <MemberField label="Nombre del Responsable" value={newMember.responsible_adult_name} onChange={um('responsible_adult_name')} placeholder="Nombre completo" />
                            <MemberField label="Contacto del Responsable" value={newMember.responsible_adult_contact} onChange={um('responsible_adult_contact')} placeholder="Teléfono" />
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <MemberField label="Nombre del Acudiente" value={newMember.guardian_name} onChange={um('guardian_name')} placeholder="Nombre completo" />
                            <MemberField label="Contacto del Acudiente" value={newMember.guardian_contact} onChange={um('guardian_contact')} placeholder="Teléfono" />
                        </div>
                    </FormSection>

                    {/* ── Espiritual ── */}
                    <FormSection title="Información Espiritual">
                        <MemberField label="Talentos y Habilidades" value={newMember.talents} onChange={um('talents')} placeholder="Canto, enseñanza, liderazgo..." />
                        <MemberField label="Dones Espirituales" value={newMember.spiritual_gifts} onChange={um('spiritual_gifts')} placeholder="Profecía, enseñanza, servicio..." />
                        <MemberField label="Notas Pastorales" value={newMember.pastoral_notes} onChange={um('pastoral_notes')} placeholder="Observaciones pastorales..." />
                        <div className="grid grid-cols-2 gap-3">
                            <MemberField label="Última Asistencia a Grupo" type="date" value={newMember.last_group_attendance} onChange={um('last_group_attendance')} placeholder="" />
                            <MemberField label="Última Asistencia a Reunión" type="date" value={newMember.last_meeting_attendance} onChange={um('last_meeting_attendance')} placeholder="" />
                        </div>
                    </FormSection>

                    {/* ── Registro ── */}
                    <FormSection title="Información de Registro">
                        <MemberField label="Motivo de Registro" value={newMember.registration_reason} onChange={um('registration_reason')} placeholder="Conversión, transferencia..." />
                        <MemberField label="Motivo de Baja" value={newMember.unregistration_reason} onChange={um('unregistration_reason')} placeholder="Si aplica..." />
                        <div className="grid grid-cols-2 gap-3">
                            <MemberField label="Fecha de Registro" type="date" value={newMember.registration_date} onChange={um('registration_date')} placeholder="" />
                            <MemberField label="Fecha de Baja" type="date" value={newMember.unregistration_date} onChange={um('unregistration_date')} placeholder="" />
                        </div>
                        <MemberField label="Información Opcional" value={newMember.optional_info} onChange={um('optional_info')} placeholder="Notas adicionales..." />
                    </FormSection>
                </form>
            </WorkspaceDrawer>
        </CrmShell>
    );
}
