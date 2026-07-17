"use client";

import CrmShell from '@/components/crm/CrmShell';
import TableView from '@/components/ui/TableView';
import ViewSwitcher from '@/components/ViewSwitcher';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';
import { useAuth } from '@/context/AuthContext';
import { useCrmAccess } from '@/hooks/useCrmAccess';
import { FULL_VIEWS,useViewType } from '@/hooks/useViewType';
import clsx from 'clsx';
import { AnimatePresence,motion } from 'framer-motion';
import {
BookOpen,
ChevronRight,
Fingerprint,
LayoutDashboard,
Loader2,
MapPin,
Plus,
Search,
Send,
SlidersHorizontal,
Users,
VenetianMask,
X,
} from 'lucide-react'
import { useRouter } from 'next/navigation';
import React,{ useCallback, useEffect,useMemo,useState } from 'react';
import { toast } from 'sonner';
import {
  Department,
  City,
  PersonaFormData,
  ID_TYPES,
  MARITAL_STATUSES,
  SEX_OPTIONS,
  EDUCATION_LEVELS,
  EDUCATION_STATUSES,
  BLOOD_TYPES,
  HOUSING_TYPES,
  PARTICIPATION_TYPES,
  ATTENDANCE_TYPES,
  INITIAL_PERSONA,
} from '@/types/crm';
import { FormSection, SelectField, PersonaField } from '@/components/crm/ui';
import { extractErrorMessage, apiFetch } from '@/lib/http';

interface PersonasPageResponse {
    items: any[];
    total: number;
    skip: number;
    limit: number;
    available_groups: string[];
}

const PERSONAS_PAGE_SIZE_OPTIONS = [25, 50, 100, 200] as const;
const DEFAULT_PERSONAS_PAGE_SIZE = 50;

function buildPaginationItems(currentPage: number, totalPages: number) {
    if (totalPages <= 7) {
        return Array.from({ length: totalPages }, (_, index) => index + 1);
    }

    const pages: Array<number | 'ellipsis'> = [1];
    const left = Math.max(2, currentPage - 1);
    const right = Math.min(totalPages - 1, currentPage + 1);

    if (left > 2) pages.push('ellipsis');
    for (let page = left; page <= right; page += 1) {
        pages.push(page);
    }
    if (right < totalPages - 1) pages.push('ellipsis');
    pages.push(totalPages);

    return pages;
}

// ─── Main Component ───────────────────────────────────────────────────────────

export default function PersonasPage() {
    const { token, loading: authLoading } = useAuth();
    const { canEditCrm } = useCrmAccess();
    const router = useRouter();
    const { viewType, setViewType } = useViewType('crm_personas', 'grid');
    const [personasPage, setPersonasPage] = useState<PersonasPageResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [personasError, setPersonasError] = useState<string | null>(null);
    const [page, setPage] = useState(1);
    const [pageSize, setPageSize] = useState(DEFAULT_PERSONAS_PAGE_SIZE);

    const [roles, setRoles] = useState<any[]>([]);
    const [isCreateOpen, setIsCreateOpen] = useState(false);
    const [isSaving, setIsSaving] = useState(false);
    const [newPersona, setNewPersona] = useState<PersonaFormData>({ ...INITIAL_PERSONA });
    const [departments, setDepartments] = useState<Department[]>([]);
    const [cities, setCities] = useState<City[]>([]);
    const [loadingCities, setLoadingCities] = useState(false);

    const [query, setQuery] = useState('');
    const [roleFilter, setRoleFilter] = useState('Todos');
    const [idTypeFilter, setIdTypeFilter] = useState('');
    const [sexFilter, setSexFilter] = useState('');
    const [groupFilter, setGroupFilter] = useState('');
    const [participationFilter, setParticipationFilter] = useState('');
    const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
    const activeFilterCount = useMemo(
        () => [idTypeFilter, sexFilter, groupFilter, participationFilter].filter(Boolean).length
            + (roleFilter !== 'Todos' ? 1 : 0),
        [idTypeFilter, sexFilter, groupFilter, participationFilter, roleFilter]
    );

    const loadPersonas = useCallback(async () => {
        if (!token) {
            setLoading(false);
            return;
        }

        setLoading(true);
        setPersonasError(null);

        try {
            const params = new URLSearchParams({
                skip: String((page - 1) * pageSize),
                limit: String(pageSize),
                sort_by: 'nombre_completo',
                sort_dir: 'asc',
            });
            if (query.trim()) params.set('search', query.trim());
            if (roleFilter !== 'Todos') params.set('role', roleFilter);
            if (idTypeFilter) params.set('id_type', idTypeFilter);
            if (sexFilter) params.set('sex', sexFilter);
            if (groupFilter) params.set('group_name', groupFilter);
            if (participationFilter) params.set('participation_type', participationFilter);

            const personasData = await apiFetch<PersonasPageResponse>(`/crm/personas/page?${params.toString()}`, {
                token,
                cache: 'no-store',
            });
            setPersonasPage(personasData);
        } catch (err) {
            setPersonasPage(null);

            const message = extractErrorMessage(err, 'No se pudo cargar la lista de personas');
            setPersonasError(message);
            toast.error(message);
        } finally {
            setLoading(false);
        }
    }, [token, page, pageSize, query, roleFilter, idTypeFilter, sexFilter, groupFilter, participationFilter]);

    useEffect(() => {
        loadPersonas();
    }, [loadPersonas]);

    useEffect(() => {
        if (!token) return;
        apiFetch<any[]>('/crm/roles', { token, cache: 'no-store' })
            .then(setRoles)
            .catch(() => setRoles([]));

        apiFetch<Department[]>('/crm/colombian-departments', { token, cache: 'no-store' })
            .then(setDepartments)
            .catch(() => setDepartments([]));
    }, [token]);

    useEffect(() => {
        setPage(1);
    }, [query, roleFilter, idTypeFilter, sexFilter, groupFilter, participationFilter]);

    useEffect(() => {
        if (!token || !newPersona.colombian_department_id) {
            setCities([]);
            return;
        }
        setLoadingCities(true);
        apiFetch<City[]>(`/crm/colombian-departments/${newPersona.colombian_department_id}/cities`, { token })
            .then(setCities)
            .catch(() => setCities([]))
            .finally(() => setLoadingCities(false));
    }, [token, newPersona.colombian_department_id]);

    const getRoleColor = (roleName: string) => {
        const r = roles.find(x => roleName?.toLowerCase().includes(x.name.toLowerCase()));
        return r ? r.color : 'text-[hsl(var(--text-secondary))] bg-[hsl(var(--surface-2))] dark:bg-white/10 dark:text-[hsl(var(--text-secondary))]';
    };

    const personas = personasPage?.items ?? [];
    const totalPersonas = personasPage?.total ?? 0;
    const totalPages = Math.max(1, Math.ceil(totalPersonas / pageSize));
    const pageStart = totalPersonas === 0 ? 0 : ((page - 1) * pageSize) + 1;
    const pageEnd = Math.min(totalPersonas, page * pageSize);
    const uniqueGroups = personasPage?.available_groups ?? [];
    const paginationItems = useMemo(() => buildPaginationItems(page, totalPages), [page, totalPages]);

    useEffect(() => {
        if (page > totalPages) {
            setPage(totalPages);
        }
    }, [page, totalPages]);

    if (!authLoading && !token) {
        return (
            <CrmShell
                breadcrumbs={[
                    { label: 'CRM', icon: LayoutDashboard, href: '/plataforma/crm' },
                    { label: 'Personas', icon: LayoutDashboard },
                ]}
            >
                <main className="flex-1 overflow-y-auto scrollbar-thin p-4">
                    <div className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-[#15171c] p-4 text-center">
                        <p className="text-[11px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                            La sesión no está disponible para cargar personas.
                        </p>
                    </div>
                </main>
            </CrmShell>
        );
    }

    if (authLoading && !token) {
        return (
            <CrmShell
                breadcrumbs={[
                    { label: 'CRM', icon: LayoutDashboard, href: '/plataforma/crm' },
                    { label: 'Personas', icon: LayoutDashboard },
                ]}
            >
                <main className="flex-1 overflow-y-auto scrollbar-thin p-4">
                    <div className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-[#15171c] p-4 text-center">
                        <p className="text-[11px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] animate-pulse">
                            Verificando sesión y cargando personas...
                        </p>
                    </div>
                </main>
            </CrmShell>
        );
    }

    const um = (key: keyof PersonaFormData) => (value: string) => setNewPersona(prev => ({ ...prev, [key]: value }));

    const handleCreatePersona = async (event: React.FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        if (!token || !newPersona.first_name.trim() || !newPersona.last_name.trim()) return;

        setIsSaving(true);
        try {
            const body: any = { ...newPersona };
            if (!body.colombian_department_id) body.colombian_department_id = null;
            // Convert empty date strings to null
            ['birthday','church_join_date','baptism_date','registration_date','unregistration_date','last_group_attendance','last_meeting_attendance'].forEach(k => {
                if (!body[k]) body[k] = null;
            });

            await apiFetch<any>('/crm/personas/', {
                method: 'POST',
                token,
                body,
            });
            setNewPersona({ ...INITIAL_PERSONA });
            setIsCreateOpen(false);
            await loadPersonas();
            toast.success('Persona registrada');
        } catch {
            toast.error('No se pudo registrar la persona');
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
                {/* Header */}
                <div className="px-3 py-2 border-b border-[hsl(var(--border))] dark:border-white/5">
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                        <div>
                            <h1 className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tight">Personas</h1>
                            <p className="text-xs text-[hsl(var(--text-secondary))] font-medium">Directorio completo de la comunidad</p>
                        </div>
                        {canEditCrm && (
                            <button
                                onClick={() => setIsCreateOpen(true)}
                                className="flex items-center gap-2 px-4 py-1.5 bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] rounded-lg text-[11px] font-bold uppercase tracking-wide hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 transition-all shrink-0"
                            >
                                <Plus size={16} /> Nueva Persona
                            </button>
                        )}
                    </div>
                </div>

                <div className="p-4 lg:p-4 space-y-4 w-full">
                    {personasError && (
                        <div className="rounded-lg border border-amber-300/60 bg-amber-50 dark:bg-amber-500/10 dark:border-amber-500/30 p-3 flex flex-col md:flex-row md:items-center md:justify-between gap-3">
                            <div className="min-w-0">
                                <p className="text-[11px] font-bold uppercase tracking-wide text-amber-800 dark:text-amber-200">
                                    No se pudo cargar el directorio de personas
                                </p>
                                <p className="text-sm text-amber-900/80 dark:text-amber-100/80 mt-1 break-words">
                                    {personasError}
                                </p>
                            </div>
                            <button
                                onClick={() => loadPersonas()}
                                className="shrink-0 px-3 py-2 rounded-lg bg-[hsl(var(--primary))] text-white text-[10px] font-bold uppercase tracking-wide shadow-lg shadow-blue-500/20 hover:opacity-90 transition-all"
                            >
                                Reintentar
                            </button>
                        </div>
                    )}

                    {/* Filters Toolbar */}
                    <div className="sticky top-0 z-10 bg-[hsl(var(--surface-1))]/80 dark:bg-[#121212]/80 backdrop-blur-xl pt-2 space-y-2">
                        {/* Search + Filter Toggle Row */}
                        <div className="flex flex-col md:flex-row gap-2">
                            <div className="relative flex-1">
                                <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]" size={18} />
                                <input
                                    value={query}
                                    onChange={e => setQuery(e.target.value)}
                                    placeholder="Buscar por nombre, documento, teléfono, email o ministerio..."
                                    className="w-full bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg py-1.5 pl-12 pr-4 text-sm font-medium outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-all shadow-sm"
                                />
                            </div>
                            <div className="flex items-center gap-2 shrink-0">
                                <button
                                    onClick={() => setShowAdvancedFilters(!showAdvancedFilters)}
                                    className={clsx(
                                        "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-bold uppercase tracking-wide transition-all shrink-0 border",
                                        showAdvancedFilters || activeFilterCount > 0
                                            ? "bg-ccf-blue text-white border-ccf-blue shadow-md"
                                            : "bg-[hsl(var(--surface-1))] dark:bg-white/5 border-[hsl(var(--border))] dark:border-white/10 text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10"
                                    )}
                                >
                                    <SlidersHorizontal size={14} />
                                    Filtros
                                    {activeFilterCount > 0 && (
                                        <span className="ml-1 size-4 rounded-full bg-[hsl(var(--bg-primary))] text-ccf-blue text-[9px] font-bold flex items-center justify-center">
                                            {activeFilterCount}
                                        </span>
                                    )}
                                </button>
                                <ViewSwitcher viewType={viewType} setViewType={setViewType} availableViews={FULL_VIEWS} />
                            </div>
                        </div>

                        {/* Role Chips Row */}
                        <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-none snap-x">
                            <button onClick={() => setRoleFilter('Todos')} className={clsx("px-3 py-1 rounded-lg text-[10px] font-bold uppercase tracking-wide whitespace-nowrap transition-all shrink-0 snap-start", roleFilter === 'Todos' ? "bg-[hsl(var(--surface-2))] text-white dark:bg-[hsl(var(--bg-primary))] dark:text-[hsl(var(--text-primary))] shadow-md" : "bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10")}>Todos</button>
                            {roles.map(role => (
                                <button key={role.id} onClick={() => setRoleFilter(role.name)} className={clsx("px-3 py-1 rounded-lg text-[10px] font-bold uppercase tracking-wide whitespace-nowrap transition-all shrink-0 snap-start", roleFilter === role.name ? "bg-[hsl(var(--surface-2))] text-white dark:bg-[hsl(var(--bg-primary))] dark:text-[hsl(var(--text-primary))] shadow-md" : "bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10")}>{role.name}</button>
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
                                    <div className="bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg p-3">
                                        <div className="flex items-center justify-between mb-2">
                                            <h4 className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Filtros Avanzados</h4>
                                            <button
                                                onClick={() => {
                                                    setIdTypeFilter('');
                                                    setSexFilter('');
                                                    setGroupFilter('');
                                                    setParticipationFilter('');
                                                    setRoleFilter('Todos');
                                                }}
                                                className="flex items-center gap-1 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--destructive))] hover:text-[hsl(var(--destructive))] transition-colors"
                                            >
                                                <X size={12} /> Limpiar
                                            </button>
                                        </div>
                                        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                                            {/* Tipo de Identificación */}
                                            <div className="space-y-1">
                                                <label className="flex items-center gap-1 text-[9px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                                                    <Fingerprint size={11} /> Tipo ID
                                                </label>
                                                <select
                                                    value={idTypeFilter}
                                                    onChange={e => setIdTypeFilter(e.target.value)}
                                                    className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-black/20 px-2.5 py-1 text-[11px] font-semibold outline-none focus:ring-2 focus:ring-blue-500/20"
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
                                                <label className="flex items-center gap-1 text-[9px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                                                    <VenetianMask size={11} /> Sexo
                                                </label>
                                                <select
                                                    value={sexFilter}
                                                    onChange={e => setSexFilter(e.target.value)}
                                                    className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-black/20 px-2.5 py-1 text-[11px] font-semibold outline-none focus:ring-2 focus:ring-blue-500/20"
                                                >
                                                    <option value="">Todos</option>
                                                    <option value="M">Masculino</option>
                                                    <option value="F">Femenino</option>
                                                </select>
                                            </div>

                                            {/* Grupo */}
                                            <div className="space-y-1">
                                                <label className="flex items-center gap-1 text-[9px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                                                    <MapPin size={11} /> Grupo
                                                </label>
                                                <select
                                                    value={groupFilter}
                                                    onChange={e => setGroupFilter(e.target.value)}
                                                    className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-black/20 px-2.5 py-1 text-[11px] font-semibold outline-none focus:ring-2 focus:ring-blue-500/20"
                                                >
                                                    <option value="">Todos</option>
                                                    {uniqueGroups.map(g => (
                                                        <option key={g} value={g}>{g}</option>
                                                    ))}
                                                </select>
                                            </div>

                                            {/* Tipo Participación */}
                                            <div className="space-y-1">
                                                <label className="flex items-center gap-1 text-[9px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                                                    <BookOpen size={11} /> Participación
                                                </label>
                                                <select
                                                    value={participationFilter}
                                                    onChange={e => setParticipationFilter(e.target.value)}
                                                    className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-black/20 px-2.5 py-1 text-[11px] font-semibold outline-none focus:ring-2 focus:ring-blue-500/20"
                                                >
                                                    <option value="">Todos</option>
                                                    <option value="Activo">Activo</option>
                                                    <option value="Inactivo">Inactivo</option>
                                                    <option value="Visitante">Visitante</option>
                                                    <option value="Persona">Persona</option>
                                                    <option value="Transferido">Transferido</option>
                                                </select>
                                            </div>
                                        </div>
                                    </div>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>

                    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/5 px-3 py-2">
                        <div className="flex flex-col gap-1">
                            <div className="text-[11px] font-medium text-[hsl(var(--text-secondary))]">
                                {totalPersonas === 0
                                    ? 'No hay personas para mostrar en esta consulta.'
                                    : `Mostrando ${pageStart}-${pageEnd} de ${totalPersonas} personas`}
                            </div>
                            <label className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                                Registros por página
                                <select
                                    value={pageSize}
                                    onChange={(event) => {
                                        setPage(1);
                                        setPageSize(Number(event.target.value));
                                    }}
                                    className="rounded-md border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-white/5 px-2 py-1 text-[11px] font-bold text-[hsl(var(--text-primary))] outline-none focus:ring-2 focus:ring-blue-500/20"
                                >
                                    {PERSONAS_PAGE_SIZE_OPTIONS.map((option) => (
                                        <option key={option} value={option}>{option}</option>
                                    ))}
                                </select>
                            </label>
                        </div>
                        <div className="flex flex-wrap items-center gap-2">
                            <button
                                type="button"
                                onClick={() => setPage(1)}
                                disabled={loading || page <= 1}
                                className="px-3 py-1.5 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 disabled:opacity-50"
                            >
                                Primera
                            </button>
                            <button
                                type="button"
                                onClick={() => setPage(p => Math.max(1, p - 1))}
                                disabled={loading || page <= 1}
                                className="px-3 py-1.5 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 disabled:opacity-50"
                            >
                                Anterior
                            </button>
                            <div className="flex items-center gap-1">
                                {paginationItems.map((item, index) => (
                                    item === 'ellipsis' ? (
                                        <span key={`ellipsis-${index}`} className="px-2 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">…</span>
                                    ) : (
                                        <button
                                            key={item}
                                            type="button"
                                            onClick={() => setPage(item)}
                                            disabled={loading}
                                            className={clsx(
                                                "min-w-8 px-2.5 py-1.5 rounded-lg border text-[10px] font-bold uppercase tracking-wide transition-all",
                                                item === page
                                                    ? "bg-[hsl(var(--primary))] text-white border-[hsl(var(--primary))] shadow-lg shadow-blue-500/20"
                                                    : "border-[hsl(var(--border))] dark:border-white/10 text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10"
                                            )}
                                        >
                                            {item}
                                        </button>
                                    )
                                ))}
                            </div>
                            <button
                                type="button"
                                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                                disabled={loading || page >= totalPages}
                                className="px-3 py-1.5 rounded-lg bg-[hsl(var(--primary))] text-white text-[10px] font-bold uppercase tracking-wide shadow-lg shadow-blue-500/20 hover:opacity-90 disabled:opacity-50"
                            >
                                Siguiente
                            </button>
                            <button
                                type="button"
                                onClick={() => setPage(totalPages)}
                                disabled={loading || page >= totalPages}
                                className="px-3 py-1.5 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 disabled:opacity-50"
                            >
                                Última
                            </button>
                            <span className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                                Página {page} de {totalPages}
                            </span>
                        </div>
                    </div>

                    {/* Personas List */}
                    {loading ? (
                        <div className="flex items-center justify-center py-1.5 gap-3">
                            <Loader2 size={18} className="animate-spin text-[hsl(var(--primary))]" />
                            <span className="animate-pulse font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] text-xs">Sincronizando base de datos...</span>
                        </div>
                    ) : viewType === 'list' ? (
                        <div className="space-y-1">
                            {personas.map(m => (
                                <div key={m.id} onClick={() => router.push(`/plataforma/crm/personas/${m.id}`)} className="flex items-center gap-3 p-3 rounded-lg hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 cursor-pointer transition-all">
                                    <div className="w-8 h-8 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center shrink-0 text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))] font-bold text-xs">
                                        {(m.nombre_completo?.charAt(0) || '')}
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <p className="text-sm font-semibold text-[hsl(var(--text-primary))] dark:text-white truncate">{m.nombre_completo || `${m.first_name ?? ''} ${m.last_name ?? ''}`.trim()}</p>
                                        <p className="text-xs text-[hsl(var(--text-secondary))]">{m.church_role || 'Persona'}{m.email ? ` · ${m.email}` : ''}</p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : viewType === 'table' ? (
                        <TableView
                            data={personas}
                            idAccessor="id"
                            storageKey="crm_personas"
                            enableFilters={false}
                            columns={[
                                { id: 'nombre_completo', name: 'Nombre Completo', type: 'text' },
                                { id: 'church_role', name: 'Rol', type: 'select', options: roles.map(r => ({ label: r.name, value: r.name, color: r.color })) },
                                { id: 'email', name: 'Email', type: 'email' },
                                { id: 'phone', name: 'Teléfono', type: 'phone' },
                                { id: 'participation_type', name: 'Participación', type: 'select', options: [{ label: 'Activo', value: 'Activo' }, { label: 'Inactivo', value: 'Inactivo' }] },
                                { id: 'spiritual_health', name: 'Salud Espiritual', type: 'progress' },
                            ]}
                        />
                    ) : (
                        <div className="space-y-6">
                            {(() => {
                                const FIXED_GROUPS = [
                                    { key: 'Activo', label: 'Personas Activos', desc: 'Personas activos y en cobertura', color: 'text-emerald-600', bg: 'bg-emerald-50 dark:bg-emerald-900/20', border: 'border-emerald-200 dark:border-emerald-800/30' },
                                    { key: 'Persona', label: 'Personas', desc: 'Personas registrados sin estado específico', color: 'text-[hsl(var(--primary))]', bg: 'bg-blue-50 dark:bg-blue-900/20', border: 'border-blue-200 dark:border-blue-800/30' },
                                    { key: 'Inactivo', label: 'Inactivos', desc: 'Personas que han dejado de asistir', color: 'text-[hsl(var(--text-secondary))]', bg: 'bg-[hsl(var(--surface-1))] dark:bg-[hsl(var(--surface-2))]/20', border: 'border-[hsl(var(--border))] dark:border-[hsl(var(--border))]/30' },
                                    { key: 'Transferido', label: 'Transferidos', desc: 'Personas transferidos a otra congregación', color: 'text-[hsl(var(--primary))]', bg: 'bg-blue-50 dark:bg-blue-900/20', border: 'border-blue-200 dark:border-blue-800/30' },
                                ];

                                // Collect unique group_name values from filtered Visitante personas
                                const visitantes = personas.filter(m => (m.participation_type || '') === 'Visitante');
                                const visitantGroups = [...new Set(visitantes.map((m: any) => m.group_name).filter(Boolean))].sort();
                                const visitantesSinGrupo = visitantes.filter(m => !m.group_name);

                                const sinMembresia = personas.filter(m => !m.participation_type);
                                const gruposFijosConPersonas = FIXED_GROUPS.map(group => ({
                                    ...group,
                                    personas: personas.filter(m => (m.participation_type || '') === group.key),
                                }));

                                const renderedIds = new Set<string>();
                                visitantes.forEach(persona => renderedIds.add(String(persona.id)));
                                gruposFijosConPersonas.forEach(group => {
                                    group.personas.forEach(persona => renderedIds.add(String(persona.id)));
                                });
                                sinMembresia.forEach(persona => renderedIds.add(String(persona.id)));
                                const otrasPersonas = personas.filter(persona => !renderedIds.has(String(persona.id)));

                                function renderPersonaCard(persona: any) {
                                    return (
                                        <motion.div key={persona.id} layout initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.9 }} transition={{ duration: 0.2 }}>
                                            <div onClick={() => router.push(`/plataforma/crm/personas/${persona.id}`)} className="group p-3 bg-[hsl(var(--surface-1))] dark:bg-[#1e1f21] border border-[hsl(var(--border))] dark:border-white/5 rounded-md hover:border-blue-500/30 hover:shadow-xl hover:shadow-blue-500/10 transition-all cursor-pointer flex items-center justify-between">
                                                <div className="flex items-center gap-4">
                                                    <div className="relative">
                                                        <div className="size-9 rounded-lg bg-gradient-to-br from-[hsl(var(--surface-2))] to-[hsl(var(--surface-2))] dark:from-white/5 dark:to-white/10 flex items-center justify-center text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] font-bold text-sm">
                                                            {(persona.nombre_completo?.charAt(0) || '')}
                                                        </div>
                                                        <div className={clsx("absolute -bottom-1 -right-1 size-4 rounded-full border-2 border-white dark:border-[#1e1f21]", persona.spiritual_health > 0.7 ? "bg-emerald-500" : persona.spiritual_health > 0.4 ? "bg-amber-500" : "bg-[hsl(var(--destructive))]")} />
                                                    </div>
                                                    <div>
                                                        <h3 className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-white uppercase truncate max-w-[150px]">{persona.nombre_completo || `${persona.first_name ?? ''} ${persona.last_name ?? ''}`.trim()}</h3>
                                                        <div className="mt-1 flex items-center gap-2">
                                                            <span className={clsx("px-2 py-0.5 rounded-md text-[9px] font-bold uppercase tracking-wide", getRoleColor(persona.church_role || ''))}>{persona.church_role || 'Persona'}</span>
                                                        </div>
                                                    </div>
                                                </div>
                                                <div className="size-8 rounded-full bg-[hsl(var(--surface-1))] dark:bg-white/5 flex items-center justify-center text-[hsl(var(--text-secondary))] group-hover:bg-blue-50 dark:group-hover:bg-blue-500/20 group-hover:text-[hsl(var(--primary))] transition-all">
                                                    <ChevronRight size={16} />
                                                </div>
                                            </div>
                                        </motion.div>
                                    );
                                }

                                function renderGroupPersonaCards(personas: any[]) {
                                    return (
                                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                                            <AnimatePresence>
                                                {personas.map(renderPersonaCard)}
                                            </AnimatePresence>
                                        </div>
                                    );
                                }

                                function renderSectionHeader(label: string, desc: string, color: string, bg: string, count: number) {
                                    return (
                                        <div className="flex items-center gap-3 mb-3">
                                            <div className={clsx("size-8 rounded-lg flex items-center justify-center", bg, color)}>
                                                <Users size={16} />
                                            </div>
                                            <div>
                                                <h3 className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-white">{label}</h3>
                                                <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{desc} · {count} persona{count !== 1 ? 's' : ''}</p>
                                            </div>
                                        </div>
                                    );
                                }

                                return (
                                    <>
                                        {/* Visitantes — subagrupados por estrategia evangelística (group_name) */}
                                        {visitantes.length > 0 && (
                                            <div key="Visitantes">
                                                {renderSectionHeader('Visitantes', 'Personas en proceso de conocer la iglesia', 'text-amber-600', 'bg-amber-50 dark:bg-amber-900/20', visitantes.length)}
                                                <div className="space-y-5 pl-4 border-l-2 border-amber-200 dark:border-amber-800/30">
                                                    {visitantGroups.map(g => {
                                                        const gm = visitantes.filter(m => m.group_name === g);
                                                        return (
                                                            <div key={g}>
                                                                <h4 className="text-[10px] font-bold uppercase tracking-wide text-amber-600 dark:text-amber-400 mb-2">▸ {g} ({gm.length})</h4>
                                                                {renderGroupPersonaCards(gm)}
                                                            </div>
                                                        );
                                                    })}
                                                    {visitantesSinGrupo.length > 0 && (
                                                        <div>
                                                            <h4 className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-2">▸ Sin Grupo ({visitantesSinGrupo.length})</h4>
                                                            {renderGroupPersonaCards(visitantesSinGrupo)}
                                                        </div>
                                                    )}
                                                </div>
                                            </div>
                                        )}

                                        {/* Grupos fijos: Activo, Persona, Inactivo, Transferido */}
                                        {gruposFijosConPersonas.map(group => {
                                            if (group.personas.length === 0) return null;
                                            return (
                                                <div key={group.key}>
                                                    {renderSectionHeader(group.label, group.desc, group.color, group.bg, group.personas.length)}
                                                    {renderGroupPersonaCards(group.personas)}
                                                </div>
                                            );
                                        })}

                                        {/* Sin Participación */}
                                        {sinMembresia.length > 0 && (
                                            <div>
                                                {renderSectionHeader('Sin Participación', 'Sin tipo de participación asignado', 'text-[hsl(var(--text-secondary))]', 'bg-[hsl(var(--surface-1))] dark:bg-white/5', sinMembresia.length)}
                                                {renderGroupPersonaCards(sinMembresia)}
                                            </div>
                                        )}

                                        {/* Fallback estructural: personas que no encajan en ningún bucket visible */}
                                        {otrasPersonas.length > 0 && (
                                            <div>
                                                {renderSectionHeader(
                                                    'Sin Clasificación',
                                                    'Personas con un estado de participación no cubierto por la vista actual',
                                                    'text-[hsl(var(--primary))]',
                                                    'bg-blue-50 dark:bg-blue-900/20',
                                                    otrasPersonas.length
                                                )}
                                                {renderGroupPersonaCards(otrasPersonas)}
                                            </div>
                                        )}

                                        {/* Empty state */}
                                        {!personasError && personas.length === 0 && (
                                            <div className="text-center py-6 font-bold text-[hsl(var(--text-secondary))]">No se encontraron personas con esos filtros.</div>
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
                title="Nueva Persona"
                subtitle="Registrar perfil en la base ministerial"
                actions={
                    <>
                        <button type="button" onClick={() => setIsCreateOpen(false)} className="px-4 py-2 text-[11px] font-bold text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]">Cancelar</button>
                        <button form="create-persona-form" type="submit" disabled={isSaving} className="flex items-center gap-2 rounded-lg bg-[hsl(var(--primary))] px-3 py-2 text-[11px] font-bold uppercase tracking-wide text-white shadow-lg shadow-blue-500/20 transition-all hover:bg-[hsl(var(--primary))] active:scale-95 disabled:opacity-60">
                            {isSaving ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
                            Registrar
                        </button>
                    </>
                }
            >
                <form id="create-persona-form" onSubmit={handleCreatePersona} className="space-y-2">
                    {/* ── Información Básica (siempre visible) ── */}
                    <div className="rounded-lg overflow-hidden">
                        <div className="px-3 py-2 space-y-2">
                            <div className="grid grid-cols-2 gap-3">
                                <PersonaField label="Nombre *" value={newPersona.first_name} onChange={um('first_name')} placeholder="Juan" required />
                                <PersonaField label="Apellido *" value={newPersona.last_name} onChange={um('last_name')} placeholder="Pérez" required />
                            </div>
                            <div className="grid grid-cols-2 gap-3">
                                <PersonaField label="Segundo Nombre" value={newPersona.second_name} onChange={um('second_name')} placeholder="José" />
                                <PersonaField label="Segundo Apellido" value={newPersona.second_last_name} onChange={um('second_last_name')} placeholder="García" />
                            </div>
                            <div className="grid grid-cols-2 gap-3">
                                <PersonaField label="Correo" type="email" value={newPersona.email} onChange={um('email')} placeholder="correo@ejemplo.com" />
                                <PersonaField label="Teléfono" value={newPersona.phone} onChange={um('phone')} placeholder="+57 300 000 0000" />
                            </div>
                            <div className="grid grid-cols-2 gap-3">
                                <SelectField label="Rol" value={newPersona.church_role} onChange={um('church_role')} options={roles.map(r => r.name)} placeholder="Persona" />
                                <SelectField label="Tipo de Participación" value={newPersona.participation_type} onChange={um('participation_type')} options={PARTICIPATION_TYPES} placeholder="Seleccionar..." />
                            </div>
                        </div>
                    </div>

                    {/* ── Identificación ── */}
                    <FormSection title="Identificación">
                        <div className="grid grid-cols-2 gap-3">
                            <SelectField label="Tipo de ID" value={newPersona.id_type} onChange={um('id_type')} options={ID_TYPES} />
                            <PersonaField label="Número de ID" value={newPersona.id_number} onChange={um('id_number')} placeholder="1234567890" />
                        </div>
                    </FormSection>

                    {/* ── Información Personal ── */}
                    <FormSection title="Información Personal">
                        <div className="grid grid-cols-2 gap-3">
                            <SelectField label="Sexo" value={newPersona.sex} onChange={um('sex')} options={SEX_OPTIONS} />
                            <SelectField label="Estado Civil" value={newPersona.marital_status} onChange={um('marital_status')} options={MARITAL_STATUSES} />
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <PersonaField label="País de Nacimiento" value={newPersona.birth_country} onChange={um('birth_country')} placeholder="Colombia" />
                            <PersonaField label="Fecha de Nacimiento" type="date" value={newPersona.birthday} onChange={um('birthday')} placeholder="" />
                        </div>
                    </FormSection>

                    {/* ── Contacto y Ubicación ── */}
                    <FormSection title="Contacto y Ubicación">
                        <div className="grid grid-cols-2 gap-3">
                            <PersonaField label="Teléfono Fijo" value={newPersona.landline_phone} onChange={um('landline_phone')} placeholder="+57 1 000 0000" />
                            <PersonaField label="Otro Teléfono" value={newPersona.other_phone} onChange={um('other_phone')} placeholder="+57 300 000 0000" />
                        </div>
                        <PersonaField label="Dirección" value={newPersona.address} onChange={um('address')} placeholder="Cra 1 # 2-3, Barrio..." />
                        <div className="grid grid-cols-2 gap-3">
                            <SelectField label="Tipo de Vivienda" value={newPersona.housing_type} onChange={um('housing_type')} options={HOUSING_TYPES} />
                            <PersonaField label="Celular" value={newPersona.mobile_phone} onChange={um('mobile_phone')} placeholder="+57 300 000 0000" />
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <div className="space-y-2">
                                <label className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Departamento</label>
                                <select value={newPersona.colombian_department_id ?? ''} onChange={e => setNewPersona(prev => ({ ...prev, colombian_department_id: e.target.value ? Number(e.target.value) : null, city: '' }))} className="w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-4 py-1.5 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-white/10 dark:bg-black/20 dark:text-white">
                                    <option value="">Seleccionar departamento</option>
                                    {departments.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
                                </select>
                            </div>
                            <div className="space-y-2">
                                <label className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Ciudad</label>
                                <select value={newPersona.city} onChange={e => setNewPersona(prev => ({ ...prev, city: e.target.value }))} disabled={!newPersona.colombian_department_id || loadingCities} className="w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-4 py-1.5 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500/20 disabled:opacity-50 disabled:cursor-not-allowed dark:border-white/10 dark:bg-black/20 dark:text-white">
                                    <option value="">{loadingCities ? 'Cargando ciudades...' : 'Seleccionar ciudad'}</option>
                                    {cities.map(c => <option key={c.id} value={c.name}>{c.name}</option>)}
                                </select>
                            </div>
                        </div>
                    </FormSection>

                    {/* ── Educación y Profesión ── */}
                    <FormSection title="Educación y Profesión">
                        <div className="grid grid-cols-2 gap-3">
                            <SelectField label="Nivel Educativo" value={newPersona.education_level} onChange={um('education_level')} options={EDUCATION_LEVELS} />
                            <SelectField label="Estado Educativo" value={newPersona.education_status} onChange={um('education_status')} options={EDUCATION_STATUSES} />
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <PersonaField label="Profesión" value={newPersona.profession} onChange={um('profession')} placeholder="Ingeniero, Abogado..." />
                            <PersonaField label="Sector Económico" value={newPersona.economic_sector} onChange={um('economic_sector')} placeholder="Salud, Educación..." />
                        </div>
                    </FormSection>

                    {/* ── Información Médica ── */}
                    <FormSection title="Información Médica">
                        <div className="grid grid-cols-2 gap-3">
                            <SelectField label="Tipo de Sangre" value={newPersona.blood_type} onChange={um('blood_type')} options={BLOOD_TYPES} />
                            <input type="hidden" />
                        </div>
                        <PersonaField label="Notas Médicas" value={newPersona.medical_notes} onChange={um('medical_notes')} placeholder="Alergias, condiciones..." />
                    </FormSection>

                    {/* ── Iglesia ── */}
                    <FormSection title="Información de Iglesia">
                        <div className="grid grid-cols-2 gap-3">
                            <SelectField label="Tipo de Asistencia" value={newPersona.attendance_type} onChange={um('attendance_type')} options={ATTENDANCE_TYPES} />
                            <PersonaField label="Grupo" value={newPersona.group_name} onChange={um('group_name')} placeholder="Grupo 1, Casa de Paz..." />
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <PersonaField label="Campus / Sede" value={newPersona.campus} onChange={um('campus')} placeholder="Principal, Norte..." />
                            <PersonaField label="Fecha de Ingreso" type="date" value={newPersona.church_join_date} onChange={um('church_join_date')} placeholder="" />
                        </div>
                        <PersonaField label="Fecha de Bautismo" type="date" value={newPersona.baptism_date} onChange={um('baptism_date')} placeholder="" />
                    </FormSection>

                    {/* ── Familiar ── */}
                    <FormSection title="Información Familiar">
                        <div className="grid grid-cols-2 gap-3">
                            <PersonaField label="Nombre del Responsable" value={newPersona.responsible_adult_name} onChange={um('responsible_adult_name')} placeholder="Nombre completo" />
                            <PersonaField label="Contacto del Responsable" value={newPersona.responsible_adult_contact} onChange={um('responsible_adult_contact')} placeholder="Teléfono" />
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <PersonaField label="Nombre del Acudiente" value={newPersona.guardian_name} onChange={um('guardian_name')} placeholder="Nombre completo" />
                            <PersonaField label="Contacto del Acudiente" value={newPersona.guardian_contact} onChange={um('guardian_contact')} placeholder="Teléfono" />
                        </div>
                    </FormSection>

                    {/* ── Espiritual ── */}
                    <FormSection title="Información Espiritual">
                        <PersonaField label="Talentos y Habilidades" value={newPersona.talents} onChange={um('talents')} placeholder="Canto, enseñanza, liderazgo..." />
                        <PersonaField label="Dones Espirituales" value={newPersona.spiritual_gifts} onChange={um('spiritual_gifts')} placeholder="Profecía, enseñanza, servicio..." />
                        <PersonaField label="Notas Pastorales" value={newPersona.pastoral_notes} onChange={um('pastoral_notes')} placeholder="Observaciones pastorales..." />
                        <div className="grid grid-cols-2 gap-3">
                            <PersonaField label="Última Asistencia a Grupo" type="date" value={newPersona.last_group_attendance} onChange={um('last_group_attendance')} placeholder="" />
                            <PersonaField label="Última Asistencia a Reunión" type="date" value={newPersona.last_meeting_attendance} onChange={um('last_meeting_attendance')} placeholder="" />
                        </div>
                    </FormSection>

                    {/* ── Registro ── */}
                    <FormSection title="Información de Registro">
                        <PersonaField label="Motivo de Registro" value={newPersona.registration_reason} onChange={um('registration_reason')} placeholder="Conversión, transferencia..." />
                        <PersonaField label="Motivo de Baja" value={newPersona.unregistration_reason} onChange={um('unregistration_reason')} placeholder="Si aplica..." />
                        <div className="grid grid-cols-2 gap-3">
                            <PersonaField label="Fecha de Registro" type="date" value={newPersona.registration_date} onChange={um('registration_date')} placeholder="" />
                            <PersonaField label="Fecha de Baja" type="date" value={newPersona.unregistration_date} onChange={um('unregistration_date')} placeholder="" />
                        </div>
                        <PersonaField label="Información Opcional" value={newPersona.optional_info} onChange={um('optional_info')} placeholder="Notas adicionales..." />
                    </FormSection>
                </form>
            </WorkspaceDrawer>
        </CrmShell>
    );
}
