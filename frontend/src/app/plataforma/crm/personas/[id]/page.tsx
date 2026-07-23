"use client";

import React, { useCallback, useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
    User,
    Mail,
    Phone,
    MapPin,
    Calendar,
    ShieldCheck,
    Heart,
    Star,
    Activity,
    History,
    MessageSquare,
    ArrowLeft,
    MoreHorizontal,
    Edit3,
    Share2,
    GraduationCap,
    Users,
    DollarSign,
    Zap,
    Sparkles,
    ChevronRight,
    CheckCircle2,
    BookOpen,
    Award,
    TrendingUp,
    AlertCircle,
    Plus,
    ExternalLink,
    Flame,
    Loader2,
    Send,
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import { useAuth } from '@/context/AuthContext';
import { useCrmAccess } from '@/hooks/useCrmAccess';
import { apiFetch } from '@/lib/http';
import { toast } from 'sonner';
import CrmShell from '@/components/crm/CrmShell';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';
import Link from 'next/link';

// ─── Mentor Assignment Drawer ──────────────────────────────────────────────────

function MentorAssignmentDrawer({
    open,
    onClose,
    personaName,
    currentMentor,
    candidates,
    search,
    onSearchChange,
    selectedMentorId,
    onSelectMentor,
    notes,
    onNotesChange,
    loadingCandidates,
    saving,
    onSave,
    error,
    title = 'Asignar Mentoría',
    subtitle,
}: {
    open: boolean;
    onClose: () => void;
    personaName: string;
    currentMentor?: PersonaMentorshipSummary | null;
    candidates: PersonaMentorCandidate[];
    search: string;
    onSearchChange: (value: string) => void;
    selectedMentorId: string;
    onSelectMentor: (mentorId: string) => void;
    notes: string;
    onNotesChange: (value: string) => void;
    loadingCandidates: boolean;
    saving: boolean;
    onSave: () => void;
    error?: string | null;
    title?: string;
    subtitle?: string;
}) {
    return (
        <WorkspaceDrawer
            isOpen={open}
            onClose={onClose}
            title={title}
            subtitle={subtitle || `Para: ${personaName}`}
            actions={
                <div className="flex items-center gap-2">
                    <button onClick={onClose} className="px-4 py-2 text-[11px] font-bold text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] transition-colors">
                        Cerrar
                    </button>
                    <button
                        onClick={onSave}
                        disabled={saving || !selectedMentorId}
                        className="flex items-center gap-2 rounded-lg bg-[hsl(var(--primary))] px-4 py-2 text-[11px] font-bold uppercase tracking-wide text-white shadow-lg shadow-[hsl(var(--info)/20%)] transition-all hover:bg-[hsl(var(--primary))] active:scale-95 disabled:opacity-60"
                    >
                        {saving ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
                        Guardar
                    </button>
                </div>
            }
        >
            <div className="mt-6 space-y-4">
                {currentMentor?.mentor_name ? (
                    <div className="rounded-lg border border-[hsl(var(--success)/100%)]/20 bg-[hsl(var(--success))]/5 p-4">
                        <p className="text-[10px] font-bold uppercase tracking-wide text-success-text dark:text-success-text">Mentoría actual</p>
                        <p className="mt-1 text-sm font-bold text-[hsl(var(--text-primary))] dark:text-white">{currentMentor.mentor_name}</p>
                        <p className="text-xs text-[hsl(var(--text-secondary))]">{currentMentor.mentor_role || 'Mentor activo'}</p>
                    </div>
                ) : (
                    <div className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/5 p-4 text-sm text-[hsl(var(--text-secondary))]">
                        Esta persona aún no tiene mentoría activa.
                    </div>
                )}

                <div className="space-y-2">
                    <label className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Buscar mentor</label>
                    <input
                        value={search}
                        onChange={(e) => onSearchChange(e.target.value)}
                        placeholder="Busca por nombre, correo o teléfono"
                        className="w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] px-3 py-2 text-sm text-[hsl(var(--text-primary))] outline-none transition-all focus:border-[hsl(var(--primary))]"
                    />
                </div>

                <div className="space-y-3">
                    <p className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Candidatos sugeridos</p>
                    {loadingCandidates ? (
                        <div className="flex items-center gap-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/5 p-4 text-sm text-[hsl(var(--text-secondary))]">
                            <Loader2 size={14} className="animate-spin" />
                            Cargando candidatos...
                        </div>
                    ) : candidates.length > 0 ? (
                        <div className="space-y-2 max-h-[320px] overflow-y-auto pr-1">
                            {candidates.map((candidate) => {
                                const selected = candidate.id === selectedMentorId;
                                return (
                                    <button
                                        key={candidate.id}
                                        type="button"
                                        onClick={() => onSelectMentor(candidate.id)}
                                        className={clsx(
                                            "w-full rounded-lg border p-3 text-left transition-all",
                                            selected
                                                ? "border-[hsl(var(--primary))] bg-info-soft dark:bg-[hsl(var(--info))]/10"
                                                : "border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/5 hover:border-[hsl(var(--info)/100%)]/30"
                                        )}
                                    >
                                        <div className="flex items-start justify-between gap-3">
                                            <div>
                                                <p className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-white">{candidate.nombre_completo}</p>
                                                <p className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{candidate.church_role || 'Persona'}</p>
                                            </div>
                                            <div className="text-right">
                                                <p className="text-[11px] font-bold text-[hsl(var(--primary))]">{candidate.fit_score ?? 0}%</p>
                                                <p className="text-[9px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Ajuste</p>
                                            </div>
                                        </div>
                                        <p className="mt-2 text-xs text-[hsl(var(--text-secondary))] leading-relaxed">{candidate.fit_reason}</p>
                                    </button>
                                );
                            })}
                        </div>
                    ) : (
                        <div className="rounded-lg border border-dashed border-[hsl(var(--border))] dark:border-white/10 p-4 text-sm text-[hsl(var(--text-secondary))]">
                            No hay candidatos que cumplan el umbral mínimo de mentoría.
                        </div>
                    )}
                </div>

                <div className="space-y-2">
                    <label className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Observaciones</label>
                    <textarea
                        value={notes}
                        onChange={(e) => onNotesChange(e.target.value)}
                        rows={4}
                        placeholder="Anota contexto pastoral, frecuencia de seguimiento o acuerdos."
                        className="w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] px-3 py-2 text-sm text-[hsl(var(--text-primary))] outline-none transition-all focus:border-[hsl(var(--primary))]"
                    />
                </div>

                {error ? (
                    <div className="rounded-lg border border-[hsl(var(--danger)/100%)]/20 bg-[hsl(var(--danger))]/5 px-3 py-2 text-sm text-danger-text dark:text-danger-text">
                        {error}
                    </div>
                ) : null}
            </div>
        </WorkspaceDrawer>
    );
}

import { Tab } from '@/types/crm';

interface PersonaMeshMetric {
    key: string;
    label: string;
    value: number;
    display_value: string;
    detail?: string | null;
    tone?: string;
    has_data?: boolean;
}

interface PersonaMentorshipSummary {
    id: string;
    mentor_persona_id: string;
    mentor_name?: string | null;
    mentor_role?: string | null;
    mentee_persona_id: string;
    mentee_name?: string | null;
    mentee_role?: string | null;
    notes?: string | null;
    status?: string;
    started_at?: string;
    ended_at?: string | null;
}

interface PersonaMeshInsight {
    title: string;
    summary: string;
    recommendation: string;
    health_score?: number | null;
    health_status?: string | null;
    attendance_rate?: number;
    academy_progress?: number;
    volunteer_commitment?: number;
    metrics: PersonaMeshMetric[];
    signals: string[];
    current_mentorship?: PersonaMentorshipSummary | null;
}

interface PersonaMentorCandidate {
    id: string;
    nombre_completo: string;
    church_role?: string | null;
    health_score?: number | null;
    spiritual_health?: number;
    academy_progress?: number;
    volunteer_commitment?: number;
    fit_score?: number;
    fit_reason?: string;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatDate(val?: string | null): string {
    if (!val) return '—';
    const d = new Date(val);
    return isNaN(d.getTime()) ? '—' : d.toLocaleDateString('es-CO', { year: 'numeric', month: 'long', day: 'numeric' });
}

function formatCurrency(val?: number | null): string {
    if (val == null) return '$0';
    return new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 }).format(val);
}

function getDeptName(departments: any[], id: number | null | undefined): string {
    if (!id) return '';
    const d = departments.find(d => d.id === id);
    return d ? d.name : String(id);
}

function metricToneClass(tone?: string) {
    switch (tone) {
        case 'emerald':
            return 'bg-[hsl(var(--success))]';
        case 'amber':
            return 'bg-[hsl(var(--warning))]';
        case 'rose':
            return 'bg-[hsl(var(--danger))]';
        case 'blue':
            return 'bg-[hsl(var(--primary))]';
        default:
            return 'bg-slate-400';
    }
}

import {
  ID_TYPES,
  MARITAL_STATUSES,
  SEX_OPTIONS,
  EDUCATION_LEVELS,
  EDUCATION_STATUSES,
  BLOOD_TYPES,
  HOUSING_TYPES,
  PARTICIPATION_TYPES,
  ATTENDANCE_TYPES,
} from '@/types/crm';
import { FormSection, SelectField, EditField, QuickStat, HealthIndicator, EmptyState, InfoGrid } from '@/components/crm/ui';

// ─── Main Component ───────────────────────────────────────────────────────────

export default function PersonaDetailPage() {
    const params = useParams();
    const id = Array.isArray(params?.id) ? params.id[0] : (params?.id ?? '');
    const router = useRouter();
    const { token } = useAuth();
    const { canEditCrm } = useCrmAccess();
    const [persona, setPersona] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState<Tab>('overview');
    const [mentorDrawerOpen, setMentorDrawerOpen] = useState(false);
    const [mentorDrawerConfig, setMentorDrawerConfig] = useState<{ title: string; subtitle: string }>({
        title: 'Asignar Mentoría',
        subtitle: 'Selecciona el mentor que guiará el proceso espiritual de este persona.',
    });
    const [isEditOpen, setIsEditOpen] = useState(false);
    const [editPersona, setEditPersona] = useState<any>({});
    const [isEditSaving, setIsEditSaving] = useState(false);
    const [departments, setDepartments] = useState<any[]>([]);
    const [editCities, setEditCities] = useState<any[]>([]);
    const [loadingEditCities, setLoadingEditCities] = useState(false);
    const [mentorCandidates, setMentorCandidates] = useState<PersonaMentorCandidate[]>([]);
    const [mentorSearch, setMentorSearch] = useState('');
    const [selectedMentorId, setSelectedMentorId] = useState('');
    const [mentorNotes, setMentorNotes] = useState('');
    const [loadingMentorCandidates, setLoadingMentorCandidates] = useState(false);
    const [savingMentor, setSavingMentor] = useState(false);
    const [mentorError, setMentorError] = useState<string | null>(null);
    
    // Extra data fetched on demand
    const [history, setHistory] = useState<any[]>([]);
    const [donations, setDonations] = useState<any[]>([]);
    const [loadingHistory, setLoadingHistory] = useState(false);
    const [loadingDonations, setLoadingDonations] = useState(false);

    const loadPersonaDetail = useCallback(async (signal?: AbortSignal) => {
        try {
            const data = await apiFetch<any>(`/crm/personas/${id}`, { token, signal, cache: 'no-store' });
            const m = {
                ...data,
                first_name: data.first_name ?? '',
                last_name: data.last_name ?? '',
                email: data.email ?? '',
                phone: data.phone ?? '',
                address: data.address ?? '',
                joinedAt: data.joinedAt ?? data.created_at ?? null,
                status: data.status ?? 'Activo',
                church_role: data.church_role ?? 'Persona',
                xp: data.xp ?? 0,
                level: data.level ?? 1,
                house: data.house ?? '',
                family: Array.isArray(data.family) ? data.family : [],
                birthday: data.birthday ?? null,
                pastoral_notes: data.pastoral_notes ?? '',
                spiritual_gifts: data.spiritual_gifts ?? '',
                talents: data.talents ?? '',
                baptism_date: data.baptism_date ?? null,
                second_name: data.second_name ?? '',
                second_last_name: data.second_last_name ?? '',
                id_type: data.id_type ?? '',
                id_number: data.id_number ?? '',
                birth_country: data.birth_country ?? '',
                sex: data.sex ?? '',
                marital_status: data.marital_status ?? '',
                landline_phone: data.landline_phone ?? '',
                other_phone: data.other_phone ?? '',
                mobile_phone: data.mobile_phone ?? '',
                housing_type: data.housing_type ?? '',
                education_level: data.education_level ?? '',
                education_status: data.education_status ?? '',
                profession: data.profession ?? '',
                economic_sector: data.economic_sector ?? '',
                blood_type: data.blood_type ?? '',
                medical_notes: data.medical_notes ?? '',
                participation_type: data.participation_type ?? '',
                attendance_type: data.attendance_type ?? '',
                group_name: data.group_name ?? '',
                campus: data.campus ?? '',
                church_join_date: data.church_join_date ?? null,
                registration_reason: data.registration_reason ?? '',
                unregistration_reason: data.unregistration_reason ?? '',
                registration_date: data.registration_date ?? null,
                unregistration_date: data.unregistration_date ?? null,
                optional_info: data.optional_info ?? '',
                responsible_adult_name: data.responsible_adult_name ?? '',
                responsible_adult_contact: data.responsible_adult_contact ?? '',
                guardian_name: data.guardian_name ?? '',
                guardian_contact: data.guardian_contact ?? '',
                colombian_department_id: data.colombian_department_id ?? null,
                city: data.city ?? '',
                last_group_attendance: data.last_group_attendance ?? null,
                last_meeting_attendance: data.last_meeting_attendance ?? null,
            };
            setPersona(m);
            setEditPersona({ ...m });
            if (m.current_mentorship?.mentor_persona_id) {
                setSelectedMentorId(String(m.current_mentorship.mentor_persona_id));
            }
            if (m.current_mentorship?.notes) {
                setMentorNotes(m.current_mentorship.notes);
            }
        } catch {
            if (!signal?.aborted) {
                setPersona(null);
            }
        } finally {
            if (!signal?.aborted) {
                setLoading(false);
            }
        }
    }, [id, token]);

    useEffect(() => {
        const abortCtrl = new AbortController();
        loadPersonaDetail(abortCtrl.signal);
        // Load departments for display
        apiFetch<any[]>('/crm/colombian-departments', { token, signal: abortCtrl.signal })
            .then(setDepartments)
            .catch((_err) => {
                if (!abortCtrl.signal.aborted) {
                    toast.error('Error al cargar departamentos');
                }
            });
        return () => abortCtrl.abort();
    }, [loadPersonaDetail, id, token]);

    useEffect(() => {
        if (!mentorDrawerOpen || !token) return;

        const abortCtrl = new AbortController();
        const timer = window.setTimeout(async () => {
            setLoadingMentorCandidates(true);
            setMentorError(null);
            try {
                const params = new URLSearchParams({ limit: '12' });
                if (mentorSearch.trim()) {
                    params.set('q', mentorSearch.trim());
                }
                const data = await apiFetch<PersonaMentorCandidate[]>(
                    `/crm/personas/${id}/mentor-candidates?${params.toString()}`,
                    { token, signal: abortCtrl.signal, cache: 'no-store' }
                );
                setMentorCandidates(Array.isArray(data) ? data : []);
                if (!selectedMentorId && data?.[0]?.id) {
                    setSelectedMentorId(String(data[0].id));
                }
            } catch {
                if (!abortCtrl.signal.aborted) {
                    setMentorError('No se pudieron cargar los candidatos de mentoría.');
                    setMentorCandidates([]);
                }
            } finally {
                if (!abortCtrl.signal.aborted) {
                    setLoadingMentorCandidates(false);
                }
            }
        }, mentorSearch.trim() ? 250 : 0);

        return () => {
            abortCtrl.abort();
            window.clearTimeout(timer);
        };
    }, [id, mentorDrawerOpen, mentorSearch, selectedMentorId, token]);

    // Load cities for edit drawer cascade
    useEffect(() => {
        if (!token || !editPersona.colombian_department_id) {
            setEditCities([]);
            return;
        }
        setLoadingEditCities(true);
        apiFetch<any[]>(`/crm/colombian-departments/${editPersona.colombian_department_id}/cities`, { token })
            .then(setEditCities)
            .catch(() => setEditCities([]))
            .finally(() => setLoadingEditCities(false));
    }, [token, editPersona.colombian_department_id]);

    const handleSavePersona = async () => {
        if (!token) return;
        setIsEditSaving(true);
        try {
            const body: any = {};
            const fields = [
                'first_name','last_name','email','phone','church_role','second_name','second_last_name',
                'id_type','id_number','birth_country','sex','marital_status','birthday',
                'landline_phone','other_phone','mobile_phone','address','housing_type',
                'colombian_department_id','city','education_level','education_status','profession','economic_sector',
                'blood_type','medical_notes','participation_type','attendance_type','group_name','campus',
                'church_join_date','baptism_date','responsible_adult_name','responsible_adult_contact',
                'guardian_name','guardian_contact','talents','spiritual_gifts','pastoral_notes',
                'registration_reason','unregistration_reason','registration_date','unregistration_date',
                'optional_info','last_group_attendance','last_meeting_attendance',
            ];
            const dateFields = ['birthday','church_join_date','baptism_date','registration_date','unregistration_date','last_group_attendance','last_meeting_attendance'];
            fields.forEach(k => {
                let val = editPersona[k];
                if (dateFields.includes(k) && !val) val = null;
                // Only send changed values
                if (String(val) !== String(persona[k])) {
                    body[k] = val;
                }
            });
            if (body.colombian_department_id === '' || body.colombian_department_id === null) {
                body.colombian_department_id = null;
            }
            const updated = await apiFetch<any>(`/crm/personas/${id}`, {
                method: 'PATCH', token, body,
            });
            setPersona((prev: any) => ({ ...prev, ...updated }));
            setEditPersona((prev: any) => ({ ...prev, ...updated }));
            setIsEditOpen(false);
            toast.success('Persona actualizada');
        } catch {
            toast.error('No se pudo actualizar la persona');
        } finally {
            setIsEditSaving(false);
        }
    };

    const handleMentorSave = async () => {
        if (!token || !selectedMentorId) return;
        setSavingMentor(true);
        setMentorError(null);
        try {
            await apiFetch(`/crm/personas/${id}/mentorship`, {
                method: 'POST',
                token,
                body: {
                    mentor_persona_id: selectedMentorId,
                    notes: mentorNotes || null,
                },
            });
            toast.success('Mentoría asignada');
            setMentorDrawerOpen(false);
            await loadPersonaDetail();
        } catch {
            setMentorError('No se pudo guardar la mentoría.');
            toast.error('No se pudo guardar la mentoría');
        } finally {
            setSavingMentor(false);
        }
    };

    // Fetch history when tab activated
    useEffect(() => {
        if (activeTab === 'history' && history.length === 0 && token) {
            setLoadingHistory(true);
            apiFetch<any[]>(`/crm/personas/${id}/timeline`, { token })
                .then(d => setHistory(Array.isArray(d) ? d : []))
                .catch(() => setHistory([]))
                .finally(() => setLoadingHistory(false));
        }
        }, [activeTab, id, token, history.length]);

    // Fetch donations when financial tab activated
    useEffect(() => {
        if (activeTab === 'financial' && donations.length === 0 && token) {
            setLoadingDonations(true);
            apiFetch<any[]>(`/crm/personas/${id}/donations`, { token })
                .then(d => setDonations(Array.isArray(d) ? d : []))
                .catch(() => setDonations([]))
                .finally(() => setLoadingDonations(false));
        }
    }, [activeTab, id, token, donations.length]);

    if (loading) return (
        <div className="h-full flex flex-col items-center justify-center space-y-4">
            <div className="size-9 rounded-lg bg-[hsl(var(--info))]/10 flex items-center justify-center">
                <Activity size={24} className="text-[hsl(var(--primary))] animate-spin" />
            </div>
            <p className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Accediendo al Expediente...</p>
        </div>
    );

    if (!persona) return (
        <div className="h-full flex flex-col items-center justify-center gap-4 text-center p-4">
            <AlertCircle size={48} className="text-[hsl(var(--text-secondary))]" />
            <div>
                <p className="text-base font-bold text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]">Persona no encontrada</p>
                <p className="text-sm text-[hsl(var(--text-secondary))] mt-1">El expediente #{id} no existe o no tienes acceso.</p>
            </div>
            <button onClick={() => router.push('/plataforma/crm/personas')} className="flex items-center gap-2 px-4 py-1.5 bg-[hsl(var(--primary))] text-white rounded-lg font-bold text-sm hover:bg-[hsl(var(--primary))] transition-all">
                <ArrowLeft size={16} /> Volver a Personas
            </button>
        </div>
    );

    const fullName = persona.nombre_completo || `${persona.first_name ?? ''} ${persona.last_name ?? ''}`.trim();
    const nameParts = (persona.nombre_completo || `${persona.first_name ?? ''} ${persona.last_name ?? ''}`).trim().split(/\s+/);
    const initials = (nameParts[0]?.[0] ?? '') + (nameParts.length > 1 ? nameParts[nameParts.length - 1]?.[0] ?? '' : '');

    const TABS: { id: Tab; label: string; icon: any }[] = [
        { id: 'overview', label: 'Resumen', icon: User },
        { id: 'spiritual', label: 'Vida Espiritual', icon: Heart },
        { id: 'academy', label: 'Academia', icon: GraduationCap },
        { id: 'financial', label: 'Contribuciones', icon: DollarSign },
        { id: 'history', label: 'Historial', icon: History },
    ];

    return (
        <CrmShell
            breadcrumbs={[
                { label: 'Personas', icon: Users, href: '/plataforma/crm/personas' },
                { label: fullName, icon: User }
            ]}
            rightActions={canEditCrm ? (
                <div className="flex gap-2">
                    <button title="Editar" aria-label="Editar" onClick={() => setIsEditOpen(true)} className="p-2.5 bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-md text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] hover:border-[hsl(var(--info)/100%)]/30 transition-all"><Edit3 size={16} /></button>
                    <button title="Compartir" aria-label="Compartir" className="p-2.5 bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-md text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] hover:border-[hsl(var(--info)/100%)]/30 transition-all"><Share2 size={16} /></button>
                    <button title="Más acciones" aria-label="Más acciones" className="p-2.5 bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-md text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] hover:border-[hsl(var(--info)/100%)]/30 transition-all"><MoreHorizontal size={16} /></button>
                </div>
            ) : undefined}
        >
 <div className="w-full space-y-3 pb-4 p-4 lg:p-4">

            {/* ── 1. Profile Hero ── */}
            <motion.section
                initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                className="relative bg-[hsl(var(--surface-1))] dark:bg-[#15171c] rounded-lg border border-[hsl(var(--border))] dark:border-white/5 p-3 lg:p-4 shadow-xl shadow-black/10/20 dark:shadow-none overflow-hidden group"
            >
                <div className="absolute top-0 right-0 w-[500px] h-full bg-gradient-to-l to-[hsl(var(--info)/5%)] to-transparent pointer-events-none" />
                <div className="relative z-10 flex flex-col lg:flex-row lg:items-center gap-3">
                    {/* Avatar */}
                    <div className="relative shrink-0">
                        <div className="size-10 lg:size-10 rounded-md bg-gradient-to-tr from-[hsl(var(--info))] to-[hsl(var(--info))] flex items-center justify-center text-white text-xl font-bold shadow-2xl shadow-[hsl(var(--info)/30%)] group-hover:scale-105 transition-transform duration-500">
                            {initials}
                        </div>
                        <div className="absolute -bottom-3 -right-3 size-9 bg-[hsl(var(--surface-1))] dark:bg-[#15171c] rounded-lg flex items-center justify-center shadow-xl border border-[hsl(var(--border))] dark:border-white/10">
                            <ShieldCheck size={24} className="text-[hsl(var(--primary))]" />
                        </div>
                    </div>

                    {/* Info */}
                    <div className="flex-1 space-y-2">
                        <div className="space-y-2">
                            <div className="inline-flex items-center gap-2 px-3 py-1 bg-info-soft dark:bg-[hsl(var(--info))]/10 rounded-full text-[10px] font-bold text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))] uppercase tracking-wide border border-[hsl(var(--info)/20%)] dark:border-[hsl(var(--info)/100%)]/20">
                                ID: #{persona.id} <span className="text-[hsl(var(--text-secondary))]">•</span> {persona.status}
                            </div>
                            <h1 className="text-lg lg:text-xl font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tighter">{fullName}</h1>
                            <p className="text-sm text-[hsl(var(--text-secondary))] font-semibold">{persona.church_role}</p>
                        </div>
                        <div className="flex flex-wrap gap-3 items-center">
                            {persona.email !== '—' && <span className="flex items-center gap-2 text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] text-sm"><Mail size={16} className="text-[hsl(var(--primary))]" /> {persona.email}</span>}
                            {persona.phone !== '—' && <span className="flex items-center gap-2 text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] text-sm"><Phone size={16} className="text-[hsl(var(--success))]" /> {persona.phone}</span>}
                            {persona.address !== '—' && <span className="flex items-center gap-2 text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] text-sm"><MapPin size={16} className="text-[hsl(var(--danger))]" /> {persona.address}</span>}
                        </div>
                    </div>

                    {/* Quick Stats */}
                    <div className="flex flex-row lg:flex-col gap-3 shrink-0">
                        <QuickStat label="Puntos MESH" value={persona.xp} icon={Star} color="text-[hsl(var(--warning))]" />
                        <QuickStat label="Nivel" value={persona.level} icon={Zap} color="text-[hsl(var(--primary))]" />
                        <QuickStat label="Grupo" value={persona.house} icon={Heart} color="text-[hsl(var(--danger))]" />
                    </div>
                </div>
            </motion.section>

            {/* ── 2. Tabs ── */}
            <div className="flex border-b border-[hsl(var(--border))] dark:border-white/10 overflow-x-auto">
                {TABS.map(({ id: tabId, label, icon: Icon }) => {
                    const active = activeTab === tabId;
                    return (
                        <button
                            key={tabId}
                            onClick={() => setActiveTab(tabId)}
                            className={clsx(
                                "flex items-center gap-2 px-4 py-2 text-[11px] font-bold uppercase tracking-wider transition-all relative whitespace-nowrap shrink-0",
                                active ? "text-[hsl(var(--primary))]" : "text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-secondary))] dark:hover:text-[hsl(var(--text-secondary))]"
                            )}
                        >
                            <Icon size={14} />
                            {label}
                            {active && <motion.div layoutId="persona-tab-indicator" className="absolute bottom-0 left-0 right-0 h-[2px] bg-[hsl(var(--primary))] rounded-t-full shadow-[0_0_8px_rgba(37,99,235,0.5)]" />}
                        </button>
                    );
                })}
            </div>

            {/* ── 3. Tab Content ── */}
            <AnimatePresence mode="wait">
                <motion.div
                    key={activeTab}
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -12 }}
                    transition={{ duration: 0.2 }}
                    className="grid grid-cols-1 lg:grid-cols-12 gap-4"
                >
                    {/* ── RESUMEN ── */}
                    {activeTab === 'overview' && <>
                        <div className="lg:col-span-8 space-y-3">
                            {/* Perfil de Consolidación */}
                            <div className="bg-[hsl(var(--surface-1))] dark:bg-[#15171c] rounded-md p-3 border border-[hsl(var(--border))] dark:border-white/5 shadow-sm space-y-3">
                                <h3 className="text-[11px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Perfil de Consolidación</h3>
                                <InfoGrid items={[
                                    { label: 'Fecha de Ingreso', value: formatDate(persona.joinedAt), icon: Calendar },
                                    { label: 'Fecha de Nacimiento', value: formatDate(persona.birthday), icon: Calendar },
                                    { label: 'Grupo', value: persona.house, icon: Heart },
                                    { label: 'Rol en Ministerio', value: persona.church_role, icon: ShieldCheck },
                                ]} />
                                {persona.pastoral_notes && (
                                    <div className="p-4 bg-[hsl(var(--surface-1))] dark:bg-black/20 rounded-lg border border-[hsl(var(--border))] dark:border-white/5">
                                        <p className="text-[11px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide mb-2">Notas Pastorales</p>
                                        <p className="text-sm text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] leading-relaxed italic">&ldquo;{persona.pastoral_notes}&rdquo;</p>
                                    </div>
                                )}
                            </div>

                            {/* Datos Personales */}
                            <div className="bg-[hsl(var(--surface-1))] dark:bg-[#15171c] rounded-md p-3 border border-[hsl(var(--border))] dark:border-white/5 shadow-sm space-y-3">
                                <h3 className="text-[11px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Datos Personales</h3>
                                <InfoGrid items={[
                                    { label: 'Tipo de ID', value: persona.id_type },
                                    { label: 'Número de ID', value: persona.id_number },
                                    { label: 'Segundo Nombre', value: persona.second_name },
                                    { label: 'Segundo Apellido', value: persona.second_last_name },
                                    { label: 'Estado Civil', value: persona.marital_status },
                                    { label: 'País de Nacimiento', value: persona.birth_country },
                                    { label: 'Sexo', value: persona.sex },
                                    { label: 'Tipo de Participación', value: persona.participation_type },
                                ]} />
                            </div>

                            {/* Contacto y Ubicación */}
                            {(persona.landline_phone || persona.address || persona.city) && (
                                <div className="bg-[hsl(var(--surface-1))] dark:bg-[#15171c] rounded-md p-3 border border-[hsl(var(--border))] dark:border-white/5 shadow-sm space-y-3">
                                    <h3 className="text-[11px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Contacto y Ubicación</h3>
                                    <InfoGrid items={[
                                        { label: 'Teléfono Fijo', value: persona.landline_phone },
                                        { label: 'Celular', value: persona.mobile_phone },
                                        { label: 'Otro Teléfono', value: persona.other_phone },
                                        { label: 'Dirección', value: persona.address },
                                        { label: 'Tipo de Vivienda', value: persona.housing_type },
                                        { label: 'Departamento', value: getDeptName(departments, persona.colombian_department_id) },
                                        { label: 'Ciudad', value: persona.city },
                                    ]} />
                                </div>
                            )}

                            {/* Educación y Profesión */}
                            {(persona.profession || persona.education_level) && (
                                <div className="bg-[hsl(var(--surface-1))] dark:bg-[#15171c] rounded-md p-3 border border-[hsl(var(--border))] dark:border-white/5 shadow-sm space-y-3">
                                    <h3 className="text-[11px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Educación y Profesión</h3>
                                    <InfoGrid items={[
                                        { label: 'Nivel Educativo', value: persona.education_level },
                                        { label: 'Estado Educativo', value: persona.education_status },
                                        { label: 'Profesión', value: persona.profession },
                                        { label: 'Sector Económico', value: persona.economic_sector },
                                    ]} />
                                </div>
                            )}

                            {/* Médico */}
                            {(persona.blood_type || persona.medical_notes) && (
                                <div className="bg-[hsl(var(--surface-1))] dark:bg-[#15171c] rounded-md p-3 border border-[hsl(var(--border))] dark:border-white/5 shadow-sm space-y-3">
                                    <h3 className="text-[11px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Información Médica</h3>
                                    <InfoGrid items={[
                                        { label: 'Tipo de Sangre', value: persona.blood_type },
                                        { label: 'Notas Médicas', value: persona.medical_notes },
                                    ]} />
                                </div>
                            )}

                            {/* Núcleo Familiar */}
                            <div className="bg-[hsl(var(--surface-1))] dark:bg-[#15171c] rounded-md p-3 border border-[hsl(var(--border))] dark:border-white/5 shadow-sm space-y-3">
                                <div className="flex items-center justify-between">
                                    <h3 className="text-[11px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Núcleo Familiar</h3>
                                    <button className="flex items-center gap-1.5 text-[10px] font-bold text-[hsl(var(--primary))] uppercase tracking-wide hover:text-[hsl(var(--primary))] transition-all">
                                        <Plus size={12} /> Añadir
                                    </button>
                                </div>
                                {persona.family.length > 0 ? (
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                        {persona.family.map((f: any) => (
                                            <div key={f.id} className="p-3 bg-[hsl(var(--surface-1))] dark:bg-white/5 rounded-lg border border-[hsl(var(--border))] dark:border-white/5 flex items-center justify-between group hover:border-[hsl(var(--info)/100%)]/30 hover:bg-info-soft/50 dark:hover:bg-[hsl(var(--info))]/5 transition-all cursor-pointer">
                                                <div className="flex items-center gap-3">
                                                    <div className="size-9 rounded-md bg-[hsl(var(--surface-1))] dark:bg-[#15171c] flex items-center justify-center shadow-sm border border-[hsl(var(--border))] dark:border-white/10">
                                                        <User size={16} className="text-[hsl(var(--text-secondary))]" />
                                                    </div>
                                                    <div>
                                                        <p className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-white">{f.name ?? f.first_name}</p>
                                                        <p className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">{f.relation}</p>
                                                    </div>
                                                </div>
                                                <ChevronRight size={16} className="text-[hsl(var(--text-secondary))] group-hover:translate-x-1 transition-transform" />
                                            </div>
                                        ))}
                                    </div>
                                ) : (
                                    <div className="py-2 text-center rounded-lg bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-dashed border-[hsl(var(--border))] dark:border-white/10">
                                        <Users size={28} className="mx-auto text-[hsl(var(--text-secondary))] mb-3" />
                                        <p className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Sin núcleo familiar registrado</p>
                                        <p className="text-xs text-[hsl(var(--text-secondary))] mt-1">Este persona aún no pertenece a una familia</p>
                                    </div>
                                )}
                            </div>
                        </div>

                        <div className="lg:col-span-4 space-y-3">
                            {/* MESH Insight */}
                            {(() => {
                                const insight: PersonaMeshInsight | undefined = persona.mesh_insight;
                                const metrics = insight?.metrics ?? [];
                                const currentMentor = insight?.current_mentorship ?? persona.current_mentorship;
                                return (
                                    <div className="p-4 bg-gradient-to-br from-[hsl(var(--info))] via-[hsl(var(--info))] to-[hsl(var(--info))] rounded-md text-white shadow-xl relative overflow-hidden group">
                                        <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:scale-110 transition-transform duration-700"><Sparkles size={100} /></div>
                                        <div className="relative z-10 space-y-4">
                                            <div className="flex items-center gap-2">
                                                <Flame size={18} className="text-[hsl(var(--warning))]" />
                                                <h4 className="text-base font-bold tracking-tight uppercase">{insight?.title || 'MESH Insight'}</h4>
                                            </div>
                                            <div className="space-y-2">
                                                <p className="text-sm font-medium text-[hsl(var(--info))] leading-relaxed">
                                                    {insight?.summary || `${fullName} tiene potencial pastoral en su área de servicio.`}
                                                </p>
                                                <p className="text-xs text-[hsl(var(--info)/90%)] leading-relaxed">
                                                    {insight?.recommendation || 'Mantener seguimiento activo y asignar acompañamiento si hace falta.'}
                                                </p>
                                            </div>
                                            {currentMentor?.mentor_name ? (
                                                <div className="rounded-lg bg-white/10 p-3 border border-white/10">
                                                    <p className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--info))]">Mentoría actual</p>
                                                    <p className="mt-1 text-sm font-bold text-white">{currentMentor.mentor_name}</p>
                                                    <p className="text-[11px] text-[hsl(var(--info)/90%)]">{currentMentor.mentor_role || 'Mentor activo'}</p>
                                                </div>
                                            ) : null}
                                            {metrics.length > 0 ? (
                                                <div className="space-y-3 rounded-lg bg-white/10 p-3 border border-white/10">
                                                    {metrics.map((metric) => (
                                                        <HealthIndicator
                                                            key={metric.key}
                                                            label={metric.label}
                                                            value={Math.max(0, Math.min(100, Math.round(metric.value || 0)))}
                                                            color={metricToneClass(metric.tone)}
                                                        />
                                                    ))}
                                                </div>
                                            ) : null}
                                            {insight?.signals?.length ? (
                                                <div className="flex flex-wrap gap-2">
                                                    {insight.signals.slice(0, 4).map((signal) => (
                                                        <span key={signal} className="rounded-full border border-white/15 bg-white/10 px-3 py-1 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--info))]">
                                                            {signal}
                                                        </span>
                                                    ))}
                                                </div>
                                            ) : null}
                                            <button
                                                onClick={() => {
                                                    setMentorDrawerConfig({
                                                        title: 'Asignar Mentoría',
                                                        subtitle: `Selecciona el mentor que guiará el proceso espiritual de ${fullName}.`,
                                                    });
                                                    setMentorDrawerOpen(true);
                                                }}
                                                className="w-full py-1.5 bg-[hsl(var(--surface-1))] text-[hsl(var(--text-primary))] rounded-lg font-bold text-[10px] uppercase tracking-wide shadow-xl hover:scale-105 active:scale-95 transition-all"
                                            >
                                                Asignar Mentoría
                                            </button>
                                        </div>
                                    </div>
                                );
                            })()}

                            {/* Indicadores de Salud */}
                            <div className="bg-[hsl(var(--surface-1))] dark:bg-[#15171c] rounded-md p-4 border border-[hsl(var(--border))] dark:border-white/5 shadow-sm space-y-2">
                                <h3 className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Indicadores de Salud</h3>
                                <HealthIndicator label="Asistencia Mensual" value={Math.max(0, Math.min(100, Math.round(persona.mesh_insight?.attendance_rate ?? 0)))} color="bg-[hsl(var(--success))]" />
                                <HealthIndicator label="Progreso Academia" value={Math.max(0, Math.min(100, Math.round(persona.mesh_insight?.academy_progress ?? persona.academy_progress ?? 0)))} color="bg-[hsl(var(--primary))]" />
                                <HealthIndicator label="Compromiso Voluntario" value={Math.max(0, Math.min(100, Math.round(persona.mesh_insight?.volunteer_commitment ?? persona.volunteer_commitment ?? 0)))} color="bg-[hsl(var(--warning))]" />
                            </div>
                        </div>
                    </>}

                    {/* ── VIDA ESPIRITUAL ── */}
                    {activeTab === 'spiritual' && <>
                        <div className="lg:col-span-8 space-y-3">
                            <div className="bg-[hsl(var(--surface-1))] dark:bg-[#15171c] rounded-md p-3 border border-[hsl(var(--border))] dark:border-white/5 shadow-sm space-y-3">
                                <h3 className="text-[11px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Datos Espirituales</h3>
                                <InfoGrid items={[
                                    { label: 'Fecha de Bautismo', value: formatDate(persona.baptism_date), icon: CheckCircle2 },
                                    { label: 'Grupo', value: persona.house, icon: Heart },
                                    { label: 'Estado Espiritual', value: persona.status, icon: ShieldCheck },
                                    { label: 'Rol en la Iglesia', value: persona.church_role, icon: Star },
                                ]} />
                                {persona.spiritual_gifts ? (
                                    <div className="space-y-3">
                                        <p className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Dones Espirituales</p>
                                        <div className="flex flex-wrap gap-2">
                                            {persona.spiritual_gifts.split(',').map((gift: string, i: number) => (
                                                <span key={i} className="px-3 py-1.5 bg-info-soft dark:bg-[hsl(var(--primary))]/10 text-[hsl(var(--primary))] dark:text-info-text text-[11px] font-bold rounded-md border border-[hsl(var(--info)/20%)] dark:border-[hsl(var(--primary))]/20 uppercase tracking-wide">
                                                    {gift.trim()}
                                                </span>
                                            ))}
                                        </div>
                                    </div>
                                ) : (
                                    <div className="p-4 bg-[hsl(var(--surface-1))] dark:bg-white/5 rounded-lg border border-dashed border-[hsl(var(--border))] dark:border-white/10 text-center">
                                        <p className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Dones espirituales no registrados</p>
                                    </div>
                                )}
                                {persona.talents ? (
                                    <div className="space-y-3">
                                        <p className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Talentos y Habilidades</p>
                                        <p className="text-sm text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] leading-relaxed">{persona.talents}</p>
                                    </div>
                                ) : null}
                            </div>
                        </div>
                        <div className="lg:col-span-4 space-y-3">
                            <div className="p-4 bg-gradient-to-br from-[hsl(var(--danger))] to-[hsl(var(--domain-pink))] rounded-md text-white shadow-xl relative overflow-hidden">
                                <div className="absolute top-0 right-0 p-4 opacity-10"><Heart size={80} /></div>
                                <div className="relative z-10 space-y-4">
                                    <h4 className="text-sm font-bold uppercase tracking-wide">Cuidado Pastoral</h4>
                                    <p className="text-sm text-[hsl(var(--danger))] leading-relaxed">Esta persona está siendo acompañada activamente en su proceso espiritual.</p>
                                    <button
                                        onClick={() => {
                                            setMentorDrawerConfig({
                                                title: 'Asignar Pastor',
                                                subtitle: `Selecciona el pastor que hará seguimiento espiritual de ${fullName}.`,
                                            });
                                            setMentorDrawerOpen(true);
                                        }}
                                        className="w-full py-1.5 bg-[hsl(var(--surface-1))] text-danger-text rounded-lg font-bold text-[10px] uppercase tracking-wide hover:scale-105 transition-all"
                                    >
                                        Asignar Pastor
                                    </button>
                                </div>
                            </div>
                        </div>
                    </>}

                    {/* ── ACADEMIA ── */}
                    {activeTab === 'academy' && <>
                        <div className="lg:col-span-12">
                            <div className="bg-[hsl(var(--surface-1))] dark:bg-[#15171c] rounded-md p-3 border border-[hsl(var(--border))] dark:border-white/5 shadow-sm">
                                <div className="flex items-center justify-between mb-3">
                                    <h3 className="text-[11px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Progreso Académico</h3>
                                    <Link href="/plataforma/academy" className="flex items-center gap-1.5 text-[10px] font-bold text-[hsl(var(--primary))] uppercase tracking-wide hover:text-[hsl(var(--primary))] transition-all">
                                        Ver Academia <ExternalLink size={12} />
                                    </Link>
                                </div>
                                <EmptyState
                                    icon={GraduationCap}
                                    title="Sin cursos registrados"
                                    description={`${fullName} aún no está inscrito en ningún curso de la Academia CCF.`}
                                    action={
                                        <Link href="/plataforma/academy" className="flex items-center gap-2 px-4 py-1.5 bg-[hsl(var(--primary))] text-white rounded-lg font-bold text-sm hover:bg-[hsl(var(--primary))] transition-all mt-2">
                                            <BookOpen size={16} /> Explorar Cursos
                                        </Link>
                                    }
                                />
                            </div>
                        </div>
                    </>}

                    {/* ── CONTRIBUCIONES ── */}
                    {activeTab === 'financial' && <>
                        <div className="lg:col-span-12 space-y-3">
                            {/* Summary Cards */}
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                {[
                                    { label: 'Total Diezmos', value: donations.filter(d => d.donation_type === 'diezmo').reduce((s: number, d: any) => s + d.amount, 0), color: 'bg-[hsl(var(--success))]', icon: TrendingUp },
                                    { label: 'Total Ofrendas', value: donations.filter(d => d.donation_type === 'ofrenda').reduce((s: number, d: any) => s + d.amount, 0), color: 'bg-[hsl(var(--primary))]', icon: DollarSign },
                                    { label: 'Total Registrado', value: donations.reduce((s: number, d: any) => s + d.amount, 0), color: 'bg-[hsl(var(--primary))]', icon: Award },
                                ].map((stat, i) => (
                                    <div key={i} className="bg-[hsl(var(--surface-1))] dark:bg-[#15171c] rounded-md p-4 border border-[hsl(var(--border))] dark:border-white/5 shadow-sm space-y-3">
                                        <div className={clsx('size-8 rounded-md flex items-center justify-center text-white', stat.color)}>
                                            <stat.icon size={18} />
                                        </div>
                                        <p className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">{stat.label}</p>
                                        <p className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white">{formatCurrency(stat.value)}</p>
                                    </div>
                                ))}
                            </div>

                            {/* Transactions */}
                            <div className="bg-[hsl(var(--surface-1))] dark:bg-[#15171c] rounded-md p-3 border border-[hsl(var(--border))] dark:border-white/5 shadow-sm">
                                <h3 className="text-[11px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-3">Historial de Siembras</h3>
                                {loadingDonations ? (
                                    <div className="py-2 text-center text-[hsl(var(--text-secondary))] text-sm">Cargando...</div>
                                ) : donations.length > 0 ? (
                                    <div className="space-y-3">
                                        {donations.map((d: any, i: number) => (
                                            <div key={i} className="flex items-center justify-between p-4 bg-[hsl(var(--surface-1))] dark:bg-white/5 rounded-lg">
                                                <div className="flex items-center gap-3">
                                                    <div className="size-9 rounded-md bg-success-soft dark:bg-[hsl(var(--success))]/10 flex items-center justify-center">
                                                        <DollarSign size={16} className="text-success-text" />
                                                    </div>
                                                    <div>
                                                        <p className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-white capitalize">{d.donation_type}</p>
                                                        <p className="text-[10px] text-[hsl(var(--text-secondary))]">{formatDate(d.created_at)}</p>
                                                    </div>
                                                </div>
                                                <p className="text-sm font-bold text-success-text">{formatCurrency(d.amount)}</p>
                                            </div>
                                        ))}
                                    </div>
                                ) : (
                                    <EmptyState
                                        icon={DollarSign}
                                        title="Sin contribuciones registradas"
                                        description="No se han registrado diezmos u ofrendas para este persona."
                                    />
                                )}
                            </div>
                        </div>
                    </>}

                    {/* ── HISTORIAL ── */}
                    {activeTab === 'history' && <>
                        <div className="lg:col-span-12">
                            <div className="bg-[hsl(var(--surface-1))] dark:bg-[#15171c] rounded-md p-3 border border-[hsl(var(--border))] dark:border-white/5 shadow-sm">
                                <h3 className="text-[11px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-3">Línea de Tiempo Pastoral</h3>
                                {loadingHistory ? (
                                    <div className="py-2 text-center text-[hsl(var(--text-secondary))] text-sm">Cargando historial...</div>
                                ) : history.length > 0 ? (
                                    <div className="relative space-y-0">
                                        <div className="absolute left-5 top-0 bottom-0 w-px bg-[hsl(var(--surface-2))] dark:bg-white/5" />
                                        {history.map((event: any, i: number) => (
                                            <div key={i} className="flex gap-4 pl-12 pb-8 relative">
                                                <div className="absolute left-0 top-1 size-8 rounded-md bg-[hsl(var(--surface-1))] dark:bg-[#15171c] border border-[hsl(var(--border))] dark:border-white/10 flex items-center justify-center shadow-sm z-10">
                                                    <MessageSquare size={16} className="text-[hsl(var(--primary))]" />
                                                </div>
                                                <div className="flex-1 bg-[hsl(var(--surface-1))] dark:bg-white/5 rounded-lg p-3">
                                                    <div className="flex items-center justify-between mb-2">
                                                        <p className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-white">{event.event_type ?? event.type ?? 'Evento'}</p>
                                                        <p className="text-[10px] text-[hsl(var(--text-secondary))]">{formatDate(event.created_at)}</p>
                                                    </div>
                                                    {event.notes && <p className="text-xs text-[hsl(var(--text-secondary))] leading-relaxed">{event.notes}</p>}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                ) : (
                                    <EmptyState
                                        icon={History}
                                        title="Sin historial registrado"
                                        description={`No se han registrado eventos pastorales para ${fullName} aún.`}
                                        action={
                                            <button className="flex items-center gap-2 px-4 py-1.5 bg-[hsl(var(--surface-2))] dark:bg-[hsl(var(--bg-primary))] text-white dark:text-[hsl(var(--text-primary))] rounded-lg font-bold text-sm hover:opacity-90 transition-all mt-2">
                                                <Plus size={16} /> Registrar Evento
                                            </button>
                                        }
                                    />
                                )}
                            </div>
                        </div>
                    </>}
                </motion.div>
            </AnimatePresence>
        </div>
        
            {/* Mentor Assignment Drawer */}
            <MentorAssignmentDrawer
                open={mentorDrawerOpen}
                onClose={() => setMentorDrawerOpen(false)}
                personaName={fullName}
                currentMentor={persona.current_mentorship}
                candidates={mentorCandidates}
                search={mentorSearch}
                onSearchChange={setMentorSearch}
                selectedMentorId={selectedMentorId}
                onSelectMentor={setSelectedMentorId}
                notes={mentorNotes}
                onNotesChange={setMentorNotes}
                loadingCandidates={loadingMentorCandidates}
                saving={savingMentor}
                onSave={handleMentorSave}
                error={mentorError}
                title={mentorDrawerConfig.title}
                subtitle={mentorDrawerConfig.subtitle}
            />

            {/* Edit Persona Drawer */}
            <WorkspaceDrawer
                isOpen={isEditOpen}
                onClose={() => setIsEditOpen(false)}
                title="Editar Persona"
                subtitle={`Actualizando perfil de ${fullName}`}
                actions={
                    <>
                        <button type="button" onClick={() => setIsEditOpen(false)} className="px-4 py-2 text-[11px] font-bold text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]">Cancelar</button>
                        <button type="button" onClick={handleSavePersona} disabled={isEditSaving} className="flex items-center gap-2 rounded-lg bg-[hsl(var(--primary))] px-3 py-2 text-[11px] font-bold uppercase tracking-wide text-white shadow-lg shadow-[hsl(var(--info)/20%)] transition-all hover:bg-[hsl(var(--primary))] active:scale-95 disabled:opacity-60">
                            {isEditSaving ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
                            Guardar
                        </button>
                    </>
                }
            >
                <div className="space-y-2">
                    {/* Básicos */}
                    <div className="rounded-lg overflow-hidden">
                        <div className="px-3 py-2 space-y-2">
                            <div className="grid grid-cols-2 gap-3">
                                <EditField label="Nombre" value={editPersona.first_name ?? ''} onChange={v => setEditPersona((p: any) => ({...p, first_name: v}))} placeholder="Juan" />
                                <EditField label="Apellido" value={editPersona.last_name ?? ''} onChange={v => setEditPersona((p: any) => ({...p, last_name: v}))} placeholder="Pérez" />
                            </div>
                            <div className="grid grid-cols-2 gap-3">
                                <EditField label="Segundo Nombre" value={editPersona.second_name ?? ''} onChange={v => setEditPersona((p: any) => ({...p, second_name: v}))} placeholder="José" />
                                <EditField label="Segundo Apellido" value={editPersona.second_last_name ?? ''} onChange={v => setEditPersona((p: any) => ({...p, second_last_name: v}))} placeholder="García" />
                            </div>
                            <div className="grid grid-cols-2 gap-3">
                                <EditField label="Correo" type="email" value={editPersona.email ?? ''} onChange={v => setEditPersona((p: any) => ({...p, email: v}))} placeholder="correo@ejemplo.com" />
                                <EditField label="Teléfono" value={editPersona.phone ?? ''} onChange={v => setEditPersona((p: any) => ({...p, phone: v}))} placeholder="+57 300 000 0000" />
                            </div>
                            <div className="grid grid-cols-2 gap-3">
                                <SelectField label="Rol" value={editPersona.church_role ?? ''} onChange={v => setEditPersona((p: any) => ({...p, church_role: v}))} options={['Persona','Pastor','Líder','Diácono','Ministro de Culto','Apóstol','Profeta','Evangelista','Maestro','Administrador']} />
                                <SelectField label="Tipo de Participación" value={editPersona.participation_type ?? ''} onChange={v => setEditPersona((p: any) => ({...p, participation_type: v}))} options={PARTICIPATION_TYPES} />
                            </div>
                        </div>
                    </div>

                    <FormSection title="Identificación">
                        <div className="grid grid-cols-2 gap-3">
                            <SelectField label="Tipo de ID" value={editPersona.id_type ?? ''} onChange={v => setEditPersona((p: any) => ({...p, id_type: v}))} options={ID_TYPES} />
                            <EditField label="Número de ID" value={editPersona.id_number ?? ''} onChange={v => setEditPersona((p: any) => ({...p, id_number: v}))} placeholder="1234567890" />
                        </div>
                    </FormSection>

                    <FormSection title="Información Personal">
                        <div className="grid grid-cols-2 gap-3">
                            <SelectField label="Sexo" value={editPersona.sex ?? ''} onChange={v => setEditPersona((p: any) => ({...p, sex: v}))} options={SEX_OPTIONS} />
                            <SelectField label="Estado Civil" value={editPersona.marital_status ?? ''} onChange={v => setEditPersona((p: any) => ({...p, marital_status: v}))} options={MARITAL_STATUSES} />
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <EditField label="País de Nacimiento" value={editPersona.birth_country ?? ''} onChange={v => setEditPersona((p: any) => ({...p, birth_country: v}))} placeholder="Colombia" />
                            <EditField label="Fecha de Nacimiento" type="date" value={editPersona.birthday ? editPersona.birthday.slice(0,10) : ''} onChange={v => setEditPersona((p: any) => ({...p, birthday: v}))} placeholder="" />
                        </div>
                    </FormSection>

                    <FormSection title="Contacto y Ubicación">
                        <div className="grid grid-cols-2 gap-3">
                            <EditField label="Teléfono Fijo" value={editPersona.landline_phone ?? ''} onChange={v => setEditPersona((p: any) => ({...p, landline_phone: v}))} placeholder="+57 1 000 0000" />
                            <EditField label="Otro Teléfono" value={editPersona.other_phone ?? ''} onChange={v => setEditPersona((p: any) => ({...p, other_phone: v}))} placeholder="+57 300 000 0000" />
                        </div>
                        <EditField label="Dirección" value={editPersona.address ?? ''} onChange={v => setEditPersona((p: any) => ({...p, address: v}))} placeholder="Cra 1 # 2-3, Barrio..." />
                        <div className="grid grid-cols-2 gap-3">
                            <SelectField label="Tipo de Vivienda" value={editPersona.housing_type ?? ''} onChange={v => setEditPersona((p: any) => ({...p, housing_type: v}))} options={HOUSING_TYPES} />
                            <EditField label="Celular" value={editPersona.mobile_phone ?? ''} onChange={v => setEditPersona((p: any) => ({...p, mobile_phone: v}))} placeholder="+57 300 000 0000" />
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <div className="space-y-2">
                                <label className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Departamento</label>
                                <select value={editPersona.colombian_department_id ?? ''} onChange={e => setEditPersona((p: any) => ({ ...p, colombian_department_id: e.target.value ? Number(e.target.value) : null, city: '' }))} className="w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-4 py-1.5 text-sm font-bold outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.2] dark:border-white/10 dark:bg-black/20 dark:text-white">
                                    <option value="">Seleccionar departamento</option>
                                    {departments.map((d: any) => <option key={d.id} value={d.id}>{d.name}</option>)}
                                </select>
                            </div>
                            <div className="space-y-2">
                                <label className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Ciudad</label>
                                <select value={editPersona.city ?? ''} onChange={e => setEditPersona((p: any) => ({ ...p, city: e.target.value }))} disabled={!editPersona.colombian_department_id || loadingEditCities} className="w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-4 py-1.5 text-sm font-bold outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.2] disabled:opacity-50 disabled:cursor-not-allowed dark:border-white/10 dark:bg-black/20 dark:text-white">
                                    <option value="">{loadingEditCities ? 'Cargando ciudades...' : 'Seleccionar ciudad'}</option>
                                    {editCities.map((c: any) => <option key={c.id} value={c.name}>{c.name}</option>)}
                                </select>
                            </div>
                        </div>
                    </FormSection>

                    <FormSection title="Educación y Profesión">
                        <div className="grid grid-cols-2 gap-3">
                            <SelectField label="Nivel Educativo" value={editPersona.education_level ?? ''} onChange={v => setEditPersona((p: any) => ({...p, education_level: v}))} options={EDUCATION_LEVELS} />
                            <SelectField label="Estado Educativo" value={editPersona.education_status ?? ''} onChange={v => setEditPersona((p: any) => ({...p, education_status: v}))} options={EDUCATION_STATUSES} />
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <EditField label="Profesión" value={editPersona.profession ?? ''} onChange={v => setEditPersona((p: any) => ({...p, profession: v}))} placeholder="Ingeniero, Abogado..." />
                            <EditField label="Sector Económico" value={editPersona.economic_sector ?? ''} onChange={v => setEditPersona((p: any) => ({...p, economic_sector: v}))} placeholder="Salud, Educación..." />
                        </div>
                    </FormSection>

                    <FormSection title="Información Médica">
                        <SelectField label="Tipo de Sangre" value={editPersona.blood_type ?? ''} onChange={v => setEditPersona((p: any) => ({...p, blood_type: v}))} options={BLOOD_TYPES} />
                        <EditField label="Notas Médicas" value={editPersona.medical_notes ?? ''} onChange={v => setEditPersona((p: any) => ({...p, medical_notes: v}))} placeholder="Alergias, condiciones..." />
                    </FormSection>

                    <FormSection title="Información de Iglesia">
                        <div className="grid grid-cols-2 gap-3">
                            <SelectField label="Tipo de Asistencia" value={editPersona.attendance_type ?? ''} onChange={v => setEditPersona((p: any) => ({...p, attendance_type: v}))} options={ATTENDANCE_TYPES} />
                            <EditField label="Grupo" value={editPersona.group_name ?? ''} onChange={v => setEditPersona((p: any) => ({...p, group_name: v}))} placeholder="Grupo 1, Casa de Paz..." />
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <EditField label="Campus / Sede" value={editPersona.campus ?? ''} onChange={v => setEditPersona((p: any) => ({...p, campus: v}))} placeholder="Principal, Norte..." />
                            <EditField label="Fecha de Ingreso" type="date" value={editPersona.church_join_date ? editPersona.church_join_date.slice(0,10) : ''} onChange={v => setEditPersona((p: any) => ({...p, church_join_date: v}))} placeholder="" />
                        </div>
                        <EditField label="Fecha de Bautismo" type="date" value={editPersona.baptism_date ? editPersona.baptism_date.slice(0,10) : ''} onChange={v => setEditPersona((p: any) => ({...p, baptism_date: v}))} placeholder="" />
                    </FormSection>

                    <FormSection title="Información Familiar">
                        <div className="grid grid-cols-2 gap-3">
                            <EditField label="Nombre del Responsable" value={editPersona.responsible_adult_name ?? ''} onChange={v => setEditPersona((p: any) => ({...p, responsible_adult_name: v}))} placeholder="Nombre completo" />
                            <EditField label="Contacto del Responsable" value={editPersona.responsible_adult_contact ?? ''} onChange={v => setEditPersona((p: any) => ({...p, responsible_adult_contact: v}))} placeholder="Teléfono" />
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <EditField label="Nombre del Acudiente" value={editPersona.guardian_name ?? ''} onChange={v => setEditPersona((p: any) => ({...p, guardian_name: v}))} placeholder="Nombre completo" />
                            <EditField label="Contacto del Acudiente" value={editPersona.guardian_contact ?? ''} onChange={v => setEditPersona((p: any) => ({...p, guardian_contact: v}))} placeholder="Teléfono" />
                        </div>
                    </FormSection>

                    <FormSection title="Información Espiritual">
                        <EditField label="Talentos y Habilidades" value={editPersona.talents ?? ''} onChange={v => setEditPersona((p: any) => ({...p, talents: v}))} placeholder="Canto, enseñanza, liderazgo..." />
                        <EditField label="Dones Espirituales" value={editPersona.spiritual_gifts ?? ''} onChange={v => setEditPersona((p: any) => ({...p, spiritual_gifts: v}))} placeholder="Profecía, enseñanza, servicio..." />
                        <EditField label="Notas Pastorales" value={editPersona.pastoral_notes ?? ''} onChange={v => setEditPersona((p: any) => ({...p, pastoral_notes: v}))} placeholder="Observaciones pastorales..." />
                        <div className="grid grid-cols-2 gap-3">
                            <EditField label="Última Asistencia a Grupo" type="date" value={editPersona.last_group_attendance ? editPersona.last_group_attendance.slice(0,10) : ''} onChange={v => setEditPersona((p: any) => ({...p, last_group_attendance: v}))} placeholder="" />
                            <EditField label="Última Asistencia a Reunión" type="date" value={editPersona.last_meeting_attendance ? editPersona.last_meeting_attendance.slice(0,10) : ''} onChange={v => setEditPersona((p: any) => ({...p, last_meeting_attendance: v}))} placeholder="" />
                        </div>
                    </FormSection>

                    <FormSection title="Información de Registro">
                        <EditField label="Motivo de Registro" value={editPersona.registration_reason ?? ''} onChange={v => setEditPersona((p: any) => ({...p, registration_reason: v}))} placeholder="Conversión, transferencia..." />
                        <EditField label="Motivo de Baja" value={editPersona.unregistration_reason ?? ''} onChange={v => setEditPersona((p: any) => ({...p, unregistration_reason: v}))} placeholder="Si aplica..." />
                        <div className="grid grid-cols-2 gap-3">
                            <EditField label="Fecha de Registro" type="date" value={editPersona.registration_date ? editPersona.registration_date.slice(0,10) : ''} onChange={v => setEditPersona((p: any) => ({...p, registration_date: v}))} placeholder="" />
                            <EditField label="Fecha de Baja" type="date" value={editPersona.unregistration_date ? editPersona.unregistration_date.slice(0,10) : ''} onChange={v => setEditPersona((p: any) => ({...p, unregistration_date: v}))} placeholder="" />
                        </div>
                        <EditField label="Información Opcional" value={editPersona.optional_info ?? ''} onChange={v => setEditPersona((p: any) => ({...p, optional_info: v}))} placeholder="Notas adicionales..." />
                    </FormSection>
                </div>
            </WorkspaceDrawer>
        </CrmShell>
    );
}
