'use client';

import React, { useState, useEffect } from 'react';
import { Home, MapPin, Users, Heart, Search, Loader2, Plus, X, Check, Zap, Map, Navigation, Grid3x3 } from 'lucide-react';
import { apiFetch } from '@/lib/http';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import CrmShell from '@/components/crm/CrmShell';
import AdminHero from '@/components/admin/AdminHero';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import { ViewType, getStoredView } from '@/components/ViewSwitcher';

interface GloryHouse {
    id: number;
    name: string;
    zone: string;
    address: string;
    latitude?: number;
    longitude?: number;
    leader_name: string;
    members_count: number;
    capacity: number;
    status: string;
    schedule: string;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function getSaturationTone(sat: number) {
    if (sat >= 1.0) return 'rose';
    if (sat >= 0.7) return 'amber';
    return 'emerald';
}

const TONE_STYLES = {
    rose:    { bar: 'bg-rose-500',    badge: 'bg-rose-50 dark:bg-rose-500/10 text-rose-600 dark:text-rose-400',    pulse: '244,63,94'   },
    amber:   { bar: 'bg-amber-500',   badge: 'bg-amber-50 dark:bg-amber-500/10 text-amber-600 dark:text-amber-400', pulse: '245,158,11'  },
    emerald: { bar: 'bg-emerald-500', badge: 'bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400', pulse: '16,185,129' },
};

function SatBar({ sat }: { sat: number }) {
    const tone = getSaturationTone(sat);
    const pct = Math.min(100, Math.round(sat * 100));
    return (
        <div>
            <div className="flex justify-between items-end mb-1.5">
                <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Ocupación</p>
                <span className={clsx('px-2 py-0.5 rounded text-[8px] font-black uppercase tracking-widest', TONE_STYLES[tone].badge)}>
                    {pct}% Sat.
                </span>
            </div>
            <p className="text-xl font-black text-slate-800 dark:text-white tracking-tight mb-2">
                {sat !== undefined ? Math.round(sat * (0)) : 0}
                <span className="text-sm text-slate-400"> / —</span>
            </p>
        </div>
    );
}

// ─── Main Component ───────────────────────────────────────────────────────────

export default function GroupsPage() {
    const [groups, setGroups] = useState<GloryHouse[]>([]);
    const [loading, setLoading] = useState(true);
    const [viewMode, setViewMode] = useState<'grid' | 'map'>(
        () => (getStoredView('crm_groups_view', 'grid') === 'grid' ? 'grid' : 'map')
    );
    const ALL_VIEWS: ViewType[] = ['table', 'list', 'grid', 'board', 'kanban', 'gantt', 'calendar'];
    const crmViewType: ViewType = viewMode === 'grid' ? 'grid' : 'board';
    const handleViewChange = (v: ViewType) => setViewMode(v === 'grid' ? 'grid' : 'map');

    const [showCreateModal, setShowCreateModal] = useState(false);
    const { token } = useAuth();
    const { addToast } = useToast();

    const [newHouse, setNewHouse] = useState({
        name: '', zone: '', address: '', leader_name: '', capacity: 15, latitude: '', longitude: ''
    });
    const [submitting, setSubmitting] = useState(false);
    const [searchTerm, setSearchTerm] = useState('');

    const filteredGroups = groups.filter(g =>
        g.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        g.zone?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        g.leader_name?.toLowerCase().includes(searchTerm.toLowerCase())
    );

    const fetchHouses = async () => {
        if (!token) return;
        setLoading(true);
        try {
            const data = await apiFetch<GloryHouse[]>('/crm/glory-houses', { token, cache: 'no-store' });
            setGroups(Array.isArray(data) ? data : []);
        } catch (err) {
            console.error(err);
            addToast("Error al cargar casas", "error");
        } finally {
            setLoading(false);
        }
    };

    const handleCreateHouse = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!newHouse.name || !newHouse.zone) return;
        setSubmitting(true);
        try {
            await apiFetch('/crm/glory-houses', {
                method: 'POST',
                token,
                body: {
                    ...newHouse,
                    latitude: newHouse.latitude ? parseFloat(newHouse.latitude) : null,
                    longitude: newHouse.longitude ? parseFloat(newHouse.longitude) : null,
                    capacity: parseInt(newHouse.capacity.toString())
                }
            });
            addToast("Casa de Gloria aperturada", "success");
            setShowCreateModal(false);
            setNewHouse({ name: '', zone: '', address: '', leader_name: '', capacity: 15, latitude: '', longitude: '' });
            fetchHouses();
        } catch {
            addToast("Error al crear casa", "error");
        } finally {
            setSubmitting(false);
        }
    };

    // Close modal on Escape
    useEffect(() => {
        const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') setShowCreateModal(false); };
        window.addEventListener('keydown', handler);
        return () => window.removeEventListener('keydown', handler);
    }, []);

    useEffect(() => { fetchHouses(); }, [token]);

    return (
        <CrmShell
            breadcrumbs={[
                { label: 'CRM Pastoral', icon: Users },
                { label: 'Casas de Gloria', icon: Home }
            ]}
            viewOptions={ALL_VIEWS}
            viewType={crmViewType}
            onViewChange={handleViewChange}
            rightActions={
                <button
                    onClick={() => setShowCreateModal(true)}
                    className="flex items-center gap-2 bg-blue-600 px-5 py-2 rounded-xl text-[11px] font-black text-white hover:bg-blue-700 transition-all shadow-lg shadow-blue-900/20 uppercase tracking-widest"
                >
                    <Plus size={14} /> Nueva Casa
                </button>
            }
        >
        <div className="space-y-8 pb-20">
            {/* ─── AdminHero ─── */}
            <AdminHero
                eyebrow="Red Geográfica"
                title="Casas de Gloria"
                description="Mapea y administra los grupos que sostienen el discipulado en los barrios. Optimus Brain detecta zonas sin cobertura."
                tags={['Mapas', 'Discipulado', 'Clustering']}
                watchers={['Equipo Casas', 'Optimus Brain']}
                primaryAction={{ label: 'Nueva casa', icon: Plus, onClick: () => setShowCreateModal(true) }}
                secondaryAction={{
                    label: viewMode === 'grid' ? 'Vista Satelital' : 'Ver Cuadrícula',
                    icon: viewMode === 'grid' ? Map : Navigation,
                    onClick: () => setViewMode(viewMode === 'grid' ? 'map' : 'grid')
                }}
            />

            {/* ─── Toolbar: Search + Toggle ─── */}
            <div className="flex flex-col md:flex-row gap-4 items-center justify-between">
                <div className="relative flex-1 w-full max-w-2xl group">
                    <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-blue-600 transition-colors" size={18} />
                    <input
                        type="text"
                        placeholder="Buscar por zona, nombre o líder..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="w-full bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-[2rem] py-3.5 pl-12 pr-4 focus:outline-none focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 transition-all text-sm font-bold shadow-sm dark:text-white placeholder:text-slate-400"
                    />
                </div>
                <div className="flex gap-1 bg-slate-100 dark:bg-white/5 p-1 rounded-2xl border border-slate-200 dark:border-white/10">
                    <button
                        onClick={() => setViewMode('grid')}
                        className={clsx(
                            'flex items-center gap-2 px-6 py-2.5 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all',
                            viewMode === 'grid'
                                ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/20'
                                : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
                        )}
                    >
                        <Grid3x3 size={12} /> Cuadrícula
                    </button>
                    <button
                        onClick={() => setViewMode('map')}
                        className={clsx(
                            'flex items-center gap-2 px-6 py-2.5 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all',
                            viewMode === 'map'
                                ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/20'
                                : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
                        )}
                    >
                        <Map size={12} /> Mapa de Calor
                    </button>
                </div>
            </div>

            {/* ─── Main Content ─── */}
            <AnimatePresence mode="wait">
                {loading ? (
                    <motion.div key="loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                        className="flex flex-col items-center justify-center py-40 gap-6"
                    >
                        <Loader2 className="animate-spin text-blue-600" size={48} strokeWidth={1.5} />
                        <p className="text-[10px] font-black uppercase tracking-[0.5em] text-slate-400 animate-pulse">
                            Sincronizando Nodos Geo-Pastorales...
                        </p>
                    </motion.div>
                ) : viewMode === 'grid' ? (
                    <motion.div
                        key="grid"
                        initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }}
                        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6"
                    >
                        {filteredGroups.length === 0 && !loading && (
                            <div className="col-span-4 py-20 text-center">
                                <Home size={48} className="mx-auto text-slate-300 mb-4" />
                                <p className="text-lg font-black text-slate-500 dark:text-slate-400">
                                    {searchTerm ? 'Sin resultados para tu búsqueda' : 'No hay casas registradas aún'}
                                </p>
                                <p className="text-sm text-slate-400 mt-1">
                                    {searchTerm ? 'Intenta con otro término' : 'Apertura la primera casa de gloria'}
                                </p>
                            </div>
                        )}

                        {filteredGroups.map((group, i) => {
                            const sat = group.capacity > 0 ? (group.members_count / group.capacity) : 0;
                            const tone = getSaturationTone(sat);
                            const pct = Math.min(100, Math.round(sat * 100));
                            const displayPct = Math.round(sat * 100); // real %, can exceed 100

                            return (
                                <motion.div
                                    key={group.id}
                                    initial={{ opacity: 0, scale: 0.95 }}
                                    animate={{ opacity: 1, scale: 1 }}
                                    transition={{ delay: i * 0.04 }}
                                    className="bg-white dark:bg-[#1e1f21] p-8 rounded-[3rem] border border-slate-100 dark:border-white/5 hover:shadow-2xl hover:shadow-slate-200/30 dark:hover:shadow-none hover:-translate-y-1 transition-all duration-500 group overflow-hidden relative cursor-pointer"
                                >
                                    {/* BG watermark */}
                                    <div className="absolute top-0 right-0 p-6 opacity-[0.03] group-hover:opacity-[0.07] group-hover:rotate-12 transition-all duration-700 pointer-events-none">
                                        <Home size={100} />
                                    </div>

                                    {/* Zone + Status */}
                                    <div className="flex justify-between items-start mb-6 relative z-10">
                                        <span className="px-3 py-1.5 bg-slate-50 dark:bg-white/5 text-slate-600 dark:text-slate-300 text-[9px] font-black uppercase tracking-[0.15em] rounded-xl flex items-center gap-1.5 border border-slate-200 dark:border-white/10">
                                            <MapPin size={10} /> {group.zone || 'Sin Zona'}
                                        </span>
                                        <div className="flex items-center gap-1.5">
                                            <div className={clsx(
                                                'size-2 rounded-full',
                                                group.status === 'Activo' ? 'bg-emerald-500 shadow-[0_0_6px_#10b981] animate-pulse' : 'bg-slate-300'
                                            )} />
                                            <span className="text-[9px] font-black text-slate-400 uppercase tracking-widest">
                                                {group.status || 'Activo'}
                                            </span>
                                        </div>
                                    </div>

                                    {/* Name + Leader */}
                                    <div className="relative z-10 mb-6">
                                        <h3 className="text-xl font-black text-slate-900 dark:text-white tracking-tighter leading-none mb-2 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors line-clamp-2">
                                            {group.name}
                                        </h3>
                                        <p className="text-[11px] font-bold text-slate-500 uppercase tracking-widest flex items-center gap-1.5">
                                            <Users size={11} /> {group.leader_name || 'Sin líder asignado'}
                                        </p>
                                        {group.address && (
                                            <p className="text-[10px] text-slate-400 mt-1 flex items-center gap-1.5">
                                                <MapPin size={10} /> {group.address}
                                            </p>
                                        )}
                                    </div>

                                    {/* Saturation bar */}
                                    <div className="space-y-2 pt-5 border-t border-slate-100 dark:border-white/5 relative z-10">
                                        <div className="flex justify-between items-center">
                                            <div>
                                                <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-0.5">Ocupación</p>
                                                <p className="text-lg font-black text-slate-800 dark:text-white">
                                                    {group.members_count} <span className="text-sm text-slate-400 font-bold">/ {group.capacity}</span>
                                                </p>
                                            </div>
                                            <span className={clsx('px-2.5 py-1 rounded-lg text-[9px] font-black uppercase tracking-widest', TONE_STYLES[tone].badge)}>
                                                {displayPct}%
                                            </span>
                                        </div>
                                        <div className="h-1.5 w-full bg-slate-100 dark:bg-white/10 rounded-full overflow-hidden">
                                            <motion.div
                                                initial={{ width: 0 }}
                                                animate={{ width: `${pct}%` }}
                                                transition={{ duration: 0.8, ease: 'easeOut', delay: i * 0.04 }}
                                                className={clsx('h-full rounded-full', TONE_STYLES[tone].bar, tone === 'rose' && 'shadow-[0_0_8px_rgba(244,63,94,0.5)]')}
                                            />
                                        </div>
                                    </div>
                                </motion.div>
                            );
                        })}

                        {/* Add New Card */}
                        <motion.div
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            transition={{ delay: filteredGroups.length * 0.04 }}
                            onClick={() => setShowCreateModal(true)}
                            className="bg-slate-50/50 dark:bg-white/5 border-2 border-dashed border-slate-200 dark:border-white/10 hover:border-blue-400 hover:bg-blue-50/50 dark:hover:bg-blue-900/10 transition-all duration-300 cursor-pointer flex flex-col items-center justify-center p-8 text-center min-h-[280px] rounded-[3rem] group"
                        >
                            <div className="size-16 bg-white dark:bg-[#1e1f21] rounded-[2rem] flex items-center justify-center shadow-md mb-5 text-slate-300 dark:text-slate-600 group-hover:text-blue-600 group-hover:scale-110 group-hover:rotate-90 transition-all duration-500">
                                <Plus size={32} strokeWidth={1.5} />
                            </div>
                            <h3 className="text-base font-black text-slate-600 dark:text-slate-400 uppercase tracking-tight group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                                Plantación Estratégica
                            </h3>
                            <p className="text-[10px] font-bold text-slate-400 mt-1.5 uppercase tracking-[0.15em] max-w-[180px] leading-relaxed">
                                Establecer un nuevo nodo ministerial
                            </p>
                        </motion.div>
                    </motion.div>
                ) : (
                    /* ─── MAP VIEW ─── */
                    <motion.div
                        key="map"
                        initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.98 }}
                        className="relative bg-slate-900 rounded-[3rem] overflow-hidden shadow-2xl border border-slate-800"
                        style={{ height: 680 }}
                    >
                        {/* Grid overlay */}
                        <div className="absolute inset-0 opacity-30" style={{
                            backgroundImage: `url("data:image/svg+xml,%3Csvg width='100%25' height='100%25' xmlns='http://www.w3.org/2000/svg'%3E%3Cdefs%3E%3Cpattern id='grid' width='40' height='40' patternUnits='userSpaceOnUse'%3E%3Cpath d='M 40 0 L 0 0 0 40' fill='none' stroke='rgba(255,255,255,0.08)' stroke-width='1'/%3E%3C/pattern%3E%3C/defs%3E%3Crect width='100%25' height='100%25' fill='url(%23grid)'/%3E%3C/svg%3E")`
                        }} />

                        {/* Heatmap blobs */}
                        <div className="absolute top-[15%] left-[28%] size-[380px] rounded-full opacity-50 mix-blend-screen animate-pulse"
                            style={{ background: 'radial-gradient(circle, rgba(244,63,94,0.18) 0%, transparent 70%)', animationDuration: '4s' }} />
                        <div className="absolute bottom-[18%] right-[22%] size-[280px] rounded-full opacity-35 mix-blend-screen animate-pulse"
                            style={{ background: 'radial-gradient(circle, rgba(59,130,246,0.15) 0%, transparent 70%)', animationDuration: '6s' }} />
                        <div className="absolute top-[45%] right-[35%] size-[200px] rounded-full opacity-40 mix-blend-screen animate-pulse"
                            style={{ background: 'radial-gradient(circle, rgba(16,185,129,0.15) 0%, transparent 70%)', animationDuration: '5s' }} />

                        {/* Real nodes (if lat/lon available) */}
                        {groups.filter(g => g.latitude && g.longitude).map((g, i) => {
                            const sat = g.capacity > 0 ? g.members_count / g.capacity : 0;
                            const tone = getSaturationTone(sat);
                            const pulseColor = TONE_STYLES[tone].pulse;
                            const top = `${25 + (i % 4) * 14}%`;
                            const left = `${20 + (i % 5) * 13}%`;
                            return (
                                <div key={g.id} className="absolute group cursor-crosshair z-10" style={{ top, left, transform: 'translate(-50%,-50%)' }}>
                                    <div className="absolute inset-0 size-8 -ml-4 -mt-4 rounded-full animate-ping opacity-30" style={{ backgroundColor: `rgb(${pulseColor})` }} />
                                    <div className="relative size-5 -ml-2.5 -mt-2.5 rounded-full border-[3px] bg-white shadow-[0_0_15px_rgba(255,255,255,0.6)]" style={{ borderColor: `rgb(${pulseColor})` }}>
                                        <div className="absolute inset-1 rounded-full" style={{ backgroundColor: `rgb(${pulseColor})` }} />
                                    </div>
                                    <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-4 w-52 p-4 bg-white/10 backdrop-blur-xl border border-white/20 rounded-2xl shadow-2xl opacity-0 group-hover:opacity-100 pointer-events-none transition-all duration-200 scale-95 group-hover:scale-100 origin-bottom">
                                        <p className="text-[10px] font-black text-white uppercase tracking-widest truncate">{g.name}</p>
                                        <p className="text-[9px] text-white/70 font-bold mb-2">{g.zone}</p>
                                        <div className="flex justify-between items-center text-white">
                                            <span className="flex items-center gap-1 text-[10px] font-black"><Users size={10} className="opacity-70" /> {g.members_count}/{g.capacity}</span>
                                            <span className="text-[8px] font-black px-1.5 py-0.5 rounded bg-white/20">{Math.round(sat * 100)}%</span>
                                        </div>
                                    </div>
                                </div>
                            );
                        })}

                        {/* Simulated nodes (when no lat/lon) */}
                        {groups.filter(g => !g.latitude).slice(0, 6).map((g, i) => {
                            const sat = g.capacity > 0 ? g.members_count / g.capacity : 0;
                            const tone = getSaturationTone(sat);
                            const pulseColor = TONE_STYLES[tone].pulse;
                            const positions = [
                                { top: '30%', left: '35%' }, { top: '25%', left: '60%' },
                                { top: '55%', left: '45%' }, { top: '45%', left: '70%' },
                                { top: '65%', left: '30%' }, { top: '40%', left: '20%' },
                            ];
                            const pos = positions[i] ?? { top: `${30 + i * 8}%`, left: `${30 + i * 10}%` };
                            return (
                                <div key={g.id} className="absolute group cursor-crosshair z-10" style={{ ...pos, transform: 'translate(-50%,-50%)' }}>
                                    <div className="absolute size-8 -ml-4 -mt-4 rounded-full animate-ping opacity-20" style={{ backgroundColor: `rgb(${pulseColor})` }} />
                                    <div className="relative size-4 -ml-2 -mt-2 rounded-full border-[3px] bg-white shadow-lg" style={{ borderColor: `rgb(${pulseColor})` }}>
                                        <div className="absolute inset-1 rounded-full" style={{ backgroundColor: `rgb(${pulseColor})` }} />
                                    </div>
                                    <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-3 w-48 p-3.5 bg-white/10 backdrop-blur-xl border border-white/20 rounded-2xl shadow-2xl opacity-0 group-hover:opacity-100 pointer-events-none transition-all duration-200 scale-95 group-hover:scale-100 origin-bottom">
                                        <p className="text-[10px] font-black text-white uppercase tracking-widest truncate">{g.name}</p>
                                        <p className="text-[9px] text-white/60 font-bold mb-1.5">{g.zone} · {g.leader_name}</p>
                                        <div className="flex justify-between text-white">
                                            <span className="text-[10px] font-black">{g.members_count}/{g.capacity}</span>
                                            <span className="text-[8px] font-black px-1.5 py-0.5 rounded" style={{ backgroundColor: `rgba(${pulseColor},0.3)` }}>{Math.round(sat * 100)}%</span>
                                        </div>
                                    </div>
                                </div>
                            );
                        })}

                        {/* Empty state overlay when no groups at all */}
                        {groups.length === 0 && (
                            <div className="absolute inset-0 flex items-center justify-center">
                                <div className="text-center space-y-3">
                                    <Map size={48} className="mx-auto text-white/20" />
                                    <p className="text-white/40 font-black uppercase tracking-widest text-sm">Sin datos de casas</p>
                                </div>
                            </div>
                        )}

                        {/* AI Insight Overlay */}
                        <div className="absolute bottom-8 left-8 p-7 bg-black/50 backdrop-blur-2xl border border-white/10 rounded-[2rem] shadow-2xl max-w-[320px]">
                            <div className="flex items-center gap-2.5 mb-3 text-blue-400">
                                <Zap size={18} className="animate-pulse" fill="currentColor" />
                                <h3 className="text-[10px] font-black uppercase tracking-[0.3em]">Optimus Clusters</h3>
                            </div>
                            <p className="text-sm text-white/75 font-medium leading-relaxed mb-4">
                                Alta concentración sin cobertura en <span className="font-bold text-white">Zona Sur (Sector 4)</span>. Se recomienda aperturar una nueva célula.
                            </p>
                            <div className="flex gap-4">
                                <div className="flex items-center gap-1.5"><div className="size-2 bg-rose-500 rounded-full shadow-[0_0_6px_#f43f5e]" /><span className="text-[9px] text-white/50 font-black uppercase tracking-widest">Saturado</span></div>
                                <div className="flex items-center gap-1.5"><div className="size-2 bg-amber-500 rounded-full shadow-[0_0_6px_#f59e0b]" /><span className="text-[9px] text-white/50 font-black uppercase tracking-widest">Alertado</span></div>
                                <div className="flex items-center gap-1.5"><div className="size-2 bg-emerald-500 rounded-full shadow-[0_0_6px_#10b981]" /><span className="text-[9px] text-white/50 font-black uppercase tracking-widest">Óptimo</span></div>
                            </div>
                        </div>

                        {/* Stats top-right */}
                        <div className="absolute top-6 right-6 flex flex-col gap-2">
                            {[
                                { label: 'Casas Activas', value: groups.filter(g => g.status !== 'Inactivo').length, color: 'text-emerald-400' },
                                { label: 'Saturadas', value: groups.filter(g => g.capacity > 0 && g.members_count / g.capacity >= 1).length, color: 'text-rose-400' },
                            ].map(stat => (
                                <div key={stat.label} className="px-4 py-2.5 bg-black/40 backdrop-blur border border-white/10 rounded-2xl flex items-center gap-3">
                                    <p className={clsx('text-xl font-black', stat.color)}>{stat.value}</p>
                                    <p className="text-[9px] font-black text-white/50 uppercase tracking-widest">{stat.label}</p>
                                </div>
                            ))}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>

        {/* ─── Create Modal ─── */}
        <AnimatePresence>
            {showCreateModal && (
                <motion.div
                    initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                    className="fixed inset-0 z-[200] flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-md"
                    onClick={(e) => { if (e.target === e.currentTarget) setShowCreateModal(false); }}
                >
                    <motion.div
                        initial={{ opacity: 0, scale: 0.95, y: 16 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.95, y: 16 }}
                        transition={{ duration: 0.2 }}
                        className="w-full max-w-xl bg-white dark:bg-[#1e1f21] rounded-[2.5rem] shadow-2xl border border-slate-100 dark:border-white/10 overflow-hidden"
                    >
                        {/* Modal Header */}
                        <div className="px-10 py-7 border-b border-slate-100 dark:border-white/10 flex justify-between items-center">
                            <div>
                                <h2 className="text-xl font-black text-slate-900 dark:text-white flex items-center gap-3">
                                    <MapPin size={20} className="text-blue-600" /> Aperturar Casa
                                </h2>
                                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-[0.2em] mt-1">
                                    Configuración geográfica y liderazgo
                                </p>
                            </div>
                            <button
                                onClick={() => setShowCreateModal(false)}
                                className="p-2.5 rounded-xl bg-slate-100 dark:bg-white/10 text-slate-500 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-white/20 hover:text-slate-800 dark:hover:text-white transition-all"
                            >
                                <X size={18} />
                            </button>
                        </div>

                        {/* Modal Form */}
                        <form onSubmit={handleCreateHouse} className="p-10 space-y-5">
                            <div className="grid grid-cols-2 gap-5">
                                <div className="space-y-1.5">
                                    <label className="text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest">Nombre *</label>
                                    <input
                                        required
                                        value={newHouse.name}
                                        onChange={e => setNewHouse({ ...newHouse, name: e.target.value })}
                                        className="w-full px-4 py-3.5 rounded-2xl border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/5 focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 outline-none font-bold text-sm text-slate-800 dark:text-white transition-all placeholder:text-slate-400"
                                        placeholder="Casa de Paz Ebenezer"
                                    />
                                </div>
                                <div className="space-y-1.5">
                                    <label className="text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest">Zona *</label>
                                    <input
                                        required
                                        value={newHouse.zone}
                                        onChange={e => setNewHouse({ ...newHouse, zone: e.target.value })}
                                        className="w-full px-4 py-3.5 rounded-2xl border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/5 focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 outline-none font-bold text-sm text-slate-800 dark:text-white transition-all placeholder:text-slate-400"
                                        placeholder="Zona Norte"
                                    />
                                </div>
                            </div>

                            <div className="space-y-1.5">
                                <label className="text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest">Líder Asignado</label>
                                <input
                                    value={newHouse.leader_name}
                                    onChange={e => setNewHouse({ ...newHouse, leader_name: e.target.value })}
                                    className="w-full px-4 py-3.5 rounded-2xl border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/5 focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 outline-none font-bold text-sm text-slate-800 dark:text-white transition-all placeholder:text-slate-400"
                                    placeholder="Nombre del responsable"
                                />
                            </div>

                            <div className="space-y-1.5">
                                <label className="text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest">Dirección Física</label>
                                <input
                                    value={newHouse.address}
                                    onChange={e => setNewHouse({ ...newHouse, address: e.target.value })}
                                    className="w-full px-4 py-3.5 rounded-2xl border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/5 focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 outline-none font-bold text-sm text-slate-800 dark:text-white transition-all placeholder:text-slate-400"
                                    placeholder="Calle, número, ciudad"
                                />
                            </div>

                            <div className="grid grid-cols-3 gap-5">
                                <div className="space-y-1.5">
                                    <label className="text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest">Capacidad</label>
                                    <input
                                        type="number" min="1" max="100"
                                        value={newHouse.capacity}
                                        onChange={e => setNewHouse({ ...newHouse, capacity: Number(e.target.value) })}
                                        className="w-full px-4 py-3.5 rounded-2xl border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/5 focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 outline-none font-bold text-sm text-slate-800 dark:text-white transition-all"
                                    />
                                </div>
                                <div className="space-y-1.5">
                                    <label className="text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest flex items-center gap-1"><Map size={10} className="text-blue-500" /> Latitud</label>
                                    <input
                                        type="number" step="any"
                                        value={newHouse.latitude}
                                        onChange={e => setNewHouse({ ...newHouse, latitude: e.target.value })}
                                        className="w-full px-4 py-3.5 rounded-2xl border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/5 focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 outline-none font-mono font-bold text-sm text-slate-800 dark:text-white transition-all placeholder:text-slate-400"
                                        placeholder="0.000000"
                                    />
                                </div>
                                <div className="space-y-1.5">
                                    <label className="text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest flex items-center gap-1"><Map size={10} className="text-blue-500" /> Longitud</label>
                                    <input
                                        type="number" step="any"
                                        value={newHouse.longitude}
                                        onChange={e => setNewHouse({ ...newHouse, longitude: e.target.value })}
                                        className="w-full px-4 py-3.5 rounded-2xl border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/5 focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 outline-none font-mono font-bold text-sm text-slate-800 dark:text-white transition-all placeholder:text-slate-400"
                                        placeholder="0.000000"
                                    />
                                </div>
                            </div>

                            <div className="pt-4 flex gap-3">
                                <button
                                    type="button"
                                    onClick={() => setShowCreateModal(false)}
                                    className="flex-1 py-4 bg-slate-100 dark:bg-white/10 text-slate-600 dark:text-slate-300 rounded-2xl text-[10px] font-black uppercase tracking-widest hover:bg-slate-200 dark:hover:bg-white/20 transition-all"
                                >
                                    Cancelar
                                </button>
                                <button
                                    type="submit"
                                    disabled={submitting}
                                    className="flex-[2] py-4 bg-blue-600 text-white rounded-2xl text-[10px] font-black uppercase tracking-widest hover:bg-blue-700 active:scale-95 transition-all shadow-xl shadow-blue-500/20 flex items-center justify-center gap-2 disabled:opacity-60"
                                >
                                    {submitting ? <Loader2 size={16} className="animate-spin" /> : <Check size={16} />}
                                    {submitting ? 'Aperturando...' : 'Aperturar Casa'}
                                </button>
                            </div>
                        </form>
                    </motion.div>
                </motion.div>
            )}
        </AnimatePresence>
        </CrmShell>
    );
}
