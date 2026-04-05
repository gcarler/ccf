"use client";

import React, { useState, useEffect, useMemo } from 'react';
import { useAuth } from '@/context/AuthContext';
import {
    Users,
    MapPin,
    Clock,
    ChevronRight,
    Layout,
    Map,
    Hash,
    User,
    History,
    CheckCircle,
    Phone,
    Mail,
    Edit3,
    MoreHorizontal,
    TrendingUp,
    Home,
    AlertCircle
} from 'lucide-react';
import { apiFetch } from '@/lib/http';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';
import { ViewType } from '@/components/ViewSwitcher';
import MetricCard from '@/components/ui/MetricCard';

interface GloryHouse {
    id: number;
    name: string;
    zone: string;
    leader_name: string;
    schedule: string;
    members_count: number;
    capacity: number;
    address?: string;
    phone?: string;
    email?: string;
    status?: string;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function safeInitials(name?: string): string {
    if (!name) return '??';
    return name.trim().split(/\s+/).map(w => w[0] ?? '').join('').substring(0, 2).toUpperCase();
}

function safeEmail(name?: string): string {
    if (!name) return 'sin-lider@ccf.org';
    return name.trim().toLowerCase().replace(/\s+/g, '.') + '@ccf.org';
}

// ─── Sub-components ──────────────────────────────────────────────────────────

function HouseStat({ label, value, icon: Icon }: { label: string; value?: string | number; icon: React.ElementType }) {
    return (
        <div className="p-3 bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/5 rounded-xl">
            <div className="flex items-center gap-2 mb-1">
                <Icon size={12} className="text-slate-400" />
                <span className="text-[9px] font-black text-slate-400 uppercase tracking-widest">{label}</span>
            </div>
            <p className="text-[12px] font-bold text-slate-700 dark:text-slate-200 truncate">
                {value != null && value !== '' ? String(value) : 'No especificado'}
            </p>
        </div>
    );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function GroupsPage() {
    const { token } = useAuth();
    const [viewType, setViewType] = useState<ViewType>('grid');
    const [selectedHouse, setSelectedHouse] = useState<GloryHouse | null>(null);
    const [isDrawerOpen, setIsDrawerOpen] = useState(false);
    const [houses, setHouses] = useState<GloryHouse[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [search, setSearch] = useState('');

    useEffect(() => {
        const fetchHouses = async () => {
            if (!token) return;
            setLoading(true);
            setError(null);
            try {
                const data = await apiFetch<any[]>('/crm/glory-houses', { token });
                if (Array.isArray(data)) {
                    setHouses(data.map((h) => ({
                        id: h.id,
                        name: h.name ?? 'Sin nombre',
                        zone: h.zone ?? 'Sin zona',
                        leader_name: h.leader_name ?? '',
                        schedule: h.schedule ?? '',
                        members_count: h.members_count ?? 0,
                        capacity: h.capacity ?? 0,
                        address: h.address ?? '',
                        phone: h.phone ?? '',
                        email: h.email ?? '',
                        status: h.status ?? 'Activo',
                    })));
                }
            } catch (e) {
                console.error("Error fetching houses", e);
                setError("No se pudieron cargar las casas.");
            } finally {
                setLoading(false);
            }
        };
        fetchHouses();
    }, [token]);

    const filtered = useMemo(() =>
        houses.filter(h =>
            h.zone.toLowerCase().includes(search.toLowerCase()) ||
            h.name.toLowerCase().includes(search.toLowerCase()) ||
            h.leader_name.toLowerCase().includes(search.toLowerCase())
        ), [houses, search]
    );

    // ─── Computed metrics (real data) ───────────────────────────────────────
    const totalMembers = houses.reduce((sum, h) => sum + h.members_count, 0);
    const uniqueZones = new Set(houses.map(h => h.zone).filter(Boolean)).size;
    const saturatedCount = houses.filter(h => h.capacity > 0 && h.members_count / h.capacity >= 1).length;
    const avgOccupancyPct = houses.length > 0
        ? Math.round(houses.filter(h => h.capacity > 0).reduce((sum, h) => sum + (h.members_count / h.capacity) * 100, 0) / (houses.filter(h => h.capacity > 0).length || 1))
        : 0;

    const handleOpenHouse = (house: GloryHouse) => {
        setSelectedHouse(house);
        setIsDrawerOpen(true);
    };

    return (
        <div className="flex flex-col h-full bg-white dark:bg-[#1e1f21] overflow-hidden">
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
                    <button className="flex items-center gap-2 px-3 py-1.5 bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 rounded-md text-[11px] font-bold hover:bg-blue-100 dark:hover:bg-blue-900/30 transition-all shadow-sm">
                        <Map size={14} /> Ver Mapa
                    </button>
                }
            />

            <main className="flex-1 overflow-y-auto scrollbar-thin">
                {/* ─── Error state ─── */}
                {error && (
                    <div className="m-6 p-4 bg-rose-50 dark:bg-rose-900/20 border border-rose-200 dark:border-rose-500/20 rounded-2xl flex items-center gap-3 text-rose-700 dark:text-rose-400">
                        <AlertCircle size={18} />
                        <p className="text-sm font-bold">{error}</p>
                    </div>
                )}

                {viewType === 'grid' ? (
                    <div className="p-4 lg:p-6 space-y-6">
                        {/* ─── Stats from real data ─── */}
                        <section className="grid grid-cols-2 md:grid-cols-4 gap-4">
                            <MetricCard
                                title="Total Casas"
                                value={loading ? '...' : houses.length.toString()}
                                trend={houses.length > 0 ? `${houses.length} registradas` : 'Sin datos'}
                                icon={Home}
                                tone="blue"
                            />
                            <MetricCard
                                title="Miembros Totales"
                                value={loading ? '...' : totalMembers.toString()}
                                trend={totalMembers > 0 ? 'En comunidad' : 'Sin datos'}
                                icon={Users}
                                tone="emerald"
                            />
                            <MetricCard
                                title="Zonas Cubiertas"
                                value={loading ? '...' : uniqueZones.toString()}
                                trend={uniqueZones > 0 ? 'Zonas activas' : 'Sin datos'}
                                icon={MapPin}
                                tone="indigo"
                            />
                            <MetricCard
                                title="Ocup. Promedio"
                                value={loading ? '...' : `${avgOccupancyPct}%`}
                                trend={saturatedCount > 0 ? `${saturatedCount} saturadas` : 'Sin saturación'}
                                icon={TrendingUp}
                                tone={avgOccupancyPct >= 90 ? 'rose' : avgOccupancyPct >= 70 ? 'amber' : 'emerald'}
                            />
                        </section>

                        {/* ─── Loading skeleton ─── */}
                        {loading && (
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                                {[...Array(8)].map((_, i) => (
                                    <div key={i} className="h-44 bg-slate-100 dark:bg-white/5 rounded-2xl animate-pulse" />
                                ))}
                            </div>
                        )}

                        {/* ─── Empty state ─── */}
                        {!loading && filtered.length === 0 && !error && (
                            <div className="flex flex-col items-center justify-center py-24 gap-4 text-center">
                                <Home size={44} className="text-slate-200 dark:text-white/10" />
                                <p className="font-black text-slate-500 dark:text-slate-400">
                                    {search ? 'Sin resultados' : 'No hay casas registradas'}
                                </p>
                                <p className="text-sm text-slate-400">
                                    {search ? 'Intenta con otro término de búsqueda' : 'Las casas de bendición aparecerán aquí'}
                                </p>
                            </div>
                        )}

                        {/* ─── Grid cards ─── */}
                        {!loading && filtered.length > 0 && (
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                                {filtered.map(house => (
                                    <div
                                        key={house.id}
                                        onClick={() => handleOpenHouse(house)}
                                        className="p-5 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/5 rounded-2xl shadow-sm hover:shadow-xl hover:border-blue-500/30 hover:-translate-y-0.5 transition-all cursor-pointer group relative overflow-hidden active:scale-95"
                                    >
                                        {/* Header: zone + member count */}
                                        <div className="flex items-center justify-between mb-4">
                                            <div className="px-2 py-0.5 bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 text-[8px] font-black uppercase rounded-lg tracking-widest">
                                                {house.zone}
                                            </div>
                                            <div className="flex items-center gap-1 text-[10px] font-bold text-slate-400">
                                                <Users size={11} /> {house.members_count}
                                                {house.capacity > 0 && (
                                                    <span className="text-slate-300">/{house.capacity}</span>
                                                )}
                                            </div>
                                        </div>

                                        {/* Name */}
                                        <h3 className="text-[15px] font-bold text-slate-800 dark:text-white mb-3 line-clamp-2 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                                            {house.name}
                                        </h3>

                                        {/* Meta */}
                                        <div className="space-y-1.5 mb-4">
                                            <div className="flex items-center gap-2 text-[11px] text-slate-500 dark:text-slate-400 font-medium">
                                                <User size={11} className="text-slate-300 shrink-0" />
                                                <span className="truncate">{house.leader_name || 'Sin líder asignado'}</span>
                                            </div>
                                            <div className="flex items-center gap-2 text-[11px] text-slate-500 dark:text-slate-400 font-medium">
                                                <Clock size={11} className="text-slate-300 shrink-0" />
                                                <span className="truncate">{house.schedule || 'Horario no definido'}</span>
                                            </div>
                                            {house.address && (
                                                <div className="flex items-center gap-2 text-[11px] text-slate-400 font-medium">
                                                    <MapPin size={11} className="text-slate-300 shrink-0" />
                                                    <span className="truncate">{house.address}</span>
                                                </div>
                                            )}
                                        </div>

                                        {/* Footer */}
                                        <div className="pt-3 border-t border-slate-50 dark:border-white/5 flex justify-between items-center">
                                            <span className="text-[10px] font-black text-blue-500 uppercase tracking-widest opacity-0 group-hover:opacity-100 transition-opacity">
                                                Ver Detalles
                                            </span>
                                            <ChevronRight size={14} className="text-slate-300 group-hover:text-blue-500 group-hover:translate-x-0.5 transition-all" />
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                ) : (
                    /* ─── Table View ─── */
                    <div className="overflow-x-auto">
                        <table className="w-full text-left border-collapse table-fixed min-w-[900px]">
                            <thead className="sticky top-0 z-20 bg-slate-50 dark:bg-[#1e1f21] border-b border-slate-200 dark:border-white/5">
                                <tr className="h-10">
                                    <th className="px-6 text-[10px] font-black text-slate-400 uppercase tracking-widest w-12 text-center">#</th>
                                    <th className="px-6 text-[10px] font-black text-slate-400 uppercase tracking-widest w-[30%]">Casa / Nombre</th>
                                    <th className="px-6 text-[10px] font-black text-slate-400 uppercase tracking-widest">Zona</th>
                                    <th className="px-6 text-[10px] font-black text-slate-400 uppercase tracking-widest">Líder</th>
                                    <th className="px-6 text-[10px] font-black text-slate-400 uppercase tracking-widest">Horario</th>
                                    <th className="px-6 text-[10px] font-black text-slate-400 uppercase tracking-widest text-center w-24">Miembros</th>
                                    <th className="px-6 text-[10px] font-black text-slate-400 uppercase tracking-widest text-right w-24">Acciones</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100 dark:divide-white/5">
                                {loading && (
                                    [...Array(6)].map((_, i) => (
                                        <tr key={i} className="h-12">
                                            {[...Array(7)].map((_, j) => (
                                                <td key={j} className="px-6 py-3">
                                                    <div className="h-3 bg-slate-100 dark:bg-white/5 rounded animate-pulse" />
                                                </td>
                                            ))}
                                        </tr>
                                    ))
                                )}
                                {!loading && filtered.map(house => (
                                    <tr
                                        key={house.id}
                                        onClick={() => handleOpenHouse(house)}
                                        className="hover:bg-blue-50/50 dark:hover:bg-blue-500/5 transition-colors group cursor-pointer h-12"
                                    >
                                        <td className="px-6 text-center text-[11px] font-bold text-slate-400">#{house.id}</td>
                                        <td className="px-6">
                                            <span className="text-[13px] font-bold text-slate-700 dark:text-slate-200 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                                                {house.name}
                                            </span>
                                        </td>
                                        <td className="px-6">
                                            <div className="flex items-center gap-2">
                                                <MapPin size={11} className="text-slate-300 shrink-0" />
                                                <span className="text-[12px] font-medium text-slate-500">{house.zone || '—'}</span>
                                            </div>
                                        </td>
                                        <td className="px-6">
                                            {house.leader_name ? (
                                                <div className="flex items-center gap-2">
                                                    <div className="size-6 rounded-full bg-slate-900 dark:bg-blue-600 flex items-center justify-center text-[9px] font-black text-white shrink-0">
                                                        {safeInitials(house.leader_name)}
                                                    </div>
                                                    <span className="text-[12px] font-bold text-slate-600 dark:text-slate-300 truncate">
                                                        {house.leader_name}
                                                    </span>
                                                </div>
                                            ) : (
                                                <span className="text-[11px] text-slate-400 italic">Sin asignar</span>
                                            )}
                                        </td>
                                        <td className="px-6">
                                            <div className="flex items-center gap-2">
                                                <Clock size={11} className="text-slate-300 shrink-0" />
                                                <span className="text-[12px] font-medium text-slate-500">{house.schedule || '—'}</span>
                                            </div>
                                        </td>
                                        <td className="px-6 text-center">
                                            <span className="text-[13px] font-black text-slate-700 dark:text-slate-200">
                                                {house.members_count}
                                                {house.capacity > 0 && (
                                                    <span className="text-slate-400 font-medium">/{house.capacity}</span>
                                                )}
                                            </span>
                                        </td>
                                        <td className="px-6 text-right">
                                            <div className="opacity-0 group-hover:opacity-100 transition-opacity flex justify-end gap-1">
                                                <button className="p-1.5 hover:bg-slate-200 dark:hover:bg-white/10 rounded-md text-slate-400"><Edit3 size={13} /></button>
                                                <button className="p-1.5 hover:bg-slate-200 dark:hover:bg-white/10 rounded-md text-slate-400"><MoreHorizontal size={13} /></button>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                                {!loading && filtered.length === 0 && (
                                    <tr>
                                        <td colSpan={7} className="py-20 text-center">
                                            <p className="text-sm font-bold text-slate-400">
                                                {search ? 'Sin resultados para tu búsqueda' : 'No hay casas registradas'}
                                            </p>
                                        </td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </div>
                )}
            </main>

            {/* ─── Detail Drawer ─── */}
            <WorkspaceDrawer
                isOpen={isDrawerOpen}
                onClose={() => setIsDrawerOpen(false)}
                title={selectedHouse?.name || 'Detalles de la Casa'}
                subtitle={`${selectedHouse?.zone || 'CCF'} · Casa de Bendición`}
                actions={
                    <>
                        <button
                            onClick={() => setIsDrawerOpen(false)}
                            className="px-4 py-2 text-[11px] font-bold text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 transition-colors"
                        >
                            Cerrar
                        </button>
                        <button className="px-6 py-2 bg-blue-600 text-white rounded-lg text-[11px] font-bold shadow-lg shadow-blue-500/20 active:scale-95 transition-all hover:bg-blue-700">
                            Registrar Asistencia
                        </button>
                    </>
                }
            >
                {selectedHouse && (
                    <div className="space-y-8">
                        {/* Info grid */}
                        <section className="grid grid-cols-2 gap-3">
                            <HouseStat label="Líder" value={selectedHouse.leader_name || 'No asignado'} icon={User} />
                            <HouseStat label="Horario" value={selectedHouse.schedule || 'No definido'} icon={Clock} />
                            <HouseStat label="Miembros" value={`${selectedHouse.members_count}${selectedHouse.capacity > 0 ? ` / ${selectedHouse.capacity}` : ''}`} icon={Users} />
                            <HouseStat label="Zona" value={selectedHouse.zone} icon={MapPin} />
                            {selectedHouse.address && (
                                <div className="col-span-2">
                                    <HouseStat label="Dirección" value={selectedHouse.address} icon={MapPin} />
                                </div>
                            )}
                        </section>

                        {/* Contact Info */}
                        <section className="space-y-3">
                            <div className="flex items-center gap-2">
                                <Hash size={13} className="text-blue-500" />
                                <h4 className="text-[11px] font-black text-slate-400 uppercase tracking-widest">Contacto del Líder</h4>
                            </div>
                            <div className="space-y-2">
                                {selectedHouse.phone ? (
                                    <div className="flex items-center gap-3 p-3 bg-slate-50 dark:bg-white/5 rounded-xl border border-slate-100 dark:border-white/5">
                                        <Phone size={13} className="text-slate-400 shrink-0" />
                                        <span className="text-[12px] font-bold text-slate-700 dark:text-slate-200">{selectedHouse.phone}</span>
                                    </div>
                                ) : (
                                    <div className="flex items-center gap-3 p-3 bg-slate-50 dark:bg-white/5 rounded-xl border border-slate-100 dark:border-white/5">
                                        <Phone size={13} className="text-slate-300 shrink-0" />
                                        <span className="text-[12px] text-slate-400 italic">Teléfono no registrado</span>
                                    </div>
                                )}
                                <div className="flex items-center gap-3 p-3 bg-slate-50 dark:bg-white/5 rounded-xl border border-slate-100 dark:border-white/5">
                                    <Mail size={13} className="text-slate-400 shrink-0" />
                                    <span className="text-[12px] font-bold text-slate-700 dark:text-slate-200">
                                        {selectedHouse.email || safeEmail(selectedHouse.leader_name)}
                                    </span>
                                </div>
                            </div>
                        </section>

                        {/* Attendance history — empty state since no API data */}
                        <section className="space-y-4 pt-6 border-t border-slate-100 dark:border-white/5">
                            <h4 className="text-[11px] font-black text-slate-400 uppercase tracking-widest flex items-center gap-2">
                                <History size={13} className="text-blue-500" /> Reportes de Asistencia
                            </h4>
                            <div className="flex flex-col items-center justify-center py-10 gap-3 text-center bg-slate-50 dark:bg-white/5 rounded-2xl border border-dashed border-slate-200 dark:border-white/10">
                                <CheckCircle size={32} className="text-slate-200 dark:text-white/10" />
                                <p className="text-sm font-black text-slate-400">Sin reportes registrados</p>
                                <p className="text-[11px] text-slate-400">Los reportes de asistencia de {selectedHouse.name} aparecerán aquí</p>
                                <button className="mt-1 px-4 py-2 text-[10px] font-black uppercase tracking-widest text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20 rounded-xl hover:bg-blue-100 dark:hover:bg-blue-900/30 transition-all">
                                    Registrar primer reporte
                                </button>
                            </div>
                        </section>
                    </div>
                )}
            </WorkspaceDrawer>
        </div>
    );
}
