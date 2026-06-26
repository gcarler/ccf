"use client";

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { 
    Send, 
    MessageSquare, 
    Mail, 
    Users, 
    Smartphone, 
    Zap, 
    History, 
    Filter, 
    ChevronRight, 
    Bot,
    Sparkles,
    CheckCircle2,
    Clock,
    AlertCircle,
    Image as ImageIcon,
    FileText,
    Target,
    BarChart3
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useCrmAccess } from '@/hooks/useCrmAccess';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import { useWikiDocument } from '@/hooks/useWikiDocument';
import clsx from 'clsx';
import { ViewType, getStoredView } from '@/components/ViewSwitcher';
import CrmViewPlaceholder from '@/components/crm/CrmViewPlaceholder';
import CrmShell from '@/components/crm/CrmShell';

import { Channel, MessagingHistoryRow } from '@/types/crm';
import { ChannelButton, SegmentTag } from '@/components/crm/ui';

const STATUS_PROGRESS: Record<string, number> = { failed: 20, sent: 75, delivered: 100 };

function normalizeHistoryRow(row: any): MessagingHistoryRow {
    const sentAt = row?.sent_at ? new Date(row.sent_at) : null;
    const targetCount = Number(row?.target_count ?? row?.count ?? 1);
    const deliveredCount = Number(row?.delivered_count ?? (row?.status === 'failed' ? 0 : targetCount));
    const failedCount = Number(row?.failed_count ?? (row?.status === 'failed' ? targetCount : 0));
    return {
        id: Number(row?.id ?? 0),
        name: row?.name ?? row?.campaign_name ?? row?.persona_name ?? `Mensaje #${row?.id ?? 0}`,
        campaign_name: row?.campaign_name,
        channel: (String(row?.channel || 'whatsapp').toLowerCase() as Channel),
        status: String(row?.status || 'sent'),
        count: Number(row?.count ?? row?.target_count ?? 1),
        date: sentAt && !Number.isNaN(sentAt.getTime()) ? sentAt.toLocaleString() : String(row?.date || 'Sin fecha'),
        target_count: targetCount,
        delivered_count: deliveredCount,
        failed_count: failedCount,
    };
}

export default function MessagingCampaignCenter() {
    const router = useRouter();
    const { token } = useAuth();
    const { canEditCrm } = useCrmAccess();
    const { addToast } = useToast();
    const [channel, setChannel] = useState<Channel>('whatsapp');
    const [campaignName, setCampaignName] = useState('');
    const [message, setMessage] = useState('');
    const [segments, setSegments] = useState<string[]>([]);
    const [history, setHistory] = useState<any[]>([]);
    const [isSending, setIsSending] = useState(false);
    const [viewType, setViewType] = useState<ViewType>(() => getStoredView('crm_messaging_view', 'grid'));
    const { content: wikiNotes, setContent: setWikiNotes } = useWikiDocument('crm_messaging_wiki_notes', {
        title: 'Wiki de mensajeria CRM',
    });

    const fetchHistory = useCallback(async () => {
        if (!token) return;
        try {
            const data = await apiFetch('/crm/messaging/history', { token });
            setHistory(Array.isArray(data) ? data.map(normalizeHistoryRow) : []);
        } catch (err) {
            console.error(err);
            setHistory([]);
            addToast('No se pudo cargar el historial de mensajeria', 'error');
        }
    }, [addToast, token]);

    useEffect(() => { fetchHistory(); }, [fetchHistory]);


    const handleSendCampaign = async () => {
        if (!canEditCrm) return;
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
                    campaign_name: campaignName,
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
        if (!canEditCrm) return;
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
        const map = {} as Record<string, any[]>;
        for (const item of history) {
            const key = item.date || 'Sin fecha';
            if (!map[key]) map[key] = [];
            map[key].push(item);
        }
        return Object.entries(map);
    }, [history]);

    return (
        <CrmShell
            breadcrumbs={[
                { label: 'Consolidación', icon: Users },
                { label: 'Centro de Mensajería', icon: Send }
            ]}
            viewOptions={['table', 'list', 'grid', 'board', 'kanban', 'gantt', 'calendar', 'wiki']}
            viewType={viewType}
            onViewChange={setViewType}
            rightActions={canEditCrm ? (
                <button className="flex items-center gap-2 px-4 py-2 bg-[hsl(var(--surface-1))] dark:bg-white/5 hover:bg-slate-50 rounded-md text-[11px] font-bold uppercase tracking-wide text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-white/10 shadow-sm transition-all active:scale-95">
                    <History size={14} /> Historial Detallado
                </button>
            ) : undefined}
        >
            <div className="flex flex-col h-full bg-slate-50/50 dark:bg-[#1e1f21] overflow-hidden font-display rounded-lg">
                <div className="flex-1 overflow-y-auto scrollbar-thin p-4 lg:p-4">
                {viewType === 'list' && (
 <div className="w-full space-y-3">
                        {history.map((item) => (
                            <div 
                                key={item.id} 
                                onClick={() => router.push(`/plataforma/crm/messaging/${item.id}`)}
                                className="rounded-lg border border-slate-200 dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/5 p-4 flex items-center justify-between hover:border-blue-500/30 transition-all cursor-pointer group"
                            >
                                <div>
                                    <p className="text-sm font-bold text-slate-800 dark:text-slate-100">{item.name}</p>
                                    <p className="text-[11px] text-slate-500">{item.channel} · {item.date} · {item.count} contactos</p>
                                </div>
                                <span className="text-[10px] font-bold uppercase tracking-wide text-slate-400">{item.status}</span>
                            </div>
                        ))}
                        {history.length === 0 && <div className="py-2 text-center text-slate-400 text-sm">Sin campañas recientes</div>}
                    </div>
                )}

                {viewType === 'table' && (
 <div className="w-full rounded-lg border border-slate-200 dark:border-white/10 overflow-x-auto bg-[hsl(var(--surface-1))] dark:bg-white/5">
                        <table className="w-full min-w-[480px] text-left">
                            <thead className="bg-slate-50 dark:bg-white/5">
                                <tr>
                                    <th className="px-4 py-1.5 text-[10px] font-bold uppercase tracking-wide text-slate-400">Campaña</th>
                                    <th className="px-4 py-1.5 text-[10px] font-bold uppercase tracking-wide text-slate-400">Canal</th>
                                    <th className="px-4 py-1.5 text-[10px] font-bold uppercase tracking-wide text-slate-400">Fecha</th>
                                    <th className="px-4 py-1.5 text-[10px] font-bold uppercase tracking-wide text-slate-400">Estado</th>
                                    <th className="px-4 py-1.5 text-[10px] font-bold uppercase tracking-wide text-slate-400">Volumen</th>
                                </tr>
                            </thead>
                            <tbody>
                                {history.map((item) => (
                                    <tr 
                                        key={item.id} 
                                        onClick={() => router.push(`/plataforma/crm/messaging/${item.id}`)}
                                        className="border-t border-slate-100 dark:border-white/5 hover:bg-slate-50 dark:hover:bg-white/[0.02] cursor-pointer transition-colors"
                                    >
                                        <td className="px-4 py-1.5 text-sm font-bold text-slate-800 dark:text-slate-100">{item.name}</td>
                                        <td className="px-4 py-1.5 text-xs text-slate-500 uppercase">{item.channel}</td>
                                        <td className="px-4 py-1.5 text-xs text-slate-500">{item.date}</td>
                                        <td className="px-4 py-1.5 text-xs font-bold uppercase text-slate-500">{item.status}</td>
                                        <td className="px-4 py-1.5 text-xs text-slate-500">{item.target_count}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}

                {(viewType === 'board' || viewType === 'kanban') && (
 <div className="w-full grid grid-cols-1 lg:grid-cols-3 gap-4">
                        {groupedByChannel.map(col => (
                            <div key={col.key} className="rounded-lg border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/[0.03] p-3">
                                <div className="mb-3 flex items-center justify-between">
                                    <p className="text-[10px] font-bold uppercase tracking-wide text-slate-500">{col.label}</p>
                                    <span className="text-[10px] font-bold text-slate-400">{col.items.length}</span>
                                </div>
                                <div className="space-y-2">
                                    {col.items.map((item: any) => (
                                        <div 
                                            key={item.id} 
                                            onClick={() => router.push(`/plataforma/crm/messaging/${item.id}`)}
                                            className="rounded-md border border-slate-200 dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/5 p-3 hover:border-blue-500/30 transition-all cursor-pointer"
                                        >
                                            <p className="text-xs font-bold text-slate-800 dark:text-slate-100">{item.name}</p>
                                            <p className="text-[10px] text-slate-400">{item.date} · {item.target_count} envíos</p>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        ))}
                    </div>
                )}

                {viewType === 'calendar' && (
 <div className="w-full space-y-4">
                        {groupedByDate.map(([label, items]) => (
                            <div key={label} className="rounded-lg border border-slate-200 dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/5 p-4">
                                <p className="mb-3 text-[10px] font-bold uppercase tracking-wide text-slate-500">{label}</p>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                    {items.map((item: any) => (
                                        <div 
                                            key={item.id} 
                                            onClick={() => router.push(`/plataforma/crm/messaging/${item.id}`)}
                                            className="rounded-md border border-slate-200 dark:border-white/10 p-3 hover:border-blue-500/30 transition-all cursor-pointer bg-[hsl(var(--surface-1))] dark:bg-white/5"
                                        >
                                            <p className="text-sm font-bold text-slate-800 dark:text-slate-100">{item.name}</p>
                                            <p className="text-[10px] text-slate-400">{item.channel} · {item.status} · {item.target_count}</p>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        ))}
                    </div>
                )}

                {viewType === 'gantt' && (
 <div className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/5 p-4 space-y-3">
                        <p className="text-[10px] font-bold uppercase tracking-wide text-slate-500">Avance de entrega</p>
                        {history.map((item) => (
                            <div 
                                key={item.id} 
                                onClick={() => router.push(`/plataforma/crm/messaging/${item.id}`)}
                                        className="space-y-1 cursor-pointer group p-2 hover:bg-slate-50 dark:hover:bg-white/5 rounded-md transition-all"
                            >
                                <div className="flex items-center justify-between text-[11px]">
                                    <span className="font-bold text-slate-700 dark:text-slate-300">{item.name}</span>
                                    <span className="font-bold text-slate-400">{STATUS_PROGRESS[item.status] ?? 0}%</span>
                                </div>
                                <div className="h-2 rounded-full bg-slate-100 dark:bg-white/10 overflow-hidden">
                                    <div className="h-full bg-[hsl(var(--primary))]" style={{ width: `${STATUS_PROGRESS[item.status] ?? 0}%` }} />
                                </div>
                            </div>
                        ))}
                    </div>
                )}

                {viewType === 'wiki' && (
 <div className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/5 p-4 space-y-3">
                        <p className="text-[10px] font-bold uppercase tracking-wide text-slate-500">Wiki de mensajería</p>
                        <textarea
                            value={wikiNotes}
                            onChange={(e) => setWikiNotes(e.target.value)}
                            placeholder="Documenta políticas por canal, horarios recomendados, segmentación y compliance..."
                            className="w-full min-h-[320px] rounded-lg border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-black/20 p-4 text-sm font-medium text-slate-700 dark:text-slate-200 outline-none focus:ring-2 focus:ring-blue-500/20"
                        />
                    </div>
                )}

                {viewType === 'grid' && (
 <div className="w-full grid grid-cols-1 lg:grid-cols-12 gap-3">
                    
                    {/* Left Column: Composer */}
                    <div className="lg:col-span-7 space-y-3">
                        <section className="bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg p-3 shadow-xl space-y-4 relative overflow-hidden">
                            <div className="absolute top-0 right-0 -mr-12 -mt-3 size-10 bg-blue-600/5 rounded-full blur-3xl" />
                            
                            <div className="relative z-10 flex justify-between items-center">
                                <div>
                                    <h2 className="text-lg font-bold tracking-tight text-slate-900 dark:text-white leading-none mb-2 uppercase">Campaign Composer</h2>
                                    <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">Crea mensajes de alto impacto</p>
                                </div>
                                <div className="flex bg-slate-100 dark:bg-white/5 p-1.5 rounded-lg border border-slate-200 dark:border-white/10">
                                    <ChannelButton active={channel === 'whatsapp'} onClick={() => canEditCrm && setChannel('whatsapp')} icon={MessageSquare} label="WhatsApp" disabled={!canEditCrm} />
                                    <ChannelButton active={channel === 'email'} onClick={() => canEditCrm && setChannel('email')} icon={Mail} label="Email" disabled={!canEditCrm} />
                                    <ChannelButton active={channel === 'sms'} onClick={() => canEditCrm && setChannel('sms')} icon={Smartphone} label="SMS" disabled={!canEditCrm} />
                                </div>
                            </div>

                            <div className="space-y-3">
                                <div className="space-y-2">
                                    <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wide px-4">Nombre de la Campaña</label>
                                        <input 
                                            disabled={!canEditCrm}
                                            value={campaignName} onChange={(e) => setCampaignName(e.target.value)}
                                        placeholder="Ej: Invitación Asamblea de Personas"
                                        className="w-full bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/5 rounded-lg py-2 px-4 text-sm font-medium outline-none focus:ring-4 focus:ring-blue-500/10 transition-all"
                                    />
                                </div>

                                <div className="space-y-2">
                                    <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wide px-4">Mensaje (Personalización con {`{nombre}`})</label>
                                    <div className="relative">
                                        <textarea 
                                            disabled={!canEditCrm}
                                            value={message} onChange={(e) => setMessage(e.target.value)}
                                            placeholder="Hola {nombre}, te escribimos de CCF para..."
                                            className="w-full h-48 bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/5 rounded-md p-4 text-sm font-medium outline-none focus:ring-4 focus:ring-blue-500/10 transition-all resize-none"
                                        />
                                        <div className="absolute bottom-4 right-4 flex gap-2">
                                            <button disabled={!canEditCrm} className="p-2.5 bg-[hsl(var(--surface-1))] dark:bg-white/10 rounded-md text-slate-400 hover:text-[hsl(var(--primary))] transition-colors shadow-sm disabled:opacity-50"><Bot size={18} /></button>
                                            <button disabled={!canEditCrm} className="p-2.5 bg-[hsl(var(--surface-1))] dark:bg-white/10 rounded-md text-slate-400 hover:text-[hsl(var(--primary))] transition-colors shadow-sm disabled:opacity-50"><ImageIcon size={18} /></button>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <div className="pt-6 border-t border-slate-100 dark:border-white/5 flex items-center justify-between">
                                <div className="flex gap-2">
                                    <button disabled={!canEditCrm} className="flex items-center gap-2 px-4 py-2 text-[10px] font-bold uppercase tracking-wide text-slate-400 hover:text-slate-600 transition-colors disabled:opacity-50">
                                        <FileText size={14} /> Guardar Borrador
                                    </button>
                                </div>
                                <button 
                                    onClick={handleSendCampaign} disabled={isSending || !canEditCrm}
                                    className="flex items-center gap-3 px-3 py-2 bg-[hsl(var(--primary))] text-white rounded-lg text-[11px] font-bold uppercase tracking-wide shadow-xl shadow-blue-500/20 active:scale-95 transition-all disabled:opacity-50"
                                >
                                    {isSending ? <Clock size={18} className="animate-spin" /> : <Zap size={18} fill="currentColor" />}
                                    Lanzar Campaña
                                </button>
                            </div>
                        </section>

                        <section className="bg-blue-50 dark:bg-blue-900/10 rounded-lg p-3 border border-blue-100 dark:border-blue-500/20 space-y-3">
                            <div className="flex items-center gap-3 text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))]">
                                <Sparkles size={20} />
                                <h3 className="text-[11px] font-bold uppercase tracking-wide">IA Copywriting Helper</h3>
                            </div>
                            <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed font-medium italic">
                                &ldquo;Optimus sugiere: Los mensajes enviados por WhatsApp entre las 10:00 AM y 11:30 AM tienen un 25% más de tasa de respuesta en el segmento de Líderes.&rdquo;
                            </p>
                        </section>
                    </div>

                    {/* Right Column: Targeting & History */}
                    <div className="lg:col-span-5 space-y-3">
                        <section className="bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg p-3 shadow-xl space-y-3">
                            <div className="flex items-center justify-between">
                                <h3 className="text-sm font-bold tracking-tight uppercase tracking-wide leading-none">Audiencia</h3>
                                <Filter size={18} className="text-slate-300" />
                            </div>
                            <div className="grid grid-cols-2 gap-3">
                                <SegmentTag label="Personas Activos" active={segments.includes('active')} onClick={() => toggleSegment('active')} disabled={!canEditCrm} />
                                <SegmentTag label="Nuevos Visitantes" active={segments.includes('new')} onClick={() => toggleSegment('new')} disabled={!canEditCrm} />
                                <SegmentTag label="Pastores & Staff" active={segments.includes('staff')} onClick={() => toggleSegment('staff')} disabled={!canEditCrm} />
                                <SegmentTag label="Grupos" active={segments.includes('groups')} onClick={() => toggleSegment('groups')} disabled={!canEditCrm} />
                                <SegmentTag label="Baja Asistencia" active={segments.includes('low')} onClick={() => toggleSegment('low')} disabled={!canEditCrm} />
                                <SegmentTag label="Donantes Pro" active={segments.includes('vip')} onClick={() => toggleSegment('vip')} disabled={!canEditCrm} />
                            </div>
                            <div className="p-4 bg-slate-50 dark:bg-black/20 rounded-md border border-slate-100 dark:border-white/5 flex items-center justify-between">
                                <div className="flex items-center gap-4">
                                    <div className="size-8 rounded-md bg-blue-100 flex items-center justify-center text-[hsl(var(--primary))]"><Users size={20} /></div>
                                    <div>
                                        <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wide mb-0.5">Segmentos Seleccionados</p>
                                        <h4 className="text-base font-bold text-slate-900 dark:text-white">{segments.length} <span className="text-[10px] text-slate-400 font-bold tracking-normal uppercase">Segmentos</span></h4>
                                    </div>
                                </div>
                                <Target size={20} className="text-[hsl(var(--primary))]" />
                            </div>
                        </section>

                        <section className="bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg p-3 shadow-xl space-y-3">
                            <div className="flex items-center justify-between">
                                <h3 className="text-sm font-bold tracking-tight uppercase tracking-wide leading-none">Actividad Reciente</h3>
                                <BarChart3 size={18} className="text-slate-300" />
                            </div>
                            <div className="space-y-3">
                                {history.map((item) => (
                                    <div 
                                        key={item.id} 
                                        onClick={() => router.push(`/plataforma/crm/messaging/${item.id}`)}
                                        className="flex items-center justify-between group cursor-pointer hover:bg-slate-50 dark:hover:bg-white/5 p-2 rounded-lg transition-all"
                                    >
                                        <div className="flex items-center gap-4">
                                            <div className={clsx(
                                                "size-9 rounded-lg flex items-center justify-center transition-all group-hover:scale-110",
                                                item.channel === 'whatsapp' ? "bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600" : "bg-blue-50 dark:bg-blue-900/20 text-[hsl(var(--primary))]"
                                            )}>
                                                {item.channel === 'whatsapp' ? <MessageSquare size={20} /> : <Mail size={20} />}
                                            </div>
                                            <div>
                                                <h4 className="text-xs font-bold text-slate-800 dark:text-white uppercase leading-tight mb-1">{item.name}</h4>
                                                <div className="flex items-center gap-2">
                                                    <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wide">{item.date}</span>
                                                    <div className="size-1 rounded-full bg-slate-300" />
                                                    <span className="text-[9px] font-bold text-[hsl(var(--primary))] uppercase">{item.count} envíos</span>
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
                            <button className="w-full py-2 bg-slate-900 dark:bg-white/5 text-white rounded-lg text-[10px] font-bold uppercase tracking-wide hover:bg-slate-800 transition-all">
                                Ver Reporte Completo
                            </button>
                        </section>
                    </div>
                </div>
                )}

                {!['table', 'list', 'grid', 'board', 'kanban', 'gantt', 'calendar', 'wiki'].includes(viewType) && (
                    <CrmViewPlaceholder moduleName="Centro de Mensajeria" viewType={viewType} />
                )}
                </div>
            </div>
        </CrmShell>
    );
}
