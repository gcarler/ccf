"use client";

import React, { useState, useEffect } from 'react';
import {
    DollarSign, TrendingUp, TrendingDown, BarChart3, PiggyBank,
    ArrowUpRight, ArrowDownLeft, Filter, Download, Plus,
    Calendar, Search, ChevronRight, Landmark, ShoppingCart,
    Gift, HeartHandshake, BookOpen, Zap, MoreHorizontal,
    CreditCard, Wallet, CircleDollarSign, AlertCircle
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import WorkspaceLayout from '@/components/WorkspaceLayout';

// ─── Mock data ─────────────────────────────────────────────────────────────────
const SUMMARY = {
    ingresos: 48_250_000,
    egresos:  31_840_000,
    balance:  16_410_000,
    reserva:  8_200_000,
};

const TRANSACTIONS = [
    { id: 1,  type: 'ingreso', category: 'Diezmos',      description: 'Ofrenda dominical — Sede Norte',    amount: 4_200_000, date: '2026-04-06', icon: HeartHandshake, color: 'emerald' },
    { id: 2,  type: 'egreso',  category: 'Operacional',  description: 'Pago arriendo sede principal',        amount: 5_800_000, date: '2026-04-05', icon: Landmark,       color: 'rose' },
    { id: 3,  type: 'ingreso', category: 'Ofrendas',     description: 'Ofrenda especial — Misiones',         amount: 1_540_000, date: '2026-04-05', icon: Gift,           color: 'emerald' },
    { id: 4,  type: 'egreso',  category: 'Ministerio',   description: 'Material didáctico Academia Digital', amount: 820_000,   date: '2026-04-04', icon: BookOpen,       color: 'rose' },
    { id: 5,  type: 'ingreso', category: 'Donaciones',   description: 'Donación corporativa anónima',        amount: 10_000_000,date: '2026-04-03', icon: HeartHandshake, color: 'emerald' },
    { id: 6,  type: 'egreso',  category: 'Tecnología',   description: 'Suscripción servicios digitales',     amount: 450_000,   date: '2026-04-02', icon: Zap,            color: 'rose' },
    { id: 7,  type: 'ingreso', category: 'Diezmos',      description: 'Ofrenda dominical — Sede Sur',        amount: 3_800_000, date: '2026-04-01', icon: HeartHandshake, color: 'emerald' },
    { id: 8,  type: 'egreso',  category: 'Salarios',     description: 'Liquidación staff pastoral',           amount: 18_000_000,date: '2026-03-31', icon: CreditCard,     color: 'rose' },
];

const CATEGORIES = [
    { label: 'Diezmos',    percent: 42, color: 'bg-blue-500',    amount: 20_250_000 },
    { label: 'Ofrendas',   percent: 22, color: 'bg-indigo-500',  amount: 10_615_000 },
    { label: 'Donaciones', percent: 36, color: 'bg-violet-500',  amount: 17_385_000 },
];

const FINANCE_SECTIONS = [
    {
        title: 'Reportes',
        items: [
            { id: 'finances', label: 'Resumen', href: '/finances', icon: BarChart3 },
            { id: 'transparency', label: 'Transparencia', href: '/finances/transparency', icon: Landmark },
        ],
    },
];

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
    const [filter, setFilter] = useState<'all' | 'ingreso' | 'egreso'>('all');
    const [search, setSearch] = useState('');

    const filtered = TRANSACTIONS.filter(t => {
        if (filter !== 'all' && t.type !== filter) return false;
        if (search && !t.description.toLowerCase().includes(search.toLowerCase())) return false;
        return true;
    });

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
                        <StatCard label="Ingresos Mes"  value={fmt(SUMMARY.ingresos)} sub="+8.2% vs mes anterior" trend="up"   icon={TrendingUp}   colorClass="bg-emerald-100 dark:bg-emerald-500/10 text-emerald-600" />
                        <StatCard label="Egresos Mes"   value={fmt(SUMMARY.egresos)}  sub="-3.1% vs mes anterior" trend="down" icon={TrendingDown}  colorClass="bg-rose-100 dark:bg-rose-500/10 text-rose-500" />
                        <StatCard label="Balance Neto"  value={fmt(SUMMARY.balance)}  sub="Saldo disponible"      trend="up"   icon={Wallet}        colorClass="bg-blue-100 dark:bg-blue-500/10 text-blue-600" />
                        <StatCard label="Fondo Reserva" value={fmt(SUMMARY.reserva)}  sub="17% del balance"                   icon={PiggyBank}     colorClass="bg-violet-100 dark:bg-violet-500/10 text-violet-600" />
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
                                {filtered.map((tx, idx) => {
                                    const Icon = tx.icon;
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
                                                tx.color === 'emerald' ? 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600' : 'bg-rose-50 dark:bg-rose-900/20 text-rose-500'
                                            )}>
                                                <Icon size={15} />
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <p className="text-[13px] font-semibold text-slate-800 dark:text-slate-200 truncate">{tx.description}</p>
                                                <p className="text-[11px] text-slate-400 font-medium">{tx.category} · {tx.date}</p>
                                            </div>
                                            <span className={clsx(
                                                'text-[14px] font-black shrink-0 tabular-nums',
                                                tx.type === 'ingreso' ? 'text-emerald-600' : 'text-rose-500'
                                            )}>
                                                {tx.type === 'ingreso' ? '+' : '-'}{fmt(tx.amount)}
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
                                    {CATEGORIES.map(cat => (
                                        <div key={cat.label}>
                                            <div className="flex items-center justify-between mb-1.5">
                                                <span className="text-[12px] font-semibold text-slate-700 dark:text-slate-300">{cat.label}</span>
                                                <span className="text-[12px] font-black text-slate-800 dark:text-white tabular-nums">{fmt(cat.amount)}</span>
                                            </div>
                                            <div className="h-2 bg-slate-100 dark:bg-white/5 rounded-full overflow-hidden">
                                                <motion.div
                                                    initial={{ width: 0 }}
                                                    animate={{ width: `${cat.percent}%` }}
                                                    transition={{ duration: 0.8, delay: 0.2 }}
                                                    className={clsx('h-full rounded-full', cat.color)}
                                                />
                                            </div>
                                            <p className="text-[10px] text-slate-400 mt-0.5 text-right font-bold">{cat.percent}%</p>
                                        </div>
                                    ))}
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
