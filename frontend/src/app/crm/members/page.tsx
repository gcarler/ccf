"use client";

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import CrmShell from '@/components/crm/CrmShell';
import { 
    Users, 
    Plus, 
    Search, 
    Filter, 
    Download, 
    ChevronRight, 
    LayoutDashboard,
    User,
    Mail,
    Phone,
    TrendingUp
} from 'lucide-react';
import { DSCard } from '@/design/components/DSCard';
import { DSBadge } from '@/design/components/DSBadge';
import { DSMetric } from '@/design/components/DSMetric';
import { toast } from 'sonner';

export default function MembersPage() {
    const { token } = useAuth();
    const router = useRouter();
    const [members, setMembers] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [query, setQuery] = useState('');

    useEffect(() => {
        if (!token) return;
        const loadMembers = async () => {
            try {
                setLoading(true);
                const data = await apiFetch<any[]>('/crm/members', { token }).catch(() => []);
                setMembers(data);
            } catch (err) {
                toast.error('Error al cargar membresía');
            } finally {
                setLoading(false);
            }
        };
        loadMembers();
    }, [token]);

    const filteredMembers = members.filter(m => 
        `${m.first_name} ${m.last_name}`.toLowerCase().includes(query.toLowerCase()) ||
        m.email?.toLowerCase().includes(query.toLowerCase())
    );

    return (
        <CrmShell
            breadcrumbs={[
                { label: 'CRM', icon: LayoutDashboard, href: '/crm' },
                { label: 'Membresía', icon: Users },
            ]}
        >
            <main className="flex-1 overflow-y-auto p-8 lg:p-12 space-y-10">
                <header className="flex flex-col md:flex-row md:items-center justify-between gap-6">
                    <h1 className="text-4xl font-black text-slate-900 dark:text-white tracking-tight uppercase">Base de Datos de Miembros</h1>
                    <button className="px-6 py-2 bg-blue-600 text-white rounded-xl text-[10px] font-black uppercase tracking-widest shadow-lg shadow-blue-500/20 hover:scale-105 transition-all flex items-center gap-2">
                        <Plus size={14} /> Nuevo Miembro
                    </button>
                </header>

                <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <DSMetric label="Total Miembros" value={String(members.length)} trend="Vivos en Cristo" tone="blue" />
                    <DSMetric label="Actividad Académica" value="78%" trend="Promedio" tone="emerald" />
                    <DSMetric label="Nuevas Almas" value="15" trend="Este mes" tone="amber" />
                </section>

                <div className="space-y-6">
                    <div className="relative max-w-md w-full">
                        <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                        <input 
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            placeholder="Buscar por nombre o correo..."
                            className="w-full bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-2xl py-3 pl-12 pr-4 text-sm outline-none focus:ring-4 focus:ring-blue-500/10 transition-all"
                        />
                    </div>

                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        {filteredMembers.map(member => (
                            <DSCard key={member.id}>
                                <div className="flex items-center justify-between group cursor-pointer" onClick={() => router.push(`/crm/members/${member.id}`)}>
                                    <div className="flex items-center gap-4">
                                        <div className="size-12 rounded-2xl bg-blue-500/10 flex items-center justify-center text-blue-600">
                                            <User size={24} />
                                        </div>
                                        <div>
                                            <h3 className="text-sm font-black text-slate-900 dark:text-white uppercase">{member.first_name} {member.last_name}</h3>
                                            <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">{member.church_role}</p>
                                        </div>
                                    </div>
                                    <ChevronRight size={18} className="text-slate-200 group-hover:text-blue-500 transition-all" />
                                </div>
                            </DSCard>
                        ))}
                    </div>
                </div>
            </main>
        </CrmShell>
    );
}
