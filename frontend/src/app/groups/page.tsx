"use client";

import React, { useState, useEffect, useMemo } from 'react';
import { useAuth } from '@/context/AuthContext';
import { 
    Users, 
    MapPin, 
    Clock, 
    ChevronRight, 
    Search, 
    Filter, 
    MoreHorizontal, 
    Plus, 
    Layout, 
    Map, 
    Hash, 
    User, 
    History, 
    CheckCircle,
    Calendar,
    Phone,
    Mail,
    Edit3,
    TrendingUp
} from 'lucide-react';
import { apiFetch } from '@/lib/http';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';
import { ViewType } from '@/components/ViewSwitcher';
import clsx from 'clsx';
import MetricCard from '@/components/ui/MetricCard';

interface GloryHouse {
    id: number;
    name: string;
    zone: string;
    leader_name: string;
    schedule: string;
    members_count: number;
    phone?: string;
    email?: string;
}

export default function GroupsPage() {
    const { token } = useAuth();
    const [viewType, setViewType] = useState<ViewType>('grid');
    const [selectedHouse, setSelectedHouse] = useState<GloryHouse | null>(null);
    const [isDrawerOpen, setIsDrawerOpen] = useState(false);
    const [houses, setHouses] = useState<GloryHouse[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');

    useEffect(() => {
        const fetchHouses = async () => {
            if (!token) return;
            try {
                const data = await apiFetch('/crm/glory-houses', { token });
                if (Array.isArray(data)) {
                    setHouses(data.map((h: any) => ({
                        id: h.id,
                        name: h.name,
                        zone: h.zone,
                        leader_name: h.leader_name,
                        schedule: h.schedule,
                        members_count: h.members_count || 0,
                        phone: h.phone,
                        email: h.email
                    })));
                }
            } catch (e) {
                console.error("Error fetching houses", e);
            } finally {
                setLoading(false);
            }
        };
        fetchHouses();
    }, [token]);

    const filtered = useMemo(() => 
        houses.filter(h =>
            h.zone.toLowerCase().includes(search.toLowerCase()) ||
            h.name.toLowerCase().includes(search.toLowerCase())
        ), [houses, search]
    );

    const handleOpenHouse = (house: GloryHouse) => {
        setSelectedHouse(house);
        setIsDrawerOpen(true);
    };

    return (
        <div className="flex flex-col h-full bg-white dark:bg-[#1e1f21] overflow-hidden animate-fade-in">
            <WorkspaceToolbar 
                breadcrumbs={[
                    { label: 'CCF', icon: Layout },
                    { label: 'Casas de Bendición', icon: Users }
                ]}
                viewType={viewType}
                setViewType={setViewType}
                availableViews={['grid', 'table']}
                onSearch={setSearch}
                rightActions={
                    <button className="flex items-center gap-2 px-3 py-1.5 bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 rounded-md text-[11px] font-bold hover:bg-blue-100 transition-all shadow-sm">
                        <Map size={14} /> Ver Mapa
                    </button>
                }
            />

            <main className="flex-1 overflow-y-auto scrollbar-thin">
                {viewType === 'grid' ? (
                    <div className="p-4 lg:p-6 space-y-8">
                        {/* Stats Section */}
                        <section className="grid grid-cols-1 md:grid-cols-4 gap-4">
                            <MetricCard title="Total Casas" value={houses.length.toString()} trend="+2" icon={Users} tone="blue" />
                            <MetricCard title="Miembros Activos" value="480" trend="+15" icon={Users} tone="emerald" />
                            <MetricCard title="Zonas Cubiertas" value="8" trend="Estable" icon={MapPin} tone="indigo" />
                            <MetricCard title="Asistencia Promedio" value="92%" trend="+4%" icon={TrendingUp} tone="amber" />
                        </section>

                        {/* Dense Grid View */}
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                            {filtered.map(house => (
                                <div 
                                    key={house.id} 
                                    onClick={() => handleOpenHouse(house)}
                                    className="p-5 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/5 rounded-2xl shadow-sm hover:shadow-xl hover:border-blue-500/30 transition-all cursor-pointer group relative overflow-hidden active:scale-95"
                                >
                                    <div className="flex items-center justify-between mb-4">
                                        <div className="px-2 py-0.5 bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 text-[8px] font-black uppercase rounded-lg tracking-widest">
                                            {house.zone}
                                        </div>
                                        <div className="text-[10px] font-bold text-slate-400 flex items-center gap-1">
                                            <Users size={12} /> {house.members_count}
                                        </div>
                                    </div>
                                    <h3 className="text-[16px] font-bold text-slate-800 dark:text-white mb-4 line-clamp-1">{house.name}</h3>
                                    <div className="space-y-2 mb-4">
                                        <div className="flex items-center gap-2 text-[11px] text-slate-500 dark:text-slate-400 font-medium">
                                            <User size={12} className="text-slate-300" /> {house.leader_name}
                                        </div>
                                        <div className="flex items-center gap-2 text-[11px] text-slate-500 dark:text-slate-400 font-medium">
                                            <Clock size={12} className="text-slate-300" /> {house.schedule}
                                        </div>
                                    </div>
                                    <div className="pt-3 border-t border-slate-50 dark:border-white/5 flex justify-between items-center">
                                        <span className="text-[10px] font-black text-blue-500 uppercase tracking-widest opacity-0 group-hover:opacity-100 transition-opacity">Ver Detalles</span>
                                        <ChevronRight size={14} className="text-slate-300 group-hover:text-blue-500 transition-all" />
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                ) : (
                    <div className="h-full flex flex-col">
                        <table className="w-full text-left border-collapse table-fixed min-w-[900px]">
                            <thead className="sticky top-0 z-20 bg-slate-50 dark:bg-[#1e1f21] border-b border-slate-200 dark:border-white/5">
                                <tr className="h-10">
                                    <th className="px-6 text-[10px] font-black text-slate-400 uppercase tracking-widest w-12 text-center">#</th>
                                    <th className="px-6 text-[10px] font-black text-slate-400 uppercase tracking-widest w-[30%]">Casa / Nombre</th>
                                    <th className="px-6 text-[10px] font-black text-slate-400 uppercase tracking-widest">Zona / Barrio</th>
                                    <th className="px-6 text-[10px] font-black text-slate-400 uppercase tracking-widest text-center w-32">Líder</th>
                                    <th className="px-6 text-[10px] font-black text-slate-400 uppercase tracking-widest">Miembros</th>
                                    <th className="px-6 text-[10px] font-black text-slate-400 uppercase tracking-widest text-right w-24">Acciones</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100 dark:divide-white/5">
                                {filtered.map(house => (
                                    <tr 
                                        key={house.id} 
                                        onClick={() => handleOpenHouse(house)}
                                        className="hover:bg-blue-50/50 dark:hover:bg-blue-500/5 transition-colors group cursor-pointer h-12"
                                    >
                                        <td className="px-6 text-center text-[11px] font-bold text-slate-400">#{house.id}</td>
                                        <td className="px-6">
                                            <span className="text-[13px] font-bold text-slate-700 dark:text-slate-200">{house.name}</span>
                                        </td>
                                        <td className="px-6">
                                            <div className="flex items-center gap-2">
                                                <MapPin size={12} className="text-slate-300" />
                                                <span className="text-[12px] font-medium text-slate-500">{house.zone}</span>
                                            </div>
                                        </td>
                                        <td className="px-6 text-center">
                                            <div className="flex items-center justify-center gap-2">
                                                <div className="w-6 h-6 rounded-full bg-slate-900 dark:bg-blue-600 flex items-center justify-center text-[9px] font-black text-white">{house.leader_name.substring(0, 2).toUpperCase()}</div>
                                                <span className="text-[12px] font-bold text-slate-600 dark:text-slate-300">{house.leader_name}</span>
                                            </div>
                                        </td>
                                        <td className="px-6">
                                            <div className="flex items-center gap-2">
                                                <Users size={12} className="text-slate-300" />
                                                <span className="text-[12px] font-bold text-slate-500">{house.members_count}</span>
                                            </div>
                                        </td>
                                        <td className="px-6 text-right">
                                            <div className="opacity-0 group-hover:opacity-100 transition-opacity flex justify-end gap-1">
                                                <button className="p-1.5 hover:bg-slate-200 dark:hover:bg-white/10 rounded-md text-slate-400"><Edit3 size={13} /></button>
                                                <button className="p-1.5 hover:bg-slate-200 dark:hover:bg-white/10 rounded-md text-slate-400"><MoreHorizontal size={13} /></button>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </main>

            {/* Glory House Detail Drawer */}
            <WorkspaceDrawer 
                isOpen={isDrawerOpen} 
                onClose={() => setIsDrawerOpen(false)}
                title={selectedHouse?.name || 'Detalles de la Casa'}
                subtitle={`${selectedHouse?.zone || 'CCF'} • Grupo de Bendición`}
                actions={
                    <>
                        <button className="px-4 py-2 text-[11px] font-bold text-slate-500">Cerrar</button>
                        <button className="px-6 py-2 bg-blue-600 text-white rounded-lg text-[11px] font-bold shadow-lg shadow-blue-500/20 active:scale-95 transition-all">Registrar Asistencia</button>
                    </>
                }
            >
                <div className="space-y-8 animate-fade-in">
                    <section className="grid grid-cols-2 gap-4">
                        <HouseStat label="Líder" value={selectedHouse?.leader_name} icon={User} />
                        <HouseStat label="Horario" value={selectedHouse?.schedule} icon={Clock} />
                        <HouseStat label="Miembros" value={selectedHouse?.members_count?.toString()} icon={Users} />
                        <HouseStat label="Zona" value={selectedHouse?.zone} icon={MapPin} />
                    </section>

                    <section className="space-y-4">
                        <div className="flex items-center gap-2">
                            <Hash size={14} className="text-blue-500" />
                            <h4 className="text-[11px] font-black text-slate-400 uppercase tracking-widest">Información de Contacto</h4>
                        </div>
                        <div className="grid grid-cols-1 gap-2">
                            <div className="flex items-center gap-3 p-3 bg-slate-50 dark:bg-white/5 rounded-xl border border-slate-100 dark:border-white/5">
                                <Phone size={14} className="text-slate-400" />
                                <span className="text-[12px] font-bold text-slate-700 dark:text-slate-200">+57 300 123 4567</span>
                            </div>
                            <div className="flex items-center gap-3 p-3 bg-slate-50 dark:bg-white/5 rounded-xl border border-slate-100 dark:border-white/5">
                                <Mail size={14} className="text-slate-400" />
                                <span className="text-[12px] font-bold text-slate-700 dark:text-slate-200">{selectedHouse?.leader_name.toLowerCase().replace(' ', '.')}@ccf.org</span>
                            </div>
                        </div>
                    </section>

                    <section className="space-y-4 pt-6 border-t border-slate-100 dark:border-white/5">
                        <h4 className="text-[11px] font-black text-slate-400 uppercase tracking-widest flex items-center gap-2">
                            <History size={14} className="text-blue-500" /> Reportes de Asistencia
                        </h4>
                        <div className="space-y-3">
                            {[1, 2, 3].map(i => (
                                <div key={i} className="flex gap-4 p-4 bg-slate-50 dark:bg-white/5 rounded-xl border border-slate-200 dark:border-white/5 hover:border-blue-500/20 transition-all cursor-pointer">
                                    <div className="w-8 h-8 rounded-lg bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center text-emerald-600 shrink-0"><CheckCircle size={14} /></div>
                                    <div className="flex-1">
                                        <div className="flex justify-between items-center mb-1">
                                            <p className="text-[12px] font-bold text-slate-700 dark:text-slate-200">Reunión de Bendición</p>
                                            <span className="text-[10px] font-bold text-emerald-500">12 Presentes</span>
                                        </div>
                                        <p className="text-[10px] text-slate-400">Hace {i} semana • Reportado por {selectedHouse?.leader_name}</p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </section>
                </div>
            </WorkspaceDrawer>
        </div>
    );
}

function HouseStat({ label, value, icon: Icon }: any) {
    return (
        <div className="p-3 bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/5 rounded-xl">
            <div className="flex items-center gap-2 mb-1">
                <Icon size={12} className="text-slate-400" />
                <span className="text-[9px] font-black text-slate-400 uppercase tracking-widest">{label}</span>
            </div>
            <p className="text-[12px] font-bold text-slate-700 dark:text-slate-200 truncate">{value || 'N/A'}</p>
        </div>
    );
}
