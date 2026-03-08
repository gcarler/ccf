"use client";

import React from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { apiUrl } from '@/lib/api';
import {
    ArrowLeft,
    Bell,
    TrendingUp,
    PieChart,
    DollarSign,
    ArrowUpRight,
    MoreVertical
} from 'lucide-react';

export default function FinancialReports() {
    const { isAuthenticated, token } = useAuth();
    const router = useRouter();
    const [analytics, setAnalytics] = React.useState<any>(null);
    const [loading, setLoading] = React.useState(true);

    React.useEffect(() => {
        const fetchAnalytics = async () => {
            if (!token) return;
            try {
                const res = await fetch(apiUrl('/analytics/events/summary'), {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                if (res.ok) setAnalytics(await res.json());
            } catch (e) {
                console.error("Analytics fetch failed", e);
            } finally {
                setLoading(false);
            }
        };
        fetchAnalytics();
    }, [token]);

    const transactions = [
        { id: '1', name: 'Ricardo Mendez', category: 'Diezmos', amount: 450.00, status: 'Completado', avatar: 'https://i.pravatar.cc/150?u=10' },
        { id: '2', name: 'Elena Rodriguez', category: 'Misiones', amount: 120.00, status: 'Completado', avatar: 'https://i.pravatar.cc/150?u=11' },
        { id: '3', name: 'Marcos Lopez', category: 'Construcción', amount: 1200.00, status: 'Completado', avatar: 'https://i.pravatar.cc/150?u=12' },
        { id: '4', name: 'Ana Victoria', category: 'Ofrendas', amount: 50.00, status: 'Completado', avatar: 'https://i.pravatar.cc/150?u=13' },
    ];

    if (!isAuthenticated) return null;

    return (
        <div className="flex flex-col h-full bg-slate-950/20 font-display">
            {/* Header Area */}
            <div className="px-8 pt-10 pb-6 flex items-center justify-between">
                <button onClick={() => router.back()} className="p-3 rounded-2xl bg-white/5 border border-white/10 text-slate-400 hover:text-white transition-all">
                    <ArrowLeft size={20} />
                </button>
                <h1 className="text-xl font-black text-white tracking-tight uppercase tracking-[0.1em]">Reportes Financieros</h1>
                <button className="p-3 rounded-2xl bg-white/5 border border-white/10 text-primary hover:bg-primary/10 transition-all relative">
                    <Bell size={20} />
                    <span className="absolute top-3.5 right-3.5 size-2 bg-primary rounded-full ring-2 ring-slate-950"></span>
                </button>
            </div>

            <main className="flex-1 px-8 pb-32 space-y-10 animate-in fade-in slide-in-from-bottom-8 duration-700">

                {/* Hero Financial Card */}
                <section>
                    <div className="relative overflow-hidden rounded-[2.5rem] bg-gradient-to-br from-slate-900 via-primary-900/40 to-slate-950 p-8 border border-white/5 shadow-2xl group">
                        <div className="absolute top-0 right-0 -mr-20 -mt-20 size-80 bg-primary/10 rounded-full blur-3xl group-hover:bg-primary/20 transition-all duration-1000"></div>

                        <div className="relative z-10">
                            <div className="flex justify-between items-start">
                                <div>
                                    <p className="text-[10px] font-black text-slate-500 uppercase tracking-[0.2em]">Eventos Totales (7 días)</p>
                                    <h3 className="text-4xl font-black mt-2 text-white">{analytics?.total_events || "0"}</h3>
                                </div>
                                <div className="flex items-center gap-1.5 bg-emerald-500/10 text-emerald-500 text-[10px] font-black px-3 py-1.5 rounded-xl border border-emerald-500/20 uppercase tracking-widest">
                                    <TrendingUp size={14} />
                                    <span>+12.5%</span>
                                </div>
                            </div>

                            <p className="text-[10px] font-black text-slate-600 mt-8 uppercase tracking-widest">Tendencia - Últimos 30 días</p>

                            {/* Trend Chart Mockup */}
                            <div className="mt-4 h-28 flex items-end gap-2.5">
                                {[40, 55, 45, 70, 60, 85, 100, 75, 90].map((h, i) => (
                                    <div
                                        key={i}
                                        style={{ height: `${h}%` }}
                                        className={`flex-1 rounded-t-lg transition-all duration-500 group-hover:opacity-100 ${i === 6 ? 'bg-primary shadow-[0_0_15px_rgba(37,157,244,0.4)]' :
                                            'bg-white/10 opacity-30 group-hover:opacity-50'
                                            }`}
                                    ></div>
                                ))}
                            </div>

                            <div className="mt-8 flex justify-between items-center bg-white/5 p-4 rounded-2xl border border-white/5">
                                <p className="text-[10px] font-black text-slate-400 italic uppercase tracking-widest">Resumen de Crecimiento</p>
                                <button className="bg-primary hover:bg-primary-600 text-white text-[10px] font-black py-2.5 px-6 rounded-xl transition-all shadow-lg shadow-primary/20 active:scale-95 border border-primary-400/20 uppercase tracking-widest">
                                    Ver Detalle
                                </button>
                            </div>
                        </div>
                    </div>
                </section>

                {/* Breakdown Grid */}
                <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div className="md:col-span-2 bg-slate-900/40 backdrop-blur-xl border border-white/5 rounded-[2.5rem] p-8 flex flex-col md:flex-row items-center gap-8 shadow-2xl">
                        <div className="relative size-32 shrink-0 group">
                            <svg className="size-full -rotate-90 drop-shadow-[0_0_10px_rgba(37,157,244,0.2)]" viewBox="0 0 36 36">
                                <circle cx="18" cy="18" fill="transparent" r="15.9" stroke="rgba(255,255,255,0.03)" strokeWidth="3"></circle>
                                <circle cx="18" cy="18" fill="transparent" r="15.9" stroke="#259df4" strokeDasharray="60 100" strokeWidth="3.5" className="transition-all duration-1000"></circle>
                                <circle cx="18" cy="18" fill="transparent" r="15.9" stroke="#1d4e89" strokeDasharray="25 100" strokeDashoffset="-60" strokeWidth="3.5" className="opacity-70"></circle>
                                <circle cx="18" cy="18" fill="transparent" r="15.9" stroke="#0e2a47" strokeDasharray="15 100" strokeDashoffset="-85" strokeWidth="3.5" className="opacity-40"></circle>
                            </svg>
                            <div className="absolute inset-0 flex flex-col items-center justify-center">
                                <span className="text-[9px] font-black text-slate-500 uppercase tracking-widest">Total</span>
                                <PieChart size={16} className="text-primary mt-1" />
                            </div>
                        </div>

                        <div className="flex-1 w-full space-y-5">
                            <h4 className="text-[10px] font-black text-slate-500 uppercase tracking-[0.2em] mb-2">Desglose Operativo</h4>
                            {[
                                { color: 'bg-primary', label: 'Diezmos', val: '$27,168', perc: 60 },
                                { color: 'bg-blue-800', label: 'Misiones', val: '$11,320', perc: 25 },
                                { color: 'bg-slate-800', label: 'Ofrendas', val: '$6,792', perc: 15 },
                            ].map((item, idx) => (
                                <div key={idx} className="flex items-center justify-between group">
                                    <div className="flex items-center gap-3">
                                        <div className={`size-2.5 rounded-full ${item.color} shadow-lg shadow-black/20 group-hover:scale-125 transition-transform`}></div>
                                        <span className="text-xs font-black text-slate-300 uppercase tracking-tight">{item.label}</span>
                                    </div>
                                    <div className="text-right">
                                        <p className="text-xs font-black text-white">{item.val}</p>
                                        <div className="w-16 bg-slate-950 h-1 rounded-full mt-1 overflow-hidden">
                                            <div className={`${item.color} h-full`} style={{ width: `${item.perc}%` }}></div>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                    <div className="bg-slate-900/40 backdrop-blur-xl border border-white/5 rounded-[2.5rem] p-8 flex flex-col justify-center items-center text-center space-y-4 shadow-2xl">
                        <div className="size-16 rounded-[1.5rem] bg-amber-500/10 flex items-center justify-center text-amber-500 border border-amber-500/20">
                            <DollarSign size={32} />
                        </div>
                        <div>
                            <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest leading-none mb-1">Caja Chica</p>
                            <h4 className="text-2xl font-black text-white">$1,450.00</h4>
                        </div>
                        <button className="w-full py-3 bg-white/5 hover:bg-white/10 rounded-xl text-[10px] font-black text-white border border-white/5 uppercase tracking-widest transition-all">
                            Conciliar
                        </button>
                    </div>
                </section>

                {/* Recent Transactions */}
                <section className="space-y-6">
                    <div className="flex justify-between items-center px-2">
                        <h4 className="text-white text-lg font-black tracking-tight uppercase tracking-widest">Transacciones Recientes</h4>
                        <button className="text-[10px] font-black text-primary uppercase tracking-widest hover:underline">Ver todas</button>
                    </div>

                    <div className="space-y-4">
                        {transactions.map((tr) => (
                            <div key={tr.id} className="flex items-center justify-between p-5 rounded-[2rem] bg-slate-900/20 backdrop-blur-md border border-white/5 hover:bg-slate-900/40 hover:border-white/10 transition-all group cursor-pointer">
                                <div className="flex items-center gap-5">
                                    <div className="size-12 rounded-2xl overflow-hidden border-2 border-white/5 group-hover:border-primary/50 transition-all shadow-xl shadow-black/40">
                                        <div className="size-full bg-slate-800 flex items-center justify-center text-white text-[10px] font-bold">
                                            {tr.name?.charAt(0)}
                                        </div>

                                    </div>
                                    <div>
                                        <p className="text-sm font-black text-white tracking-tight group-hover:text-primary transition-colors">{tr.name}</p>
                                        <p className="text-[9px] text-slate-500 font-bold uppercase tracking-widest mt-0.5">{tr.category}</p>
                                    </div>
                                </div>
                                <div className="flex items-center gap-6">
                                    <div className="text-right">
                                        <p className="text-sm font-black text-white">${tr.amount.toFixed(2)}</p>
                                        <span className="text-[8px] font-black bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded-lg border border-emerald-500/20 uppercase tracking-widest">
                                            {tr.status}
                                        </span>
                                    </div>
                                    <button className="text-slate-700 hover:text-white transition-colors">
                                        <ArrowUpRight size={18} />
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                </section>
            </main>
        </div>
    );
}
