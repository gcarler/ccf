"use client";

import React, { useEffect, useState } from 'react';
import { 
    DollarSign, ArrowUpCircle, ArrowDownCircle, TrendingUp, Calendar, ChevronRight, PieChart, Filter
} from 'lucide-react';
import { api } from '@/services/apiService';
import { StatCard } from '@/components/StatCard';

export default function AdminTreasuryPage() {
    const [transactions, setTransactions] = useState<any[]>([]);
    const [funds, setFunds] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        Promise.all([
            api.get<any[]>('/finance/transactions'),
            api.get<any[]>('/finance/funds')
        ]).then(([txs, fnds]) => {
            setTransactions(txs);
            setFunds(fnds);
        }).catch(console.error)
        .finally(() => setLoading(false));
    }, []);

    const totalBalance = funds.reduce((acc, f) => acc + (f.current_balance || 0), 0);

    if (loading) return <div className="p-8 animate-pulse text-amber-500 font-black tracking-widest uppercase italic">Abriendo Libro Mayor...</div>;

    return (
        <div className="p-8 space-y-8 animate-in fade-in duration-700">
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
                <div className="space-y-2">
                    <div className="inline-flex items-center gap-2 px-3 py-1 bg-amber-500/10 text-amber-500 rounded-full text-[10px] font-black uppercase tracking-[0.2em] w-fit">
                        <DollarSign size={12} /> Gestion de Tesoreria
                    </div>
                    <h1 className="text-4xl font-black tracking-tighter text-white uppercase italic">
                        Libro <span className="text-amber-500">Contable</span>
                    </h1>
                    <p className="text-muted-foreground text-sm max-w-xl">
                        Control real de fondos e ingresos ministeriales. Datos sincronizados con la base de datos central.
                    </p>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <StatCard label="Saldo Total" value={`$${totalBalance.toLocaleString()}`} icon={TrendingUp} color="text-primary" bg="bg-primary/10" />
                <StatCard label="Fondos Activos" value={funds.length} icon={PieChart} color="text-emerald-500" bg="bg-emerald-500/10" />
                <StatCard label="Transacciones" value={transactions.length} icon={Calendar} color="text-blue-500" bg="bg-blue-500/10" />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                <div className="lg:col-span-2 bg-[#1e1f21] border border-white/5 rounded-[2.5rem] overflow-hidden">
                    <div className="p-6 border-b border-white/5 flex items-center justify-between">
                        <h3 className="text-xs font-black text-white uppercase tracking-widest">Movimientos Reales</h3>
                        <Filter size={18} className="text-muted-foreground" />
                    </div>
                    <div className="overflow-x-auto">
                        <table className="w-full text-left">
                            <tbody className="divide-y divide-white/5">
                                {transactions.map((tx, i) => (
                                    <tr key={i} className="group hover:bg-white/[0.02] transition-colors">
                                        <td className="px-6 py-5">
                                            <div className="text-sm font-bold text-white uppercase tracking-tight">
                                                {tx.person?.first_name ? `Ofrenda: ${tx.person.first_name}` : 'Entrada General'}
                                            </div>
                                            <div className="text-[10px] text-muted-foreground font-bold uppercase tracking-widest">ID: {tx.donation_id}</div>
                                        </td>
                                        <td className="px-6 py-5">
                                            <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                                <Calendar size={14} /> {new Date(tx.transaction_date).toLocaleDateString()}
                                            </div>
                                        </td>
                                        <td className="px-6 py-5 text-right font-black italic tracking-tighter text-emerald-500">
                                            + ${tx.amount.toLocaleString()}
                                        </td>
                                    </tr>
                                ))}
                                {transactions.length === 0 && (
                                    <tr>
                                        <td colSpan={3} className="py-12 text-center text-muted-foreground text-[10px] font-black uppercase tracking-widest">No hay transacciones registradas</td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>

                <div className="bg-[#1e1f21] border border-white/5 p-8 rounded-[2.5rem] space-y-8">
                    <h3 className="text-xs font-black text-white uppercase tracking-widest flex items-center gap-2">
                        <PieChart size={14} className="text-amber-500" /> Estados de Fondos
                    </h3>
                    <div className="space-y-6">
                        {funds.map((fund, i) => (
                            <div key={i} className="space-y-2">
                                <div className="flex justify-between text-[10px] font-black uppercase tracking-widest">
                                    <span className="text-white/60">{fund.name}</span>
                                    <span className="text-white">${fund.current_balance.toLocaleString()}</span>
                                </div>
                                <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
                                    <div className="h-full bg-amber-500" style={{ width: '100%' }} />
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}

