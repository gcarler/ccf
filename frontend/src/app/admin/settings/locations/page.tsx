"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import {
    ArrowLeft,
    Search,
    Church,
    MapPin,
    Edit2,
    PlusCircle,
    User,
    Building2,
    DoorOpen,
    Loader2,
    Check,
    X
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';

interface Location {
    id: number;
    name: string;
    address: string;
    pastor: string;
    active: boolean;
    type: string;
}

export default function LocationManagement() {
    const { token, isAuthenticated } = useAuth();
    const { addToast } = useToast();
    const router = useRouter();

    const [locations, setLocations] = useState<Location[]>([]);
    const [loading, setLoading] = useState(true);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [newLoc, setNewLoc] = useState({ name: '', address: '', pastor: '', type: 'Sede' });

    const fetchLocations = useCallback(async () => {
        if (!token) return;
        setLoading(true);
        try {
            const data = await apiFetch<any[]>('/admin/locations', { token, cache: 'no-store' });
            setLocations(Array.isArray(data) ? data : []);
        } catch (err) {
            console.error(err);
            addToast("Error al cargar sedes", "error");
        } finally {
            setLoading(false);
        }
    }, [token, addToast]);

    useEffect(() => {
        if (isAuthenticated) fetchLocations();
    }, [isAuthenticated, fetchLocations]);

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            await apiFetch('/admin/locations', {
                method: 'POST',
                token,
                body: newLoc
            });
            addToast("Sede registrada", "success");
            setIsModalOpen(false);
            setNewLoc({ name: '', address: '', pastor: '', type: 'Sede' });
            fetchLocations();
        } catch (err) {
            addToast("Error al registrar sede", "error");
        }
    };

    if (!isAuthenticated) return null;

    return (
        <div className="flex flex-col h-full bg-slate-50 dark:bg-[#0a0f16] font-display overflow-hidden">
            {/* Header Area */}
            <div className="bg-white dark:bg-white/5 border-b border-slate-200 dark:border-white/10 sticky top-0 z-50 p-8 flex items-center justify-between">
                <div className="flex items-center gap-6">
                    <button onClick={() => router.back()} className="p-3 rounded-2xl bg-slate-100 dark:bg-white/5 text-slate-500 hover:text-blue-600 transition-all">
                        <ArrowLeft size={20} />
                    </button>
                    <div>
                        <h1 className="text-3xl font-black text-slate-900 dark:text-white tracking-tighter uppercase leading-none">Gestión de Sedes</h1>
                        <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mt-1">Nodos Ministeriales CCF</p>
                    </div>
                </div>
                <button 
                    onClick={() => setIsModalOpen(true)}
                    className="flex items-center gap-3 px-8 py-4 bg-blue-600 text-white rounded-[1.5rem] text-[11px] font-black uppercase tracking-widest shadow-xl shadow-blue-500/20 active:scale-95 transition-all"
                >
                    <PlusCircle size={18} /> Añadir Nueva Sede
                </button>
            </div>

            <main className="flex-1 overflow-y-auto p-8 lg:p-12 space-y-10 scrollbar-thin">
                {loading ? (
                    <div className="flex flex-col items-center justify-center py-40 gap-4 text-slate-400 font-black uppercase tracking-widest animate-pulse">
                        <Loader2 className="animate-spin" size={40} /> Sincronizando Sedes...
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 pb-40">
                        {locations.map((loc, i) => (
                            <motion.div
                                initial={{ opacity: 0, scale: 0.9 }}
                                animate={{ opacity: 1, scale: 1 }}
                                transition={{ delay: i * 0.05 }}
                                key={loc.id}
                                className={clsx(
                                    "bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-[3rem] p-10 flex flex-col gap-8 shadow-sm group hover:border-blue-500/30 transition-all relative overflow-hidden",
                                    !loc.active && "opacity-60"
                                )}
                            >
                                <div className="absolute top-0 right-0 p-8 opacity-5 group-hover:scale-110 transition-transform duration-700">
                                    <Church size={120} />
                                </div>

                                <div className="flex items-start justify-between relative z-10">
                                    <div className="flex gap-6">
                                        <div className="size-16 rounded-[1.5rem] bg-blue-50 dark:bg-blue-900/20 text-blue-600 flex items-center justify-center shadow-inner group-hover:bg-blue-600 group-hover:text-white transition-all duration-500">
                                            {loc.type === 'Central' ? <Church size={32} /> : loc.type === 'Sede' ? <Building2 size={32} /> : <DoorOpen size={32} />}
                                        </div>
                                        <div className="space-y-1">
                                            <h3 className="text-2xl font-black text-slate-900 dark:text-white tracking-tight uppercase leading-none">{loc.name}</h3>
                                            <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest flex items-center gap-2">
                                                <MapPin size={12} className="text-blue-500" />
                                                {loc.address || 'Sin dirección registrada'}
                                            </p>
                                        </div>
                                    </div>
                                </div>

                                <div className="flex items-center justify-between pt-8 border-t border-slate-100 dark:border-white/5 relative z-10">
                                    <div className="flex items-center gap-4">
                                        <div className="size-10 rounded-full border border-slate-200 dark:border-white/10 bg-slate-100 dark:bg-white/10 flex items-center justify-center text-xs font-black text-slate-500 dark:text-slate-300 shadow-sm">
                                            {loc.pastor?.charAt(0) || 'P'}
                                        </div>
                                        <div>
                                            <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Responsable</p>
                                            <p className="text-sm font-bold text-slate-800 dark:text-slate-200">Pastor {loc.pastor || 'No asignado'}</p>
                                        </div>
                                    </div>
                                    <button className="p-3 text-slate-300 hover:text-blue-600 transition-all hover:bg-blue-50 dark:hover:bg-white/5 rounded-xl">
                                        <Edit2 size={18} />
                                    </button>
                                </div>
                            </motion.div>
                        ))}
                    </div>
                )}
            </main>

            {/* Creation Modal Cinematic */}
            <AnimatePresence>
                {isModalOpen && (
                    <motion.div 
                        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                        className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-slate-950/40 backdrop-blur-xl"
                    >
                        <motion.div 
                            initial={{ scale: 0.9, y: 20 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.9, y: 20 }}
                            className="w-full max-w-xl bg-white dark:bg-[#1e1f21] rounded-[3rem] shadow-2xl overflow-hidden border border-white/20 dark:border-white/5"
                        >
                            <div className="p-10 border-b border-slate-100 dark:border-white/5 flex justify-between items-center bg-slate-50/50 dark:bg-black/20">
                                <div>
                                    <h2 className="text-2xl font-black text-slate-900 dark:text-white uppercase tracking-tighter">Aperturar Sede</h2>
                                    <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mt-1">Configuración de Nuevo Nodo</p>
                                </div>
                                <button onClick={() => setIsModalOpen(false)} className="p-3 hover:bg-white dark:hover:bg-white/5 rounded-full transition-all text-slate-400 hover:text-slate-900"><X size={24} /></button>
                            </div>
                            <form onSubmit={handleCreate} className="p-10 space-y-6">
                                <div className="space-y-2">
                                    <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 ml-2">Nombre de la Sede</label>
                                    <input required value={newLoc.name} onChange={e => setNewLoc({...newLoc, name: e.target.value})} className="w-full px-6 py-4 bg-slate-100 dark:bg-white/5 border-transparent focus:border-blue-500 rounded-2xl text-sm font-bold outline-none transition-all" placeholder="Ej: Sede Norte" />
                                </div>
                                <div className="space-y-2">
                                    <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 ml-2">Dirección</label>
                                    <input value={newLoc.address} onChange={e => setNewLoc({...newLoc, address: e.target.value})} className="w-full px-6 py-4 bg-slate-100 dark:bg-white/5 border-transparent focus:border-blue-500 rounded-2xl text-sm font-bold outline-none transition-all" placeholder="Calle #, Barrio..." />
                                </div>
                                <div className="grid grid-cols-2 gap-6">
                                    <div className="space-y-2">
                                        <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 ml-2">Pastor Encargado</label>
                                        <input value={newLoc.pastor} onChange={e => setNewLoc({...newLoc, pastor: e.target.value})} className="w-full px-6 py-4 bg-slate-100 dark:bg-white/5 border-transparent focus:border-blue-500 rounded-2xl text-sm font-bold outline-none transition-all" placeholder="Nombre" />
                                    </div>
                                    <div className="space-y-2">
                                        <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 ml-2">Tipo</label>
                                        <select value={newLoc.type} onChange={e => setNewLoc({...newLoc, type: e.target.value})} className="w-full px-6 py-4 bg-slate-100 dark:bg-white/5 border-transparent focus:border-blue-500 rounded-2xl text-sm font-bold outline-none transition-all appearance-none">
                                            <option value="Central">Central</option>
                                            <option value="Sede">Sede</option>
                                            <option value="Anexo">Anexo</option>
                                        </select>
                                    </div>
                                </div>
                                <button type="submit" className="w-full py-5 bg-blue-600 text-white rounded-[2rem] font-black text-xs uppercase tracking-widest shadow-2xl shadow-blue-500/30 hover:bg-blue-700 active:scale-95 transition-all flex items-center justify-center gap-3">
                                    Confirmar Apertura <Check size={18} />
                                </button>
                            </form>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
