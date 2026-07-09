'use client';

import EvangelismShell from '@/components/evangelism/EvangelismShell';
import ConfirmActionDrawer, { type ConfirmActionState } from '@/components/evangelism/ConfirmActionDrawer';
import EmptyState from '@/components/ui/EmptyState';
import Skeleton from '@/components/ui/Skeleton';
import ViewSwitcher from '@/components/ViewSwitcher';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';
import { useAuth } from '@/context/AuthContext';
import { DSBadge,DSCard,DSMetric } from '@/design';
import { MINIMAL_VIEWS,useViewType } from '@/hooks/useViewType';
import { ApiError,apiFetch } from '@/lib/http';
import clsx from 'clsx';
import { Award,CheckCircle2,ChevronRight,Clock,FileText,Home,Loader2 } from 'lucide-react';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useCallback,useEffect,useState } from 'react';
import { toast } from 'sonner';

interface GroupSeason { id: number; name: string; start_date: string; end_date: string; periodicity: string; status: string; }
interface Grupo { id: string; name: string; leader_name?: string; zone?: string; day_of_week?: string; time?: string; status?: string; }
interface GroupAnalytics {
 active_groups: number;
 total_sessions: number;
 total_attendance: number;
 avg_per_session: number;
 per_group: Array<{
 grupo_id: string;
 total_sessions: number;
 total_attendance: number;
 avg: number;
 }>;
}
interface SeasonForm {
 name: string;
 start_date: string;
 end_date: string;
 periodicity: 'SEMANAL' | 'MENSUAL';
}

const PERIODICITY_LABEL: Record<string, string> = { SEMANAL: 'Semanal', MENSUAL: 'Mensual' };

export default function GroupPage() {
 const { token, user } = useAuth();
 const router = useRouter();
 const { viewType, setViewType } = useViewType('evangelism_groups', 'grid');
 const [seasons, setSeasons] = useState<GroupSeason[]>([]);
 const [houses, setHouses] = useState<Grupo[]>([]);
 const [analytics, setAnalytics] = useState<GroupAnalytics | null>(null);
 const [activeSeason, setActiveSeason] = useState<GroupSeason | null>(null);
 const [loading, setLoading] = useState(true);
 const [showNewSeason, setShowNewSeason] = useState(false);
 const [showNewSession, setShowNewSession] = useState(false);
 const [confirmAction, setConfirmAction] = useState<ConfirmActionState>(null);
 const [savingSession, setSavingSession] = useState(false);
 const [savingSeason, setSavingSeason] = useState(false);
 const [counselingCount, setCounselingCount] = useState<number | null>(null);
 const [confirmReminders, setConfirmReminders] = useState<ConfirmActionState>(null);
 const [sendingReminders, setSendingReminders] = useState(false);
 const [sessionForm, setSessionForm] = useState({ grupo_id: '', session_date: new Date().toISOString().split('T')[0], topic: 'S1', report_deadline: '' });
 const [seasonForm, setSeasonForm] = useState<SeasonForm>({ name: '', start_date: '', end_date: '', periodicity: 'SEMANAL' });
 const isSeasonFormValid = Boolean(seasonForm.name.trim() && seasonForm.start_date && seasonForm.end_date);
 const isSessionFormValid = Boolean(sessionForm.grupo_id && sessionForm.session_date && activeSeason);
 const role = String(user?.role || '').toLowerCase();
 const isPrivileged = ['admin', 'administrador', 'pastor'].includes(role);

 const load = useCallback(async () => {
 if (!token) return;
 setLoading(true);
 try {
 const [s, h]: [GroupSeason[], Grupo[]] = await Promise.all([
 apiFetch<GroupSeason[]>('/evangelism/groups/seasons', { token }).catch(() => [] as GroupSeason[]),
 apiFetch<Grupo[]>('/evangelism/grupos/mine', { token }).catch(() => [] as Grupo[])
 ]);
 setSeasons(s);
 setHouses(h);
 const active = s.find(x => x.status === 'Activa') || s[0] || null;
 setActiveSeason(active);
 if (active) {
 const a = await apiFetch<GroupAnalytics>(`/evangelism/groups/analytics?season_id=${active.id}`, { token }).catch(() => null);
 setAnalytics(a);
 }
 } catch { toast.error('Error al cargar Grupos en Casa'); }
 finally { setLoading(false); }
 }, [token]);

 useEffect(() => {
 load();
 }, [load]);

 useEffect(() => {
   if (!token) return;
   apiFetch<unknown>('/crm/counseling', { token, query: { status: 'open', limit: 1 } })
     .then((res: any) => {
       const arr = Array.isArray(res) ? res : Array.isArray(res?.items) ? res.items : [];
       setCounselingCount(arr.length);
     })
     .catch(() => setCounselingCount(0));
 }, [token]);

 const triggerReminders = async () => {
   setSendingReminders(true);
   try {
     const res: any = await apiFetch('/evangelism/notifications/send-reminders', { method: 'POST', token });
     const total = res?.notifications_created ?? res?.created ?? 0;
     const sessionsT = res?.sessions_tomorrow_count ?? 0;
     const inactive = res?.inactive_groups_count ?? 0;
     toast.success(
       total
         ? `Se enviaron ${total} recordatorios (${sessionsT} sesiones de mañana, ${inactive} grupos sin reporte)`
         : 'Sin recordatorios pendientes. Todos los líderes están al día.'
     );
     setConfirmReminders(null);
   } catch (e: any) {
     toast.error(e?.message || 'Error al enviar recordatorios');
   } finally {
     setSendingReminders(false);
   }
 };

 const requestSendReminders = () => {
   setConfirmReminders({
     title: 'Disparar recordatorios pastorales',
     description: 'Se enviarán notificaciones a líderes con sesiones programadas para mañana y a grupos sin reporte de asistencia en los últimos 7 días. Esta operación es masiva pero idempotente.',
     confirmLabel: 'Enviar recordatorios',
     onConfirm: triggerReminders,
   });
 };

 const handleCreateSeason = async () => {
 if (!seasonForm.name || !seasonForm.start_date || !seasonForm.end_date) return toast.error('Completa todos los campos');
 setSavingSeason(true);
 try {
 await apiFetch('/evangelism/groups/seasons', { method: 'POST', body: seasonForm, token });
 toast.success('Temporada creada');
 setShowNewSeason(false);
 setSeasonForm({ name: '', start_date: '', end_date: '', periodicity: 'SEMANAL' });
 load();
 } catch (e) {
 const detail = e instanceof ApiError && typeof e.detail === 'object' && e.detail && 'detail' in e.detail
 ? String((e.detail as { detail?: string }).detail || '')
 : '';
 toast.error(detail || 'Error al crear temporada');
 }
 finally { setSavingSeason(false); }
 };

 const handleCreateSession = async () => {
 if (!sessionForm.grupo_id || !sessionForm.session_date || !activeSeason) return toast.error('Selecciona el grupo y la fecha');
 setSavingSession(true);
 try {
 const bodyPayload: any = { ...sessionForm, season_id: activeSeason.id };
 if (sessionForm.grupo_id !== 'all') {
 bodyPayload.grupo_id = sessionForm.grupo_id;
 } else {
 bodyPayload.grupo_id = 'all';
 }
 delete bodyPayload.grupo_id;
 if (sessionForm.report_deadline) {
 bodyPayload.report_deadline = sessionForm.report_deadline + ':00Z';
 } else {
 delete bodyPayload.report_deadline;
 }

 const res = await apiFetch<{ message: string, created_count: number }>('/evangelism/groups/sessions', { method: 'POST', body: bodyPayload, token });
 toast.success(res.message || 'Sesión registrada');
 setShowNewSession(false);
 setSessionForm({ grupo_id: '', session_date: new Date().toISOString().split('T')[0], topic: 'S1', report_deadline: '' });
 load();
 } catch (e) {
 const detail = e instanceof ApiError && typeof e.detail === 'object' && e.detail && 'detail' in e.detail
 ? String((e.detail as { detail?: string }).detail || '')
 : '';
 toast.error(detail || 'Error al registrar sesión');
 }
 finally { setSavingSession(false); }
 };

 const closeSeason = async (id: number) => {
 await apiFetch(`/evangelism/groups/seasons/${id}`, { method: 'PATCH', body: { status: 'Finalizada' }, token });
 toast.success('Temporada finalizada');
 load();
 };

 const handleCloseSeason = (id: number) => {
 setConfirmAction({
 title: 'Finalizar temporada',
 description: 'La temporada quedará finalizada y dejará de aparecer como activa para nuevos reportes.',
 confirmLabel: 'Finalizar',
 destructive: true,
 onConfirm: () => closeSeason(id),
 });
 };

 if (loading) {
 return (
 <EvangelismShell breadcrumbs={[]}>
 <div className="p-4 space-y-3">
 <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
 {[1, 2, 3, 4].map(i => <Skeleton key={i} className="h-32 rounded-lg" />)}
 </div>
 <Skeleton className="h-[400px] rounded-lg" />
 </div>
 </EvangelismShell>
 );
 }

 return (
 <EvangelismShell breadcrumbs={[]}>
 <div className="p-4 space-y-3">
 {/* Page Header Area */}
 <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
 <div>
 <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1">Evangelismo · Estrategia</p>
 <h1 className="text-xl font-bold text-[hsl(var(--text-primary))] tracking-tight">Grupos en Casa</h1>
 {activeSeason
 ? <p className="text-[hsl(var(--text-secondary))] text-sm font-medium flex items-center gap-1.5 mt-2">
 <span className="inline-block size-2 rounded-full bg-emerald-500" />
 Temporada activa: <strong className="text-[hsl(var(--text-primary))] ">{activeSeason.name}</strong>
 <span className="text-[hsl(var(--text-secondary))] /20">·</span>
 {PERIODICITY_LABEL[activeSeason.periodicity]}
 </p>
 : <p className="text-amber-500 text-sm font-bold mt-2 flex items-center gap-2">
 <Clock size={16} /> Sin temporada activa. Crea una para comenzar.
 </p>
 }
 </div>
 </div>

 {/* View Switcher */}
 <div className="flex items-center gap-2 mt-2 mb-4">
 <ViewSwitcher viewType={viewType} setViewType={setViewType} availableViews={MINIMAL_VIEWS} />
 </div>

 {/* KPIs */}
 <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
 <DSMetric label="Grupos Activos" value={String(analytics?.active_groups ?? '—')} tone="emerald" trend="Red actual" />
 <DSMetric label="Sesiones Totales" value={String(analytics?.total_sessions ?? '—')} tone="blue" trend={activeSeason?.name} />
 <DSMetric label="Asistentes Totales" value={String(analytics?.total_attendance ?? '—')} tone="blue" trend="Acumulado" />
 <DSMetric label="Promedio / Sesión" value={String(analytics?.avg_per_session ?? '—')} tone="amber" trend="Por semana" />
 </div>

 {isPrivileged && (
  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
   <button onClick={requestSendReminders} disabled={sendingReminders}
    className="flex items-center gap-3 px-4 py-3 rounded-lg bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border-primary))] hover:border-blue-300 dark:hover:border-blue-500 hover:shadow-md transition-all text-left disabled:opacity-60">
    <div className="size-10 rounded-lg bg-blue-100 dark:bg-blue-900/30 text-[hsl(var(--primary))] flex items-center justify-center shrink-0">
     {sendingReminders ? <Loader2 size={18} className="animate-spin" /> : <FileText size={18} />}
    </div>
    <div className="flex-1 min-w-0">
     <p className="text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]">Acción pastoral</p>
     <p className="text-sm font-bold text-[hsl(var(--text-primary))] mt-0.5">Disparar recordatorios</p>
     <p className="text-[10px] text-[hsl(var(--text-secondary))] mt-0.5 truncate">Notifica a líderes sobre sesiones de mañana y reportes atrasados.</p>
    </div>
   </button>
   <Link href="/plataforma/crm?counseling=open"
    className="flex items-center gap-3 px-4 py-3 rounded-lg bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border-primary))] hover:border-amber-300 dark:hover:border-amber-500 hover:shadow-md transition-all">
    <div className="size-10 rounded-lg bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 flex items-center justify-center shrink-0">
     <Award size={18} />
    </div>
    <div className="flex-1 min-w-0">
     <p className="text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]">Seguimiento pastoral</p>
     <p className="text-sm font-bold text-[hsl(var(--text-primary))] mt-0.5">
      Consejería pendiente
      {counselingCount !== null && (
       <span className="ml-2 px-2 py-0.5 rounded-md bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 text-[10px] font-bold">{counselingCount}</span>
      )}
     </p>
     <p className="text-[10px] text-[hsl(var(--text-secondary))] mt-0.5 truncate">Tickets abiertos esperando respuesta pastoral.</p>
    </div>
   </Link>
  </div>
 )}

 <div className="space-y-3 pb-12">
 {/* Mis Grupos */}
 <section>
 <h2 className="text-[11px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-3">Mis Grupos</h2>
 {houses.length === 0 ? (
 <EmptyState 
 icon={Home} 
 title="Sin Grupos Asignados" 
 description="No tienes ningún grupo asignado como líder." 
 />
 ) : (
 <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
 {houses.map((h) => (
 <button
 key={h.id}
 onClick={() => router.push(`/plataforma/evangelism/groups/${h.id}`)}
 className="text-left bg-[hsl(var(--bg-primary))] rounded-lg border border-[hsl(var(--border-primary))] p-3 shadow-sm hover:shadow-xl hover:shadow-blue-500/5 hover:border-blue-500/30 transition-all group"
 >
 <div className="size-7 rounded-lg bg-blue-50 dark:bg-blue-900/30 text-[hsl(var(--primary))] flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
 <Home size={24} />
 </div>
 <p className="text-lg font-bold text-[hsl(var(--text-primary))]">{h.name}</p>
 <p className="text-sm font-bold text-[hsl(var(--text-secondary))] mt-1">{h.zone || 'Sin zona'} · {h.day_of_week || 'Sin dia'}</p>
 </button>
 ))}
 </div>
 )}
 </section>

 {/* Temporadas */}
 {isPrivileged && (
 <section>
 <h2 className="text-[11px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-3">Temporadas</h2>
 {seasons.length === 0 ? (
 <EmptyState 
 icon={Clock} 
 title="No hay temporadas" 
 description="Crea la primera temporada para comenzar a registrar sesiones."
 onAction={() => setShowNewSeason(true)}
 actionLabel="Nueva Temporada"
 />
 ) : (
 <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
 {seasons.map(s => (
 <div key={s.id} className={clsx(
 "bg-[hsl(var(--bg-primary))] rounded-lg border p-3 shadow-sm transition-all",
 s.status === 'Activa' ? 'border-blue-400/50 shadow-blue-500/10' : 'border-[hsl(var(--border-primary))]'
 )}>
 <div className="flex items-start justify-between mb-4">
 <DSBadge tone={s.status === 'Activa' ? 'emerald' : 'slate'} label={s.status} />
 <span className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">{PERIODICITY_LABEL[s.periodicity]}</span>
 </div>
 <h3 className="text-xl font-bold text-[hsl(var(--text-primary))] mb-2 tracking-tight">{s.name}</h3>
 <p className="text-sm text-[hsl(var(--text-secondary))] font-bold mb-3">{s.start_date} → {s.end_date}</p>
 {s.status === 'Activa' && (
 <button onClick={() => handleCloseSeason(s.id)} className="w-full py-2 bg-red-50 text-[hsl(var(--destructive))] dark:bg-red-500/10 dark:text-[hsl(var(--destructive))] rounded-md text-[10px] font-semibold uppercase tracking-wide hover:bg-red-100 dark:hover:bg-red-500/20 transition-colors">
 Finalizar Temporada
 </button>
 )}
 </div>
 ))}
 </div>
 )}
 </section>
 )}

 {/* Desempeño por Grupo */}
 {isPrivileged && Boolean(analytics && analytics.per_group && analytics.per_group.length > 0) && (
 <section>
 <h2 className="text-[11px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-3">Desempeño por Grupo · {activeSeason?.name}</h2>
 <DSCard tone="light" className="shadow-2xl overflow-hidden rounded-lg">
 <div className="overflow-x-auto">
 <table className="w-full text-left">
 <thead className="bg-[hsl(var(--bg-secondary))] text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
 <tr>
 <th className="px-4 py-1.5">Grupo</th>
 <th className="px-4 py-1.5 text-center">Sesiones</th>
 <th className="px-4 py-1.5 text-center">Asistentes</th>
 <th className="px-4 py-1.5 text-center">Promedio</th>
 </tr>
 </thead>
 <tbody className="divide-y divide-[hsl(var(--border-primary))]">
 {analytics!.per_group.map((row) => {
 const house = houses.find(h => h.id === row.grupo_id);
 return (
 <tr key={row.grupo_id} onClick={() => router.push(`/plataforma/evangelism/groups/${row.grupo_id}`)} className="group hover:bg-[hsl(var(--bg-muted))] dark:hover:bg-white/[0.01] transition-colors cursor-pointer">
 <td className="px-4 py-2">
 <div className="flex items-center gap-4">
 <div className="size-10 rounded-md bg-blue-100 dark:bg-blue-900/30 text-[hsl(var(--primary))] flex items-center justify-center shrink-0 group-hover:scale-110 transition-transform"><Home size={18} /></div>
 <span className="text-base font-bold text-[hsl(var(--text-primary))] group-hover:text-[hsl(var(--primary))] transition-colors">{house?.name || `Grupo #${row.grupo_id}`}</span>
 </div>
 </td>
 <td className="px-4 py-2 text-center text-sm font-bold text-[hsl(var(--text-secondary))]">{row.total_sessions}</td>
 <td className="px-4 py-2 text-center">
 <span className="px-4 py-1.5 bg-blue-100 dark:bg-blue-900/30 text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))] rounded-md text-sm font-semibold">{row.total_attendance}</span>
 </td>
 <td className="px-4 py-2 text-center text-sm font-bold text-[hsl(var(--text-secondary))]">{row.avg}</td>
 </tr>
 );
 })}
 </tbody>
 </table>
 </div>
 </DSCard>
 </section>
 )}
 </div>
 </div>

 {/* NEW SEASON DRAWER */}
 <WorkspaceDrawer
 isOpen={showNewSeason && isPrivileged}
 onClose={() => setShowNewSeason(false)}
 title="Nueva Temporada"
 subtitle="Configura una nueva temporada para Grupos en Casa"
 actions={
 <>
 <button disabled={savingSeason} onClick={() => setShowNewSeason(false)} className="px-4 py-2 text-[11px] font-bold text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] transition-colors disabled:opacity-60">
 Cancelar
 </button>
 <button onClick={handleCreateSeason} disabled={savingSeason || !isSeasonFormValid} className="flex items-center gap-2 px-3 py-2 bg-[hsl(var(--primary))] text-white rounded-lg text-[11px] font-semibold uppercase tracking-wide shadow-lg shadow-blue-500/20 hover:bg-[hsl(var(--primary))] active:scale-95 transition-all disabled:opacity-60">
 {savingSeason ? <Loader2 size={14} className="animate-spin" /> : <CheckCircle2 size={14} />} Crear
 </button>
 </>
 }
 >
 <div className="space-y-3 mt-4">
 {[
 { label: 'Nombre de la Campaña', key: 'name', type: 'text', placeholder: 'Grupos en Casa Temporada 2026' },
 { label: 'Fecha de Inicio', key: 'start_date', type: 'date', placeholder: '' },
 { label: 'Fecha de Cierre', key: 'end_date', type: 'date', placeholder: '' },
 ].map(f => (
 <div key={f.key} className="space-y-1.5">
 <label className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] block">{f.label}</label>
 <input type={f.type} placeholder={f.placeholder} value={seasonForm[f.key as keyof SeasonForm]} onChange={e => setSeasonForm(p => ({ ...p, [f.key]: e.target.value } as SeasonForm))} className="w-full bg-[hsl(var(--bg-muted))] dark:bg-black/20 border border-[hsl(var(--border-primary))] rounded-lg py-1.5 px-4 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500" />
 </div>
 ))}
 <div className="space-y-1.5">
 <label className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] block">Periodicidad de Reporte</label>
 <select value={seasonForm.periodicity} onChange={e => setSeasonForm(p => ({ ...p, periodicity: e.target.value as SeasonForm['periodicity'] }))} className="w-full bg-[hsl(var(--bg-muted))] dark:bg-black/20 border border-[hsl(var(--border-primary))] rounded-lg py-1.5 px-4 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500 appearance-none">
 <option value="SEMANAL">Semanal (Reporte cada semana)</option>
 <option value="MENSUAL">Mensual (Reporte cada mes)</option>
 </select>
 </div>
 </div>
 </WorkspaceDrawer>

 {/* NEW SESSION DRAWER */}
 <WorkspaceDrawer
 isOpen={showNewSession && !!activeSeason && isPrivileged}
 onClose={() => setShowNewSession(false)}
 title="Registrar Sesión Semanal"
 subtitle="Ingresa la asistencia y detalles de la reunión"
 actions={
 <>
 <button disabled={savingSession} onClick={() => setShowNewSession(false)} className="px-4 py-2 text-[11px] font-bold text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] transition-colors disabled:opacity-60">
 Cancelar
 </button>
 <button onClick={handleCreateSession} disabled={savingSession || !isSessionFormValid} className="flex items-center gap-2 px-3 py-2 bg-emerald-600 text-white rounded-lg text-[11px] font-semibold uppercase tracking-wide shadow-lg shadow-emerald-500/20 hover:bg-emerald-700 active:scale-95 transition-all disabled:opacity-60">
 {savingSession ? <Loader2 size={14} className="animate-spin" /> : <ChevronRight size={14} />} Registrar
 </button>
 </>
 }
 >
 <div className="space-y-3 mt-4">
 <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-100 dark:border-blue-900/30">
 <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--primary))] dark:text-blue-300 mb-1">Temporada Activa</p>
 <p className="text-sm font-bold text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))]">{activeSeason?.name}</p>
 </div>
 
 <div className="space-y-1.5">
 <label className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] block">Grupo</label>
 <select value={sessionForm.grupo_id} onChange={e => setSessionForm(p => ({ ...p, grupo_id: e.target.value }))} className="w-full bg-[hsl(var(--bg-muted))] dark:bg-black/20 border border-[hsl(var(--border-primary))] rounded-lg py-1.5 px-4 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500 appearance-none">
 <option value="">— Seleccionar Grupo —</option>
 {isPrivileged && <option value="all" className="font-bold">✨ TODOS LOS GRUPOS ACTIVOS</option>}
 {houses.map(h => <option key={h.id} value={h.id}>{h.name} {h.leader_name ? `· Líder: ${h.leader_name}` : ''}</option>)}
 </select>
 {sessionForm.grupo_id === 'all' && (
 <p className="text-[10px] text-[hsl(var(--primary))] font-bold mt-1">Se creará una sesión idéntica para todas las casas activas simultáneamente.</p>
 )}
 </div>
 
 <div className="grid grid-cols-2 gap-4">
 <div className="space-y-1.5">
 <label className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] block">Nombre / Alias (Ej. S1)</label>
 <input type="text" placeholder="S1" value={sessionForm.topic} onChange={e => setSessionForm(p => ({ ...p, topic: e.target.value }))} className="w-full bg-[hsl(var(--bg-muted))] dark:bg-black/20 border border-[hsl(var(--border-primary))] rounded-lg py-1.5 px-4 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500" />
 </div>
 <div className="space-y-1.5">
 <label className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] block">Fecha de la Reunión</label>
 <input type="date" value={sessionForm.session_date} onChange={e => setSessionForm(p => ({ ...p, session_date: e.target.value }))} className="w-full bg-[hsl(var(--bg-muted))] dark:bg-black/20 border border-[hsl(var(--border-primary))] rounded-lg py-1.5 px-4 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500" />
 </div>
 </div>

 <div className="space-y-1.5">
 <label className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] block flex items-center gap-2">
 Fecha y Hora Límite para Reportar <span className="px-1.5 py-0.5 rounded-md bg-[hsl(var(--bg-muted))] text-[8px] font-bold">OPCIONAL</span>
 </label>
 <input type="datetime-local" value={sessionForm.report_deadline} onChange={e => setSessionForm(p => ({ ...p, report_deadline: e.target.value }))} className="w-full bg-[hsl(var(--bg-muted))] dark:bg-black/20 border border-[hsl(var(--border-primary))] rounded-lg py-1.5 px-4 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500" />
 <p className="text-[10px] text-[hsl(var(--text-secondary))] mt-1">Si configuras este límite, los líderes no podrán guardar asistencia después de esta hora.</p>
 </div>
 </div>
 </WorkspaceDrawer>
 <ConfirmActionDrawer action={confirmAction} onClose={() => setConfirmAction(null)} />
 <ConfirmActionDrawer action={confirmReminders} onClose={() => setConfirmReminders(null)} />
 </EvangelismShell>
 );
}
