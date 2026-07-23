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
    const [newLoc, setNewLoc] = useState({ nombre: '', address: '', pastor: '', type: 'Sede' });

    const fetchLocations = useCallback(async (signal?: AbortSignal) => {
        if (!token) return;
        setLoading(true);
        try {
            const data = await apiFetch<{ items: Location[]; total: number }>('/admin/locations', { token, cache: 'no-store', signal });
            setLocations(data?.items ?? []);
        } catch (err) {
            console.error(err);
            addToast("Error al cargar sedes", "error");
        } finally {
            setLoading(false);
        }
    }, [token, addToast]);

    useEffect(() => {
        if (!isAuthenticated) return;
        const controller = new AbortController();
        fetchLocations(controller.signal);
        return () => controller.abort();
    }, [isAuthenticated, fetchLocations]);

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            await apiFetch('/admin/locations', { method: 'POST', token, body: newLoc });
            addToast("Sede registrada", "success");
            setIsDrawerOpen(false);
            setNewLoc({ nombre: '', address: '', pastor: '', type: 'Sede' });
            fetchLocations();
        } catch {
            addToast("Error al registrar sede", "error");
        }
    };

    if (!isAuthenticated) return null;

    return (
        <div className="flex flex-col h-full bg-[hsl(var(--surface-1))] dark:bg-[#0a0f16] font-display overflow-hidden">
            {/* Header Area */}
            <div className="bg-[hsl(var(--bg-primary))] dark:bg-white/5 border-b border-[hsl(var(--border))] dark:border-white/10 sticky top-0 z-50 p-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <button onClick={() => router.back()} className="p-3 rounded-lg bg-[hsl(var(--surface-2))] dark:bg-white/5 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] transition-all">
                        <ArrowLeft size={20} />
                    </button>
                    <div>
                        <h1 className="text-xl font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tighter uppercase leading-none">Gestión de Sedes</h1>
                        <p className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide mt-1">Nodos Ministeriales CCF</p>
                    </div>
                </div>
                <button
                    onClick={() => setIsDrawerOpen(true)}
                    className="flex items-center gap-3 px-4 py-1.5 bg-[hsl(var(--primary))] text-white rounded-lg text-[11px] font-semibold uppercase tracking-wide shadow-xl shadow-[hsl(var(--info)/20%)] active:scale-95 transition-all"
                >
                    <PlusCircle size={18} /> Añadir Nueva Sede
                </button>
            </div>

            <main className="flex-1 overflow-y-auto p-4 lg:p-4 space-y-3 scrollbar-thin">
                {loading ? (
                    <div className="flex flex-col items-center justify-center py-1.5 gap-4 text-[hsl(var(--text-secondary))] font-semibold uppercase tracking-wide animate-pulse">
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
                                    "bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg p-4 flex flex-col gap-3 shadow-sm group hover:border-[hsl(var(--info)/100%)]/30 transition-all relative overflow-hidden",
                                    !loc.active && "opacity-60"
                                )}
                            >
                                <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:scale-110 transition-transform duration-700">
                                    <Church size={120} />
                                </div>

                                <div className="flex items-start justify-between relative z-10">
                                    <div className="flex gap-3">
                                        <div className="size-8 rounded-lg bg-info-soft dark:bg-[hsl(var(--info))]/20 text-[hsl(var(--primary))] flex items-center justify-center shadow-inner group-hover:bg-[hsl(var(--primary))] group-hover:text-white transition-all duration-500">
                                            {loc.type === 'Central' ? <Church size={32} /> : loc.type === 'Sede' ? <Building2 size={32} /> : <DoorOpen size={32} />}
                                        </div>
                                        <div className="space-y-1">
                                            <h3 className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tight uppercase leading-none">{loc.name}</h3>
                                            <p className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide flex items-center gap-2">
                                                <MapPin size={12} className="text-[hsl(var(--primary))]" />
                                                {loc.address || 'Sin dirección registrada'}
                                            </p>
                                        </div>
                                    </div>
                                </div>

                                <div className="flex items-center justify-between pt-8 border-t border-[hsl(var(--border))] dark:border-white/5 relative z-10">
                                    <div className="flex items-center gap-4">
                                        <div className="size-10 rounded-full border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-2))] dark:bg-white/10 flex items-center justify-center text-xs font-semibold text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] shadow-sm">
                                            {loc.pastor?.charAt(0) || 'P'}
                                        </div>
                                        <div>
                                            <p className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Responsable</p>
                                            <p className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">Pastor {loc.pastor || 'No asignado'}</p>
                                        </div>
                                    </div>
                                    <button className="p-3 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] transition-all hover:bg-info-soft dark:hover:bg-white/5 rounded-md">
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
                        <button type="button" onClick={() => setIsDrawerOpen(false)} className="px-4 py-2 text-[11px] font-bold text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] transition-colors">
                            Cancelar
                        </button>
                        <button
                            form="location-create-form"
                            type="submit"
                            className="px-4 py-2 bg-[hsl(var(--primary))] text-white rounded-lg text-[11px] font-semibold uppercase tracking-wide shadow-lg shadow-[hsl(var(--info)/20%)] hover:bg-[hsl(var(--primary))] active:scale-95 transition-all"
                        >
                            Confirmar Apertura
                        </button>
                    </>
                }
            >
                <form id="location-create-form" onSubmit={handleCreate} className="space-y-3">
                    <div className="space-y-2">
                        <label className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Nombre de la Sede *</label>
                        <input required value={newLoc.nombre} onChange={e => setNewLoc({...newLoc, nombre: e.target.value})} className="w-full px-3 py-1.5 bg-[hsl(var(--surface-1))] dark:bg-black/20 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg text-sm font-bold outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.2] dark:text-white transition-all" placeholder="Ej: Sede Norte" />
                    </div>
                    <div className="space-y-2">
                        <label className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Dirección</label>
                        <input value={newLoc.address} onChange={e => setNewLoc({...newLoc, address: e.target.value})} className="w-full px-3 py-1.5 bg-[hsl(var(--surface-1))] dark:bg-black/20 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg text-sm font-bold outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.2] dark:text-white transition-all" placeholder="Calle #, Barrio..." />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <label className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Pastor Encargado</label>
                            <input value={newLoc.pastor} onChange={e => setNewLoc({...newLoc, pastor: e.target.value})} className="w-full px-3 py-1.5 bg-[hsl(var(--surface-1))] dark:bg-black/20 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg text-sm font-bold outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.2] dark:text-white transition-all" placeholder="Nombre" />
                        </div>
                        <div className="space-y-2">
                            <label className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Tipo</label>
                            <select value={newLoc.type} onChange={e => setNewLoc({...newLoc, type: e.target.value})} className="w-full px-3 py-1.5 bg-[hsl(var(--surface-1))] dark:bg-black/20 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg text-sm font-bold outline-none transition-all appearance-none dark:text-white">
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
