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
import { STAGE_LABEL } from '@/app/plataforma/crm/pipeline/constants';
import type { CrmAnalyticsSummary, KpiTone, KpiRow, FunnelRow } from '@/types/crm';

const ALL_VIEWS: ViewType[] = ['table', 'list', 'grid', 'board', 'kanban', 'gantt', 'calendar', 'wiki'];
const NUMBER_FORMATTER = new Intl.NumberFormat('es-CO');

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

    const activeRate = analytics?.total_personas
        ? Math.round((analytics.active_personas / analytics.total_personas) * 100)
        : 0;

    const kpiRows = useMemo<KpiRow[]>(() => {
        if (!analytics) return [];
        const casesByStage = analytics.cases_by_stage ?? {};

        return [
            {
                label: 'Personas Totales',
                value: formatCount(analytics.total_personas),
                context: `${formatCount(analytics.total_families)} familias registradas`,
                tone: 'neutral',
            },
            {
                label: 'Personas Activos',
                value: formatCount(analytics.active_personas),
                context: `${activeRate}% de la membresia`,
                tone: activeRate >= 70 ? 'positive' : 'warning',
            },
            {
                label: 'Casos en Pipeline',
                value: formatCount(analytics.total_cases),
                context: `${Object.keys(casesByStage).length} etapas activas`,
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
        const casesByStage = analytics.cases_by_stage ?? {};
        const total = Math.max(analytics.total_cases, 1);

        return Object.entries(casesByStage)
            .map(([stage, value]) => ({
                stage,
                label: STAGE_LABEL[stage] ?? titleCase(stage),
                value: Number(value),
                percent: Math.round((Number(value) / total) * 100),
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
                    <button className="flex items-center gap-2 px-3 py-2 bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-md text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-1))] transition-all">
                        <Download size={13} /> Exportar PDF
                    </button>
                    <button className="flex items-center gap-2 px-3 py-2 bg-[hsl(var(--primary))] text-white rounded-md text-[10px] font-bold uppercase tracking-wide shadow-xl shadow-blue-500/20 active:scale-95 transition-all">
                        <Share2 size={13} /> Compartir
                    </button>
                </div>
            }
        >
            <div className="space-y-4 pb-6">
                {loadingAnalytics && (
                    <div className="space-y-4">
                        <StatusBanner tone="neutral">
                            Cargando analitica operativa desde CRM...
                        </StatusBanner>
                        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
                            {[...Array(4)].map((_, i) => (
                                <div key={i} className="h-24 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] dark:border-white/10 dark:bg-white/5 animate-pulse p-4 space-y-2">
                                    <div className="h-3 w-1/2 rounded bg-[hsl(var(--surface-2))] dark:bg-white/10" />
                                    <div className="h-6 w-1/3 rounded bg-[hsl(var(--surface-2))] dark:bg-white/10" />
                                    <div className="h-2 w-2/3 rounded bg-[hsl(var(--surface-2))] dark:bg-white/10" />
                                </div>
                            ))}
                        </div>
                    </div>
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
                            <motion.section variants={itemVariants} className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-[#15171c] p-3 shadow-sm">
                                <div className="mb-4 flex items-center justify-between gap-4">
                                    <div>
                                        <h1 className="text-sm font-bold tracking-tight text-[hsl(var(--text-primary))] dark:text-white">
                                            Resumen operativo
                                        </h1>
                                        <p className="text-[11px] font-medium text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]">
                                            Datos agregados reales del modulo de consolidacion.
                                        </p>
                                    </div>
                                    <span className="rounded-full bg-[hsl(var(--surface-2))] px-3 py-1 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] dark:bg-white/5 dark:text-[hsl(var(--text-secondary))]">
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

                                <div className="mt-4 rounded-lg bg-[hsl(var(--surface-1))] p-4 dark:bg-white/[0.03]">
                                    <div className="mb-2 flex items-center justify-between text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                                        <span>Activacion de personas</span>
                                        <span>{activeRate}%</span>
                                    </div>
                                    <div className="h-2 overflow-hidden rounded-full bg-[hsl(var(--surface-3))]/70 dark:bg-white/10">
                                        <div
                                            className="h-full rounded-full bg-[hsl(var(--primary))] transition-all"
                                            style={{ width: `${Math.min(activeRate, 100)}%` }}
                                        />
                                    </div>
                                </div>
                            </motion.section>

                            <motion.aside variants={itemVariants} className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-[#15171c] p-3 shadow-sm">
                                <div className="mb-4 flex items-center gap-2">
                                    <Activity size={15} className="text-[hsl(var(--primary))]" />
                                    <h2 className="text-[11px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                                        Pipeline
                                    </h2>
                                </div>

                                {funnelRows.length === 0 ? (
                                    <p className="rounded-md bg-[hsl(var(--surface-1))] px-3 py-2 text-sm font-medium text-[hsl(var(--text-secondary))] dark:bg-white/[0.03]">
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
                <div key={row.label} className="flex items-center justify-between rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-4 dark:border-white/10 dark:bg-white/5">
                    <div>
                        <p className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{row.label}</p>
                        <p className="text-base font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">{row.value}</p>
                    </div>
                    <Badge tone={row.tone}>{row.context}</Badge>
                </div>
            ))}
        </div>
    );
}

function TableView({ rows }: { rows: KpiRow[] }) {
    return (
        <div className="overflow-x-auto rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] dark:border-white/10 dark:bg-white/5">
            <table className="w-full min-w-[480px] text-left">
                <thead className="bg-[hsl(var(--surface-1))] dark:bg-white/5">
                    <tr>
                        <th className="px-4 py-1.5 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Metrica</th>
                        <th className="px-4 py-1.5 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Valor</th>
                        <th className="px-4 py-1.5 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Contexto</th>
                    </tr>
                </thead>
                <tbody>
                    {rows.map((row) => (
                        <tr key={row.label} className="border-t border-[hsl(var(--border))] dark:border-white/5">
                            <td className="px-4 py-1.5 text-sm font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">{row.label}</td>
                            <td className="px-4 py-1.5 text-xs text-[hsl(var(--text-secondary))]">{row.value}</td>
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
                <div key={column.title} className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-3 dark:border-white/10 dark:bg-white/[0.03]">
                    <p className="mb-3 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{column.title}</p>
                    <div className="space-y-2">
                        {column.items.map((item) => (
                            <div key={item.label} className="rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-3 dark:border-white/10 dark:bg-white/5">
                                <p className="text-xs font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">{item.label}</p>
                                <p className="mt-1 text-[10px] text-[hsl(var(--text-secondary))]">{item.value}</p>
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
        <div className="space-y-3 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-4 dark:border-white/10 dark:bg-white/5">
            <p className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Distribucion del pipeline</p>
            {rows.length === 0 ? (
                <p className="text-sm font-medium text-[hsl(var(--text-secondary))]">No hay datos disponibles.</p>
            ) : rows.map((row) => (
                <div key={row.stage} className="space-y-1">
                    <div className="flex items-center justify-between text-[11px]">
                        <span className="font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">{row.label}</span>
                        <span className="font-bold text-[hsl(var(--text-secondary))]">{row.value}</span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full bg-[hsl(var(--surface-2))] dark:bg-white/10">
                        <div className="h-full rounded-full bg-[hsl(var(--primary))]" style={{ width: `${row.percent}%` }} />
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
        <div className="space-y-3 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-4 dark:border-white/10 dark:bg-white/5">
            <p className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Wiki analitica CRM</p>
            <textarea
                value={wikiNotes}
                onChange={(event) => onChange(event.target.value)}
                placeholder="Documenta definiciones de metricas, fuentes de datos, supuestos y acuerdos de interpretacion para liderazgo pastoral..."
                className="min-h-[320px] w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-4 text-sm font-medium text-[hsl(var(--text-primary))] outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-white/10 dark:bg-black/20 dark:text-[hsl(var(--text-secondary))]"
            />
        </div>
    );
}

function AnalyticsKpi({ row }: { row: KpiRow }) {
    return (
        <motion.div
            variants={{ hidden: { opacity: 0, scale: 0.98 }, show: { opacity: 1, scale: 1 } }}
            className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-4 shadow-sm dark:border-white/10 dark:bg-[#15171c]"
        >
            <div className="mb-3 flex items-center justify-between gap-3">
                <p className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{row.label}</p>
                <Badge tone={row.tone}>{row.context}</Badge>
            </div>
            <p className="text-xl font-bold tracking-tight text-[hsl(var(--text-primary))] dark:text-white">{row.value}</p>
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
        <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-4 dark:border-white/10 dark:bg-white/5">
            <div className="mb-3 flex size-9 items-center justify-center rounded-md bg-blue-50 text-[hsl(var(--primary))] dark:bg-blue-500/10">
                <Icon size={16} />
            </div>
            <p className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{label}</p>
            <p className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white">{value}</p>
        </div>
    );
}

function FunnelStep({ row }: { row: FunnelRow }) {
    return (
        <div className="space-y-1.5">
            <div className="flex items-center justify-between text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                <span>{row.label}</span>
                <span>{row.value}</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-[hsl(var(--surface-2))] dark:bg-white/10">
                <div className="h-full rounded-full bg-[hsl(var(--primary))]" style={{ width: `${row.percent}%` }} />
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
                tone === 'neutral' && 'bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))] dark:bg-white/5 dark:text-[hsl(var(--text-secondary))]',
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
                tone === 'neutral' && 'border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-secondary))] dark:border-white/10 dark:bg-white/5 dark:text-[hsl(var(--text-secondary))]',
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
