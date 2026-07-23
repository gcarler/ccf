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
    personas_count?: number;
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
        <div className="flex flex-col h-full bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-1))]">
            <header className="p-3 border-b border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-white/5 space-y-4">
                <div>
                    <h1 className="text-xl font-bold text-[hsl(var(--text-primary))] dark:text-white uppercase tracking-tight">Descubrir Grupos</h1>
                    <p className="text-xs text-[hsl(var(--text-secondary))] font-medium mt-1">Encuentra un grupo cerca de ti</p>
                </div>
                <div className="relative max-w-xl">
                    <input
                        type="text"
                        placeholder="Buscar por nombre, zona o líder..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="w-full pl-10 pr-4 py-2 bg-[hsl(var(--surface-2))] dark:bg-black/20 border border-[hsl(var(--border))] dark:border-white/10 rounded-md text-sm font-bold text-[hsl(var(--text-primary))] dark:text-white focus:ring-2 focus:ring-primary focus:border-transparent outline-none transition-all"
                    />
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]" size={16} />
                </div>
            </header>

            <main className="flex-1 overflow-y-auto p-3 scrollbar-thin">
                {loading ? (
 <div className="space-y-3 w-full">
                        {[1, 2, 3].map(i => <Skeleton key={i} className="h-20 w-full rounded-md" />)}
                    </div>
                ) : (
 <div className="w-full grid gap-3">
                        {filteredGroups.length === 0 ? (
                            <div className="text-center py-1.5 text-[hsl(var(--text-secondary))]">
                                <Search className="mx-auto h-8 w-12 mb-4 opacity-20" />
                                <p className="font-bold text-sm">No se encontraron grupos</p>
                            </div>
                        ) : (
                            filteredGroups.map(group => (
                                <article key={group.id} className="bg-[hsl(var(--bg-primary))] dark:bg-white/[0.02] border border-[hsl(var(--border))] dark:border-white/10 p-4 rounded-md flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:border-primary/30 transition-colors group">
                                    <div className="flex-1">
                                        <div className="flex items-center gap-2 mb-1">
                                            <h3 className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-white">{group.name}</h3>
                                            {group.zone && (
                                                <span className="px-2 py-0.5 bg-[hsl(var(--info-muted))] text-[hsl(var(--info))] rounded-md text-[9px] font-bold uppercase tracking-wide">
                                                    {group.zone}
                                                </span>
                                            )}
                                        </div>
                                        <div className="flex items-center gap-4 text-xs font-medium text-[hsl(var(--text-secondary))]">
                                            <span className="flex items-center gap-1"><MapPin size={12} /> {group.address || 'Dirección pendiente'}</span>
                                            <span className="flex items-center gap-1"><Users size={12} /> Lider: {group.leader_name || 'N/A'}</span>
                                        </div>
                                    </div>
                                    <button className="shrink-0 px-4 py-2 bg-[hsl(var(--surface-2))] dark:bg-white/5 hover:bg-[hsl(var(--surface-3))] dark:hover:bg-white/10 text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] rounded-lg text-[10px] font-bold uppercase tracking-wide transition-colors flex items-center gap-2">
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

