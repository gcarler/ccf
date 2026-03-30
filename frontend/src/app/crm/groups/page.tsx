'use client';

import React, { useState, useEffect } from 'react';
import { Home, MapPin, Users, Heart, Search, Filter, Compass, Loader2, Link2, Plus, X, Check, Navigation, Zap, Map } from 'lucide-react';
import { apiFetch } from '@/lib/http';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import CrmShell from '@/components/crm/CrmShell';
import AdminHero from '@/components/admin/AdminHero';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';

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

export default function GroupsPage() {
    const [groups, setGroups] = useState<GloryHouse[]>([]);
    const [loading, setLoading] = useState(true);
    const [viewMode, setViewMode] = useState<'grid' | 'map'>('grid');
    const [showCreateModal, setShowCreateModal] = useState(false);
    const { token } = useAuth();
    const { addToast } = useToast();

    // Form state
    const [newHouse, setNewHouse] = useState({
        name: '',
        zone: '',
        address: '',
        leader_name: '',
        capacity: 15,
        latitude: '',
        longitude: ''
    });

    const [searchTerm, setSearchTerm] = useState('');

    const filteredGroups = groups.filter(g => 
        g.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
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
        } catch (err) {
            addToast("Error al crear casa", "error");
        }
    };

    useEffect(() => {
        fetchHouses();
    }, [token]);

    return (
        <CrmShell
            breadcrumbs={[{ label: 'CCF', icon: Users }, { label: 'CRM Pastoral', icon: Users }, { label: 'Casas de Gloria', icon: Home }]}
        >
        <style jsx global>{`
            .house-card-aura {
                position: relative;
            }
            .house-card-aura::after {
                content: '';
                position: absolute;
                inset: -1px;
                background: linear-gradient(45deg, var(--aura-color, #3b82f620), transparent 60%);
                z-index: -1;
                border-radius: inherit;
                opacity: 0;
                transition: opacity 0.5s ease;
            }
            .house-card-aura:hover::after {
                opacity: 1;
            }
            
            /* Map Heatmap/Pulse effects */
            .map-node {
                position: absolute;
                transform: translate(-50%, -50%);
                border-radius: 50%;
            }
            .map-pulse {
                animation: pulse-ring 2s cubic-bezier(0.215, 0.61, 0.355, 1) infinite;
            }
            @keyframes pulse-ring {
                0% { transform: scale(0.8); box-shadow: 0 0 0 0 rgba(var(--pulse-color), 0.7); }
                70% { transform: scale(1); box-shadow: 0 0 0 15px rgba(var(--pulse-color), 0); }
                100% { transform: scale(0.8); box-shadow: 0 0 0 0 rgba(var(--pulse-color), 0); }
            }
            
            .heatmap-layer {
                background: radial-gradient(circle at center, rgba(244,63,94,0.15) 0%, transparent 60%);
            }
        `}</style>

        <AdminHero
            eyebrow="Red Geográfica"
            title="Casas de Gloria"
            description="Mapea y administra los grupos que sostienen el discipulado en los barrios. Optimus Brain está detectando zonas de calor sin cobertura."
            tags={['Mapas', 'Discipulado', 'Clustering']}
            watchers={['Equipo Casas', 'Optimus Brain']}
            primaryAction={{ label: 'Nueva casa', icon: Plus, onClick: () => setShowCreateModal(true) }}
            secondaryAction={{ label: viewMode === 'grid' ? 'Vista Satelital' : 'Ver Cuadrícula', icon: viewMode === 'grid' ? Map : Navigation, onClick: () => setViewMode(viewMode === 'grid' ? 'map' : 'grid') }}
        />
        <div className="space-y-8 animate-in fade-in duration-500 pb-20">

            {/* Toolbar */}
            <div className="flex flex-col md:flex-row gap-4 items-center justify-between">
                <div className="relative flex-1 w-full max-w-2xl group">
                    <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-blue-600 transition-colors" size={20} />
                    <input
                        type="text"
                        placeholder="Buscar por zona, nombre o líder..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="w-full bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-[2rem] py-4 pl-12 pr-4 focus:outline-none focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 transition-all text-sm font-bold shadow-sm"
                    />
                </div>
                <div className="flex gap-2 w-full md:w-auto bg-slate-100 dark:bg-white/5 p-1 rounded-2xl border border-slate-200 dark:border-white/10 shadow-sm">
                    <button 
                        onClick={() => setViewMode('grid')}
                        className={`flex-1 md:flex-none px-8 py-2.5 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all ${viewMode === 'grid' ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/20' : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'}`}
                    >
                        Cuadrícula
                    </button>
                    <button 
                        onClick={() => setViewMode('map')}
                        className={`flex-1 md:flex-none px-8 py-2.5 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all ${viewMode === 'map' ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/20' : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'}`}
                    >
                        Mapa de Calor
                    </button>
                </div>
            </div>

            <AnimatePresence mode="wait">
            {loading ? (
                <motion.div key="loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex flex-col items-center justify-center py-40 gap-6">
                    <Loader2 className="animate-spin text-blue-600" size={64} strokeWidth={1.5} />
                    <p className="text-[10px] font-black uppercase tracking-[0.5em] text-slate-400 animate-pulse">Sincronizando Nodos Geo-Pastorales...</p>
                </motion.div>
            ) : viewMode === 'grid' ? (
                <motion.div 
                    key="grid" 
                    initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }}
                    className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6"
                >
                    {filteredGroups.map((group, i) => {
                        const saturation = group.capacity > 0 ? (group.members_count / group.capacity) : 0;
                        const tone = saturation >= 0.9 ? 'rose' : saturation >= 0.7 ? 'amber' : 'emerald';
                        const auraColor = tone === 'rose' ? 'rgba(244,63,94,0.3)' : tone === 'amber' ? 'rgba(245,158,11,0.3)' : 'rgba(16,185,129,0.3)';

                        return (
                            <motion.div 
                                initial={{ opacity: 0, scale: 0.95 }}
                                animate={{ opacity: 1, scale: 1 }}
                                transition={{ delay: i * 0.05 }}
                                key={group.id} 
                                className="house-card-aura bg-white dark:bg-[#1e1f21] p-8 rounded-[3rem] border border-slate-100 dark:border-white/5 hover:shadow-2xl transition-all duration-500 group overflow-hidden relative"
                                style={{ '--aura-color': auraColor } as any}
                            >
                                <div className="absolute top-0 right-0 p-6 opacity-5 group-hover:opacity-10 group-hover:rotate-12 transition-all duration-700">
                                    <Home size={100} />
                                </div>

                                <div className="flex justify-between items-start mb-8 relative z-10">
                                    <span className="px-3 py-1.5 bg-slate-50 dark:bg-white/5 text-slate-600 dark:text-slate-300 text-[9px] font-black uppercase tracking-[0.2em] rounded-xl flex items-center gap-1.5 border border-slate-200 dark:border-white/10">
                                        <MapPin size={12} /> {group.zone || 'Sin Zona'}
                                    </span>
                                    <div className="flex items-center gap-2">
                                        <div className={clsx("size-2 rounded-full shadow-[0_0_8px_currentColor] animate-pulse", group.status === 'Activo' ? "text-emerald-500" : "text-slate-400")} />
                                    </div>
                                </div>

                                <div className="relative z-10 mb-8">
                                    <h3 className="text-2xl font-black text-slate-900 dark:text-white tracking-tighter leading-none mb-2 group-hover:text-blue-600 transition-colors line-clamp-2">
                                        {group.name}
                                    </h3>
                                    <p className="text-[11px] font-bold text-slate-500 uppercase tracking-widest flex items-center gap-2">
                                        <Users size={12} /> {group.leader_name}
                                    </p>
                                </div>

                                <div className="space-y-4 pt-6 border-t border-slate-100 dark:border-white/5 relative z-10">
                                    <div className="flex justify-between items-end">
                                        <div>
                                            <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-1">Ocupación</p>
                                            <p className="text-xl font-black text-slate-800 dark:text-white tracking-tight">
                                                {group.members_count} <span className="text-sm text-slate-400">/ {group.capacity}</span>
                                            </p>
                                        </div>
                                        <div className={clsx("px-2 py-1 rounded text-[8px] font-black uppercase tracking-widest", 
                                            tone === 'rose' ? "bg-rose-50 text-rose-600" : 
                                            tone === 'amber' ? "bg-amber-50 text-amber-600" : 
                                            "bg-emerald-50 text-emerald-600"
                                        )}>
                                            {Math.round(saturation * 100)}% Sat.
                                        </div>
                                    </div>
                                    <div className="h-1.5 w-full bg-slate-100 dark:bg-white/10 rounded-full overflow-hidden">
                                        <motion.div 
                                            initial={{ width: 0 }} 
                                            animate={{ width: `${Math.min(100, saturation * 100)}%` }}
                                            className={clsx("h-full", tone === 'rose' ? "bg-rose-500 shadow-[0_0_10px_rgba(244,63,94,0.5)]" : tone === 'amber' ? "bg-amber-500" : "bg-emerald-500")}
                                        />
                                    </div>
                                </div>
                            </motion.div>
                        );
                    })}

                    <motion.div 
                        initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: filteredGroups.length * 0.05 }}
                        onClick={() => setShowCreateModal(true)}
                        className="bg-slate-50/50 dark:bg-white/5 border-2 border-dashed border-slate-200 dark:border-white/10 hover:border-blue-400 hover:bg-blue-50/50 dark:hover:bg-blue-900/10 transition-all duration-300 cursor-pointer flex flex-col items-center justify-center p-8 text-center min-h-[350px] rounded-[3rem] group"
                    >
                        <div className="size-20 bg-white dark:bg-[#1e1f21] rounded-[2rem] flex items-center justify-center shadow-lg mb-6 text-slate-300 dark:text-slate-600 group-hover:text-blue-600 group-hover:scale-110 group-hover:rotate-90 transition-all duration-500">
                            <Plus size={40} strokeWidth={1.5} />
                        </div>
                        <h3 className="text-lg font-black text-slate-700 dark:text-slate-300 uppercase tracking-tight group-hover:text-blue-600 transition-colors">Plantación Estratégica</h3>
                        <p className="text-[10px] font-bold text-slate-400 mt-2 uppercase tracking-[0.2em] max-w-[200px]">Establecer un nuevo nodo ministerial en la ciudad.</p>
                    </motion.div>
                </motion.div>
            ) : (
                <motion.div 
                    key="map"
                    initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.98 }}
                    className="relative bg-slate-900 rounded-[3.5rem] h-[700px] overflow-hidden shadow-2xl flex items-center justify-center border border-slate-800"
                >
                    {/* Simulated Advanced Map Background */}
                    <div className="absolute inset-0 opacity-40 mix-blend-screen" style={{
                        backgroundImage: `url("data:image/svg+xml,%3Csvg width='100%25' height='100%25' xmlns='http://www.w3.org/2000/svg'%3E%3Cdefs%3E%3Cpattern id='grid' width='40' height='40' patternUnits='userSpaceOnUse'%3E%3Cpath d='M 40 0 L 0 0 0 40' fill='none' stroke='rgba(255,255,255,0.1)' stroke-width='1'/%3E%3C/pattern%3E%3C/defs%3E%3Crect width='100%25' height='100%25' fill='url(%23grid)'/%3E%3C/svg%3E")`
                    }} />
                    
                    {/* Mock Heatmap Layers */}
                    <div className="absolute top-[20%] left-[30%] size-[400px] heatmap-layer rounded-full opacity-60 mix-blend-screen animate-pulse" style={{ animationDuration: '4s' }} />
                    <div className="absolute bottom-[20%] right-[25%] size-[300px] heatmap-layer rounded-full opacity-40 mix-blend-screen animate-pulse" style={{ animationDuration: '6s', backgroundColor: 'rgba(59,130,246,0.1)' }} />

                    {/* Nodes */}
                    {groups.filter(g => g.latitude).map((g, i) => {
                        // Mock positioning based on lat/lon (assuming they are roughly in a specific area, we map them to % for demo)
                        // In a real app, this would be a Leaflet/Mapbox instance.
                        const top = `${40 + (i % 3) * 15}%`;
                        const left = `${30 + (i % 4) * 15}%`;
                        
                        const saturation = g.capacity > 0 ? (g.members_count / g.capacity) : 0;
                        const pulseColor = saturation >= 0.9 ? '244,63,94' : saturation >= 0.7 ? '245,158,11' : '16,185,129';

                        return (
                            <div key={g.id} className="map-node group cursor-crosshair z-10" style={{ top, left, '--pulse-color': pulseColor } as any}>
                                <div className="map-pulse absolute inset-0 size-6 -ml-3 -mt-3 rounded-full" />
                                <div className="relative size-4 -ml-2 -mt-2 bg-white rounded-full border-[3px] shadow-[0_0_15px_rgba(255,255,255,0.8)] flex items-center justify-center" style={{ borderColor: `rgb(${pulseColor})` }}>
                                    <div className="size-1 rounded-full" style={{ backgroundColor: `rgb(${pulseColor})` }} />
                                </div>
                                
                                {/* Hover Info Card */}
                                <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-4 w-48 p-4 bg-white/10 backdrop-blur-xl border border-white/20 rounded-2xl shadow-2xl opacity-0 group-hover:opacity-100 transition-all duration-300 pointer-events-none scale-90 group-hover:scale-100 origin-bottom">
                                    <p className="text-[10px] font-black text-white uppercase tracking-widest truncate">{g.name}</p>
                                    <p className="text-[9px] text-white/70 font-bold mb-2">{g.zone}</p>
                                    <div className="flex justify-between items-center text-white">
                                        <div className="flex items-center gap-1"><Users size={10} className="opacity-70" /> <span className="text-[10px] font-black">{g.members_count}/{g.capacity}</span></div>
                                        <span className="text-[8px] font-black px-1.5 py-0.5 rounded bg-white/20">{Math.round(saturation*100)}%</span>
                                    </div>
                                </div>
                            </div>
                        );
                    })}

                    {/* AI Overlay Panel */}
                    <div className="absolute bottom-10 left-10 p-8 bg-black/40 backdrop-blur-2xl border border-white/10 rounded-[2.5rem] shadow-2xl max-w-sm pointer-events-none">
                        <div className="flex items-center gap-3 mb-4 text-blue-400">
                            <Zap size={20} className="animate-pulse" fill="currentColor" />
                            <h3 className="text-xs font-black uppercase tracking-[0.3em]">Optimus Clusters</h3>
                        </div>
                        <p className="text-sm text-white/80 font-medium leading-relaxed mb-6">
                            Detectada alta concentración de miembros sin cobertura en la <span className="font-bold text-white">Zona Sur (Sector 4)</span>. Se recomienda establecer una nueva célula para absorber la demanda y evitar saturación en "Casa de Paz Norte".
                        </p>
                        <div className="flex gap-4">
                            <div className="flex items-center gap-2"><div className="size-2 bg-rose-500 rounded-full shadow-[0_0_8px_#f43f5e]" /><span className="text-[9px] text-white/60 font-black uppercase tracking-widest">Saturado</span></div>
                            <div className="flex items-center gap-2"><div className="size-2 bg-emerald-500 rounded-full shadow-[0_0_8px_#10b981]" /><span className="text-[9px] text-white/60 font-black uppercase tracking-widest">Óptimo</span></div>
                        </div>
                    </div>
                </motion.div>
            )}
            </AnimatePresence>
        </div>

        {/* Create Modal */}
        {showCreateModal && (
            <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-slate-950/40 backdrop-blur-md animate-in fade-in">
                <div className="w-full max-w-xl bg-white rounded-[3rem] shadow-2xl border border-white overflow-hidden animate-in zoom-in-95 duration-300">
                    <div className="p-8 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
                        <div>
                            <h2 className="text-2xl font-black text-slate-900 uppercase tracking-tight text-blue-600 flex items-center gap-3"><MapPin size={24} /> Aperturar Casa</h2>
                            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-[0.2em] mt-1">Configuración geográfica y liderazgo</p>
                        </div>
                        <button onClick={() => setShowCreateModal(false)} className="p-3 bg-white text-slate-400 hover:text-slate-900 hover:shadow-sm rounded-full transition-all">
                            <X size={20} />
                        </button>
                    </div>
                    <form onSubmit={handleCreateHouse} className="p-10 space-y-6">
                        <div className="grid grid-cols-2 gap-6">
                            <div className="space-y-1.5">
                                <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Nombre *</label>
                                <input required value={newHouse.name} onChange={e => setNewHouse({...newHouse, name: e.target.value})} className="w-full px-5 py-4 rounded-2xl border border-slate-100 focus:ring-4 focus:ring-blue-500/10 outline-none font-bold text-xs transition-all bg-slate-50 focus:bg-white" placeholder="Ej: Casa de Paz Ebenezer" />
                            </div>
                            <div className="space-y-1.5">
                                <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Zona *</label>
                                <input required value={newHouse.zone} onChange={e => setNewHouse({...newHouse, zone: e.target.value})} className="w-full px-5 py-4 rounded-2xl border border-slate-100 focus:ring-4 focus:ring-blue-500/10 outline-none font-bold text-xs transition-all bg-slate-50 focus:bg-white" placeholder="Ej: Zona Norte" />
                            </div>
                        </div>
                        <div className="space-y-1.5">
                            <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Líder Asignado</label>
                            <input value={newHouse.leader_name} onChange={e => setNewHouse({...newHouse, leader_name: e.target.value})} className="w-full px-5 py-4 rounded-2xl border border-slate-100 focus:ring-4 focus:ring-blue-500/10 outline-none font-bold text-xs transition-all bg-slate-50 focus:bg-white" placeholder="Nombre del responsable" />
                        </div>
                        <div className="space-y-1.5">
                            <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Dirección Física</label>
                            <input value={newHouse.address} onChange={e => setNewHouse({...newHouse, address: e.target.value})} className="w-full px-5 py-4 rounded-2xl border border-slate-100 focus:ring-4 focus:ring-blue-500/10 outline-none font-bold text-xs transition-all bg-slate-50 focus:bg-white" placeholder="Calle, número, ciudad" />
                        </div>
                        <div className="grid grid-cols-2 gap-6">
                            <div className="space-y-1.5">
                                <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1 flex items-center gap-2"><Map size={12} className="text-blue-500"/> Latitud (Opcional)</label>
                                <input type="number" step="any" value={newHouse.latitude} onChange={e => setNewHouse({...newHouse, latitude: e.target.value})} className="w-full px-5 py-4 rounded-2xl border border-slate-100 focus:ring-4 focus:ring-blue-500/10 outline-none font-bold text-xs transition-all bg-slate-50 focus:bg-white font-mono" placeholder="0.000000" />
                            </div>
                            <div className="space-y-1.5">
                                <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1 flex items-center gap-2"><Map size={12} className="text-blue-500"/> Longitud (Opcional)</label>
                                <input type="number" step="any" value={newHouse.longitude} onChange={e => setNewHouse({...newHouse, longitude: e.target.value})} className="w-full px-5 py-4 rounded-2xl border border-slate-100 focus:ring-4 focus:ring-blue-500/10 outline-none font-bold text-xs transition-all bg-slate-50 focus:bg-white font-mono" placeholder="0.000000" />
                            </div>
                        </div>
                        <div className="pt-6 flex gap-4">
                            <button type="button" onClick={() => setShowCreateModal(false)} className="flex-1 py-5 bg-white border border-slate-200 text-slate-500 rounded-2xl text-[10px] font-black uppercase tracking-widest hover:bg-slate-50 hover:text-slate-700 transition-all">Cancelar</button>
                            <button type="submit" className="flex-2 px-12 py-5 bg-blue-600 text-white rounded-2xl text-[10px] font-black uppercase tracking-widest hover:bg-blue-700 transition-all shadow-xl shadow-blue-500/30 flex items-center justify-center gap-3">Aperturar Casa <Check size={18} /></button>
                        </div>
                    </form>
                </div>
            </div>
        )}
        </CrmShell>
    );
}
