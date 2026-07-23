"use client";

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
    Calendar,
    Check,
    ChevronDown,
    Clock,
    Heart,
    History,
    Link2,
    Loader2,
    MessageSquare,
    Phone,
    Plus,
    Send,
    User,
    Users,
} from 'lucide-react';
import clsx from 'clsx';
import { useAuth } from '@/context/AuthContext';
import { useCrmAccess } from '@/hooks/useCrmAccess';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import CrmShell from '@/components/crm/CrmShell';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';

interface CallLog {
    id: number;
    outcome: string;
    notes: string | null;
    prayer_requests?: string | null;
    created_at: string;
    duration_seconds?: number;
}

const STAGES = ['new', 'call', 'visit', 'discipleship', 'consolidated', 'lost'];
const STAGE_LABELS: Record<string, string> = {
    new: 'Nuevo',
    call: 'Por llamar',
    visit: 'Visita',
    discipleship: 'Discipulado',
    consolidated: 'Consolidado',
    lost: 'Perdido',
};

const STAGE_BADGES: Record<string, string> = {
    new: 'bg-[hsl(var(--surface-2))] text-[hsl(var(--text-primary))] border-[hsl(var(--border))] dark:bg-white/5 dark:text-[hsl(var(--text-secondary))] dark:border-white/10',
    call: 'bg-warning-soft text-warning-text border-[hsl(var(--warning)/25%)] dark:bg-[hsl(var(--warning))]/10 dark:text-warning-text dark:border-[hsl(var(--warning)/100%)]/20',
    visit: 'bg-info-soft text-info-text border-[hsl(var(--info)/25%)] dark:bg-[hsl(var(--info))]/10 dark:text-info-text dark:border-[hsl(var(--info)/100%)]/20',
    discipleship: 'bg-info-soft text-info-text border-[hsl(var(--info)/25%)] dark:bg-[hsl(var(--info))]/10 dark:text-info-text dark:border-[hsl(var(--info)/100%)]/20',
    consolidated: 'bg-success-soft text-success-text border-[hsl(var(--success)/25%)] dark:bg-[hsl(var(--success))]/10 dark:text-success-text dark:border-[hsl(var(--success)/100%)]/20',
    lost: 'bg-danger-soft text-danger-text border-[hsl(var(--danger)/25%)] dark:bg-[hsl(var(--danger))]/10 dark:text-danger-text dark:border-[hsl(var(--danger)/100%)]/20',
};

function formatDate(value?: string | null) {
    if (!value) return 'Sin fecha';
    return new Date(value).toLocaleString('es-CO', {
        day: '2-digit',
        month: 'short',
        hour: '2-digit',
        minute: '2-digit',
    });
}

export default function LeadDetail() {
    const { token, loading: authLoading } = useAuth();
    const { canEditCrm } = useCrmAccess();
    const { addToast } = useToast();
    const router = useRouter();
    const params = useParams<{ id: string }>();
    const leadId = params?.id ?? '';

    const [activeTab, setActiveTab] = useState<'history' | 'notes'>('history');
    const [lead, setLead] = useState<any>(null);
    const [callLogs, setCallLogs] = useState<CallLog[]>([]);
    const [counselingSessions, setCounselingSessions] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [reloadKey, setReloadKey] = useState(0);

    const [isCallDrawerOpen, setIsCallDrawerOpen] = useState(false);
    const [isSavingCall, setIsSavingCall] = useState(false);
    const [callForm, setCallForm] = useState({ outcome: 'Exitoso', notes: '', prayer_requests: '' });

    const [noteText, setNoteText] = useState('');
    const [isSavingNote, setIsSavingNote] = useState(false);
    const [isStageOpen, setIsStageOpen] = useState(false);
    const [isSavingStage, setIsSavingStage] = useState(false);

    const fetchLeadData = useCallback(async () => {
        if (authLoading) return;
        if (!leadId) {
            setLoading(false);
            setError('No se encontró el contacto.');
            return;
        }
        if (!token) {
            setLoading(false);
            setError('Debes iniciar sesión para ver este contacto.');
            return;
        }
        setLoading(true);
        try {
            setError(null);
            const [leadData, logsData] = await Promise.allSettled([
                apiFetch(`/crm/casos/${leadId}`, { token, cache: 'no-store' }),
                apiFetch<CallLog[]>(`/crm/casos/${leadId}/calls`, { token, cache: 'no-store' }),
            ]);
            if (leadData.status === 'fulfilled') {
                const leadValue = leadData.value as { persona_id?: string | null };
                setLead(leadValue);
                if (leadValue.persona_id) {
                    try {
                        const counselingData = await apiFetch(`/crm/counseling/lead/${leadValue.persona_id}`, {
                            token,
                            cache: 'no-store',
                        });
                        setCounselingSessions(Array.isArray(counselingData) ? counselingData : []);
                    } catch {
                        setCounselingSessions([]);
                    }
                } else {
                    setCounselingSessions([]);
                }
            } else {
                setLead(null);
                setCounselingSessions([]);
                setError('No se pudo cargar el contacto.');
            }
            setCallLogs(logsData.status === 'fulfilled' && Array.isArray(logsData.value) ? logsData.value : []);
        } catch (err) {
            setLead(null);
            setCallLogs([]);
            setCounselingSessions([]);
            setError('No se pudo cargar el contacto.');
            addToast('No se pudo cargar el contacto', 'error');
        } finally {
            setLoading(false);
        }
    }, [addToast, authLoading, leadId, token]);

    useEffect(() => { fetchLeadData(); }, [fetchLeadData, reloadKey]);

    const handleStageChange = async (newStage: string) => {
        setIsStageOpen(false);
        setIsSavingStage(true);
        try {
            await apiFetch(`/crm/casos/${leadId}`, {
                method: 'PATCH',
                token,
                body: { stage: newStage },
            });
            setLead((prev: any) => ({ ...prev, stage: newStage }));
            addToast(`Etapa actualizada a ${STAGE_LABELS[newStage]}`, 'success');
        } catch {
            addToast('Error al actualizar etapa', 'error');
        } finally {
            setIsSavingStage(false);
        }
    };

    const handleRegisterCall = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsSavingCall(true);
        try {
            await apiFetch(`/crm/casos/${leadId}/calls`, {
                method: 'POST',
                token,
                body: callForm,
            });
            addToast('Interacción registrada', 'success');
            setIsCallDrawerOpen(false);
            setCallForm({ outcome: 'Exitoso', notes: '', prayer_requests: '' });
            fetchLeadData();
        } catch {
            addToast('Error al registrar la interacción', 'error');
        } finally {
            setIsSavingCall(false);
        }
    };

    const handleSaveNote = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!noteText.trim()) return;
        setIsSavingNote(true);
        try {
            await apiFetch(`/crm/casos/${leadId}/calls`, {
                method: 'POST',
                token,
                body: { outcome: 'Nota', notes: noteText.trim(), prayer_requests: '' },
            });
            setNoteText('');
            addToast('Nota guardada', 'success');
            fetchLeadData();
        } catch {
            addToast('Error al guardar la nota', 'error');
        } finally {
            setIsSavingNote(false);
        }
    };

    const timeline = useMemo(() => {
        const rows = [
            ...callLogs.map(log => ({
                id: `log-${log.id}`,
                title: log.outcome === 'Nota' ? 'Nota registrada' : `Contacto: ${log.outcome}`,
                message: log.notes || 'Sin observaciones.',
                prayer: log.prayer_requests || '',
                time: log.created_at,
                type: log.outcome === 'Nota' ? 'note' : 'call',
            })),
            ...counselingSessions.map(session => ({
                id: `counseling-${session.id}`,
                title: `Consejería: ${session.subject || session.topic || 'Sesión'}`,
                message: session.notes || 'Sesión de acompañamiento espiritual.',
                prayer: '',
                time: session.created_at,
                type: 'counseling',
            })),
        ];
        if (lead?.created_at) {
            rows.push({
                id: 'init',
                title: 'Contacto registrado',
                message: 'El contacto ingresó al sistema de consolidación.',
                prayer: '',
                time: lead.created_at,
                type: 'system',
            });
        }
        return rows.sort((a, b) => new Date(b.time).getTime() - new Date(a.time).getTime());
    }, [callLogs, counselingSessions, lead?.created_at]);

    const noteRows = timeline.filter(item => item.type === 'note' || item.message);
    const stage = String(lead?.stage ?? 'new');
    const initials = (lead?.nombre_completo || 'Contacto')
        .split(/\s+/)
        .filter(Boolean)
        .slice(0, 2)
        .map((part: string) => part[0])
        .join('')
        .toUpperCase();

    if (authLoading) {
        return (
            <div className="flex h-full items-center justify-center text-xs font-bold uppercase tracking-wide text-[hsl(var(--primary))]">
                Verificando sesión...
            </div>
        );
    }

    if (error) {
        return (
            <div className="mx-auto flex max-w-xl flex-col items-center gap-3 p-4 text-center">
                <p className="font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{error}</p>
                <button
                    onClick={() => setReloadKey(key => key + 1)}
                    className="rounded-md border border-[hsl(var(--border))] px-3 py-1.5 text-[11px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] transition-colors hover:bg-[hsl(var(--surface-1))] dark:border-white/10 dark:hover:bg-white/5"
                >
                    Reintentar
                </button>
            </div>
        );
    }

    if (loading) {
        return (
            <div className="flex h-full items-center justify-center text-xs font-bold uppercase tracking-wide text-[hsl(var(--primary))]">
                Cargando contacto...
            </div>
        );
    }

    return (
        <CrmShell
            breadcrumbs={[
                { label: 'Consolidación', icon: Users },
                { label: 'Leads / Contactos', href: '/plataforma/crm/contacts', icon: User },
                { label: lead?.nombre_completo || 'Contacto', icon: User },
            ]}
            rightActions={canEditCrm ? (
                <button
                    onClick={() => setIsCallDrawerOpen(true)}
                    className="inline-flex h-8 items-center gap-2 rounded-md bg-[hsl(var(--primary))] px-3 text-[11px] font-bold uppercase tracking-wide text-white shadow-sm transition-all active:scale-95"
                >
                    <Plus size={14} />
                    Interacción
                </button>
            ) : undefined}
        >
            <div className="mx-auto flex w-full max-w-6xl flex-col gap-4">
                <section className="rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-4 shadow-sm dark:border-white/10 dark:bg-white/[0.03]">
                    <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                        <div className="flex min-w-0 items-start gap-4">
                            <div className="flex size-12 shrink-0 items-center justify-center rounded-md bg-[hsl(var(--primary))] text-sm font-bold text-white">
                                {initials || '?'}
                            </div>
                            <div className="min-w-0">
                                <div className="flex flex-wrap items-center gap-2">
                                    <h1 className="truncate text-xl font-bold tracking-tight text-[hsl(var(--text-primary))] dark:text-white">
                                        {lead?.nombre_completo || 'Contacto sin nombre'}
                                    </h1>
                                    <span className={clsx('rounded-full border px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide', STAGE_BADGES[stage])}>
                                        {STAGE_LABELS[stage] ?? stage}
                                    </span>
                                </div>
                                <div className="mt-2 flex flex-wrap gap-3 text-xs font-medium text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]">
                                    <span className="inline-flex items-center gap-1.5"><Phone size={13} />{lead?.telefono || lead?.phone || 'Sin teléfono'}</span>
                                    <span className="inline-flex items-center gap-1.5"><Clock size={13} />Registrado {lead?.created_at ? new Date(lead.created_at).toLocaleDateString('es-CO') : 'sin fecha'}</span>
                                    <span className="inline-flex items-center gap-1.5"><Link2 size={13} />{lead?.source || 'Origen general'}</span>
                                </div>
                            </div>
                        </div>

                        <div className="flex flex-wrap gap-2">
                            <button
                                onClick={() => router.push('/plataforma/crm/pipeline')}
                                className="inline-flex h-8 items-center gap-2 rounded-md border border-[hsl(var(--border))] px-3 text-[11px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] transition-colors hover:bg-[hsl(var(--surface-1))] dark:border-white/10 dark:text-[hsl(var(--text-secondary))] dark:hover:bg-white/5"
                            >
                                <Link2 size={14} />
                                Pipeline
                            </button>
                            {canEditCrm && (
                                <div className="relative">
                                    <button
                                        onClick={() => setIsStageOpen(value => !value)}
                                        disabled={isSavingStage}
                                        className="inline-flex h-8 items-center gap-2 rounded-md border border-[hsl(var(--border))] px-3 text-[11px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] transition-colors hover:bg-[hsl(var(--surface-1))] disabled:opacity-60 dark:border-white/10 dark:text-[hsl(var(--text-secondary))] dark:hover:bg-white/5"
                                    >
                                        {isSavingStage ? <Loader2 size={14} className="animate-spin" /> : <ChevronDown size={14} />}
                                        Cambiar etapa
                                    </button>
                                    {isStageOpen && (
                                        <div className="absolute right-0 top-9 z-50 w-48 overflow-hidden rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] shadow-xl dark:border-white/10 dark:bg-[hsl(var(--surface-1))]">
                                            {STAGES.map(item => (
                                                <button
                                                    key={item}
                                                    onClick={() => handleStageChange(item)}
                                                    className={clsx(
                                                        'flex w-full items-center justify-between px-3 py-2 text-left text-[11px] font-bold uppercase tracking-wide transition-colors hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5',
                                                        stage === item ? 'text-[hsl(var(--primary))]' : 'text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]'
                                                    )}
                                                >
                                                    {STAGE_LABELS[item]}
                                                    {stage === item && <Check size={13} />}
                                                </button>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    </div>
                </section>

                <section className="grid grid-cols-1 gap-3 md:grid-cols-3">
                    {[
                        { label: 'Interacciones', value: callLogs.length, icon: MessageSquare },
                        { label: 'Llamadas', value: callLogs.filter(log => log.outcome !== 'Nota').length, icon: Phone },
                        { label: 'Motivos de oración', value: callLogs.filter(log => log.prayer_requests).length, icon: Heart },
                    ].map(stat => (
                        <div key={stat.label} className="rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-3 dark:border-white/10 dark:bg-white/[0.03]">
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{stat.label}</p>
                                    <p className="mt-1 text-2xl font-bold text-[hsl(var(--text-primary))] dark:text-white">{stat.value}</p>
                                </div>
                                <div className="flex size-9 items-center justify-center rounded-md bg-[hsl(var(--surface-2))] text-[hsl(var(--primary))] dark:bg-white/5">
                                    <stat.icon size={17} />
                                </div>
                            </div>
                        </div>
                    ))}
                </section>

                <section className="rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] dark:border-white/10 dark:bg-white/[0.03]">
                    <div className="flex border-b border-[hsl(var(--border))] px-3 dark:border-white/10">
                        {[
                            { id: 'history', label: 'Historial de contacto' },
                            { id: 'notes', label: 'Notas e interacción' },
                        ].map(tab => (
                            <button
                                key={tab.id}
                                onClick={() => setActiveTab(tab.id as 'history' | 'notes')}
                                className={clsx(
                                    'relative px-3 py-3 text-[11px] font-bold uppercase tracking-wide transition-colors',
                                    activeTab === tab.id
                                        ? 'text-[hsl(var(--primary))]'
                                        : 'text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] dark:hover:text-[hsl(var(--text-secondary))]'
                                )}
                            >
                                {tab.label}
                                {activeTab === tab.id && <span className="absolute inset-x-3 bottom-0 h-0.5 rounded-full bg-[hsl(var(--primary))]" />}
                            </button>
                        ))}
                    </div>

                    {activeTab === 'notes' && (
                        <div className="border-b border-[hsl(var(--border))] p-4 dark:border-white/10">
                            <form onSubmit={handleSaveNote} className="space-y-3">
                                <label className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Nueva nota</label>
                                <textarea
                                    value={noteText}
                                    onChange={event => setNoteText(event.target.value)}
                                    rows={3}
                                    placeholder="Registra observaciones, acuerdos o próximos pasos..."
                                    className="w-full resize-none rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] px-3 py-2 text-sm font-medium text-[hsl(var(--text-primary))] outline-none transition-all placeholder:text-[hsl(var(--text-secondary))] focus:border-[hsl(var(--primary))] focus:ring-2 focus:ring-[hsl(var(--primary))]/10 dark:border-white/10 dark:bg-black/20 dark:text-[hsl(var(--text-secondary))]"
                                />
                                <div className="flex justify-end">
                                    <button
                                        type="submit"
                                        disabled={isSavingNote || !noteText.trim()}
                                        className="inline-flex h-8 items-center gap-2 rounded-md bg-[hsl(var(--primary))] px-3 text-[11px] font-bold uppercase tracking-wide text-white shadow-sm transition-all disabled:opacity-50 active:scale-95"
                                    >
                                        {isSavingNote ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
                                        Guardar nota
                                    </button>
                                </div>
                            </form>
                        </div>
                    )}

                    <div className="p-4">
                        {(activeTab === 'history' ? timeline : noteRows).length > 0 ? (
                            <div className="space-y-3">
                                {(activeTab === 'history' ? timeline : noteRows).map(item => (
                                    <div key={item.id} className="flex gap-3 rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] p-3 dark:border-white/10 dark:bg-black/10">
                                        <div className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-md bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))] dark:bg-white/5 dark:text-[hsl(var(--text-secondary))]">
                                            {item.type === 'call' && <Phone size={15} />}
                                            {item.type === 'note' && <MessageSquare size={15} />}
                                            {item.type === 'counseling' && <Heart size={15} />}
                                            {item.type === 'system' && <History size={15} />}
                                        </div>
                                        <div className="min-w-0 flex-1">
                                            <div className="flex flex-wrap items-start justify-between gap-2">
                                                <h3 className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-white">{item.title}</h3>
                                                <span className="inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                                                    <Calendar size={11} />
                                                    {formatDate(item.time)}
                                                </span>
                                            </div>
                                            <p className="mt-1 whitespace-pre-line text-xs leading-relaxed text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]">{item.message}</p>
                                            {item.prayer && (
                                                <div className="mt-3 rounded-md border border-[hsl(var(--success)/25%)] bg-success-soft p-3 text-xs text-success-text dark:border-[hsl(var(--success)/100%)]/20 dark:bg-[hsl(var(--success))]/10 dark:text-[hsl(var(--success))]">
                                                    <p className="mb-1 flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wide">
                                                        <Heart size={11} />
                                                        Motivo de oración
                                                    </p>
                                                    {item.prayer}
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div className="py-10 text-center">
                                <History size={34} className="mx-auto text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]" />
                                <p className="mt-3 text-[11px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Sin registros todavía</p>
                            </div>
                        )}
                    </div>
                </section>
            </div>

            <WorkspaceDrawer
                isOpen={isCallDrawerOpen}
                onClose={() => setIsCallDrawerOpen(false)}
                title="Registrar interacción"
                subtitle="Llamadas, seguimientos y motivos de oración"
                actions={
                    <>
                        <button type="button" onClick={() => setIsCallDrawerOpen(false)} className="px-4 py-2 text-[11px] font-bold text-[hsl(var(--text-secondary))]">
                            Cancelar
                        </button>
                        <button
                            form="call-form"
                            type="submit"
                            disabled={isSavingCall}
                            className="inline-flex items-center gap-2 rounded-md bg-[hsl(var(--primary))] px-3 py-2 text-[11px] font-bold uppercase tracking-wide text-white shadow-sm transition-all disabled:opacity-60 active:scale-95"
                        >
                            {isSavingCall ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
                            Registrar
                        </button>
                    </>
                }
            >
                <form id="call-form" onSubmit={handleRegisterCall} className="space-y-3">
                    <div className="space-y-2">
                        <label className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Tipo / resultado</label>
                        <select
                            value={callForm.outcome}
                            onChange={event => setCallForm({ ...callForm, outcome: event.target.value })}
                            className="w-full rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] px-3 py-2 text-sm font-bold text-[hsl(var(--text-primary))] outline-none focus:border-[hsl(var(--primary))] focus:ring-2 focus:ring-[hsl(var(--primary))]/10 dark:border-white/10 dark:bg-black/20 dark:text-white"
                        >
                            {['Exitoso', 'Sin respuesta', 'Buzón de voz', 'Número equivocado', 'Reagendar', 'Nota'].map(option => (
                                <option key={option} value={option}>{option}</option>
                            ))}
                        </select>
                    </div>
                    <div className="space-y-2">
                        <label className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Notas</label>
                        <textarea
                            value={callForm.notes}
                            onChange={event => setCallForm({ ...callForm, notes: event.target.value })}
                            placeholder="Observaciones, acuerdos, próximos pasos..."
                            rows={4}
                            className="w-full resize-none rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] px-3 py-2 text-sm font-medium text-[hsl(var(--text-primary))] outline-none focus:border-[hsl(var(--primary))] focus:ring-2 focus:ring-[hsl(var(--primary))]/10 dark:border-white/10 dark:bg-black/20 dark:text-white"
                        />
                    </div>
                    <div className="space-y-2">
                        <label className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Motivo de oración</label>
                        <textarea
                            value={callForm.prayer_requests}
                            onChange={event => setCallForm({ ...callForm, prayer_requests: event.target.value })}
                            placeholder="Opcional"
                            rows={2}
                            className="w-full resize-none rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] px-3 py-2 text-sm font-medium text-[hsl(var(--text-primary))] outline-none focus:border-[hsl(var(--primary))] focus:ring-2 focus:ring-[hsl(var(--primary))]/10 dark:border-white/10 dark:bg-black/20 dark:text-white"
                        />
                    </div>
                </form>
            </WorkspaceDrawer>
        </CrmShell>
    );
}
