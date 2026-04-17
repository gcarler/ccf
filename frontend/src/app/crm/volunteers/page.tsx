"use client";

import React, { useState, useEffect } from 'react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import { 
    Users, 
    Calendar, 
    Plus, 
    Heart, 
    LayoutDashboard,
    Search,
    ChevronRight,
    Star,
    MoreHorizontal
} from 'lucide-react';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import { DSCard } from '@/design/components/DSCard';
import { DSBadge } from '@/design/components/DSBadge';
import { DSMetric } from '@/design/components/DSMetric';
import { toast } from 'sonner';
import CrmShell from '@/components/crm/CrmShell';

export default function VolunteersPage() {
    const { token } = useAuth();
    const [volunteers, setVolunteers] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!token) return;
        const loadVolunteers = async () => {
            try {
                setLoading(true);
                const data = await apiFetch<any[]>('/crm/volunteers', { token }).catch(() => []);
                setVolunteers(data);
            } catch (err) {
                toast.error('Error al cargar servidores');
            } finally {
                setLoading(false);
            }
        };
        loadVolunteers();
    }, [token]);

    return (
        <CrmShell
            breadcrumbs={[
                { label: 'CRM', icon: LayoutDashboard, href: '/crm' },
                { label: 'Voluntariado', icon: Heart },
            ]}
        >
            <main className="flex-1 overflow-y-auto p-8 lg:p-12 space-y-10">
                <header className="flex items-center justify-between">
                    <h1 className="text-4xl font-black text-slate-900 dark:text-white tracking-tight uppercase">Cuerpo de Servidores</h1>
                    <button className="px-6 py-2 bg-blue-600 text-white rounded-xl text-[10px] font-black uppercase tracking-widest shadow-lg shadow-blue-500/20 hover:scale-105 transition-all flex items-center gap-2">
                        <Plus size={14} /> Registrar Servidor
                    </button>
                </header>

                <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <DSMetric label="Total Servidores" value={String(volunteers.length)} trend="Activos" tone="blue" />
                    <DSMetric label="Nuevos" value="5" trend="Últimos 30 días" tone="emerald" />
                    <DSMetric label="Fidelidad" value="92%" trend="Asistencia" tone="amber" />
                </section>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                    {volunteers.map(v => (
                        <DSCard key={v.id}>
                            <div className="flex items-start justify-between">
                                <div className="flex items-center gap-4">
                                    <div className="size-12 rounded-2xl bg-violet-500/10 flex items-center justify-center text-violet-600">
                                        <Users size={24} />
                                    </div>
                                    <div>
                                        <h3 className="text-lg font-black text-slate-900 dark:text-white uppercase">{v.name}</h3>
                                        <p className="text-xs font-medium text-slate-500">{v.role} • {v.team}</p>
                                    </div>
                                </div>
                                <DSBadge tone={v.status === 'active' ? 'emerald' : 'slate'} label={v.status.toUpperCase()} />
                            </div>
                        </DSCard>
                    ))}
                    
                    {volunteers.length === 0 && (
                        <div className="col-span-full py-20 text-center border-2 border-dashed border-slate-100 rounded-[2.5rem]">
                            <Users size={48} className="mx-auto text-slate-100 mb-4" />
                            <p className="text-xs font-black uppercase tracking-widest text-slate-400">No hay servidores registrados aún</p>
                        </div>
                    )}
                </div>
            </main>
        </CrmShell>
    );
}
