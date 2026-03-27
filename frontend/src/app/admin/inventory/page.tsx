"use client";

import React, { useEffect, useState } from 'react';
import { 
    Package, Search, Filter, Plus, CheckCircle2, Wrench, AlertTriangle, ChevronRight
} from 'lucide-react';
import { api } from '@/services/apiService';
import { StatCard } from '@/components/StatCard';

export default function AdminInventoryPage() {
    const [assets, setAssets] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        api.get<any[]>('/assets/')
            .then(setAssets)
            .catch(console.error)
            .finally(() => setLoading(false));
    }, []);

    const stats = {
        total: assets.length,
        operativo: assets.filter(a => a.current_status === 'Disponible').length,
        mantenimiento: assets.filter(a => a.current_status === 'Mantenimiento').length,
        daniado: assets.filter(a => a.current_status === 'Dañado').length,
    };

    if (loading) return <div className="p-8 animate-pulse text-primary font-black tracking-widest uppercase italic">Contando Activos...</div>;

    return (
        <div className="p-8 space-y-8 animate-in fade-in duration-700">
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
                <div className="space-y-2">
                    <h1 className="text-4xl font-black tracking-tighter text-white uppercase italic">
                        Control de <span className="text-primary">Inventario</span>
                    </h1>
                    <p className="text-muted-foreground text-sm max-w-xl">
                        Gestion de recursos materiales sincronizada con la base de datos v3.9.
                    </p>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <StatCard label="Total Activos" value={stats.total} icon={Package} color="text-white" bg="bg-white/5" />
                <StatCard label="En Operación" value={stats.operativo} icon={CheckCircle2} color="text-emerald-500" bg="bg-emerald-500/10" />
                <StatCard label="En Revisión" value={stats.mantenimiento} icon={Wrench} color="text-amber-500" bg="bg-amber-500/10" />
                <StatCard label="Baja / Dañado" value={stats.daniado} icon={AlertTriangle} color="text-rose-500" bg="bg-rose-500/10" />
            </div>

            <div className="bg-[#1e1f21] border border-white/5 rounded-[2.5rem] overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full text-left">
                        <thead>
                            <tr className="border-b border-white/5 bg-white/[0.02]">
                                <th className="px-6 py-4 text-[10px] font-black text-muted-foreground uppercase tracking-widest">Activo</th>
                                <th className="px-6 py-4 text-[10px] font-black text-muted-foreground uppercase tracking-widest">Marca / Serial</th>
                                <th className="px-6 py-4 text-[10px] font-black text-muted-foreground uppercase tracking-widest">Estado</th>
                                <th className="px-6 py-4 text-[10px] font-black text-muted-foreground uppercase tracking-widest text-right">Acciones</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5">
                            {assets.map((asset, i) => (
                                <tr key={i} className="group hover:bg-white/[0.02] transition-colors">
                                    <td className="px-6 py-5">
                                        <div className="text-sm font-bold text-white uppercase tracking-tight">{asset.name}</div>
                                    </td>
                                    <td className="px-6 py-5">
                                        <div className="text-xs text-muted-foreground font-medium">{asset.brand} <span className="opacity-30">|</span> {asset.serial_number || 'S/N'}</div>
                                    </td>
                                    <td className="px-6 py-5">
                                        <span className={`text-[10px] font-black uppercase ${asset.current_status === 'Disponible' ? 'text-emerald-500' : 'text-amber-500'}`}>
                                            {asset.current_status}
                                        </span>
                                    </td>
                                    <td className="px-6 py-5 text-right">
                                        <button className="p-2 bg-white/5 hover:bg-white/10 text-white rounded-lg transition-all">
                                            <ChevronRight size={16} />
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
