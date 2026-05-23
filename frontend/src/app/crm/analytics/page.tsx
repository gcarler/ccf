"use client";

import React, { useEffect, useMemo, useState } from 'react';
import {
    Activity,
    BarChart3,
    CalendarDays,
    Download,
    HeartHandshake,
    Share2,
    Target,
    Users,
    UsersRound,
} from 'lucide-react';
import { motion } from 'framer-motion';
import clsx from 'clsx';
import CrmShell from '@/components/crm/CrmShell';
import CrmViewPlaceholder from '@/components/crm/CrmViewPlaceholder';
import { ViewType, getStoredView } from '@/components/ViewSwitcher';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import { useWikiDocument } from '@/hooks/useWikiDocument';
import { STAGE_LABEL } from '@/app/crm/pipeline/constants';
import type { CrmAnalyticsSummary } from '@/app/crm/types';

const ALL_VIEWS: ViewType[] = ['table', 'list', 'grid', 'board', 'kanban', 'gantt', 'calendar', 'wiki'];
const NUMBER_FORMATTER = new Intl.NumberFormat('es-CO');

type KpiTone = 'neutral' | 'positive' | 'warning';

interface KpiRow {
    label: string;
    value: string;
    context: string;
    tone: KpiTone;
}

interface FunnelRow {
    stage: string;
    label: string;
    value: number;
    percent: number;
}

export default function CrmAnalyticsPage() {
    const { token } = useAuth();
    const [viewType, setViewType] = useState<ViewType>(() => getStoredView('crm_analytics_view', 'grid'));
    const { content: wikiNotes, setContent: setWikiNotes } = useWikiDocument('crm_analytics_wiki_notes', {
        title: 'Wiki analitica CRM',
    });
    const [analytics, setAnalytics] = useState<CrmAnalyticsSummary | null>(null);
    const [loadingAnalytics, setLoadingAnalytics] = useState(true);
    const [analyticsError, setAnalyticsError] = useState<string | null>(null);


    useEffect(() => {
        if (!token) return;

        let alive = true;
        const loadAnalytics = async () => {
            setLoadingAnalytics(true);
            setAnalyticsError(null);
            try {
                const data = await apiFetch<CrmAnalyticsSummary>('/crm/analytics', {
                    token,
                    cache: 'no-store',
                });
                if (alive) setAnalytics(data);
            } catch {
                if (alive) setAnalyticsError('No fue posible cargar la analitica operativa.');
            } finally {
                if (alive) setLoadingAnalytics(false);
            }
        };

        loadAnalytics();
        return () => {
            alive = false;
        };
    }, [token]);

    const activeRate = analytics?.total_members
        ? Math.round((analytics.active_members / analytics.total_members) * 100)
        : 0;

    const kpiRows = useMemo<KpiRow[]>(() => {
        if (!analytics) return [];

        return [
            {
                label: 'Miembros Totales',
                value: formatCount(analytics.total_members),
                context: `${formatCount(analytics.total_families)} familias registradas`,
                tone: 'neutral',
            },
            {
                label: 'Miembros Activos',
                value: formatCount(analytics.active_members),
                context: `${activeRate}% de la membresia`,
                tone: activeRate >= 70 ? 'positive' : 'warning',
            },
            {
                label: 'Leads en Pipeline',
                value: formatCount(analytics.total_leads),
                context: `${Object.keys(analytics.pipeline_by_stage).length} etapas activas`,
                tone: 'neutral',
            },
            {
                label: 'Eventos Este Mes',
                value: formatCount(analytics.events_this_month),
                context: `${formatCount(analytics.total_groups)} grupos operativos`,
                tone: 'positive',
            },
        ];
    }, [activeRate, analytics]);

    const funnelRows = useMemo<FunnelRow[]>(() => {
        if (!analytics) return [];
        const total = Math.max(analytics.total_leads, 1);

        return Object.entries(analytics.pipeline_by_stage)
            .map(([stage, value]) => ({
                stage,
                label: STAGE_LABEL[stage] ?? titleCase(stage),
                value,
                percent: Math.round((value / total) * 100),
            }))
            .sort((a, b) => b.value - a.value);
    }, [analytics]);

    const containerVariants = {
        hidden: { opacity: 0 },
        show: { opacity: 1, transition: { staggerChildren: 0.08 } },
    };

    const itemVariants = {
        hidden: { opacity: 0, y: 12 },
        show: { opacity: 1, y: 0, transition: { type: 'spring', stiffness: 320, damping: 28 } },
    };

    return (
        <CrmShell
            breadcrumbs={[
                { label: 'Consolidacion', icon: Users },
                { label: 'Analitica Avanzada', icon: BarChart3 },
            ]}
            viewOptions={ALL_VIEWS}
            viewType={viewType}
            onViewChange={setViewType}
            rightActions={
                <div className="flex items-center gap-2">
                    <button className="flex items-center gap-2 px-3 py-2 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-md text-[10px] font-bold uppercase tracking-wide text-slate-600 dark:text-slate-300 hover:bg-slate-50 transition-all">
                        <Download size={13} /> Exportar PDF
                    </button>
                    <button className="flex items-center gap-2 px-3 py-2 bg-blue-600 text-white rounded-md text-[10px] font-bold uppercase tracking-wide shadow-xl shadow-blue-500/20 active:scale-95 transition-all">
                        <Share2 size={13} /> Compartir
                    </button>
                </div>
            }
        >
            <div className="space-y-4 pb-6">
                {loadingAnalytics && (
                    <StatusBanner tone="neutral">
                        Cargando analitica operativa desde CRM...
                    </StatusBanner>
                )}
                {analyticsError && (
                    <StatusBanner tone="warning">
                        {analyticsError}
                    </StatusBanner>
                )}

                {viewType === 'list' && <ListView rows={kpiRows} />}
                {viewType === 'table' && <TableView rows={kpiRows} />}
                {(viewType === 'board' || viewType === 'kanban') && <BoardView rows={kpiRows} />}
                {viewType === 'calendar' && <CalendarView analytics={analytics} />}
                {viewType === 'gantt' && <GanttView rows={funnelRows} />}
                {viewType === 'wiki' && <WikiView wikiNotes={wikiNotes} onChange={setWikiNotes} />}

                {!['table', 'list', 'grid', 'board', 'kanban', 'gantt', 'calendar', 'wiki'].includes(viewType) && (
                    <CrmViewPlaceholder moduleName="Analitica CRM" viewType={viewType} />
                )}

                {viewType === 'grid' && (
                    <motion.div
                        variants={containerVariants}
                        initial="hidden"
                        animate="show"
                        className="space-y-4"
                    >
                        <motion.section variants={itemVariants} className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
                            {kpiRows.map((row) => (
                                <AnalyticsKpi key={row.label} row={row} />
                            ))}
                        </motion.section>

                        <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.45fr)_minmax(320px,0.75fr)]">
                            <motion.section variants={itemVariants} className="rounded-lg border border-slate-200 dark:border-white/10 bg-white dark:bg-[#15171c] p-3 shadow-sm">
                                <div className="mb-4 flex items-center justify-between gap-4">
                                    <div>
                                        <h1 className="text-sm font-bold tracking-tight text-slate-900 dark:text-white">
                                            Resumen operativo
                                        </h1>
                                        <p className="text-[11px] font-medium text-slate-500 dark:text-slate-400">
                                            Datos agregados reales del modulo de consolidacion.
                                        </p>
                                    </div>
                                    <span className="rounded-full bg-slate-100 px-3 py-1 text-[10px] font-bold uppercase tracking-wide text-slate-500 dark:bg-white/5 dark:text-slate-300">
                                        Actual
                                    </span>
                                </div>

                                <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
                                    <SummaryTile
                                        icon={HeartHandshake}
                                        label="Consejeria abierta"
                                        value={formatCount(analytics?.open_counseling ?? 0)}
                                    />
                                    <SummaryTile
                                        icon={UsersRound}
                                        label="Familias"
                                        value={formatCount(analytics?.total_families ?? 0)}
                                    />
                                    <SummaryTile
                                        icon={Target}
                                        label="Grupos"
                                        value={formatCount(analytics?.total_groups ?? 0)}
                                    />
                                </div>

                                <div className="mt-4 rounded-lg bg-slate-50 p-4 dark:bg-white/[0.03]">
                                    <div className="mb-2 flex items-center justify-between text-[10px] font-bold uppercase tracking-wide text-slate-400">
                                        <span>Activacion de miembros</span>
                                        <span>{activeRate}%</span>
                                    </div>
                                    <div className="h-2 overflow-hidden rounded-full bg-slate-200/70 dark:bg-white/10">
                                        <div
                                            className="h-full rounded-full bg-blue-600 transition-all"
                                            style={{ width: `${Math.min(activeRate, 100)}%` }}
                                        />
                                    </div>
                                </div>
                            </motion.section>

                            <motion.aside variants={itemVariants} className="rounded-lg border border-slate-200 dark:border-white/10 bg-white dark:bg-[#15171c] p-3 shadow-sm">
                                <div className="mb-4 flex items-center gap-2">
                                    <Activity size={15} className="text-blue-600" />
                                    <h2 className="text-[11px] font-bold uppercase tracking-wide text-slate-500">
                                        Pipeline
                                    </h2>
                                </div>

                                {funnelRows.length === 0 ? (
                                    <p className="rounded-md bg-slate-50 px-3 py-2 text-sm font-medium text-slate-400 dark:bg-white/[0.03]">
                                        No hay leads registrados.
                                    </p>
                                ) : (
                                    <div className="space-y-3">
                                        {funnelRows.map((row) => (
                                            <FunnelStep key={row.stage} row={row} />
                                        ))}
                                    </div>
                                )}
                            </motion.aside>
                        </div>
                    </motion.div>
                )}
            </div>
        </CrmShell>
    );
}

function ListView({ rows }: { rows: KpiRow[] }) {
    return (
        <div className="space-y-2">
            {rows.map((row) => (
                <div key={row.label} className="flex items-center justify-between rounded-lg border border-slate-200 bg-white p-4 dark:border-white/10 dark:bg-white/5">
                    <div>
                        <p className="text-[10px] font-bold uppercase tracking-wide text-slate-400">{row.label}</p>
                        <p className="text-base font-bold text-slate-800 dark:text-slate-100">{row.value}</p>
                    </div>
                    <Badge tone={row.tone}>{row.context}</Badge>
                </div>
            ))}
        </div>
    );
}

function TableView({ rows }: { rows: KpiRow[] }) {
    return (
        <div className="overflow-hidden rounded-lg border border-slate-200 bg-white dark:border-white/10 dark:bg-white/5">
            <table className="w-full text-left">
                <thead className="bg-slate-50 dark:bg-white/5">
                    <tr>
                        <th className="px-4 py-1.5 text-[10px] font-bold uppercase tracking-wide text-slate-400">Metrica</th>
                        <th className="px-4 py-1.5 text-[10px] font-bold uppercase tracking-wide text-slate-400">Valor</th>
                        <th className="px-4 py-1.5 text-[10px] font-bold uppercase tracking-wide text-slate-400">Contexto</th>
                    </tr>
                </thead>
                <tbody>
                    {rows.map((row) => (
                        <tr key={row.label} className="border-t border-slate-100 dark:border-white/5">
                            <td className="px-4 py-1.5 text-sm font-bold text-slate-800 dark:text-slate-100">{row.label}</td>
                            <td className="px-4 py-1.5 text-xs text-slate-500">{row.value}</td>
                            <td className="px-4 py-1.5"><Badge tone={row.tone}>{row.context}</Badge></td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}

function BoardView({ rows }: { rows: KpiRow[] }) {
    const columns = [
        { title: 'Base', items: rows.slice(0, 1) },
        { title: 'Salud', items: rows.slice(1, 2) },
        { title: 'Operacion', items: rows.slice(2) },
    ];

    return (
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
            {columns.map((column) => (
                <div key={column.title} className="rounded-lg border border-slate-200 bg-slate-50 p-3 dark:border-white/10 dark:bg-white/[0.03]">
                    <p className="mb-3 text-[10px] font-bold uppercase tracking-wide text-slate-500">{column.title}</p>
                    <div className="space-y-2">
                        {column.items.map((item) => (
                            <div key={item.label} className="rounded-md border border-slate-200 bg-white p-3 dark:border-white/10 dark:bg-white/5">
                                <p className="text-xs font-bold text-slate-800 dark:text-slate-100">{item.label}</p>
                                <p className="mt-1 text-[10px] text-slate-400">{item.value}</p>
                                <div className="mt-2"><Badge tone={item.tone}>{item.context}</Badge></div>
                            </div>
                        ))}
                    </div>
                </div>
            ))}
        </div>
    );
}

function CalendarView({ analytics }: { analytics: CrmAnalyticsSummary | null }) {
    const cells = [
        { label: 'Eventos este mes', value: analytics?.events_this_month ?? 0, icon: CalendarDays },
        { label: 'Consejeria abierta', value: analytics?.open_counseling ?? 0, icon: HeartHandshake },
        { label: 'Grupos', value: analytics?.total_groups ?? 0, icon: Target },
        { label: 'Familias', value: analytics?.total_families ?? 0, icon: UsersRound },
    ];

    return (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            {cells.map((cell) => (
                <SummaryTile key={cell.label} icon={cell.icon} label={cell.label} value={formatCount(cell.value)} />
            ))}
        </div>
    );
}

function GanttView({ rows }: { rows: FunnelRow[] }) {
    return (
        <div className="space-y-3 rounded-lg border border-slate-200 bg-white p-4 dark:border-white/10 dark:bg-white/5">
            <p className="text-[10px] font-bold uppercase tracking-wide text-slate-500">Distribucion del pipeline</p>
            {rows.length === 0 ? (
                <p className="text-sm font-medium text-slate-400">No hay datos disponibles.</p>
            ) : rows.map((row) => (
                <div key={row.stage} className="space-y-1">
                    <div className="flex items-center justify-between text-[11px]">
                        <span className="font-bold text-slate-700 dark:text-slate-300">{row.label}</span>
                        <span className="font-bold text-slate-400">{row.value}</span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full bg-slate-100 dark:bg-white/10">
                        <div className="h-full rounded-full bg-blue-600" style={{ width: `${row.percent}%` }} />
                    </div>
                </div>
            ))}
        </div>
    );
}

function WikiView({
    wikiNotes,
    onChange,
}: {
    wikiNotes: string;
    onChange: (value: string) => void;
}) {
    return (
        <div className="space-y-3 rounded-lg border border-slate-200 bg-white p-4 dark:border-white/10 dark:bg-white/5">
            <p className="text-[10px] font-bold uppercase tracking-wide text-slate-500">Wiki analitica CRM</p>
            <textarea
                value={wikiNotes}
                onChange={(event) => onChange(event.target.value)}
                placeholder="Documenta definiciones de metricas, fuentes de datos, supuestos y acuerdos de interpretacion para liderazgo pastoral..."
                className="min-h-[320px] w-full rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm font-medium text-slate-700 outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-white/10 dark:bg-black/20 dark:text-slate-200"
            />
        </div>
    );
}

function AnalyticsKpi({ row }: { row: KpiRow }) {
    return (
        <motion.div
            variants={{ hidden: { opacity: 0, scale: 0.98 }, show: { opacity: 1, scale: 1 } }}
            className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm dark:border-white/10 dark:bg-[#15171c]"
        >
            <div className="mb-3 flex items-center justify-between gap-3">
                <p className="text-[10px] font-bold uppercase tracking-wide text-slate-400">{row.label}</p>
                <Badge tone={row.tone}>{row.context}</Badge>
            </div>
            <p className="text-xl font-bold tracking-tight text-slate-900 dark:text-white">{row.value}</p>
        </motion.div>
    );
}

function SummaryTile({
    icon: Icon,
    label,
    value,
}: {
    icon: React.ElementType;
    label: string;
    value: string;
}) {
    return (
        <div className="rounded-lg border border-slate-200 bg-white p-4 dark:border-white/10 dark:bg-white/5">
            <div className="mb-3 flex size-9 items-center justify-center rounded-md bg-blue-50 text-blue-600 dark:bg-blue-500/10">
                <Icon size={16} />
            </div>
            <p className="text-[10px] font-bold uppercase tracking-wide text-slate-400">{label}</p>
            <p className="text-lg font-bold text-slate-900 dark:text-white">{value}</p>
        </div>
    );
}

function FunnelStep({ row }: { row: FunnelRow }) {
    return (
        <div className="space-y-1.5">
            <div className="flex items-center justify-between text-[10px] font-bold uppercase tracking-wide text-slate-500">
                <span>{row.label}</span>
                <span>{row.value}</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-slate-100 dark:bg-white/10">
                <div className="h-full rounded-full bg-blue-600" style={{ width: `${row.percent}%` }} />
            </div>
        </div>
    );
}

function Badge({
    tone,
    children,
}: {
    tone: KpiTone;
    children: React.ReactNode;
}) {
    return (
        <span
            className={clsx(
                'inline-flex rounded-full px-2.5 py-1 text-[9px] font-bold uppercase tracking-wide',
                tone === 'positive' && 'bg-emerald-50 text-emerald-600 dark:bg-emerald-500/10 dark:text-emerald-300',
                tone === 'warning' && 'bg-amber-50 text-amber-700 dark:bg-amber-500/10 dark:text-amber-300',
                tone === 'neutral' && 'bg-slate-100 text-slate-500 dark:bg-white/5 dark:text-slate-300',
            )}
        >
            {children}
        </span>
    );
}

function StatusBanner({
    tone,
    children,
}: {
    tone: 'neutral' | 'warning';
    children: React.ReactNode;
}) {
    return (
        <div
            className={clsx(
                'rounded-lg border px-4 py-1.5 text-sm font-medium',
                tone === 'neutral' && 'border-slate-200 bg-slate-50 text-slate-500 dark:border-white/10 dark:bg-white/5 dark:text-slate-300',
                tone === 'warning' && 'border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-500/20 dark:bg-amber-500/10 dark:text-amber-200',
            )}
        >
            {children}
        </div>
    );
}

function formatCount(value: number) {
    return NUMBER_FORMATTER.format(value);
}

function titleCase(value: string) {
    return value
        .replace(/_/g, ' ')
        .replace(/\b\w/g, (char) => char.toUpperCase());
}
