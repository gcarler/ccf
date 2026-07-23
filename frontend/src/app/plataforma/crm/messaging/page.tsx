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
import { extractErrorMessage, apiFetch } from '@/lib/http';
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
        id: String(row?.id ?? ''),
        name: row?.name ?? row?.campaign_name ?? row?.persona_name ?? `Mensaje #${row?.id ?? 0}`,
        campaign_name: row?.campaign_name,
        channel: (String(row?.channel || 'whatsapp').toLowerCase() as Channel),
        status: String(row?.status || 'sent'),
        count: Number(row?.count ?? row?.target_count ?? 1),
        date: sentAt && !Number.isNaN(sentAt.getTime()) ? sentAt.toLocaleString() : String(row?.date || 'Sin fecha'),
        target_count: targetCount,
        delivered_count: deliveredCount,
        failed_count: failedCount,
        external_id: row?.external_id ?? null,
        log_ids: Array.isArray(row?.log_ids) ? row.log_ids.map(String) : undefined,
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
    const [history, setHistory] = useState<MessagingHistoryRow[]>([]);
    const [historyError, setHistoryError] = useState<string | null>(null);
    const [isSending, setIsSending] = useState(false);
    const [loadingHistory, setLoadingHistory] = useState(true);
    const [campaignErrors, setCampaignErrors] = useState<{ campaignName?: boolean; message?: boolean; segments?: boolean }>({});
    const [viewType, setViewType] = useState<ViewType>(() => getStoredView('crm_messaging_view', 'grid'));
    const { content: wikiNotes, setContent: setWikiNotes } = useWikiDocument('crm_messaging_wiki_notes', {
        title: 'Wiki de mensajeria CRM',
    });

    const fetchHistory = useCallback(async () => {
        if (!token) {
            setHistory([]);
            setLoadingHistory(false);
            return;
        }
        setLoadingHistory(true);
        try {
            setHistoryError(null);
            const data = await apiFetch('/crm/messaging/history', { token });
            setHistory(Array.isArray(data) ? data.map(normalizeHistoryRow) : []);
        } catch (err) {
            setHistory([]);
            const message = extractErrorMessage(err, 'No se pudo cargar el historial de mensajeria');
            setHistoryError(message);
            addToast(message, 'error');
        } finally {
            setLoadingHistory(false);
        }
    }, [addToast, token]);

    useEffect(() => { fetchHistory(); }, [fetchHistory]);


    const handleSendCampaign = async () => {
        if (!canEditCrm) return;
        const newErrors = {
            campaignName: !campaignName.trim(),
            message: !message.trim(),
            segments: segments.length === 0,
        };
        setCampaignErrors(newErrors);
        if (newErrors.campaignName || newErrors.message || newErrors.segments) {
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
                <button className="flex items-center gap-2 px-4 py-2 bg-[hsl(var(--surface-1))] dark:bg-white/5 hover:bg-[hsl(var(--surface-1))] rounded-md text-[11px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] border border-[hsl(var(--border))] dark:border-white/10 shadow-sm transition-all active:scale-95">
                    <History size={14} /> Historial Detallado
                </button>
            ) : undefined}
        >
            <div className="flex flex-col h-full bg-[hsl(var(--surface-1))]/50 dark:bg-[hsl(var(--surface-1))] overflow-hidden font-display rounded-lg">
                {historyError && (
                    <div className="mx-4 mt-4 rounded-lg border border-[hsl(var(--warning)/30%)]/60 bg-warning-soft dark:bg-[hsl(var(--warning))]/10 dark:border-[hsl(var(--warning)/100%)]/30 p-3 flex flex-col md:flex-row md:items-center md:justify-between gap-3">
                        <div className="min-w-0">
                            <p className="text-[11px] font-bold uppercase tracking-wide text-warning-text dark:text-[hsl(var(--warning))]">
                                No se pudo cargar la mensajería
                            </p>
                            <p className="text-sm text-warning-text/80 dark:text-[hsl(var(--warning)/80%)] mt-1 break-words">
                                {historyError}
                            </p>
                        </div>
                        <button
                            onClick={fetchHistory}
                            className="shrink-0 px-3 py-2 rounded-lg bg-[hsl(var(--primary))] text-white text-[10px] font-bold uppercase tracking-wide shadow-lg shadow-[hsl(var(--info)/20%)] hover:opacity-90 transition-all"
                        >
                            Reintentar
                        </button>
                    </div>
                )}
                <div className="flex-1 overflow-y-auto scrollbar-thin p-4 lg:p-4">
                {viewType === 'list' && (
 <div className="w-full space-y-3">
                        {loadingHistory ? (
                            [...Array(4)].map((_, i) => (
                                <div key={i} className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/5 p-4 animate-pulse">
                                    <div className="flex items-center justify-between">
                                        <div className="space-y-2">
                                            <div className="h-4 w-32 rounded bg-[hsl(var(--surface-2))] dark:bg-white/10" />
                                            <div className="h-3 w-48 rounded bg-[hsl(var(--surface-2))] dark:bg-white/10" />
                                        </div>
                                        <div className="h-4 w-16 rounded bg-[hsl(var(--surface-2))] dark:bg-white/10" />
                                    </div>
                                </div>
                            ))
                        ) : history.map((item) => (
                            <div 
                                key={item.id} 
                                onClick={() => router.push(`/plataforma/crm/messaging/${item.id}`)}
                                role="button"
                                tabIndex={0}
                                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); router.push(`/plataforma/crm/messaging/${item.id}`); } }}
                                className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/5 p-4 flex items-center justify-between hover:border-[hsl(var(--info)/100%)]/30 transition-all cursor-pointer group"
                            >
                                <div>
                                    <p className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">{item.name}</p>
                                    <p className="text-[11px] text-[hsl(var(--text-secondary))]">{item.channel} · {item.date} · {item.count} contactos</p>
                                </div>
                                <span className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{item.status}</span>
                            </div>
                        ))}
                        {!historyError && history.length === 0 && <div className="py-2 text-center text-[hsl(var(--text-secondary))] text-sm">Sin campañas recientes</div>}
                    </div>
                )}

                {viewType === 'table' && (
 <div className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 overflow-x-auto bg-[hsl(var(--surface-1))] dark:bg-white/5">
                        <table className="w-full min-w-[480px] text-left">
                            <thead className="bg-[hsl(var(--surface-1))] dark:bg-white/5">
                                <tr>
                                    <th className="px-4 py-1.5 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Campaña</th>
                                    <th className="px-4 py-1.5 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Canal</th>
                                    <th className="px-4 py-1.5 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Fecha</th>
                                    <th className="px-4 py-1.5 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Estado</th>
                                    <th className="px-4 py-1.5 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Volumen</th>
                                </tr>
                            </thead>
                            <tbody>
                                {loadingHistory ? (
                                    [...Array(4)].map((_, i) => (
                                        <tr key={i} className="border-t border-[hsl(var(--border))] dark:border-white/5">
                                            <td colSpan={5} className="px-4 py-3"><div className="h-4 w-3/4 rounded bg-[hsl(var(--surface-2))] dark:bg-white/10 animate-pulse" /></td>
                                        </tr>
                                    ))
                                ) : history.map((item) => (
                                    <tr 
                                        key={item.id} 
                                        onClick={() => router.push(`/plataforma/crm/messaging/${item.id}`)}
                                        role="button"
                                        tabIndex={0}
                                        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); router.push(`/plataforma/crm/messaging/${item.id}`); } }}
                                        className="border-t border-[hsl(var(--border))] dark:border-white/5 hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/[0.02] cursor-pointer transition-colors"
                                    >
                                        <td className="px-4 py-1.5 text-sm font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">{item.name}</td>
                                        <td className="px-4 py-1.5 text-xs text-[hsl(var(--text-secondary))] uppercase">{item.channel}</td>
                                        <td className="px-4 py-1.5 text-xs text-[hsl(var(--text-secondary))]">{item.date}</td>
                                        <td className="px-4 py-1.5 text-xs font-bold uppercase text-[hsl(var(--text-secondary))]">{item.status}</td>
                                        <td className="px-4 py-1.5 text-xs text-[hsl(var(--text-secondary))]">{item.target_count}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}

                {(viewType === 'board' || viewType === 'kanban') && (
 <div className="w-full grid grid-cols-1 lg:grid-cols-3 gap-4">
                        {loadingHistory ? (
                            ['WhatsApp', 'Email', 'SMS'].map((label, i) => (
                                <div key={i} className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/[0.03] p-3">
                                    <div className="mb-3 flex items-center justify-between">
                                        <div className="h-3 w-16 rounded bg-[hsl(var(--surface-2))] dark:bg-white/10 animate-pulse" />
                                        <div className="h-3 w-4 rounded bg-[hsl(var(--surface-2))] dark:bg-white/10 animate-pulse" />
                                    </div>
                                    <div className="space-y-2">
                                        {[...Array(2)].map((_, j) => (
                                            <div key={j} className="h-14 rounded-md bg-[hsl(var(--surface-2))] dark:bg-white/5 animate-pulse p-3 space-y-2">
                                                <div className="h-3 w-2/3 rounded bg-[hsl(var(--surface-3))] dark:bg-white/10" />
                                                <div className="h-2 w-1/2 rounded bg-[hsl(var(--surface-3))] dark:bg-white/10" />
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            ))
                        ) : groupedByChannel.map(col => (
                            <div key={col.key} className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/[0.03] p-3">
                                <div className="mb-3 flex items-center justify-between">
                                    <p className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{col.label}</p>
                                    <span className="text-[10px] font-bold text-[hsl(var(--text-secondary))]">{col.items.length}</span>
                                </div>
                                <div className="space-y-2">
                                    {col.items.map((item: any) => (
                                        <div 
                                            key={item.id} 
                                            onClick={() => router.push(`/plataforma/crm/messaging/${item.id}`)}
                                            role="button"
                                            tabIndex={0}
                                            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); router.push(`/plataforma/crm/messaging/${item.id}`); } }}
                                            className="rounded-md border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/5 p-3 hover:border-[hsl(var(--info)/100%)]/30 transition-all cursor-pointer"
                                        >
                                            <p className="text-xs font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">{item.name}</p>
                                            <p className="text-[10px] text-[hsl(var(--text-secondary))]">{item.date} · {item.target_count} envíos</p>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        ))}
                    </div>
                )}

                {viewType === 'calendar' && (
 <div className="w-full space-y-4">
                            {loadingHistory ? (
                                [...Array(2)].map((_, i) => (
                                    <div key={i} className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/5 p-4 animate-pulse">
                                        <div className="h-3 w-24 rounded bg-[hsl(var(--surface-2))] dark:bg-white/10 mb-3" />
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                            {[...Array(2)].map((_, j) => (
                                                <div key={j} className="h-16 rounded-md bg-[hsl(var(--surface-2))] dark:bg-white/5 p-3 space-y-2">
                                                    <div className="h-3 w-2/3 rounded bg-[hsl(var(--surface-3))] dark:bg-white/10" />
                                                    <div className="h-2 w-1/2 rounded bg-[hsl(var(--surface-3))] dark:bg-white/10" />
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                ))
                            ) : !historyError && groupedByDate.map(([label, items]) => (
                            <div key={label} className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/5 p-4">
                                <p className="mb-3 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{label}</p>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                    {items.map((item: any) => (
                                        <div 
                                            key={item.id} 
                                            onClick={() => router.push(`/plataforma/crm/messaging/${item.id}`)}
                                            role="button"
                                            tabIndex={0}
                                            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); router.push(`/plataforma/crm/messaging/${item.id}`); } }}
                                            className="rounded-md border border-[hsl(var(--border))] dark:border-white/10 p-3 hover:border-[hsl(var(--info)/100%)]/30 transition-all cursor-pointer bg-[hsl(var(--surface-1))] dark:bg-white/5"
                                        >
                                            <p className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">{item.name}</p>
                                            <p className="text-[10px] text-[hsl(var(--text-secondary))]">{item.channel} · {item.status} · {item.target_count}</p>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        ))}
                    </div>
                )}

                {viewType === 'gantt' && (
 <div className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/5 p-4 space-y-3">
                        <p className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Avance de entrega</p>
                        {loadingHistory ? (
                            [...Array(3)].map((_, i) => (
                                <div key={i} className="space-y-1 p-2 animate-pulse">
                                    <div className="flex items-center justify-between">
                                        <div className="h-3 w-32 rounded bg-[hsl(var(--surface-2))] dark:bg-white/10" />
                                        <div className="h-3 w-8 rounded bg-[hsl(var(--surface-2))] dark:bg-white/10" />
                                    </div>
                                    <div className="h-2 rounded-full bg-[hsl(var(--surface-2))] dark:bg-white/10" />
                                </div>
                            ))
                        ) : history.map((item) => (
                            <div 
                                key={item.id} 
                                onClick={() => router.push(`/plataforma/crm/messaging/${item.id}`)}
                                role="button"
                                tabIndex={0}
                                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); router.push(`/plataforma/crm/messaging/${item.id}`); } }}
                                className="space-y-1 cursor-pointer group p-2 hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 rounded-md transition-all"
                            >
                                <div className="flex items-center justify-between text-[11px]">
                                    <span className="font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">{item.name}</span>
                                    <span className="font-bold text-[hsl(var(--text-secondary))]">{STATUS_PROGRESS[item.status] ?? 0}%</span>
                                </div>
                                <div className="h-2 rounded-full bg-[hsl(var(--surface-2))] dark:bg-white/10 overflow-hidden">
                                    <div className="h-full bg-[hsl(var(--primary))]" style={{ width: `${STATUS_PROGRESS[item.status] ?? 0}%` }} />
                                </div>
                            </div>
                        ))}
                    </div>
                )}

                {viewType === 'wiki' && (
 <div className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/5 p-4 space-y-3">
                        <p className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Wiki de mensajería</p>
                        <textarea
                            value={wikiNotes}
                            onChange={(e) => setWikiNotes(e.target.value)}
                            placeholder="Documenta políticas por canal, horarios recomendados, segmentación y compliance..."
                            className="w-full min-h-[320px] rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-black/20 p-4 text-sm font-medium text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.2]"
                        />
                    </div>
                )}

                {viewType === 'grid' && (
 <div className="w-full grid grid-cols-1 lg:grid-cols-12 gap-3">
                    
                    {/* Left Column: Composer */}
                    <div className="lg:col-span-7 space-y-3">
                        <section className="bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg p-3 shadow-xl space-y-4 relative overflow-hidden">
                            <div className="absolute top-0 right-0 -mr-12 -mt-3 size-10 bg-[hsl(var(--info))]/5 rounded-full blur-3xl" />
                            
                            <div className="relative z-10 flex justify-between items-center">
                                <div>
                                    <h2 className="text-lg font-bold tracking-tight text-[hsl(var(--text-primary))] dark:text-white leading-none mb-2 uppercase">Campaign Composer</h2>
                                    <p className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Crea mensajes de alto impacto</p>
                                </div>
                                <div className="flex bg-[hsl(var(--surface-2))] dark:bg-white/5 p-1.5 rounded-lg border border-[hsl(var(--border))] dark:border-white/10">
                                    <ChannelButton active={channel === 'whatsapp'} onClick={() => canEditCrm && setChannel('whatsapp')} icon={MessageSquare} label="WhatsApp" disabled={!canEditCrm} />
                                    <ChannelButton active={channel === 'email'} onClick={() => canEditCrm && setChannel('email')} icon={Mail} label="Email" disabled={!canEditCrm} />
                                    <ChannelButton active={channel === 'sms'} onClick={() => canEditCrm && setChannel('sms')} icon={Smartphone} label="SMS" disabled={!canEditCrm} />
                                </div>
                            </div>

                            <div className="space-y-3">
                                <div className="space-y-2">
                                    <label className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide px-4">Nombre de la Campaña</label>
                                        <input 
                                            required
                                            disabled={!canEditCrm}
                                            aria-invalid={!!campaignErrors.campaignName}
                                            aria-describedby="campaignName-error"
                                            value={campaignName} onChange={(e) => setCampaignName(e.target.value)}
                                        placeholder="Ej: Invitación Asamblea de Personas"
                                        className={`w-full bg-[hsl(var(--surface-1))] dark:bg-black/20 border rounded-lg py-2 px-4 text-sm font-medium outline-none focus:ring-4 focus:ring-[hsl(var(--primary))]/10 transition-all ${campaignErrors.campaignName ? 'border-red-500 dark:border-red-500/50' : 'border-[hsl(var(--border))] dark:border-white/5'}`}
                                    />
                                    {campaignErrors.campaignName && <p id="campaignName-error" className="text-red-500 text-xs mt-1">Campo requerido</p>}
                                </div>

                                <div className="space-y-2">
                                    <label className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide px-4">Mensaje (Personalización con {`{nombre}`})</label>
                                    <div className="relative">
                                        <textarea 
                                            required
                                            disabled={!canEditCrm}
                                            aria-invalid={!!campaignErrors.message}
                                            aria-describedby="message-error"
                                            value={message} onChange={(e) => setMessage(e.target.value)}
                                            placeholder="Hola {nombre}, te escribimos de CCF para..."
                                            className={`w-full h-48 bg-[hsl(var(--surface-1))] dark:bg-black/20 border rounded-md p-4 text-sm font-medium outline-none focus:ring-4 focus:ring-[hsl(var(--primary))]/10 transition-all resize-none ${campaignErrors.message ? 'border-red-500 dark:border-red-500/50' : 'border-[hsl(var(--border))] dark:border-white/5'}`}
                                        />
                                        <div className="absolute bottom-4 right-4 flex gap-2">
                                            <button disabled={!canEditCrm} aria-label="Generar con IA" className="p-2.5 bg-[hsl(var(--surface-1))] dark:bg-white/10 rounded-md text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] transition-colors shadow-sm disabled:opacity-50"><Bot size={18} /></button>
                                            <button disabled={!canEditCrm} aria-label="Insertar imagen" className="p-2.5 bg-[hsl(var(--surface-1))] dark:bg-white/10 rounded-md text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] transition-colors shadow-sm disabled:opacity-50"><ImageIcon size={18} /></button>
                                        </div>
                                    </div>
                                    {campaignErrors.message && <p id="message-error" className="text-red-500 text-xs mt-1">Campo requerido</p>}
                                    {campaignErrors.segments && <p className="text-red-500 text-xs mt-1">Selecciona al menos un segmento</p>}
                                </div>
                            </div>

                            <div className="pt-6 border-t border-[hsl(var(--border))] dark:border-white/5 flex items-center justify-between">
                                <div className="flex gap-2">
                                    <button disabled={!canEditCrm} className="flex items-center gap-2 px-4 py-2 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-secondary))] transition-colors disabled:opacity-50">
                                        <FileText size={14} /> Guardar Borrador
                                    </button>
                                </div>
                                <button 
                                    onClick={handleSendCampaign} disabled={isSending || !canEditCrm}
                                    className="flex items-center gap-3 px-3 py-2 bg-[hsl(var(--primary))] text-white rounded-lg text-[11px] font-bold uppercase tracking-wide shadow-xl shadow-[hsl(var(--info)/20%)] active:scale-95 transition-all disabled:opacity-50"
                                >
                                    {isSending ? <Clock size={18} className="animate-spin" /> : <Zap size={18} fill="currentColor" />}
                                    Lanzar Campaña
                                </button>
                            </div>
                        </section>

                        <section className="bg-info-soft dark:bg-[hsl(var(--info))]/10 rounded-lg p-3 border border-[hsl(var(--info)/20%)] dark:border-[hsl(var(--info)/100%)]/20 space-y-3">
                            <div className="flex items-center gap-3 text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))]">
                                <Sparkles size={20} />
                                <h3 className="text-[11px] font-bold uppercase tracking-wide">IA Copywriting Helper</h3>
                            </div>
                            <p className="text-sm text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] leading-relaxed font-medium italic">
                                &ldquo;Optimus sugiere: Los mensajes enviados por WhatsApp entre las 10:00 AM y 11:30 AM tienen un 25% más de tasa de respuesta en el segmento de Líderes.&rdquo;
                            </p>
                        </section>
                    </div>

                    {/* Right Column: Targeting & History */}
                    <div className="lg:col-span-5 space-y-3">
                        <section className="bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg p-3 shadow-xl space-y-3">
                            <div className="flex items-center justify-between">
                                <h3 className="text-sm font-bold tracking-tight uppercase tracking-wide leading-none">Audiencia</h3>
                                <Filter size={18} className="text-[hsl(var(--text-secondary))]" />
                            </div>
                            <div className="grid grid-cols-2 gap-3">
                                <SegmentTag label="Personas Activos" active={segments.includes('active')} onClick={() => toggleSegment('active')} disabled={!canEditCrm} />
                                <SegmentTag label="Nuevos Visitantes" active={segments.includes('new')} onClick={() => toggleSegment('new')} disabled={!canEditCrm} />
                                <SegmentTag label="Pastores & Staff" active={segments.includes('staff')} onClick={() => toggleSegment('staff')} disabled={!canEditCrm} />
                                <SegmentTag label="Grupos" active={segments.includes('groups')} onClick={() => toggleSegment('groups')} disabled={!canEditCrm} />
                                <SegmentTag label="Baja Asistencia" active={segments.includes('low')} onClick={() => toggleSegment('low')} disabled={!canEditCrm} />
                                <SegmentTag label="Donantes Pro" active={segments.includes('vip')} onClick={() => toggleSegment('vip')} disabled={!canEditCrm} />
                            </div>
                            <div className="p-4 bg-[hsl(var(--surface-1))] dark:bg-black/20 rounded-md border border-[hsl(var(--border))] dark:border-white/5 flex items-center justify-between">
                                <div className="flex items-center gap-4">
                                    <div className="size-8 rounded-md bg-[hsl(var(--info-muted))] flex items-center justify-center text-[hsl(var(--primary))]"><Users size={20} /></div>
                                    <div>
                                        <p className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide mb-0.5">Segmentos Seleccionados</p>
                                        <h4 className="text-base font-bold text-[hsl(var(--text-primary))] dark:text-white">{segments.length} <span className="text-[10px] text-[hsl(var(--text-secondary))] font-bold tracking-normal uppercase">Segmentos</span></h4>
                                    </div>
                                </div>
                                <Target size={20} className="text-[hsl(var(--primary))]" />
                            </div>
                        </section>

                        <section className="bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg p-3 shadow-xl space-y-3">
                            <div className="flex items-center justify-between">
                                <h3 className="text-sm font-bold tracking-tight uppercase tracking-wide leading-none">Actividad Reciente</h3>
                                <BarChart3 size={18} className="text-[hsl(var(--text-secondary))]" />
                            </div>
                            <div className="space-y-3">
                                {loadingHistory ? (
                                    <div className="space-y-3">{[1,2,3].map(i => <div key={i} className="h-16 bg-gray-100 dark:bg-white/5 rounded animate-pulse" />)}</div>
                                ) : history.map((item) => (
                                    <div 
                                        key={item.id} 
                                        onClick={() => router.push(`/plataforma/crm/messaging/${item.id}`)}
                                        role="button"
                                        tabIndex={0}
                                        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); router.push(`/plataforma/crm/messaging/${item.id}`); } }}
                                        className="flex items-center justify-between group cursor-pointer hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 p-2 rounded-lg transition-all"
                                    >
                                        <div className="flex items-center gap-4">
                                            <div className={clsx(
                                                "size-9 rounded-lg flex items-center justify-center transition-all group-hover:scale-110",
                                                item.channel === 'whatsapp' ? "bg-success-soft dark:bg-[hsl(var(--success))]/20 text-success-text" : "bg-info-soft dark:bg-[hsl(var(--info))]/20 text-[hsl(var(--primary))]"
                                            )}>
                                                {item.channel === 'whatsapp' ? <MessageSquare size={20} /> : <Mail size={20} />}
                                            </div>
                                            <div>
                                                <h4 className="text-xs font-bold text-[hsl(var(--text-primary))] dark:text-white uppercase leading-tight mb-1">{item.name}</h4>
                                                <div className="flex items-center gap-2">
                                                    <span className="text-[9px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">{item.date}</span>
                                                    <div className="size-1 rounded-full bg-[hsl(var(--surface-2))]" />
                                                    <span className="text-[9px] font-bold text-[hsl(var(--primary))] uppercase">{item.count} envíos</span>
                                                </div>
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-3">
                                            {item.status === 'sent' && <CheckCircle2 size={16} className="text-[hsl(var(--success))]" />}
                                            {item.status === 'delivered' && <Zap size={16} fill="currentColor" className="text-[hsl(var(--warning))]" />}
                                            {item.status === 'failed' && <AlertCircle size={16} className="text-[hsl(var(--danger))]" />}
                                            <ChevronRight size={16} className="text-[hsl(var(--text-secondary))] opacity-0 group-hover:opacity-100 transition-all group-hover:translate-x-1" />
                                        </div>
                                    </div>
                                ))}
                            </div>
                            <button className="w-full py-2 bg-[hsl(var(--bg-muted))] dark:bg-white/5 text-white rounded-lg text-[10px] font-bold uppercase tracking-wide hover:bg-[hsl(var(--surface-2))] transition-all">
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
