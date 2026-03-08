"use client";

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { apiUrl } from '@/lib/api';
import {
    ArrowLeft,
    MoreVertical,
    Phone,
    MessageSquare,
    Heart,
    Clock,
    History,
    Calendar,
    Plus,
    Sparkles,
    CheckCircle2,
    Check
} from 'lucide-react';

interface CallLog {
    id: number;
    outcome: string;
    notes: string;
    prayer_requests: string;
    created_at: string;
}

export default function LeadDetail({ params }: { params: { id: string } }) {
    const { isAuthenticated } = useAuth();
    const router = useRouter();
    const [activeTab, setActiveTab] = useState('history');
    const [lead, setLead] = useState<any>(null);
    const [callLogs, setCallLogs] = useState<CallLog[]>([]);
    const [counselingSessions, setCounselingSessions] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (params.id) {
            fetchLeadData();
        }
    }, [params.id]);

    const fetchLeadData = async () => {
        try {
            const leadRes = await fetch(apiUrl(`/pipeline/${params.id}`));
            if (leadRes.ok) {
                const leadData = await leadRes.json();
                setLead(leadData);
            }

            const logsRes = await fetch(apiUrl(`/crm/pipeline/leads/${params.id}/calls`));
            if (logsRes.ok) {
                const logsData = await logsRes.json();
                setCallLogs(logsData);
            }

            const counsRes = await fetch(apiUrl(`/crm/counseling/lead/${params.id}`));
            if (counsRes.ok) {
                const counsData = await counsRes.json();
                setCounselingSessions(counsData);
            }
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

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
            title: `Consejería: ${session.topic}`,
            message: session.summary || 'Sesión de acompañamiento espiritual.',
            prayer: '',
            time: new Date(session.scheduled_at).toLocaleString(),
            type: 'counseling',
            color: 'bg-purple-600',
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
    if (loading) return <div className="min-h-screen bg-slate-950 flex items-center justify-center text-primary font-black uppercase tracking-widest text-xs">Cargando...</div>;

    return (
        <div className="min-h-screen bg-slate-950 font-display text-slate-100 selection:bg-primary/30 relative overflow-x-hidden flex flex-col uppercase-none">
            {/* Ambient Backgrounds */}
            <div className="fixed inset-0 z-0 bg-slate-950 pointer-events-none">
                <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-[radial-gradient(circle_at_top_right,_var(--tw-gradient-stops))] from-primary/10 via-slate-950 to-slate-950 opacity-40 blur-3xl mix-blend-screen"></div>
            </div>

            <div className="relative z-10 max-w-4xl mx-auto flex flex-col min-h-screen w-full">
                {/* Header Section */}
                <header className="sticky top-0 z-50 bg-slate-950/80 backdrop-blur-xl px-6 py-6 border-b border-white/5 flex items-center justify-between">
                    <button onClick={() => router.back()} className="text-slate-400 flex size-10 items-center justify-center rounded-full bg-white/5 hover:bg-primary/20 hover:text-primary transition-all cursor-pointer">
                        <ArrowLeft size={20} />
                    </button>
                    <h2 className="text-white text-lg font-black tracking-tight flex-1 text-center pr-10">Detalle de Seguimiento</h2>
                    <button className="flex size-10 items-center justify-center rounded-full bg-white/5 text-slate-400 hover:text-white transition-all">
                        <MoreVertical size={20} />
                    </button>
                </header>

                <main className="flex-1 pb-32 overflow-y-auto hide-scrollbar animate-in fade-in slide-in-from-bottom-8 duration-700">

                    {/* Hero Profile Section */}
                    <section className="px-6 pt-10 pb-6 flex flex-col items-center text-center space-y-4">
                        <div className="relative group">
                            <div className="size-32 rounded-[2.5rem] overflow-hidden border-4 border-white/10 group-hover:border-primary/50 transition-all shadow-2xl relative">
                                <div className="size-full rounded-[2.2rem] bg-slate-800 flex items-center justify-center text-white text-3xl font-black">
                                    {lead?.first_name?.charAt(0).toUpperCase() || '?'}
                                </div>
                            </div>
                            <div className="absolute -bottom-2 -right-2 size-8 rounded-full bg-emerald-500 border-4 border-slate-950 flex items-center justify-center">
                                <Check size={14} className="text-white" />
                            </div>
                        </div>
                        <div className="space-y-1">
                            <h1 className="text-3xl font-black tracking-tight text-white">{lead?.first_name} {lead?.last_name}</h1>
                            <p className="text-primary font-black uppercase tracking-[0.2em] text-[10px]">Etapa: {lead?.stage} • Origen: {lead?.source}</p>
                        </div>
                        <div className="flex items-center gap-2 px-4 py-2 bg-white/5 rounded-full border border-white/5">
                            <Clock size={12} className="text-primary" />
                            <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest leading-none">
                                Miembro desde: {lead ? new Date(lead.created_at).toLocaleDateString() : '...'}
                            </span>
                        </div>
                    </section>

                    {/* Quick Stats */}
                    <section className="px-6 py-4 flex gap-4 overflow-x-auto hide-scrollbar">
                        {[
                            { label: 'Llamadas', val: callLogs.length.toString(), icon: Phone },
                            { label: 'Prayer Requests', val: callLogs.filter(l => l.prayer_requests).length.toString(), icon: Heart },
                        ].map((stat, i) => (
                            <div key={i} className="flex-1 min-w-[120px] bg-slate-900/40 backdrop-blur-xl border border-white/5 rounded-3xl p-5 flex flex-col gap-2 group hover:border-primary/30 transition-all">
                                <div className="size-8 rounded-xl bg-primary/10 flex items-center justify-center text-primary group-hover:bg-primary group-hover:text-white transition-all text-xs">
                                    <stat.icon size={16} />
                                </div>
                                <div>
                                    <p className="text-[9px] font-black text-slate-500 uppercase tracking-widest leading-none mb-1">{stat.label}</p>
                                    <p className="text-2xl font-black text-white">{stat.val}</p>
                                </div>
                            </div>
                        ))}
                    </section>

                    {/* Tabs */}
                    <section className="sticky top-[80px] z-40 bg-slate-950/80 backdrop-blur-xl px-6 pt-6 border-b border-white/5">
                        <div className="flex gap-10 justify-center">
                            {[
                                { id: 'history', label: 'Historial de Contacto' },
                                { id: 'notes', label: 'Notas e Interacción' },
                            ].map((tab) => (
                                <button
                                    key={tab.id}
                                    onClick={() => setActiveTab(tab.id)}
                                    className={`pb-4 text-xs font-black uppercase tracking-widest transition-all relative ${activeTab === tab.id ? 'text-primary' : 'text-slate-500 hover:text-slate-300'
                                        }`}
                                >
                                    {tab.label}
                                    {activeTab === tab.id && (
                                        <div className="absolute bottom-0 left-0 w-full h-1 bg-primary rounded-full shadow-[0_0_8px_#4242f0]"></div>
                                    )}
                                </button>
                            ))}
                        </div>
                    </section>

                    {/* Timeline */}
                    <section className="px-8 py-10 space-y-10">
                        {combinedTimeline.map((item, idx) => (
                            <div key={item.id} className="relative flex gap-6">
                                {idx !== combinedTimeline.length - 1 && (
                                    <div className="absolute left-[1.125rem] top-10 bottom-[-40px] w-px bg-white/5"></div>
                                )}
                                <div className={`z-10 size-9 shrink-0 items-center justify-center rounded-2xl ${item.color} text-white shadow-xl flex border-4 border-slate-950`}>
                                    {item.type === 'call' && <Phone size={16} />}
                                    {item.type === 'spiritual' && <Sparkles size={16} />}
                                    {item.type === 'counseling' && <MessageSquare size={16} />}
                                </div>
                                <div className={`flex flex-col gap-2 flex-1 ${item.isInsight ? 'bg-amber-500/5 border border-amber-500/10 p-5 rounded-[2rem]' : 'bg-white/2 p-5 rounded-[2rem] border border-white/5'}`}>
                                    <div className="flex justify-between items-start">
                                        <h4 className={`text-sm font-black tracking-tight ${item.isInsight ? 'text-amber-500' : 'text-white'}`}>{item.title}</h4>
                                        <span className="text-[9px] font-black text-slate-600 uppercase tracking-widest">{item.time}</span>
                                    </div>
                                    <p className={`text-xs leading-relaxed font-medium ${item.isInsight ? 'text-amber-200/60 italic' : 'text-slate-400'}`}>
                                        {item.message || 'Sin observaciones.'}
                                    </p>
                                    {item.prayer && (
                                        <div className="mt-2 p-3 bg-emerald-500/10 rounded-xl border border-emerald-500/20">
                                            <p className="text-[10px] text-emerald-500 font-bold flex items-center gap-1 uppercase tracking-widest mb-1">
                                                <Heart size={10} /> Motivo de Oración
                                            </p>
                                            <p className="text-xs text-emerald-200/80">{item.prayer}</p>
                                        </div>
                                    )}
                                </div>
                            </div>
                        ))}

                        {combinedTimeline.length === 0 && (
                            <div className="py-20 text-center space-y-4">
                                <History size={48} className="mx-auto text-slate-800" />
                                <p className="text-slate-500 font-bold uppercase tracking-widest text-[10px]">Sin historial registrado</p>
                            </div>
                        )}
                    </section>

                    {/* Call to Action */}
                    <section className="px-6 py-6 border-t border-white/5 mt-6 mb-20 space-y-6">
                        <div className="bg-primary/5 rounded-[2.5rem] border border-primary/20 p-8 flex flex-col gap-6 relative overflow-hidden group">
                            <div className="absolute top-0 right-0 -mr-10 -mt-10 size-32 bg-primary/10 rounded-full blur-2xl group-hover:bg-primary/20 transition-all"></div>
                            <div className="flex items-center gap-4 relative z-10">
                                <div className="bg-primary size-12 rounded-2xl flex items-center justify-center text-white shadow-xl shadow-primary/20">
                                    <Calendar size={24} />
                                </div>
                                <div>
                                    <h4 className="text-white font-black tracking-tight">Agendar Seguimiento</h4>
                                    <p className="text-slate-500 text-[10px] font-black uppercase tracking-widest">Próxima acción recomendada</p>
                                </div>
                            </div>
                            <div className="flex gap-4 relative z-10">
                                <button className="flex-1 bg-primary hover:bg-primary-600 text-white py-4 rounded-2xl font-black uppercase tracking-[0.2em] text-[10px] shadow-2xl shadow-primary/30 active:scale-95 transition-all flex items-center justify-center gap-2 border border-primary-400/20">
                                    <History size={16} />
                                    Nueva Llamada
                                </button>
                                <button className="size-14 rounded-2xl bg-white/5 border border-white/5 flex items-center justify-center text-slate-400 hover:text-white hover:bg-white/10 transition-all">
                                    <Calendar size={20} />
                                </button>
                            </div>
                        </div>
                    </section>
                </main>

                {/* Floating Action Button */}
                <button
                    onClick={() => router.push('/crm/pipeline')}
                    className="fixed bottom-32 right-8 size-16 bg-primary text-white rounded-[2rem] shadow-2xl shadow-primary/40 flex items-center justify-center hover:scale-110 active:scale-90 transition-all z-50 animate-bounce"
                >
                    <Plus size={32} />
                </button>
            </div>
        </div>
    );
}
