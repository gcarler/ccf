"use client";

import React, { useCallback, useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import type { LucideIcon } from 'lucide-react';
import clsx from 'clsx';
import {
    LayoutDashboard,
    Loader2,
    RefreshCw,
    Users,
    BookOpen,
    Home,
    PiggyBank,
    Calendar,
    FileText,
    FolderKanban,
    Shield,
    AlertTriangle,
    MapPin,
    List,
    Filter,
} from 'lucide-react';
import { DSCard } from '@/design/components/DSCard';
import { DSMetric } from '@/design/components/DSMetric';
import { DSChart } from '@/design/components/DSChart';
import { DSSectionHeader } from '@/design/components/DSSectionHeader';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';

// ─── Types ─────────────────────────────────────────────────────────

interface FilterDef {
    key: string;
    label: string;
    type: string;
    options?: { label: string; value: string }[];
    default?: any;
}

interface DashboardData {
    cards?: MetricCardData[];
    [key: string]: any;
}

interface MetricCardData {
    title: string;
    value: string;
    trend?: string;
    tone?: string;
    icon?: string;
    subtitle?: string;
}

interface FunnelStage {
    stage: string;
    count: number;
    conversion_rate?: number;
}

interface GeoBucket {
    label: string;
    value: number;
    lat?: number;
    lng?: number;
    metadata?: Record<string, any>;
}

interface HeatmapItem {
    x: string;
    y: string;
    value: number;
}

interface TableRow {
    id: string;
    columns: Record<string, any>;
    link?: string;
}

// ─── Module config ─────────────────────────────────────────────────

const MODULE_CONFIG: Record<string, { label: string; icon: LucideIcon; color: string }> = {
    crm:        { label: 'CRM Pastoral',       icon: Users,        color: 'hsl(var(--primary))' },
    academy:    { label: 'Academia',            icon: BookOpen,     color: 'hsl(var(--success))' },
    evangelism: { label: 'Evangelismo',         icon: Home,         color: 'hsl(var(--warning))' },
    finance:    { label: 'Finanzas',            icon: PiggyBank,    color: 'hsl(var(--info))' },
    agenda:     { label: 'Agenda',              icon: Calendar,     color: 'hsl(var(--primary))' },
    cms:        { label: 'CMS',                 icon: FileText,     color: 'hsl(var(--info))' },
    projects:   { label: 'Proyectos',           icon: FolderKanban, color: 'hsl(var(--accent, 336 80% 58%))' },
    admin:      { label: 'Admin',               icon: Shield,       color: 'hsl(var(--text-secondary))' },
};

// ─── Helpers ───────────────────────────────────────────────────────

// ─── SEO score trend widget (CMS module only) ─────────────────────────

import { SeoTrendCard, type SeoTrendResponse } from '@/components/SeoTrendCard';


function fmtNum(n: number) {
    if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
    if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
    return String(n);
}

// ─── Sub-components ────────────────────────────────────────────────

function FilterBar({
    filters,
    activeFilters,
    onFilterChange,
}: {
    filters: FilterDef[];
    activeFilters: Record<string, string>;
    onFilterChange: (key: string, value: string) => void;
}) {
    if (!filters?.length) return null;

    return (
        <div className="flex flex-wrap items-center gap-2 mb-4">
            <Filter size={14} className="text-[hsl(var(--text-secondary))]" />
            {filters.map((f) => (
                <div key={f.key} className="flex items-center gap-1.5">
                    <label className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                        {f.label}:
                    </label>
                    <select
                        value={activeFilters[f.key] ?? f.default ?? ''}
                        onChange={(e) => onFilterChange(f.key, e.target.value)}
                        className="text-[11px] font-medium bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border))] rounded-md px-2 py-1 text-[hsl(var(--text-primary))] focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]/30"
                    >
                        {(f.options || []).map((opt) => (
                            <option key={opt.value} value={opt.value}>
                                {opt.label}
                            </option>
                        ))}
                    </select>
                </div>
            ))}
        </div>
    );
}

function FunnelChart({ stages }: { stages: FunnelStage[] }) {
    if (!stages?.length) return null;
    const maxVal = Math.max(...stages.map((s) => s.count), 1);

    return (
        <div className="space-y-2">
            {stages.map((s, i) => {
                const pct = (s.count / maxVal) * 100;
                const barColor =
                    i === 0 ? 'bg-[hsl(var(--primary))]' :
                    i === stages.length - 1 ? 'bg-[hsl(var(--success))]' :
                    'bg-[hsl(var(--primary)/0.7)]';
                return (
                    <div key={s.stage} className="space-y-0.5">
                        <div className="flex items-center justify-between text-[11px]">
                            <span className="font-medium text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]">{s.stage}</span>
                            <div className="flex items-center gap-2">
                                <span className="font-bold text-[hsl(var(--text-primary))] dark:text-white">{fmtNum(s.count)}</span>
                                {s.conversion_rate !== undefined && (
                                    <span className="text-[10px] text-[hsl(var(--text-secondary))]">({s.conversion_rate}%)</span>
                                )}
                            </div>
                        </div>
                        <div className="h-2 bg-[hsl(var(--surface-2))] dark:bg-white/5 rounded-full overflow-hidden">
                            <motion.div
                                initial={{ width: 0 }}
                                animate={{ width: `${pct}%` }}
                                transition={{ duration: 0.6, delay: i * 0.1 }}
                                className={clsx('h-full rounded-full', barColor)}
                            />
                        </div>
                    </div>
                );
            })}
        </div>
    );
}

function HeatMap({ data }: { data: HeatmapItem[] }) {
    if (!data?.length) {
        return <p className="text-xs text-[hsl(var(--text-secondary))] italic">Sin datos de interacciones</p>;
    }
    const days = [...new Set(data.map((d) => d.y))];
    const types = [...new Set(data.map((d) => d.x))];
    const maxVal = Math.max(...data.map((d) => d.value), 1);

    return (
        <div className="overflow-x-auto">
            <table className="w-full text-[10px]">
                <thead>
                    <tr>
                        <th className="p-1 text-left text-[hsl(var(--text-secondary))] font-medium">Tipo \ Día</th>
                        {days.map((d) => (
                            <th key={d} className="p-1 text-center text-[hsl(var(--text-secondary))] font-medium">{d.slice(0, 3)}</th>
                        ))}
                    </tr>
                </thead>
                <tbody>
                    {types.map((t) => (
                        <tr key={t}>
                            <td className="p-1 text-[hsl(var(--text-secondary))] font-medium">{t}</td>
                            {days.map((d) => {
                                const item = data.find((h) => h.x === t && h.y === d);
                                const intensity = item ? (item.value / maxVal) * 100 : 0;
                                return (
                                    <td key={d} className="p-1">
                                        <div
                                            className="h-5 w-full rounded"
                                            style={{
                                                backgroundColor: item
                                                    ? `hsl(var(--primary) / ${0.1 + intensity * 0.006})`
                                                    : 'transparent',
                                            }}
                                            title={item ? `${item.value} interacciones` : ''}
                                        />
                                    </td>
                                );
                            })}
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}

function GeoMap({ data }: { data: GeoBucket[] }) {
    if (!data?.length) {
        return (
            <div className="flex items-center justify-center h-48 bg-[hsl(var(--surface-1))] dark:bg-black/20 rounded-lg border border-[hsl(var(--border))] dark:border-white/5">
                <p className="text-xs text-[hsl(var(--text-secondary))] italic">Sin datos geográficos</p>
            </div>
        );
    }

    return (
        <div className="space-y-2">
            {data.map((g) => (
                <div
                    key={g.label}
                    className="flex items-center gap-3 p-2 rounded-lg bg-[hsl(var(--surface-1))] dark:bg-white/5 hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 transition-colors"
                >
                    <div className="size-8 rounded-full bg-[hsl(var(--primary)/0.15)] flex items-center justify-center shrink-0">
                        <MapPin size={14} className="text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))]" />
                    </div>
                    <div className="flex-1 min-w-0">
                        <p className="text-[12px] font-semibold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] truncate">
                            {g.label}
                        </p>
                        {g.lat && g.lng && (
                            <p className="text-[9px] text-[hsl(var(--text-secondary))]">
                                {g.lat.toFixed(4)}, {g.lng.toFixed(4)}
                            </p>
                        )}
                    </div>
                </div>
            ))}
        </div>
    );
}

function DataTable({ rows, title }: { rows: TableRow[]; title?: string }) {
    if (!rows?.length) {
        return (
            <div className="flex items-center justify-center h-24 bg-[hsl(var(--surface-1))] dark:bg-black/20 rounded-lg border border-[hsl(var(--border))] dark:border-white/5">
                <p className="text-xs text-[hsl(var(--text-secondary))] italic">Sin datos</p>
            </div>
        );
    }

    const columns = Object.keys(rows[0].columns ?? {});

    return (
        <div className="overflow-x-auto">
            {title && (
                <p className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-2">{title}</p>
            )}
            <table className="w-full text-[11px]">
                <thead>
                    <tr className="border-b border-[hsl(var(--border))] dark:border-white/5">
                        {columns.map((col) => (
                            <th key={col} className="text-left py-2 px-1.5 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                                {col}
                            </th>
                        ))}
                    </tr>
                </thead>
                <tbody>
                    {rows.map((row) => (
                        <tr
                            key={row.id}
                            className="border-b border-[hsl(var(--border))] dark:border-white/5 hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 transition-colors cursor-pointer"
                            onClick={() => row.link && (window.location.href = row.link)}
                        >
                            {columns.map((col) => (
                                <td key={col} className="py-2 px-1.5 text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">
                                    {String(row.columns[col] ?? '—')}
                                </td>
                            ))}
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}


// ─── DashboardShell ────────────────────────────────────────────────

interface DashboardShellProps {
    module: string;
    title?: string;
    extraCharts?: React.ReactNode;
    children?: React.ReactNode;
}

export default function DashboardShell({
    module,
    title,
    extraCharts,
    children,
}: DashboardShellProps) {
    const { token } = useAuth();
    const [data, setData] = useState<DashboardData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [filters, setFilters] = useState<Record<string, string>>({});
    const [filterDefs, setFilterDefs] = useState<FilterDef[]>([]);
    const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');

    const config = MODULE_CONFIG[module];

    const fetchDashboard = useCallback(async () => {
        if (!token) return;
        setLoading(true);
        setError(null);
        try {
            const params = new URLSearchParams();
            Object.entries(filters).forEach(([k, v]) => {
                if (v) params.set(k, v);
            });
            const qs = params.toString();
            const res = await apiFetch<any>(`/dashboard/${module}${qs ? `?${qs}` : ''}`, { token });
            setData(res);
            if (res.filters) setFilterDefs(res.filters);
        } catch (err: any) {
            setError(err?.message || 'Error al cargar dashboard');
        } finally {
            setLoading(false);
        }
    }, [module, token, filters]);

    useEffect(() => {
        fetchDashboard();
    }, [fetchDashboard]);

    const handleFilterChange = (key: string, value: string) => {
        setFilters((prev) => ({ ...prev, [key]: value }));
    };

    const containerVariants = {
        hidden: { opacity: 0 },
        show: { opacity: 1, transition: { staggerChildren: 0.08 } },
    };

    const itemVariants = {
        hidden: { opacity: 0, y: 16 },
        show: { opacity: 1, y: 0, transition: { type: 'spring', stiffness: 300, damping: 24 } },
    };

    const MetricIcon = config?.icon || LayoutDashboard;

    // ── Render ──
    return (
        <div className="flex flex-col h-full bg-[hsl(var(--surface-1))] dark:bg-transparent p-4 font-sans">
            {/* Header */}
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                    <div className={clsx(
                        'size-10 rounded-xl flex items-center justify-center',
                        'bg-[hsl(var(--primary)/0.08)]',
                    )}>
                        <MetricIcon size={20} className="text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))]" />
                    </div>
                    <div>
                        <h1 className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tight">
                            {title || config?.label || module}
                        </h1>
                        {data?.last_updated && (
                            <p className="text-[10px] text-[hsl(var(--text-secondary))]">
                                Actualizado: {new Date(data.last_updated).toLocaleString('es-CO')}
                            </p>
                        )}
                    </div>
                </div>
                <div className="flex items-center gap-2">
                    <button
                        onClick={() => setViewMode(viewMode === 'grid' ? 'list' : 'grid')}
                        className="p-1.5 rounded-md hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 text-[hsl(var(--text-secondary))] transition-colors"
                        title="Cambiar vista"
                    >
                        {viewMode === 'grid' ? <List size={16} /> : <LayoutDashboard size={16} />}
                    </button>
                    <button
                        onClick={fetchDashboard}
                        disabled={loading}
                        className="p-1.5 rounded-md hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 text-[hsl(var(--text-secondary))] transition-colors disabled:opacity-40"
                        title="Actualizar"
                    >
                        <RefreshCw size={16} className={clsx(loading && 'animate-spin')} />
                    </button>
                </div>
            </div>

            {/* Filters */}
            <FilterBar
                filters={filterDefs}
                activeFilters={filters}
                onFilterChange={handleFilterChange}
            />

            {/* Loading */}
            {loading && (
                <div className="flex items-center justify-center h-64">
                    <Loader2 size={24} className="animate-spin text-[hsl(var(--primary))]" />
                </div>
            )}

            {/* Error */}
            {error && !loading && (
                <div className="flex items-center justify-center h-64">
                    <div className="text-center space-y-2">
                        <AlertTriangle size={32} className="mx-auto text-amber-500" />
                        <p className="text-sm text-[hsl(var(--text-secondary))]">{error}</p>
                        <button
                            onClick={fetchDashboard}
                            className="text-[11px] font-semibold text-[hsl(var(--primary))] hover:underline"
                        >
                            Reintentar
                        </button>
                    </div>
                </div>
            )}

            {/* Dashboard Content */}
            {!loading && !error && data && (
                <motion.div
                    variants={containerVariants}
                    initial="hidden"
                    animate="show"
                    className="space-y-4"
                >
                    {/* Metric Cards */}
                    {data.cards && data.cards.length > 0 && (
                        <motion.div
                            variants={itemVariants}
                            className={clsx(
                                viewMode === 'grid'
                                    ? 'grid grid-cols-2 md:grid-cols-4 gap-3'
                                    : 'flex flex-col gap-2'
                            )}
                        >
                            {data.cards.map((card: MetricCardData, idx: number) => (
                                <DSMetric
                                    key={idx}
                                    label={card.title}
                                    value={card.value}
                                    trend={card.trend}
                                    tone={(card.tone as any) || 'blue'}
                                />
                            ))}
                        </motion.div>
                    )}

                    {/* ── CMS SEO score trend widget (data-driven; rendered
                        whenever the dashboard payload includes seo_trend
                        with has_data=true) ───────────────────────── */}
                    {data.seo_trend?.has_data && (
                        <motion.div variants={itemVariants}>
                            <SeoTrendCard trend={data.seo_trend as SeoTrendResponse} />
                        </motion.div>
                    )}

                    {/* Charts grid — 2 columns */}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">

                        {/* Pipeline / Funnel */}
                        {data.pipeline_funnel && (
                            <motion.div variants={itemVariants}>
                                <DSCard padding="md">
                                    <DSSectionHeader
                                        eyebrow="Pipeline"
                                        title="Distribución por Etapa"
                                        description="Casos activos en cada etapa del pipeline"
                                    />
                                    <div className="mt-4">
                                        <FunnelChart stages={data.pipeline_funnel} />
                                    </div>
                                </DSCard>
                            </motion.div>
                        )}

                        {/* Growth chart (line) */}
                        {data.growth_chart && (
                            <motion.div variants={itemVariants}>
                                <DSCard padding="md">
                                    <DSSectionHeader
                                        eyebrow="Crecimiento"
                                        title="Tendencia Mensual"
                                    />
                                    <div className="mt-3">
                                        <DSChart
                                            type="area"
                                            data={data.growth_chart}
                                            height={200}
                                            color="hsl(var(--primary))"
                                        />
                                    </div>
                                </DSCard>
                            </motion.div>
                        )}

                        {/* Enrollment trends (Academy) */}
                        {data.enrollment_trends && (
                            <motion.div variants={itemVariants}>
                                <DSCard padding="md">
                                    <DSSectionHeader
                                        eyebrow="Matrículas"
                                        title="Tendencia de Inscripciones"
                                    />
                                    <div className="mt-3">
                                        <DSChart
                                            type="bar"
                                            data={data.enrollment_trends}
                                            height={200}
                                            color="hsl(var(--success))"
                                        />
                                    </div>
                                </DSCard>
                            </motion.div>
                        )}

                        {/* Income by category (Finance) */}
                        {data.income_by_category && (
                            <motion.div variants={itemVariants}>
                                <DSCard padding="md">
                                    <DSSectionHeader
                                        eyebrow="Ingresos"
                                        title="Por Categoría"
                                    />
                                    <div className="mt-3">
                                        <DSChart
                                            type="bar"
                                            data={data.income_by_category}
                                            height={200}
                                            color="hsl(var(--info))"
                                        />
                                    </div>
                                </DSCard>
                            </motion.div>
                        )}

                        {/* Monthly series (Finance) */}
                        {data.monthly_series && (
                            <motion.div variants={itemVariants}>
                                <DSCard padding="md">
                                    <DSSectionHeader
                                        eyebrow="Histórico"
                                        title="Comparativa Mensual"
                                    />
                                    <div className="mt-3">
                                        <DSChart
                                            type="area"
                                            data={data.monthly_series}
                                            height={200}
                                            color="hsl(var(--success))"
                                        />
                                    </div>
                                </DSCard>
                            </motion.div>
                        )}

                        {/* Interaction heatmap (CRM) */}
                        {data.interaction_heatmap && (
                            <motion.div variants={itemVariants}>
                                <DSCard padding="md">
                                    <DSSectionHeader
                                        eyebrow="Interacciones"
                                        title="Mapa de Calor"
                                        description="Tipo × Día de la semana"
                                    />
                                    <div className="mt-3">
                                        <HeatMap data={data.interaction_heatmap} />
                                    </div>
                                </DSCard>
                            </motion.div>
                        )}

                        {/* Embudo evangelism */}
                        {data.embudo && !data.pipeline_funnel && (
                            <motion.div variants={itemVariants}>
                                <DSCard padding="md">
                                    <DSSectionHeader
                                        eyebrow="Embudo"
                                        title="Estrategias → Asistentes"
                                    />
                                    <div className="mt-4">
                                        <FunnelChart stages={data.embudo} />
                                    </div>
                                </DSCard>
                            </motion.div>
                        )}

                        {/* Asistencia por sesión */}
                        {data.asistencia_por_sesion && (
                            <motion.div variants={itemVariants}>
                                <DSCard padding="md">
                                    <DSSectionHeader
                                        eyebrow="Asistencia"
                                        title="Últimas 10 Sesiones"
                                        description="Verdes = presentes, naranja = ausentes"
                                    />
                                    <div className="mt-3">
                                        <DSChart
                                            type="bar"
                                            data={data.asistencia_por_sesion}
                                            height={200}
                                            color="hsl(var(--success))"
                                        />
                                    </div>
                                </DSCard>
                            </motion.div>
                        )}

                        {/* Grupos por ubicación */}
                        {data.grupos_por_ubicacion && (
                            <motion.div variants={itemVariants}>
                                <DSCard padding="md">
                                    <DSSectionHeader
                                        eyebrow="Geografía"
                                        title="Grupos por Ubicación"
                                    />
                                    <div className="mt-3">
                                        <GeoMap data={data.grupos_por_ubicacion} />
                                    </div>
                                </DSCard>
                            </motion.div>
                        )}

                        {/* Grade distribution */}
                        {data.grade_distribution && (
                            <motion.div variants={itemVariants}>
                                <DSCard padding="md">
                                    <DSSectionHeader
                                        eyebrow="Rendimiento"
                                        title="Distribución de Notas"
                                    />
                                    <div className="mt-3">
                                        <DSChart
                                            type="bar"
                                            data={data.grade_distribution}
                                            height={200}
                                            color="hsl(var(--primary))"
                                        />
                                    </div>
                                </DSCard>
                            </motion.div>
                        )}

                        {/* Versiones por página (CMS) */}
                        {data.versiones_por_pagina && (
                            <motion.div variants={itemVariants}>
                                <DSCard padding="md">
                                    <DSSectionHeader
                                        eyebrow="Versiones"
                                        title="Top Páginas por Versiones"
                                    />
                                    <div className="mt-3">
                                        <DSChart
                                            type="bar"
                                            data={data.versiones_por_pagina}
                                            height={200}
                                            color="hsl(var(--info))"
                                        />
                                    </div>
                                </DSCard>
                            </motion.div>
                        )}

                        {/* Publicaciones por mes (CMS) */}
                        {data.publicaciones_por_mes && (
                            <motion.div variants={itemVariants}>
                                <DSCard padding="md">
                                    <DSSectionHeader
                                        eyebrow="Publicaciones"
                                        title="Por Mes"
                                    />
                                    <div className="mt-3">
                                        <DSChart
                                            type="line"
                                            data={data.publicaciones_por_mes}
                                            height={200}
                                            color="#06b6d4"
                                        />
                                    </div>
                                </DSCard>
                            </motion.div>
                        )}

                        {/* Workload distribution (Projects) */}
                        {data.workload_distribution && (
                            <motion.div variants={itemVariants}>
                                <DSCard padding="md">
                                    <DSSectionHeader
                                        eyebrow="Carga"
                                        title="Asignación por Persona"
                                    />
                                    <div className="mt-3">
                                        <DSChart
                                            type="bar"
                                            data={data.workload_distribution}
                                            height={200}
                                            color="hsl(var(--primary))"
                                        />
                                    </div>
                                </DSCard>
                            </motion.div>
                        )}

                        {/* Status distribution (Projects) */}
                        {data.status_distribution && (
                            <motion.div variants={itemVariants}>
                                <DSCard padding="md">
                                    <DSSectionHeader
                                        eyebrow="Estado"
                                        title="Tareas por Estado"
                                    />
                                    <div className="mt-3">
                                        <DSChart
                                            type="bar"
                                            data={data.status_distribution}
                                            height={200}
                                            color="hsl(var(--primary))"
                                        />
                                    </div>
                                </DSCard>
                            </motion.div>
                        )}

                        {/* Usuarios por rol (Admin) */}
                        {data.usuarios_por_rol && (
                            <motion.div variants={itemVariants}>
                                <DSCard padding="md">
                                    <DSSectionHeader
                                        eyebrow="Usuarios"
                                        title="Distribución por Rol"
                                    />
                                    <div className="mt-3">
                                        <DSChart
                                            type="bar"
                                            data={data.usuarios_por_rol}
                                            height={200}
                                            color="hsl(var(--text-secondary))"
                                        />
                                    </div>
                                </DSCard>
                            </motion.div>
                        )}

                        {/* Participación por evento (Agenda) */}
                        {data.participacion_por_evento && (
                            <motion.div variants={itemVariants}>
                                <DSCard padding="md">
                                    <DSSectionHeader
                                        eyebrow="Eventos"
                                        title="Top por Participación"
                                    />
                                    <div className="mt-3">
                                        <DSChart
                                            type="bar"
                                            data={data.participacion_por_evento}
                                            height={200}
                                            color="hsl(var(--primary))"
                                        />
                                    </div>
                                </DSCard>
                            </motion.div>
                        )}

                        {/* Recursos ocupados (Agenda) */}
                        {data.recursos_ocupados && data.recursos_ocupados.length > 0 && (
                            <motion.div variants={itemVariants}>
                                <DSCard padding="md">
                                    <DSSectionHeader
                                        eyebrow="Recursos"
                                        title="Ocupación"
                                    />
                                    <div className="mt-3">
                                        <DSChart
                                            type="bar"
                                            data={data.recursos_ocupados}
                                            height={200}
                                            color="hsl(var(--warning))"
                                        />
                                    </div>
                                </DSCard>
                            </motion.div>
                        )}

                        {/* Extra charts from parent */}
                        {extraCharts}
                    </div>

                    {/* Detail tables — full width */}
                    {data.ausentes_detalle && (
                        <motion.div variants={itemVariants}>
                            <DSCard padding="md">
                                <DSSectionHeader
                                    eyebrow="Detalle"
                                    title="Ausentes (últimos 30 días)"
                                    description="Quiénes faltaron, de qué grupo, y su excusa"
                                />
                                <div className="mt-3">
                                    <DataTable rows={data.ausentes_detalle} title="Ausencias" />
                                </div>
                            </DSCard>
                        </motion.div>
                    )}

                    {data.asistentes_detalle && (
                        <motion.div variants={itemVariants}>
                            <DSCard padding="md">
                                <DSSectionHeader
                                    eyebrow="Detalle"
                                    title="Asistentes (últimos 30 días)"
                                />
                                <div className="mt-3">
                                    <DataTable rows={data.asistentes_detalle} title="Asistencias" />
                                </div>
                            </DSCard>
                        </motion.div>
                    )}

                    {/* Top courses (Academy) */}
                    {data.top_courses && (
                        <motion.div variants={itemVariants}>
                            <DSCard padding="md">
                                <DSSectionHeader
                                    eyebrow="Cursos"
                                    title="Top 5 Cursos por Matrícula"
                                />
                                <div className="mt-3 space-y-2">
                                    {data.top_courses.map((c: any, i: number) => (
                                        <div
                                            key={i}
                                            className="flex items-center justify-between py-1.5 px-2 rounded-md bg-[hsl(var(--surface-1))] dark:bg-white/5"
                                        >
                                            <span className="text-[12px] font-medium text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">
                                                {c.title}
                                            </span>
                                            <span className="text-[11px] font-bold text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))]">
                                                {c.count} matriculados
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            </DSCard>
                        </motion.div>
                    )}

                    {/* Latest donations (Finance) */}
                    {data.latest_donations && (
                        <motion.div variants={itemVariants}>
                            <DSCard padding="md">
                                <DSSectionHeader
                                    eyebrow="Donaciones"
                                    title="Últimos 5 Aportes"
                                />
                                <div className="mt-3 space-y-2">
                                    {data.latest_donations.map((d: any, i: number) => (
                                        <div
                                            key={i}
                                            className="flex items-center justify-between py-1.5 px-2 rounded-md bg-[hsl(var(--surface-1))] dark:bg-white/5"
                                        >
                                            <div>
                                                <p className="text-[12px] font-medium text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">
                                                    {d.donor}
                                                </p>
                                                <p className="text-[10px] text-[hsl(var(--text-secondary))]">{d.type}</p>
                                            </div>
                                            <span className="text-[12px] font-bold text-[hsl(var(--success))]">
                                                ${Number(d.amount).toLocaleString()}
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            </DSCard>
                        </motion.div>
                    )}

                    {/* Próximos eventos (Agenda) */}
                    {data.eventos_proximos && (
                        <motion.div variants={itemVariants}>
                            <DSCard padding="md">
                                <DSSectionHeader
                                    eyebrow="Próximos"
                                    title="Próximos 5 Eventos"
                                />
                                <div className="mt-3 space-y-2">
                                    {data.eventos_proximos.map((e: any, i: number) => (
                                        <div
                                            key={i}
                                            className="flex items-center justify-between py-1.5 px-2 rounded-md bg-[hsl(var(--surface-1))] dark:bg-white/5"
                                        >
                                            <div>
                                                <p className="text-[12px] font-medium text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">
                                                    {e.titulo}
                                                </p>
                                                <p className="text-[10px] text-[hsl(var(--text-secondary))]">
                                                    {e.ubicacion} · {e.participantes} participantes
                                                </p>
                                            </div>
                                            <span className="text-[11px] text-[hsl(var(--text-secondary))]">
                                                {new Date(e.fecha).toLocaleDateString('es-CO', {
                                                    day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
                                                })}
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            </DSCard>
                        </motion.div>
                    )}

                    {children}
                </motion.div>
            )}
        </div>
    );
}

export { FunnelChart, HeatMap, GeoMap, DataTable, MODULE_CONFIG };
