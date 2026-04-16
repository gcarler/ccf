'use client';

import React, { useState, useEffect } from 'react';
import {
    Home, MapPin, Users, Search, Loader2, Plus, Check,
    Zap, Map, Navigation, Grid3x3, X
} from 'lucide-react';
import { apiFetch } from '@/lib/http';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import CrmShell from '@/components/crm/CrmShell';
import CrmViewPlaceholder from '@/components/crm/CrmViewPlaceholder';
import AdminHero from '@/components/admin/AdminHero';
import RightPanel from '@/components/ui/RightPanel';
import { useSidebarLayers } from '@/context/SidebarLayerContext';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import { ViewType, getStoredView } from '@/components/ViewSwitcher';
import { useRouter } from 'next/navigation';
import { ChevronRight } from 'lucide-react';

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
    rose:    { bar: 'bg-rose-500',    badge: 'bg-rose-50 dark:bg-rose-500/10 text-rose-600 dark:text-rose-400' },
    amber:   { bar: 'bg-amber-500',   badge: 'bg-amber-50 dark:bg-amber-500/10 text-amber-600 dark:text-amber-400' },
    emerald: { bar: 'bg-emerald-500', badge: 'bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400' },
};

const PULSE_COLORS = { rose: '244,63,94', amber: '245,158,11', emerald: '16,185,129' };

// ─── Form field component ─────────────────────────────────────────────────────

function Field({ label, required, children }: { label: string; required?: boolean; children: React.ReactNode }) {
    return (
        <div className="space-y-1.5">
            <label className="flex items-center gap-1 text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest">
                {label}{required && <span className="text-blue-500">*</span>}
            </label>
            {children}
        </div>
    );
}

const INPUT_CLS = "w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 text-sm font-medium text-slate-800 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500 transition-all";

// ─── Main Component ───────────────────────────────────────────────────────────

export default function GroupsPage() {
    const router = useRouter();
    const [groups, setGroups] = useState<GloryHouse[]>([]);
    const [loading, setLoading] = useState(true);
    const [viewMode, setViewMode] = useState<'grid' | 'map' | 'list' | 'table' | 'calendar' | 'gantt' | 'wiki'>(
        () => {
            const saved = getStoredView('crm_groups_view', 'grid');
            if (saved === 'board' || saved === 'kanban') return 'map';
            if (saved === 'list' || saved === 'table' || saved === 'calendar' || saved === 'gantt' || saved === 'wiki') return saved;
            return 'grid';
        }
    );
    const [wikiNotes, setWikiNotes] = useState('');
    const ALL_VIEWS: ViewType[] = ['table', 'list', 'grid', 'board', 'kanban', 'gantt', 'calendar', 'wiki'];
    const crmViewType: ViewType = viewMode === 'map' ? 'board' : viewMode;
    const handleViewChange = (v: ViewType) => {
        if (v === 'board' || v === 'kanban') setViewMode('map');
        else if (v === 'list' || v === 'table' || v === 'calendar' || v === 'gantt' || v === 'wiki' || v === 'grid') setViewMode(v);
        else setViewMode('grid');
    };

    const { token } = useAuth();
    const { addToast } = useToast();
    const { openLayer, closeLayer, setRightMode, layers } = useSidebarLayers();

    const [newHouse, setNewHouse] = useState({
        name: '', zone: '', address: '', leader_name: '', capacity: 15, latitude: '', longitude: ''
    });
    const [submitting, setSubmitting] = useState(false);
    const [searchTerm, setSearchTerm] = useState('');

    const openCreatePanel = () => {
        setRightMode('overlay');
        openLayer('RIGHT');
    };

    const closeCreatePanel = () => {
        closeLayer('RIGHT');
        setNewHouse({ name: '', zone: '', address: '', leader_name: '', capacity: 15, latitude: '', longitude: '' });
    };

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
            closeCreatePanel();
            fetchHouses();
        } catch {
            addToast("Error al crear casa", "error");
        } finally {
            setSubmitting(false);
        }
    };

    useEffect(() => { 
        fetchHouses(); 
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [token]);

    useEffect(() => {
        const saved = localStorage.getItem('crm_groups_wiki_notes');
        if (saved) setWikiNotes(saved);
    }, []);

    useEffect(() => {
        localStorage.setItem('crm_groups_wiki_notes', wikiNotes);
    }, [wikiNotes]);

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
                    onClick={openCreatePanel}
                    className="flex items-center gap-2 bg-blue-600 px-5 py-2 rounded-xl text-[11px] font-black text-white hover:bg-blue-700 active:scale-95 transition-all shadow-lg shadow-blue-900/20 uppercase tracking-widest"
                >
                    <Plus size={14} /> Nueva Casa
                </button>
            }
        >
        {/* ─── Layout principal: contenido + RightPanel ─── */}
        <div className="flex h-full overflow-hidden relative">

            {/* ─── Contenido scrolleable ─── */}
            <div className="flex-1 overflow-y-auto">
                <div className="space-y-8 pb-20 p-1">

                    {/* AdminHero */}
                    <AdminHero
                        eyebrow="Red Geográfica"
                        title="Casas de Gloria"
                        description="Mapea y administra los grupos que sostienen el discipulado en los barrios. Optimus Brain detecta zonas sin cobertura."
                        tags={['Mapas', 'Discipulado', 'Clustering']}
                        watchers={['Equipo Casas', 'Optimus Brain']}
                        primaryAction={{ label: 'Nueva casa', icon: Plus, onClick: openCreatePanel }}
                        secondaryAction={{
                            label: viewMode === 'grid' ? 'Vista Satelital' : 'Ver Cuadrícula',
                            icon: viewMode === 'grid' ? Map : Navigation,
                            onClick: () => setViewMode(viewMode === 'grid' ? 'map' : 'grid')
                        }}
                    />

                    {/* Search + Toggle */}
                    <div className="flex flex-col md:flex-row gap-4 items-center justify-between">
                        <div className="relative flex-1 w-full max-w-2xl group">
                            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-blue-600 transition-colors" size={17} />
                            <input
                                type="text"
                                placeholder="Buscar por zona, nombre o líder..."
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                                className="w-full bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-[2rem] py-3.5 pl-12 pr-4 focus:outline-none focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 transition-all text-sm font-bold shadow-sm dark:text-white placeholder:text-slate-400"
                            />
                        </div>
                        <div className="flex gap-1 bg-slate-100 dark:bg-white/5 p-1 rounded-2xl border border-slate-200 dark:border-white/10">
                            <button onClick={() => setViewMode('grid')} className={clsx('flex items-center gap-2 px-5 py-2.5 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all', viewMode === 'grid' ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/20' : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200')}>
                                <Grid3x3 size={12} /> Cuadrícula
                            </button>
                            <button onClick={() => setViewMode('map')} className={clsx('flex items-center gap-2 px-5 py-2.5 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all', viewMode === 'map' ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/20' : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200')}>
                                <Map size={12} /> Mapa de Calor
                            </button>
                        </div>
                    </div>

                    {/* Main View */}
                    <AnimatePresence mode="wait">
                        {loading ? (
                            <motion.div key="loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                                className="flex flex-col items-center justify-center py-32 gap-5"
                            >
                                <Loader2 className="animate-spin text-blue-600" size={40} strokeWidth={1.5} />
                                <p className="text-[10px] font-black uppercase tracking-[0.4em] text-slate-400 animate-pulse">
                                    Sincronizando nodos geo-pastorales...
                                </p>
                            </motion.div>
                        ) : viewMode === 'grid' ? (
                            <motion.div key="grid" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -16 }}
                                className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5"
                            >
                                {filteredGroups.length === 0 && (
                                    <div className="col-span-4 py-24 text-center flex flex-col items-center gap-4">
                                        <Home size={44} className="text-slate-200 dark:text-white/10" />
                                        <p className="font-black text-slate-500 dark:text-slate-400">
                                            {searchTerm ? 'Sin resultados' : 'No hay casas registradas aún'}
                                        </p>
                                        <p className="text-sm text-slate-400">{searchTerm ? 'Prueba con otro término' : 'Apertura la primera casa de gloria'}</p>
                                        {!searchTerm && (
                                            <button onClick={openCreatePanel} className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white rounded-xl text-sm font-black hover:bg-blue-700 active:scale-95 transition-all mt-1">
                                                <Plus size={15} /> Nueva Casa
                                            </button>
                                        )}
                                    </div>
                                )}

                                {filteredGroups.map((group, i) => {
                                    const sat = group.capacity > 0 ? group.members_count / group.capacity : 0;
                                    const tone = getSaturationTone(sat);
                                    const pct = Math.min(100, Math.round(sat * 100));
                                    const displayPct = Math.round(sat * 100);

                                    return (
                                        <motion.div
                                            onClick={() => router.push(`/crm/groups/${group.id}`)}
                                            className="bg-white dark:bg-[#1e1f21] p-7 rounded-[2.5rem] border border-slate-100 dark:border-white/5 hover:shadow-xl hover:shadow-slate-200/30 hover:-translate-y-1 dark:hover:shadow-none transition-all duration-400 group overflow-hidden relative cursor-pointer"
                                        >
                                            {/* BG watermark */}
                                            <div className="absolute top-0 right-0 p-5 opacity-[0.03] group-hover:opacity-[0.07] group-hover:rotate-12 transition-all duration-700 pointer-events-none">
                                                <Home size={80} />
                                            </div>

                                            {/* Zone + Status */}
                                            <div className="flex justify-between items-start mb-5 relative z-10">
                                                <span className="px-2.5 py-1 bg-slate-50 dark:bg-white/5 text-slate-600 dark:text-slate-300 text-[9px] font-black uppercase tracking-widest rounded-xl flex items-center gap-1.5 border border-slate-200 dark:border-white/10">
                                                    <MapPin size={9} /> {group.zone || 'Sin zona'}
                                                </span>
                                                <div className="flex items-center gap-1.5">
                                                    <div className={clsx('size-2 rounded-full', group.status === 'Activo' ? 'bg-emerald-500 shadow-[0_0_6px_#10b981] animate-pulse' : 'bg-slate-300')} />
                                                    <span className="text-[9px] font-black text-slate-400 uppercase tracking-widest">{group.status || 'Activo'}</span>
                                                </div>
                                            </div>

                                            {/* Name + Leader */}
                                            <div className="relative z-10 mb-5">
                                                <h3 className="text-xl font-black text-slate-900 dark:text-white tracking-tighter leading-none mb-1.5 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors line-clamp-2">
                                                    {group.name}
                                                </h3>
                                                <p className="text-[11px] font-bold text-slate-400 uppercase tracking-widest flex items-center gap-1.5">
                                                    <Users size={11} /> {group.leader_name || 'Sin líder asignado'}
                                                </p>
                                            </div>

                                            {/* Saturation bar */}
                                            <div className="space-y-2 pt-4 border-t border-slate-100 dark:border-white/5 relative z-10">
                                                <div className="flex justify-between items-center">
                                                    <div>
                                                        <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-0.5">Ocupación</p>
                                                        <p className="text-lg font-black text-slate-800 dark:text-white">
                                                            {group.members_count} <span className="text-sm text-slate-400 font-semibold">/ {group.capacity}</span>
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

                                {/* Add card */}
                                <motion.div
                                    initial={{ opacity: 0, scale: 0.95 }}
                                    animate={{ opacity: 1, scale: 1 }}
                                    transition={{ delay: filteredGroups.length * 0.04 }}
                                    onClick={openCreatePanel}
                                    className="bg-slate-50/50 dark:bg-white/[0.03] border-2 border-dashed border-slate-200 dark:border-white/10 hover:border-blue-400 hover:bg-blue-50/50 dark:hover:bg-blue-900/10 transition-all duration-300 cursor-pointer flex flex-col items-center justify-center p-8 text-center min-h-[220px] rounded-[2.5rem] group"
                                >
                                    <div className="size-14 bg-white dark:bg-[#1e1f21] rounded-[1.5rem] flex items-center justify-center shadow-md mb-4 text-slate-300 dark:text-slate-600 group-hover:text-blue-600 group-hover:scale-110 group-hover:rotate-90 transition-all duration-500">
                                        <Plus size={28} strokeWidth={1.5} />
                                    </div>
                                    <h3 className="text-sm font-black text-slate-500 dark:text-slate-400 uppercase tracking-tight group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                                        Plantación Estratégica
                                    </h3>
                                    <p className="text-[10px] font-bold text-slate-400 mt-1 uppercase tracking-widest max-w-[150px] leading-relaxed">
                                        Nuevo nodo ministerial
                                    </p>
                                </motion.div>
                            </motion.div>
                        ) : viewMode === 'map' ? (
                            /* ─── MAP VIEW ─── */
                            <motion.div key="map" initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.98 }}
                                className="relative bg-slate-900 rounded-[2.5rem] overflow-hidden shadow-2xl border border-slate-800"
                                style={{ height: 640 }}
                            >
                                <div className="absolute inset-0 opacity-30" style={{
                                    backgroundImage: `url("data:image/svg+xml,%3Csvg width='100%25' height='100%25' xmlns='http://www.w3.org/2000/svg'%3E%3Cdefs%3E%3Cpattern id='grid' width='40' height='40' patternUnits='userSpaceOnUse'%3E%3Cpath d='M 40 0 L 0 0 0 40' fill='none' stroke='rgba(255,255,255,0.07)' stroke-width='1'/%3E%3C/pattern%3E%3C/defs%3E%3Crect width='100%25' height='100%25' fill='url(%23grid)'/%3E%3C/svg%3E")`
                                }} />
                                <div className="absolute top-[15%] left-[28%] size-[350px] rounded-full opacity-50 mix-blend-screen animate-pulse" style={{ background: 'radial-gradient(circle, rgba(244,63,94,0.18) 0%, transparent 70%)', animationDuration: '4s' }} />
                                <div className="absolute bottom-[18%] right-[22%] size-[260px] rounded-full opacity-35 mix-blend-screen animate-pulse" style={{ background: 'radial-gradient(circle, rgba(59,130,246,0.15) 0%, transparent 70%)', animationDuration: '6s' }} />
                                <div className="absolute top-[45%] right-[38%] size-[180px] rounded-full opacity-40 mix-blend-screen animate-pulse" style={{ background: 'radial-gradient(circle, rgba(16,185,129,0.15) 0%, transparent 70%)', animationDuration: '5s' }} />

                                {/* Nodes */}
                                {groups.slice(0, 6).map((g, i) => {
                                    const sat = g.capacity > 0 ? g.members_count / g.capacity : 0;
                                    const tone = getSaturationTone(sat);
                                    const pulseColor = PULSE_COLORS[tone];
                                    const positions = [
                                        { top: '28%', left: '33%' }, { top: '22%', left: '58%' },
                                        { top: '52%', left: '44%' }, { top: '42%', left: '68%' },
                                        { top: '64%', left: '28%' }, { top: '38%', left: '19%' },
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

                                {/* AI Overlay */}
                                <div className="absolute bottom-8 left-8 p-6 bg-black/50 backdrop-blur-2xl border border-white/10 rounded-[2rem] shadow-2xl max-w-[300px]">
                                    <div className="flex items-center gap-2.5 mb-3 text-blue-400">
                                        <Zap size={17} className="animate-pulse" fill="currentColor" />
                                        <h3 className="text-[10px] font-black uppercase tracking-[0.3em]">Optimus Clusters</h3>
                                    </div>
                                    <p className="text-sm text-white/75 font-medium leading-relaxed mb-3">
                                        Alta concentración sin cobertura en <span className="font-bold text-white">Zona Sur</span>. Se recomienda aperturar una nueva célula.
                                    </p>
                                    <div className="flex gap-3 flex-wrap">
                                        {Object.entries({ Saturado: 'rose', Alertado: 'amber', Óptimo: 'emerald' } as const).map(([label, tone]) => (
                                            <div key={label} className="flex items-center gap-1.5">
                                                <div className="size-2 rounded-full" style={{ backgroundColor: `rgb(${PULSE_COLORS[tone]})`, boxShadow: `0 0 6px rgb(${PULSE_COLORS[tone]})` }} />
                                                <span className="text-[9px] text-white/50 font-black uppercase tracking-widest">{label}</span>
                                            </div>
                                        ))}
                                    </div>
                                </div>

                                {/* Stats */}
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
                        ) : viewMode === 'list' ? (
                            <motion.div key="list" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-3">
                                {filteredGroups.map(group => (
                                <div 
                                    key={group.id} 
                                    onClick={() => router.push(`/crm/groups/${group.id}`)}
                                    className="cursor-pointer group"
                                >
                                    <div className="rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 p-4 flex items-center justify-between hover:border-blue-500/50 transition-all">
                                        <div>
                                            <p className="text-sm font-black text-slate-800 dark:text-slate-100 group-hover:text-blue-600 transition-colors uppercase tracking-tight">{group.name}</p>
                                            <p className="text-[11px] text-slate-500">{group.zone} · {group.leader_name || 'Sin líder'}</p>
                                        </div>
                                        <div className="flex items-center gap-3">
                                            <span className="text-[10px] font-black uppercase tracking-widest text-slate-400">{group.members_count}/{group.capacity}</span>
                                            <ChevronRight size={14} className="text-slate-300 group-hover:text-blue-500 transition-all" />
                                        </div>
                                    </div>
                                </div>
                                ))}
                            </motion.div>
                        ) : viewMode === 'table' ? (
                            <motion.div key="table" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="rounded-2xl border border-slate-200 dark:border-white/10 overflow-hidden bg-white dark:bg-white/5">
                                <table className="w-full text-left">
                                    <thead className="bg-slate-50 dark:bg-white/5">
                                        <tr>
                                            <th className="px-4 py-3 text-[10px] font-black uppercase tracking-widest text-slate-400">Casa</th>
                                            <th className="px-4 py-3 text-[10px] font-black uppercase tracking-widest text-slate-400">Zona</th>
                                            <th className="px-4 py-3 text-[10px] font-black uppercase tracking-widest text-slate-400">Lider</th>
                                            <th className="px-4 py-3 text-[10px] font-black uppercase tracking-widest text-slate-400">Ocupacion</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {filteredGroups.map(group => (
                                            <tr 
                                                key={group.id} 
                                                onClick={() => router.push(`/crm/groups/${group.id}`)}
                                                className="border-t border-slate-100 dark:border-white/5 hover:bg-slate-50 dark:hover:bg-white/5 cursor-pointer transition-all group"
                                            >
                                                <td className="px-4 py-3 text-sm font-bold text-slate-800 dark:text-slate-100 group-hover:text-blue-600 uppercase italic">{group.name}</td>
                                                <td className="px-4 py-3 text-xs text-slate-500">{group.zone}</td>
                                                <td className="px-4 py-3 text-xs text-slate-500">{group.leader_name || 'Sin líder'}</td>
                                                <td className="px-4 py-3 text-xs font-black text-slate-500 flex items-center justify-between">
                                                    <span>{group.members_count}/{group.capacity}</span>
                                                    <ChevronRight size={14} className="opacity-0 group-hover:opacity-100 text-blue-500" />
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </motion.div>
                        ) : (
                            <CrmViewPlaceholder 
                                viewType={viewMode as any} 
                                items={filteredGroups}
                                wikiKey="crm_groups_wiki_notes"
                            />
                        )}
                    </AnimatePresence>
                </div>
            </div>

            {/* ─── RightPanel: Formulario de Creación ─── */}
            <RightPanel title="Nueva Casa de Gloria" width={380}>
                <form onSubmit={handleCreateHouse} className="flex flex-col h-full">
                    <div className="flex-1 overflow-y-auto p-5 space-y-4">

                        {/* Header visual del panel */}
                        <div className="p-5 rounded-2xl bg-gradient-to-br from-blue-600 to-indigo-700 text-white mb-2">
                            <div className="flex items-center gap-3 mb-1">
                                <div className="size-9 bg-white/10 rounded-xl flex items-center justify-center">
                                    <Home size={18} />
                                </div>
                                <div>
                                    <p className="text-xs font-black uppercase tracking-widest">Aperturar</p>
                                    <p className="text-[10px] text-blue-200 font-bold">Nueva Casa de Gloria</p>
                                </div>
                            </div>
                        </div>

                        <Field label="Nombre" required>
                            <input required value={newHouse.name} onChange={e => setNewHouse({ ...newHouse, name: e.target.value })}
                                className={INPUT_CLS} placeholder="Casa de Paz Ebenezer" />
                        </Field>

                        <Field label="Zona" required>
                            <input required value={newHouse.zone} onChange={e => setNewHouse({ ...newHouse, zone: e.target.value })}
                                className={INPUT_CLS} placeholder="Zona Norte" />
                        </Field>

                        <Field label="Líder Asignado">
                            <input value={newHouse.leader_name} onChange={e => setNewHouse({ ...newHouse, leader_name: e.target.value })}
                                className={INPUT_CLS} placeholder="Nombre del responsable" />
                        </Field>

                        <Field label="Dirección Física">
                            <input value={newHouse.address} onChange={e => setNewHouse({ ...newHouse, address: e.target.value })}
                                className={INPUT_CLS} placeholder="Calle, número, ciudad" />
                        </Field>

                        <Field label="Capacidad máx.">
                            <input type="number" min="1" max="200" value={newHouse.capacity} onChange={e => setNewHouse({ ...newHouse, capacity: Number(e.target.value) })}
                                className={INPUT_CLS} />
                        </Field>

                        <div className="pt-1">
                            <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-3 flex items-center gap-1.5">
                                <Map size={10} className="text-blue-500" /> Coordenadas (Opcional)
                            </p>
                            <div className="grid grid-cols-2 gap-3">
                                <Field label="Latitud">
                                    <input type="number" step="any" value={newHouse.latitude} onChange={e => setNewHouse({ ...newHouse, latitude: e.target.value })}
                                        className={INPUT_CLS + ' font-mono'} placeholder="0.000000" />
                                </Field>
                                <Field label="Longitud">
                                    <input type="number" step="any" value={newHouse.longitude} onChange={e => setNewHouse({ ...newHouse, longitude: e.target.value })}
                                        className={INPUT_CLS + ' font-mono'} placeholder="0.000000" />
                                </Field>
                            </div>
                        </div>
                    </div>

                    {/* Footer de acciones */}
                    <div className="shrink-0 p-5 border-t border-slate-100 dark:border-white/10 flex gap-3">
                        <button type="button" onClick={closeCreatePanel}
                            className="flex-1 py-3 bg-slate-100 dark:bg-white/10 text-slate-600 dark:text-slate-300 rounded-xl text-[10px] font-black uppercase tracking-widest hover:bg-slate-200 dark:hover:bg-white/20 transition-all"
                        >
                            Cancelar
                        </button>
                        <button type="submit" disabled={submitting}
                            className="flex-[2] py-3 bg-blue-600 text-white rounded-xl text-[10px] font-black uppercase tracking-widest hover:bg-blue-700 active:scale-95 transition-all shadow-xl shadow-blue-500/20 flex items-center justify-center gap-2 disabled:opacity-60"
                        >
                            {submitting ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />}
                            {submitting ? 'Aperturando...' : 'Aperturar Casa'}
                        </button>
                    </div>
                </form>
            </RightPanel>
        </div>
        </CrmShell>
    );
}
