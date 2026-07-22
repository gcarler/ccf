"use client";

import DashboardEmbed from '@/components/DashboardEmbed';
import WorkspaceLayout from '@/components/WorkspaceLayout';
import { useAuth } from '@/context/AuthContext';
import { DSCard } from '@/design/components/DSCard';
import { DSChart } from '@/design/components/DSChart';
import { DSMetric } from '@/design/components/DSMetric';
import { apiFetch } from '@/lib/http';
import clsx from 'clsx';
import { motion } from 'framer-motion';
import {
BarChart3,
ChevronRight,
CircleDollarSign,
Download,
Gift,HeartHandshake,
Landmark,
Loader2,
Plus,
Search,
Zap
} from 'lucide-react';
import React,{ useEffect,useMemo,useState } from 'react';
import { toast } from 'sonner';

// ─── Helpers ───────────────────────────────────────────────────────────────────
// ─── Tipo local ───────────────────────────────────────────────────────────────
interface DashboardCard {
    title: string;
    value: string;
    trend?: string;
    tone?: 'blue' | 'emerald' | 'amber';
    color?: 'blue' | 'emerald' | 'amber';
    icon?: string;
    subtitle?: string;
}
interface ChartDataPoint {
    label: string;
    value: number;
    secondary_value?: number;
    metadata?: Record<string, unknown>;
}
interface DashboardFinance {
    cards: DashboardCard[];
    income_by_category?: ChartDataPoint[];
    monthly_comparison?: ChartDataPoint[];
    monthly_series?: ChartDataPoint[];
    pending_pledges_total?: number;
    latest_donations?: Array<Record<string, unknown>>;
    last_updated?: string;
}
interface TxRecord {
    id: number;
    type: 'ingreso' | 'egreso';
    category: string;
    description: string;
    amount: number;
    date: string | null;
}

// ─── Iconos por categoría ─────────────────────────────────────────────────────
const CATEGORY_ICON: Record<string, React.ElementType> = {
    'Diezmo': HeartHandshake,
    'Diezmos': HeartHandshake,
    'Ofrenda': Gift,
    'Ofrendas': Gift,
    'Especial': Zap,
    'Donación': CircleDollarSign,
};
const DEFAULT_ICON = CircleDollarSign;


function fmt(n: number) {
    return new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 }).format(n);
}

export default function FinancesPage() {
    const { token } = useAuth();
    const [filter, setFilter] = useState<'all' | 'ingreso' | 'egreso'>('all');
    const [search, setSearch] = useState('');
    const [transactions, setTransactions] = useState<TxRecord[]>([]);
    const [dashboard, setDashboard] = useState<DashboardFinance | null>(null);
    const [loading, setLoading] = useState(true);

    const FINANCE_SECTIONS = useMemo(() => ([
        {
            title: 'Reportes',
            items: [
                { id: 'finances', label: 'Resumen', href: '/plataforma/finances', icon: BarChart3 },
                { id: 'transparency', label: 'Transparencia', href: '/plataforma/finances/transparency', icon: Landmark },
            ],
        },
    ]), []);

    useEffect(() => {
        const ctrl = new AbortController();
        if (!token) { setLoading(false); return; }
        Promise.all([
            apiFetch<TxRecord[]>('/finance/transactions?limit=50', { token, cache: 'no-store', signal: ctrl.signal }),
            apiFetch<DashboardFinance>('/dashboard/finance', { token, cache: 'no-store', signal: ctrl.signal }),
        ]).then(([txs, dbData]) => {
            if (Array.isArray(txs)) setTransactions(txs);
            if (dbData) setDashboard(dbData);
        }).catch(e => { if (e.name !== 'AbortError') { console.error(e); toast.error('Error al cargar datos'); } })
        .finally(() => setLoading(false));
        return () => ctrl.abort();
    }, [token]);

    const filtered = useMemo(() => transactions.filter(t => {
        if (filter !== 'all' && t.type !== filter) return false;
        if (search && !t.description.toLowerCase().includes(search.toLowerCase())) return false;
        return true;
    }), [transactions, filter, search]);

    return (
        <WorkspaceLayout
        sidebarTitle="Tesorería Pro"
        sidebarSections={FINANCE_SECTIONS}
    >
        <div className="h-full overflow-y-auto bg-[#f8fafc] dark:bg-[#1E1F21] font-display scrollbar-thin">
 <div className="w-full px-4 py-3 space-y-3">

                {/* Header */}
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tight uppercase">
                            Centro Financiero
                        </h1>
                        <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--primary))] mt-0.5">
                            Gestión de Recursos Ministeriales
                        </p>
                    </div>
                    <div className="flex items-center gap-2">
                        <div className="flex items-center gap-1 bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-md p-0.5 text-[10px] font-semibold">
                            {(['Semana', 'Mes', 'Año']).map((p) => (
                                <button key={p} className={clsx(
                                    'px-2 py-1 rounded-md transition-colors',
                                    p === 'Mes' ? 'bg-[hsl(var(--primary))] text-white shadow-sm' : 'text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] dark:hover:text-[hsl(var(--text-secondary))]'
                                )}>{p}</button>
                            ))}
                        </div>
                        <button className="flex items-center gap-1.5 px-2.5 py-1.5 bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-md text-[10px] font-semibold text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/10 transition-all">
                            <Download size={12} /> Exportar
                        </button>
                        <button className="flex items-center gap-1.5 px-3 py-1.5 bg-[hsl(var(--primary))] text-white rounded-md text-[10px] font-semibold shadow-sm hover:bg-[hsl(var(--primary))] active:scale-95 transition-all">
                            <Plus size={12} /> Registro
                        </button>
                    </div>
                </div>

                    {/* 📊 Financial Metrics */}
                    <section className="grid grid-cols-1 md:grid-cols-4 gap-4 relative z-10">
                        {dashboard?.cards.map((card, idx) => (
                            <DSMetric 
                                key={idx}
                                label={card.title} 
                                value={card.value} 
                                trend={card.trend} 
                                tone={card.color} 
                            />
                        ))}
                    </section>

                    {/* 📈 Charts */}
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-3 relative z-10">
                        <div className="lg:col-span-2">
                            <DSCard>
                                <h3 className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-3">Comparativa Mensual de Ingresos</h3>
                                <DSChart type="area" data={dashboard?.monthly_comparison} color="#10b981" height={220} />
                            </DSCard>
                        </div>
                        <div>
                            <DSCard>
                                <h3 className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-3">Distribución por Categoría</h3>
                                <DSChart type="bar" data={dashboard?.income_by_category} color="#3b82f6" height={220} />
                            </DSCard>
                        </div>
                    </div>

                    <div className="h-px bg-white/5 my-8 relative z-10" />

                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-3 relative z-10">
                        {/* Transaction List */}
                        <div className="lg:col-span-2 bg-[hsl(var(--bg-primary))] dark:bg-[#1a1b1e] rounded-lg border border-[hsl(var(--border))] dark:border-white/5 shadow-sm overflow-hidden">
                            {/* Table header */}
                            <div className="px-3 py-1.5 border-b border-[hsl(var(--border))] dark:border-white/5 flex items-center justify-between gap-4">
                                <h2 className="font-semibold text-[hsl(var(--text-primary))] dark:text-white">Movimientos</h2>
                                <div className="flex items-center gap-2">
                                    <div className="relative">
                                        <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]" />
                                        <input
                                            type="text"
                                            value={search}
                                            onChange={e => setSearch(e.target.value)}
                                            placeholder="Buscar..."
                                            className="pl-8 pr-3 py-1.5 text-[12px] bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg outline-none focus:ring-2 focus:ring-blue-500/20 w-40"
                                        />
                                    </div>
                                    <div className="flex rounded-lg overflow-hidden border border-[hsl(var(--border))] dark:border-white/10 text-[11px] font-bold">
                                        {(['all', 'ingreso', 'egreso'] as const).map(f => (
                                            <button
                                                key={f}
                                                onClick={() => setFilter(f)}
                                                className={clsx(
                                                    'px-3 py-1.5 transition-colors',
                                                    filter === f
                                                        ? 'bg-[hsl(var(--primary))] text-white'
                                                        : 'text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] dark:hover:text-[hsl(var(--text-secondary))]'
                                                )}
                                            >
                                                {f === 'all' ? 'Todo' : f === 'ingreso' ? 'Ingresos' : 'Egresos'}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            </div>

                            {/* Rows */}
                            <div className="divide-y divide-[hsl(var(--border))] dark:divide-white/[0.03]">
                                {loading ? (
                                    <div className="flex items-center justify-center py-1.5">
                                        <Loader2 size={20} className="animate-spin text-[hsl(var(--text-secondary))]" />
                                    </div>
                                ) : filtered.length === 0 ? (
                                    <div className="py-1.5 text-center text-[hsl(var(--text-secondary))] text-sm">Sin movimientos registrados.</div>
                                ) : filtered.map((tx, idx) => {
                                    const Icon = CATEGORY_ICON[tx.category] ?? DEFAULT_ICON;
                                    const isIngreso = tx.type === 'ingreso';
                                    return (
                                        <motion.div
                                            key={tx.id}
                                            initial={{ opacity: 0 }}
                                            animate={{ opacity: 1 }}
                                            transition={{ delay: idx * 0.03 }}
                                            className="flex items-center gap-4 px-3 py-1.5 hover:bg-[hsl(var(--surface-1))]/50 dark:hover:bg-white/[0.02] transition-colors cursor-pointer"
                                        >
                                            <div className={clsx(
                                                'size-9 rounded-md flex items-center justify-center shrink-0',
                                                isIngreso ? 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600' : 'bg-rose-50 dark:bg-rose-900/20 text-rose-500'
                                            )}>
                                                <Icon size={15} />
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <p className="text-[13px] font-semibold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] truncate">{tx.description}</p>
                                                <p className="text-[11px] text-[hsl(var(--text-secondary))] font-medium">{tx.category} · {tx.date ? new Date(tx.date).toLocaleDateString('es-CO') : '—'}</p>
                                            </div>
                                            <span className={clsx(
                                                'text-sm font-semibold shrink-0 tabular-nums',
                                                isIngreso ? 'text-emerald-600' : 'text-rose-500'
                                            )}>
                                                {isIngreso ? '+' : '-'}{fmt(tx.amount)}
                                            </span>
                                        </motion.div>
                                    );
                                })}
                            </div>
                        </div>

                        {/* Right: Breakdown */}
                        <div className="space-y-4">
                            {/* Category breakdown */}
                            <div className="bg-[hsl(var(--bg-primary))] dark:bg-[#1a1b1e] rounded-lg border border-[hsl(var(--border))] dark:border-white/5 shadow-sm p-3">
                                <h3 className="font-semibold text-[hsl(var(--text-primary))] dark:text-white uppercase tracking-wide mb-5">Fuentes de Ingreso</h3>
                                <div className="space-y-4">
                                    {/* Categorías calculadas dinámicamente */}
                                    {(() => {
                                        const cats: Record<string, number> = {};
                                        transactions.forEach(t => { cats[t.category] = (cats[t.category] || 0) + t.amount; });
                                        const total = Object.values(cats).reduce((s, v) => s + v, 0) || 1;
                                        const COLORS = ['bg-[hsl(var(--primary))]', 'bg-[hsl(var(--primary))]', 'bg-[hsl(var(--primary))]', 'bg-emerald-500', 'bg-amber-500'];
                                        return Object.entries(cats).slice(0, 5).map(([label, amount], i) => {
                                            const pct = Math.round((amount / total) * 100);
                                            return (
                                                <div key={label}>
                                                    <div className="flex items-center justify-between mb-1.5">
                                                        <span className="text-[12px] font-semibold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">{label}</span>
                                                        <span className="font-semibold text-[hsl(var(--text-primary))] dark:text-white tabular-nums">{fmt(amount)}</span>
                                                    </div>
                                                    <div className="h-2 bg-[hsl(var(--surface-2))] dark:bg-white/5 rounded-full overflow-hidden">
                                                        <motion.div
                                                            initial={{ width: 0 }}
                                                            animate={{ width: `${pct}%` }}
                                                            transition={{ duration: 0.8, delay: 0.2 }}
                                                            className={clsx('h-full rounded-full', COLORS[i % COLORS.length])}
                                                        />
                                                    </div>
                                                    <p className="text-[10px] text-[hsl(var(--text-secondary))] mt-0.5 text-right font-bold">{pct}%</p>
                                                </div>
                                            );
                                        });
                                    })()}
                                </div>
                            </div>

                            {/* Transparency banner */}
                            <div className="bg-gradient-to-br from-[hsl(var(--bg-muted))] to-[hsl(var(--bg-muted))] rounded-lg p-3 text-white relative overflow-hidden">
                                <div className="absolute top-0 right-0 size-10 bg-blue-500/20 rounded-full blur-2xl" />
                                <Landmark size={24} className="text-[hsl(var(--primary))] mb-3 relative z-10" />
                                <h3 className="font-semibold relative z-10 mb-1">Informe de Transparencia</h3>
                                <p className="text-[11px] text-[hsl(var(--text-secondary))] relative z-10 mb-4 leading-relaxed">
                                    Reportes auditados disponibles para la congregación.
                                </p>
                                <button className="flex items-center gap-2 font-semibold text-[hsl(var(--primary))] hover:text-blue-300 transition-colors relative z-10">
                                    Ver informes <ChevronRight size={13} />
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        <div className="px-4 pb-2"><DashboardEmbed module="finance" label="Finanzas" /></div>
</WorkspaceLayout>
    );
}
