"use client";

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { 
    ChevronLeft, 
    TrendingUp, 
    ArrowUpRight, 
    DollarSign, 
    Calendar, 
    Filter,
    Download,
    Search
} from 'lucide-react';
import { apiUrl } from '@/lib/api';
import { useAuth } from '@/context/AuthContext';

interface Donation {
    id: number;
    amount: number;
    currency: string;
    donor_name: string;
    donation_type: string;
    created_at: string;
}

export default function FinanceAdminPage() {
    const { token } = useAuth();
    const [donations, setDonations] = useState<Donation[]>([]);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchFinanceData = async () => {
            if (!token) return;
            try {
                const [donRes, totalRes] = await Promise.all([
                    fetch(apiUrl('/donations/'), { headers: { Authorization: `Bearer ${token}` } }),
                    fetch(apiUrl('/donations/total'), { headers: { Authorization: `Bearer ${token}` } })
                ]);
                
                if (donRes.ok) setDonations(await donRes.json());
                if (totalRes.ok) {
                    const t = await totalRes.json();
                    setTotal(t.total);
                }
            } catch (e) {
                console.error(e);
            } finally {
                setLoading(false);
            }
        };
        fetchFinanceData();
    }, [token]);

    return (
        <div className="space-y-6 animate-in fade-in duration-500 max-w-6xl mx-auto pb-24">
            <header className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
                <div>
                    <h1 className="flex items-center gap-3 text-3xl font-black text-slate-900 dark:text-white tracking-tight">
                        <DollarSign className="text-primary" size={32} /> Reportes Financieros
                    </h1>
                    <p className="text-slate-500 font-medium mt-1">Supervisa las ofrendas, diezmos y donaciones del ministerio.</p>
                </div>
                <button className="flex items-center gap-2 px-6 py-3 bg-white dark:bg-slate-800 text-slate-900 dark:text-white border border-slate-200 dark:border-white/10 rounded-2xl font-bold text-xs uppercase tracking-widest shadow-sm hover:shadow-md transition-all active:scale-95">
                    <Download size={16} /> Exportar CSV
                </button>
            </header>

            {/* KPI Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="glass dark:bg-slate-900/40 p-8 rounded-[2.5rem] border border-slate-200 dark:border-white/5 shadow-sm relative overflow-hidden group">
                    <div className="absolute top-0 right-0 w-32 h-32 bg-emerald-500/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2 transition-transform group-hover:scale-150"></div>
                    <div className="relative z-10">
                        <div className="flex items-center justify-between mb-4">
                            <span className="text-[10px] font-black uppercase tracking-widest text-slate-500">Total Ingresos Mes</span>
                            <div className="size-10 rounded-xl bg-emerald-500/10 text-emerald-500 flex items-center justify-center">
                                <TrendingUp size={18} />
                            </div>
                        </div>
                        <h3 className="text-4xl font-black text-slate-900 dark:text-white">${total.toFixed(2)}</h3>
                        <p className="text-xs text-emerald-500 font-bold mt-2 flex items-center gap-1"><ArrowUpRight size={12}/> +12% vs mes anterior</p>
                    </div>
                </div>

                <div className="glass dark:bg-slate-900/40 p-8 rounded-[2.5rem] border border-slate-200 dark:border-white/5 shadow-sm">
                    <div className="flex items-center justify-between mb-4">
                        <span className="text-[10px] font-black uppercase tracking-widest text-slate-500">Misiones</span>
                        <div className="size-10 rounded-xl bg-purple-500/10 text-purple-500 flex items-center justify-center">
                            <Globe size={18} />
                        </div>
                    </div>
                    <h3 className="text-4xl font-black text-slate-900 dark:text-white">$0.00</h3>
                    <p className="text-xs text-slate-400 font-bold mt-2">Objetivo: $5,000</p>
                </div>

                <div className="glass dark:bg-slate-900/40 p-8 rounded-[2.5rem] border border-slate-200 dark:border-white/5 shadow-sm">
                    <div className="flex items-center justify-between mb-4">
                        <span className="text-[10px] font-black uppercase tracking-widest text-slate-500">Transacciones</span>
                        <div className="size-10 rounded-xl bg-blue-500/10 text-blue-500 flex items-center justify-center">
                            <CreditCard size={18} />
                        </div>
                    </div>
                    <h3 className="text-4xl font-black text-slate-900 dark:text-white">{donations.length}</h3>
                    <p className="text-xs text-slate-400 font-bold mt-2">En los últimos 30 días</p>
                </div>
            </div>

            {/* Transactions Table */}
            <div className="bg-white dark:bg-slate-900/40 rounded-[2.5rem] border border-slate-200 dark:border-white/5 shadow-xl overflow-hidden mt-8">
                <div className="p-6 border-b border-slate-200 dark:border-white/5 flex flex-col md:flex-row gap-4 justify-between items-center bg-slate-50/50 dark:bg-transparent">
                    <div className="relative w-full md:max-w-md">
                        <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                        <input 
                            type="text" 
                            placeholder="Buscar por donante..." 
                            className="w-full pl-12 pr-4 py-3 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl text-sm focus:ring-2 focus:ring-primary transition-all font-medium shadow-sm"
                        />
                    </div>
                    <button className="flex items-center gap-2 px-4 py-3 bg-slate-100 dark:bg-white/5 rounded-xl text-xs font-bold text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-white/10 transition-colors w-full md:w-auto justify-center">
                        <Filter size={16} /> Filtrar
                    </button>
                </div>

                <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                        <thead>
                            <tr className="bg-slate-50/50 dark:bg-white/5 text-[10px] font-black uppercase tracking-widest text-slate-500">
                                <th className="p-6">Donante</th>
                                <th className="p-6">Tipo</th>
                                <th className="p-6">Monto</th>
                                <th className="p-6">Fecha</th>
                                <th className="p-6">Estado</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 dark:divide-white/5">
                            {donations.length > 0 ? donations.map(d => (
                                <tr key={d.id} className="hover:bg-slate-50 dark:hover:bg-white/5 transition-colors group">
                                    <td className="p-6 font-bold text-slate-900 dark:text-white flex items-center gap-3">
                                        <div className="size-8 rounded-full bg-primary/10 flex items-center justify-center text-primary text-xs">{d.donor_name ? d.donor_name.charAt(0).toUpperCase() : 'A'}</div>
                                        {d.donor_name || 'Anónimo'}
                                    </td>
                                    <td className="p-6 text-sm text-slate-600 dark:text-slate-400">{d.donation_type}</td>
                                    <td className="p-6 font-black text-slate-900 dark:text-white">${d.amount.toFixed(2)} <span className="text-[10px] text-slate-500 font-bold">{d.currency}</span></td>
                                    <td className="p-6 text-xs text-slate-500 font-medium flex items-center gap-2">
                                        <Calendar size={14} /> {new Date(d.created_at).toLocaleDateString()}
                                    </td>
                                    <td className="p-6">
                                        <span className="px-3 py-1 bg-emerald-500/10 text-emerald-500 text-[10px] font-black uppercase tracking-widest rounded-lg border border-emerald-500/20">
                                            {d.status}
                                        </span>
                                    </td>
                                </tr>
                            )) : (
                                <tr>
                                    <td colSpan={5} className="p-16 text-center text-slate-500 font-medium italic">No se han registrado ofrendas aún.</td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}

import { Globe, CreditCard as CreditCardIcon } from 'lucide-react';