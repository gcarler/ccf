"use client";

import CrmShell from '@/components/crm/CrmShell';
import CrmViewPlaceholder from '@/components/crm/CrmViewPlaceholder';
import Skeleton from '@/components/ui/Skeleton';
import { ViewType,getStoredView } from '@/components/ViewSwitcher';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { useWikiDocument } from '@/hooks/useWikiDocument';
import { apiFetch } from '@/lib/http';
import clsx from 'clsx';
import {
BookOpen,
Calendar,
ChevronLeft,
ChevronRight,
Download,
Filter,
Globe,
Loader2,
Mail,
Search,
Tag,
Users
} from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useCallback,useEffect,useMemo,useState } from 'react';

interface NewsletterLead {
    case_id: number;
    persona_id: string | null;
    nombre_completo?: string;
    first_name?: string;
    last_name?: string;
    email: string | null;
    phone: string | null;
    source: string;
    stage: string;
    notes: string | null;
    created_at: string | null;
}

interface NewsletterResponse {
    leads: NewsletterLead[];
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
}

const STAGE_LABELS: Record<string, string> = {
    new: 'Nuevo',
    call: 'Por Llamar',
    visit: 'Visita',
    discipleship: 'Discipulado',
    consolidated: 'Consolidado',
};

const STAGE_COLORS: Record<string, string> = {
    new: 'bg-blue-500/10 text-[hsl(var(--primary))] border-blue-500/20',
    call: 'bg-amber-500/10 text-amber-600 border-amber-500/20',
    visit: 'bg-sky-500/10 text-sky-600 border-sky-500/20',
    discipleship: 'bg-[hsl(var(--primary))]/10 text-[hsl(var(--primary))] border-[hsl(var(--primary))]/20',
    consolidated: 'bg-emerald-500/10 text-emerald-600 border-emerald-500/20',
};

export default function NewsletterLeadsPage() {
    const { token } = useAuth();
    const { addToast } = useToast();
    const router = useRouter();

    const [data, setData] = useState<NewsletterResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [exporting, setExporting] = useState(false);
    const [searchQuery, setSearchQuery] = useState('');
    const [page, setPage] = useState(1);
    const [viewType, setViewType] = useState<ViewType>(() => getStoredView('crm_newsletter_view', 'list'));
    const [dateFrom, setDateFrom] = useState('');
    const [showFilters, setShowFilters] = useState(false);
    const { content: wikiNotes, setContent: setWikiNotes } = useWikiDocument('crm_newsletter_wiki_notes', {
        title: 'Wiki de leads de newsletter',
    });

    const fetchLeads = useCallback(async () => {
        if (!token) return;
        setLoading(true);
        try {
            const params = new URLSearchParams({ page: String(page), page_size: '50' });
            if (dateFrom) params.set('date_from', dateFrom);
            const res = await apiFetch<NewsletterResponse>(`/crm/leads/newsletter?${params}`, {
                token, cache: 'no-store',
            });
            setData(res);
        } catch {
            addToast('Error al cargar leads del newsletter', 'error');
        } finally {
            setLoading(false);
        }
    }, [token, page, dateFrom, addToast]);

    useEffect(() => { fetchLeads(); }, [fetchLeads]);

    const filteredLeads = useMemo(() => {
        if (!data?.leads) return [];
        if (!searchQuery.trim()) return data.leads;
        const q = searchQuery.toLowerCase();
        return data.leads.filter(l =>
            `${l.nombre_completo || `${l.first_name ?? ''} ${l.last_name ?? ''}`.trim()}`.toLowerCase().includes(q) ||
            (l.email || '').toLowerCase().includes(q) ||
            (l.notes || '').toLowerCase().includes(q)
        );
    }, [data, searchQuery]);

    const handleExport = async () => {
        if (!token) return;
        setExporting(true);
        try {
            const params = new URLSearchParams();
            if (dateFrom) params.set('date_from', dateFrom);
            const res = await apiFetch<{ rows: Record<string, string>[]; count: number }>(
                `/crm/leads/export-newsletter?${params}`, { token, cache: 'no-store' }
            );
            if (!res.rows?.length) {
                addToast('No hay datos para exportar', 'warning');
                return;
            }
            const headers = Object.keys(res.rows.find(Boolean) ?? {});
            if (headers.length === 0) {
                addToast('No se pudo determinar la estructura del CSV', 'error');
                return;
            }
            const csv = [
                headers.join(','),
                ...res.rows.map(r => headers.map(h => `"${(r[h] || '').replace(/"/g, '""')}"`).join(',')),
            ].join('\n');
            const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `newsletter-leads-${new Date().toISOString().slice(0, 10)}.csv`;
            a.click();
            URL.revokeObjectURL(url);
            addToast(`${res.count} registros exportados`, 'success');
        } catch {
            addToast('Error al exportar', 'error');
        } finally {
            setExporting(false);
        }
    };

    const summary = useMemo(() => {
        if (!data?.leads) return null;
        const total = data.leads.length;
        const withEmail = data.leads.filter(l => l.email).length;
        const withPhone = data.leads.filter(l => l.phone).length;
        const newCount = data.leads.filter(l => l.stage === 'new').length;
        const landingPages = new Set(
            data.leads.map(l => l.notes?.match(/Landing: (.+)/)?.[1]).filter(Boolean)
        );
        return { total, withEmail, withPhone, newCount, landingPages: landingPages.size };
    }, [data]);

    return (
        <CrmShell
            breadcrumbs={[
                { label: 'Newsletter', icon: Mail },
                { label: 'Suscriptores CRM', icon: Users },
            ]}
            viewOptions={['list', 'table', 'calendar', 'wiki']}
            viewType={viewType}
            onViewChange={setViewType}
            rightActions={
                <div className="flex gap-2">
                    <button
                        onClick={() => setShowFilters(!showFilters)}
                        className={clsx(
                            "flex items-center gap-2 px-3 py-2 rounded-md text-[11px] font-bold uppercase tracking-wide transition-all",
                            showFilters
                                ? "bg-[hsl(var(--primary))] text-white shadow-lg shadow-blue-500/20"
                                : "bg-[hsl(var(--surface-1))] dark:bg-white/5 text-[hsl(var(--text-secondary))] border border-[hsl(var(--border))] dark:border-white/10"
                        )}
                    >
                        <Filter size={14} /> Filtros
                    </button>
                    <button
                        onClick={handleExport}
                        disabled={exporting}
                        className="flex items-center gap-2 px-3 py-2 bg-emerald-600 text-white rounded-md text-[11px] font-bold uppercase tracking-wide shadow-lg shadow-emerald-500/20 hover:bg-emerald-700 active:scale-95 transition-all disabled:opacity-50"
                    >
                        {exporting ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />}
                        Exportar CSV
                    </button>
                </div>
            }
        >
            <div className="flex flex-col h-full overflow-hidden">
                {/* Summary cards */}
                {summary && (
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 px-4 pt-4 pb-2">
                        {[
                            { label: 'Total leads', value: summary.total, icon: Users, color: 'text-[hsl(var(--primary))]', bg: 'bg-blue-50 dark:bg-blue-500/10' },
                            { label: 'Con email', value: summary.withEmail, icon: Mail, color: 'text-emerald-600', bg: 'bg-emerald-50 dark:bg-emerald-500/10' },
                            { label: 'Nuevos', value: summary.newCount, icon: Tag, color: 'text-amber-600', bg: 'bg-amber-50 dark:bg-amber-500/10' },
                            { label: 'Landings', value: summary.landingPages, icon: Globe, color: 'text-[hsl(var(--primary))]', bg: 'bg-blue-50 dark:bg-blue-500/10' },
                        ].map((stat, i) => (
                            <div key={i} className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/5 p-3">
                                <div className="flex items-center gap-2 mb-1">
                                    <div className={`size-6 rounded-md ${stat.bg} flex items-center justify-center ${stat.color}`}>
                                        <stat.icon size={14} />
                                    </div>
                                    <span className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{stat.label}</span>
                                </div>
                                <p className="text-xl font-bold text-[hsl(var(--text-primary))] dark:text-white">{stat.value}</p>
                            </div>
                        ))}
                    </div>
                )}

                {/* Filters */}
                {showFilters && (
                    <div className="px-4 py-2 border-b border-[hsl(var(--border))] dark:border-white/5 bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02]">
                        <div className="flex gap-3 items-end">
                            <div className="space-y-1">
                                <label className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Desde</label>
                                <input
                                    type="date"
                                    value={dateFrom}
                                    onChange={e => { setPage(1); setDateFrom(e.target.value); }}
                                    className="px-3 py-1.5 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-black/20 text-sm outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.2] dark:text-white"
                                />
                            </div>
                        </div>
                    </div>
                )}

                {/* Search */}
                <div className="px-4 py-2 border-b border-[hsl(var(--border))] dark:border-white/5">
                    <div className="relative">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]" size={15} />
                        <input
                            type="text"
                            placeholder="Buscar por nombre, email o notas..."
                            className="w-full bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg py-1.5 pl-9 pr-4 text-sm outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.2] dark:text-white transition-all"
                            value={searchQuery}
                            onChange={e => setSearchQuery(e.target.value)}
                        />
                    </div>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-4 space-y-3">
                    {loading ? (
                        [...Array(5)].map((_, i) => <Skeleton key={i} className="h-20 w-full rounded-md" />)
                    ) : filteredLeads.length === 0 ? (
                        <div className="flex flex-col items-center justify-center py-16 text-center space-y-4">
                            <div className="size-12 rounded-full bg-[hsl(var(--surface-2))] dark:bg-white/5 flex items-center justify-center text-[hsl(var(--text-secondary))]">
                                <Mail size={40} />
                            </div>
                            <h4 className="text-[hsl(var(--text-primary))] dark:text-white font-bold text-sm">No hay leads de newsletter</h4>
                            <p className="text-[hsl(var(--text-secondary))] text-sm max-w-[250px]">Los suscriptores del newsletter aparecerán aquí cuando se registren desde el sitio web.</p>
                        </div>
                    ) : viewType === 'list' ? (
                        filteredLeads.map(lead => {
                            const stageValue = lead.stage ?? 'new';
                            return (
                            <div
                                key={lead.case_id}
                                onClick={() => router.push(`/plataforma/crm/contacts/${lead.case_id}`)}
                                className="bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-md p-4 hover:border-blue-300 dark:hover:border-blue-700 transition-all group cursor-pointer shadow-sm hover:shadow-md"
                            >
                                <div className="flex items-start justify-between mb-2">
                                    <div className="flex items-center gap-3">
                                        <div className="size-9 rounded-lg bg-blue-50 dark:bg-[hsl(var(--primary))]/10 border border-blue-200 dark:border-[hsl(var(--primary))]/20 flex items-center justify-center text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))] font-bold text-sm">
                                            {lead.nombre_completo?.charAt(0) || (lead.first_name?.charAt(0) ?? '?')}{(lead.nombre_completo?.split(/\s+/).filter(Boolean).slice(-1)[0]?.[0]) || (lead.last_name?.charAt(0) ?? '')}
                                        </div>
                                        <div>
                                            <h3 className="font-bold text-[hsl(var(--text-primary))] dark:text-white group-hover:text-[hsl(var(--primary))] transition-colors">
                                                {lead.nombre_completo || `${lead.first_name ?? ''} ${lead.last_name ?? ''}`.trim()}
                                            </h3>
                                            <p className="text-xs text-[hsl(var(--text-secondary))] flex items-center gap-1.5 mt-0.5">
                                                <Mail size={11} /> {lead.email || 'Sin email'}
                                                {lead.phone && <><span className="text-[hsl(var(--text-secondary))]">·</span> {lead.phone}</>}
                                            </p>
                                        </div>
                                    </div>
                                    <span className={`px-2.5 py-1 rounded-md text-[10px] font-bold uppercase tracking-wide border ${STAGE_COLORS[stageValue] || 'bg-[hsl(var(--surface-2))]/10 text-[hsl(var(--text-secondary))]'}`}>
                                        {STAGE_LABELS[stageValue] || stageValue}
                                    </span>
                                </div>
                                {lead.notes && (
                                    <p className="text-xs text-[hsl(var(--text-secondary))] mt-2 pl-12 line-clamp-2">{lead.notes.replace(/\n/g, ' · ')}</p>
                                )}
                                <div className="flex items-center gap-3 mt-2 pl-12">
                                    <span className="text-[10px] text-[hsl(var(--text-secondary))] flex items-center gap-1">
                                        <Calendar size={10} />
                                        {lead.created_at ? new Date(lead.created_at).toLocaleDateString('es-CO') : '—'}
                                    </span>
                                    <span className="text-[10px] text-[hsl(var(--text-secondary))] flex items-center gap-1">
                                        <Globe size={10} />
                                        {lead.source || '—'}
                                    </span>
                                </div>
                            </div>
                            );
                        })
                    ) : viewType === 'table' ? (
                        <div className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 overflow-hidden">
                            <table className="w-full text-left">
                                <thead className="bg-[hsl(var(--surface-1))] dark:bg-white/5">
                                    <tr>
                                        <th className="px-4 py-2 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Nombre</th>
                                        <th className="px-4 py-2 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Email</th>
                                        <th className="px-4 py-2 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Teléfono</th>
                                        <th className="px-4 py-2 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Fuente</th>
                                        <th className="px-4 py-2 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Etapa</th>
                                        <th className="px-4 py-2 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Notas</th>
                                        <th className="px-4 py-2 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Fecha</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {filteredLeads.map(lead => {
                                        const stageValue = lead.stage ?? 'new';
                                        return (
                                        <tr
                                            key={lead.case_id}
                                            onClick={() => router.push(`/plataforma/crm/contacts/${lead.case_id}`)}
                                            className="cursor-pointer border-t border-[hsl(var(--border))] dark:border-white/5 hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/[0.02]"
                                        >
                                            <td className="px-4 py-2 text-sm font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">
                                                {lead.nombre_completo || `${lead.first_name ?? ''} ${lead.last_name ?? ''}`.trim()}
                                            </td>
                                            <td className="px-4 py-2 text-xs text-[hsl(var(--text-secondary))]">{lead.email || '—'}</td>
                                            <td className="px-4 py-2 text-xs text-[hsl(var(--text-secondary))]">{lead.phone || '—'}</td>
                                            <td className="px-4 py-2 text-xs">
                                                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-[hsl(var(--surface-2))] dark:bg-white/5 text-[hsl(var(--text-secondary))] uppercase tracking-wide">
                                                    {lead.source?.replace('newsletter-', '') || '—'}
                                                </span>
                                            </td>
                                            <td className="px-4 py-2">
                                                <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide border ${STAGE_COLORS[stageValue] || ''}`}>
                                                    {STAGE_LABELS[stageValue] || stageValue}
                                                </span>
                                            </td>
                                            <td className="px-4 py-2 text-xs text-[hsl(var(--text-secondary))] max-w-[200px] truncate">
                                                {lead.notes?.replace(/\n/g, ' · ') || '—'}
                                            </td>
                                            <td className="px-4 py-2 text-xs text-[hsl(var(--text-secondary))]">
                                                {lead.created_at ? new Date(lead.created_at).toLocaleDateString('es-CO') : '—'}
                                            </td>
                                        </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                        </div>
                    ) : viewType === 'calendar' ? (
                        <div className="space-y-4">
                            {(() => {
                                const grouped: Record<string, NewsletterLead[]> = {};
                                for (const lead of filteredLeads) {
                                    const date = lead.created_at ? new Date(lead.created_at).toISOString().slice(0, 10) : 'unknown';
                                    if (!grouped[date]) grouped[date] = [];
                                    grouped[date].push(lead);
                                }
                                return Object.entries(grouped).sort((a, b) => b[0].localeCompare(a[0])).map(([dateKey, items]) => (
                                    <div key={dateKey} className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/5 p-4">
                                        <p className="mb-3 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                                            {dateKey === 'unknown' ? 'Sin fecha' : new Date(dateKey + 'T00:00:00').toLocaleDateString('es-CO', { day: '2-digit', month: 'long', year: 'numeric' })}
                                            <span className="ml-2 text-[hsl(var(--text-secondary))]">({items.length})</span>
                                        </p>
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                                            {items.map(lead => (
                                                <button
                                                    key={lead.case_id}
                                                    onClick={() => router.push(`/plataforma/crm/contacts/${lead.case_id}`)}
                                                    className="rounded-md border border-[hsl(var(--border))] dark:border-white/10 px-3 py-2 text-left hover:border-blue-300 dark:hover:border-blue-700 transition-all"
                                                >
                                                    <p className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">
                                                        {lead.nombre_completo || `${lead.first_name ?? ''} ${lead.last_name ?? ''}`.trim()}
                                                    </p>
                                                    <p className="text-[10px] text-[hsl(var(--text-secondary))]">{lead.email || 'Sin email'}</p>
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                ));
                            })()}
                        </div>
                    ) : viewType === 'wiki' ? (
                        <div className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/5 p-4 space-y-3">
                            <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                                <BookOpen size={12} /> Wiki de leads de newsletter
                            </div>
                            <textarea
                                value={wikiNotes}
                                onChange={e => setWikiNotes(e.target.value)}
                                placeholder="Documenta el proceso de seguimiento de leads del newsletter, criterios de clasificación, etc..."
                                className="w-full min-h-[360px] rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-black/20 p-4 text-sm font-medium text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.2]"
                            />
                        </div>
                    ) : (
                        <CrmViewPlaceholder moduleName="Newsletter Leads" viewType={viewType} />
                    )}
                </div>

                {/* Pagination */}
                {data && data.total_pages > 1 && (
                    <div className="px-4 py-3 border-t border-[hsl(var(--border))] dark:border-white/5 flex items-center justify-between">
                        <span className="text-[11px] text-[hsl(var(--text-secondary))] font-medium">
                            {data.total} registros · Página {data.page} de {data.total_pages}
                        </span>
                        <div className="flex gap-1">
                            <button
                                onClick={() => setPage(p => Math.max(1, p - 1))}
                                disabled={page <= 1}
                                className="size-8 rounded-md border border-[hsl(var(--border))] dark:border-white/10 flex items-center justify-center text-[hsl(var(--text-secondary))] disabled:opacity-30 hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 transition-all"
                                aria-label="Página anterior"
                            >
                                <ChevronLeft size={14} />
                            </button>
                            <button
                                onClick={() => setPage(p => Math.min(data.total_pages, p + 1))}
                                disabled={page >= data.total_pages}
                                className="size-8 rounded-md border border-[hsl(var(--border))] dark:border-white/10 flex items-center justify-center text-[hsl(var(--text-secondary))] disabled:opacity-30 hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 transition-all"
                                aria-label="Página siguiente"
                            >
                                <ChevronRight size={14} />
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </CrmShell>
    );
}
