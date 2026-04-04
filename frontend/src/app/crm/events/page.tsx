'use client';

import React, { useState, useEffect } from 'react';
import { apiFetch } from '@/lib/http';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { Plus, Calendar, Check, X as CloseIcon, Link2, Users, Clock, MoreHorizontal } from 'lucide-react';
import ViewSwitcher, { ViewType, getStoredView } from '@/components/ViewSwitcher';
import CrmShell from '@/components/crm/CrmShell';
import AdminHero from '@/components/admin/AdminHero';

const EVENT_TYPE_LABEL: Record<string, string> = {
    PERMANENT: 'Semanal',
    ANNUAL: 'Anual',
    ONCE: 'Única Vez',
};

const DAY_LABELS = ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado'];

interface Event {
    id: number;
    name: string;
    description: string;
    event_type: string; // PERMANENT, ANNUAL, ONCE
    day_of_week?: number;
    month_day?: string;
    fixed_date?: string;
}

interface Member {
    id: number;
    first_name: string;
    last_name: string;
    email: string;
}

export default function EventsPage() {
    const { token } = useAuth();
    const { addToast } = useToast();
    const [viewType, setViewType] = useState<ViewType>(() => getStoredView('crm_events_view', 'grid'));
    const ALL_VIEWS: ViewType[] = ['table', 'list', 'grid', 'board', 'kanban', 'gantt', 'calendar'];
    const [events, setEvents] = useState<Event[]>([]);
    const [members, setMembers] = useState<Member[]>([]);
    const [loading, setLoading] = useState(true);

    // Modal states
    const [isRegModalOpen, setIsRegModalOpen] = useState(false);
    const [isAttendanceModalOpen, setIsAttendanceModalOpen] = useState(false);
    const [showScanner, setShowScanner] = useState(false);
    const [scannerToken, setScannerToken] = useState('');
    const [isScanning, setIsScanning] = useState(false);

    const handleScanToken = async () => {
        if (!scannerToken || !selectedEvent) return;
        setIsScanning(true);
        try {
            const result = await apiFetch<any>(`/crm/scanner/validate/${scannerToken}`, {
                method: 'POST',
                token
            });
            
            if (result.valid) {
                const mid = result.member_id;
                if (!attendedMemberIds.includes(mid)) {
                    setAttendedMemberIds(prev => [...prev, mid]);
                    addToast(`¡Bienvenido ${result.member_name}!`, "success");
                } else {
                    addToast(`${result.member_name} ya está marcado`, "info");
                }
                setScannerToken('');
            }
        } catch (err) {
            addToast("Token de escaneo inválido", "error");
        } finally {
            setIsScanning(false);
        }
    };
    const [selectedEvent, setSelectedEvent] = useState<Event | null>(null);

    // Form states
    const [newEvent, setNewEvent] = useState({
        name: '',
        description: '',
        event_type: 'PERMANENT',
        day_of_week: '0',
        month_day: '',
        fixed_date: ''
    });

    // Attendance State
    const [attendanceDate, setAttendanceDate] = useState(new Date().toISOString().split('T')[0]);
    const [attendedMemberIds, setAttendedMemberIds] = useState<number[]>([]);

    const fetchData = async () => {
        setLoading(true);
        try {
            const [eventsRes, membersRes] = await Promise.all([
                apiFetch<Event[]>('/crm/events/', { token, cache: 'no-store' }),
                apiFetch<Member[]>('/crm/members/', { token, cache: 'no-store' })
            ]);
            setEvents(Array.isArray(eventsRes) ? eventsRes : []);
            setMembers(Array.isArray(membersRes) ? membersRes : []);
        } catch (err) {
            addToast("Error al cargar datos", "error");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [token]);

    const handleCreateEvent = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!newEvent.name) return;

        let payload: any = {
            name: newEvent.name,
            description: newEvent.description,
            event_type: newEvent.event_type,
        };

        if (newEvent.event_type === 'PERMANENT') payload.day_of_week = parseInt(newEvent.day_of_week);
        if (newEvent.event_type === 'ANNUAL') payload.month_day = newEvent.month_day;
        if (newEvent.event_type === 'ONCE') payload.fixed_date = new Date(newEvent.fixed_date).toISOString();

        try {
            await apiFetch('/crm/events/', {
                method: 'POST',
                token,
                body: payload
            });

            addToast("Evento creado exitosamente", "success");
            setIsRegModalOpen(false);
            setNewEvent({ name: '', description: '', event_type: 'PERMANENT', day_of_week: '0', month_day: '', fixed_date: '' });
            fetchData();
        } catch (err) {
            addToast("Error de conexión", "error");
        }
    };

    const openAttendance = (ev: Event) => {
        setSelectedEvent(ev);
        setIsAttendanceModalOpen(true);
        setAttendanceDate(new Date().toISOString().split('T')[0]);
        setAttendedMemberIds([]); // Could fetch existing attendance here
    };

    const saveAttendance = async () => {
        if (!selectedEvent) return;

        try {
            const result = await apiFetch<any>('/crm/attendance/bulk', {
                method: 'POST',
                token,
                body: {
                    event_id: selectedEvent.id,
                    member_ids: attendedMemberIds,
                    attendance_date: new Date(attendanceDate).toISOString()
                }
            });
            
            if (result.recorded > 0) {
                addToast(`Registro de asistencia guardado (${result.recorded} presentes)`, "success");
            } else {
                addToast("No se registraron cambios nuevos", "info");
            }
            setIsAttendanceModalOpen(false);
            fetchData();
        } catch (err) {
            addToast("Error al guardar asistencia", "error");
        }
    };

    const toggleAttendance = (id: number) => {
        if (attendedMemberIds.includes(id)) {
            setAttendedMemberIds(prev => prev.filter(mId => mId !== id));
        } else {
            setAttendedMemberIds(prev => [...prev, id]);
        }
    };

    const heroWatchers = ['Eventos', 'Optimus Brain'];

    return (
        <CrmShell
            breadcrumbs={[{ label: 'CCF', icon: Calendar }, { label: 'CRM Pastoral', icon: Users }, { label: 'Eventos', icon: Calendar }]}
            viewOptions={ALL_VIEWS}
            viewType={viewType}
            onViewChange={(view) => setViewType(view as ViewType)}
            rightActions={
                <button
                    onClick={() => setIsRegModalOpen(true)}
                    className="flex items-center gap-2 bg-blue-600 px-5 py-2 rounded-2xl text-[11px] font-black text-white hover:bg-blue-700 transition-all shadow-lg shadow-blue-900/20 uppercase tracking-widest"
                >
                    <Plus size={16} /> Nuevo evento
                </button>
            }
        >
        <AdminHero
            eyebrow="Eventos"
            title="Eventos y asistencia"
            description="Programa encuentros recurrentes y registra la participación en tiempo real con paneles estilo ClickUp."
            tags={['Agenda', 'Asistencia', 'IA']}
            watchers={heroWatchers}
            primaryAction={{ label: 'Crear evento', icon: Plus, onClick: () => setIsRegModalOpen(true) }}
            secondaryAction={{ label: 'Ver calendario', icon: Link2, onClick: () => setViewType('grid') }}
        />
        <div className="space-y-8">

            {/* Toolbar: View Switcher (inline secondary) */}
            <div className="flex items-center justify-end">
                <ViewSwitcher
                    viewType={viewType}
                    setViewType={setViewType}
                    availableViews={ALL_VIEWS}
                    storageKey="crm_events_view"
                />
            </div>

            {loading ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {Array.from({ length: 6 }).map((_, i) => (
                        <div key={i} className="animate-pulse h-48 rounded-[2rem] bg-slate-100" />
                    ))}
                </div>
            ) : (
            <>
            {/* GRID VIEW */}
            {viewType === 'grid' && (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {events.map(ev => (
                        <div key={ev.id} className="p-6 rounded-[2rem] border border-slate-100 dark:border-white/5 bg-white dark:bg-[#1e1f21] hover:border-blue-100 hover:shadow-2xl hover:shadow-blue-50 transition-all group flex flex-col justify-between">
                            <div>
                                <div className="flex justify-between items-start mb-4">
                                    <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-blue-50 to-indigo-50 text-blue-600 flex items-center justify-center">
                                        <Calendar size={20} />
                                    </div>
                                    <span className="px-3 py-1 bg-slate-50 dark:bg-white/10 text-slate-500 dark:text-slate-400 text-[10px] font-black uppercase tracking-widest rounded-full">{ev.event_type}</span>
                                </div>
                                <h3 className="text-lg font-black text-slate-900 dark:text-white mb-2 truncate">{ev.name}</h3>
                                <p className="text-sm font-medium text-slate-500 line-clamp-2">{ev.description || 'Evento comunitario de CCF.'}</p>
                            </div>
                            <button onClick={() => openAttendance(ev)} className="mt-6 w-full py-3 bg-slate-50 dark:bg-white/5 group-hover:bg-blue-600 text-slate-500 group-hover:text-white rounded-xl text-[10px] font-black uppercase tracking-widest transition-all">
                                Panel de Asistencia
                            </button>
                        </div>
                    ))}
                </div>
            )}

            {/* LIST VIEW */}
            {viewType === 'list' && (
                <div className="bg-white dark:bg-[#1e1f21] rounded-[2rem] border border-slate-100 dark:border-white/5 overflow-hidden shadow-sm divide-y divide-slate-100 dark:divide-white/5">
                    {events.map(ev => (
                        <div key={ev.id} className="flex items-center gap-4 px-6 py-4 hover:bg-slate-50 dark:hover:bg-white/5 transition-colors group">
                            <div className="w-9 h-9 rounded-xl bg-blue-50 dark:bg-blue-900/20 text-blue-600 flex items-center justify-center shrink-0">
                                <Calendar size={16} />
                            </div>
                            <div className="flex-1 min-w-0">
                                <p className="font-bold text-slate-800 dark:text-slate-100 text-sm truncate">{ev.name}</p>
                                <p className="text-xs text-slate-400 truncate">{ev.description || 'Sin descripción'}</p>
                            </div>
                            <span className="px-2.5 py-0.5 rounded-full bg-slate-100 dark:bg-white/10 text-slate-500 text-[10px] font-black uppercase">{ev.event_type}</span>
                            <button onClick={() => openAttendance(ev)} className="px-3 py-1.5 rounded-xl bg-blue-50 dark:bg-blue-900/20 text-blue-600 text-[10px] font-black uppercase opacity-0 group-hover:opacity-100 transition-opacity">
                                Asistencia
                            </button>
                        </div>
                    ))}
                </div>
            )}

            {/* KANBAN VIEW */}
            {viewType === 'kanban' && (
                <div className="flex gap-4 overflow-x-auto pb-6">
                    {['PERMANENT', 'ANNUAL', 'ONCE'].map(type => (
                        <div key={type} className="flex-none w-72">
                            <div className="flex items-center justify-between mb-3">
                                <h3 className="text-[11px] font-black uppercase tracking-widest text-slate-500">
                                    {type === 'PERMANENT' ? 'Semanal' : type === 'ANNUAL' ? 'Anual' : 'Única Vez'}
                                </h3>
                                <span className="text-[11px] font-bold bg-slate-100 dark:bg-white/10 text-slate-500 px-2 py-0.5 rounded-full">{events.filter(e => e.event_type === type).length}</span>
                            </div>
                            <div className="flex flex-col gap-3">
                                {events.filter(e => e.event_type === type).map(ev => (
                                    <div key={ev.id} className="p-4 rounded-2xl border border-slate-100 dark:border-white/5 bg-white dark:bg-[#1e1f21] shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all cursor-pointer group">
                                        <div className="flex items-center gap-3 mb-2">
                                            <Calendar size={14} className="text-blue-500 shrink-0" />
                                            <p className="font-bold text-slate-800 dark:text-slate-100 text-sm truncate">{ev.name}</p>
                                        </div>
                                        {ev.description && <p className="text-[11px] text-slate-400 line-clamp-2 mb-3">{ev.description}</p>}
                                        <button onClick={() => openAttendance(ev)} className="w-full py-1.5 rounded-xl bg-slate-50 dark:bg-white/5 group-hover:bg-blue-600 group-hover:text-white text-slate-400 text-[10px] font-black uppercase tracking-widest transition-all">
                                            Asistencia
                                        </button>
                                    </div>
                                ))}
                                {events.filter(e => e.event_type === type).length === 0 && (
                                    <div className="flex items-center justify-center py-8 rounded-2xl border-2 border-dashed border-slate-100 dark:border-white/5 text-slate-300 text-xs">Sin eventos</div>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* TABLE VIEW */}
            {viewType === 'table' && (
                <div className="bg-white dark:bg-[#1e1f21] rounded-[2rem] border border-slate-100 dark:border-white/5 overflow-hidden shadow-sm">
                    <table className="w-full">
                        <thead>
                            <tr className="border-b border-slate-100 dark:border-white/5">
                                {['#', 'Nombre', 'Tipo', 'Frecuencia', 'Descripción', 'Acciones'].map(col => (
                                    <th key={col} className="px-5 py-3 text-left text-[10px] font-black uppercase tracking-widest text-slate-400">{col}</th>
                                ))}
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-50 dark:divide-white/5">
                            {events.map((ev, i) => (
                                <tr key={ev.id} className="hover:bg-slate-50 dark:hover:bg-white/5 transition-colors group">
                                    <td className="px-5 py-3.5 text-xs font-bold text-slate-400">{i + 1}</td>
                                    <td className="px-5 py-3.5">
                                        <div className="flex items-center gap-2.5">
                                            <div className="size-7 rounded-lg bg-blue-50 dark:bg-blue-900/20 flex items-center justify-center">
                                                <Calendar size={13} className="text-blue-600" />
                                            </div>
                                            <span className="text-sm font-bold text-slate-800 dark:text-white">{ev.name}</span>
                                        </div>
                                    </td>
                                    <td className="px-5 py-3.5">
                                        <span className="px-2.5 py-1 rounded-full bg-slate-50 dark:bg-white/10 text-slate-500 text-[10px] font-black uppercase">
                                            {EVENT_TYPE_LABEL[ev.event_type] ?? ev.event_type}
                                        </span>
                                    </td>
                                    <td className="px-5 py-3.5 text-xs font-medium text-slate-500">
                                        {ev.event_type === 'PERMANENT' && ev.day_of_week !== undefined ? DAY_LABELS[ev.day_of_week] : '—'}
                                    </td>
                                    <td className="px-5 py-3.5 text-xs text-slate-400 max-w-[240px] truncate">{ev.description || '—'}</td>
                                    <td className="px-5 py-3.5">
                                        <button onClick={() => openAttendance(ev)} className="px-3 py-1.5 rounded-lg bg-blue-50 dark:bg-blue-900/20 text-blue-600 text-[10px] font-black uppercase tracking-widest opacity-0 group-hover:opacity-100 transition-opacity">
                                            Asistencia
                                        </button>
                                    </td>
                                </tr>
                            ))}
                            {events.length === 0 && (
                                <tr><td colSpan={6} className="px-5 py-16 text-center text-slate-400 text-sm">No hay eventos registrados</td></tr>
                            )}
                        </tbody>
                    </table>
                </div>
            )}

            {/* BOARD VIEW — agrupado por tipo */}
            {viewType === 'board' && (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {(['PERMANENT', 'ANNUAL', 'ONCE'] as const).map(type => {
                        const typeEvents = events.filter(e => e.event_type === type);
                        return (
                            <div key={type} className="bg-white dark:bg-[#1e1f21] rounded-[2rem] border border-slate-100 dark:border-white/5 overflow-hidden shadow-sm">
                                <div className="px-5 py-4 border-b border-slate-100 dark:border-white/5 flex items-center justify-between">
                                    <div>
                                        <span className="text-[11px] font-black uppercase tracking-widest text-slate-500">{EVENT_TYPE_LABEL[type]}</span>
                                    </div>
                                    <span className="size-5 rounded-full bg-blue-50 dark:bg-blue-900/20 text-blue-600 text-[10px] font-black flex items-center justify-center">{typeEvents.length}</span>
                                </div>
                                <div className="p-3 space-y-2 min-h-[200px]">
                                    {typeEvents.map(ev => (
                                        <div key={ev.id} className="p-4 rounded-xl bg-slate-50 dark:bg-white/5 border border-transparent hover:border-blue-100 dark:hover:border-white/10 transition-all group cursor-pointer">
                                            <div className="flex items-start justify-between gap-2">
                                                <p className="font-bold text-sm text-slate-800 dark:text-white line-clamp-1">{ev.name}</p>
                                                <button onClick={() => openAttendance(ev)} className="shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                                                    <MoreHorizontal size={14} className="text-slate-400" />
                                                </button>
                                            </div>
                                            {ev.description && <p className="text-xs text-slate-400 mt-1 line-clamp-2">{ev.description}</p>}
                                            {ev.day_of_week !== undefined && (
                                                <div className="flex items-center gap-1 mt-2">
                                                    <Clock size={10} className="text-blue-500" />
                                                    <span className="text-[10px] font-bold text-slate-400">{DAY_LABELS[ev.day_of_week]}</span>
                                                </div>
                                            )}
                                        </div>
                                    ))}
                                    {typeEvents.length === 0 && (
                                        <div className="flex items-center justify-center h-24 text-slate-300 text-xs">Sin eventos</div>
                                    )}
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}

            {/* GANTT VIEW — línea de tiempo por día de la semana */}
            {viewType === 'gantt' && (
                <div className="bg-white dark:bg-[#1e1f21] rounded-[2rem] border border-slate-100 dark:border-white/5 overflow-hidden shadow-sm">
                    <div className="p-5 border-b border-slate-100 dark:border-white/5">
                        <p className="text-[11px] font-black uppercase tracking-widest text-slate-400">Línea de tiempo semanal — eventos recurrentes</p>
                    </div>
                    <div className="p-5 overflow-x-auto">
                        {/* Day headers */}
                        <div className="grid grid-cols-7 gap-2 mb-4">
                            {DAY_LABELS.map(d => (
                                <div key={d} className="text-center text-[9px] font-black uppercase tracking-widest text-slate-400 py-2 bg-slate-50 dark:bg-white/5 rounded-lg">{d.slice(0, 3)}</div>
                            ))}
                        </div>
                        {/* Event rows */}
                        <div className="space-y-2">
                            {events.filter(e => e.event_type === 'PERMANENT').map(ev => (
                                <div key={ev.id} className="grid grid-cols-7 gap-2 items-center min-h-[48px]">
                                    {DAY_LABELS.map((_, idx) => (
                                        <div key={idx} className={`rounded-xl p-2 transition-all ${
                                            ev.day_of_week === idx
                                                ? 'bg-blue-600 shadow-lg shadow-blue-500/20'
                                                : 'bg-slate-50 dark:bg-white/5'
                                        }`}>
                                            {ev.day_of_week === idx && (
                                                <div>
                                                    <p className="text-[10px] font-black text-white leading-none truncate">{ev.name}</p>
                                                    <p className="text-[8px] text-blue-100 mt-0.5 uppercase tracking-widest">Semanal</p>
                                                </div>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            ))}
                            {events.filter(e => e.event_type !== 'PERMANENT').map(ev => (
                                <div key={ev.id} className="grid grid-cols-7 gap-2 items-center min-h-[48px]">
                                    <div className="col-span-7 bg-indigo-50 dark:bg-indigo-900/20 rounded-xl px-4 py-2 flex items-center justify-between">
                                        <p className="text-sm font-bold text-indigo-800 dark:text-indigo-200">{ev.name}</p>
                                        <span className="px-2 py-0.5 rounded-full bg-indigo-100 dark:bg-indigo-800/30 text-indigo-600 text-[9px] font-black uppercase">{EVENT_TYPE_LABEL[ev.event_type]}</span>
                                    </div>
                                </div>
                            ))}
                            {events.length === 0 && (
                                <div className="py-16 text-center text-slate-400 text-sm">Sin eventos para mostrar en el timeline</div>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* CALENDAR VIEW — vista semanal de eventos fijos */}
            {viewType === 'calendar' && (
                <div className="bg-white dark:bg-[#1e1f21] rounded-[2rem] border border-slate-100 dark:border-white/5 overflow-hidden shadow-sm">
                    <div className="p-5 border-b border-slate-100 dark:border-white/5 flex items-center justify-between">
                        <p className="text-[11px] font-black uppercase tracking-widest text-slate-400">Calendario semanal de eventos</p>
                        <div className="flex items-center gap-2">
                            <span className="size-2 rounded-full bg-blue-500" />
                            <span className="text-[10px] font-bold text-slate-400">Semanal</span>
                            <span className="size-2 rounded-full bg-indigo-400 ml-3" />
                            <span className="text-[10px] font-bold text-slate-400">Puntual</span>
                        </div>
                    </div>
                    <div className="p-5">
                        <div className="grid grid-cols-7 gap-3">
                            {DAY_LABELS.map((day, idx) => {
                                const dayEvents = events.filter(e => e.event_type === 'PERMANENT' && e.day_of_week === idx);
                                return (
                                    <div key={day} className="flex flex-col gap-2">
                                        <div className={`text-center py-3 rounded-xl text-[10px] font-black uppercase tracking-widest ${
                                            idx === 0 || idx === 6 ? 'bg-blue-50 text-blue-600 dark:bg-blue-900/20' : 'bg-slate-50 dark:bg-white/5 text-slate-500'
                                        }`}>{day.slice(0, 3)}</div>
                                        <div className="space-y-1.5 min-h-[120px]">
                                            {dayEvents.map(ev => (
                                                <button
                                                    key={ev.id}
                                                    onClick={() => openAttendance(ev)}
                                                    className="w-full text-left p-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 transition-colors shadow-sm shadow-blue-500/20 group"
                                                >
                                                    <p className="text-[10px] font-black text-white leading-tight line-clamp-2">{ev.name}</p>
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                        {/* Eventos no recurrentes */}
                        {events.filter(e => e.event_type !== 'PERMANENT').length > 0 && (
                            <div className="mt-6 pt-5 border-t border-slate-100 dark:border-white/5">
                                <p className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-3">Eventos Puntuales</p>
                                <div className="flex flex-wrap gap-2">
                                    {events.filter(e => e.event_type !== 'PERMANENT').map(ev => (
                                        <div key={ev.id} className="px-4 py-2 rounded-xl bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-100 dark:border-indigo-800/20">
                                            <p className="text-sm font-bold text-indigo-800 dark:text-indigo-200">{ev.name}</p>
                                            <p className="text-[10px] text-indigo-400 mt-0.5">{EVENT_TYPE_LABEL[ev.event_type]}</p>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            )}

            </>
            )}

            {/* Registration Modal */}
            {isRegModalOpen && (
                <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-slate-950/20 backdrop-blur-md animate-in fade-in duration-300">
                    <div className="w-full max-w-xl bg-white rounded-[2rem] shadow-2xl border border-white/20 overflow-hidden animate-in zoom-in-95 duration-300">
                        <div className="p-8 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
                            <div>
                                <h2 className="text-xl font-black text-slate-900 uppercase tracking-tight">Nuevo Evento</h2>
                                <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mt-1">Configura un evento de la iglesia</p>
                            </div>
                            <button onClick={() => setIsRegModalOpen(false)} className="p-3 bg-white text-slate-400 hover:text-slate-900 rounded-full transition-all shadow-sm">
                                <CloseIcon size={20} />
                            </button>
                        </div>
                        <form onSubmit={handleCreateEvent} className="p-8 space-y-6">
                            <div className="space-y-1.5">
                                <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Nombre del Evento *</label>
                                <input
                                    required
                                    value={newEvent.name}
                                    onChange={e => setNewEvent({ ...newEvent, name: e.target.value })}
                                    className="w-full px-4 py-3 rounded-2xl border border-slate-100 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm"
                                    placeholder="Ej: Servicio Dominical"
                                />
                            </div>

                            <div className="space-y-1.5">
                                <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Tipo de Evento *</label>
                                <select
                                    required
                                    value={newEvent.event_type}
                                    onChange={e => setNewEvent({ ...newEvent, event_type: e.target.value })}
                                    className="w-full px-4 py-3 rounded-2xl border border-slate-100 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm appearance-none bg-white"
                                >
                                    <option value="PERMANENT">Semanal / Rutinario</option>
                                    <option value="ANNUAL">Anual</option>
                                    <option value="ONCE">Única Vez</option>
                                </select>
                            </div>

                            {newEvent.event_type === 'PERMANENT' && (
                                <div className="space-y-1.5">
                                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Día de la Semana</label>
                                    <select
                                        value={newEvent.day_of_week}
                                        onChange={e => setNewEvent({ ...newEvent, day_of_week: e.target.value })}
                                        className="w-full px-4 py-3 rounded-2xl border border-slate-100 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm bg-white"
                                    >
                                        <option value="0">Domingo</option>
                                        <option value="1">Lunes</option>
                                        <option value="2">Martes</option>
                                        <option value="3">Miércoles</option>
                                        <option value="4">Jueves</option>
                                        <option value="5">Viernes</option>
                                        <option value="6">Sábado</option>
                                    </select>
                                </div>
                            )}

                            {newEvent.event_type === 'ONCE' && (
                                <div className="space-y-1.5">
                                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Fecha Exacta</label>
                                    <input
                                        type="date"
                                        value={newEvent.fixed_date}
                                        onChange={e => setNewEvent({ ...newEvent, fixed_date: e.target.value })}
                                        className="w-full px-4 py-3 rounded-2xl border border-slate-100 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm"
                                    />
                                </div>
                            )}

                            <div className="pt-4 flex gap-3">
                                <button
                                    type="button"
                                    onClick={() => setIsRegModalOpen(false)}
                                    className="flex-1 py-4 bg-slate-50 text-slate-400 rounded-2xl text-[10px] font-black uppercase tracking-widest hover:bg-slate-100 transition-all border border-slate-100"
                                >
                                    Cancelar
                                </button>
                                <button
                                    type="submit"
                                    className="flex-2 px-12 py-4 bg-blue-600 text-white rounded-2xl text-[10px] font-black uppercase tracking-widest hover:bg-blue-700 transition-all shadow-xl shadow-blue-100 flex items-center justify-center gap-2"
                                >
                                    Guardar <Check size={16} />
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Attendance Modal */}
            {isAttendanceModalOpen && selectedEvent && (
                <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-slate-950/20 backdrop-blur-md animate-in fade-in duration-300">
                    <div className="w-full max-w-4xl max-h-[90vh] flex flex-col bg-white rounded-[2rem] shadow-2xl border border-white/20 overflow-hidden animate-in zoom-in-95 duration-300">
                        <div className="p-8 border-b border-slate-100 flex justify-between items-center bg-blue-50/30">
                            <div>
                                <h2 className="text-xl font-black text-slate-900 uppercase tracking-tight">Registro de Asistencia</h2>
                                <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mt-1">{selectedEvent.name}</p>
                            </div>
                            <div className="flex items-center gap-4">
                                <button 
                                    onClick={() => setShowScanner(!showScanner)}
                                    className={`px-4 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all ${showScanner ? 'bg-rose-500 text-white' : 'bg-slate-900 text-white hover:bg-slate-800'}`}
                                >
                                    {showScanner ? 'Cerrar Escáner' : 'Modo Escáner'}
                                </button>
                                <div className="flex items-center gap-2 bg-white px-4 py-2 border border-slate-100 rounded-xl">
                                    <Calendar size={16} className="text-slate-400" />
                                    <input
                                        type="date"
                                        value={attendanceDate}
                                        onChange={(e) => setAttendanceDate(e.target.value)}
                                        className="text-sm font-bold text-slate-700 outline-none bg-transparent"
                                    />
                                </div>
                                <button onClick={() => setIsAttendanceModalOpen(false)} className="p-3 bg-white border border-slate-100 text-slate-400 hover:text-slate-900 rounded-full transition-all shadow-sm">
                                    <CloseIcon size={20} />
                                </button>
                            </div>
                        </div>

                        {showScanner && (
                            <div className="p-8 bg-slate-900 border-b border-white/10 animate-in slide-in-from-top duration-300">
                                <div className="max-w-md mx-auto space-y-4 text-center">
                                    <div className="w-20 h-20 mx-auto border-2 border-dashed border-blue-500 rounded-2xl flex items-center justify-center text-blue-500 animate-pulse">
                                        <Users size={32} />
                                    </div>
                                    <h3 className="text-white font-black uppercase tracking-widest text-xs">Simulador de Escáner Cámara</h3>
                                    <p className="text-[10px] text-slate-400">Ingresa el token del carnet (formato: CCF-MBR-ID-TOKEN)</p>
                                    <div className="flex gap-2">
                                        <input 
                                            type="text"
                                            value={scannerToken}
                                            onChange={(e) => setScannerToken(e.target.value)}
                                            placeholder="CCF-MBR-1-XXXXXX"
                                            className="flex-1 bg-slate-950 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-blue-500"
                                            onKeyDown={(e) => e.key === 'Enter' && handleScanToken()}
                                        />
                                        <button 
                                            onClick={handleScanToken}
                                            disabled={isScanning || !scannerToken}
                                            className="px-6 py-3 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-xl text-[10px] font-black uppercase tracking-widest transition-all"
                                        >
                                            {isScanning ? 'Validando...' : 'Validar'}
                                        </button>
                                    </div>
                                </div>
                            </div>
                        )}

                        <div className="p-8 overflow-y-auto flex-1 bg-slate-50/30">
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                {members.map(member => (
                                    <div
                                        key={member.id}
                                        onClick={() => toggleAttendance(member.id)}
                                        className={`flex items-center p-4 rounded-2xl cursor-pointer transition-all border ${attendedMemberIds.includes(member.id)
                                            ? 'bg-emerald-50 border-emerald-200 shadow-sm'
                                            : 'bg-white border-slate-100 hover:border-slate-300'
                                            }`}
                                    >
                                        <div className={`w-6 h-6 rounded-full border-2 flex items-center justify-center mr-4 transition-colors ${attendedMemberIds.includes(member.id)
                                            ? 'bg-emerald-500 border-emerald-500 text-white'
                                            : 'border-slate-300 bg-slate-50'
                                            }`}>
                                            {attendedMemberIds.includes(member.id) && <Check size={12} strokeWidth={4} />}
                                        </div>
                                        <div>
                                            <p className={`font-bold text-sm ${attendedMemberIds.includes(member.id) ? 'text-emerald-900' : 'text-slate-700'}`}>
                                                {member.first_name} {member.last_name}
                                            </p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>

                        <div className="p-6 border-t border-slate-100 bg-white flex justify-between items-center">
                            <p className="text-sm font-bold text-slate-500">
                                Total presentes: <span className="text-emerald-600 font-black">{attendedMemberIds.length}</span> / {members.length}
                            </p>
                            <button
                                onClick={saveAttendance}
                                className="px-8 py-4 bg-emerald-600 text-white rounded-2xl text-[10px] font-black uppercase tracking-widest hover:bg-emerald-700 transition-all shadow-xl shadow-emerald-100"
                            >
                                Guardar Registro
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
        </CrmShell>
    );
}
