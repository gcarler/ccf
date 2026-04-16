"use client";

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import { 
    Heart, 
    DollarSign, 
    Users, 
    TrendingUp, 
    Plus, 
    Filter, 
    Search,
    Download,
    Calendar,
    ChevronRight,
    ArrowUpRight,
    ArrowDownRight,
    Settings,
    LayoutDashboard
} from 'lucide-react';
import { apiFetch } from '@/lib/http';
import DSMetric from '@/design/components/DSMetric';
import DSCard from '@/design/components/DSCard';
import DSBadge from '@/design/components/DSBadge';
import { toast } from 'sonner';

export default function DonationsManagementPage() {
    const router = useRouter();
    const { token } = useAuth();
    const [donations, setDonations] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [query, setQuery] = useState('');

    useEffect(() => {
        if (!token) return;
        const loadDonations = async () => {
            try {
                setLoading(true);
                // Fallback to mock if endpoint is not fully ready
                const data = await apiFetch<any[]>('/crm/members/donations', { token }).catch(() => []);
                setDonations(Array.isArray(data) ? data : [
                    { id: 1, donor: 'Juan Perez', amount: 500, type: 'Diezmo', date: '2026-04-10', status: 'completed' },
                    { id: 2, donor: 'Maria Garcia', amount: 200, type: 'Ofrenda', date: '2026-04-12', status: 'completed' },
                    { id: 3, donor: 'Pedro Lopez', amount: 1000, type: 'Donación Especial', date: '2026-04-13', status: 'pending' },
                ]);
            } catch (err) {
                console.error(err);
                toast.error('Error al cargar donaciones');
            } finally {
                setLoading(false);
            }
        };
        loadDonations();
    }, [token]);

    return (
        <div className="flex flex-col h-full bg-[#f8fafc] dark:bg-[#0b0d11] overflow-hidden">
            <WorkspaceToolbar
                breadcrumbs={[
                    { label: 'Administración', icon: LayoutDashboard },
                    { label: 'Donaciones y Ofrendas', icon: Heart },
                ]}
                rightActions={
                    <div className="flex items-center gap-3">
                        <button 
                            onClick={() => router.push('/admin/donations/config')}
                            className="size-10 flex items-center justify-center rounded-xl bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 text-slate-500 hover:text-blue-600 transition-all"
                        >
                            <Settings size={20} />
                        </button>
                        <button 
                            className="px-6 py-2 bg-blue-600 text-white rounded-xl text-[10px] font-black uppercase tracking-widest shadow-lg shadow-blue-500/20 hover:scale-105 transition-all flex items-center gap-2"
                        >
                            <Plus size={14} /> Registrar Manual
                        </button>
                    </div>
                }
            />

            <main className="flex-1 overflow-y-auto p-8 lg:p-12 space-y-10">
                <section className="grid grid-cols-1 md:grid-cols-4 gap-6">
                    <DSMetric label="Recaudación Mensual" value="$42,500" trend="+12% vs marzo" tone="blue" icon={DollarSign} />
                    <DSMetric label="Donantes Activos" value="156" trend="+8 nuevos" tone="emerald" icon={Users} />
                    <DSMetric label="Promedio por Donación" value="$272" trend="Sostenido" tone="amber" icon={TrendingUp} />
                    <DSMetric label="Pendientes" value="4" trend="Por conciliar" tone="purple" icon={Calendar} />
                </section>

                <div className="space-y-6">
                    <header className="flex items-center justify-between">
                        <div className="relative max-w-md w-full">
                            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                            <input 
                                value={query}
                                onChange={(e) => setQuery(e.target.value)}
                                placeholder="Buscar por donante o referencia..."
                                className="w-full bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-2xl py-3 pl-12 pr-4 text-sm outline-none focus:ring-4 focus:ring-blue-500/10 transition-all"
                            />
                        </div>
                        <div className="flex items-center gap-3">
                            <button className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl text-[10px] font-black uppercase tracking-widest text-slate-600 hover:bg-slate-50 transition-all">
                                <Filter size={14} /> Filtrar
                            </button>
                            <button className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl text-[10px] font-black uppercase tracking-widest text-slate-600 hover:bg-slate-50 transition-all">
                                <Download size={14} /> Exportar
                            </button>
                        </div>
                    </header>

                    <DSCard>
                        <div className="overflow-x-auto">
                            <table className="w-full text-left">
                                <thead>
                                    <tr className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400 border-b border-slate-100 dark:border-white/5">
                                        <th className="px-6 py-4">Donante</th>
                                        <th className="px-6 py-4">Monto</th>
                                        <th className="px-6 py-4">Categoría</th>
                                        <th className="px-6 py-4">Fecha</th>
                                        <th className="px-6 py-4">Estado</th>
                                        <th className="px-6 py-4 text-right">Acción</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-50 dark:divide-white/5">
                                    {donations.map((d) => (
                                        <tr 
                                            key={d.id} 
                                            className="hover:bg-slate-50/50 dark:hover:bg-white/[0.02] transition-colors group cursor-pointer"
                                            onClick={() => router.push(`/admin/donations/${d.id}`)}
                                        >
                                            <td className="px-6 py-4">
                                                <div className="font-bold text-slate-900 dark:text-white group-hover:text-blue-600 transition-colors">{d.donor}</div>
                                                <div className="text-[10px] text-slate-400 uppercase font-black">ID: #{d.id}0034</div>
                                            </td>
                                            <td className="px-6 py-4">
                                                <div className="font-black text-slate-900 dark:text-white tracking-tight">${d.amount}</div>
                                            </td>
                                            <td className="px-6 py-4 text-xs font-medium text-slate-500">{d.type}</td>
                                            <td className="px-6 py-4 text-xs text-slate-400">{new Date(d.date).toLocaleDateString()}</td>
                                            <td className="px-6 py-4">
                                                <DSBadge variant={d.status === 'completed' ? 'success' : 'warning'}>
                                                    {d.status === 'completed' ? 'COMPLETADO' : 'PENDIENTE'}
                                                </DSBadge>
                                            </td>
                                            <td className="px-6 py-4 text-right">
                                                <button className="size-8 rounded-lg bg-slate-100 dark:bg-white/5 flex items-center justify-center text-slate-400 hover:bg-blue-600 hover:text-white transition-all">
                                                    <ChevronRight size={16} />
                                                </button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </DSCard>
                </div>
            </main>
        </div>
    );
}
