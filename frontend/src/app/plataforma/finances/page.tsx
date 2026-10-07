"use client";

import DashboardEmbed from '@/components/DashboardEmbed';
import WorkspaceLayout from '@/components/WorkspaceLayout';
import { useAuth } from '@/context/AuthContext';
import { DSCard } from '@/design';
import { DSChart } from '@/design';
import { DSMetric } from '@/design';
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
Receipt,
Search,
Zap,
} from 'lucide-react';
import React,{ useEffect,useMemo,useState,useCallback } from 'react';
import { toast } from 'sonner';
import ExpenseApprovalDrawer, { ExpenseReport } from '@/components/finance/ExpenseApprovalDrawer';

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
    const [viewMode, setViewMode] = useState<'transactions' | 'expenses'>('transactions');
    const [expenseReports, setExpenseReports] = useState<ExpenseReport[]>([]);
    const [selectedReport, setSelectedReport] = useState<ExpenseReport | null>(null);
    const [isExpenseDrawerOpen, setIsExpenseDrawerOpen] = useState(false);

    const loadExpenseReports = useCallback(async (signal?: AbortSignal) => {
        if (!token) return;
        try {
            const data = await apiFetch<ExpenseReport[]>('/finance-suite/expense-reports?limit=50', {
                token,
                cache: 'no-store',
                signal,
            });
            if (Array.isArray(data)) setExpenseReports(data);
        } catch (e: unknown) {
            if ((e as Error)?.name !== 'AbortError') console.error('Error fetching expense reports', e);
        }
    }, [token]);

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
            apiFetch<ExpenseReport[]>('/finance-suite/expense-reports?limit=50', { token, cache: 'no-store', signal: ctrl.signal }).catch(() => [] as ExpenseReport[]),
        ]).then(([txs, dbData, expReports]) => {
            if (Array.isArray(txs)) setTransactions(txs);
            if (dbData) setDashboard(dbData);
            if (Array.isArray(expReports)) setExpenseReports(expReports);
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
        <div className="h-full overflow-y-auto bg-[hsl(var(--bg-primary))] font-display scrollbar-thin">
            <div className="w-full px-4 py-3 space-y-3">

                {/* Header */}
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-lg font-bold text-[hsl(var(--text-primary))] tracking-tight uppercase">
                            Centro Financiero
                        </h1>
                        <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--primary))] mt-0.5">
                            Gestión de Recursos Ministeriales
                        </p>
                    </div>
                    <div className="flex items-center gap-2">
                        <div className="flex items-center gap-1 bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] rounded-md p-0.5 text-2xs font-semibold">
                            {(['Semana', 'Mes', 'Año']).map((p) => (
                                <button key={p} className={clsx(
                                    'px-2 py-1 rounded-md transition-colors',
                                    p === 'Mes' ? 'bg-[hsl(var(--primary))] text-[hsl(var(--text-inverse))] shadow-sm' : 'text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]'
                                )}>{p}</button>
                            ))}
                        </div>
                        <button className="flex items-center gap-1.5 px-2.5 py-1.5 bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] rounded-md text-2xs font-semibold text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] transition-all">
                            <Download size={12} /> Exportar
                        </button>
                        <button className="flex items-center gap-1.5 px-3 py-1.5 bg-[hsl(var(--primary))] text-[hsl(var(--text-inverse))] rounded-md text-2xs font-semibold shadow-sm active:scale-95 transition-all">
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
                                <h3 className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-3">Comparativa Mensual de Ingresos</h3>
                                <DSChart type="area" data={dashboard?.monthly_series} color="hsl(var(--success))" height={220} />
                            </DSCard>
                        </div>
                        <div>
                            <DSCard>
                                <h3 className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-3">Distribución por Categoría</h3>
                                <DSChart type="bar" data={dashboard?.income_by_category} color="hsl(var(--info))" height={220} />
                            </DSCard>
                        </div>
                    </div>

                    <div className="h-px bg-[hsl(var(--border))] my-8 relative z-10" />

                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-3 relative z-10">
                        {/* Transaction & Expenses List */}
                        <div className="lg:col-span-2 bg-[hsl(var(--surface-1))] rounded-lg border border-[hsl(var(--border))] shadow-sm overflow-hidden">
                            {/* Table header */}
                            <div className="px-3 py-2 border-b border-[hsl(var(--border))] flex items-center justify-between gap-4 flex-wrap">
                                <div className="flex items-center gap-4">
                                    <button
                                        onClick={() => setViewMode('transactions')}
                                        className={clsx(
                                            "text-xs font-bold pb-0.5 border-b-2 transition-all",
                                            viewMode === 'transactions'
                                                ? "border-[hsl(var(--primary))] text-[hsl(var(--text-primary))]"
                                                : "border-transparent text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]"
                                        )}
                                    >
                                        Movimientos
                                    </button>
                                    <button
                                        onClick={() => setViewMode('expenses')}
                                        className={clsx(
                                            "text-xs font-bold pb-0.5 border-b-2 transition-all flex items-center gap-1.5",
                                            viewMode === 'expenses'
                                                ? "border-[hsl(var(--primary))] text-[hsl(var(--text-primary))]"
                                                : "border-transparent text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]"
                                        )}
                                    >
                                        <Receipt size={13} />
                                        Gastos de Sede
                                        {expenseReports.length > 0 && (
                                            <span className="px-1.5 py-0.2 rounded-full bg-[hsl(var(--primary)/0.15)] text-[hsl(var(--primary))] text-3xs font-mono font-bold">
                                                {expenseReports.length}
                                            </span>
                                        )}
                                    </button>
                                </div>

                                {viewMode === 'transactions' ? (
                                    <div className="flex items-center gap-2">
                                        <div className="relative">
                                            <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]" />
                                            <input
                                                type="text"
                                                value={search}
                                                onChange={e => setSearch(e.target.value)}
                                                placeholder="Buscar..."
                                                className="pl-8 pr-3 py-1.5 text-xs bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded-lg text-[hsl(var(--text-primary))] outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]"
                                            />
                                        </div>
                                        <div className="flex rounded-lg overflow-hidden border border-[hsl(var(--border))] text-xs font-bold">
                                            {(['all', 'ingreso', 'egreso'] as const).map(f => (
                                                <button
                                                    key={f}
                                                    onClick={() => setFilter(f)}
                                                    className={clsx(
                                                        'px-2.5 py-1 transition-colors text-2xs',
                                                        filter === f
                                                            ? 'bg-[hsl(var(--primary))] text-[hsl(var(--text-inverse))]'
                                                            : 'text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]'
                                                    )}
                                                >
                                                    {f === 'all' ? 'Todo' : f === 'ingreso' ? 'Ingresos' : 'Egresos'}
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                ) : (
                                    <div className="text-2xs text-[hsl(var(--text-secondary))] font-medium">
                                        Circuito multinivel de autorización y desembolso
                                    </div>
                                )}
                            </div>

                            {/* Rows */}
                            <div className="divide-y divide-[hsl(var(--border))]">
                                {viewMode === 'transactions' ? (
                                    loading ? (
                                        <div className="flex items-center justify-center py-6">
                                            <Loader2 size={20} className="animate-spin text-[hsl(var(--text-secondary))]" />
                                        </div>
                                    ) : filtered.length === 0 ? (
                                        <div className="py-6 text-center text-[hsl(var(--text-secondary))] text-xs">Sin movimientos registrados.</div>
                                    ) : filtered.map((tx, idx) => {
                                        const Icon = CATEGORY_ICON[tx.category] ?? DEFAULT_ICON;
                                        const isIngreso = tx.type === 'ingreso';
                                        return (
                                            <motion.div
                                                key={tx.id}
                                                initial={{ opacity: 0 }}
                                                animate={{ opacity: 1 }}
                                                transition={{ delay: idx * 0.03 }}
                                                className="flex items-center gap-4 px-3 py-2 hover:bg-[hsl(var(--surface-2))] transition-colors cursor-pointer"
                                            >
                                                <div className={clsx(
                                                    'size-8 rounded-md flex items-center justify-center shrink-0',
                                                    isIngreso ? 'bg-[hsl(var(--success-muted))] text-[hsl(var(--success))]' : 'bg-[hsl(var(--destructive)/0.08)] text-[hsl(var(--destructive))]'
                                                )}>
                                                    <Icon size={14} />
                                                </div>
                                                <div className="flex-1 min-w-0">
                                                    <p className="text-xs font-semibold text-[hsl(var(--text-primary))] truncate">{tx.description}</p>
                                                    <p className="text-2xs text-[hsl(var(--text-secondary))] font-medium">{tx.category} · {tx.date ? new Date(tx.date).toLocaleDateString('es-CO') : '—'}</p>
                                                </div>
                                                <span className={clsx(
                                                    'text-xs font-semibold shrink-0 tabular-nums',
                                                    isIngreso ? 'text-[hsl(var(--success))]' : 'text-[hsl(var(--destructive))]'
                                                )}>
                                                    {isIngreso ? '+' : '-'}{fmt(tx.amount)}
                                                </span>
                                            </motion.div>
                                        );
                                    })
                                ) : (
                                    expenseReports.length === 0 ? (
                                        <div className="py-6 text-center text-[hsl(var(--text-secondary))] text-xs">
                                            No hay informes de gastos registrados en la sede.
                                        </div>
                                    ) : expenseReports.map((rep) => {
                                        const step = rep.approval_step || rep.status;
                                        const getBadge = () => {
                                            switch (step) {
                                                case 'draft':
                                                    return { label: 'Borrador', cls: 'bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))] border-[hsl(var(--border))]' };
                                                case 'pastor_review':
                                                    return { label: 'Revisión Pastoral', cls: 'bg-[hsl(var(--warning-muted))] text-[hsl(var(--warning))] border-[hsl(var(--warning)/0.3)]' };
                                                case 'central_authorization':
                                                    return { label: 'Autorización Central', cls: 'bg-[hsl(var(--info-muted))] text-[hsl(var(--info))] border-[hsl(var(--info)/0.3)]' };
                                                case 'approved':
                                                    return { label: 'Aprobado', cls: 'bg-[hsl(var(--primary)/0.15)] text-[hsl(var(--primary))] border-[hsl(var(--primary)/0.3)]' };
                                                case 'disbursed':
                                                    return { label: 'Desembolsado', cls: 'bg-[hsl(var(--success-muted))] text-[hsl(var(--success))] border-[hsl(var(--success)/0.3)]' };
                                                case 'rejected':
                                                    return { label: 'Rechazado', cls: 'bg-[hsl(var(--destructive)/0.1)] text-[hsl(var(--destructive))] border-[hsl(var(--destructive)/0.2)]' };
                                                default:
                                                    return { label: step, cls: 'bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))] border-[hsl(var(--border))]' };
                                            }
                                        };
                                        const badge = getBadge();
                                        return (
                                            <div
                                                key={rep.id}
                                                onClick={() => {
                                                    setSelectedReport(rep);
                                                    setIsExpenseDrawerOpen(true);
                                                }}
                                                className="flex items-center justify-between gap-3 px-3 py-2.5 hover:bg-[hsl(var(--surface-2))] transition-colors cursor-pointer"
                                            >
                                                <div className="min-w-0 flex-1">
                                                    <div className="flex items-center gap-2">
                                                        <p className="text-xs font-semibold text-[hsl(var(--text-primary))] truncate">{rep.description}</p>
                                                        <span className={clsx("px-2 py-0.5 rounded text-3xs font-bold border", badge.cls)}>
                                                            {badge.label}
                                                        </span>
                                                    </div>
                                                    <p className="text-2xs text-[hsl(var(--text-secondary))] mt-0.5">
                                                        Folio #{rep.id.slice(0, 8)} · {new Date(rep.created_at).toLocaleDateString('es-CO')}
                                                    </p>
                                                </div>
                                                <div className="text-right shrink-0">
                                                    <p className="text-xs font-mono font-bold text-[hsl(var(--primary))]">
                                                        ${Number(rep.total_amount).toLocaleString('es-CO')} {rep.currency}
                                                    </p>
                                                    <p className="text-3xs text-[hsl(var(--text-secondary))] font-medium">Ver trazabilidad &rarr;</p>
                                                </div>
                                            </div>
                                        );
                                    })
                                )}
                            </div>
                        </div>

                        {/* Right: Breakdown */}
                        <div className="space-y-4">
                            {/* Category breakdown */}
                            <div className="bg-[hsl(var(--surface-1))] rounded-lg border border-[hsl(var(--border))] shadow-sm p-3">
                                <h3 className="font-semibold text-[hsl(var(--text-primary))] uppercase tracking-wide mb-5">Fuentes de Ingreso</h3>
                                <div className="space-y-4">
                                    {/* Categorías calculadas dinámicamente */}
                                    {(() => {
                                        const cats: Record<string, number> = {};
                                        transactions.forEach(t => { cats[t.category] = (cats[t.category] || 0) + t.amount; });
                                        const total = Object.values(cats).reduce((s, v) => s + v, 0) || 1;
                                        const COLORS = ['bg-[hsl(var(--primary))]', 'bg-[hsl(var(--primary))]', 'bg-[hsl(var(--primary))]', 'bg-[hsl(var(--success))]', 'bg-[hsl(var(--warning))]'];
                                        return Object.entries(cats).slice(0, 5).map(([label, amount], i) => {
                                            const pct = Math.round((amount / total) * 100);
                                            return (
                                                <div key={label}>
                                                    <div className="flex items-center justify-between mb-1.5">
                                                        <span className="text-sm font-semibold text-[hsl(var(--text-primary))]">{label}</span>
                                                        <span className="font-semibold text-[hsl(var(--text-primary))] tabular-nums">{fmt(amount)}</span>
                                                    </div>
                                                    <div className="h-2 bg-[hsl(var(--surface-2))] rounded-full overflow-hidden">
                                                        <motion.div
                                                            initial={{ width: 0 }}
                                                            animate={{ width: `${pct}%` }}
                                                            transition={{ duration: 0.8, delay: 0.2 }}
                                                            className={clsx('h-full rounded-full', COLORS[i % COLORS.length])}
                                                        />
                                                    </div>
                                                    <p className="text-2xs text-[hsl(var(--text-secondary))] mt-0.5 text-right font-bold">{pct}%</p>
                                                </div>
                                            );
                                        });
                                    })()}
                                </div>
                            </div>

                            {/* Transparency banner */}
                            <div className="bg-gradient-to-br from-[hsl(var(--surface-2))] to-[hsl(var(--surface-1))] border border-[hsl(var(--border))] rounded-lg p-3 text-[hsl(var(--text-primary))] relative overflow-hidden">
                                <div className="absolute top-0 right-0 size-10 bg-[hsl(var(--primary))/0.2] rounded-full blur-2xl" />
                                <Landmark size={24} className="text-[hsl(var(--primary))] mb-3 relative z-10" />
                                <h3 className="font-semibold relative z-10 mb-1">Informe de Transparencia</h3>
                                <p className="text-xs text-[hsl(var(--text-secondary))] relative z-10 mb-4 leading-relaxed">
                                    Reportes auditados disponibles para la congregación.
                                </p>
                                <button className="flex items-center gap-2 font-semibold text-[hsl(var(--primary))] hover:text-[hsl(var(--primary)/0.7)] transition-colors relative z-10">
                                    Ver informes <ChevronRight size={13} />
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        <div className="px-4 pb-2"><DashboardEmbed module="finance" label="Finanzas" /></div>

        <ExpenseApprovalDrawer
            isOpen={isExpenseDrawerOpen}
            onClose={() => {
                setIsExpenseDrawerOpen(false);
                setSelectedReport(null);
            }}
            report={selectedReport}
            onUpdated={() => {
                loadExpenseReports();
            }}
        />
    </WorkspaceLayout>
    );
}
