'use client';

import React, { useState, useEffect } from 'react';
import { apiUrl } from '@/lib/api';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { Plus, Calendar, Settings, Clock, Check, X as CloseIcon, LayoutGrid, List } from 'lucide-react';

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
    const [events, setEvents] = useState<Event[]>([]);
    const [members, setMembers] = useState<Member[]>([]);
    const [loading, setLoading] = useState(true);

    // Modal states
    const [isRegModalOpen, setIsRegModalOpen] = useState(false);
    const [isAttendanceModalOpen, setIsAttendanceModalOpen] = useState(false);
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
                fetch(apiUrl('/events/')),
                fetch(apiUrl('/members/'))
            ]);
            if (eventsRes.ok) setEvents(await eventsRes.json());
            if (membersRes.ok) setMembers(await membersRes.json());
        } catch (err) {
            addToast("Error al cargar datos", "error");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

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
            const response = await fetch(apiUrl('/events/'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (response.ok) {
                addToast("Evento creado exitosamente", "success");
                setIsRegModalOpen(false);
                setNewEvent({ name: '', description: '', event_type: 'PERMANENT', day_of_week: '0', month_day: '', fixed_date: '' });
                fetchData();
            } else {
                addToast("Error al crear evento", "error");
            }
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

        let successCount = 0;
        let errorCount = 0;

        for (const memberId of attendedMemberIds) {
            try {
                const response = await fetch(apiUrl('/attendance/'), {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        member_id: memberId,
                        event_id: selectedEvent.id,
                        attendance_date: new Date(attendanceDate).toISOString()
                    })
                });
                if (response.ok) successCount++;
                else errorCount++;
            } catch (err) {
                errorCount++;
            }
        }

        if (successCount > 0) addToast(`Registro de asistencia guardado (${successCount} presentes)`, "success");
        if (errorCount > 0) addToast(`Hubo ${errorCount} errores al guardar`, "warning");

        setIsAttendanceModalOpen(false);
    };

    const toggleAttendance = (id: number) => {
        if (attendedMemberIds.includes(id)) {
            setAttendedMemberIds(prev => prev.filter(mId => mId !== id));
        } else {
            setAttendedMemberIds(prev => [...prev, id]);
        }
    };

    return (
        <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-bold text-slate-900 tracking-tight">Eventos y Asistencia</h1>
                    <p className="text-slate-500 mt-1">Programa eventos recurrentes y registra la asistencia comunitaria.</p>
                </div>
                <button
                    onClick={() => setIsRegModalOpen(true)}
                    className="flex items-center gap-2 bg-blue-600 px-6 py-3 rounded-2xl text-sm font-black text-white hover:bg-blue-700 transition-all shadow-lg shadow-blue-100 uppercase tracking-widest"
                >
                    <Plus size={20} />
                    Nuevo Evento
                </button>
            </div>

            {/* Events Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {loading ? (
                    Array.from({ length: 6 }).map((_, i) => (
                        <div key={i} className="glass-card p-6 border border-slate-100/50 bg-white/50 animate-pulse h-48 rounded-[2rem]" />
                    ))
                ) : (
                    events.map(ev => (
                        <div key={ev.id} className="p-6 rounded-[2rem] border border-slate-100 bg-white hover:border-blue-100 hover:shadow-2xl hover:shadow-blue-50 transition-all group flex flex-col justify-between">
                            <div>
                                <div className="flex justify-between items-start mb-4">
                                    <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-blue-50 to-indigo-50 text-blue-600 flex items-center justify-center">
                                        <Calendar size={20} />
                                    </div>
                                    <span className="px-3 py-1 bg-slate-50 text-slate-500 text-[10px] font-black uppercase tracking-widest rounded-full">
                                        {ev.event_type}
                                    </span>
                                </div>
                                <h3 className="text-lg font-black text-slate-900 mb-2 truncate">{ev.name}</h3>
                                <p className="text-sm font-medium text-slate-500 line-clamp-2">{ev.description || "Evento comunitario de CCF."}</p>
                            </div>

                            <button
                                onClick={() => openAttendance(ev)}
                                className="mt-6 w-full py-3 bg-slate-50 group-hover:bg-blue-600 text-slate-500 group-hover:text-white rounded-xl text-[10px] font-black uppercase tracking-widest transition-all"
                            >
                                Panel de Asistencia
                            </button>
                        </div>
                    ))
                )}
            </div>

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
    );
}
