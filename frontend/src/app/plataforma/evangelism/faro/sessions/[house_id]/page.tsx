"use client";

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { apiFetch } from '@/lib/http';
import { toast } from 'sonner';
import {
    ArrowLeft, Calendar, Users, CheckCircle2, XCircle, UserPlus,
    Save, DollarSign, FileText, Clock, Plus, Search,
    Home, User, Shield, AlertCircle,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import EvangelismShell from '@/components/evangelism/EvangelismShell';

interface GloryHouse {
    id: number;
    name: string;
    zone: string | null;
    address: string | null;
    leader_name: string | null;
    leader_id: number | null;
    assistant_id: number | null;
    host_id: number | null;
    members_count: number;
    status: string;
    evangelism_strategy_id: number | null;
    base_attendees?: { member_id: number; role: string; member?: { first_name: string; last_name: string; phone?: string } }[];
}

interface SessionPerson {
    member_id: number;
    name: string;
    role: string;
    phone?: string;
    status: 'present' | 'absent' | 'first_time';
}

interface NewGuest {
    firstName: string;
    lastName: string;
    phone: string;
}

export default function SessionReportPage() {
    const params = useParams();
    const router = useRouter();
    const houseId = (params?.house_id as string) || '';
    const { token } = useAuth();

    const [house, setHouse] = useState<GloryHouse | null>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [sessionDate, setSessionDate] = useState(new Date().toISOString().split('T')[0]);
    const [topic, setTopic] = useState('');
    const [offering, setOffering] = useState('');
    const [reportNotes, setReportNotes] = useState('');
    const [people, setPeople] = useState<SessionPerson[]>([]);
    const [newGuests, setNewGuests] = useState<NewGuest[]>([]);
    const [searchQuery, setSearchQuery] = useState('');

    function useAuth() {
        const [authToken, setAuthToken] = useState<string | null>(null);
        useEffect(() => {
            setAuthToken(localStorage.getItem('auth_token'));
        }, []);
        return { token: authToken };
    }

    const fetchHouse = useCallback(async () => {
        setLoading(true);
        try {
            const localToken = localStorage.getItem('auth_token') || '';
            const data = await apiFetch<GloryHouse>(`/evangelism/glory-houses/${houseId}`, { token: localToken });
            setHouse(data);

            const ppl: SessionPerson[] = [];
            const baseMembers = data.base_attendees || [];
            const roleIds = new Set<number>();

            if (data.leader_id) {
                const m = baseMembers.find(x => x.member_id === data.leader_id);
                ppl.push({ member_id: data.leader_id, name: m?.member ? `${m.member.first_name} ${m.member.last_name}` : (data.leader_name || 'Líder'), role: 'Líder', phone: m?.member?.phone, status: 'present' });
                roleIds.add(data.leader_id);
            }
            if (data.assistant_id) {
                const m = baseMembers.find(x => x.member_id === data.assistant_id);
                ppl.push({ member_id: data.assistant_id, name: m?.member ? `${m.member.first_name} ${m.member.last_name}` : 'Asistente del Líder', role: 'Asistente del Líder', phone: m?.member?.phone, status: 'present' });
                roleIds.add(data.assistant_id);
            }
            if (data.host_id) {
                const m = baseMembers.find(x => x.member_id === data.host_id);
                ppl.push({ member_id: data.host_id, name: m?.member ? `${m.member.first_name} ${m.member.last_name}` : 'Anfitrión', role: 'Anfitrión', phone: m?.member?.phone, status: 'present' });
                roleIds.add(data.host_id);
            }
            for (const m of baseMembers) {
                if (!roleIds.has(m.member_id)) {
                    ppl.push({ member_id: m.member_id, name: m.member ? `${m.member.first_name} ${m.member.last_name}` : `Miembro #${m.member_id}`, role: 'Asistente', phone: m.member?.phone, status: 'absent' });
                }
            }
            setPeople(ppl);
        } catch {
            toast.error('Error al cargar el grupo');
        } finally {
            setLoading(false);
        }
    }, [houseId]);

    useEffect(() => { fetchHouse(); }, [fetchHouse]);

    const updateStatus = (memberId: number, status: 'present' | 'absent' | 'first_time') => {
        setPeople(prev => prev.map(p => p.member_id === memberId ? { ...p, status } : p));
    };

    const addGuest = () => setNewGuests(prev => [...prev, { firstName: '', lastName: '', phone: '' }]);
    const updateGuest = (i: number, f: keyof NewGuest, v: string) => setNewGuests(prev => prev.map((g, j) => j === i ? { ...g, [f]: v } : g));
    const removeGuest = (i: number) => setNewGuests(prev => prev.filter((_, j) => j !== i));

    const stats = useMemo(() => ({
        present: people.filter(p => p.status === 'present').length,
        absent: people.filter(p => p.status === 'absent').length,
        firstTime: people.filter(p => p.status === 'first_time').length + newGuests.length,
        total: people.length + newGuests.length,
    }), [people, newGuests]);

    const filtered = useMemo(() => {
        if (!searchQuery) return people;
        const q = searchQuery.toLowerCase();
        return people.filter(p => p.name.toLowerCase().includes(q) || p.role.toLowerCase().includes(q));
    }, [people, searchQuery]);

    const handleSubmit = async () => {
        if (!house) return;
        setSaving(true);
        const localToken = localStorage.getItem('auth_token') || '';
        try {
            const sessionData = await apiFetch<any>('/evangelism/sessions', {
                method: 'POST', token: localToken,
                body: {
                    glory_house_id: parseInt(houseId),
                    session_date: new Date(sessionDate).toISOString(),
                    topic: topic || null,
                    offering_amount: offering ? parseFloat(offering) : null,
                    report_notes: reportNotes || null,
                    status: 'Realizada',
                },
            });

            const sessionId = sessionData.id;
            const attPayload = people.map(p => ({
                session_id: sessionId, member_id: p.member_id, status: p.status, notes: null,
            }));

            await apiFetch(`/evangelism/sessions/${sessionId}/attendance`, {
                method: 'POST', token: localToken, body: attPayload,
            });

            toast.success(`Reporte: ${stats.present} presentes, ${stats.absent} ausentes, ${stats.firstTime} nuevos`);
            router.push(`/evangelism/faro/groups`);
        } catch (error: any) {
            toast.error(error?.message || 'Error al guardar');
        } finally {
            setSaving(false);
        }
    };

    const ROLE_STYLES: Record<string, { bg: string; text: string; border: string; icon: typeof User }> = {
        'Líder': { bg: 'bg-blue-50 dark:bg-blue-900/20', text: 'text-blue-700 dark:text-blue-400', border: 'border-blue-200 dark:border-blue-800', icon: Shield },
        'Asistente del Líder': { bg: 'bg-indigo-50 dark:bg-indigo-900/20', text: 'text-indigo-700 dark:text-indigo-400', border: 'border-indigo-200 dark:border-indigo-800', icon: User },
        'Anfitrión': { bg: 'bg-amber-50 dark:bg-amber-900/20', text: 'text-amber-700 dark:text-amber-400', border: 'border-amber-200 dark:border-amber-800', icon: Home },
        'Asistente': { bg: 'bg-slate-50 dark:bg-white/5', text: 'text-slate-700 dark:text-slate-300', border: 'border-slate-200 dark:border-white/10', icon: Users },
    };

    if (loading) return (
        <EvangelismShell breadcrumbs={[{ label: 'Evangelismo', href: '/evangelism' }, { label: 'Grupos Faro', href: '/evangelism/faro/groups' }, { label: 'Reporte' }]}>
            <div className="space-y-3 p-3">{[1, 2, 3].map(i => <div key={i} className="h-16 bg-slate-100 dark:bg-white/5 rounded-lg animate-pulse" />)}</div>
        </EvangelismShell>
    );

    if (!house) return (
        <EvangelismShell breadcrumbs={[{ label: 'Evangelismo', href: '/evangelism' }, { label: 'No encontrado' }]}>
            <div className="flex flex-col items-center justify-center py-16 text-center">
                <AlertCircle size={48} className="text-slate-300 dark:text-slate-600 mb-4" />
                <h2 className="text-lg font-bold text-slate-700 dark:text-slate-300">Grupo no encontrado</h2>
                <button onClick={() => router.push('/evangelism/faro/groups')} className="mt-4 px-4 h-9 rounded-lg bg-blue-600 text-white text-xs font-semibold hover:bg-blue-700 transition-colors">Volver</button>
            </div>
        </EvangelismShell>
    );

    return (
        <EvangelismShell breadcrumbs={[{ label: 'Evangelismo', href: '/evangelism' }, { label: 'Grupos Faro', href: '/evangelism/faro/groups' }, { label: house.name }, { label: 'Reporte' }]}>
            <div className="p-4 lg:p-3 space-y-3 max-w-4xl mx-auto animate-fade-in">
                {/* Header */}
                <div className="flex items-start justify-between">
                    <div className="flex items-start gap-3">
                        <button onClick={() => router.push('/evangelism/faro/groups')} className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-white/5 text-slate-400 hover:text-white transition-all mt-1"><ArrowLeft size={16} /></button>
                        <div>
                            <h1 className="text-xl font-bold text-slate-900 dark:text-white">Reportar Sesión</h1>
                            <p className="text-sm text-slate-400 font-medium">{house.name} · {house.zone || 'Sin zona'}</p>
                        </div>
                    </div>
                </div>

                {/* Date */}
                <div className="bg-white dark:bg-[#1e1f21] border border-slate-200 dark:border-white/10 rounded-lg p-4">
                    <label className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5 mb-2"><Calendar size={12} /> Fecha</label>
                    <input type="date" value={sessionDate} onChange={e => setSessionDate(e.target.value)} className="w-full md:w-auto px-3 py-2 rounded-lg border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/5 text-sm text-slate-900 dark:text-white focus:border-blue-500 focus:outline-none" />
                </div>

                {/* Stats */}
                <div className="grid grid-cols-4 gap-2">
                    <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-3 text-center"><p className="text-2xl font-bold text-green-600 dark:text-green-400">{stats.present}</p><p className="text-[10px] font-semibold text-green-700 dark:text-green-500">Presentes</p></div>
                    <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3 text-center"><p className="text-2xl font-bold text-red-500 dark:text-red-400">{stats.absent}</p><p className="text-[10px] font-semibold text-red-600 dark:text-red-500">Ausentes</p></div>
                    <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-3 text-center"><p className="text-2xl font-bold text-blue-600 dark:text-blue-400">{stats.firstTime}</p><p className="text-[10px] font-semibold text-blue-700 dark:text-blue-500">Nuevos</p></div>
                    <div className="bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg p-3 text-center"><p className="text-2xl font-bold text-slate-700 dark:text-slate-300">{stats.total}</p><p className="text-[10px] font-semibold text-slate-500">Total</p></div>
                </div>

                {/* Attendance */}
                <div className="bg-white dark:bg-[#1e1f21] border border-slate-200 dark:border-white/10 rounded-lg overflow-hidden">
                    <div className="px-4 py-3 border-b border-slate-100 dark:border-white/5 flex items-center justify-between">
                        <h2 className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5"><Users size={12} /> Asistencia ({people.length})</h2>
                        <div className="relative">
                            <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
                            <input type="text" value={searchQuery} onChange={e => setSearchQuery(e.target.value)} placeholder="Buscar..." className="pl-8 pr-3 py-1.5 rounded-lg border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/5 text-xs text-slate-700 dark:text-slate-200 focus:border-blue-500 focus:outline-none w-40" />
                        </div>
                    </div>
                    <div className="divide-y divide-slate-100 dark:divide-white/5 max-h-[400px] overflow-y-auto scrollbar-thin">
                        {filtered.map(person => {
                            const rs = ROLE_STYLES[person.role] || ROLE_STYLES['Asistente'];
                            const Icon = rs.icon;
                            return (
                                <div key={person.member_id} className={`px-4 py-3 flex items-center gap-3 ${rs.bg}`}>
                                    <div className={`size-8 rounded-lg flex items-center justify-center shrink-0 border ${rs.bg} ${rs.border}`}><Icon size={14} className={rs.text} /></div>
                                    <div className="flex-1 min-w-0">
                                        <p className="text-sm font-semibold text-slate-800 dark:text-white truncate">{person.name}</p>
                                        <div className="flex items-center gap-2 text-[10px] font-medium text-slate-400">
                                            <span className={`px-1.5 py-0.5 rounded font-bold ${rs.text} ${rs.bg}`}>{person.role}</span>
                                            {person.phone && <span>📱 {person.phone}</span>}
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-1 shrink-0">
                                        <button onClick={() => updateStatus(person.member_id, 'present')} className={`p-1.5 rounded-lg transition-all ${person.status === 'present' ? 'bg-green-100 dark:bg-green-900/30 text-green-600' : 'text-slate-300 dark:text-slate-600 hover:bg-slate-100 dark:hover:bg-white/5'}`} title="Presente"><CheckCircle2 size={16} /></button>
                                        <button onClick={() => updateStatus(person.member_id, 'absent')} className={`p-1.5 rounded-lg transition-all ${person.status === 'absent' ? 'bg-red-100 dark:bg-red-900/30 text-red-500' : 'text-slate-300 dark:text-slate-600 hover:bg-slate-100 dark:hover:bg-white/5'}`} title="Ausente"><XCircle size={16} /></button>
                                        <button onClick={() => updateStatus(person.member_id, 'first_time')} className={`p-1.5 rounded-lg transition-all ${person.status === 'first_time' ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-600' : 'text-slate-300 dark:text-slate-600 hover:bg-slate-100 dark:hover:bg-white/5'}`} title="Primera vez"><UserPlus size={16} /></button>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>

                {/* New Guests */}
                <div className="bg-white dark:bg-[#1e1f21] border border-slate-200 dark:border-white/10 rounded-lg overflow-hidden">
                    <div className="px-4 py-3 border-b border-slate-100 dark:border-white/5 flex items-center justify-between">
                        <h2 className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5"><UserPlus size={12} /> Invitados nuevos ({newGuests.length})</h2>
                        <button onClick={addGuest} className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-blue-600 text-white text-[10px] font-bold hover:bg-blue-700"><Plus size={11} /> Agregar</button>
                    </div>
                    <AnimatePresence>
                        {newGuests.map((g, i) => (
                            <motion.div key={i} initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }} className="px-4 py-3 border-b border-slate-100 dark:border-white/5 last:border-b-0 bg-blue-50/50 dark:bg-blue-900/10">
                                <div className="flex items-center gap-2">
                                    <input type="text" value={g.firstName} onChange={e => updateGuest(i, 'firstName', e.target.value)} placeholder="Nombre" className="flex-1 px-3 py-2 rounded-lg border border-blue-200 dark:border-blue-800 bg-white dark:bg-[#1e1f21] text-sm text-slate-900 dark:text-white focus:border-blue-500 focus:outline-none" />
                                    <input type="text" value={g.lastName} onChange={e => updateGuest(i, 'lastName', e.target.value)} placeholder="Apellido" className="flex-1 px-3 py-2 rounded-lg border border-blue-200 dark:border-blue-800 bg-white dark:bg-[#1e1f21] text-sm text-slate-900 dark:text-white focus:border-blue-500 focus:outline-none" />
                                    <input type="text" value={g.phone} onChange={e => updateGuest(i, 'phone', e.target.value)} placeholder="Teléfono" className="flex-1 px-3 py-2 rounded-lg border border-blue-200 dark:border-blue-800 bg-white dark:bg-[#1e1f21] text-sm text-slate-900 dark:text-white focus:border-blue-500 focus:outline-none" />
                                    <button onClick={() => removeGuest(i)} className="p-2 rounded-lg text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-500/10"><XCircle size={16} /></button>
                                </div>
                            </motion.div>
                        ))}
                    </AnimatePresence>
                    {newGuests.length === 0 && <div className="px-4 py-6 text-center text-xs text-slate-400">Sin invitados nuevos — agrega personas que vinieron por primera vez</div>}
                </div>

                {/* Session Details */}
                <div className="bg-white dark:bg-[#1e1f21] border border-slate-200 dark:border-white/10 rounded-lg p-4 space-y-4">
                    <h2 className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5"><FileText size={12} /> Detalles</h2>
                    <div>
                        <label className="block text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-1">Tema</label>
                        <input type="text" value={topic} onChange={e => setTopic(e.target.value)} placeholder="Tema de la reunión..." className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/5 text-sm text-slate-900 dark:text-white focus:border-blue-500 focus:outline-none" />
                    </div>
                    <div>
                        <label className="block text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-1">Ofrenda</label>
                        <div className="relative w-48">
                            <DollarSign size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                            <input type="number" step="0.01" value={offering} onChange={e => setOffering(e.target.value)} placeholder="0.00" className="w-full pl-9 pr-3 py-2 rounded-lg border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/5 text-sm text-slate-900 dark:text-white focus:border-blue-500 focus:outline-none" />
                        </div>
                    </div>
                    <div>
                        <label className="block text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-1">Notas</label>
                        <textarea value={reportNotes} onChange={e => setReportNotes(e.target.value)} rows={3} placeholder="Observaciones..." className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/5 text-sm text-slate-900 dark:text-white focus:border-blue-500 focus:outline-none resize-none" />
                    </div>
                </div>

                {/* Submit */}
                <div className="flex items-center justify-end gap-3 pb-4">
                    <button onClick={() => router.push('/evangelism/faro/groups')} className="px-4 h-9 rounded-lg border border-slate-200 dark:border-white/10 text-xs font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-white/5">Cancelar</button>
                    <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }} onClick={handleSubmit} disabled={saving} className="inline-flex items-center gap-2 px-6 h-10 rounded-lg bg-blue-600 text-white text-sm font-bold hover:bg-blue-700 disabled:opacity-60 shadow-sm">
                        {saving ? <><Clock size={16} className="animate-spin" /> Guardando...</> : <><Save size={16} /> Guardar Reporte</>}
                    </motion.button>
                </div>
            </div>
        </EvangelismShell>
    );
}
