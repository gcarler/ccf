'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Users, Filter, Plus, Calendar, Clock, Heart, Search, Video, MoreVertical, X as CloseIcon, ShieldCheck, CheckCircle2, XCircle, Loader2, ArrowLeft, MessageSquare, History, Link2 } from 'lucide-react';
import { apiFetch } from '@/lib/http';
import { toast } from 'react-toastify';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import CrmShell from '@/components/crm/CrmShell';
import AdminHero from '@/components/admin/AdminHero';

interface CounselingSession {
    id: number;
    pastor_id: number;
    member_id?: number;
    lead_id?: number;
    scheduled_at: string;
    duration_minutes: number;
    status: string;
    topic?: string;
    summary?: string;
    confidential_notes?: string;
    created_at: string;
}

export default function CounselingPage() {
    const [sessions, setSessions] = useState<CounselingSession[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');
    const [filterStatus, setFilterStatus] = useState('All');
    const [showModal, setShowModal] = useState(false);

    // Form state
    const [newSession, setNewSession] = useState({
        pastor_id: 1, // Mock current user
        scheduled_at: '',
        topic: '',
        status: 'Pendiente',
        duration_minutes: 60
    });

    const router = useRouter();
    const { token } = useAuth();

    const heroWatchers = ['Cuidado Pastoral', 'Optimus Brain'];

    const fetchSessions = useCallback(async () => {
        if (!token) {
            setSessions([]);
            setLoading(false);
            return;
        }
        setLoading(true);
        try {
            const data = await apiFetch<CounselingSession[]>('/crm/counseling/', { token, cache: 'no-store' });
            setSessions(Array.isArray(data) ? data : []);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    }, [token]);

    useEffect(() => {
        fetchSessions();
    }, [fetchSessions]);

    const handleCreateSession = async () => {
        if (!token) return;
        try {
            await apiFetch('/crm/counseling/', {
                method: 'POST',
                token,
                body: newSession,
            });
            toast.success('Sesión agendada correctamente');
            setShowModal(false);
            fetchSessions();
        } catch (err) {
            toast.error('Error al agendar sesión');
        }
    };

    const handleUpdateStatus = async (id: number, status: string) => {
        if (!token) return;
        try {
            await apiFetch(`/crm/counseling/${id}`, {
                method: 'PATCH',
                token,
                body: { status }
            });
            toast.success(`Estado actualizado a ${status}`);
            fetchSessions();
        } catch (err) {
            toast.error('Error al actualizar estado');
        }
    };

    const filteredSessions = sessions.filter(s => {
        const matchesSearch = s.topic?.toLowerCase().includes(searchTerm.toLowerCase());
        const matchesStatus = filterStatus === 'All' || s.status === filterStatus;
        return matchesSearch && matchesStatus;
    });

    return (
        <CrmShell
            breadcrumbs={[{ label: 'CCF', icon: Users }, { label: 'CRM Pastoral', icon: Users }, { label: 'Consejería', icon: Heart }]}
            rightActions={
                <button
                    onClick={() => setShowModal(true)}
                    className="px-6 py-2.5 bg-purple-600 hover:bg-purple-500 text-white rounded-xl text-xs font-black uppercase tracking-widest shadow-xl shadow-purple-900/20 transition-all flex items-center gap-2"
                >
                    <Plus size={16} /> Agendar sesión
                </button>
            }
        >
        <AdminHero
            eyebrow="Consejería"
            title="Centro de consejería"
            description="Coordina sesiones pastorales y seguimiento espiritual por estado con IA que prioriza casos urgentes."
            tags={['Consejería', 'Seguimiento', 'IA']}
            watchers={heroWatchers}
            primaryAction={{ label: 'Agendar sesión', icon: Plus, onClick: () => setShowModal(true) }}
            secondaryAction={{ label: 'Ver políticas', icon: Link2, onClick: () => {} }}
        />
        {/* Header */}
            <div className="flex justify-between items-end shrink-0">
                <div>
                    <p className="text-slate-500 mt-1 uppercase text-[10px] font-black tracking-[0.2em]">Cuidado pastoral y acompañamiento espiritual</p>
                </div>
            </div>

            <div className="space-y-8">
            {/* Stats */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {[
                    { label: 'Sesiones Pendientes', val: sessions.filter(s => s.status === 'Pendiente').length, color: 'text-amber-500', bg: 'bg-amber-500/10' },
                    { label: 'Completadas', val: sessions.filter(s => s.status === 'Realizada').length, color: 'text-emerald-500', bg: 'bg-emerald-500/10' },
                    { label: 'Total Histórico', val: sessions.length, color: 'text-blue-500', bg: 'bg-blue-500/10' },
                ].map((stat, i) => (
                    <div key={i} className="bg-slate-900/40 border border-white/5 p-6 rounded-3xl flex items-center justify-between">
                        <div>
                            <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest leading-none mb-2">{stat.label}</p>
                            <p className="text-3xl font-black text-white">{stat.val}</p>
                        </div>
                        <div className={`p-4 rounded-2xl ${stat.bg} ${stat.color}`}>
                            <History size={24} />
                        </div>
                    </div>
                ))}
            </div>

            {/* Filters */}
            <div className="flex flex-col md:flex-row gap-4 items-center justify-between bg-slate-900/20 p-4 rounded-2xl border border-white/5">
                <div className="relative w-full md:w-96">
                    <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
                    <input
                        type="text"
                        placeholder="Buscar por tema..."
                        className="w-full bg-slate-900 border border-white/10 rounded-xl py-3 pl-12 pr-4 text-sm text-white focus:outline-none focus:border-purple-500 transition-all"
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                    />
                </div>
                <div className="flex gap-2 w-full md:w-auto overflow-x-auto pb-1 md:pb-0">
                    {['All', 'Pendiente', 'Realizada', 'Cancelada'].map(status => (
                        <button
                            key={status}
                            onClick={() => setFilterStatus(status)}
                            className={`px-4 py-2 rounded-lg text-[10px] font-black uppercase tracking-widest transition-all ${filterStatus === status ? 'bg-purple-600 text-white shadow-lg' : 'bg-white/5 text-slate-400 hover:text-white hover:bg-white/10'}`}
                        >
                            {status === 'All' ? 'Todos' : status}
                        </button>
                    ))}
                </div>
            </div>

            {/* Sessions List */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {loading ? (
                    Array.from({ length: 6 }).map((_, i) => (
                        <div key={i} className="h-64 bg-slate-900/50 animate-pulse rounded-[40px] border border-white/5" />
                    ))
                ) : filteredSessions.length > 0 ? (
                    filteredSessions.map(session => (
                        <div key={session.id} className="bg-slate-900/40 border border-white/5 rounded-[40px] p-8 space-y-6 hover:border-purple-500/30 transition-all group relative overflow-hidden">
                            <div className="absolute top-0 right-0 p-6 opacity-5 group-hover:opacity-10 transition-opacity">
                                <MessageSquare size={80} />
                            </div>

                            <div className="flex justify-between items-start relative z-10">
                                <span className={`px-4 py-1.5 rounded-full text-[9px] font-black uppercase tracking-widest ${session.status === 'Realizada' ? 'bg-emerald-500/10 text-emerald-500' :
                                        session.status === 'Cancelada' ? 'bg-rose-500/10 text-rose-500' :
                                            'bg-amber-500/10 text-amber-500'
                                    }`}>
                                    {session.status}
                                </span>
                                <p className="text-[10px] font-bold text-slate-500 flex items-center gap-2">
                                    <Clock size={12} /> {session.duration_minutes} min
                                </p>
                            </div>

                            <div className="space-y-2 relative z-10">
                                <h3 className="text-xl font-bold text-white leading-tight">{session.topic || 'Sin tema definido'}</h3>
                                <p className="text-xs text-slate-400 flex items-center gap-2">
                                    <Calendar size={14} className="text-purple-500" />
                                    {new Date(session.scheduled_at).toLocaleString()}
                                </p>
                            </div>

                            <div className="pt-4 border-t border-white/5 flex items-center justify-between relative z-10">
                                <div className="flex items-center gap-3">
                                    <div className="w-10 h-10 rounded-2xl bg-purple-600/20 text-purple-500 flex items-center justify-center font-bold">
                                        P
                                    </div>
                                    <div>
                                        <p className="text-[9px] font-black text-slate-500 uppercase tracking-widest leading-none mb-1">Pastor Asignado</p>
                                        <p className="text-xs font-bold text-white">Pr. Demo</p>
                                    </div>
                                </div>
                            </div>

                            {session.status === 'Pendiente' && (
                                <div className="flex gap-2 pt-2 relative z-10">
                                    <button
                                        onClick={() => handleUpdateStatus(session.id, 'Realizada')}
                                        className="flex-1 py-3 bg-white/5 hover:bg-emerald-500 text-slate-300 hover:text-white rounded-2xl text-[10px] font-black uppercase tracking-widest transition-all flex items-center justify-center gap-2"
                                    >
                                        <CheckCircle2 size={14} /> Completar
                                    </button>
                                    <button
                                        onClick={() => handleUpdateStatus(session.id, 'Cancelada')}
                                        className="flex-1 py-3 bg-white/5 hover:bg-rose-500 text-slate-300 hover:text-white rounded-2xl text-[10px] font-black uppercase tracking-widest transition-all flex items-center justify-center gap-2"
                                    >
                                        <XCircle size={14} /> Cancelar
                                    </button>
                                </div>
                            )}
                        </div>
                    ))
                ) : (
                    <div className="col-span-full py-20 text-center space-y-4 bg-slate-900/20 rounded-[40px] border border-dashed border-white/10">
                        <MessageSquare size={48} className="mx-auto text-slate-800" />
                        <p className="text-slate-500 font-bold uppercase tracking-[0.2em] text-[10px]">No hay sesiones registradas</p>
                    </div>
                )}
            </div>

            {/* Create Modal */}
            {showModal && (
                <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-xl z-[100] flex items-center justify-center p-4">
                    <div className="bg-slate-900 w-full max-w-lg rounded-[40px] shadow-2xl border border-white/10 p-10 space-y-8 animate-in zoom-in-95 duration-200">
                        <div className="flex justify-between items-start">
                            <div>
                                <h2 className="text-2xl font-black text-white tracking-tight">Agendar Consejería</h2>
                                <p className="text-[10px] font-black text-purple-500 uppercase tracking-widest mt-1">Nuevo acompañamiento espiritual</p>
                            </div>
                            <button onClick={() => setShowModal(false)} className="text-slate-500 hover:text-white transition-colors">
                                <XCircle size={24} />
                            </button>
                        </div>

                        <div className="space-y-6">
                            <div className="space-y-2">
                                <label className="text-[9px] font-black uppercase tracking-[0.2em] text-slate-500 ml-4">Tema de la Sesión</label>
                                <input
                                    type="text"
                                    className="w-full bg-slate-950 border border-white/5 rounded-2xl px-6 py-4 text-sm text-white focus:outline-none focus:border-purple-500 transition-all font-medium"
                                    placeholder="Ej: Orientación Familiar, Fortaleza..."
                                    value={newSession.topic}
                                    onChange={(e) => setNewSession({ ...newSession, topic: e.target.value })}
                                />
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <label className="text-[9px] font-black uppercase tracking-[0.2em] text-slate-500 ml-4">Fecha y Hora</label>
                                    <input
                                        type="datetime-local"
                                        className="w-full bg-slate-950 border border-white/5 rounded-2xl px-6 py-4 text-sm text-white focus:outline-none focus:border-purple-500 transition-all font-medium color-scheme-dark"
                                        style={{ colorScheme: 'dark' }}
                                        value={newSession.scheduled_at}
                                        onChange={(e) => setNewSession({ ...newSession, scheduled_at: e.target.value })}
                                    />
                                </div>
                                <div className="space-y-2">
                                    <label className="text-[9px] font-black uppercase tracking-[0.2em] text-slate-500 ml-4">Duración (min)</label>
                                    <select
                                        className="w-full bg-slate-950 border border-white/5 rounded-2xl px-6 py-4 text-sm text-white focus:outline-none focus:border-purple-500 transition-all font-medium appearance-none"
                                        value={newSession.duration_minutes}
                                        onChange={(e) => setNewSession({ ...newSession, duration_minutes: parseInt(e.target.value) })}
                                    >
                                        <option value={30}>30 min</option>
                                        <option value={60}>1 hora</option>
                                        <option value={90}>1.5 horas</option>
                                        <option value={120}>2 horas</option>
                                    </select>
                                </div>
                            </div>
                        </div>

                        <div className="flex gap-4 pt-4">
                            <button
                                onClick={() => setShowModal(false)}
                                className="flex-1 py-4 bg-white/5 hover:bg-white/10 text-slate-400 font-black uppercase tracking-widest text-[10px] rounded-2xl transition-all"
                            >
                                Descartar
                            </button>
                            <button
                                onClick={handleCreateSession}
                                className="flex-1 py-4 bg-purple-600 hover:bg-purple-500 text-white font-black uppercase tracking-widest text-[10px] rounded-2xl shadow-2xl shadow-purple-900/40 transition-all"
                            >
                                Agendar Ahora
                            </button>
                        </div>
                    </div>
                </div>
            )}
            </div>
        </CrmShell>
    );
}
