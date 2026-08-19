"use client";

import type {
  BulkHabilitacionResponse,
  GroupDetailResponse,
  SessionDetailResponse,
  SessionRow,
  StrategyGroup,
} from '../../types';
import { formatLocalDate, getErrorMessage, toAttendanceStatus } from '../../utils';
import { type ConfirmActionState } from '@/components/evangelism/ConfirmActionDrawer';
import {
  AttendancePersona,
  AttendanceSaveResult,
  CustomRole,
  customRoleValue,
  FALLBACK_MEMBER_ROLES,
  isAssistantLeaderRole,
  isPrimaryLeaderRole,
  ROLE_COLORS,
  roleMatches,
  TabId,
} from './strategyDetailShared';
import {
  useCustomRoles,
  useFollowUps,
  useGroups,
  useMetrics,
  useRemotePersonaSearch,
  useSessionActions,
  useSessions,
  useStrategy,
} from './useStrategyDetail';
import { useAuth } from '@/context/AuthContext';
import { useViewType } from '@/hooks/useViewType';
import type { GroupForm, RoleSearchPersona } from './panels/GroupCreationDrawer';
import { apiFetch } from '@/lib/http';
import { useParams, useRouter } from 'next/navigation';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { toast } from 'sonner';

type SearchablePersona = {
  id: string;
  nombre_completo?: string;
  first_name?: string;
  last_name?: string;
  email?: string;
  church_role?: string;
};

type RoleSearchQuery = { limit: number; search?: string; sort_by?: string; sort_dir?: string };

export function useStrategyDetailPage() {
 const params = useParams();
 const id = (params?.id as string) || '';
 const router = useRouter();
 const { token, loading: authLoading, hasModuleAccess } = useAuth();
 const canReadStrategySurface = hasModuleAccess('evangelism', 'read');
 const canManageStrategySurface = hasModuleAccess('evangelism', 'manage');
 const {
 strategy,
 loading,
 loadError,
 saving,
 editName,
 setEditName,
 editDesc,
 setEditDesc,
 editType,
 setEditType,
 editStatus,
 setEditStatus,
 editActiva,
 setEditActiva,
 editClaseRaiz,
 setEditClaseRaiz,
 editDefaultRoleId,
 setEditDefaultRoleId,
 editStartDate,
 setEditStartDate,
 editEndDate,
 setEditEndDate,
 editRecurrence,
 setEditRecurrence,
 fetchStrategy,
 handleSave,
 handleDelete,
 } = useStrategy(id, token);

 // Roles personalizados
 const {
 customRoles,
 setCustomRoles,
 loadingRoles,
 showRoleForm,
 setShowRoleForm,
 newRoleName,
 setNewRoleName,
 newRoleDesc,
 setNewRoleDesc,
 fetchCustomRoles,
 } = useCustomRoles(id, token);

 // Seguimiento
 const { followUps, loadingFollowUps, fetchFollowUps } = useFollowUps(token, id);
 const [confirmAction, setConfirmAction] = useState<ConfirmActionState>(null);
 const [activeTab, setActiveTab] = useState<TabId>('overview');
 const { viewType, setViewType } = useViewType(`strategy_${id}`, 'dashboard');
 const { groups, groupsLoading, fetchGroups } = useGroups(id, token);
 const { metrics, fetchMetrics } = useMetrics(id, token);
 const [personaCache, setPersonaCache] = useState<Record<string, RoleSearchPersona>>({});
 const [roleResults, setRoleResults] = useState<Record<string, RoleSearchPersona[]>>({});
 const [roleLoading, setRoleLoading] = useState<Record<string, boolean>>({});

 // Group creation drawer
 const [isGroupDrawerOpen, setIsGroupDrawerOpen] = useState(false);
 const [groupForm, setGroupForm] = useState<GroupForm>({
 name: '', zone: '', address: '', capacity: 15,
 day_of_week: '', start_time: '', end_time: '',
 });
 const [groupRoleAssignments, setGroupRoleAssignments] = useState<Record<string, string | null>>({});
 const [groupSaving, setGroupSaving] = useState(false);
 const [roleSearch, setRoleSearch] = useState<Record<string, string>>({});
 const [roleDropdown, setRoleDropdown] = useState<string | null>(null);

 // Persona management drawer
 const [isPersonaDrawerOpen, setIsPersonaDrawerOpen] = useState(false);
 const [selectedGroup, setSelectedGroup] = useState<StrategyGroup | null>(null);
 const [groupPersonas, setGroupPersonas] = useState<{ id: string; name: string; email: string; role: string; role_label?: string }[]>([]);
 const [personaSearch, setPersonaSearch] = useState('');
 const [personaSearchLoading, setPersonaSearchLoading] = useState(false);
 const [personaSearchResults, setPersonaSearchResults] = useState<SearchablePersona[]>([]);
 const [personaSaving, setPersonaSaving] = useState(false);
 const [personaSplitHeight, setPersonaSplitHeight] = useState(200);
 const personaSplitRef = useRef<HTMLDivElement>(null);
 const { search: searchPersonas, cancel: cancelPersonaSearch } = useRemotePersonaSearch(token);

 const handlePersonaSplitDrag = useCallback((e: React.MouseEvent) => {
 e.preventDefault();
 const startY = e.clientY;
 const startHeight = personaSplitRef.current
 ? personaSplitRef.current.querySelector<HTMLDivElement>(':first-child')?.offsetHeight ?? 200
 : 200;
 const onMouseMove = (ev: MouseEvent) => {
 const containerH = personaSplitRef.current?.clientHeight ?? 600;
 const next = Math.max(80, Math.min(startHeight + ev.clientY - startY, containerH - 140));
 setPersonaSplitHeight(next);
 };
 const onMouseUp = () => {
 document.removeEventListener('mousemove', onMouseMove);
 document.removeEventListener('mouseup', onMouseUp);
 };
 document.addEventListener('mousemove', onMouseMove);
 document.addEventListener('mouseup', onMouseUp);
 }, []);

 // Sessions
 const { sessions, setSessions, sessionsLoading, fetchSessions } = useSessions(id, token);
 const { toggleSessionHabilitacion, handleDeleteSession: deleteSession } = useSessionActions(fetchSessions, token);
 const [isNewSessionDrawerOpen, setIsNewSessionDrawerOpen] = useState(false);
 const [sessionForm, setSessionForm] = useState({
 grupo_id: '' as string | number,
 session_date: formatLocalDate(new Date()),
 topic: '',
 offering_amount: '',
 report_notes: '',
 });
 const [sessionSaving, setSessionSaving] = useState(false);

 // Attendance drawer
 const [attendanceSession, setAttendanceSession] = useState<SessionRow | null>(null);
 const [attendancePersonas, setAttendancePersonas] = useState<AttendancePersona[]>([]);
 const [attendanceSaving, setAttendanceSaving] = useState(false);
 const [isAttendanceDrawerOpen, setIsAttendanceDrawerOpen] = useState(false);

 // Session menu
 const [sessionMenuId, setSessionMenuId] = useState<string | null>(null);
 const [shareMenuId, setShareMenuId] = useState<string | null>(null);
 const [sessionGroupFilter, setSessionGroupFilter] = useState<string | 'all'>('all');
 const [sessionHabFilter, setSessionHabFilter] = useState<'all' | 'HABILITADO' | 'DESHABILITADO' | 'CERRADO'>('all');
 const [sessionMonthFilter, setSessionMonthFilter] = useState<string>('all');
 const [sessionSearch, setSessionSearch] = useState('');
 const [tableSubTab, setTableSubTab] = useState<'groups' | 'sessions'>('groups');

 useEffect(() => {
 if (sessionMenuId === null) return;
 const close = () => setSessionMenuId(null);
 document.addEventListener('click', close);
 return () => document.removeEventListener('click', close);
 }, [sessionMenuId]);

 useEffect(() => {
 if (shareMenuId === null) return;
 const close = () => setShareMenuId(null);
 document.addEventListener('click', close);
 return () => document.removeEventListener('click', close);
 }, [shareMenuId]);

 const personaRoleOptions = customRoles.length > 0
 ? [
 ...customRoles.map(role => ({ value: customRoleValue(role), label: role.nombre_rol })),
 { value: 'visitante', label: 'Visitante' },
 ]
 : FALLBACK_MEMBER_ROLES;

 const selectedDefaultRole = customRoles.find(role => role.id === editDefaultRoleId) || null;
 const defaultPersonaRoleLinkValue = selectedDefaultRole
 ? customRoleValue(selectedDefaultRole)
 : personaRoleOptions[0]?.value || 'persona';
 const defaultPersonaRoleLinkLabel = selectedDefaultRole?.nombre_rol
 || personaRoleOptions[0]?.label
 || 'Persona';
 const strategyGroupCount = strategy?.grupos_count ?? null;

 const getRoleLabel = (value: string, fallback?: string) => {
 const customId = value?.startsWith('custom:') ? value.split(':')[1] : null;
 if (customId) {
 return customRoles.find(role => role.id === customId)?.nombre_rol || fallback || value;
 }
 return personaRoleOptions.find(role => role.value === value)?.label || fallback || value;
 };

 const getRoleColor = (value: string) => {
 if (value?.startsWith('custom:')) return ROLE_COLORS.personalizado;
 return ROLE_COLORS[value] || ROLE_COLORS.persona;
 };

 const buildRoleDrivenGroupAssignments = (): {
 fixed: { leader_id: string | null; assistant_id: string | null; host_id: string | null };
 base_attendees_with_roles: Array<{ persona_id: string; role: string; rol_personalizado_id: string }>;
 } => {
 const assigned = customRoles
 .map(role => ({
 role,
 personaId: groupRoleAssignments[customRoleValue(role)],
 }))
 .filter((item): item is { role: CustomRole; personaId: string } => Boolean(item.personaId));

 const fixed = {
 leader_id: null as string | null,
 assistant_id: null as string | null,
 host_id: null as string | null,
 };

 assigned.forEach(({ role, personaId }) => {
 if (isPrimaryLeaderRole(role)) fixed.leader_id ||= personaId;
 if (isAssistantLeaderRole(role)) fixed.assistant_id ||= personaId;
 if (roleMatches(role, ['anfitrion'])) fixed.host_id ||= personaId;
 });

 return {
 fixed,
 base_attendees_with_roles: assigned.map(({ role, personaId }) => ({
 persona_id: personaId,
 role: customRoleValue(role),
 rol_personalizado_id: role.id,
 })),
 };
 };

 useEffect(() => {
 if (authLoading) return;
 if (!token || !canReadStrategySurface) return;
 fetchStrategy();
 fetchFollowUps();
 if (canManageStrategySurface) {
 fetchCustomRoles();
 } else {
 setCustomRoles([]);
 }
 }, [authLoading, canManageStrategySurface, canReadStrategySurface, fetchStrategy, fetchCustomRoles, fetchFollowUps, setCustomRoles, token]);

 // Cargar grupos al montar para que aparezcan en el sidebar
 useEffect(() => {
 if (token && canReadStrategySurface) fetchGroups();
 }, [canReadStrategySurface, fetchGroups, token]);

 useEffect(() => {
 if (!token || !canReadStrategySurface) return;
 if (activeTab === 'groups') fetchGroups();
 if (activeTab === 'metrics') fetchMetrics();
 if (activeTab === 'sessions') { fetchGroups(); fetchSessions(); }
 if (activeTab === 'attendance') { fetchGroups(); fetchSessions(); }
 }, [activeTab, canReadStrategySurface, fetchGroups, fetchMetrics, fetchSessions, token]);

 useEffect(() => {
 if (!roleDropdown || !token || !canManageStrategySurface) return;
 const field = roleDropdown;
 const query = (roleSearch[field] || '').trim();
 setRoleLoading(l => ({ ...l, [field]: true }));
 const timer = setTimeout(async () => {
 try {
 const params: RoleSearchQuery = query.length >= 1
 ? { limit: 200, search: query }
 : { limit: 1000, sort_by: 'first_name', sort_dir: 'asc' };
 const res = await apiFetch<RoleSearchPersona[]>('/crm/personas', { token, silent: true, query: params });
 setRoleResults(r => ({ ...r, [field]: res || [] }));
 } catch {
 setRoleResults(r => ({ ...r, [field]: [] }));
 } finally {
 setRoleLoading(l => ({ ...l, [field]: false }));
 }
 }, query.length >= 1 ? 300 : 0);
 return () => clearTimeout(timer);
 }, [canManageStrategySurface, roleSearch, roleDropdown, token]);

 const openGroupDrawer = () => {
 setGroupForm({
 name: '', zone: '', address: '', capacity: 15,
 day_of_week: strategy?.typology === 'relacional' ? strategy.day_of_week || '' : '',
 start_time: strategy?.typology === 'relacional' ? strategy.start_time || '' : '',
 end_time: '',
 });
 setGroupRoleAssignments(Object.fromEntries(customRoles.map(role => [customRoleValue(role), null])));
 setRoleSearch({});
 setRoleResults({});
 setRoleLoading({});
 setRoleDropdown(null);
 setIsGroupDrawerOpen(true);
 };

 const handleCreateGroup = async () => {
 if (!groupForm.name.trim()) { toast.error('El nombre del grupo es obligatorio'); return; }
 setGroupSaving(true);
 try {
 const roleDrivenAssignments = buildRoleDrivenGroupAssignments();
 await apiFetch('/evangelism/grupos', {
 method: 'POST', token,
 silent: true,
 body: {
 name: groupForm.name.trim(),
 code: null,
 zone: groupForm.zone || null,
 address: groupForm.address || null,
 latitude: null, longitude: null,
 leader_name: null,
 leader_id: roleDrivenAssignments.fixed.leader_id,
 assistant_id: roleDrivenAssignments.fixed.assistant_id,
 host_id: roleDrivenAssignments.fixed.host_id,
 evangelism_strategy_id: id,
 personas_count: 0, capacity: groupForm.capacity,
 status: 'Activo',
 day_of_week: groupForm.day_of_week || null,
 start_time: groupForm.start_time || null,
 end_time: groupForm.end_time || null,
 base_attendees_with_roles: roleDrivenAssignments.base_attendees_with_roles,
 },
 });
 toast.success('Grupo creado');
 setIsGroupDrawerOpen(false);
 fetchGroups(); fetchStrategy();
 } catch (error: unknown) {
 toast.error('Error al crear: ' + getErrorMessage(error, 'Intente de nuevo'));
 } finally { setGroupSaving(false); }
 };

 const handleDeleteGroup = async (groupId: string) => {
 try {
 await apiFetch(`/evangelism/grupos/${groupId}`, { method: 'DELETE', token, silent: true });
 toast.success('Grupo eliminado');
 fetchGroups(); fetchStrategy();
 } catch { toast.error('Error al eliminar'); }
 };

 const requestDeleteGroup = (groupId: string, groupName: string) => {
 setConfirmAction({
 title: 'Eliminar grupo',
 description: `Se eliminará "${groupName}" y todo su historial de asistencia.`,
 confirmLabel: 'Eliminar',
 destructive: true,
 onConfirm: () => handleDeleteGroup(groupId),
 });
 };

 // ── Persona management ──
 const openPersonaDrawer = async (group: StrategyGroup) => {
 setSelectedGroup(group);
 setIsPersonaDrawerOpen(true);
 setPersonaSearch('');
 setPersonaSearchResults([]);
 setPersonaSplitHeight(200);
 try {
 const house = await apiFetch<GroupDetailResponse>(`/evangelism/grupos/${group.id}`, { token, silent: true });
 setGroupPersonas(house?.base_attendees?.map((a) => ({
 id: a.persona_id,
 name: a.name || a.persona?.nombre_completo || '',
 email: a.persona?.email || '',
 role: a.role || 'persona',
 role_label: a.role_label,
 })) || []);
 } catch { setGroupPersonas([]); }
 };

 useEffect(() => {
 if (!token || !isPersonaDrawerOpen) return;
 const q = personaSearch.trim();
 if (q.length < 3) {
 setPersonaSearchLoading(false);
 setPersonaSearchResults([]);
 cancelPersonaSearch();
 return;
 }
 setPersonaSearchLoading(true);
 const handle = setTimeout(() => {
 searchPersonas(q, 12)
 .then(results => {
 setPersonaSearchResults(results);
 })
 .catch(() => {
 setPersonaSearchResults([]);
 })
 .finally(() => {
 setPersonaSearchLoading(false);
 });
 }, 300);
 return () => {
 clearTimeout(handle);
 cancelPersonaSearch();
 };
 }, [cancelPersonaSearch, isPersonaDrawerOpen, personaSearch, searchPersonas, token]);

 const handleSavePersonas = async () => {
 if (!selectedGroup) return;
 setPersonaSaving(true);
 try {
 await apiFetch(`/evangelism/grupos/${selectedGroup.id}`, {
 method: 'PUT', token,
 silent: true,
 body: {
  base_attendees_with_roles: groupPersonas.map(m => ({
   persona_id: m.id,
   role: m.role,
   rol_personalizado_id: m.role.startsWith('custom:') ? m.role.split(':')[1] : null,
  })),
 },
 });
 toast.success('Personas actualizados');
 setIsPersonaDrawerOpen(false);
 fetchGroups();
 } catch (error: unknown) {
 toast.error('Error al guardar: ' + getErrorMessage(error, 'Intente de nuevo'));
 } finally { setPersonaSaving(false); }
 };

 const addPersonaToGroup = (persona: SearchablePersona) => {
 if (groupPersonas.find(m => m.id === persona.id)) return;
 setGroupPersonas(prev => [...prev, {
 id: persona.id,
 name: persona.nombre_completo || `${persona.first_name ?? ''} ${persona.last_name ?? ''}`.trim(),
 email: persona.email || '',
 role: defaultPersonaRoleLinkValue,
 role_label: defaultPersonaRoleLinkLabel,
 }]);
 };

 const updateGroupPersonaRole = (personaId: string, role: string) => {
 setGroupPersonas(prev => prev.map(m => m.id === personaId ? { ...m, role, role_label: getRoleLabel(role) } : m));
 };

 const removePersonaFromGroup = (personaId: string) => {
 setGroupPersonas(prev => prev.filter(m => m.id !== personaId));
 };

 // ── Sessions ──
 const handleCreateSession = async () => {
 if (!sessionForm.grupo_id) { toast.error('Selecciona un grupo'); return; }
 if (!sessionForm.session_date) { toast.error('Selecciona una fecha'); return; }
 setSessionSaving(true);
 try {
 await apiFetch('/evangelism/sessions', {
 method: 'POST', token, silent: true,
 body: {
 grupo_id: sessionForm.grupo_id,
 session_date: `${sessionForm.session_date}T12:00:00`,
 topic: sessionForm.topic || null,
 offering_amount: sessionForm.offering_amount ? parseFloat(sessionForm.offering_amount) : null,
 report_notes: sessionForm.report_notes || null,
 status: 'Realizada',
 },
 });
 toast.success('Sesión registrada');
 setIsNewSessionDrawerOpen(false);
 setSessionForm({ grupo_id: '', session_date: formatLocalDate(new Date()), topic: '', offering_amount: '', report_notes: '' });
 fetchSessions();
 } catch (error: unknown) {
 toast.error('Error al guardar: ' + getErrorMessage(error, 'Intente de nuevo'));
 } finally { setSessionSaving(false); }
 };

 const openMassAttendance = async () => {
  if (!token || !canManageStrategySurface || strategy?.typology !== 'evento_masivo') return;
  try {
   const event = await apiFetch<{ id: string }>(`/evangelism/events/strategy/${id}/ensure`, {
    method: 'POST', token, silent: true,
   });
   router.push(`/plataforma/evangelism/events?event_id=${encodeURIComponent(event.id)}`);
  } catch (error: unknown) {
   toast.error('No se pudo preparar el evento: ' + getErrorMessage(error, 'Intente de nuevo'));
  }
 };

 const openGroupAttendance = async (g: StrategyGroup) => {
  let sessionList = sessions;
  if (sessionList.length === 0) {
   try {
 sessionList = (await apiFetch<SessionRow[]>(`/evangelism/sessions?strategy_id=${id}`, { token, silent: true })) || [];
    setSessions(sessionList);
   } catch {
    return;
   }
  }
  const grpSessions = sessionList
   .filter(s => s.grupo_id === g.id)
   .sort((a, b) => b.session_date.localeCompare(a.session_date));
  const target = grpSessions.find(s => s.estado_habilitacion === 'HABILITADO');
  if (!target) {
   toast.error(grpSessions.length === 0 ? 'Este grupo no tiene sesiones registradas' : 'Habilita una sesión antes de registrar asistencia');
   return;
  }
  openAttendanceDrawer(target);
 };

 const openAttendanceDrawer = async (session: SessionRow) => {
 if (session.estado_habilitacion !== 'HABILITADO') {
  toast.error('Habilita la sesión antes de registrar asistencia');
  return;
 }
 setAttendanceSession(session);
 setIsAttendanceDrawerOpen(true);
 try {
 // Get house personas to build attendance list
 const house = await apiFetch<GroupDetailResponse>(`/evangelism/grupos/${session.grupo_id}`, { token, silent: true });
 const existing = await apiFetch<SessionDetailResponse>(`/evangelism/sessions/${session.id}`, { token, silent: true }).catch(() => null);
 const existingMap: Record<string, { status: string; notes: string }> = {};
 if (existing?.attendance) {
 for (const a of existing.attendance) {
 existingMap[a.persona_id] = { status: a.status, notes: a.notes || '' };
 }
 }
 const personaList = house?.base_attendees?.map((a) => ({
 persona_id: a.persona_id,
 name: a.name || a.persona?.nombre_completo || '',
 role: a.role || 'persona',
 role_label: a.role_label,
 status: toAttendanceStatus(existingMap[a.persona_id]?.status),
 notes: existingMap[a.persona_id]?.notes || '',
 })) || [];
 setAttendancePersonas(personaList);
 } catch { setAttendancePersonas([]); }
 };

 const handleSaveAttendance = async () => {
 if (!attendanceSession) return;
 if (attendanceSession.estado_habilitacion !== 'HABILITADO') {
 toast.error('Habilita la sesión antes de registrar asistencia');
 return;
 }
 setAttendanceSaving(true);
 try {
 const res = await apiFetch<AttendanceSaveResult>(`/evangelism/sessions/${attendanceSession.id}/attendance`, {
 method: 'POST', token,
 body: attendancePersonas.map(m => ({
 session_id: attendanceSession.id,
 persona_id: m.persona_id,
 status: m.status,
 notes: m.notes || null,
 })),
 });
 toast.success('Asistencia registrada');
 if (res?.evento_integracion) {
 const integrationLabel = res.evento_integracion.crm_consolidacion?.caso_id
 ? ` caso ${res.evento_integracion.crm_consolidacion.caso_id}`
 : '';
 toast.info(`Integración CRM activada${integrationLabel}`.trim());
 }
 setIsAttendanceDrawerOpen(false);
 fetchSessions();
 } catch (error: unknown) {
 toast.error('Error: ' + getErrorMessage(error, 'Intente de nuevo'));
 } finally { setAttendanceSaving(false); }
 };

 const requestDeleteSession = (sessionId: string) => {
 setConfirmAction({
 title: 'Eliminar sesión',
 description: 'Se eliminará esta sesión y su asistencia registrada.',
 confirmLabel: 'Eliminar',
 destructive: true,
 onConfirm: async () => {
 await deleteSession(sessionId);
 setSessionMenuId(null);
 },
 });
 };

 const requestDeleteStrategy = () => {
 if (!strategy) return;
 setConfirmAction({
 title: 'Eliminar estrategia',
 description: `Se eliminará "${strategy.name}" con sus grupos, sesiones y registros de asistencia.`,
 confirmLabel: 'Eliminar',
 destructive: true,
 onConfirm: handleDelete,
 });
 };

 const requestBlockAllSessions = () => {
 setConfirmAction({
 title: 'Bloquear sesiones',
 description: 'Se bloquearán todas las sesiones para reporte.',
 confirmLabel: 'Bloquear',
 destructive: true,
 onConfirm: async () => {
 try {
 const res = await apiFetch<BulkHabilitacionResponse>(`/evangelism/strategies/${id}/deshabilitar-todas`, { method: 'POST', token, silent: true });
 toast.success(`${res.sesiones_deshabilitadas} sesiones bloqueadas`);
 fetchSessions();
 } catch { toast.error('Error al deshabilitar sesiones'); }
 },
 });
 };

 const handleCreateRole = async () => {
 if (!newRoleName.trim()) return;
 try {
 await apiFetch(`/evangelism/strategies/${id}/roles`, {
 method: 'POST', token, silent: true,
 body: { estrategia_id: id, nombre_rol: newRoleName.trim(), descripcion: newRoleDesc || null },
 });
 toast.success('Rol creado');
 setNewRoleName(''); setNewRoleDesc(''); setShowRoleForm(false);
 fetchCustomRoles();
 } catch { toast.error('Error al crear rol'); }
 };

 const requestDeleteRole = (role: CustomRole) => {
 setConfirmAction({
 title: 'Eliminar rol',
 description: `Se eliminará el rol "${role.nombre_rol}".`,
 confirmLabel: 'Eliminar',
 destructive: true,
 onConfirm: async () => {
 try {
 await apiFetch(`/evangelism/strategies/${id}/roles/${role.id}`, { method: 'DELETE', token, silent: true });
 toast.success('Rol eliminado');
 fetchCustomRoles();
 fetchStrategy();
 } catch { toast.error('Error al eliminar rol'); }
 },
 });
 };

 const formatDate = (dateStr: string | null | undefined) => {
 if (!dateStr) return 'Sin fecha';
 try { return new Date(dateStr).toLocaleDateString('es-ES', { day: 'numeric', month: 'short', year: 'numeric' }); }
 catch { return dateStr; }
 };

 const groupName = (grupoId: string) => groups.find(g => g.id === grupoId)?.name || `Grupo #${grupoId}`;

 const shareGroupLink = (groupId: string, gName: string, via: 'copy' | 'whatsapp' | 'telegram') => {
 const url = `${window.location.origin}/plataforma/evangelism/groups/${groupId}`;
 const msg = `Hola, este es el enlace directo a tu grupo "${gName}" en la plataforma CCF:`;
 if (via === 'copy') {
 navigator.clipboard.writeText(url).then(() => toast.success('Enlace copiado al portapapeles'));
 } else if (via === 'whatsapp') {
 window.open(`https://wa.me/?text=${encodeURIComponent(msg + '\n' + url)}`, '_blank');
 } else {
 window.open(`https://t.me/share/url?url=${encodeURIComponent(url)}&text=${encodeURIComponent(msg)}`, '_blank');
 }
 setShareMenuId(null);
 };

 // Meses disponibles para el filtro de sesiones
 const sessionMonths = useMemo(() => {
 const seen = new Set<string>();
 sessions.forEach(s => seen.add(s.session_date.substring(0, 7)));
 return Array.from(seen).sort();
 }, [sessions]);

 // Sesiones para tab Asistencia — centrado en grupos
 const attendanceByGroup = useMemo(() => {
  // Para cada grupo, tomar su sesión más reciente
  const byGroup: Record<string, SessionRow[]> = {};
  sessions.forEach(s => {
   if (!byGroup[s.grupo_id]) byGroup[s.grupo_id] = [];
   byGroup[s.grupo_id].push(s);
  });
  // Ordenar sesiones de cada grupo por fecha desc
  Object.values(byGroup).forEach(arr => arr.sort((a, b) => b.session_date.localeCompare(a.session_date)));
  // Construir lista de grupos con su sesión más reciente primero
  return groups.map(g => ({
   group: g,
   sessions: (byGroup[g.id] || []).slice(0, 5), // hasta 5 sesiones recientes por grupo
   latest: (byGroup[g.id] || [])[0] ?? null,
  })).filter(entry => entry.sessions.length > 0);
 }, [sessions, groups]);

 // Sesiones filtradas para la vista de lista
 const filteredSessions = useMemo(() => {
 const q = sessionSearch.trim().toLowerCase();
 return sessions.filter(s => {
 if (sessionGroupFilter !== 'all' && s.grupo_id !== sessionGroupFilter) return false;
 if (sessionHabFilter !== 'all' && s.estado_habilitacion !== sessionHabFilter) return false;
 if (sessionMonthFilter !== 'all' && !s.session_date.startsWith(sessionMonthFilter)) return false;
 if (q) {
 const haystack = [
 s.topic || '',
 groupName(s.grupo_id),
 s.session_date.substring(0, 7),
 ].join(' ').toLowerCase();
 if (!haystack.includes(q)) return false;
 }
 return true;
 });
 // eslint-disable-next-line react-hooks/exhaustive-deps
 }, [sessions, sessionGroupFilter, sessionHabFilter, sessionMonthFilter, sessionSearch]);

  return {
    id,
    token,
    authLoading,
    canReadStrategySurface,
    canManageStrategySurface,
    strategy,
    loading,
    loadError,
    saving,
    editName, setEditName,
    editDesc, setEditDesc,
    editType, setEditType,
    editStatus, setEditStatus,
    editActiva, setEditActiva,
    editClaseRaiz, setEditClaseRaiz,
    editDefaultRoleId, setEditDefaultRoleId,
    editStartDate, setEditStartDate,
    editEndDate, setEditEndDate,
    editRecurrence, setEditRecurrence,
    handleSave,
    fetchStrategy,
    customRoles,
    loadingRoles,
    showRoleForm, setShowRoleForm,
    newRoleName, setNewRoleName,
    newRoleDesc, setNewRoleDesc,
    followUps,
    loadingFollowUps,
    fetchFollowUps,
    confirmAction, setConfirmAction,
    activeTab, setActiveTab,
    viewType, setViewType,
    groups, groupsLoading, fetchGroups,
    metrics,
    personaCache, setPersonaCache,
    roleResults, roleLoading,
    roleSearch, setRoleSearch,
    roleDropdown, setRoleDropdown,
    isGroupDrawerOpen, setIsGroupDrawerOpen,
    groupForm, setGroupForm,
    groupRoleAssignments, setGroupRoleAssignments,
    groupSaving,
    isPersonaDrawerOpen, setIsPersonaDrawerOpen,
    selectedGroup,
    groupPersonas,
    personaSearch, setPersonaSearch,
    personaSearchLoading,
    personaSearchResults,
    personaSaving,
    personaSplitHeight,
    personaSplitRef,
    handlePersonaSplitDrag,
    sessions, sessionsLoading, fetchSessions,
    toggleSessionHabilitacion,
    isNewSessionDrawerOpen, setIsNewSessionDrawerOpen,
    sessionForm, setSessionForm,
    sessionSaving,
    attendanceSession,
    attendancePersonas, setAttendancePersonas,
    attendanceSaving,
    isAttendanceDrawerOpen, setIsAttendanceDrawerOpen,
    sessionMenuId, setSessionMenuId,
    shareMenuId, setShareMenuId,
    sessionGroupFilter, setSessionGroupFilter,
    sessionHabFilter, setSessionHabFilter,
    sessionMonthFilter, setSessionMonthFilter,
    sessionSearch, setSessionSearch,
    tableSubTab, setTableSubTab,
    personaRoleOptions,
    strategyGroupCount,
    getRoleLabel,
    getRoleColor,
    handleCreateGroup,
    openGroupDrawer,
    requestDeleteGroup,
    openPersonaDrawer,
    handleSavePersonas,
    addPersonaToGroup,
    updateGroupPersonaRole,
    removePersonaFromGroup,
    handleCreateSession,
    openMassAttendance,
    openGroupAttendance,
    openAttendanceDrawer,
    handleSaveAttendance,
    requestDeleteSession,
    requestDeleteStrategy,
    requestBlockAllSessions,
    handleCreateRole,
    requestDeleteRole,
    formatDate,
    groupName,
    shareGroupLink,
    sessionMonths,
    attendanceByGroup,
    filteredSessions,
  };
}
