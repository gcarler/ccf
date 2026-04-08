"use client";

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { 
    Send, 
    MessageSquare, 
    Mail, 
    Users, 
    Smartphone, 
    Zap, 
    History, 
    Plus, 
    Filter, 
    ChevronRight, 
    MoreHorizontal,
    Bot,
    Sparkles,
    Calendar,
    Layout,
    CheckCircle2,
    Clock,
    AlertCircle,
    Image as ImageIcon,
    FileText,
    Target,
    BarChart3
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import { ViewType, getStoredView } from '@/components/ViewSwitcher';
import CrmViewPlaceholder from '@/components/crm/CrmViewPlaceholder';

type Channel = 'whatsapp' | 'email' | 'sms';
const STATUS_PROGRESS: Record<string, number> = { failed: 20, sent: 75, delivered: 100 };

export default function MessagingCampaignCenter() {
    const { token } = useAuth();
    const { addToast } = useToast();
    const [channel, setChannel] = useState<Channel>('whatsapp');
    const [campaignName, setCampaignName] = useState('');
    const [message, setMessage] = useState('');
    const [segments, setSegments] = useState<string[]>([]);
    const [history, setHistory] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [isSending, setIsSending] = useState(false);
    const [viewType, setViewType] = useState<ViewType>(() => getStoredView('crm_messaging_view', 'grid'));
    const [wikiNotes, setWikiNotes] = useState('');

    const fetchHistory = useCallback(async () => {
        if (!token) return;
        setLoading(true);
        try {
            const data = await apiFetch('/crm/messaging/history', { token });
            setHistory(Array.isArray(data) ? data : []);
        } catch (err) {
            // Mock history for visual demo
            setHistory([
                { id: 1, name: 'Bienvenida Nuevos', channel: 'whatsapp', status: 'sent', count: 45, date: 'Hace 2 horas' },
                { id: 2, name: 'Recordatorio Ofrenda', channel: 'email', status: 'delivered', count: 128, date: 'Ayer' },
                { id: 3, name: 'Alerta Evento Jóvenes', channel: 'sms', status: 'failed', count: 12, date: 'Hace 3 días' }
            ]);
        } finally {
            setLoading(false);
        }
    }, [token]);

    useEffect(() => { fetchHistory(); }, [fetchHistory]);

    useEffect(() => {
        const saved = localStorage.getItem('crm_messaging_wiki_notes');
        if (saved) setWikiNotes(saved);
    }, []);

    useEffect(() => {
        localStorage.setItem('crm_messaging_wiki_notes', wikiNotes);
    }, [wikiNotes]);

    const handleSendCampaign = async () => {
        if (!message || !campaignName || segments.length === 0) {
            addToast('Completa todos los campos antes de enviar', 'warning');
            return;
        }
        setIsSending(true);
        try {
            await apiFetch('/crm/messaging/send', {
                method: 'POST',
                token,
                body: {
                    name: campaignName,
                    channel,
                    content: message,
                    target_segments: segments
                }
            });
            addToast('Campaña iniciada con éxito', 'success');
            setCampaignName('');
            setMessage('');
            fetchHistory();
        } catch (err) {
            addToast('Error al procesar el envío masivo', 'error');
        } finally {
            setIsSending(false);
        }
    };

    const toggleSegment = (id: string) => {
        setSegments(prev => prev.includes(id) ? prev.filter(s => s !== id) : [...prev, id]);
    };

    const groupedByChannel = useMemo(() => {
        const channels: Channel[] = ['whatsapp', 'email', 'sms'];
        return channels.map(ch => ({
            key: ch,
            label: ch === 'whatsapp' ? 'WhatsApp' : ch === 'email' ? 'Email' : 'SMS',
            items: history.filter((h: any) => h.channel === ch),
        }));
    }, [history]);

    const groupedByDate = useMemo(() => {
        const map: Record<string, any[]> = {};
        for (const item of history) {
            const key = item.date || 'Sin fecha';
            if (!map[key]) map[key] = [];
            map[key].push(item);
        }
        return Object.entries(map);
    }, [history]);

    return (
        <div className="flex flex-col h-full bg-slate-50/50 dark:bg-[#1e1f21] overflow-hidden font-display">
            <WorkspaceToolbar 
                breadcrumbs={[
                    { label: 'CRM Pastoral', icon: Users },
                    { label: 'Centro de Mensajería', icon: Send }
                ]}
                viewType={viewType}
                setViewType={setViewType}
                availableViews={['table', 'list', 'grid', 'board', 'kanban', 'gantt', 'calendar', 'wiki']}
                rightActions={
                    <button className="flex items-center gap-2 px-6 py-2 bg-white dark:bg-white/5 hover:bg-slate-50 rounded-xl text-[11px] font-black uppercase tracking-widest text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-white/10 shadow-sm transition-all active:scale-95">
                        <History size={14} /> Historial Detallado
                    </button>
                }
            />

            <main className="flex-1 overflow-y-auto scrollbar-thin p-8 lg:p-12">
                {viewType === 'list' && (
                    <div className="max-w-5xl mx-auto space-y-3">
                        {history.map((item) => (
                            <div key={item.id} className="rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 p-4 flex items-center justify-between">
                                <div>
                                    <p className="text-sm font-black text-slate-800 dark:text-slate-100">{item.name}</p>
                                    <p className="text-[11px] text-slate-500">{item.channel} · {item.date}</p>
                                </div>
                                <span className="text-[10px] font-black uppercase tracking-widest text-slate-400">{item.status}</span>
                            </div>
                        ))}
                        {history.length === 0 && <div className="py-10 text-center text-slate-400 text-sm">Sin campañas recientes</div>}
                    </div>
                )}

                {viewType === 'table' && (
                    <div className="max-w-6xl mx-auto rounded-2xl border border-slate-200 dark:border-white/10 overflow-hidden bg-white dark:bg-white/5">
                        <table className="w-full text-left">
                            <thead className="bg-slate-50 dark:bg-white/5">
                                <tr>
                                    <th className="px-4 py-3 text-[10px] font-black uppercase tracking-widest text-slate-400">Campaña</th>
                                    <th className="px-4 py-3 text-[10px] font-black uppercase tracking-widest text-slate-400">Canal</th>
                                    <th className="px-4 py-3 text-[10px] font-black uppercase tracking-widest text-slate-400">Fecha</th>
                                    <th className="px-4 py-3 text-[10px] font-black uppercase tracking-widest text-slate-400">Estado</th>
                                    <th className="px-4 py-3 text-[10px] font-black uppercase tracking-widest text-slate-400">Volumen</th>
                                </tr>
                            </thead>
                            <tbody>
                                {history.map((item) => (
                                    <tr key={item.id} className="border-t border-slate-100 dark:border-white/5">
                                        <td className="px-4 py-3 text-sm font-bold text-slate-800 dark:text-slate-100">{item.name}</td>
                                        <td className="px-4 py-3 text-xs text-slate-500 uppercase">{item.channel}</td>
                                        <td className="px-4 py-3 text-xs text-slate-500">{item.date}</td>
                                        <td className="px-4 py-3 text-xs font-black uppercase text-slate-500">{item.status}</td>
                                        <td className="px-4 py-3 text-xs text-slate-500">{item.count}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}

                {(viewType === 'board' || viewType === 'kanban') && (
                    <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-3 gap-4">
                        {groupedByChannel.map(col => (
                            <div key={col.key} className="rounded-2xl border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/[0.03] p-3">
                                <div className="mb-3 flex items-center justify-between">
                                    <p className="text-[10px] font-black uppercase tracking-widest text-slate-500">{col.label}</p>
                                    <span className="text-[10px] font-black text-slate-400">{col.items.length}</span>
                                </div>
                                <div className="space-y-2">
                                    {col.items.map((item: any) => (
                                        <div key={item.id} className="rounded-xl border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 p-3">
                                            <p className="text-xs font-black text-slate-800 dark:text-slate-100">{item.name}</p>
                                            <p className="text-[10px] text-slate-400">{item.date} · {item.count} envíos</p>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        ))}
                    </div>
                )}

                {viewType === 'calendar' && (
                    <div className="max-w-6xl mx-auto space-y-4">
                        {groupedByDate.map(([label, items]) => (
                            <div key={label} className="rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 p-4">
                                <p className="mb-3 text-[10px] font-black uppercase tracking-widest text-slate-500">{label}</p>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                    {items.map((item: any) => (
                                        <div key={item.id} className="rounded-xl border border-slate-200 dark:border-white/10 p-3">
                                            <p className="text-sm font-black text-slate-800 dark:text-slate-100">{item.name}</p>
                                            <p className="text-[10px] text-slate-400">{item.channel} · {item.status}</p>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        ))}
                    </div>
                )}

                {viewType === 'gantt' && (
                    <div className="max-w-5xl mx-auto rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 p-4 space-y-3">
                        <p className="text-[10px] font-black uppercase tracking-widest text-slate-500">Avance de entrega</p>
                        {history.map((item) => (
                            <div key={item.id} className="space-y-1">
                                <div className="flex items-center justify-between text-[11px]">
                                    <span className="font-bold text-slate-700 dark:text-slate-300">{item.name}</span>
                                    <span className="font-black text-slate-400">{STATUS_PROGRESS[item.status] ?? 0}%</span>
                                </div>
                                <div className="h-2 rounded-full bg-slate-100 dark:bg-white/10 overflow-hidden">
                                    <div className="h-full bg-blue-600" style={{ width: `${STATUS_PROGRESS[item.status] ?? 0}%` }} />
                                </div>
                            </div>
                        ))}
                    </div>
                )}

                {viewType === 'wiki' && (
                    <div className="max-w-5xl mx-auto rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 p-4 space-y-3">
                        <p className="text-[10px] font-black uppercase tracking-widest text-slate-500">Wiki de mensajería</p>
                        <textarea
                            value={wikiNotes}
                            onChange={(e) => setWikiNotes(e.target.value)}
                            placeholder="Documenta políticas por canal, horarios recomendados, segmentación y compliance..."
                            className="w-full min-h-[320px] rounded-2xl border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-black/20 p-4 text-sm font-medium text-slate-700 dark:text-slate-200 outline-none focus:ring-2 focus:ring-blue-500/20"
                        />
                    </div>
                )}

                {viewType === 'grid' && (
                <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-10">
                    
                    {/* Left Column: Composer */}
                    <div className="lg:col-span-7 space-y-8">
                        <section className="bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-[3rem] p-10 shadow-xl space-y-10 relative overflow-hidden">
                            <div className="absolute top-0 right-0 -mr-12 -mt-12 size-40 bg-blue-600/5 rounded-full blur-3xl" />
                            
                            <div className="relative z-10 flex justify-between items-center">
                                <div>
                                    <h2 className="text-2xl font-black tracking-tight text-slate-900 dark:text-white leading-none mb-2 uppercase">Campaign Composer</h2>
                                    <p className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em]">Crea mensajes de alto impacto</p>
                                </div>
                                <div className="flex bg-slate-100 dark:bg-white/5 p-1.5 rounded-2xl border border-slate-200 dark:border-white/10">
                                    <ChannelButton active={channel === 'whatsapp'} onClick={() => setChannel('whatsapp')} icon={MessageSquare} label="WhatsApp" />
                                    <ChannelButton active={channel === 'email'} onClick={() => setChannel('email')} icon={Mail} label="Email" />
                                    <ChannelButton active={channel === 'sms'} onClick={() => setChannel('sms')} icon={Smartphone} label="SMS" />
                                </div>
                            </div>

                            <div className="space-y-6">
                                <div className="space-y-2">
                                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest px-4">Nombre de la Campaña</label>
                                    <input 
                                        value={campaignName} onChange={(e) => setCampaignName(e.target.value)}
                                        placeholder="Ej: Invitación Asamblea de Miembros"
                                        className="w-full bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/5 rounded-2xl py-4 px-6 text-sm font-medium outline-none focus:ring-4 focus:ring-blue-500/10 transition-all"
                                    />
                                </div>

                                <div className="space-y-2">
                                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest px-4">Mensaje (Personalización con {`{nombre}`})</label>
                                    <div className="relative">
                                        <textarea 
                                            value={message} onChange={(e) => setMessage(e.target.value)}
                                            placeholder="Hola {nombre}, te escribimos de CCF para..."
                                            className="w-full h-48 bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/5 rounded-3xl p-6 text-[15px] font-medium outline-none focus:ring-4 focus:ring-blue-500/10 transition-all resize-none"
                                        />
                                        <div className="absolute bottom-4 right-4 flex gap-2">
                                            <button className="p-2.5 bg-white dark:bg-white/10 rounded-xl text-slate-400 hover:text-blue-600 transition-colors shadow-sm"><Bot size={18} /></button>
                                            <button className="p-2.5 bg-white dark:bg-white/10 rounded-xl text-slate-400 hover:text-blue-600 transition-colors shadow-sm"><ImageIcon size={18} /></button>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <div className="pt-6 border-t border-slate-100 dark:border-white/5 flex items-center justify-between">
                                <div className="flex gap-2">
                                    <button className="flex items-center gap-2 px-4 py-2 text-[10px] font-black uppercase tracking-widest text-slate-400 hover:text-slate-600 transition-colors">
                                        <FileText size={14} /> Guardar Borrador
                                    </button>
                                </div>
                                <button 
                                    onClick={handleSendCampaign} disabled={isSending}
                                    className="flex items-center gap-3 px-10 py-4 bg-blue-600 text-white rounded-2xl text-[11px] font-black uppercase tracking-[0.2em] shadow-xl shadow-blue-500/20 active:scale-95 transition-all disabled:opacity-50"
                                >
                                    {isSending ? <Clock size={18} className="animate-spin" /> : <Zap size={18} fill="currentColor" />}
                                    Lanzar Campaña
                                </button>
                            </div>
                        </section>

                        <section className="bg-blue-50 dark:bg-blue-900/10 rounded-[3.5rem] p-10 border border-blue-100 dark:border-blue-500/20 space-y-6">
                            <div className="flex items-center gap-3 text-blue-600 dark:text-blue-400">
                                <Sparkles size={20} />
                                <h3 className="text-[11px] font-black uppercase tracking-widest">IA Copywriting Helper</h3>
                            </div>
                            <p className="text-[14px] text-slate-600 dark:text-slate-300 leading-relaxed font-medium italic">
                                &ldquo;Optimus sugiere: Los mensajes enviados por WhatsApp entre las 10:00 AM y 11:30 AM tienen un 25% más de tasa de respuesta en el segmento de Líderes.&rdquo;
                            </p>
                        </section>
                    </div>

                    {/* Right Column: Targeting & History */}
                    <div className="lg:col-span-5 space-y-8">
                        <section className="bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-[3rem] p-10 shadow-xl space-y-8">
                            <div className="flex items-center justify-between">
                                <h3 className="text-lg font-black tracking-tight uppercase tracking-widest leading-none">Audiencia</h3>
                                <Filter size={18} className="text-slate-300" />
                            </div>
                            <div className="grid grid-cols-2 gap-3">
                                <SegmentTag label="Miembros Activos" active={segments.includes('active')} onClick={() => toggleSegment('active')} />
                                <SegmentTag label="Nuevos Visitantes" active={segments.includes('new')} onClick={() => toggleSegment('new')} />
                                <SegmentTag label="Pastores & Staff" active={segments.includes('staff')} onClick={() => toggleSegment('staff')} />
                                <SegmentTag label="Casas de Gloria" active={segments.includes('groups')} onClick={() => toggleSegment('groups')} />
                                <SegmentTag label="Baja Asistencia" active={segments.includes('low')} onClick={() => toggleSegment('low')} />
                                <SegmentTag label="Donantes Pro" active={segments.includes('vip')} onClick={() => toggleSegment('vip')} />
                            </div>
                            <div className="p-6 bg-slate-50 dark:bg-black/20 rounded-[2rem] border border-slate-100 dark:border-white/5 flex items-center justify-between">
                                <div className="flex items-center gap-4">
                                    <div className="size-10 rounded-xl bg-blue-100 flex items-center justify-center text-blue-600"><Users size={20} /></div>
                                    <div>
                                        <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-0.5">Total Estimado</p>
                                        <h4 className="text-xl font-black text-slate-900 dark:text-white">1,450 <span className="text-[10px] text-slate-400 font-bold tracking-normal uppercase">Contactos</span></h4>
                                    </div>
                                </div>
                                <Target size={20} className="text-blue-500" />
                            </div>
                        </section>

                        <section className="bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-[3rem] p-10 shadow-xl space-y-8">
                            <div className="flex items-center justify-between">
                                <h3 className="text-lg font-black tracking-tight uppercase tracking-widest leading-none">Actividad Reciente</h3>
                                <BarChart3 size={18} className="text-slate-300" />
                            </div>
                            <div className="space-y-6">
                                {history.map((item) => (
                                    <div key={item.id} className="flex items-center justify-between group cursor-pointer">
                                        <div className="flex items-center gap-4">
                                            <div className={clsx(
                                                "size-12 rounded-2xl flex items-center justify-center transition-all group-hover:scale-110",
                                                item.channel === 'whatsapp' ? "bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600" : "bg-blue-50 dark:bg-blue-900/20 text-blue-600"
                                            )}>
                                                {item.channel === 'whatsapp' ? <MessageSquare size={20} /> : <Mail size={20} />}
                                            </div>
                                            <div>
                                                <h4 className="text-[13px] font-black text-slate-800 dark:text-white uppercase leading-tight mb-1">{item.name}</h4>
                                                <div className="flex items-center gap-2">
                                                    <span className="text-[9px] font-bold text-slate-400 uppercase tracking-widest">{item.date}</span>
                                                    <div className="size-1 rounded-full bg-slate-300" />
                                                    <span className="text-[9px] font-black text-blue-500 uppercase">{item.count} envíos</span>
                                                </div>
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-3">
                                            {item.status === 'sent' && <CheckCircle2 size={16} className="text-emerald-500" />}
                                            {item.status === 'delivered' && <Zap size={16} fill="currentColor" className="text-amber-500" />}
                                            {item.status === 'failed' && <AlertCircle size={16} className="text-rose-500" />}
                                            <ChevronRight size={16} className="text-slate-300 opacity-0 group-hover:opacity-100 transition-all group-hover:translate-x-1" />
                                        </div>
                                    </div>
                                ))}
                            </div>
                            <button className="w-full py-4 bg-slate-900 dark:bg-white/5 text-white rounded-2xl text-[10px] font-black uppercase tracking-[0.2em] hover:bg-slate-800 transition-all">
                                Ver Reporte Completo
                            </button>
                        </section>
                    </div>
                </div>
                )}

                {!['table', 'list', 'grid', 'board', 'kanban', 'gantt', 'calendar', 'wiki'].includes(viewType) && (
                    <CrmViewPlaceholder moduleName="Centro de Mensajeria" viewType={viewType} />
                )}
            </main>
        </div>
    );
}

function ChannelButton({ active, onClick, icon: Icon, label }: any) {
    return (
        <button 
            onClick={onClick}
            className={clsx(
                "flex items-center gap-2.5 px-6 py-2.5 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all",
                active ? "bg-white dark:bg-blue-600 text-blue-600 dark:text-white shadow-xl shadow-blue-500/10" : "text-slate-400 hover:text-slate-600"
            )}
        >
            <Icon size={14} /> {label}
        </button>
    );
}

function SegmentTag({ label, active, onClick }: any) {
    return (
        <button 
            onClick={onClick}
            className={clsx(
                "py-3.5 px-4 rounded-2xl text-[10px] font-bold uppercase tracking-wider text-left transition-all border",
                active 
                    ? "bg-blue-600 border-blue-600 text-white shadow-lg shadow-blue-500/20" 
                    : "bg-white dark:bg-white/5 border-slate-200 dark:border-white/10 text-slate-500 hover:border-blue-500/30"
            )}
        >
            {label}
        </button>
    );
}
