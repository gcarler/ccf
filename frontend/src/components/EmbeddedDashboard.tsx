"use client";

import { motion } from 'framer-motion';

import React, { useCallback, useEffect, useRef, useState } from 'react';

import {
    Loader2,
    RefreshCw,
    AlertTriangle,
    Download,
    BarChart3,
    Bell,
    BellOff,
    Eye,
    EyeOff,
} from 'lucide-react';
import { DSCard } from '@/design/components/DSCard';
import { DSMetric } from '@/design/components/DSMetric';
import { DSChart } from '@/design/components/DSChart';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import { useToast } from '@/hooks/useToast';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';

// Types
interface MetricData { title: string; value: string; trend?: string; tone?: string; icon?: string; }
interface ChartPoint { label: string; value: number; secondary_value?: number; metadata?: any; }
interface FunnelStage { stage: string; count: number; conversion_rate?: number; }
interface TableRow { id: string; columns: Record<string, any>; link?: string; }
interface AlertRule {
    id: string; metric: string; operator: 'gt' | 'lt' | 'eq'; threshold: number;
    label: string; enabled: boolean;
}

// ─── PDF Export ──────────────────────────────────────────────────────
function exportToPdf(module: string, element: HTMLElement | null) {
    if (!element) return;
    // We use window.print with a specific stylesheet for clean PDF output
    const originalTitle = document.title;
    document.title = `Dashboard ${module} - CCF Mesh`;

    // Inject print styles
    const style = document.createElement('style');
    style.id = 'pdf-export-style';
    style.textContent = `
        @media print {
            body * { visibility: hidden; }
            #dashboard-export-area, #dashboard-export-area * { visibility: visible; }
            #dashboard-export-area { position: absolute; left: 0; top: 0; width: 100%; }
            .no-print { display: none !important; }
            @page { margin: 1.5cm; size: A4 landscape; }
        }
    `;
    document.head.appendChild(style);
    window.print();
    document.head.removeChild(style);
    document.title = originalTitle;
}

// ─── Alert Badge ─────────────────────────────────────────────────────
function AlertBadge({ rules, metrics }: { rules: AlertRule[]; metrics: Record<string, number> }) {
    const activeAlerts = rules.filter(r => {
        const val = metrics[r.metric];
        if (val === undefined) return false;
        if (r.operator === 'gt') return val > r.threshold;
        if (r.operator === 'lt') return val < r.threshold;
        return val === r.threshold;
    });

    if (!activeAlerts.length) return null;

    return (
        <div className="flex items-center gap-1.5 px-2 py-1 bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/20 rounded-md">
            <AlertTriangle size={12} className="text-[hsl(var(--destructive))]" />
            <span className="text-[10px] font-bold text-[hsl(var(--destructive))] dark:text-[hsl(var(--destructive))]">
                {activeAlerts.length} alerta{activeAlerts.length > 1 ? 's' : ''}
            </span>
        </div>
    );
}

// ─── Alert Config Drawer ─────────────────────────────────────────────
function AlertConfigDrawer({
    open, onClose, rules, onSave, module,
}: {
    open: boolean; onClose: () => void; rules: AlertRule[];
    onSave: (r: AlertRule[]) => void; module: string;
}) {
    const [localRules, setLocalRules] = useState<AlertRule[]>(rules);
    const [newMetric, setNewMetric] = useState('');
    const [newOp, setNewOp] = useState<'gt' | 'lt' | 'eq'>('gt');
    const [newThreshold, setNewThreshold] = useState('10');
    const [newLabel, setNewLabel] = useState('');

    useEffect(() => { setLocalRules(rules); }, [rules, open]);

    if (!open) return null;

    const addRule = () => {
        if (!newMetric) return;
        setLocalRules(prev => [...prev, {
            id: `alert-${Date.now()}`,
            metric: newMetric, operator: newOp, threshold: parseFloat(newThreshold) || 0,
            label: newLabel || newMetric, enabled: true,
        }]);
        setNewMetric(''); setNewLabel('');
    };

    return (
        <WorkspaceDrawer
            isOpen={open}
            onClose={onClose}
            title={`Alertas - ${module}`}
            subtitle="Configura reglas para monitoreo automático"
            actions={(
                <div className="flex items-center justify-end gap-2">
                    <button
                        type="button"
                        onClick={onClose}
                        className="px-3 py-2 text-[11px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]"
                    >
                        Cancelar
                    </button>
                    <button
                        type="button"
                        onClick={() => { onSave(localRules); onClose(); }}
                        className="px-3 py-2 rounded-md bg-[hsl(var(--primary))] text-white text-[11px] font-bold uppercase tracking-wide transition-colors"
                    >
                        Guardar
                    </button>
                </div>
            )}
        >
            <div className="space-y-4">
                <div className="space-y-2 max-h-44 overflow-y-auto">
                    {localRules.map(r => (
                        <div key={r.id} className="flex items-center justify-between rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] px-3 py-2">
                            <div className="flex min-w-0 items-center gap-2">
                                <button onClick={() => {
                                    setLocalRules(prev => prev.map(x => x.id === r.id ? {...x, enabled: !x.enabled} : x));
                                }}>
                                    {r.enabled ? <Bell size={14} className="text-[hsl(var(--primary))]" /> : <BellOff size={14} className="text-[hsl(var(--text-secondary))]" />}
                                </button>
                                <span className="truncate text-[11px] font-medium text-[hsl(var(--text-primary))]">
                                    {r.label}
                                </span>
                                <span className="shrink-0 text-[10px] text-[hsl(var(--text-secondary))]">
                                    {r.metric} {r.operator === 'gt' ? '>' : r.operator === 'lt' ? '<' : '='} {r.threshold}
                                </span>
                            </div>
                            <button
                                onClick={() => setLocalRules(prev => prev.filter(x => x.id !== r.id))}
                                className="text-[9px] font-bold uppercase tracking-wide text-[hsl(var(--destructive))]"
                            >
                                Eliminar
                            </button>
                        </div>
                    ))}
                </div>

                <div className="grid grid-cols-4 gap-2">
                    <input
                        value={newMetric}
                        onChange={e => setNewMetric(e.target.value)}
                        placeholder="Métrica (ej: attendance)"
                        className="col-span-2 rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--bg-muted))] px-2 py-1.5 text-[11px] text-[hsl(var(--text-primary))] placeholder:text-[hsl(var(--text-secondary))]"
                    />
                    <select
                        value={newOp}
                        onChange={e => setNewOp(e.target.value as any)}
                        className="rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--bg-muted))] px-1 py-1.5 text-[11px] text-[hsl(var(--text-primary))]"
                    >
                        <option value="gt">&gt;</option><option value="lt">&lt;</option><option value="eq">=</option>
                    </select>
                    <input
                        value={newThreshold}
                        onChange={e => setNewThreshold(e.target.value)}
                        type="number"
                        className="rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--bg-muted))] px-2 py-1.5 text-[11px] text-[hsl(var(--text-primary))]"
                    />
                </div>
                {newMetric && (
                    <input
                        value={newLabel}
                        onChange={e => setNewLabel(e.target.value)}
                        placeholder="Nombre visible (ej: Asistencia baja)"
                        className="w-full rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--bg-muted))] px-2 py-1.5 text-[11px] text-[hsl(var(--text-primary))] placeholder:text-[hsl(var(--text-secondary))]"
                    />
                )}
                <button
                    onClick={addRule}
                    disabled={!newMetric}
                    className="inline-flex items-center gap-2 rounded-md bg-[hsl(var(--surface-2))] px-3 py-2 text-[11px] font-bold uppercase tracking-wide text-[hsl(var(--primary))] disabled:opacity-40"
                >
                    + Agregar Regla
                </button>
            </div>
        </WorkspaceDrawer>
    );
}

// ─── Main EmbeddedDashboard ──────────────────────────────────────────
interface EmbeddedDashboardProps {
    module: string;
    title?: string;
    compact?: boolean;
    refreshInterval?: number; // seconds, 0 = no auto-refresh
    showExport?: boolean;
    showAlerts?: boolean;
    maxHeight?: string;
}

export default function EmbeddedDashboard({
    module, title, compact = false, refreshInterval = 0,
    showExport = true, showAlerts = true, maxHeight,
}: EmbeddedDashboardProps) {
    const { token } = useAuth();
    const toast = useToast();
    const exportRef = useRef<HTMLDivElement>(null);
    const [data, setData] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [alertConfigOpen, setAlertConfigOpen] = useState(false);
    const [alertRules, setAlertRules] = useState<AlertRule[]>([]);
    const [filters, setFilters] = useState<Record<string, string>>({});
    const [filterDefs, setFilterDefs] = useState<any[]>([]);
    const [showFilters, setShowFilters] = useState(false);

    const fetchData = useCallback(async () => {
        if (!token) return;
        setLoading(true);
        setError(null);
        try {
            const params = new URLSearchParams();
            Object.entries(filters).forEach(([k, v]) => { if (v) params.set(k, v); });
            const qs = params.toString();
            const res = await apiFetch<any>(`/dashboard/${module}${qs ? `?${qs}` : ''}`, { token });
            setData(res);
            if (res.filters) setFilterDefs(res.filters);
        } catch (err: any) {
            setError(err?.message || 'Error al cargar');
        } finally {
            setLoading(false);
        }
    }, [module, token, filters]);

    useEffect(() => { fetchData(); }, [fetchData]);

    // Auto-refresh
    useEffect(() => {
        if (!refreshInterval || refreshInterval <= 0) return;
        const interval = setInterval(fetchData, refreshInterval * 1000);
        return () => clearInterval(interval);
    }, [fetchData, refreshInterval]);

    // Load saved alert rules
    useEffect(() => {
        try {
            const saved = localStorage.getItem(`dash-alerts-${module}`);
            if (saved) setAlertRules(JSON.parse(saved));
        } catch {}
    }, [module]);

    const saveAlertRules = (rules: AlertRule[]) => {
        setAlertRules(rules);
        localStorage.setItem(`dash-alerts-${module}`, JSON.stringify(rules));
        toast('Reglas de alerta guardadas', 'success');
    };

    // Extract numeric metrics for alerts
    const extractMetrics = (): Record<string, number> => {
        if (!data?.cards) return {};
        const m: Record<string, number> = {};
        data.cards.forEach((c: MetricData) => {
            const num = parseFloat(c.value.replace(/[$,.%]/g, ''));
            if (!isNaN(num)) m[c.title] = num;
            if (c.trend) {
                const t = parseFloat(c.trend.replace(/[+%]/g, ''));
                if (!isNaN(t)) m[`${c.title}_trend`] = t;
            }
        });
        if (data.attendance_rate !== undefined) m['attendance'] = data.attendance_rate;
        if (data.seguimientos_pendientes !== undefined) m['seguimientos'] = data.seguimientos_pendientes;
        if (data.slas_vencidos !== undefined) m['slas'] = data.slas_vencidos;
        if (data.conversion_rate !== undefined) m['conversion'] = data.conversion_rate;
        if (data.delayed_tasks_count !== undefined) m['vencidas'] = data.delayed_tasks_count;
        return m;
    };

    const metrics = extractMetrics();
    const hasAlerts = alertRules.some(r => {
        const val = metrics[r.metric];
        if (val === undefined) return false;
        if (r.operator === 'gt') return val > r.threshold;
        if (r.operator === 'lt') return val < r.threshold;
        return val === r.threshold;
    });

    const containerClass = compact
        ? 'bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border))] dark:border-white/5 rounded-lg p-3'
        : 'space-y-4';

    // ── Render ──
    return (
        <div className={containerClass} style={maxHeight ? { maxHeight, overflowY: 'auto' } : undefined}>
            {/* Toolbar */}
            <div className="flex items-center justify-between mb-2 no-print">
                <div className="flex items-center gap-2">
                    {title && (
                        <h3 className="text-[13px] font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] flex items-center gap-1.5">
                            <BarChart3 size={14} className="text-[hsl(var(--primary))]" /> {title}
                        </h3>
                    )}
                    {hasAlerts && <AlertBadge rules={alertRules} metrics={metrics} />}
                    {refreshInterval > 0 && (
                        <span className="text-[9px] text-[hsl(var(--text-secondary))] animate-pulse">● vivo</span>
                    )}
                </div>
                <div className="flex items-center gap-1">
                    {filterDefs.length > 0 && (
                        <button onClick={() => setShowFilters(!showFilters)}
                            className="p-1.5 rounded-md hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 text-[hsl(var(--text-secondary))] transition-colors"
                            title="Filtros">
                            {showFilters ? <EyeOff size={14} /> : <Eye size={14} />}
                        </button>
                    )}
                    {showAlerts && (
                        <button onClick={() => setAlertConfigOpen(true)}
                            className="p-1.5 rounded-md hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 text-[hsl(var(--text-secondary))] transition-colors relative"
                            title="Configurar alertas">
                            <Bell size={14} />
                            {alertRules.length > 0 && (
                                <span className="absolute -top-0.5 -right-0.5 size-2 bg-[hsl(var(--primary))] rounded-full" />
                            )}
                        </button>
                    )}
                    {showExport && (
                        <button onClick={() => exportToPdf(module, exportRef.current)}
                            className="p-1.5 rounded-md hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 text-[hsl(var(--text-secondary))] transition-colors"
                            title="Exportar PDF">
                            <Download size={14} />
                        </button>
                    )}
                    <button onClick={fetchData} disabled={loading}
                        className="p-1.5 rounded-md hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 text-[hsl(var(--text-secondary))] transition-colors disabled:opacity-40">
                        <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
                    </button>
                </div>
            </div>

            {/* Filters */}
            {showFilters && filterDefs.length > 0 && (
                <div className="flex flex-wrap items-center gap-2 mb-3 p-2 bg-[hsl(var(--surface-1))] dark:bg-white/5 rounded-md">
                    {filterDefs.map((f: any) => (
                        <div key={f.key} className="flex items-center gap-1.5">
                            <label className="text-[9px] font-semibold uppercase text-[hsl(var(--text-secondary))]">{f.label}:</label>
                            <select value={filters[f.key] ?? f.default ?? ''}
                                onChange={e => setFilters(prev => ({...prev, [f.key]: e.target.value}))}
                                className="text-[10px] font-medium bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--bg-muted))] border border-[hsl(var(--border))] dark:border-white/10 rounded-md px-1.5 py-0.5 text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">
                                {(f.options || []).map((o: any) => (
                                    <option key={o.value} value={o.value}>{o.label}</option>
                                ))}
                            </select>
                        </div>
                    ))}
                </div>
            )}

            {/* Content */}
            <div ref={exportRef} id="dashboard-export-area">
                {loading && (
                    <div className="flex items-center justify-center py-8">
                        <Loader2 size={20} className="animate-spin text-[hsl(var(--primary))]" />
                    </div>
                )}

                {error && !loading && (
                    <div className="flex items-center justify-center py-8">
                        <div className="text-center space-y-1">
                            <AlertTriangle size={20} className="mx-auto text-[hsl(var(--warning))]" />
                            <p className="text-[11px] text-[hsl(var(--text-secondary))]">{error}</p>
                            <button onClick={fetchData} className="text-[10px] font-semibold text-[hsl(var(--primary))] hover:underline">Reintentar</button>
                        </div>
                    </div>
                )}

                {!loading && !error && data && (
                    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-3">
                        {/* Metric Cards */}
                        {data.cards?.length > 0 && (
                            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                                {data.cards.map((card: MetricData, i: number) => (
                                    <DSMetric key={i} label={card.title} value={card.value}
                                        trend={card.trend} tone={card.tone as any || 'blue'} />
                                ))}
                            </div>
                        )}

                        {/* Only show rich charts in non-compact mode */}
                        {!compact && (
                            <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
                                {data.pipeline_funnel && (
                                    <DSCard padding="sm"><div className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase mb-2">Pipeline</div>
                                        {data.pipeline_funnel.map((s: FunnelStage) => {
                                            const max = Math.max(...data.pipeline_funnel.map((x: FunnelStage) => x.count), 1);
                                            return (
                                                <div key={s.stage} className="flex items-center gap-2 py-0.5">
                                                    <span className="text-[10px] text-[hsl(var(--text-secondary))] w-20 truncate">{s.stage}</span>
                                                    <div className="flex-1 h-1.5 bg-[hsl(var(--surface-2))] dark:bg-white/5 rounded-full overflow-hidden">
                                                        <div className="h-full rounded-full bg-[hsl(var(--primary))] transition-all duration-500"
                                                            style={{ width: `${(s.count / max) * 100}%` }} />
                                                    </div>
                                                    <span className="text-[10px] font-bold text-[hsl(var(--text-secondary))] w-8 text-right">{s.count}</span>
                                                </div>
                                            );
                                        })}
                                    </DSCard>
                                )}
                                {data.growth_chart && (
                                    <DSCard padding="sm">
                                        <div className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase mb-1">Crecimiento</div>
                                        <DSChart type="area" data={data.growth_chart} height={140} color="hsl(var(--primary))" />
                                    </DSCard>
                                )}
                                {data.asistencia_por_sesion && (
                                    <DSCard padding="sm">
                                        <div className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase mb-1">Asistencia x Sesión</div>
                                        <DSChart type="bar" data={data.asistencia_por_sesion} height={140} color="hsl(var(--success))" />
                                    </DSCard>
                                )}
                                {data.income_by_category && (
                                    <DSCard padding="sm">
                                        <div className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase mb-1">Ingresos x Categoría</div>
                                        <DSChart type="bar" data={data.income_by_category} height={140} color="hsl(var(--info))" />
                                    </DSCard>
                                )}
                                {data.monthly_series && (
                                    <DSCard padding="sm">
                                        <div className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase mb-1">Tendencia Mensual</div>
                                        <DSChart type="area" data={data.monthly_series} height={140} color="hsl(var(--success))" />
                                    </DSCard>
                                )}
                                {data.enrollment_trends && (
                                    <DSCard padding="sm">
                                        <div className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase mb-1">Matrículas</div>
                                        <DSChart type="bar" data={data.enrollment_trends} height={140} color="hsl(var(--success))" />
                                    </DSCard>
                                )}
                                {data.status_distribution && (
                                    <DSCard padding="sm">
                                        <div className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase mb-1">Tareas x Estado</div>
                                        <DSChart type="bar" data={data.status_distribution} height={140} color="hsl(var(--primary))" />
                                    </DSCard>
                                )}
                                {data.usuarios_por_rol && (
                                    <DSCard padding="sm">
                                        <div className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase mb-1">Usuarios x Rol</div>
                                        <DSChart type="bar" data={data.usuarios_por_rol} height={140} color="hsl(var(--text-secondary))" />
                                    </DSCard>
                                )}
                                {data.grupos_por_ubicacion && data.grupos_por_ubicacion.length > 0 && (
                                    <DSCard padding="sm">
                                        <div className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase mb-1">Grupos x Ubicación</div>
                                        <div className="space-y-1">
                                            {data.grupos_por_ubicacion.map((g: any) => (
                                                <div key={g.label} className="flex items-center gap-2 text-[11px]">
                                                    <div className="size-1.5 rounded-full bg-[hsl(var(--primary))]" />
                                                    <span className="text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]">{g.label}</span>
                                                    {g.lat && <span className="text-[9px] text-[hsl(var(--text-secondary))] ml-auto">({g.lat.toFixed(3)}, {g.lng.toFixed(3)})</span>}
                                                </div>
                                            ))}
                                        </div>
                                    </DSCard>
                                )}
                            </div>
                        )}

                        {/* Ausentes/Asistentes tables */}
                        {data.ausentes_detalle?.length > 0 && (
                            <DSCard padding="sm">
                                <div className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase mb-1 flex items-center gap-1">
                                    <AlertTriangle size={10} className="text-[hsl(var(--warning))]" /> Ausentes - {data.ausentes_detalle.length} registros
                                </div>
                                <div className="max-h-32 overflow-y-auto text-[10px]">
                                    {// eslint-disable-next-line @typescript-eslint/no-unused-vars
data.ausentes_detalle.slice(0, 10).map((r: TableRow) => (
                                        <div key={r.id} className="flex items-center gap-2 py-0.5 border-b border-[hsl(var(--border))] dark:border-white/5">
                                            <span className="font-medium text-[hsl(var(--text-secondary))] w-28 truncate">{r.columns.persona || ''}</span>
                                            <span className="text-[hsl(var(--text-secondary))] w-20 truncate">{r.columns.grupo || ''}</span>
                                            <span className="text-[hsl(var(--text-secondary))] w-16">{r.columns.fecha || ''}</span>
                                            <span className="text-[hsl(var(--destructive))] ml-auto text-[9px]">{r.columns.excusa || ''}</span>
                                        </div>
                                    ))}
                                </div>
                            </DSCard>
                        )}
                    </motion.div>
                )}
            </div>

            {/* Alert Config Drawer */}
            <AlertConfigDrawer
                open={alertConfigOpen}
                onClose={() => setAlertConfigOpen(false)}
                rules={alertRules}
                onSave={saveAlertRules}
                module={title || module}
            />
        </div>
    );
}

export type { AlertRule, MetricData, ChartPoint, FunnelStage };
