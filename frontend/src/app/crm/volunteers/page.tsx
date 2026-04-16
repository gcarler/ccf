"use client";

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
    Calendar,
    Users,
    CheckCircle2,
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
    Zap,
    ChevronLeft,
    Loader2,
    Send,
    X
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import CrmShell from '@/components/crm/CrmShell';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';
import { ViewType, getStoredView } from '@/components/ViewSwitcher';
import CrmViewPlaceholder from '@/components/crm/CrmViewPlaceholder';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import { useRouter } from 'next/navigation';
import { useSidebarLayers } from '@/context/SidebarLayerContext';
import ShiftDetailSidebar from '@/components/crm/ShiftDetailSidebar';

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

/** Computes the Monday of the current week */
function getWeekMonday(offset = 0): Date {
    const today = new Date();
    const dayOfWeek = (today.getDay() + 6) % 7; // 0=Mon, 6=Sun
    const monday = new Date(today);
    monday.setDate(today.getDate() - dayOfWeek + offset * 7);
    monday.setHours(0, 0, 0, 0);
    return monday;
}

export default function VolunteerCalendar() {
    const { token, isAuthenticated, user } = useAuth();
    const router = useRouter();
    const { addToast } = useToast();
    const [shifts, setShifts] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [weekOffset, setWeekOffset] = useState(0);
    const [viewMode, setViewMode] = useState<'week' | 'list' | 'table' | 'calendar' | 'gantt' | 'wiki' | 'board'>(
        () => {
            const saved = getStoredView('crm_volunteers_view', 'grid');
            if (saved === 'list' || saved === 'table' || saved === 'calendar' || saved === 'gantt' || saved === 'wiki' || saved === 'board') return saved as any;
            return 'week';
        }
    );
    const [isApplyDrawerOpen, setIsApplyDrawerOpen] = useState(false);
    const [applyForm, setApplyForm] = useState({ team: '', availability: '', notes: '' });
    const { pushSidebarPanel, popSidebarPanel } = useSidebarLayers();
    const [isSaving, setIsSaving] = useState(false);

    const [wikiNotes, setWikiNotes] = useState('');
    const ALL_VIEWS: ViewType[] = ['table', 'list', 'grid', 'board', 'kanban', 'gantt', 'calendar', 'wiki'];
    const crmViewType: ViewType = viewMode === 'week' ? 'grid' : viewMode === 'board' ? 'board' : viewMode;
    const handleViewChange = (v: ViewType) => {
        if (v === 'grid') setViewMode('week');
        else if (v === 'kanban' || v === 'board') setViewMode('board');
        else if (v === 'list' || v === 'table' || v === 'calendar' || v === 'gantt' || v === 'wiki') setViewMode(v);
        else setViewMode('week');
    };

    const monday = useMemo(() => getWeekMonday(weekOffset), [weekOffset]);

    const weekLabel = useMemo(() => {
        const end = new Date(monday);
        end.setDate(monday.getDate() + 6);
        const fmt = (d: Date) => d.toLocaleDateString('es-ES', { day: 'numeric', month: 'short' });
        return `${fmt(monday)} — ${fmt(end)}`;
    }, [monday]);

    const fetchShifts = useCallback(async () => {
        if (!token) return;
        setLoading(true);
        try {
            const data = await apiFetch<any[]>('/crm/volunteers/shifts', { token, cache: 'no-store' });
            if (!Array.isArray(data)) { setShifts([]); return; }
            const mapped = data.map(s => {
                const start = new Date(s.shift_start);
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
        } catch {
            addToast("Error al cargar calendario de servicio", "error");
        } finally {
            setLoading(false);
        }
    }, [token, addToast]);

    useEffect(() => {
        if (isAuthenticated) fetchShifts();
    }, [isAuthenticated, fetchShifts]);

    useEffect(() => {
        const saved = localStorage.getItem('crm_volunteers_wiki_notes');
        if (saved) setWikiNotes(saved);
    }, []);

    const openShiftDetail = (shift: any) => {
        pushSidebarPanel({
            id: `shift-detail-${shift.id}`,
            title: shift.role_name || 'Detalle de Turno',
            content: <ShiftDetailSidebar shift={shift} onClose={popSidebarPanel} />
        });
    };

    const handleApply = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsSaving(true);
        try {
            await apiFetch('/crm/volunteers/apply', {
                method: 'POST', token,
                body: { ...applyForm, member_id: (user as any)?.id }
            });
            addToast('¡Solicitud enviada! El equipo pastoral te contactará.', 'success');
            setIsApplyDrawerOpen(false);
            setApplyForm({ team: '', availability: '', notes: '' });
        } catch {
            addToast('Error al enviar solicitud', 'error');
        } finally {
            setIsSaving(false);
        }
    };

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
                <button
                    onClick={() => setIsApplyDrawerOpen(true)}
                    className="flex items-center gap-2 px-6 py-2 bg-blue-600 text-white rounded-xl text-[11px] font-black uppercase tracking-widest shadow-xl shadow-blue-500/20 active:scale-95 transition-all"
                >
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
                        <button
                            onClick={() => setWeekOffset(w => w - 1)}
                            className="p-3 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl text-slate-400 hover:text-blue-600 transition-all"
                        >
                            <ChevronLeft size={20} />
                        </button>
                        <span className="text-[13px] font-black text-slate-800 dark:text-white uppercase tracking-widest min-w-[180px] text-center">{weekLabel}</span>
                        <button
                            onClick={() => setWeekOffset(w => w + 1)}
                            className="p-3 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl text-slate-400 hover:text-blue-600 transition-all"
                        >
                            <ChevronRight size={20} />
                        </button>
                        {weekOffset !== 0 && (
                            <button
                                onClick={() => setWeekOffset(0)}
                                className="px-4 py-2 text-[10px] font-black uppercase text-blue-600 bg-blue-50 dark:bg-blue-900/20 rounded-xl hover:bg-blue-100 transition-all"
                            >
                                Hoy
                            </button>
                        )}
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
                            {DAYS.map((day, idx) => {
                                const colDate = new Date(monday);
                                colDate.setDate(monday.getDate() + idx);
                                const today = new Date();
                                today.setHours(0, 0, 0, 0);
                                const isToday = colDate.toDateString() === today.toDateString();
                                return (
                                    <div key={day} className="flex flex-col gap-4 min-w-0 h-full">
                                        <div className={`text-center p-4 border rounded-2xl shadow-sm shrink-0 ${isToday ? 'bg-blue-600 border-blue-600' : 'bg-white dark:bg-white/5 border-slate-200 dark:border-white/10'}`}>
                                            <p className={`text-[10px] font-black uppercase tracking-[0.2em] mb-1 ${isToday ? 'text-blue-100' : 'text-slate-400'}`}>{day}</p>
                                            <p className={`text-lg font-black leading-none ${isToday ? 'text-white' : 'text-slate-800 dark:text-white'}`}>{colDate.getDate()}</p>
                                        </div>

                                        <div className="flex-1 bg-slate-100/30 dark:bg-black/10 rounded-[2rem] p-3 space-y-3 overflow-y-auto scrollbar-hide border-2 border-transparent hover:border-blue-500/10 transition-all min-h-[120px]">
                                            {shifts.filter(s => s.dayIndex === idx).map(shift => (
                                                <motion.div
                                                    key={shift.id} whileHover={{ scale: 1.02 }}
                                                    onClick={() => openShiftDetail(shift)}
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
                                                    <div className="relative z-10 space-y-2">
                                                        <p className="text-[9px] font-black uppercase tracking-widest opacity-80">{shift.time}</p>
                                                        <h4 className="text-[13px] font-black uppercase leading-tight tracking-tight">{shift.role_name}</h4>
                                                        <div className="flex items-center justify-between">
                                                            <div className="text-[8px] font-black uppercase tracking-widest bg-white/20 px-2 py-0.5 rounded">{shift.team_name}</div>
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
                                );
                            })}
                        </motion.div>
                    ) : viewMode === 'list' ? (
                        <motion.div
                            key="list-view" initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.98 }}
                            className="flex-1 space-y-4 overflow-y-auto scrollbar-thin pr-4 pb-20"
                        >
                            {shifts.length > 0 ? shifts.map((shift) => (
                                <div key={shift.id} onClick={() => openShiftDetail(shift)} className="p-8 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-[2.5rem] shadow-sm hover:shadow-xl transition-all flex items-center justify-between cursor-pointer">
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
                                    <button onClick={() => setIsApplyDrawerOpen(true)} className="px-6 py-3 bg-blue-600 text-white rounded-xl text-xs font-black uppercase tracking-widest shadow-lg shadow-blue-500/20">
                                        Postularme al ministerio
                                    </button>
                                </div>
                            )}
                        </motion.div>
                    ) : viewMode === 'table' ? (
                        <motion.div key="table-view" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex-1 overflow-y-auto">
                            <div className="rounded-2xl border border-slate-200 dark:border-white/10 overflow-hidden bg-white dark:bg-white/5">
                                <table className="w-full text-left">
                                    <thead className="bg-slate-50 dark:bg-white/5">
                                        <tr>
                                            <th className="px-4 py-3 text-[10px] font-black uppercase tracking-widest text-slate-400">Rol</th>
                                            <th className="px-4 py-3 text-[10px] font-black uppercase tracking-widest text-slate-400">Equipo</th>
                                            <th className="px-4 py-3 text-[10px] font-black uppercase tracking-widest text-slate-400">Fecha</th>
                                            <th className="px-4 py-3 text-[10px] font-black uppercase tracking-widest text-slate-400">Hora</th>
                                            <th className="px-4 py-3 text-[10px] font-black uppercase tracking-widest text-slate-400">Estado</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {shifts.map(shift => (
                                            <tr key={shift.id} onClick={() => openShiftDetail(shift)} className="border-t border-slate-100 dark:border-white/5 cursor-pointer hover:bg-slate-50 dark:hover:bg-white/5">
                                                <td className="px-4 py-3 text-sm font-bold text-slate-800 dark:text-slate-100">{shift.role_name}</td>
                                                <td className="px-4 py-3 text-xs text-slate-500">{shift.team_name}</td>
                                                <td className="px-4 py-3 text-xs text-slate-500">{new Date(shift.shift_start).toLocaleDateString()}</td>
                                                <td className="px-4 py-3 text-xs text-slate-500">{shift.time}</td>
                                                <td className="px-4 py-3 text-xs font-black uppercase text-slate-500">{shift.status}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </motion.div>
                    ) : viewMode === 'board' ? (
                        <motion.div key="board-view" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-4 overflow-y-auto">
                            {['confirmed', 'pending', 'open'].map(status => (
                                <div key={status} className="rounded-2xl border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/[0.03] p-3">
                                    <div className="mb-3 flex items-center justify-between"><p className="text-[10px] font-black uppercase tracking-widest text-slate-500">{status}</p><span className="text-[10px] font-black text-slate-400">{shifts.filter(s => (s.status || 'open') === status).length}</span></div>
                                    <div className="space-y-2">
                                        {shifts.filter(s => (s.status || 'open') === status).map(shift => (
                                            <div key={shift.id} onClick={() => openShiftDetail(shift)} className="rounded-xl border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 p-3 cursor-pointer hover:border-blue-500/30 transition-all">
                                                <p className="text-xs font-black text-slate-800 dark:text-slate-100">{shift.role_name}</p>
                                                <p className="text-[10px] text-slate-400">{shift.team_name} · {shift.time}</p>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            ))}
                        </motion.div>
                    ) : (
                        <CrmViewPlaceholder
                            viewType={crmViewType}
                            items={shifts}
                            wikiKey="crm_volunteers_wiki_notes"
                        />
                    )}
                </AnimatePresence>
            </div>
        </main>

        {/* ─── Drawer: Postularme ─── */}
        <WorkspaceDrawer
            isOpen={isApplyDrawerOpen}
            onClose={() => setIsApplyDrawerOpen(false)}
            title="Postularme al Ministerio"
            subtitle="Únete al equipo de servidores"
            actions={
                <>
                    <button type="button" onClick={() => setIsApplyDrawerOpen(false)} className="px-4 py-2 text-[11px] font-bold text-slate-500 hover:text-slate-700 transition-colors">
                        Cancelar
                    </button>
                    <button
                        form="apply-form"
                        type="submit"
                        disabled={isSaving}
                        className="px-8 py-2 bg-blue-600 text-white rounded-lg text-[11px] font-black uppercase tracking-widest shadow-lg shadow-blue-500/20 hover:bg-blue-700 active:scale-95 transition-all flex items-center gap-2"
                    >
                        {isSaving ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
                        Enviar solicitud
                    </button>
                </>
            }
        >
            <form id="apply-form" onSubmit={handleApply} className="space-y-6">
                <div className="space-y-2">
                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Equipo de servicio *</label>
                    <select
                        required
                        value={applyForm.team}
                        onChange={e => setApplyForm({ ...applyForm, team: e.target.value })}
                        className="w-full px-4 py-3 rounded-2xl border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-black/20 outline-none focus:ring-2 focus:ring-blue-500/20 font-bold text-sm dark:text-white appearance-none"
                    >
                        <option value="">Selecciona un equipo...</option>
                        {Object.keys(iconMap).map(team => <option key={team} value={team}>{team}</option>)}
                    </select>
                </div>
                <div className="space-y-2">
                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Disponibilidad</label>
                    <input
                        value={applyForm.availability}
                        onChange={e => setApplyForm({ ...applyForm, availability: e.target.value })}
                        placeholder="Ej: Domingos AM, Miércoles PM..."
                        className="w-full px-4 py-3 rounded-2xl border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-black/20 outline-none focus:ring-2 focus:ring-blue-500/20 font-bold text-sm dark:text-white"
                    />
                </div>
                <div className="space-y-2">
                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Motivación / Experiencia</label>
                    <textarea
                        value={applyForm.notes}
                        onChange={e => setApplyForm({ ...applyForm, notes: e.target.value })}
                        placeholder="Cuéntanos por qué quieres servir..."
                        rows={4}
                        className="w-full px-4 py-3 rounded-2xl border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-black/20 outline-none focus:ring-2 focus:ring-blue-500/20 font-bold text-sm dark:text-white resize-none"
                    />
                </div>
            </form>
        </WorkspaceDrawer>

        </CrmShell>
    );
}
