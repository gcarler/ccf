"use client";

import React, { useState, useEffect, useMemo } from 'react';
import { Search, MapPin, Users, Navigation } from 'lucide-react';
import { apiFetch } from '@/lib/http';
import { useAuth } from '@/context/AuthContext';
import Skeleton from '@/components/ui/Skeleton';

interface GroupRecord {
    id: number;
    name: string;
    zone?: string | null;
    leader_name?: string | null;
    address?: string | null;
    members_count?: number;
}

export default function DiscoverPage() {
    const { token } = useAuth();
    const [groups, setGroups] = useState<GroupRecord[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');

    useEffect(() => {
        const loadGroups = async () => {
            if (!token) return;
            setLoading(true);
            try {
                const data = await apiFetch<GroupRecord[]>('/crm/groups', { token });
                setGroups(Array.isArray(data) ? data : []);
            } catch (err) {
                console.error(err);
            } finally {
                setLoading(false);
            }
        };
        loadGroups();
    }, [token]);

    const filteredGroups = useMemo(() => {
        const term = searchTerm.toLowerCase();
        return groups.filter(g => 
            g.name.toLowerCase().includes(term) || 
            (g.zone && g.zone.toLowerCase().includes(term)) ||
            (g.leader_name && g.leader_name.toLowerCase().includes(term))
        );
    }, [groups, searchTerm]);

    return (
        <div className="flex flex-col h-full bg-[#f8fafc] dark:bg-[#1E1F21]">
            <header className="p-6 border-b border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 space-y-4">
                <div>
                    <h1 className="text-xl font-bold text-slate-900 dark:text-white uppercase tracking-tight">Descubrir Grupos</h1>
                    <p className="text-xs text-slate-500 font-medium mt-1">Encuentra una casa de bendición cerca de ti</p>
                </div>
                <div className="relative max-w-xl">
                    <input
                        type="text"
                        placeholder="Buscar por nombre, zona o líder..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="w-full pl-10 pr-4 py-2 bg-slate-100 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-xl text-sm font-bold text-slate-900 dark:text-white focus:ring-2 focus:ring-primary focus:border-transparent outline-none transition-all"
                    />
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
                </div>
            </header>

            <main className="flex-1 overflow-y-auto p-6 scrollbar-thin">
                {loading ? (
                    <div className="space-y-3 max-w-4xl mx-auto">
                        {[1, 2, 3].map(i => <Skeleton key={i} className="h-20 w-full rounded-xl" />)}
                    </div>
                ) : (
                    <div className="max-w-4xl mx-auto grid gap-3">
                        {filteredGroups.length === 0 ? (
                            <div className="text-center py-12 text-slate-400">
                                <Search className="mx-auto h-12 w-12 mb-4 opacity-20" />
                                <p className="font-bold text-sm">No se encontraron grupos</p>
                            </div>
                        ) : (
                            filteredGroups.map(group => (
                                <article key={group.id} className="bg-white dark:bg-white/[0.02] border border-slate-200 dark:border-white/10 p-4 rounded-xl flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:border-primary/30 transition-colors group">
                                    <div className="flex-1">
                                        <div className="flex items-center gap-2 mb-1">
                                            <h3 className="text-sm font-bold text-slate-900 dark:text-white">{group.name}</h3>
                                            {group.zone && (
                                                <span className="px-2 py-0.5 bg-blue-50 dark:bg-blue-500/10 text-blue-600 dark:text-blue-400 rounded-md text-[9px] font-bold uppercase tracking-widest">
                                                    {group.zone}
                                                </span>
                                            )}
                                        </div>
                                        <div className="flex items-center gap-4 text-xs font-medium text-slate-500">
                                            <span className="flex items-center gap-1"><MapPin size={12} /> {group.address || 'Dirección pendiente'}</span>
                                            <span className="flex items-center gap-1"><Users size={12} /> Lider: {group.leader_name || 'N/A'}</span>
                                        </div>
                                    </div>
                                    <button className="shrink-0 px-4 py-2 bg-slate-100 dark:bg-white/5 hover:bg-slate-200 dark:hover:bg-white/10 text-slate-700 dark:text-slate-300 rounded-lg text-[10px] font-bold uppercase tracking-widest transition-colors flex items-center gap-2">
                                        <Navigation size={12} /> Contactar
                                    </button>
                                </article>
                            ))
                        )}
                    </div>
                )}
            </main>
        </div>
    );
}

