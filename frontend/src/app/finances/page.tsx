"use client";

import React, { useState, useEffect, useMemo } from 'react';
import {
    DollarSign, TrendingUp, TrendingDown, BarChart3, PiggyBank,
    ArrowUpRight, ArrowDownLeft, Filter, Download, Plus,
    Calendar, Search, ChevronRight, Landmark, ShoppingCart,
    Gift, HeartHandshake, BookOpen, Zap, MoreHorizontal,
    CreditCard, Wallet, CircleDollarSign, AlertCircle, Loader2
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import WorkspaceLayout from '@/components/WorkspaceLayout';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';

// ─── Helpers ───────────────────────────────────────────────────────────────────
function daysAgo(n: number) {
    const d = new Date();
    d.setDate(d.getDate() - n);
    return d.toISOString().slice(0, 10);
}

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
            className="relative p-5 rounded-2xl bg-white dark:bg-[#1e2025] border border-slate-100 dark:border-white/[0.06] shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 overflow-hidden group"
        >
            <div className={`absolute -top-4 -right-4 size-20 rounded-full blur-2xl opacity-30 group-hover:opacity-50 transition-opacity ${colorClass.split(' ')[0]}`} />
            <div className={clsx('inline-flex items-center justify-center size-10 rounded-xl mb-4 relative z-10', colorClass)}>
                <Icon size={18} className="text-current" />
            </div>
            <p className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400 dark:text-slate-500 mb-1 relative z-10">{label}</p>
            <h3 className="text-xl font-black text-slate-900 dark:text-white tracking-tight leading-none relative z-10">{value}</h3>
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
    const [funds, setFunds] = useState<FundsData | null>(null);
    const [loading, setLoading] = useState(true);

    const FINANCE_SECTIONS = useMemo(() => ([
        {
            title: 'Reportes',
            items: [
                { id: 'finances', label: 'Resumen', href: '/finances', icon: BarChart3 },
                { id: 'transparency', label: 'Transparencia', href: '/finances/transparency', icon: Landmark },
            ],
        },
    ]), []);

    useEffect(() => {
        if (!token) { setLoading(false); return; }
        Promise.all([
            apiFetch<TxRecord[]>('/finance/transactions?limit=50', { token, cache: 'no-store' }),
            apiFetch<FundsData>('/finance/funds', { token, cache: 'no-store' }),
        ]).then(([txs, f]) => {
            if (Array.isArray(txs)) setTransactions(txs);
            if (f && typeof f.ingresos_mes === 'number') setFunds(f);
        }).catch(console.error).finally(() => setLoading(false));
    }, [token]);

    const summary = funds ?? {
        ingresos_mes: 0, egresos_mes: 0, balance: 0, reserva: 0, total_historico: 0
    };

    const filtered = useMemo(() => transactions.filter(t => {
        if (filter !== 'all' && t.type !== filter) return false;
        if (search && !t.description.toLowerCase().includes(search.toLowerCase())) return false;
        return true;
    }), [transactions, filter, search]);


    return (
        <WorkspaceLayout
            sidebarTitle="Finanzas"
            sidebarSections={FINANCE_SECTIONS}
        >
            <div className="h-full overflow-y-auto bg-slate-50/40 dark:bg-[#111213] font-display scrollbar-thin">
                <div className="max-w-7xl mx-auto px-6 py-6 space-y-6">

                    {/* Header — Premium */}
                    <div className="flex items-center justify-between">
                        <div>
                            <h1 className="text-[22px] font-bold text-slate-900 dark:text-white tracking-tight">
                                Panel Financiero
                            </h1>
                            <p className="text-[12px] text-slate-400 mt-0.5 font-medium">
                                Visibilidad completa de los recursos de la comunidad
                            </p>
                        </div>
                        <div className="flex items-center gap-2">
                            <div className="flex items-center gap-1 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl p-1 text-[11px] font-bold">
                                {(['Semana', 'Mes', 'Año']).map((p) => (
                                    <button key={p} className={clsx(
                                        'px-3 py-1.5 rounded-lg transition-colors',
                                        p === 'Mes' ? 'bg-blue-600 text-white shadow-sm' : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-200'
                                    )}>{p}</button>
                                ))}
                            </div>
                            <button className="flex items-center gap-2 px-3 py-2 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl text-[11px] font-bold text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-white/10 transition-all">
                                <Download size={13} /> Exportar
                            </button>
                            <button className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-xl text-[11px] font-bold shadow-lg shadow-blue-500/20 hover:bg-blue-700 active:scale-95 transition-all">
                                <Plus size={13} /> Registro
                            </button>
                        </div>
                    </div>

                    {/* Stats Grid */}
                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                        <StatCard label="Ingresos Mes"  value={loading ? '...' : fmt(summary.ingresos_mes)} sub="Mes en curso" trend="up"   icon={TrendingUp}   colorClass="bg-emerald-100 dark:bg-emerald-500/10 text-emerald-600" />
                        <StatCard label="Egresos Est."  value={loading ? '...' : fmt(summary.egresos_mes)}  sub="Estimado"       trend="down" icon={TrendingDown}  colorClass="bg-rose-100 dark:bg-rose-500/10 text-rose-500" />
                        <StatCard label="Balance Neto"  value={loading ? '...' : fmt(summary.balance)}      sub="Saldo disponible" trend="up" icon={Wallet}        colorClass="bg-blue-100 dark:bg-blue-500/10 text-blue-600" />
                        <StatCard label="Fondo Reserva" value={loading ? '...' : fmt(summary.reserva)}      sub="10% histórico"              icon={PiggyBank}     colorClass="bg-violet-100 dark:bg-violet-500/10 text-violet-600" />
                    </div>

                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                        {/* Transaction List */}
                        <div className="lg:col-span-2 bg-white dark:bg-[#1a1b1e] rounded-2xl border border-slate-100 dark:border-white/5 shadow-sm overflow-hidden">
                            {/* Table header */}
                            <div className="px-6 py-4 border-b border-slate-100 dark:border-white/5 flex items-center justify-between gap-4">
                                <h2 className="text-[13px] font-black text-slate-800 dark:text-white">Movimientos</h2>
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
                                    <div className="flex items-center justify-center py-12">
                                        <Loader2 size={20} className="animate-spin text-slate-400" />
                                    </div>
                                ) : filtered.length === 0 ? (
                                    <div className="py-12 text-center text-slate-400 text-sm">Sin movimientos registrados.</div>
                                ) : filtered.map((tx, idx) => {
                                    const Icon = CATEGORY_ICON[tx.category] ?? DEFAULT_ICON;
                                    const isIngreso = tx.type === 'ingreso';
                                    return (
                                        <motion.div
                                            key={tx.id}
                                            initial={{ opacity: 0 }}
                                            animate={{ opacity: 1 }}
                                            transition={{ delay: idx * 0.03 }}
                                            className="flex items-center gap-4 px-6 py-3.5 hover:bg-slate-50/50 dark:hover:bg-white/[0.02] transition-colors cursor-pointer"
                                        >
                                            <div className={clsx(
                                                'size-9 rounded-xl flex items-center justify-center shrink-0',
                                                isIngreso ? 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600' : 'bg-rose-50 dark:bg-rose-900/20 text-rose-500'
                                            )}>
                                                <Icon size={15} />
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <p className="text-[13px] font-semibold text-slate-800 dark:text-slate-200 truncate">{tx.description}</p>
                                                <p className="text-[11px] text-slate-400 font-medium">{tx.category} · {tx.date ? new Date(tx.date).toLocaleDateString('es-CO') : '—'}</p>
                                            </div>
                                            <span className={clsx(
                                                'text-[14px] font-black shrink-0 tabular-nums',
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
                            <div className="bg-white dark:bg-[#1a1b1e] rounded-2xl border border-slate-100 dark:border-white/5 shadow-sm p-6">
                                <h3 className="text-[12px] font-black text-slate-800 dark:text-white uppercase tracking-widest mb-5">Fuentes de Ingreso</h3>
                                <div className="space-y-4">
                                    {/* Categorías calculadas dinámicamente */}
                                    {(() => {
                                        const cats: Record<string, number> = {};
                                        transactions.forEach(t => { cats[t.category] = (cats[t.category] || 0) + t.amount; });
                                        const total = Object.values(cats).reduce((s, v) => s + v, 0) || 1;
                                        const COLORS = ['bg-blue-500', 'bg-indigo-500', 'bg-violet-500', 'bg-emerald-500', 'bg-amber-500'];
                                        return Object.entries(cats).slice(0, 5).map(([label, amount], i) => {
                                            const pct = Math.round((amount / total) * 100);
                                            return (
                                                <div key={label}>
                                                    <div className="flex items-center justify-between mb-1.5">
                                                        <span className="text-[12px] font-semibold text-slate-700 dark:text-slate-300">{label}</span>
                                                        <span className="text-[12px] font-black text-slate-800 dark:text-white tabular-nums">{fmt(amount)}</span>
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
                            <div className="bg-gradient-to-br from-slate-900 to-slate-800 rounded-2xl p-6 text-white relative overflow-hidden">
                                <div className="absolute top-0 right-0 size-24 bg-blue-500/20 rounded-full blur-2xl" />
                                <Landmark size={24} className="text-blue-400 mb-3 relative z-10" />
                                <h3 className="text-[13px] font-black relative z-10 mb-1">Informe de Transparencia</h3>
                                <p className="text-[11px] text-slate-400 relative z-10 mb-4 leading-relaxed">
                                    Reportes auditados disponibles para la congregación.
                                </p>
                                <button className="flex items-center gap-2 text-[11px] font-black text-blue-400 hover:text-blue-300 transition-colors relative z-10">
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

