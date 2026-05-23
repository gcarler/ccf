"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import {
    ArrowLeft,
    Church,
    MapPin,
    Edit2,
    PlusCircle,
    Building2,
    DoorOpen,
    Loader2,
} from 'lucide-react';
import { motion } from 'framer-motion';
import clsx from 'clsx';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';

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
    const [isDrawerOpen, setIsDrawerOpen] = useState(false);
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
            await apiFetch('/admin/locations', { method: 'POST', token, body: newLoc });
            addToast("Sede registrada", "success");
            setIsDrawerOpen(false);
            setNewLoc({ name: '', address: '', pastor: '', type: 'Sede' });
            fetchLocations();
        } catch {
            addToast("Error al registrar sede", "error");
        }
    };

    if (!isAuthenticated) return null;

    return (
        <div className="flex flex-col h-full bg-slate-50 dark:bg-[#0a0f16] font-display overflow-hidden">
            {/* Header Area */}
            <div className="bg-white dark:bg-white/5 border-b border-slate-200 dark:border-white/10 sticky top-0 z-50 p-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <button onClick={() => router.back()} className="p-3 rounded-lg bg-slate-100 dark:bg-white/5 text-slate-500 hover:text-blue-600 transition-all">
                        <ArrowLeft size={20} />
                    </button>
                    <div>
                        <h1 className="text-xl font-bold text-slate-900 dark:text-white tracking-tighter uppercase leading-none">Gestión de Sedes</h1>
                        <p className="font-semibold text-slate-400 uppercase tracking-wide mt-1">Nodos Ministeriales CCF</p>
                    </div>
                </div>
                <button
                    onClick={() => setIsDrawerOpen(true)}
                    className="flex items-center gap-3 px-4 py-1.5 bg-blue-600 text-white rounded-lg text-[11px] font-semibold uppercase tracking-wide shadow-xl shadow-blue-500/20 active:scale-95 transition-all"
                >
                    <PlusCircle size={18} /> Añadir Nueva Sede
                </button>
            </div>

            <main className="flex-1 overflow-y-auto p-4 lg:p-4 space-y-3 scrollbar-thin">
                {loading ? (
                    <div className="flex flex-col items-center justify-center py-1.5 gap-4 text-slate-400 font-semibold uppercase tracking-wide animate-pulse">
                        <Loader2 className="animate-spin" size={40} /> Sincronizando Sedes...
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 pb-4">
                        {locations.map((loc, i) => (
                            <motion.div
                                initial={{ opacity: 0, scale: 0.9 }}
                                animate={{ opacity: 1, scale: 1 }}
                                transition={{ delay: i * 0.05 }}
                                key={loc.id}
                                className={clsx(
                                    "bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg p-4 flex flex-col gap-3 shadow-sm group hover:border-blue-500/30 transition-all relative overflow-hidden",
                                    !loc.active && "opacity-60"
                                )}
                            >
                                <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:scale-110 transition-transform duration-700">
                                    <Church size={120} />
                                </div>

                                <div className="flex items-start justify-between relative z-10">
                                    <div className="flex gap-3">
                                        <div className="size-8 rounded-lg bg-blue-50 dark:bg-blue-900/20 text-blue-600 flex items-center justify-center shadow-inner group-hover:bg-blue-600 group-hover:text-white transition-all duration-500">
                                            {loc.type === 'Central' ? <Church size={32} /> : loc.type === 'Sede' ? <Building2 size={32} /> : <DoorOpen size={32} />}
                                        </div>
                                        <div className="space-y-1">
                                            <h3 className="text-lg font-bold text-slate-900 dark:text-white tracking-tight uppercase leading-none">{loc.name}</h3>
                                            <p className="font-semibold text-slate-400 uppercase tracking-wide flex items-center gap-2">
                                                <MapPin size={12} className="text-blue-500" />
                                                {loc.address || 'Sin dirección registrada'}
                                            </p>
                                        </div>
                                    </div>
                                </div>

                                <div className="flex items-center justify-between pt-8 border-t border-slate-100 dark:border-white/5 relative z-10">
                                    <div className="flex items-center gap-4">
                                        <div className="size-10 rounded-full border border-slate-200 dark:border-white/10 bg-slate-100 dark:bg-white/10 flex items-center justify-center text-xs font-semibold text-slate-500 dark:text-slate-300 shadow-sm">
                                            {loc.pastor?.charAt(0) || 'P'}
                                        </div>
                                        <div>
                                            <p className="font-semibold text-slate-400 uppercase tracking-wide">Responsable</p>
                                            <p className="text-sm font-bold text-slate-800 dark:text-slate-200">Pastor {loc.pastor || 'No asignado'}</p>
                                        </div>
                                    </div>
                                    <button className="p-3 text-slate-300 hover:text-blue-600 transition-all hover:bg-blue-50 dark:hover:bg-white/5 rounded-md">
                                        <Edit2 size={18} />
                                    </button>
                                </div>
                            </motion.div>
                        ))}
                    </div>
                )}
            </main>

            <WorkspaceDrawer
                isOpen={isDrawerOpen}
                onClose={() => setIsDrawerOpen(false)}
                title="Aperturar Sede"
                subtitle="Configuración de nuevo nodo ministerial"
                actions={
                    <>
                        <button type="button" onClick={() => setIsDrawerOpen(false)} className="px-4 py-2 text-[11px] font-bold text-slate-500 hover:text-slate-700 transition-colors">
                            Cancelar
                        </button>
                        <button
                            form="location-create-form"
                            type="submit"
                            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-[11px] font-semibold uppercase tracking-wide shadow-lg shadow-blue-500/20 hover:bg-blue-700 active:scale-95 transition-all"
                        >
                            Confirmar Apertura
                        </button>
                    </>
                }
            >
                <form id="location-create-form" onSubmit={handleCreate} className="space-y-6">
                    <div className="space-y-2">
                        <label className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Nombre de la Sede *</label>
                        <input required value={newLoc.name} onChange={e => setNewLoc({...newLoc, name: e.target.value})} className="w-full px-3 py-1.5 bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-lg text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500/20 dark:text-white transition-all" placeholder="Ej: Sede Norte" />
                    </div>
                    <div className="space-y-2">
                        <label className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Dirección</label>
                        <input value={newLoc.address} onChange={e => setNewLoc({...newLoc, address: e.target.value})} className="w-full px-3 py-1.5 bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-lg text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500/20 dark:text-white transition-all" placeholder="Calle #, Barrio..." />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <label className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Pastor Encargado</label>
                            <input value={newLoc.pastor} onChange={e => setNewLoc({...newLoc, pastor: e.target.value})} className="w-full px-3 py-1.5 bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-lg text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500/20 dark:text-white transition-all" placeholder="Nombre" />
                        </div>
                        <div className="space-y-2">
                            <label className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Tipo</label>
                            <select value={newLoc.type} onChange={e => setNewLoc({...newLoc, type: e.target.value})} className="w-full px-3 py-1.5 bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-lg text-sm font-bold outline-none transition-all appearance-none dark:text-white">
                                <option value="Central">Central</option>
                                <option value="Sede">Sede</option>
                                <option value="Anexo">Anexo</option>
                            </select>
                        </div>
                    </div>
                </form>
            </WorkspaceDrawer>
        </div>
    );
}

