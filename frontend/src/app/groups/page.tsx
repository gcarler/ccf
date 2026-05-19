"use client";

import React, { useState, useEffect } from 'react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import { 
    Home, 
    MapPin, 
    Plus, 
    TrendingUp,
    MoreHorizontal
} from 'lucide-react';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import { DSCard } from '@/design/components/DSCard';
import { DSMetric } from '@/design/components/DSMetric';
import { toast } from 'sonner';

export default function GroupsPage() {
    const { token } = useAuth();
    const [groups, setGroups] = useState<any[]>([]);

    useEffect(() => {
        if (!token) return;
        const loadGroups = async () => {
            try {
                const data = await apiFetch<any[]>('/evangelism/glory-houses', { token }).catch(() => []);
                setGroups(data);
            } catch (err) {
                toast.error('Error al cargar Casas de Bendición');
            }
        };
        loadGroups();
    }, [token]);

    return (
        <div className="flex flex-col h-full bg-[#f8fafc] dark:bg-[#0b0d11] overflow-hidden">
            <WorkspaceToolbar
                breadcrumbs={[
                    { label: 'Casas de Bendición', icon: Home },
                    { label: 'Dashboard', icon: TrendingUp },
                ]}
                rightActions={
                    <button className="px-6 py-2 bg-blue-600 text-white rounded-xl text-[10px] font-black uppercase tracking-widest shadow-lg shadow-blue-500/20 hover:scale-105 transition-all flex items-center gap-2">
                        <Plus size={14} /> Nueva Casa
                    </button>
                }
            />

            <main className="flex-1 overflow-y-auto p-8 lg:p-12 space-y-10">
                <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <DSMetric label="Total Casas" value={String(groups.length)} trend="+2 este mes" tone="blue" />
                    <DSMetric label="Miembros Activos" value="245" trend="85% asistencia" tone="emerald" />
                    <DSMetric label="Nuevos este mes" value="12" trend="Crecimiento 5%" tone="amber" />
                </section>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                    {groups.map(group => (
                        <DSCard key={group.id}>
                            <div className="flex items-start justify-between">
                                <div className="flex items-center gap-4">
                                    <div className="size-12 rounded-2xl bg-blue-500/10 flex items-center justify-center text-blue-600">
                                        <Home size={24} />
                                    </div>
                                    <div>
                                        <h3 className="text-lg font-black text-slate-900 dark:text-white uppercase">{group.name}</h3>
                                        <p className="text-xs font-medium text-slate-500 flex items-center gap-1">
                                            <MapPin size={12} /> {group.address || 'Ubicación pendiente'}
                                        </p>
                                    </div>
                                </div>
                                <button className="p-2 text-slate-400 hover:bg-slate-50 rounded-lg">
                                    <MoreHorizontal size={18} />
                                </button>
                            </div>
                        </DSCard>
                    ))}
                    
                    {groups.length === 0 && (
                        <div className="col-span-full py-20 text-center border-2 border-dashed border-slate-100 rounded-[2.5rem]">
                            <Home size={48} className="mx-auto text-slate-100 mb-4" />
                            <p className="text-xs font-black uppercase tracking-widest text-slate-400">No hay casas registradas aún</p>
                        </div>
                    )}
                </div>
            </main>
        </div>
    );
}
