"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import {
    Phone,
    MessageSquare,
    Heart,
    Clock,
    History,
    Calendar,
    Plus,
    Sparkles,
    Check,
    MoreVertical,
    Link2,
    Users,
    ChevronDown,
    Loader2,
    Send
} from 'lucide-react';
import CrmShell from '@/components/crm/CrmShell';
import AdminHero from '@/components/admin/AdminHero';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';
import clsx from 'clsx';

interface CallLog {
    id: number;
    outcome: string;
    notes: string;
    prayer_requests: string;
    created_at: string;
}

const STAGES = ['new', 'call', 'visit', 'discipleship', 'consolidated', 'lost'];
const STAGE_LABELS: Record<string, string> = {
    new: 'Nuevo',
    call: 'Por Llamar',
    visit: 'Visita',
    discipleship: 'Discipulado',
    consolidated: 'Consolidado',
    lost: 'Perdido',
};

export default function LeadDetail() {
    const { isAuthenticated, token } = useAuth();
    const { addToast } = useToast();
    const router = useRouter();
    const params = useParams<{ id: string }>();
    const leadId = params?.id ?? '';

    const [activeTab, setActiveTab] = useState('history');
    const [lead, setLead] = useState<any>(null);
    const [callLogs, setCallLogs] = useState<CallLog[]>([]);
    const [counselingSessions, setCounselingSessions] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    // Call drawer
    const [isCallDrawerOpen, setIsCallDrawerOpen] = useState(false);
    const [isSavingCall, setIsSavingCall] = useState(false);
    const [callForm, setCallForm] = useState({ outcome: 'Exitoso', notes: '', prayer_requests: '' });

    // Stage change
    const [isStageOpen, setIsStageOpen] = useState(false);
    const [isSavingStage, setIsSavingStage] = useState(false);

    const fetchLeadData = useCallback(async () => {
        if (!token || !leadId) return;
        setLoading(true);
        try {
            const [leadData, logsData, counselingData] = await Promise.allSettled([
                apiFetch(`/crm/consolidation/pipeline/${leadId}`, { token, cache: 'no-store' }),
                apiFetch<CallLog[]>(`/crm/pipeline/leads/${leadId}/calls`, { token, cache: 'no-store' }),
                apiFetch(`/crm/counseling/lead/${leadId}`, { token, cache: 'no-store' })
            ]);
            if (leadData.status === 'fulfilled') setLead(leadData.value);
            setCallLogs(logsData.status === 'fulfilled' && Array.isArray((logsData as any).value) ? (logsData as any).value : []);
            setCounselingSessions(counselingData.status === 'fulfilled' && Array.isArray((counselingData as any).value) ? (counselingData as any).value : []);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    }, [token, leadId]);

    const handleStageChange = async (newStage: string) => {
        setIsStageOpen(false);
        setIsSavingStage(true);
        try {
            await apiFetch(`/crm/consolidation/pipeline/${leadId}`, {
                method: 'PATCH', token,
                body: { stage: newStage }
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
            await apiFetch(`/crm/pipeline/leads/${leadId}/calls`, {
                method: 'POST', token,
                body: callForm
            });
            addToast('Llamada registrada', 'success');
            setIsCallDrawerOpen(false);
            setCallForm({ outcome: 'Exitoso', notes: '', prayer_requests: '' });
            fetchLeadData();
        } catch {
            addToast('Error al registrar llamada', 'error');
        } finally {
            setIsSavingCall(false);
        }
    };

    useEffect(() => { fetchLeadData(); }, [fetchLeadData]);

    const combinedTimeline = [
        ...callLogs.map(log => ({
            id: `log-${log.id}`,
            title: `Llamada: ${log.outcome}`,
            message: log.notes,
            prayer: log.prayer_requests,
            time: new Date(log.created_at).toLocaleString(),
            type: 'call',
            color: log.outcome === 'Exitoso' ? 'bg-primary' : 'bg-slate-500',
            isInsight: false
        })),
        ...counselingSessions.map(session => ({
            id: `counseling-${session.id}`,
            title: `Consejería: ${session.subject || session.topic}`,
            message: session.notes || 'Sesión de acompañamiento espiritual.',
            prayer: '',
            time: new Date(session.created_at).toLocaleString(),
            type: 'counseling',
            color: 'bg-sky-600',
            isInsight: false
        })),
        {
            id: 'init',
            title: 'Contacto Registrado',
            message: 'El contacto ingresó al sistema de consolidación.',
            prayer: '',
            time: lead ? new Date(lead.created_at).toLocaleString() : 'Recientemente',
            type: 'spiritual',
            color: 'bg-amber-500',
            isInsight: true
        }
    ].sort((a, b) => new Date(b.time).getTime() - new Date(a.time).getTime());

    if (!isAuthenticated) return null;
    if (loading) return (
        <div className="min-h-screen bg-slate-950 flex items-center justify-center text-primary font-bold uppercase tracking-wide text-xs">
            Cargando...
        </div>
    );

    const heroWatchers = ['Coordinación de Consolidación', 'Optimus Brain'];

    return (
        <CrmShell
            breadcrumbs={[
                { label: 'CCF', icon: Users },
                { label: 'Consolidación', icon: Users },
                { label: lead ? `${lead.first_name} ${lead.last_name}` : 'Contacto', icon: Users }
            ]}
            rightActions={
                <button className="flex size-8 items-center justify-center rounded-full bg-white/5 text-slate-400 hover:text-white transition-all">
                    <MoreVertical size={20} />
                </button>
            }
        >
            <AdminHero
                eyebrow="Contacto"
                title={lead ? `${lead.first_name} ${lead.last_name}` : 'Detalle de seguimiento'}
                description="Historia, notas y próximos pasos para este contacto."
                tags={[`Etapa: ${STAGE_LABELS[lead?.stage] ?? '...'}`, `Origen: ${lead?.source ?? '...'}`]}
                watchers={heroWatchers}
                primaryAction={{ label: 'Ver pipeline', icon: Link2, onClick: () => router.push('/crm/pipeline') }}
                secondaryAction={{ label: 'Registrar llamada', icon: Plus, onClick: () => setIsCallDrawerOpen(true) }}
            />

            <div className="space-y-4">
                <section className="px-4 pt-2 pb-6 flex flex-col items-center text-center space-y-4">
                    <div className="relative group">
                        <div className="size-10 rounded-md overflow-hidden border-4 border-white/10 group-hover:border-primary/50 transition-all shadow-2xl relative">
                            <div className="size-full rounded-lg bg-slate-800 flex items-center justify-center text-white text-xl font-bold">
                                {lead?.first_name?.charAt(0).toUpperCase() || '?'}
                            </div>
                        </div>
                        <div className="absolute -bottom-2 -right-2 size-8 rounded-full bg-emerald-500 border-4 border-slate-950 flex items-center justify-center">
                            <Check size={14} className="text-white" />
                        </div>
                    </div>
                    <div className="space-y-1">
                        <h1 className="text-xl font-bold tracking-tight text-white">{lead?.first_name} {lead?.last_name}</h1>
                        <p className="text-primary font-bold uppercase tracking-wide text-[10px]">
                            Etapa: {STAGE_LABELS[lead?.stage] ?? lead?.stage} • Origen: {lead?.source ?? '...'}
                        </p>
                    </div>
                    <div className="flex items-center gap-2 px-4 py-2 bg-white/5 rounded-full border border-white/5">
                        <Clock size={12} className="text-primary" />
                        <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wide leading-none">
                            Registrado: {lead ? new Date(lead.created_at).toLocaleDateString() : '...'}
                        </span>
                    </div>
                </section>

                <section className="px-4 py-2 flex gap-4 overflow-x-auto hide-scrollbar">
                    {[
                        { label: 'Llamadas', val: callLogs.length.toString(), icon: Phone },
                        { label: 'Prayer Requests', val: callLogs.filter(l => l.prayer_requests).length.toString(), icon: Heart },
                    ].map((stat, i) => (
                        <div key={i} className="flex-1 min-w-[120px] bg-slate-900/40 backdrop-blur-xl border border-white/5 rounded-md p-3 flex flex-col gap-2 group hover:border-primary/30 transition-all">
                            <div className="size-8 rounded-md bg-primary/10 flex items-center justify-center text-primary group-hover:bg-primary group-hover:text-white transition-all text-xs">
                                <stat.icon size={16} />
                            </div>
                            <div>
                                <p className="text-[9px] font-bold text-slate-500 uppercase tracking-wide leading-none mb-1">{stat.label}</p>
                                <p className="text-lg font-bold text-white">{stat.val}</p>
                            </div>
                        </div>
                    ))}
                </section>

                <section className="sticky top-0 z-40 bg-slate-950/70 backdrop-blur-xl px-4 pt-6 border-b border-white/5">
                    <div className="flex gap-5 justify-center">
                        {[
                            { id: 'history', label: 'Historial de Contacto' },
                            { id: 'notes', label: 'Notas e Interacción' },
                        ].map((tab) => (
                            <button
                                key={tab.id}
                                onClick={() => setActiveTab(tab.id)}
                                className={`pb-4 text-xs font-bold uppercase tracking-wide transition-all relative ${activeTab === tab.id ? 'text-primary' : 'text-slate-500 hover:text-slate-300'}`}
                            >
                                {tab.label}
                                {activeTab === tab.id && (
                                    <div className="absolute bottom-0 left-0 w-full h-1 bg-primary rounded-full shadow-[0_0_8px_#4242f0]"></div>
                                )}
                            </button>
                        ))}
                    </div>
                </section>

                <section className="px-3 py-2 space-y-4">
                    {combinedTimeline.map((item, idx) => (
                        <div key={item.id} className="relative flex gap-4">
                            {idx !== combinedTimeline.length - 1 && (
                                <div className="absolute left-[1.125rem] top-5 bottom-[-40px] w-px bg-white/5"></div>
                            )}
                            <div className={`z-10 size-9 shrink-0 items-center justify-center rounded-lg ${item.color} text-white shadow-xl flex border-4 border-slate-950`}>
                                {item.type === 'call' && <Phone size={16} />}
                                {item.type === 'spiritual' && <Sparkles size={16} />}
                                {item.type === 'counseling' && <MessageSquare size={16} />}
                            </div>
                            <div className={`flex flex-col gap-2 flex-1 ${item.isInsight ? 'bg-amber-500/5 border border-amber-500/10 p-3 rounded-md' : 'bg-white/2 p-3 rounded-md border border-white/5'}`}>
                                <div className="flex justify-between items-start">
                                    <h4 className={`text-sm font-bold tracking-tight ${item.isInsight ? 'text-amber-500' : 'text-white'}`}>{item.title}</h4>
                                    <span className="text-[9px] font-bold text-slate-600 uppercase tracking-wide">{item.time}</span>
                                </div>
                                <p className={`text-xs leading-relaxed font-medium ${item.isInsight ? 'text-amber-200/60 italic' : 'text-slate-400'}`}>
                                    {item.message || 'Sin observaciones.'}
                                </p>
                                {item.prayer && (
                                    <div className="mt-2 p-3 bg-emerald-500/10 rounded-md border border-emerald-500/20">
                                        <p className="text-[10px] text-emerald-500 font-bold flex items-center gap-1 uppercase tracking-wide mb-1">
                                            <Heart size={10} /> Motivo de Oración
                                        </p>
                                        <p className="text-xs text-emerald-200/80">{item.prayer}</p>
                                    </div>
                                )}
                            </div>
                        </div>
                    ))}

                    {combinedTimeline.length === 0 && (
                        <div className="py-1.5 text-center space-y-4">
                            <History size={48} className="mx-auto text-slate-800" />
                            <p className="text-slate-500 font-bold uppercase tracking-wide text-[10px]">Sin historial registrado</p>
                        </div>
                    )}
                </section>

                {/* Actions */}
                <section className="px-4 py-2 border-t border-white/5 mt-3 space-y-3">
                    <div className="bg-primary/5 rounded-md border border-primary/20 p-4 flex flex-col gap-4 relative overflow-hidden group">
                        <div className="absolute top-0 right-0 -mr-10 -mt-3 size-10 bg-primary/10 rounded-full blur-2xl group-hover:bg-primary/20 transition-all"></div>
                        <div className="flex items-center gap-4 relative z-10">
                            <div className="bg-primary size-9 rounded-lg flex items-center justify-center text-white shadow-xl shadow-primary/20">
                                <Calendar size={24} />
                            </div>
                            <div>
                                <h4 className="text-white font-bold tracking-tight">Acciones de Consolidación</h4>
                                <p className="text-slate-500 text-[10px] font-bold uppercase tracking-wide">Gestión del Seguimiento</p>
                            </div>
                        </div>
                        <div className="flex gap-4 relative z-10">
                            <button
                                onClick={() => setIsCallDrawerOpen(true)}
                                className="flex-1 bg-primary hover:bg-primary-600 text-white py-2 rounded-lg font-bold uppercase tracking-wide text-[10px] shadow-2xl shadow-primary/30 active:scale-95 transition-all flex items-center justify-center gap-2 border border-primary-400/20"
                            >
                                <Phone size={16} />
                                Registrar Llamada
                            </button>
                            {/* Stage change dropdown */}
                            <div className="relative">
                                <button
                                    onClick={() => setIsStageOpen(s => !s)}
                                    disabled={isSavingStage}
                                    className="size-8 rounded-lg bg-white/5 border border-white/5 flex items-center justify-center text-slate-400 hover:text-white hover:bg-white/10 transition-all"
                                    title="Cambiar etapa"
                                >
                                    {isSavingStage
                                        ? <Loader2 size={20} className="animate-spin" />
                                        : <ChevronDown size={20} />
                                    }
                                </button>
                                {isStageOpen && (
                                    <div className="absolute bottom-16 right-0 w-48 bg-slate-900 border border-white/10 rounded-lg overflow-hidden shadow-2xl z-50">
                                        {STAGES.map(s => (
                                            <button
                                                key={s}
                                                onClick={() => handleStageChange(s)}
                                                className={clsx(
                                                    "w-full px-4 py-1.5 text-left text-[11px] font-bold uppercase tracking-wide transition-all hover:bg-white/10",
                                                    lead?.stage === s ? 'text-primary bg-white/5' : 'text-slate-400'
                                                )}
                                            >
                                                {STAGE_LABELS[s]}
                                            </button>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                </section>
            </div>

            {/* ─── Drawer: Registrar Llamada ─── */}
            <WorkspaceDrawer
                isOpen={isCallDrawerOpen}
                onClose={() => setIsCallDrawerOpen(false)}
                title="Registrar Llamada de Consolidación"
                subtitle="Historial de contacto con el prospecto"
                actions={
                    <>
                        <button type="button" onClick={() => setIsCallDrawerOpen(false)} className="px-4 py-2 text-[11px] font-bold text-slate-500">
                            Cancelar
                        </button>
                        <button
                            form="call-form"
                            type="submit"
                            disabled={isSavingCall}
                            className="px-3 py-2 bg-primary text-white rounded-lg text-[11px] font-bold uppercase tracking-wide shadow-lg active:scale-95 transition-all flex items-center gap-2"
                        >
                            {isSavingCall ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
                            Registrar
                        </button>
                    </>
                }
            >
                <form id="call-form" onSubmit={handleRegisterCall} className="space-y-2">
                    <div className="space-y-2">
                        <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">Resultado de la llamada</label>
                        <select
                            value={callForm.outcome}
                            onChange={e => setCallForm({ ...callForm, outcome: e.target.value })}
                            className="w-full px-4 py-1.5 rounded-lg border border-white/10 bg-black/20 outline-none focus:ring-2 focus:ring-primary/20 font-bold text-sm text-white appearance-none"
                        >
                            {['Exitoso', 'Sin respuesta', 'Buzón de voz', 'Número equivocado', 'Reagendar'].map(o =>
                                <option key={o} value={o}>{o}</option>
                            )}
                        </select>
                    </div>
                    <div className="space-y-2">
                        <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">Notas de la llamada</label>
                        <textarea
                            value={callForm.notes}
                            onChange={e => setCallForm({ ...callForm, notes: e.target.value })}
                            placeholder="Observaciones, próximos pasos..."
                            rows={3}
                            className="w-full px-4 py-1.5 rounded-lg border border-white/10 bg-black/20 outline-none focus:ring-2 focus:ring-primary/20 font-bold text-sm text-white resize-none"
                        />
                    </div>
                    <div className="space-y-2">
                        <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">Motivo de Oración (opcional)</label>
                        <textarea
                            value={callForm.prayer_requests}
                            onChange={e => setCallForm({ ...callForm, prayer_requests: e.target.value })}
                            placeholder="Petición de oración mencionada..."
                            rows={2}
                            className="w-full px-4 py-1.5 rounded-lg border border-white/10 bg-black/20 outline-none focus:ring-2 focus:ring-primary/20 font-bold text-sm text-white resize-none"
                        />
                    </div>
                </form>
            </WorkspaceDrawer>
        </CrmShell>
    );
}
