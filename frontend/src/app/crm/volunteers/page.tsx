"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { 
    Calendar, 
    Users, 
    CheckCircle2, 
    Clock, 
    Plus, 
    ChevronRight, 
    MoreHorizontal,
    Music,
    Baby,
    Heart,
    Shield,
    ShieldCheck,
    Camera,
    Coffee,
    ArrowUpRight,
    Search,
    Filter,
    Bot,
    Zap,
    ChevronLeft,
    Loader2
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import CrmShell from '@/components/crm/CrmShell';
import { ViewType, getStoredView } from '@/components/ViewSwitcher';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';

const DAYS = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'];

const iconMap: Record<string, any> = {
    'Alabanza': Music,
    'Generación G': Baby,
    'Niños': Baby,
    'Hospitalidad': Coffee,
    'Ujieres': Coffee,
    'Oración': Zap,
    'Seguridad': Shield,
    'Media': Camera,
};

const colorMap: Record<string, string> = {
    'Alabanza': 'blue',
    'Generación G': 'purple',
    'Hospitalidad': 'amber',
    'Oración': 'indigo',
    'Seguridad': 'slate',
    'Media': 'rose'
};

export default function VolunteerCalendar() {
    const { token, isAuthenticated } = useAuth();
    const { addToast } = useToast();
    const [shifts, setShifts] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [viewMode, setViewMode] = useState<'week' | 'list'>(
        () => (getStoredView('crm_volunteers_view', 'grid') === 'list' ? 'list' : 'week')
    );
    const ALL_VIEWS: ViewType[] = ['table', 'list', 'grid', 'board', 'kanban', 'gantt', 'calendar'];

    // Map CrmShell ViewType -> internal view mode
    const crmViewType: ViewType = viewMode === 'list' ? 'list' : 'grid';
    const handleViewChange = (v: ViewType) => {
        setViewMode(v === 'list' ? 'list' : 'week');
    };

    const fetchShifts = useCallback(async () => {
        if (!token) return;
        setLoading(true);
        try {
            const data = await apiFetch<any[]>('/crm/volunteers/shifts', { token, cache: 'no-store' });
            // Adaptar datos del backend al formato del calendario
            const mapped = data.map(s => {
                const start = new Date(s.shift_start);
                // Calcular dayIndex (0 = Lunes, 6 = Domingo)
                let dIdx = start.getDay() - 1;
                if (dIdx === -1) dIdx = 6; 

                return {
                    ...s,
                    dayIndex: dIdx,
                    time: start.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' }),
                    icon: iconMap[s.team_name] || Heart,
                    color: colorMap[s.team_name] || 'blue'
                };
            });
            setShifts(mapped);
        } catch (error) {
            console.error(error);
            addToast("Error al cargar calendario de servicio", "error");
        } finally {
            setLoading(false);
        }
    }, [token, addToast]);

    useEffect(() => {
        if (isAuthenticated) fetchShifts();
    }, [isAuthenticated, fetchShifts]);

    if (!isAuthenticated) return null;

    return (
        <CrmShell
            breadcrumbs={[
                { label: 'CCF', icon: Heart },
                { label: 'CRM Pastoral', icon: Users },
                { label: 'Servidores', icon: ShieldCheck }
            ]}
            viewOptions={ALL_VIEWS}
            viewType={crmViewType}
            onViewChange={handleViewChange}
            rightActions={
                <button className="flex items-center gap-2 px-6 py-2 bg-blue-600 text-white rounded-xl text-[11px] font-black uppercase tracking-widest shadow-xl shadow-blue-500/20 active:scale-95 transition-all">
                    <Plus size={14} /> Postularme
                </button>
            }
        >
        <main className="flex-1 overflow-hidden flex flex-col p-4 lg:p-6">
            <div className="max-w-[1600px] mx-auto w-full flex-1 flex flex-col gap-8">
                    
                    {/* Header Controls */}
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 shrink-0">
                        <div className="flex items-center gap-6">
                            <h2 className="text-3xl font-black tracking-tighter text-slate-900 dark:text-white uppercase leading-none">Cronograma de Servicio</h2>
                            <div className="flex items-center gap-2 bg-white dark:bg-white/5 p-1 rounded-2xl border border-slate-200 dark:border-white/10 shadow-sm">
                                <button 
                                    onClick={() => setViewMode('week')}
                                    className={clsx("px-6 py-2 rounded-[0.9rem] text-[10px] font-black uppercase transition-all", 
                                    viewMode === 'week' ? "bg-blue-600 text-white shadow-lg shadow-blue-500/20" : "text-slate-400 hover:text-slate-600")}
                                >
                                    Semana
                                </button>
                                <button 
                                    onClick={() => setViewMode('list')}
                                    className={clsx("px-6 py-2 rounded-[0.9rem] text-[10px] font-black uppercase transition-all", 
                                    viewMode === 'list' ? "bg-blue-600 text-white shadow-lg shadow-blue-500/20" : "text-slate-400 hover:text-slate-600")}
                                >
                                    Lista
                                </button>
                            </div>
                        </div>
                        <div className="flex items-center gap-4">
                            <button className="p-3 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl text-slate-400 hover:text-blue-600 transition-all"><ChevronLeft size={20} /></button>
                            <span className="text-[13px] font-black text-slate-800 dark:text-white uppercase tracking-widest">Semana Actual</span>
                            <button className="p-3 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl text-slate-400 hover:text-blue-600 transition-all"><ChevronRight size={20} /></button>
                        </div>
                    </div>

                    <AnimatePresence mode="wait">
                        {loading ? (
                            <div className="flex-1 flex flex-col items-center justify-center gap-4">
                                <Loader2 className="animate-spin text-blue-600" size={48} />
                                <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Sincronizando cronograma ministerial...</p>
                            </div>
                        ) : viewMode === 'week' ? (
                            <motion.div 
                                key="week-grid" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }}
                                className="flex-1 grid grid-cols-1 md:grid-cols-7 gap-4 min-h-0"
                            >
                                {DAYS.map((day, idx) => (
                                    <div key={day} className="flex flex-col gap-4 min-w-0 h-full">
                                        <div className="text-center p-4 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-2xl shadow-sm shrink-0">
                                            <p className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] mb-1">{day}</p>
                                            <p className={clsx("text-lg font-black leading-none", idx === 6 ? "text-blue-600" : "text-slate-800 dark:text-white")}>{new Date().getDate() + (idx - (new Date().getDay() || 7) + 1)}</p>
                                        </div>
                                        
                                        <div className="flex-1 bg-slate-100/30 dark:bg-black/10 rounded-[2rem] p-3 space-y-3 overflow-y-auto scrollbar-hide border-2 border-transparent hover:border-blue-500/10 transition-all">
                                            {shifts.filter(s => s.dayIndex === idx).map(shift => (
                                                <motion.div 
                                                    key={shift.id} whileHover={{ scale: 1.02 }}
                                                    className={clsx(
                                                        "p-4 rounded-2xl shadow-sm border border-transparent hover:border-white/20 transition-all cursor-pointer relative overflow-hidden group",
                                                        shift.color === 'blue' ? "bg-blue-600 text-white" : 
                                                        shift.color === 'purple' ? "bg-purple-600 text-white" : 
                                                        shift.color === 'amber' ? "bg-amber-500 text-white" : 
                                                        shift.color === 'indigo' ? "bg-indigo-600 text-white" : "bg-slate-800 text-white"
                                                    )}
                                                >
                                                    <div className="absolute top-0 right-0 -mr-4 -mt-4 p-6 opacity-10 group-hover:opacity-20 transition-all">
                                                        <shift.icon size={48} />
                                                    </div>
                                                    <div className="relative z-10 space-y-3">
                                                        <p className="text-[9px] font-black uppercase tracking-widest opacity-80">{shift.time}</p>
                                                        <h4 className="text-[13px] font-black uppercase leading-tight tracking-tight">{shift.role_name}</h4>
                                                        <div className="flex items-center justify-between">
                                                            <div className="text-[8px] font-black uppercase tracking-widest bg-white/20 px-2 py-0.5 rounded">
                                                                {shift.team_name}
                                                            </div>
                                                            {shift.status === 'confirmed' && <CheckCircle2 size={14} className="text-white/80" />}
                                                        </div>
                                                    </div>
                                                </motion.div>
                                            ))}
                                            <button className="w-full py-4 border-2 border-dashed border-slate-200 dark:border-white/5 rounded-2xl text-slate-400 hover:border-blue-500/30 hover:text-blue-500 transition-all flex items-center justify-center">
                                                <Plus size={16} />
                                            </button>
                                        </div>
                                    </div>
                                ))}
                            </motion.div>
                        ) : (
                            <motion.div 
                                key="list-view" initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.98 }}
                                className="flex-1 space-y-4 overflow-y-auto scrollbar-thin pr-4 pb-20"
                            >
                                {shifts.length > 0 ? shifts.map((shift) => (
                                    <div key={shift.id} className="p-8 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-[2.5rem] shadow-sm hover:shadow-xl transition-all flex items-center justify-between">
                                        <div className="flex items-center gap-6">
                                            <div className={clsx("size-14 rounded-2xl flex items-center justify-center", 
                                                shift.color === 'blue' ? "bg-blue-50 text-blue-600" : "bg-purple-50 text-purple-600")}>
                                                <shift.icon size={28} />
                                            </div>
                                            <div>
                                                <h4 className="text-xl font-black text-slate-900 dark:text-white uppercase leading-none mb-2">{shift.role_name}</h4>
                                                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{new Date(shift.shift_start).toLocaleDateString()} • {shift.time} • {shift.team_name}</p>
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-4">
                                            <span className={clsx("px-4 py-1.5 rounded-xl text-[9px] font-black uppercase tracking-widest", 
                                                shift.status === 'confirmed' ? "bg-emerald-50 text-emerald-600" : "bg-amber-50 text-amber-600")}>
                                                {shift.status}
                                            </span>
                                            <button className="p-2 text-slate-300 hover:text-slate-600"><MoreHorizontal size={20} /></button>
                                        </div>
                                    </div>
                                )) : (
                                    <div className="py-40 flex flex-col items-center justify-center text-center space-y-6">
                                        <Calendar size={64} strokeWidth={1} className="text-slate-200" />
                                        <p className="text-xl font-black text-slate-400 uppercase tracking-tighter">No hay turnos registrados</p>
                                    </div>
                                )}
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>
            </main>
        </CrmShell>
    );
}
