"use client";

import React, { useState, useEffect, useMemo } from 'react';
import {
    TrendingUp, TrendingDown, BarChart3, PiggyBank,
    Download, Plus,
    Search, ChevronRight, Landmark,
    Gift, HeartHandshake, Zap,
    Wallet, CircleDollarSign, Loader2
} from 'lucide-react';
import { motion } from 'framer-motion';
import clsx from 'clsx';
import WorkspaceLayout from '@/components/WorkspaceLayout';
import { DSMetric } from '@/design/components/DSMetric';
import { DSChart } from '@/design/components/DSChart';
import { DSCard } from '@/design/components/DSCard';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';

// ─── Helpers ───────────────────────────────────────────────────────────────────
// ─── Tipo local ───────────────────────────────────────────────────────────────
interface TxRecord {
    id: number;
    type: 'ingreso' | 'egreso';
    category: string;
    description: string;
    amount: number;
    date: string | null;
}

interface FundsData {
    ingresos_mes: number;
    egresos_mes: number;
    balance: number;
    reserva: number;
    total_historico: number;
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

function StatCard({ label, value, sub, icon: Icon, colorClass, trend }: any) {
    return (
        <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            className="relative p-3 rounded-lg bg-white dark:bg-[#1e2025] border border-slate-100 dark:border-white/[0.06] shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 overflow-hidden group"
        >
            <div className={`absolute -top-4 -right-4 size-8 rounded-full blur-2xl opacity-30 group-hover:opacity-50 transition-opacity ${colorClass.split(' ')[0]}`} />
            <div className={clsx('inline-flex items-center justify-center size-10 rounded-md mb-4 relative z-10', colorClass)}>
                <Icon size={18} className="text-current" />
            </div>
            <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 dark:text-slate-500 mb-1 relative z-10">{label}</p>
            <h3 className="text-xl font-bold text-slate-900 dark:text-white tracking-tight leading-none relative z-10">{value}</h3>
            {sub && (
                <p className={clsx('text-[11px] font-bold mt-2.5 flex items-center gap-1 relative z-10', trend === 'up' ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-500')}>
                    {trend === 'up' ? <TrendingUp size={11} /> : <TrendingDown size={11} />}
                    {sub}
                </p>
            )}
        </motion.div>
    );
}

export default function FinancesPage() {
    const { token } = useAuth();
    const [filter, setFilter] = useState<'all' | 'ingreso' | 'egreso'>('all');
    const [search, setSearch] = useState('');
    const [transactions, setTransactions] = useState<TxRecord[]>([]);
    const [dashboard, setDashboard] = useState<any>(null);
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
        if (!token) { setLoading(false); return; }
        Promise.all([
            apiFetch<TxRecord[]>('/finance/transactions?limit=50', { token, cache: 'no-store' }),
            apiFetch<any>('/dashboard/finance', { token, cache: 'no-store' }),
        ]).then(([txs, dbData]) => {
            if (Array.isArray(txs)) setTransactions(txs);
            if (dbData) setDashboard(dbData);
        }).catch(console.error).finally(() => setLoading(false));
    }, [token]);

    const summary = dashboard?.funds ?? {
        ingresos_mes: 0, egresos_mes: 0, balance: 0, reserva: 0, total_historico: 0
    };

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
                        <h1 className="text-lg font-bold text-slate-900 dark:text-white tracking-tight uppercase">
                            Centro Financiero
                        </h1>
                        <p className="text-[10px] font-semibold uppercase tracking-wide text-blue-600 mt-0.5">
                            Gestión de Recursos Ministeriales
                        </p>
                    </div>
                    <div className="flex items-center gap-2">
                        <div className="flex items-center gap-1 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-md p-0.5 text-[10px] font-semibold">
                            {(['Semana', 'Mes', 'Año']).map((p) => (
                                <button key={p} className={clsx(
                                    'px-2 py-1 rounded-md transition-colors',
                                    p === 'Mes' ? 'bg-blue-600 text-white shadow-sm' : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-200'
                                )}>{p}</button>
                            ))}
                        </div>
                        <button className="flex items-center gap-1.5 px-2.5 py-1.5 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-md text-[10px] font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-white/10 transition-all">
                            <Download size={12} /> Exportar
                        </button>
                        <button className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 text-white rounded-md text-[10px] font-semibold shadow-sm hover:bg-blue-700 active:scale-95 transition-all">
                            <Plus size={12} /> Registro
                        </button>
                    </div>
                </div>

                    {/* 📊 Financial Metrics */}
                    <section className="grid grid-cols-1 md:grid-cols-4 gap-4 relative z-10">
                        {dashboard?.cards.map((card: any, idx: number) => (
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
                                <h3 className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 mb-3">Comparativa Mensual de Ingresos</h3>
                                <DSChart type="area" data={dashboard?.monthly_comparison} color="#10b981" height={220} />
                            </DSCard>
                        </div>
                        <div>
                            <DSCard>
                                <h3 className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 mb-3">Distribución por Categoría</h3>
                                <DSChart type="bar" data={dashboard?.income_by_category} color="#3b82f6" height={220} />
                            </DSCard>
                        </div>
                    </div>

                    <div className="h-px bg-white/5 my-8 relative z-10" />

                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-3 relative z-10">
                        {/* Transaction List */}
                        <div className="lg:col-span-2 bg-white dark:bg-[#1a1b1e] rounded-lg border border-slate-100 dark:border-white/5 shadow-sm overflow-hidden">
                            {/* Table header */}
                            <div className="px-3 py-1.5 border-b border-slate-100 dark:border-white/5 flex items-center justify-between gap-4">
                                <h2 className="font-semibold text-slate-800 dark:text-white">Movimientos</h2>
                                <div className="flex items-center gap-2">
                                    <div className="relative">
                                        <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                                        <input
                                            type="text"
                                            value={search}
                                            onChange={e => setSearch(e.target.value)}
                                            placeholder="Buscar..."
                                            className="pl-8 pr-3 py-1.5 text-[12px] bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg outline-none focus:ring-2 focus:ring-blue-500/20 w-40"
                                        />
                                    </div>
                                    <div className="flex rounded-lg overflow-hidden border border-slate-200 dark:border-white/10 text-[11px] font-bold">
                                        {(['all', 'ingreso', 'egreso'] as const).map(f => (
                                            <button
                                                key={f}
                                                onClick={() => setFilter(f)}
                                                className={clsx(
                                                    'px-3 py-1.5 transition-colors',
                                                    filter === f
                                                        ? 'bg-blue-600 text-white'
                                                        : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
                                                )}
                                            >
                                                {f === 'all' ? 'Todo' : f === 'ingreso' ? 'Ingresos' : 'Egresos'}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            </div>

                            {/* Rows */}
                            <div className="divide-y divide-slate-50 dark:divide-white/[0.03]">
                                {loading ? (
                                    <div className="flex items-center justify-center py-1.5">
                                        <Loader2 size={20} className="animate-spin text-slate-400" />
                                    </div>
                                ) : filtered.length === 0 ? (
                                    <div className="py-1.5 text-center text-slate-400 text-sm">Sin movimientos registrados.</div>
                                ) : filtered.map((tx, idx) => {
                                    const Icon = CATEGORY_ICON[tx.category] ?? DEFAULT_ICON;
                                    const isIngreso = tx.type === 'ingreso';
                                    return (
                                        <motion.div
                                            key={tx.id}
                                            initial={{ opacity: 0 }}
                                            animate={{ opacity: 1 }}
                                            transition={{ delay: idx * 0.03 }}
                                            className="flex items-center gap-4 px-3 py-1.5 hover:bg-slate-50/50 dark:hover:bg-white/[0.02] transition-colors cursor-pointer"
                                        >
                                            <div className={clsx(
                                                'size-9 rounded-md flex items-center justify-center shrink-0',
                                                isIngreso ? 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600' : 'bg-rose-50 dark:bg-rose-900/20 text-rose-500'
                                            )}>
                                                <Icon size={15} />
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <p className="text-[13px] font-semibold text-slate-800 dark:text-slate-200 truncate">{tx.description}</p>
                                                <p className="text-[11px] text-slate-400 font-medium">{tx.category} · {tx.date ? new Date(tx.date).toLocaleDateString('es-CO') : '—'}</p>
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
                            <div className="bg-white dark:bg-[#1a1b1e] rounded-lg border border-slate-100 dark:border-white/5 shadow-sm p-3">
                                <h3 className="font-semibold text-slate-800 dark:text-white uppercase tracking-wide mb-5">Fuentes de Ingreso</h3>
                                <div className="space-y-4">
                                    {/* Categorías calculadas dinámicamente */}
                                    {(() => {
                                        const cats: Record<string, number> = {};
                                        transactions.forEach(t => { cats[t.category] = (cats[t.category] || 0) + t.amount; });
                                        const total = Object.values(cats).reduce((s, v) => s + v, 0) || 1;
                                        const COLORS = ['bg-blue-500', 'bg-indigo-500', 'bg-blue-500', 'bg-emerald-500', 'bg-amber-500'];
                                        return Object.entries(cats).slice(0, 5).map(([label, amount], i) => {
                                            const pct = Math.round((amount / total) * 100);
                                            return (
                                                <div key={label}>
                                                    <div className="flex items-center justify-between mb-1.5">
                                                        <span className="text-[12px] font-semibold text-slate-700 dark:text-slate-300">{label}</span>
                                                        <span className="font-semibold text-slate-800 dark:text-white tabular-nums">{fmt(amount)}</span>
                                                    </div>
                                                    <div className="h-2 bg-slate-100 dark:bg-white/5 rounded-full overflow-hidden">
                                                        <motion.div
                                                            initial={{ width: 0 }}
                                                            animate={{ width: `${pct}%` }}
                                                            transition={{ duration: 0.8, delay: 0.2 }}
                                                            className={clsx('h-full rounded-full', COLORS[i % COLORS.length])}
                                                        />
                                                    </div>
                                                    <p className="text-[10px] text-slate-400 mt-0.5 text-right font-bold">{pct}%</p>
                                                </div>
                                            );
                                        });
                                    })()}
                                </div>
                            </div>

                            {/* Transparency banner */}
                            <div className="bg-gradient-to-br from-slate-900 to-slate-800 rounded-lg p-3 text-white relative overflow-hidden">
                                <div className="absolute top-0 right-0 size-10 bg-blue-500/20 rounded-full blur-2xl" />
                                <Landmark size={24} className="text-blue-400 mb-3 relative z-10" />
                                <h3 className="font-semibold relative z-10 mb-1">Informe de Transparencia</h3>
                                <p className="text-[11px] text-slate-400 relative z-10 mb-4 leading-relaxed">
                                    Reportes auditados disponibles para la congregación.
                                </p>
                                <button className="flex items-center gap-2 font-semibold text-blue-400 hover:text-blue-300 transition-colors relative z-10">
                                    Ver informes <ChevronRight size={13} />
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </WorkspaceLayout>
    );
}

