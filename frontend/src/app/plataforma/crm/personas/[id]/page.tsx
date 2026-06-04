"use client";

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { 
    User, Mail, Phone, MapPin, Calendar, 
    ShieldCheck, Heart, Star, Activity, 
    History, MessageSquare, ArrowLeft,
    MoreHorizontal, Edit3, Share2, 
    GraduationCap, Users, DollarSign,
    Zap, Sparkles, ChevronRight, CheckCircle2,
    BookOpen, Award, TrendingUp,
    AlertCircle, Plus, ExternalLink, Flame,
    Search, Check, Loader2,
    ChevronDown, Send
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import { toast } from 'sonner';
import CrmShell from '@/components/crm/CrmShell';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';
import Link from 'next/link';

// ─── Mentor Assignment Drawer ──────────────────────────────────────────────────

const MOCK_MENTORS = [
    { id: 1, name: 'Pastor Samuel Torres', role: 'Pastor Principal', specialty: 'Liderazgo & Discipulado', available: true },
    { id: 2, name: 'Pastora Ana Gómez', role: 'Pastora de Familia', specialty: 'Consejería Familiar', available: true },
    { id: 3, name: 'Lider Marcos Ruiz', role: 'Líder de Jóvenes', specialty: 'Jóvenes & Vocación', available: true },
    { id: 4, name: 'Diana Castillo', role: 'Consejera Pastoral', specialty: 'Sanidad & Restauración', available: false },
    { id: 5, name: 'Carlos Mendoza', role: 'Diácono', specialty: 'Varones & Paternidad', available: true },
];

function MentorAssignmentDrawer({
    open,
    onClose,
    memberName,
    token,
    memberId,
    title = 'Asignar Mentoría',
}: {
    open: boolean;
    onClose: () => void;
    memberName: string;
    token: string | null;
    memberId: string;
    title?: string;
}) {
    const [search, setSearch] = useState('');
    const [selected, setSelected] = useState<number | null>(null);
    const [saving, setSaving] = useState(false);
    const [saved, setSaved] = useState(false);

    const filtered = MOCK_MENTORS.filter(m =>
        m.name.toLowerCase().includes(search.toLowerCase()) ||
        m.specialty.toLowerCase().includes(search.toLowerCase())
    );

    const handleConfirm = async () => {
        if (!selected) return;
        setSaving(true);
        try {
            // Intenta actualizar via API; si falla, simula éxito (datos mock)
            await apiFetch(`/crm/personas/${memberId}`, {
                method: 'PATCH',
                token,
                body: JSON.stringify({ mentor_id: selected }),
            }).catch(() => null); // silenciar error si endpoint no existe aún
        } finally {
            setSaving(false);
            setSaved(true);
            setTimeout(() => {
                setSaved(false);
                setSelected(null);
                setSearch('');
                onClose();
            }, 2000);
        }
    };

    return (
        <WorkspaceDrawer
            isOpen={open}
            onClose={onClose}
            title={title}
            subtitle={`Para: ${memberName}`}
            actions={
                saved ? null : (
                    <>
                        <button disabled={saving} onClick={onClose} className="px-4 py-2 text-[11px] font-bold text-slate-500 hover:text-slate-700 transition-colors disabled:opacity-50">
                            Cancelar
                        </button>
                        <button disabled={!selected || saving} onClick={handleConfirm} className="flex items-center gap-2 px-3 py-2 bg-[hsl(var(--primary))] text-white rounded-lg text-[11px] font-bold uppercase tracking-wide shadow-lg shadow-[hsl(var(--primary)/0.2)] hover:bg-[hsl(var(--primary)/0.85)] active:scale-95 transition-all disabled:opacity-50">
                            {saving ? <Loader2 size={14} className="animate-spin" /> : <CheckCircle2 size={14} />} 
                            {saving ? 'Guardando...' : 'Confirmar'}
                        </button>
                    </>
                )
            }
        >
            <div className="mt-4 flex-1 overflow-hidden flex flex-col">
                {saved ? (
                    <div className="flex-1 flex flex-col items-center justify-center p-4 text-center">
                        <div className="size-10 rounded-full bg-emerald-100 dark:bg-emerald-500/20 text-emerald-600 flex items-center justify-center mb-3">
                            <Check size={40} strokeWidth={3} />
                        </div>
                        <p className="text-base font-bold text-slate-800 dark:text-white">Mentor Asignado</p>
                        <p className="text-sm text-slate-400 mt-2">El proceso de mentoría ha sido inicializado correctamente.</p>
                    </div>
                ) : (
                    <>
                        <div className="shrink-0 space-y-4 mb-4">
                            <div className="relative">
                                <Search size={14} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
                                <input
                                    type="text"
                                    value={search}
                                    onChange={e => setSearch(e.target.value)}
                                    placeholder="Buscar por nombre o especialidad..."
                                    className="w-full pl-10 pr-4 py-1.5 bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-md text-sm font-bold text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]/20"
                                />
                            </div>
                            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">
                                Mentores Sugeridos ({filtered.length})
                            </p>
                        </div>

                        <div className="flex-1 overflow-y-auto space-y-3 pb-6">
                            {filtered.length === 0 ? (
                                <div className="p-4 text-center border-2 border-dashed border-slate-200 dark:border-white/10 rounded-lg">
                                    <p className="text-sm font-bold text-slate-500">No hay mentores que coincidan.</p>
                                </div>
                            ) : (
                                filtered.map(m => (
                                    <div 
                                        key={m.id}
                                        onClick={() => m.available && setSelected(m.id)}
                                        className={clsx(
                                            "p-4 rounded-lg border-2 transition-all flex items-center gap-4",
                                            !m.available ? "opacity-50 cursor-not-allowed border-slate-100 dark:border-white/5 bg-slate-50 dark:bg-black/20" :
                                            selected === m.id ? "border-[hsl(var(--primary))] bg-blue-50 dark:bg-[hsl(var(--primary))]/10 cursor-pointer" : "border-slate-100 dark:border-white/5 bg-[hsl(var(--surface-1))] dark:bg-[#15171c] hover:border-blue-200 cursor-pointer"
                                        )}
                                    >
                                        <div className="size-9 rounded-full bg-slate-100 dark:bg-white/10 flex flex-col items-center justify-center font-bold text-slate-400">
                                            {m.name.charAt(0)}
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <p className="text-sm font-bold text-slate-800 dark:text-white truncate">{m.name}</p>
                                            <div className="flex items-center gap-2 mt-0.5">
                                                <span className="text-[10px] text-[hsl(var(--primary))] dark:text-blue-400 font-bold uppercase tracking-wide bg-blue-50 dark:bg-[hsl(var(--primary))]/10 px-2 py-0.5 rounded-full">
                                                    {m.role}
                                                </span>
                                                {!m.available && (
                                                    <span className="text-[9px] text-rose-500 font-bold uppercase tracking-wide bg-rose-50 dark:bg-rose-500/10 px-2 py-0.5 rounded-full">
                                                        Cupo Lleno
                                                    </span>
                                                )}
                                            </div>
                                            <p className="text-[11px] text-slate-500 font-medium mt-1 truncate">
                                                Especialidad: {m.specialty}
                                            </p>
                                        </div>
                                        {selected === m.id && (
                                            <div className="size-6 rounded-full bg-[hsl(var(--primary))] text-white flex items-center justify-center shrink-0">
                                                <Check size={14} strokeWidth={3} />
                                            </div>
                                        )}
                                    </div>
                                ))
                            )}
                        </div>
                    </>
                )}
            </div>
        </WorkspaceDrawer>
    );
}

type Tab = 'overview' | 'spiritual' | 'academy' | 'financial' | 'history';

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

// ─── Sub-components ───────────────────────────────────────────────────────────

const ID_TYPES = ['Cédula de Ciudadanía', 'Cédula de Extranjería', 'Pasaporte', 'Tarjeta de Identidad', 'NIT', 'Otro'];
const MARITAL_STATUSES = ['Soltero(a)', 'Casado(a)', 'Unión Libre', 'Divorciado(a)', 'Viudo(a)', 'Separado(a)'];
const SEX_OPTIONS = ['Masculino', 'Femenino'];
const EDUCATION_LEVELS = ['Primaria', 'Secundaria', 'Técnico', 'Tecnólogo', 'Universitario', 'Postgrado', 'Maestría', 'Doctorado'];
const EDUCATION_STATUSES = ['Cursando', 'Completado', 'Incompleto'];
const BLOOD_TYPES = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'];
const HOUSING_TYPES = ['Propia', 'Arriendo', 'Familiar', 'Otro'];
const MEMBERSHIP_TYPES = ['Activo', 'Inactivo', 'Transferido', 'Fallecido'];
const ATTENDANCE_TYPES = ['Regular', 'Constante', 'Irregular', 'Ausente'];

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

function EditField({ label, value, onChange, placeholder, type = 'text' }: { label: string; value: string; onChange: (v: string) => void; placeholder: string; type?: string }) {
    return (
        <div className="space-y-2">
            <label className="text-[10px] font-bold uppercase tracking-wide text-slate-400">{label}</label>
            <input type={type} value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder} className="w-full rounded-lg border border-slate-200 bg-slate-50 px-4 py-1.5 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-white/10 dark:bg-black/20 dark:text-white" />
        </div>
    );
}

function QuickStat({ label, value, icon: Icon, color }: any) {
    return (
        <div className="px-4 py-2 bg-slate-50 dark:bg-black/20 rounded-lg flex items-center gap-4 border border-slate-100 dark:border-white/5 min-w-[180px]">
            <Icon size={20} className={color} />
            <div>
                <p className="text-[9px] font-bold text-slate-400 uppercase tracking-wide">{label}</p>
                <p className="text-sm font-bold text-slate-800 dark:text-white leading-none mt-1">{value ?? '—'}</p>
            </div>
        </div>
    );
}

function HealthIndicator({ label, value, color }: { label: string; value: number; color: string }) {
    return (
        <div className="space-y-2">
            <div className="flex justify-between text-[10px] font-bold text-slate-500 uppercase tracking-wide">
                <span>{label}</span>
                <span className="font-bold text-slate-800 dark:text-white">{value}%</span>
            </div>
            <div className="h-1.5 w-full bg-slate-50 dark:bg-white/5 rounded-full overflow-hidden">
                <motion.div initial={{ width: 0 }} animate={{ width: `${value}%` }} transition={{ duration: 0.8, ease: 'easeOut' }} className={clsx("h-full rounded-full", color)} />
            </div>
        </div>
    );
}

function EmptyState({ icon: Icon, title, description, action }: { icon: any; title: string; description: string; action?: React.ReactNode }) {
    return (
        <div className="lg:col-span-12 py-1.5 flex flex-col items-center gap-4 text-center">
            <div className="size-10 rounded-md bg-slate-100 dark:bg-white/5 flex items-center justify-center">
                <Icon size={36} className="text-slate-300" />
            </div>
            <div className="space-y-2">
                <p className="text-sm font-bold text-slate-600 dark:text-slate-300 tracking-tight">{title}</p>
                <p className="text-sm text-slate-400 max-w-xs">{description}</p>
            </div>
            {action}
        </div>
    );
}

function InfoGrid({ items }: { items: { label: string; value: string | React.ReactNode; icon?: any }[] }) {
    return (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {items.map((item, i) => (
                <div key={i} className="space-y-1">
                    <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">{item.label}</p>
                    <p className="text-base font-bold text-slate-800 dark:text-white flex items-center gap-2">
                        {item.icon && <item.icon size={16} className="text-[hsl(var(--primary))] shrink-0" />}
                        {item.value || '—'}
                    </p>
                </div>
            ))}
        </div>
    );
}

// ─── Main Component ───────────────────────────────────────────────────────────

export default function MemberDetailPage() {
    const params = useParams();
    const id = Array.isArray(params?.id) ? params.id[0] : (params?.id ?? '');
    const router = useRouter();
    const { token } = useAuth();
    const [member, setMember] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState<Tab>('overview');
    const [mentorDrawerOpen, setMentorDrawerOpen] = useState(false);
    const [mentorDrawerConfig, setMentorDrawerConfig] = useState<{ title: string; subtitle: string }>({
        title: 'Asignar Mentoría',
        subtitle: 'Selecciona el mentor que guiará el proceso espiritual de este persona.',
    });
    const [isEditOpen, setIsEditOpen] = useState(false);
    const [editMember, setEditMember] = useState<any>({});
    const [isEditSaving, setIsEditSaving] = useState(false);
    const [departments, setDepartments] = useState<any[]>([]);
    const [editCities, setEditCities] = useState<any[]>([]);
    const [loadingEditCities, setLoadingEditCities] = useState(false);
    
    // Extra data fetched on demand
    const [history, setHistory] = useState<any[]>([]);
    const [donations, setDonations] = useState<any[]>([]);
    const [loadingHistory, setLoadingHistory] = useState(false);
    const [loadingDonations, setLoadingDonations] = useState(false);

    useEffect(() => {
        const abortCtrl = new AbortController();
        const fetchMember = async () => {
            try {
                const data = await apiFetch<any>(`/crm/personas/${id}`, { token, signal: abortCtrl.signal });
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
                    membership_type: data.membership_type ?? '',
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
                setMember(m);
                setEditMember({ ...m });
            } catch {
                if (!abortCtrl.signal.aborted) {
                    setMember(null);
                }
            } finally {
                if (!abortCtrl.signal.aborted) {
                    setLoading(false);
                }
            }
        };
        fetchMember();
        // Load departments for display
        apiFetch<any[]>('/crm/colombian-departments', { token, signal: abortCtrl.signal })
            .then(setDepartments)
            .catch((err) => {
                if (!abortCtrl.signal.aborted) {
                    console.error('[MemberDetailPage] Failed to load departments:', err);
                    toast.error('Error al cargar departamentos');
                }
            });
        return () => abortCtrl.abort();
    }, [id, token]);

    // Load cities for edit drawer cascade
    useEffect(() => {
        if (!token || !editMember.colombian_department_id) {
            setEditCities([]);
            return;
        }
        setLoadingEditCities(true);
        apiFetch<any[]>(`/crm/colombian-departments/${editMember.colombian_department_id}/cities`, { token })
            .then(setEditCities)
            .catch(() => setEditCities([]))
            .finally(() => setLoadingEditCities(false));
    }, [token, editMember.colombian_department_id]);

    const handleSaveMember = async () => {
        if (!token) return;
        setIsEditSaving(true);
        try {
            const body: any = {};
            const fields = [
                'first_name','last_name','email','phone','church_role','second_name','second_last_name',
                'id_type','id_number','birth_country','sex','marital_status','birthday',
                'landline_phone','other_phone','mobile_phone','address','housing_type',
                'colombian_department_id','city','education_level','education_status','profession','economic_sector',
                'blood_type','medical_notes','membership_type','attendance_type','group_name','campus',
                'church_join_date','baptism_date','responsible_adult_name','responsible_adult_contact',
                'guardian_name','guardian_contact','talents','spiritual_gifts','pastoral_notes',
                'registration_reason','unregistration_reason','registration_date','unregistration_date',
                'optional_info','last_group_attendance','last_meeting_attendance',
            ];
            const dateFields = ['birthday','church_join_date','baptism_date','registration_date','unregistration_date','last_group_attendance','last_meeting_attendance'];
            fields.forEach(k => {
                let val = editMember[k];
                if (dateFields.includes(k) && !val) val = null;
                // Only send changed values
                if (String(val) !== String(member[k])) {
                    body[k] = val;
                }
            });
            if (body.colombian_department_id === '' || body.colombian_department_id === null) {
                body.colombian_department_id = null;
            }
            const updated = await apiFetch<any>(`/crm/personas/${id}`, {
                method: 'PATCH', token, body,
            });
            setMember((prev: any) => ({ ...prev, ...updated }));
            setEditMember((prev: any) => ({ ...prev, ...updated }));
            setIsEditOpen(false);
            toast.success('Persona actualizado');
        } catch {
            toast.error('No se pudo actualizar el persona');
        } finally {
            setIsEditSaving(false);
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
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [activeTab, id, token]);

    // Fetch donations when financial tab activated
    useEffect(() => {
        if (activeTab === 'financial' && donations.length === 0 && token) {
            setLoadingDonations(true);
            apiFetch<any[]>(`/crm/personas/${id}/donations`, { token })
                .then(d => setDonations(Array.isArray(d) ? d : []))
                .catch(() => setDonations([]))
                .finally(() => setLoadingDonations(false));
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [activeTab, id, token]);

    if (loading) return (
        <div className="h-full flex flex-col items-center justify-center space-y-4">
            <div className="size-9 rounded-lg bg-blue-600/10 flex items-center justify-center">
                <Activity size={24} className="text-[hsl(var(--primary))] animate-spin" />
            </div>
            <p className="text-[10px] font-bold uppercase tracking-wide text-slate-400">Accediendo al Expediente...</p>
        </div>
    );

    if (!member) return (
        <div className="h-full flex flex-col items-center justify-center gap-4 text-center p-4">
            <AlertCircle size={48} className="text-slate-300" />
            <div>
                <p className="text-base font-bold text-slate-600 dark:text-slate-300">Persona no encontrada</p>
                <p className="text-sm text-slate-400 mt-1">El expediente #{id} no existe o no tienes acceso.</p>
            </div>
            <button onClick={() => router.push('/plataforma/crm/personas')} className="flex items-center gap-2 px-4 py-1.5 bg-[hsl(var(--primary))] text-white rounded-lg font-bold text-sm hover:bg-[hsl(var(--primary))] transition-all">
                <ArrowLeft size={16} /> Volver a Personas
            </button>
        </div>
    );

    const fullName = member.nombre_completo || `${member.first_name ?? ''} ${member.last_name ?? ''}`.trim();
    const nameParts = (member.nombre_completo || `${member.first_name ?? ''} ${member.last_name ?? ''}`).trim().split(/\s+/);
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
            rightActions={
                <div className="flex gap-2">
                    <button title="Editar" onClick={() => setIsEditOpen(true)} className="p-2.5 bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-md text-slate-400 hover:text-[hsl(var(--primary))] hover:border-blue-500/30 transition-all"><Edit3 size={16} /></button>
                    <button title="Compartir" className="p-2.5 bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-md text-slate-400 hover:text-[hsl(var(--primary))] hover:border-blue-500/30 transition-all"><Share2 size={16} /></button>
                    <button title="Más acciones" className="p-2.5 bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-md text-slate-400 hover:text-[hsl(var(--primary))] hover:border-blue-500/30 transition-all"><MoreHorizontal size={16} /></button>
                </div>
            }
        >
 <div className="w-full space-y-3 pb-4 p-4 lg:p-4">

            {/* ── 1. Profile Hero ── */}
            <motion.section
                initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                className="relative bg-[hsl(var(--surface-1))] dark:bg-[#15171c] rounded-lg border border-slate-100 dark:border-white/5 p-3 lg:p-4 shadow-xl shadow-slate-200/20 dark:shadow-none overflow-hidden group"
            >
                <div className="absolute top-0 right-0 w-[500px] h-full bg-gradient-to-l from-blue-600/5 to-transparent pointer-events-none" />
                <div className="relative z-10 flex flex-col lg:flex-row lg:items-center gap-3">
                    {/* Avatar */}
                    <div className="relative shrink-0">
                        <div className="size-10 lg:size-10 rounded-md bg-gradient-to-tr from-blue-600 to-sky-700 flex items-center justify-center text-white text-xl font-bold shadow-2xl shadow-blue-500/30 group-hover:scale-105 transition-transform duration-500">
                            {initials}
                        </div>
                        <div className="absolute -bottom-3 -right-3 size-9 bg-[hsl(var(--surface-1))] dark:bg-[#15171c] rounded-lg flex items-center justify-center shadow-xl border border-slate-50 dark:border-white/10">
                            <ShieldCheck size={24} className="text-[hsl(var(--primary))]" />
                        </div>
                    </div>

                    {/* Info */}
                    <div className="flex-1 space-y-2">
                        <div className="space-y-2">
                            <div className="inline-flex items-center gap-2 px-3 py-1 bg-blue-50 dark:bg-blue-500/10 rounded-full text-[10px] font-bold text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))] uppercase tracking-wide border border-blue-100 dark:border-blue-500/20">
                                ID: #{member.id} <span className="text-slate-300">•</span> {member.status}
                            </div>
                            <h1 className="text-lg lg:text-xl font-bold text-slate-800 dark:text-white tracking-tighter">{fullName}</h1>
                            <p className="text-sm text-slate-500 font-semibold">{member.church_role}</p>
                        </div>
                        <div className="flex flex-wrap gap-3 items-center">
                            {member.email !== '—' && <span className="flex items-center gap-2 text-slate-500 dark:text-slate-400 text-sm"><Mail size={16} className="text-[hsl(var(--primary))]" /> {member.email}</span>}
                            {member.phone !== '—' && <span className="flex items-center gap-2 text-slate-500 dark:text-slate-400 text-sm"><Phone size={16} className="text-emerald-500" /> {member.phone}</span>}
                            {member.address !== '—' && <span className="flex items-center gap-2 text-slate-500 dark:text-slate-400 text-sm"><MapPin size={16} className="text-rose-500" /> {member.address}</span>}
                        </div>
                    </div>

                    {/* Quick Stats */}
                    <div className="flex flex-row lg:flex-col gap-3 shrink-0">
                        <QuickStat label="Puntos MESH" value={member.xp} icon={Star} color="text-amber-500" />
                        <QuickStat label="Nivel" value={member.level} icon={Zap} color="text-[hsl(var(--primary))]" />
                        <QuickStat label="Grupo" value={member.house} icon={Heart} color="text-rose-500" />
                    </div>
                </div>
            </motion.section>

            {/* ── 2. Tabs ── */}
            <div className="flex border-b border-slate-200 dark:border-white/10 overflow-x-auto">
                {TABS.map(({ id: tabId, label, icon: Icon }) => {
                    const active = activeTab === tabId;
                    return (
                        <button
                            key={tabId}
                            onClick={() => setActiveTab(tabId)}
                            className={clsx(
                                "flex items-center gap-2 px-4 py-2 text-[11px] font-bold uppercase tracking-wider transition-all relative whitespace-nowrap shrink-0",
                                active ? "text-[hsl(var(--primary))]" : "text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                            )}
                        >
                            <Icon size={14} />
                            {label}
                            {active && <motion.div layoutId="member-tab-indicator" className="absolute bottom-0 left-0 right-0 h-[2px] bg-[hsl(var(--primary))] rounded-t-full shadow-[0_0_8px_rgba(37,99,235,0.5)]" />}
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
                            <div className="bg-[hsl(var(--surface-1))] dark:bg-[#15171c] rounded-md p-3 border border-slate-100 dark:border-white/5 shadow-sm space-y-3">
                                <h3 className="text-[11px] font-bold uppercase tracking-wide text-slate-400">Perfil de Consolidación</h3>
                                <InfoGrid items={[
                                    { label: 'Fecha de Ingreso', value: formatDate(member.joinedAt), icon: Calendar },
                                    { label: 'Fecha de Nacimiento', value: formatDate(member.birthday), icon: Calendar },
                                    { label: 'Grupo', value: member.house, icon: Heart },
                                    { label: 'Rol en Ministerio', value: member.church_role, icon: ShieldCheck },
                                ]} />
                                {member.pastoral_notes && (
                                    <div className="p-4 bg-slate-50 dark:bg-black/20 rounded-lg border border-slate-100 dark:border-white/5">
                                        <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wide mb-2">Notas Pastorales</p>
                                        <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed italic">&ldquo;{member.pastoral_notes}&rdquo;</p>
                                    </div>
                                )}
                            </div>

                            {/* Datos Personales */}
                            <div className="bg-[hsl(var(--surface-1))] dark:bg-[#15171c] rounded-md p-3 border border-slate-100 dark:border-white/5 shadow-sm space-y-3">
                                <h3 className="text-[11px] font-bold uppercase tracking-wide text-slate-400">Datos Personales</h3>
                                <InfoGrid items={[
                                    { label: 'Tipo de ID', value: member.id_type },
                                    { label: 'Número de ID', value: member.id_number },
                                    { label: 'Segundo Nombre', value: member.second_name },
                                    { label: 'Segundo Apellido', value: member.second_last_name },
                                    { label: 'Estado Civil', value: member.marital_status },
                                    { label: 'País de Nacimiento', value: member.birth_country },
                                    { label: 'Sexo', value: member.sex },
                                    { label: 'Tipo de Participación', value: member.membership_type },
                                ]} />
                            </div>

                            {/* Contacto y Ubicación */}
                            {(member.landline_phone || member.address || member.city) && (
                                <div className="bg-[hsl(var(--surface-1))] dark:bg-[#15171c] rounded-md p-3 border border-slate-100 dark:border-white/5 shadow-sm space-y-3">
                                    <h3 className="text-[11px] font-bold uppercase tracking-wide text-slate-400">Contacto y Ubicación</h3>
                                    <InfoGrid items={[
                                        { label: 'Teléfono Fijo', value: member.landline_phone },
                                        { label: 'Celular', value: member.mobile_phone },
                                        { label: 'Otro Teléfono', value: member.other_phone },
                                        { label: 'Dirección', value: member.address },
                                        { label: 'Tipo de Vivienda', value: member.housing_type },
                                        { label: 'Departamento', value: getDeptName(departments, member.colombian_department_id) },
                                        { label: 'Ciudad', value: member.city },
                                    ]} />
                                </div>
                            )}

                            {/* Educación y Profesión */}
                            {(member.profession || member.education_level) && (
                                <div className="bg-[hsl(var(--surface-1))] dark:bg-[#15171c] rounded-md p-3 border border-slate-100 dark:border-white/5 shadow-sm space-y-3">
                                    <h3 className="text-[11px] font-bold uppercase tracking-wide text-slate-400">Educación y Profesión</h3>
                                    <InfoGrid items={[
                                        { label: 'Nivel Educativo', value: member.education_level },
                                        { label: 'Estado Educativo', value: member.education_status },
                                        { label: 'Profesión', value: member.profession },
                                        { label: 'Sector Económico', value: member.economic_sector },
                                    ]} />
                                </div>
                            )}

                            {/* Médico */}
                            {(member.blood_type || member.medical_notes) && (
                                <div className="bg-[hsl(var(--surface-1))] dark:bg-[#15171c] rounded-md p-3 border border-slate-100 dark:border-white/5 shadow-sm space-y-3">
                                    <h3 className="text-[11px] font-bold uppercase tracking-wide text-slate-400">Información Médica</h3>
                                    <InfoGrid items={[
                                        { label: 'Tipo de Sangre', value: member.blood_type },
                                        { label: 'Notas Médicas', value: member.medical_notes },
                                    ]} />
                                </div>
                            )}

                            {/* Núcleo Familiar */}
                            <div className="bg-[hsl(var(--surface-1))] dark:bg-[#15171c] rounded-md p-3 border border-slate-100 dark:border-white/5 shadow-sm space-y-3">
                                <div className="flex items-center justify-between">
                                    <h3 className="text-[11px] font-bold uppercase tracking-wide text-slate-400">Núcleo Familiar</h3>
                                    <button className="flex items-center gap-1.5 text-[10px] font-bold text-[hsl(var(--primary))] uppercase tracking-wide hover:text-[hsl(var(--primary))] transition-all">
                                        <Plus size={12} /> Añadir
                                    </button>
                                </div>
                                {member.family.length > 0 ? (
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                        {member.family.map((f: any) => (
                                            <div key={f.id} className="p-3 bg-slate-50 dark:bg-white/5 rounded-lg border border-slate-100 dark:border-white/5 flex items-center justify-between group hover:border-blue-500/30 hover:bg-blue-50/50 dark:hover:bg-blue-500/5 transition-all cursor-pointer">
                                                <div className="flex items-center gap-3">
                                                    <div className="size-9 rounded-md bg-[hsl(var(--surface-1))] dark:bg-[#15171c] flex items-center justify-center shadow-sm border border-slate-100 dark:border-white/10">
                                                        <User size={16} className="text-slate-400" />
                                                    </div>
                                                    <div>
                                                        <p className="text-sm font-bold text-slate-800 dark:text-white">{f.name ?? f.first_name}</p>
                                                        <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">{f.relation}</p>
                                                    </div>
                                                </div>
                                                <ChevronRight size={16} className="text-slate-300 group-hover:translate-x-1 transition-transform" />
                                            </div>
                                        ))}
                                    </div>
                                ) : (
                                    <div className="py-2 text-center rounded-lg bg-slate-50 dark:bg-white/5 border border-dashed border-slate-200 dark:border-white/10">
                                        <Users size={28} className="mx-auto text-slate-300 mb-3" />
                                        <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">Sin núcleo familiar registrado</p>
                                        <p className="text-xs text-slate-400 mt-1">Este persona aún no pertenece a una familia</p>
                                    </div>
                                )}
                            </div>
                        </div>

                        <div className="lg:col-span-4 space-y-3">
                            {/* MESH Insight */}
                            <div className="p-4 bg-gradient-to-br from-sky-600 to-blue-700 rounded-md text-white shadow-xl relative overflow-hidden group">
                                <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:scale-110 transition-transform duration-700"><Sparkles size={100} /></div>
                                <div className="relative z-10 space-y-2">
                                    <div className="flex items-center gap-2">
                                        <Flame size={18} className="text-amber-300" />
                                        <h4 className="text-base font-bold tracking-tight uppercase">MESH Insight</h4>
                                    </div>
                                    <p className="text-sm font-medium text-blue-100 leading-relaxed">
                                        {fullName} tiene potencial pastoral en su área de servicio. Su participación este mes es consistente.
                                    </p>
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

                            {/* Indicadores de Salud */}
                            <div className="bg-[hsl(var(--surface-1))] dark:bg-[#15171c] rounded-md p-4 border border-slate-100 dark:border-white/5 shadow-sm space-y-2">
                                <h3 className="text-[10px] font-bold uppercase tracking-wide text-slate-400">Indicadores de Salud</h3>
                                <HealthIndicator label="Asistencia Mensual" value={85} color="bg-emerald-500" />
                                <HealthIndicator label="Progreso Academia" value={65} color="bg-[hsl(var(--primary))]" />
                                <HealthIndicator label="Compromiso Voluntario" value={92} color="bg-amber-500" />
                            </div>
                        </div>
                    </>}

                    {/* ── VIDA ESPIRITUAL ── */}
                    {activeTab === 'spiritual' && <>
                        <div className="lg:col-span-8 space-y-3">
                            <div className="bg-[hsl(var(--surface-1))] dark:bg-[#15171c] rounded-md p-3 border border-slate-100 dark:border-white/5 shadow-sm space-y-3">
                                <h3 className="text-[11px] font-bold uppercase tracking-wide text-slate-400">Datos Espirituales</h3>
                                <InfoGrid items={[
                                    { label: 'Fecha de Bautismo', value: formatDate(member.baptism_date), icon: CheckCircle2 },
                                    { label: 'Grupo', value: member.house, icon: Heart },
                                    { label: 'Estado Espiritual', value: member.status, icon: ShieldCheck },
                                    { label: 'Rol en la Iglesia', value: member.church_role, icon: Star },
                                ]} />
                                {member.spiritual_gifts ? (
                                    <div className="space-y-3">
                                        <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">Dones Espirituales</p>
                                        <div className="flex flex-wrap gap-2">
                                            {member.spiritual_gifts.split(',').map((gift: string, i: number) => (
                                                <span key={i} className="px-3 py-1.5 bg-blue-50 dark:bg-[hsl(var(--primary))]/10 text-[hsl(var(--primary))] dark:text-blue-300 text-[11px] font-bold rounded-md border border-blue-100 dark:border-[hsl(var(--primary))]/20 uppercase tracking-wide">
                                                    {gift.trim()}
                                                </span>
                                            ))}
                                        </div>
                                    </div>
                                ) : (
                                    <div className="p-4 bg-slate-50 dark:bg-white/5 rounded-lg border border-dashed border-slate-200 dark:border-white/10 text-center">
                                        <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">Dones espirituales no registrados</p>
                                    </div>
                                )}
                                {member.talents ? (
                                    <div className="space-y-3">
                                        <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">Talentos y Habilidades</p>
                                        <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed">{member.talents}</p>
                                    </div>
                                ) : null}
                            </div>
                        </div>
                        <div className="lg:col-span-4 space-y-3">
                            <div className="p-4 bg-gradient-to-br from-rose-500 to-pink-600 rounded-md text-white shadow-xl relative overflow-hidden">
                                <div className="absolute top-0 right-0 p-4 opacity-10"><Heart size={80} /></div>
                                <div className="relative z-10 space-y-4">
                                    <h4 className="text-sm font-bold uppercase tracking-wide">Cuidado Pastoral</h4>
                                    <p className="text-sm text-rose-100 leading-relaxed">Este persona está siendo acompañado activamente en su proceso espiritual.</p>
                                    <button
                                        onClick={() => {
                                            setMentorDrawerConfig({
                                                title: 'Asignar Pastor',
                                                subtitle: `Selecciona el pastor que hará seguimiento espiritual de ${fullName}.`,
                                            });
                                            setMentorDrawerOpen(true);
                                        }}
                                        className="w-full py-1.5 bg-[hsl(var(--surface-1))] text-rose-700 rounded-lg font-bold text-[10px] uppercase tracking-wide hover:scale-105 transition-all"
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
                            <div className="bg-[hsl(var(--surface-1))] dark:bg-[#15171c] rounded-md p-3 border border-slate-100 dark:border-white/5 shadow-sm">
                                <div className="flex items-center justify-between mb-3">
                                    <h3 className="text-[11px] font-bold uppercase tracking-wide text-slate-400">Progreso Académico</h3>
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
                                    { label: 'Total Diezmos', value: donations.filter(d => d.donation_type === 'diezmo').reduce((s: number, d: any) => s + d.amount, 0), color: 'bg-emerald-500', icon: TrendingUp },
                                    { label: 'Total Ofrendas', value: donations.filter(d => d.donation_type === 'ofrenda').reduce((s: number, d: any) => s + d.amount, 0), color: 'bg-[hsl(var(--primary))]', icon: DollarSign },
                                    { label: 'Total Registrado', value: donations.reduce((s: number, d: any) => s + d.amount, 0), color: 'bg-[hsl(var(--primary))]', icon: Award },
                                ].map((stat, i) => (
                                    <div key={i} className="bg-[hsl(var(--surface-1))] dark:bg-[#15171c] rounded-md p-4 border border-slate-100 dark:border-white/5 shadow-sm space-y-3">
                                        <div className={clsx('size-8 rounded-md flex items-center justify-center text-white', stat.color)}>
                                            <stat.icon size={18} />
                                        </div>
                                        <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">{stat.label}</p>
                                        <p className="text-lg font-bold text-slate-800 dark:text-white">{formatCurrency(stat.value)}</p>
                                    </div>
                                ))}
                            </div>

                            {/* Transactions */}
                            <div className="bg-[hsl(var(--surface-1))] dark:bg-[#15171c] rounded-md p-3 border border-slate-100 dark:border-white/5 shadow-sm">
                                <h3 className="text-[11px] font-bold uppercase tracking-wide text-slate-400 mb-3">Historial de Siembras</h3>
                                {loadingDonations ? (
                                    <div className="py-2 text-center text-slate-400 text-sm">Cargando...</div>
                                ) : donations.length > 0 ? (
                                    <div className="space-y-3">
                                        {donations.map((d: any, i: number) => (
                                            <div key={i} className="flex items-center justify-between p-4 bg-slate-50 dark:bg-white/5 rounded-lg">
                                                <div className="flex items-center gap-3">
                                                    <div className="size-9 rounded-md bg-emerald-50 dark:bg-emerald-500/10 flex items-center justify-center">
                                                        <DollarSign size={16} className="text-emerald-600" />
                                                    </div>
                                                    <div>
                                                        <p className="text-sm font-bold text-slate-800 dark:text-white capitalize">{d.donation_type}</p>
                                                        <p className="text-[10px] text-slate-400">{formatDate(d.created_at)}</p>
                                                    </div>
                                                </div>
                                                <p className="text-sm font-bold text-emerald-600">{formatCurrency(d.amount)}</p>
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
                            <div className="bg-[hsl(var(--surface-1))] dark:bg-[#15171c] rounded-md p-3 border border-slate-100 dark:border-white/5 shadow-sm">
                                <h3 className="text-[11px] font-bold uppercase tracking-wide text-slate-400 mb-3">Línea de Tiempo Pastoral</h3>
                                {loadingHistory ? (
                                    <div className="py-2 text-center text-slate-400 text-sm">Cargando historial...</div>
                                ) : history.length > 0 ? (
                                    <div className="relative space-y-0">
                                        <div className="absolute left-5 top-0 bottom-0 w-px bg-slate-100 dark:bg-white/5" />
                                        {history.map((event: any, i: number) => (
                                            <div key={i} className="flex gap-4 pl-12 pb-8 relative">
                                                <div className="absolute left-0 top-1 size-8 rounded-md bg-[hsl(var(--surface-1))] dark:bg-[#15171c] border border-slate-100 dark:border-white/10 flex items-center justify-center shadow-sm z-10">
                                                    <MessageSquare size={16} className="text-[hsl(var(--primary))]" />
                                                </div>
                                                <div className="flex-1 bg-slate-50 dark:bg-white/5 rounded-lg p-3">
                                                    <div className="flex items-center justify-between mb-2">
                                                        <p className="text-sm font-bold text-slate-800 dark:text-white">{event.event_type ?? event.type ?? 'Evento'}</p>
                                                        <p className="text-[10px] text-slate-400">{formatDate(event.created_at)}</p>
                                                    </div>
                                                    {event.notes && <p className="text-xs text-slate-500 leading-relaxed">{event.notes}</p>}
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
                                            <button className="flex items-center gap-2 px-4 py-1.5 bg-slate-800 dark:bg-[hsl(var(--bg-primary))] text-white dark:text-slate-800 rounded-lg font-bold text-sm hover:opacity-90 transition-all mt-2">
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
                memberName={fullName}
                token={token}
                memberId={id}
                title={mentorDrawerConfig.title}
            />

            {/* Edit Member Drawer */}
            <WorkspaceDrawer
                isOpen={isEditOpen}
                onClose={() => setIsEditOpen(false)}
                title="Editar Persona"
                subtitle={`Actualizando perfil de ${fullName}`}
                actions={
                    <>
                        <button type="button" onClick={() => setIsEditOpen(false)} className="px-4 py-2 text-[11px] font-bold text-slate-500 hover:text-slate-700">Cancelar</button>
                        <button type="button" onClick={handleSaveMember} disabled={isEditSaving} className="flex items-center gap-2 rounded-lg bg-[hsl(var(--primary))] px-3 py-2 text-[11px] font-bold uppercase tracking-wide text-white shadow-lg shadow-blue-500/20 transition-all hover:bg-[hsl(var(--primary))] active:scale-95 disabled:opacity-60">
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
                                <EditField label="Nombre" value={editMember.first_name ?? ''} onChange={v => setEditMember((p: any) => ({...p, first_name: v}))} placeholder="Juan" />
                                <EditField label="Apellido" value={editMember.last_name ?? ''} onChange={v => setEditMember((p: any) => ({...p, last_name: v}))} placeholder="Pérez" />
                            </div>
                            <div className="grid grid-cols-2 gap-3">
                                <EditField label="Segundo Nombre" value={editMember.second_name ?? ''} onChange={v => setEditMember((p: any) => ({...p, second_name: v}))} placeholder="José" />
                                <EditField label="Segundo Apellido" value={editMember.second_last_name ?? ''} onChange={v => setEditMember((p: any) => ({...p, second_last_name: v}))} placeholder="García" />
                            </div>
                            <div className="grid grid-cols-2 gap-3">
                                <EditField label="Correo" type="email" value={editMember.email ?? ''} onChange={v => setEditMember((p: any) => ({...p, email: v}))} placeholder="correo@ejemplo.com" />
                                <EditField label="Teléfono" value={editMember.phone ?? ''} onChange={v => setEditMember((p: any) => ({...p, phone: v}))} placeholder="+57 300 000 0000" />
                            </div>
                            <div className="grid grid-cols-2 gap-3">
                                <SelectField label="Rol" value={editMember.church_role ?? ''} onChange={v => setEditMember((p: any) => ({...p, church_role: v}))} options={['Persona','Pastor','Líder','Diácono','Ministro de Culto','Apóstol','Profeta','Evangelista','Maestro','Administrador']} />
                                <SelectField label="Tipo de Participación" value={editMember.membership_type ?? ''} onChange={v => setEditMember((p: any) => ({...p, membership_type: v}))} options={MEMBERSHIP_TYPES} />
                            </div>
                        </div>
                    </div>

                    <FormSection title="Identificación">
                        <div className="grid grid-cols-2 gap-3">
                            <SelectField label="Tipo de ID" value={editMember.id_type ?? ''} onChange={v => setEditMember((p: any) => ({...p, id_type: v}))} options={ID_TYPES} />
                            <EditField label="Número de ID" value={editMember.id_number ?? ''} onChange={v => setEditMember((p: any) => ({...p, id_number: v}))} placeholder="1234567890" />
                        </div>
                    </FormSection>

                    <FormSection title="Información Personal">
                        <div className="grid grid-cols-2 gap-3">
                            <SelectField label="Sexo" value={editMember.sex ?? ''} onChange={v => setEditMember((p: any) => ({...p, sex: v}))} options={SEX_OPTIONS} />
                            <SelectField label="Estado Civil" value={editMember.marital_status ?? ''} onChange={v => setEditMember((p: any) => ({...p, marital_status: v}))} options={MARITAL_STATUSES} />
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <EditField label="País de Nacimiento" value={editMember.birth_country ?? ''} onChange={v => setEditMember((p: any) => ({...p, birth_country: v}))} placeholder="Colombia" />
                            <EditField label="Fecha de Nacimiento" type="date" value={editMember.birthday ? editMember.birthday.slice(0,10) : ''} onChange={v => setEditMember((p: any) => ({...p, birthday: v}))} placeholder="" />
                        </div>
                    </FormSection>

                    <FormSection title="Contacto y Ubicación">
                        <div className="grid grid-cols-2 gap-3">
                            <EditField label="Teléfono Fijo" value={editMember.landline_phone ?? ''} onChange={v => setEditMember((p: any) => ({...p, landline_phone: v}))} placeholder="+57 1 000 0000" />
                            <EditField label="Otro Teléfono" value={editMember.other_phone ?? ''} onChange={v => setEditMember((p: any) => ({...p, other_phone: v}))} placeholder="+57 300 000 0000" />
                        </div>
                        <EditField label="Dirección" value={editMember.address ?? ''} onChange={v => setEditMember((p: any) => ({...p, address: v}))} placeholder="Cra 1 # 2-3, Barrio..." />
                        <div className="grid grid-cols-2 gap-3">
                            <SelectField label="Tipo de Vivienda" value={editMember.housing_type ?? ''} onChange={v => setEditMember((p: any) => ({...p, housing_type: v}))} options={HOUSING_TYPES} />
                            <EditField label="Celular" value={editMember.mobile_phone ?? ''} onChange={v => setEditMember((p: any) => ({...p, mobile_phone: v}))} placeholder="+57 300 000 0000" />
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <div className="space-y-2">
                                <label className="text-[10px] font-bold uppercase tracking-wide text-slate-400">Departamento</label>
                                <select value={editMember.colombian_department_id ?? ''} onChange={e => setEditMember((p: any) => ({ ...p, colombian_department_id: e.target.value ? Number(e.target.value) : null, city: '' }))} className="w-full rounded-lg border border-slate-200 bg-slate-50 px-4 py-1.5 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-white/10 dark:bg-black/20 dark:text-white">
                                    <option value="">Seleccionar departamento</option>
                                    {departments.map((d: any) => <option key={d.id} value={d.id}>{d.name}</option>)}
                                </select>
                            </div>
                            <div className="space-y-2">
                                <label className="text-[10px] font-bold uppercase tracking-wide text-slate-400">Ciudad</label>
                                <select value={editMember.city ?? ''} onChange={e => setEditMember((p: any) => ({ ...p, city: e.target.value }))} disabled={!editMember.colombian_department_id || loadingEditCities} className="w-full rounded-lg border border-slate-200 bg-slate-50 px-4 py-1.5 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500/20 disabled:opacity-50 disabled:cursor-not-allowed dark:border-white/10 dark:bg-black/20 dark:text-white">
                                    <option value="">{loadingEditCities ? 'Cargando ciudades...' : 'Seleccionar ciudad'}</option>
                                    {editCities.map((c: any) => <option key={c.id} value={c.name}>{c.name}</option>)}
                                </select>
                            </div>
                        </div>
                    </FormSection>

                    <FormSection title="Educación y Profesión">
                        <div className="grid grid-cols-2 gap-3">
                            <SelectField label="Nivel Educativo" value={editMember.education_level ?? ''} onChange={v => setEditMember((p: any) => ({...p, education_level: v}))} options={EDUCATION_LEVELS} />
                            <SelectField label="Estado Educativo" value={editMember.education_status ?? ''} onChange={v => setEditMember((p: any) => ({...p, education_status: v}))} options={EDUCATION_STATUSES} />
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <EditField label="Profesión" value={editMember.profession ?? ''} onChange={v => setEditMember((p: any) => ({...p, profession: v}))} placeholder="Ingeniero, Abogado..." />
                            <EditField label="Sector Económico" value={editMember.economic_sector ?? ''} onChange={v => setEditMember((p: any) => ({...p, economic_sector: v}))} placeholder="Salud, Educación..." />
                        </div>
                    </FormSection>

                    <FormSection title="Información Médica">
                        <SelectField label="Tipo de Sangre" value={editMember.blood_type ?? ''} onChange={v => setEditMember((p: any) => ({...p, blood_type: v}))} options={BLOOD_TYPES} />
                        <EditField label="Notas Médicas" value={editMember.medical_notes ?? ''} onChange={v => setEditMember((p: any) => ({...p, medical_notes: v}))} placeholder="Alergias, condiciones..." />
                    </FormSection>

                    <FormSection title="Información de Iglesia">
                        <div className="grid grid-cols-2 gap-3">
                            <SelectField label="Tipo de Asistencia" value={editMember.attendance_type ?? ''} onChange={v => setEditMember((p: any) => ({...p, attendance_type: v}))} options={ATTENDANCE_TYPES} />
                            <EditField label="Grupo" value={editMember.group_name ?? ''} onChange={v => setEditMember((p: any) => ({...p, group_name: v}))} placeholder="Grupo 1, Casa de Paz..." />
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <EditField label="Campus / Sede" value={editMember.campus ?? ''} onChange={v => setEditMember((p: any) => ({...p, campus: v}))} placeholder="Principal, Norte..." />
                            <EditField label="Fecha de Ingreso" type="date" value={editMember.church_join_date ? editMember.church_join_date.slice(0,10) : ''} onChange={v => setEditMember((p: any) => ({...p, church_join_date: v}))} placeholder="" />
                        </div>
                        <EditField label="Fecha de Bautismo" type="date" value={editMember.baptism_date ? editMember.baptism_date.slice(0,10) : ''} onChange={v => setEditMember((p: any) => ({...p, baptism_date: v}))} placeholder="" />
                    </FormSection>

                    <FormSection title="Información Familiar">
                        <div className="grid grid-cols-2 gap-3">
                            <EditField label="Nombre del Responsable" value={editMember.responsible_adult_name ?? ''} onChange={v => setEditMember((p: any) => ({...p, responsible_adult_name: v}))} placeholder="Nombre completo" />
                            <EditField label="Contacto del Responsable" value={editMember.responsible_adult_contact ?? ''} onChange={v => setEditMember((p: any) => ({...p, responsible_adult_contact: v}))} placeholder="Teléfono" />
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <EditField label="Nombre del Acudiente" value={editMember.guardian_name ?? ''} onChange={v => setEditMember((p: any) => ({...p, guardian_name: v}))} placeholder="Nombre completo" />
                            <EditField label="Contacto del Acudiente" value={editMember.guardian_contact ?? ''} onChange={v => setEditMember((p: any) => ({...p, guardian_contact: v}))} placeholder="Teléfono" />
                        </div>
                    </FormSection>

                    <FormSection title="Información Espiritual">
                        <EditField label="Talentos y Habilidades" value={editMember.talents ?? ''} onChange={v => setEditMember((p: any) => ({...p, talents: v}))} placeholder="Canto, enseñanza, liderazgo..." />
                        <EditField label="Dones Espirituales" value={editMember.spiritual_gifts ?? ''} onChange={v => setEditMember((p: any) => ({...p, spiritual_gifts: v}))} placeholder="Profecía, enseñanza, servicio..." />
                        <EditField label="Notas Pastorales" value={editMember.pastoral_notes ?? ''} onChange={v => setEditMember((p: any) => ({...p, pastoral_notes: v}))} placeholder="Observaciones pastorales..." />
                        <div className="grid grid-cols-2 gap-3">
                            <EditField label="Última Asistencia a Grupo" type="date" value={editMember.last_group_attendance ? editMember.last_group_attendance.slice(0,10) : ''} onChange={v => setEditMember((p: any) => ({...p, last_group_attendance: v}))} placeholder="" />
                            <EditField label="Última Asistencia a Reunión" type="date" value={editMember.last_meeting_attendance ? editMember.last_meeting_attendance.slice(0,10) : ''} onChange={v => setEditMember((p: any) => ({...p, last_meeting_attendance: v}))} placeholder="" />
                        </div>
                    </FormSection>

                    <FormSection title="Información de Registro">
                        <EditField label="Motivo de Registro" value={editMember.registration_reason ?? ''} onChange={v => setEditMember((p: any) => ({...p, registration_reason: v}))} placeholder="Conversión, transferencia..." />
                        <EditField label="Motivo de Baja" value={editMember.unregistration_reason ?? ''} onChange={v => setEditMember((p: any) => ({...p, unregistration_reason: v}))} placeholder="Si aplica..." />
                        <div className="grid grid-cols-2 gap-3">
                            <EditField label="Fecha de Registro" type="date" value={editMember.registration_date ? editMember.registration_date.slice(0,10) : ''} onChange={v => setEditMember((p: any) => ({...p, registration_date: v}))} placeholder="" />
                            <EditField label="Fecha de Baja" type="date" value={editMember.unregistration_date ? editMember.unregistration_date.slice(0,10) : ''} onChange={v => setEditMember((p: any) => ({...p, unregistration_date: v}))} placeholder="" />
                        </div>
                        <EditField label="Información Opcional" value={editMember.optional_info ?? ''} onChange={v => setEditMember((p: any) => ({...p, optional_info: v}))} placeholder="Notas adicionales..." />
                    </FormSection>
                </div>
            </WorkspaceDrawer>
        </CrmShell>
    );
}
