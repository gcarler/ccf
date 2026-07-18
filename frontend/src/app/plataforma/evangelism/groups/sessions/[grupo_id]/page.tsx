"use client";

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { apiFetch, ApiError } from '@/lib/http';
import { toast } from 'sonner';
import { useAuth } from '@/context/AuthContext';
import {
 ArrowLeft, Calendar, Users, CheckCircle2, XCircle, UserPlus,
 Save, DollarSign, FileText, Clock, Plus, Search,
 Home, User, Shield, AlertCircle,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import EvangelismShell from '@/components/evangelism/EvangelismShell';

interface Grupo {
 id: string;
 name: string;
 zone: string | null;
 address: string | null;
 leader_name: string | null;
 leader_id: string | null;
 assistant_id: string | null;
 host_id: string | null;
 personas_count: number;
 status: string;
 evangelism_strategy_id: string | null;
 base_attendees?: {
  persona_id: string;
  name?: string;
  role: string;
  role_label?: string;
  rol_personalizado_id?: string | null;
  phone?: string;
  persona?: { nombre_completo: string; telefono?: string };
 }[];
}

interface SessionPerson {
 persona_id: string;
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

interface AttendanceSaveResult {
 evento_integracion?: {
 estado?: string;
 grupo_id?: string;
 sesion_id?: string;
 crm_consolidacion?: {
 caso_id?: string;
 } | null;
 } | null;
 metadata?: {
 trazabilidad?: string;
 } | null;
}

interface SessionCreateResult { id: string; }

function getErrorMessage(error: unknown, fallback: string): string {
 if (error instanceof ApiError) {
  const detail = error.detail;
  if (typeof detail === 'string') return detail;
  if (detail && typeof detail === 'object' && 'detail' in detail) {
   return String((detail as { detail?: unknown }).detail || fallback);
  }
 }
 return error instanceof Error ? error.message : fallback;
}

export default function SessionReportPage() {
 const params = useParams();
 const router = useRouter();
 const grupoId = (params?.grupo_id as string) || '';
 const { token, loading: authLoading } = useAuth();

 const [house, setHouse] = useState<Grupo | null>(null);
 const [loading, setLoading] = useState(true);
 const [loadError, setLoadError] = useState(false);
 const [saving, setSaving] = useState(false);
 const [sessionDate, setSessionDate] = useState(new Date().toISOString().split('T')[0]);
 const [topic, setTopic] = useState('');
 const [offering, setOffering] = useState('');
 const [reportNotes, setReportNotes] = useState('');
 const [people, setPeople] = useState<SessionPerson[]>([]);
 const [newGuests, setNewGuests] = useState<NewGuest[]>([]);
 const [searchQuery, setSearchQuery] = useState('');
 const fetchHouse = useCallback(async () => {
    if (authLoading) return;
    if (!token || !grupoId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setLoadError(false);
    try {
      const data = await apiFetch<Grupo>(`/evangelism/grupos/${grupoId}`, { token, silent: true });
      setHouse(data);

      const basePersonas = data.base_attendees || [];
      const peopleById = new Map<string, SessionPerson>();
      const addPerson = (
        personaId: string | null | undefined,
        fallbackName: string,
        fallbackRole: string,
        status: SessionPerson['status'] = 'absent',
      ) => {
        if (!personaId || peopleById.has(personaId)) return;
        const m = basePersonas.find(x => x.persona_id === personaId);
        peopleById.set(personaId, {
          persona_id: personaId,
          name: m?.name || m?.persona?.nombre_completo || fallbackName,
          role: m?.role_label || m?.role || fallbackRole,
          phone: m?.phone || m?.persona?.telefono,
          status,
        });
      };

      for (const m of basePersonas) {
        addPerson(
          m.persona_id,
          m.name || m.persona?.nombre_completo || `Persona #${m.persona_id}`,
          m.role_label || m.role || 'Participante',
        );
      }

      addPerson(data.leader_id, data.leader_name || 'Persona asignada', 'Asignado', 'present');
      addPerson(data.assistant_id, 'Persona asignada', 'Asignado', 'present');
      addPerson(data.host_id, 'Persona asignada', 'Asignado', 'present');
      setPeople(Array.from(peopleById.values()));
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        setHouse(null);
        setPeople([]);
        return;
      }
      setHouse(null);
      setPeople([]);
      setLoadError(true);
    } finally {
      setLoading(false);
    }
  }, [authLoading, grupoId, token]);

 useEffect(() => { fetchHouse(); }, [fetchHouse]);

 const updateStatus = (personaId: string, status: 'present' | 'absent' | 'first_time') => {
 setPeople(prev => prev.map(p => p.persona_id === personaId ? { ...p, status } : p));
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
 if (!house || !token) return;
 setSaving(true);
 try {
 const sessionData = await apiFetch<SessionCreateResult>('/evangelism/sessions', {
  method: 'POST', token, silent: true,
  body: {
  grupo_id: grupoId,
  session_date: `${sessionDate}T12:00:00`,
  topic: topic || null,
  offering_amount: offering ? parseFloat(offering) : null,
  report_notes: reportNotes || null,
 status: 'Realizada',
 },
 });

 const sessionId = sessionData.id;
 await apiFetch(`/evangelism/sessions/${sessionId}/habilitacion`, {
 method: 'PATCH',
 token,
 silent: true,
 body: { accion: 'HABILITAR' },
 });
 const attPayload = people.map(p => ({
 session_id: sessionId, persona_id: p.persona_id, status: p.status, notes: null,
 }));

const attendanceResult = await apiFetch<AttendanceSaveResult>(`/evangelism/sessions/${sessionId}/attendance`, {
method: 'POST', token: token, silent: true, body: attPayload,
});

 if (attendanceResult?.evento_integracion) {
 const caseId = attendanceResult.evento_integracion.crm_consolidacion?.caso_id;
 toast.info(caseId ? `Integración CRM activada para caso ${caseId}` : 'Integración CRM activada');
 }

 // Register new guests as Personas
 for (const guest of newGuests) {
 if (guest.firstName.trim() || guest.lastName.trim()) {
 await apiFetch('/evangelism/groups/visitors', {
 method: 'POST', token: token, silent: true,
 body: {
 first_name: guest.firstName.trim(),
 last_name: guest.lastName.trim(),
 phone: guest.phone.trim() || null,
 grupo_id: grupoId,
 session_id: sessionId,
 },
 });
 }
 }

 toast.success(`Reporte: ${stats.present} presentes, ${stats.absent} ausentes, ${stats.firstTime} nuevos`);
  router.push(`/plataforma/evangelism/groups`);
 } catch (error: unknown) {
 toast.error(getErrorMessage(error, 'Error al guardar'));
 } finally {
 setSaving(false);
 }
 };

 const ROLE_STYLES: Record<string, { bg: string; text: string; border: string; icon: typeof User }> = {
 'Líder': { bg: 'bg-info-soft', text: 'text-info-text dark:text-info', border: 'border-info-muted', icon: Shield },
 'Asistente del Líder': { bg: 'bg-info-soft', text: 'text-info-text dark:text-info', border: 'border-info-muted', icon: User },
 'Anfitrión': { bg: 'bg-warning-soft', text: 'text-warning-text dark:text-warning', border: 'border-warning-muted', icon: Home },
 'Participante': { bg: 'bg-[hsl(var(--bg-muted))]', text: 'text-[hsl(var(--text-primary))]', border: 'border-[hsl(var(--border-primary))]', icon: Users },
 'Asignado': { bg: 'bg-[hsl(var(--bg-muted))]', text: 'text-[hsl(var(--text-primary))]', border: 'border-[hsl(var(--border-primary))]', icon: Users },
 };

 if (loading) return (
 <EvangelismShell breadcrumbs={[{ label: 'Evangelismo', href: '/plataforma/evangelism' }, { label: 'Grupos', href: '/plataforma/evangelism/groups' }, { label: 'Reporte' }]}>
 <div className="space-y-3 p-3">{[1, 2, 3].map(i => <div key={i} className="h-16 bg-[hsl(var(--bg-muted))] rounded-lg animate-pulse" />)}</div>
 </EvangelismShell>
 );

 if (loadError) return (
 <EvangelismShell breadcrumbs={[{ label: 'Evangelismo', href: '/plataforma/evangelism' }, { label: 'Grupos', href: '/plataforma/evangelism/groups' }, { label: 'Reporte' }]}>
 <div className="flex flex-col items-center justify-center py-16 text-center">
 <AlertCircle size={48} className="text-[hsl(var(--text-secondary))] mb-4" />
 <h2 className="text-lg font-bold text-[hsl(var(--text-primary))]">No se pudo cargar el grupo</h2>
 <p className="mt-2 text-sm text-[hsl(var(--text-secondary))] max-w-md">La plataforma recibió una respuesta inválida al consultar este grupo. Puedes volver a intentarlo desde la lista de grupos.</p>
 <button onClick={() => router.push('/plataforma/evangelism/groups')} className="mt-4 px-4 h-9 rounded-lg bg-[hsl(var(--primary))] text-white text-xs font-semibold hover:bg-[hsl(var(--primary))] transition-colors">Volver</button>
 </div>
 </EvangelismShell>
 );

 if (!house) return (
 <EvangelismShell breadcrumbs={[{ label: 'Evangelismo', href: '/plataforma/evangelism' }, { label: 'No encontrado' }]}>
 <div className="flex flex-col items-center justify-center py-16 text-center">
 <AlertCircle size={48} className="text-[hsl(var(--text-secondary))] mb-4" />
 <h2 className="text-lg font-bold text-[hsl(var(--text-primary))]">Grupo no encontrado</h2>
 <button onClick={() => router.push('/plataforma/evangelism/groups')} className="mt-4 px-4 h-9 rounded-lg bg-[hsl(var(--primary))] text-white text-xs font-semibold hover:bg-[hsl(var(--primary))] transition-colors">Volver</button>
 </div>
 </EvangelismShell>
 );

 return (
 <EvangelismShell breadcrumbs={[{ label: 'Evangelismo', href: '/plataforma/evangelism' }, { label: 'Grupos', href: '/plataforma/evangelism/groups' }, { label: house.name }, { label: 'Reporte' }]}>
 <div className="p-4 lg:p-3 space-y-3 max-w-4xl mx-auto animate-fade-in">
 {/* Header */}
 <div className="flex items-start justify-between">
 <div className="flex items-start gap-3">
 <button onClick={() => router.push('/plataforma/evangelism/groups')} className="p-1.5 rounded-lg hover:bg-[hsl(var(--bg-muted))] text-[hsl(var(--text-secondary))] hover:text-white transition-all mt-1"><ArrowLeft size={16} /></button>
 <div>
 <h1 className="text-xl font-bold text-[hsl(var(--text-primary))]">Reportar Sesión</h1>
 <p className="text-sm text-[hsl(var(--text-secondary))] font-medium">{house.name} · {house.zone || 'Sin zona'}</p>
 </div>
 </div>
 </div>

 {/* Date */}
 <div className="bg-[hsl(var(--bg-primary))] dark:bg-surface-card border border-[hsl(var(--border-primary))] rounded-lg p-4">
 <label className="text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] flex items-center gap-1.5 mb-2"><Calendar size={12} /> Fecha</label>
 <input type="date" value={sessionDate} onChange={e => setSessionDate(e.target.value)} className="w-full md:w-auto px-3 py-2 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-muted))] text-sm text-[hsl(var(--text-primary))] focus:border-[hsl(var(--primary))] focus:outline-none" />
 </div>

 {/* Stats */}
 <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
 <div className="bg-success-soft border border-success-muted rounded-lg p-3 text-center"><p className="text-lg font-bold text-[hsl(var(--secondary))] dark:text-[hsl(var(--secondary))]">{stats.present}</p><p className="text-[10px] font-semibold text-[hsl(var(--secondary))] dark:text-[hsl(var(--secondary))]">Presentes</p></div>
 <div className="bg-danger-soft border border-danger-muted rounded-lg p-3 text-center"><p className="text-lg font-bold text-[hsl(var(--destructive))] dark:text-[hsl(var(--destructive))]">{stats.absent}</p><p className="text-[10px] font-semibold text-[hsl(var(--destructive))] dark:text-[hsl(var(--destructive))]">Ausentes</p></div>
 <div className="bg-info-soft border border-info-muted rounded-lg p-3 text-center"><p className="text-lg font-bold text-info-text dark:text-info">{stats.firstTime}</p><p className="text-[10px] font-semibold text-info-text dark:text-info">Nuevos</p></div>
 <div className="bg-[hsl(var(--bg-muted))] border border-[hsl(var(--border-primary))] rounded-lg p-3 text-center"><p className="text-lg font-bold text-[hsl(var(--text-primary))]">{stats.total}</p><p className="text-[10px] font-semibold text-[hsl(var(--text-secondary))]">Total</p></div>
 </div>

 {/* Attendance */}
 <div className="bg-[hsl(var(--bg-primary))] dark:bg-surface-card border border-[hsl(var(--border-primary))] rounded-lg overflow-hidden">
 <div className="px-4 py-3 border-b border-[hsl(var(--border-primary))] flex items-center justify-between">
 <h2 className="text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] flex items-center gap-1.5"><Users size={12} /> Asistencia ({people.length})</h2>
 <div className="relative">
 <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]" />
 <input type="text" value={searchQuery} onChange={e => setSearchQuery(e.target.value)} placeholder="Buscar..." className="pl-8 pr-3 py-1.5 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-muted))] text-xs text-[hsl(var(--text-primary))] focus:border-[hsl(var(--primary))] focus:outline-none w-40" />
 </div>
 </div>
 <div className="divide-y divide-[hsl(var(--border-primary))] max-h-[400px] overflow-y-auto scrollbar-thin">
 {filtered.map(person => {
 const rs = ROLE_STYLES[person.role] || ROLE_STYLES['Participante'];
 const Icon = rs.icon;
 return (
 <div key={person.persona_id} className={`px-4 py-3 flex items-center gap-3 ${rs.bg}`}>
 <div className={`size-8 rounded-lg flex items-center justify-center shrink-0 border ${rs.bg} ${rs.border}`}><Icon size={14} className={rs.text} /></div>
 <div className="flex-1 min-w-0">
 <p className="text-sm font-semibold text-[hsl(var(--text-primary))] truncate">{person.name}</p>
 <div className="flex items-center gap-2 text-[10px] font-medium text-[hsl(var(--text-secondary))]">
 <span className={`px-1.5 py-0.5 rounded font-bold ${rs.text} ${rs.bg}`}>{person.role}</span>
 {person.phone && <span>📱 {person.phone}</span>}
 </div>
 </div>
 <div className="flex items-center gap-1 shrink-0">
 <button onClick={() => updateStatus(person.persona_id, 'present')} className={`p-1.5 rounded-lg transition-all ${person.status === 'present' ? 'bg-success-soft text-success' : 'text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--bg-muted))]'}`} title="Presente"><CheckCircle2 size={16} /></button>
 <button onClick={() => updateStatus(person.persona_id, 'absent')} className={`p-1.5 rounded-lg transition-all ${person.status === 'absent' ? 'bg-danger-soft text-danger' : 'text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--bg-muted))]'}`} title="Ausente"><XCircle size={16} /></button>
 <button onClick={() => updateStatus(person.persona_id, 'first_time')} className={`p-1.5 rounded-lg transition-all ${person.status === 'first_time' ? 'bg-info-soft text-info' : 'text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--bg-muted))]'}`} title="Primera vez"><UserPlus size={16} /></button>
 </div>
 </div>
 );
 })}
 </div>
 </div>

 {/* New Guests */}
 <div className="bg-[hsl(var(--bg-primary))] dark:bg-surface-card border border-[hsl(var(--border-primary))] rounded-lg overflow-hidden">
 <div className="px-4 py-3 border-b border-[hsl(var(--border-primary))] flex items-center justify-between">
 <h2 className="text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] flex items-center gap-1.5"><UserPlus size={12} /> Invitados nuevos ({newGuests.length})</h2>
 <button onClick={addGuest} className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-[hsl(var(--primary))] text-white text-[10px] font-bold hover:bg-[hsl(var(--primary))]"><Plus size={11} /> Agregar</button>
 </div>
 <AnimatePresence>
 {newGuests.map((g, i) => (
 <motion.div key={i} initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }} className="px-4 py-3 border-b border-[hsl(var(--border-primary))] last:border-b-0 bg-info-soft">
 <div className="flex items-center gap-2">
 <input type="text" value={g.firstName} onChange={e => updateGuest(i, 'firstName', e.target.value)} placeholder="Nombre" className="flex-1 px-3 py-2 rounded-lg border border-info-muted bg-[hsl(var(--bg-primary))] dark:bg-surface-card text-sm text-[hsl(var(--text-primary))] focus:border-[hsl(var(--primary))] focus:outline-none" />
 <input type="text" value={g.lastName} onChange={e => updateGuest(i, 'lastName', e.target.value)} placeholder="Apellido" className="flex-1 px-3 py-2 rounded-lg border border-info-muted bg-[hsl(var(--bg-primary))] dark:bg-surface-card text-sm text-[hsl(var(--text-primary))] focus:border-[hsl(var(--primary))] focus:outline-none" />
 <input type="text" value={g.phone} onChange={e => updateGuest(i, 'phone', e.target.value)} placeholder="Teléfono" className="flex-1 px-3 py-2 rounded-lg border border-info-muted bg-[hsl(var(--bg-primary))] dark:bg-surface-card text-sm text-[hsl(var(--text-primary))] focus:border-[hsl(var(--primary))] focus:outline-none" />
 <button onClick={() => removeGuest(i)} className="p-2 rounded-lg text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--destructive))] hover:bg-danger-soft"><XCircle size={16} /></button>
 </div>
 </motion.div>
 ))}
 </AnimatePresence>
 {newGuests.length === 0 && <div className="px-4 py-6 text-center text-xs text-[hsl(var(--text-secondary))]">Sin invitados nuevos — agrega personas que vinieron por primera vez</div>}
 </div>

 {/* Session Details */}
 <div className="bg-[hsl(var(--bg-primary))] dark:bg-surface-card border border-[hsl(var(--border-primary))] rounded-lg p-4 space-y-4">
 <h2 className="text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] flex items-center gap-1.5"><FileText size={12} /> Detalles</h2>
 <div>
 <label className="block text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1">Tema</label>
 <input type="text" value={topic} onChange={e => setTopic(e.target.value)} placeholder="Tema de la reunión..." className="w-full px-3 py-2 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-muted))] text-sm text-[hsl(var(--text-primary))] focus:border-[hsl(var(--primary))] focus:outline-none" />
 </div>
 <div>
 <label className="block text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1">Ofrenda</label>
 <div className="relative w-48">
 <DollarSign size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]" />
 <input type="number" step="0.01" value={offering} onChange={e => setOffering(e.target.value)} placeholder="0.00" className="w-full pl-9 pr-3 py-2 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-muted))] text-sm text-[hsl(var(--text-primary))] focus:border-[hsl(var(--primary))] focus:outline-none" />
 </div>
 </div>
 <div>
 <label className="block text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1">Notas</label>
 <textarea value={reportNotes} onChange={e => setReportNotes(e.target.value)} rows={3} placeholder="Observaciones..." className="w-full px-3 py-2 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-muted))] text-sm text-[hsl(var(--text-primary))] focus:border-[hsl(var(--primary))] focus:outline-none resize-none" />
 </div>
 </div>

 {/* Submit */}
 <div className="flex items-center justify-end gap-3 pb-4">
 <button onClick={() => router.push('/plataforma/evangelism/groups')} className="px-4 h-9 rounded-lg border border-[hsl(var(--border-primary))] text-xs font-semibold text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--bg-muted))] dark:hover:bg-white/5">Cancelar</button>
 <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }} onClick={handleSubmit} disabled={saving} className="inline-flex items-center gap-2 px-6 h-10 rounded-lg bg-[hsl(var(--primary))] text-white text-sm font-bold hover:bg-[hsl(var(--primary))] disabled:opacity-60 shadow-sm">
 {saving ? <><Clock size={16} className="animate-spin" /> Guardando...</> : <><Save size={16} /> Guardar Reporte</>}
 </motion.button>
 </div>
 </div>
 </EvangelismShell>
 );
}
