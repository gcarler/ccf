'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { apiFetch } from '@/lib/http';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { Plus, Calendar, Check, Users, Clock, MoreHorizontal, Link2, X as CloseIcon } from 'lucide-react';
import ViewSwitcher, { ViewType, getStoredView } from '@/components/ViewSwitcher';
import CrmShell from '@/components/crm/CrmShell';
import AdminHero from '@/components/admin/AdminHero';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';
import SplitDropdownButton from '@/components/ui/SplitDropdownButton';
import CrmViewPlaceholder from '@/components/crm/CrmViewPlaceholder';

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
    event_type: string;
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
    const router = useRouter();
    const { addToast } = useToast();
    const [viewType, setViewType] = useState<ViewType>(() => getStoredView('crm_events_view', 'grid'));
    const ALL_VIEWS: ViewType[] = ['table', 'list', 'grid', 'board', 'kanban', 'gantt', 'calendar', 'wiki'];
    const [events, setEvents] = useState<Event[]>([]);
    const [members, setMembers] = useState<Member[]>([]);
    const [loading, setLoading] = useState(true);
    const [wikiNotes, setWikiNotes] = useState('');

    // Drawer states (NO modals)
    const [isCreateDrawerOpen, setIsCreateDrawerOpen] = useState(false);
    const [isAttendanceDrawerOpen, setIsAttendanceDrawerOpen] = useState(false);
    const [selectedEvent, setSelectedEvent] = useState<Event | null>(null);

    // Scanner
    const [showScanner, setShowScanner] = useState(false);
    const [scannerToken, setScannerToken] = useState('');
    const [isScanning, setIsScanning] = useState(false);

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
        } catch {
            addToast("Token de escaneo inválido", "error");
        } finally {
            setIsScanning(false);
        }
    };

    const fetchData = async () => {
        setLoading(true);
        try {
            const [eventsRes, membersRes] = await Promise.all([
                apiFetch<Event[]>('/crm/events/', { token, cache: 'no-store' }),
                apiFetch<Member[]>('/crm/members/', { token, cache: 'no-store' })
            ]);
            setEvents(Array.isArray(eventsRes) ? eventsRes : []);
            setMembers(Array.isArray(membersRes) ? membersRes : []);
        } catch {
            addToast("Error al cargar datos", "error");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [token]);

    useEffect(() => {
        const saved = localStorage.getItem('crm_events_wiki_notes');
        if (saved) setWikiNotes(saved);
    }, []);

    useEffect(() => {
        localStorage.setItem('crm_events_wiki_notes', wikiNotes);
    }, [wikiNotes]);

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
            await apiFetch('/crm/events/', { method: 'POST', token, body: payload });
            addToast("Evento creado exitosamente", "success");
            setIsCreateDrawerOpen(false);
            setNewEvent({ name: '', description: '', event_type: 'PERMANENT', day_of_week: '0', month_day: '', fixed_date: '' });
            fetchData();
        } catch {
            addToast("Error de conexión", "error");
        }
    };

    const openAttendance = (ev: Event) => {
        setSelectedEvent(ev);
        setIsAttendanceDrawerOpen(true);
        setAttendanceDate(new Date().toISOString().split('T')[0]);
        setAttendedMemberIds([]);
        setShowScanner(false);
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
                addToast(`Asistencia guardada (${result.recorded} presentes)`, "success");
            } else {
                addToast("No se registraron cambios nuevos", "info");
            }
            setIsAttendanceDrawerOpen(false);
            fetchData();
        } catch {
            addToast("Error al guardar asistencia", "error");
        }
    };

    const toggleAttendance = (id: number) => {
        setAttendedMemberIds(prev =>
            prev.includes(id) ? prev.filter(mId => mId !== id) : [...prev, id]
        );
    };

    const heroWatchers = ['Eventos', 'Optimus Brain'];

    return (
        <CrmShell
            breadcrumbs={[{ label: 'CCF', icon: Calendar }, { label: 'CRM Pastoral', icon: Users }, { label: 'Eventos', icon: Calendar }]}
            viewOptions={ALL_VIEWS}
            viewType={viewType}
            onViewChange={(view) => setViewType(view as ViewType)}
            rightActions={
                <SplitDropdownButton
                    mainLabel="Nuevo"
                    icon={Plus}
                    onMainClick={() => setIsCreateDrawerOpen(true)}
                    options={[
                        { id: 'event', label: 'Evento', icon: Calendar, onClick: () => setIsCreateDrawerOpen(true) },
                        { id: 'attendance', label: 'Pasar Asistencia', icon: Check, onClick: () => setViewType('table') }
                    ]}
                />
            }
        >
        <AdminHero
            eyebrow="Eventos"
            title="Eventos y asistencia"
            description="Programa encuentros recurrentes y registra la participación en tiempo real con paneles estilo ClickUp."
            tags={['Agenda', 'Asistencia', 'IA']}
            watchers={heroWatchers}
            primaryAction={{ label: 'Crear evento', icon: Plus, onClick: () => setIsCreateDrawerOpen(true) }}
            secondaryAction={{ label: 'Ver calendario', icon: Link2, onClick: () => setViewType('grid') }}
        />
        <div className="space-y-8">
            {/* View switcher */}
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
                        <div key={i} className="animate-pulse h-48 rounded-[2rem] bg-slate-100 dark:bg-white/5" />
                    ))}
                </div>
            ) : (
            <>
            {/* GRID VIEW */}
            {viewType === 'grid' && (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {events.length === 0 ? (
                        <div className="col-span-3 py-24 text-center text-slate-400 text-sm">
                            No hay eventos registrados
                        </div>
                    ) : events.map(ev => (
                        <div 
                            key={ev.id} 
                            onClick={() => router.push(`/crm/events/${ev.id}`)}
                            className="p-6 rounded-[2rem] border border-slate-100 dark:border-white/5 bg-white dark:bg-[#1e1f21] hover:border-blue-500/30 hover:shadow-2xl hover:shadow-blue-500/10 transition-all group flex flex-col justify-between cursor-pointer"
                        >
                            <div>
                                <div className="flex justify-between items-start mb-4">
                                    <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-blue-50 to-indigo-50 text-blue-600 flex items-center justify-center">
                                        <Calendar size={20} />
                                    </div>
                                    <span className="px-3 py-1 bg-slate-50 dark:bg-white/10 text-slate-500 dark:text-slate-400 text-[10px] font-black uppercase tracking-widest rounded-full">{EVENT_TYPE_LABEL[ev.event_type] ?? ev.event_type}</span>
                                </div>
                                <h3 className="text-lg font-black text-slate-900 dark:text-white mb-2 truncate group-hover:text-blue-600 transition-colors uppercase italic pr-4">
                                    {ev.name}
                                </h3>
                                <p className="text-sm font-medium text-slate-500 line-clamp-2">{ev.description || 'Evento comunitario de CCF.'}</p>
                            </div>
                            <div className="mt-6 flex items-center justify-between">
                                <button onClick={(e) => { e.stopPropagation(); openAttendance(ev); }} className="flex-1 py-3 bg-slate-50 dark:bg-white/5 group-hover:bg-blue-600 text-slate-500 group-hover:text-white rounded-xl text-[10px] font-black uppercase tracking-widest transition-all">
                                    Panel de Asistencia
                                </button>
                                <ArrowRight size={16} className="ml-3 text-slate-300 group-hover:text-blue-500 transition-all opacity-0 group-hover:opacity-100" />
                            </div>
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
                                <p 
                                    onClick={() => router.push(`/crm/events/${ev.id}`)}
                                    className="font-bold text-slate-800 dark:text-slate-100 text-sm truncate cursor-pointer hover:text-blue-600 transition-colors"
                                >
                                    {ev.name}
                                </p>
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
            </>
            )}
        </div>

        {/* ─── Drawer: Crear Evento ─── */}
        <WorkspaceDrawer
            isOpen={isCreateDrawerOpen}
            onClose={() => setIsCreateDrawerOpen(false)}
            title="Nuevo Evento"
            subtitle="Configura un evento de la iglesia"
            actions={
                <>
                    <button type="button" onClick={() => setIsCreateDrawerOpen(false)} className="px-4 py-2 text-[11px] font-bold text-slate-500 hover:text-slate-700 transition-colors">
                        Cancelar
                    </button>
                    <button
                        form="create-event-form"
                        type="submit"
                        className="px-8 py-2 bg-blue-600 text-white rounded-lg text-[11px] font-black uppercase tracking-widest shadow-lg shadow-blue-500/20 hover:bg-blue-700 active:scale-95 transition-all flex items-center gap-2"
                    >
                        Guardar <Check size={14} />
                    </button>
                </>
            }
        >
            <form id="create-event-form" onSubmit={handleCreateEvent} className="space-y-6">
                <div className="space-y-1.5">
                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Nombre del Evento *</label>
                    <input
                        required
                        value={newEvent.name}
                        onChange={e => setNewEvent({ ...newEvent, name: e.target.value })}
                        className="w-full px-4 py-3 rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-black/20 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm text-slate-800 dark:text-white"
                        placeholder="Ej: Servicio Dominical"
                    />
                </div>

                <div className="space-y-1.5">
                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Tipo de Evento *</label>
                    <select
                        required
                        value={newEvent.event_type}
                        onChange={e => setNewEvent({ ...newEvent, event_type: e.target.value })}
                        className="w-full px-4 py-3 rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-black/20 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm text-slate-800 dark:text-white appearance-none"
                    >
                        <option value="PERMANENT">Semanal / Rutinario</option>
                        <option value="ANNUAL">Anual</option>
                        <option value="ONCE">Única Vez</option>
                    </select>
                </div>

                {newEvent.event_type === 'PERMANENT' && (
                    <div className="space-y-1.5">
                        <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Día de la Semana</label>
                        <select
                            value={newEvent.day_of_week}
                            onChange={e => setNewEvent({ ...newEvent, day_of_week: e.target.value })}
                            className="w-full px-4 py-3 rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-black/20 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm dark:text-white"
                        >
                            {DAY_LABELS.map((d, i) => <option key={i} value={i}>{d}</option>)}
                        </select>
                    </div>
                )}

                {newEvent.event_type === 'ONCE' && (
                    <div className="space-y-1.5">
                        <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Fecha Exacta</label>
                        <input
                            type="date"
                            value={newEvent.fixed_date}
                            onChange={e => setNewEvent({ ...newEvent, fixed_date: e.target.value })}
                            className="w-full px-4 py-3 rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-black/20 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm dark:text-white"
                        />
                    </div>
                )}

                <div className="space-y-1.5">
                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Descripción</label>
                    <textarea
                        value={newEvent.description}
                        onChange={e => setNewEvent({ ...newEvent, description: e.target.value })}
                        rows={3}
                        className="w-full px-4 py-3 rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-black/20 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm dark:text-white resize-none"
                        placeholder="Breve descripción del evento..."
                    />
                </div>
            </form>
        </WorkspaceDrawer>

        {/* ─── Drawer: Registrar Asistencia ─── */}
        <WorkspaceDrawer
            isOpen={isAttendanceDrawerOpen}
            onClose={() => setIsAttendanceDrawerOpen(false)}
            title="Registro de Asistencia"
            subtitle={selectedEvent?.name ?? 'Evento'}
            actions={
                <>
                    <div className="flex items-center gap-2 mr-auto">
                        <Calendar size={14} className="text-slate-400" />
                        <input
                            type="date"
                            value={attendanceDate}
                            onChange={e => setAttendanceDate(e.target.value)}
                            className="text-sm font-bold text-slate-700 dark:text-slate-300 outline-none bg-transparent"
                        />
                    </div>
                    <button onClick={() => setIsAttendanceDrawerOpen(false)} className="px-4 py-2 text-[11px] font-bold text-slate-500">
                        Cancelar
                    </button>
                    <button
                        onClick={saveAttendance}
                        className="px-8 py-2 bg-emerald-600 text-white rounded-lg text-[11px] font-black uppercase tracking-widest shadow-lg shadow-emerald-500/20 hover:bg-emerald-700 active:scale-95 transition-all"
                    >
                        Guardar Registro
                    </button>
                </>
            }
        >
            <div className="space-y-6">
                {/* Scanner section */}
                <div>
                    <button
                        onClick={() => setShowScanner(s => !s)}
                        className={`px-4 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all ${showScanner ? 'bg-rose-500 text-white' : 'bg-slate-900 dark:bg-white/10 text-white hover:opacity-80'}`}
                    >
                        {showScanner ? 'Cerrar Escáner' : 'Modo Escáner'}
                    </button>
                </div>

                {showScanner && (
                    <div className="p-6 bg-slate-900 dark:bg-black/40 rounded-2xl space-y-4">
                        <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest text-center">Ingresa el token del carnet (CCF-MBR-ID-TOKEN)</p>
                        <div className="flex gap-2">
                            <input
                                type="text"
                                value={scannerToken}
                                onChange={e => setScannerToken(e.target.value)}
                                placeholder="CCF-MBR-1-XXXXXX"
                                className="flex-1 bg-slate-950 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-blue-500"
                                onKeyDown={e => e.key === 'Enter' && handleScanToken()}
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
                )}

                {/* Summary badge */}
                <div className="flex items-center justify-between px-4 py-3 bg-emerald-50 dark:bg-emerald-900/20 rounded-2xl border border-emerald-100 dark:border-emerald-900/30">
                    <p className="text-sm font-bold text-slate-600 dark:text-slate-300">Presentes</p>
                    <p className="text-xl font-black text-emerald-600">{attendedMemberIds.length} <span className="text-sm font-bold text-slate-400">/ {members.length}</span></p>
                </div>

                {/* Member list */}
                <div className="grid grid-cols-1 gap-3">
                    {members.map(member => (
                        <div
                            key={member.id}
                            onClick={() => toggleAttendance(member.id)}
                            className={`flex items-center p-4 rounded-2xl cursor-pointer transition-all border ${attendedMemberIds.includes(member.id)
                                ? 'bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200 dark:border-emerald-700/30 shadow-sm'
                                : 'bg-slate-50 dark:bg-white/5 border-slate-100 dark:border-white/5 hover:border-slate-300 dark:hover:border-white/10'
                            }`}
                        >
                            <div className={`w-6 h-6 rounded-full border-2 flex items-center justify-center mr-4 transition-colors shrink-0 ${attendedMemberIds.includes(member.id)
                                ? 'bg-emerald-500 border-emerald-500 text-white'
                                : 'border-slate-300 dark:border-white/20 bg-white dark:bg-black/20'
                            }`}>
                                {attendedMemberIds.includes(member.id) && <Check size={12} strokeWidth={4} />}
                            </div>
                            <p className={`font-bold text-sm ${attendedMemberIds.includes(member.id) ? 'text-emerald-900 dark:text-emerald-200' : 'text-slate-700 dark:text-slate-300'}`}>
                                {member.first_name} {member.last_name}
                            </p>
                        </div>
                    ))}
                    {members.length === 0 && (
                        <div className="py-12 text-center text-slate-400 text-sm">No hay miembros registrados</div>
                    )}
                </div>
            </div>
        </WorkspaceDrawer>

        </CrmShell>
    );
}
