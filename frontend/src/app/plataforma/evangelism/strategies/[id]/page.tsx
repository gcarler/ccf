"use client";

import EvangelismShell from '@/components/evangelism/EvangelismShell';
import type {
 BulkHabilitacionResponse,
 GenerateSessionsResponse,
 GroupDetailResponse,
 SessionDetailResponse,
 StrategyMetrics,
} from '../../types';
import ConfirmActionDrawer, { type ConfirmActionState } from '@/components/evangelism/ConfirmActionDrawer';
import UniversalCalendarView from '@/components/ui/UniversalCalendarView';
import UniversalGanttView from '@/components/ui/UniversalGanttView';
import UniversalTableView from '@/components/ui/UniversalTableView';
import UniversalWikiView from '@/components/ui/UniversalWikiView';
import ViewSwitcher from '@/components/ViewSwitcher';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';
import { useAuth } from '@/context/AuthContext';
import { FULL_VIEWS,useViewType } from '@/hooks/useViewType';
import { apiFetch } from '@/lib/http';
import { motion } from 'framer-motion';
import {
AlertCircle,
ArrowLeft,
BarChart3,
Calendar,
CheckCircle2,
ClipboardList,
Clock,
Copy,
Flame,
FolderOpen,
Home,
Loader2,
Plus,
Save,
Search,
Share2,
Sparkles,
Trash2,
UserCheck,
UserMinus,
UserPlus,
Users,
X
} from 'lucide-react';
import { ChevronDown } from 'lucide-react';
import { useParams,useRouter } from 'next/navigation';
import { useCallback,useEffect,useMemo,useRef,useState } from 'react';
import { toast } from 'sonner';

interface Strategy {
 id: string;
 name: string;
 description: string;
 codigo?: string;
 clase_raiz?: string;
 activa: boolean;
 default_role_id?: number | null;
 typology: string;
 recurrence: string | null;
 day_of_week: string | null;
 start_time: string | null;
 event_format: string | null;
 niche_objective: string | null;
 status: 'active' | 'pending' | 'done';
 strategy_type: string;
 start_date?: string | null;
 end_date?: string | null;
 created_at: string;
 updated_at: string;
 group_count?: number;
}

interface CustomRole {
 id: number;
 estrategia_id: string;
 nombre_rol: string;
 descripcion?: string;
}

interface FollowUpRecord {
 id: string;
 asistencia_id: string;
 tipo: string;
 fecha_seguimiento?: string;
 observaciones?: string;
 estado_completado: boolean;
 responsable_id?: string;
}

interface StrategyGroup {
 id: string;
 name: string;
 zone: string | null;
 leader_name: string | null;
 personas_count: number;
}

type HabilitacionEstado = 'DESHABILITADO' | 'HABILITADO' | 'CERRADO' | 'CANCELADA';

interface SessionRow {
 id: number;
 grupo_id: string;
 session_date: string;
 status: string;
 estado_habilitacion?: HabilitacionEstado;
 topic?: string | null;
 offering_amount?: number | null;
 report_notes?: string | null;
}

interface AttendancePersona {
 persona_id: string;
 name: string;
 role: string;
 role_label?: string;
 status: 'present' | 'absent' | 'first_time';
 notes?: string;
}

type TabId = 'overview' | 'groups' | 'sessions' | 'attendance' | 'metrics';

const STATUS_COLORS = {
 pending: '#F59E0B',
 active: '#2563EB',
 done: '#10B981',
};

const STATUS_LABELS = {
 pending: 'No iniciada',
 active: 'Iniciada',
 done: 'Terminada',
};

const TYPOLOGY_COLORS: Record<string, string> = {
 relacional: '#3B82F6',
 evento_masivo: '#F97316',
 sectorial: '#8B5CF6',
 reunion: '#10B981',
 cells: '#6366F1',
};

const TYPOLOGY_LABELS: Record<string, string> = {
 relacional: 'Relacional',
 evento_masivo: 'Evento Masivo',
 sectorial: 'Sectorial',
 reunion: 'Reunión',
 cells: 'Células',
};

const FALLBACK_MEMBER_ROLES = [
 { value: 'persona', label: 'Persona' },
 { value: 'visitante', label: 'Visitante' },
];

const ROLE_COLORS: Record<string, string> = {
 lider: 'bg-blue-100 text-[hsl(var(--primary))] dark:bg-blue-900/30 dark:text-blue-300',
 colider: 'bg-blue-100 text-[hsl(var(--primary))] dark:bg-blue-900/30 dark:text-blue-300',
 persona: 'bg-[hsl(var(--bg-muted))] text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]',
 visitante: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
 asistente: 'bg-[hsl(var(--bg-muted))] text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]',
 personalizado: 'bg-blue-100 text-[hsl(var(--primary))] dark:bg-blue-900/30 dark:text-blue-300',
};

const normalizeRoleText = (value: string) =>
 value
 .normalize('NFD')
 .replace(/[\u0300-\u036f]/g, '')
 .toLowerCase()
 .replace(/[^a-z0-9]+/g, '-')
 .replace(/^-+|-+$/g, '');

const customRoleValue = (role: CustomRole) => `custom:${role.id}`;

const roleMatches = (role: CustomRole, keywords: string[]) => {
 const tokens = normalizeRoleText(role.nombre_rol).split('-');
 return keywords.some(keyword => tokens.includes(keyword));
};

const isPrimaryLeaderRole = (role: CustomRole) => {
 const tokens = normalizeRoleText(role.nombre_rol).split('-');
 return tokens.includes('lider') && !tokens.includes('co') && !tokens.includes('colider') && !tokens.includes('asistente');
};

const isAssistantLeaderRole = (role: CustomRole) => {
 const tokens = normalizeRoleText(role.nombre_rol).split('-');
 return tokens.includes('asistente') || tokens.includes('colider') || (tokens.includes('co') && tokens.includes('lider'));
};

const TABS: { id: TabId; label: string; icon: typeof Users }[] = [
 { id: 'overview', label: 'General', icon: Sparkles },
 { id: 'groups', label: 'Grupos', icon: FolderOpen },
 { id: 'sessions', label: 'Sesiones', icon: Calendar },
 { id: 'attendance', label: 'Asistencia', icon: ClipboardList },
 { id: 'metrics', label: 'Métricas', icon: BarChart3 },
];

function RoleSelect({ value, options, colorClass, onChange }: {
 value: string;
 options: { value: string; label: string }[];
 colorClass: string;
 onChange: (v: string) => void;
}) {
 const [open, setOpen] = useState(false);
 const ref = useRef<HTMLDivElement>(null);
 const current = options.find(o => o.value === value);

 useEffect(() => {
 if (!open) return;
 const handler = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false); };
 document.addEventListener('mousedown', handler);
 return () => document.removeEventListener('mousedown', handler);
 }, [open]);

 return (
 <div ref={ref} className="relative">
 <button
 type="button"
 onClick={() => setOpen(o => !o)}
 className={`flex items-center gap-1 text-[11px] font-semibold px-2 py-1 rounded cursor-pointer ${colorClass}`}
 >
 {current?.label ?? value}
 <ChevronDown size={10} className={`transition-transform ${open ? 'rotate-180' : ''}`} />
 </button>
 {open && (
 <div className="absolute right-0 top-full mt-1 z-50 min-w-[140px] bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border-primary))] rounded-lg shadow-lg py-1 overflow-hidden">
 {options.map(opt => (
 <button
 key={opt.value}
 type="button"
 onClick={() => { onChange(opt.value); setOpen(false); }}
 className={`w-full text-left px-3 py-1.5 text-[11px] font-semibold hover:bg-[hsl(var(--bg-muted))] transition-colors ${value === opt.value ? 'opacity-60' : ''}`}
 >
 {opt.label}
 </button>
 ))}
 </div>
 )}
 </div>
 );
}

export default function StrategyDetailPage() {
 const params = useParams();
 const router = useRouter();
 const id = (params?.id as string) || '';
 const { token } = useAuth();
 const [strategy, setStrategy] = useState<Strategy | null>(null);
 const [loading, setLoading] = useState(true);
 const [saving, setSaving] = useState(false);
 const [editName, setEditName] = useState('');
 const [editDesc, setEditDesc] = useState('');
 const [editType, setEditType] = useState('');
 const [editStatus, setEditStatus] = useState<'active' | 'pending' | 'done'>('pending');
 const [editActiva, setEditActiva] = useState(true);
 const [editClaseRaiz, setEditClaseRaiz] = useState('');
 const [editDefaultRoleId, setEditDefaultRoleId] = useState<number | null | undefined>(undefined);
 const [editStartDate, setEditStartDate] = useState('');
 const [editEndDate, setEditEndDate] = useState('');
 const [editRecurrence, setEditRecurrence] = useState<string | null>(null);

 // Roles personalizados
 const [customRoles, setCustomRoles] = useState<CustomRole[]>([]);
 const [loadingRoles, setLoadingRoles] = useState(false);
 const [showRoleForm, setShowRoleForm] = useState(false);
 const [newRoleName, setNewRoleName] = useState('');
 const [newRoleDesc, setNewRoleDesc] = useState('');

 // Seguimiento
 const [followUps, setFollowUps] = useState<FollowUpRecord[]>([]);
 const [loadingFollowUps, setLoadingFollowUps] = useState(false);
 const [confirmAction, setConfirmAction] = useState<ConfirmActionState>(null);
 const [activeTab, setActiveTab] = useState<TabId>('overview');
 const { viewType, setViewType } = useViewType(`strategy_${id}`, 'dashboard');
 const [groups, setGroups] = useState<StrategyGroup[]>([]);
 const [metrics, setMetrics] = useState<any>(null);
 const [personaCache, setPersonaCache] = useState<Record<string, any>>({});
 const [roleResults, setRoleResults] = useState<Record<string, any[]>>({});
 const [roleLoading, setRoleLoading] = useState<Record<string, boolean>>({});

 // Group creation drawer
 const [isGroupDrawerOpen, setIsGroupDrawerOpen] = useState(false);
 const [groupForm, setGroupForm] = useState({
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
 const [allPersonas, setAllPersonas] = useState<any[]>([]);
 const [personaSearch, setPersonaSearch] = useState('');
 const [personaSearchLoading, setPersonaSearchLoading] = useState(false);
 const [personaSaving, setPersonaSaving] = useState(false);
 const [personaSplitHeight, setPersonaSplitHeight] = useState(200);
 const personaSplitRef = useRef<HTMLDivElement>(null);

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

 // Groups + Sessions loading
 const [groupsLoading, setGroupsLoading] = useState(false);
 // Sessions
 const [sessions, setSessions] = useState<SessionRow[]>([]);
 const [sessionsLoading, setSessionsLoading] = useState(false);
 const [isNewSessionDrawerOpen, setIsNewSessionDrawerOpen] = useState(false);
 const [sessionForm, setSessionForm] = useState({
 grupo_id: '' as string | number,
 session_date: new Date().toISOString().split('T')[0],
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
 const [sessionMenuId, setSessionMenuId] = useState<number | null>(null);
 const [shareMenuId, setShareMenuId] = useState<string | null>(null);
 const [sessionGroupFilter, setSessionGroupFilter] = useState<string | 'all'>('all');
 const [sessionHabFilter, setSessionHabFilter] = useState<'all' | 'HABILITADO' | 'DESHABILITADO' | 'CERRADO'>('all');
 const [sessionMonthFilter, setSessionMonthFilter] = useState<string>('all');
 const [sessionSearch, setSessionSearch] = useState('');
 const [tableSubTab, setTableSubTab] = useState<'groups' | 'sessions'>('groups');

 // Visitor search / new visitor form (in attendance drawer)
 const [showVisitorSearch, setShowVisitorSearch] = useState(false);
 const [visitorSearch, setVisitorSearch] = useState('');
 const [showNewVisitorForm, setShowNewVisitorForm] = useState(false);
 const [newVisitorForm, setNewVisitorForm] = useState({ first_name: '', last_name: '', phone: '', whatsapp: '', email: '', address: '' });
 const [savingNewVisitor, setSavingNewVisitor] = useState(false);
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

 const getRoleLabel = (value: string, fallback?: string) => {
 const customId = value?.startsWith('custom:') ? Number(value.split(':')[1]) : null;
 if (customId) {
 return customRoles.find(role => role.id === customId)?.nombre_rol || fallback || value;
 }
 return personaRoleOptions.find(role => role.value === value)?.label || fallback || value;
 };

 const getRoleColor = (value: string) => {
 if (value?.startsWith('custom:')) return ROLE_COLORS.personalizado;
 return ROLE_COLORS[value] || ROLE_COLORS.persona;
 };

 const buildRoleDrivenGroupAssignments = () => {
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

 const fetchStrategy = useCallback(async () => {
 setLoading(true);
 try {
 const result = await apiFetch<Strategy>(`/evangelism/strategies/${id}`, { token });
 setStrategy(result);
 setEditName(result.name);
 setEditDesc(result.description || '');
 setEditType(result.strategy_type || '');
 setEditStatus(result.status || 'pending');
 setEditActiva(result.activa !== undefined ? result.activa : true);
 setEditClaseRaiz(result.clase_raiz || result.typology || '');
 setEditDefaultRoleId(result.default_role_id ?? null);
 setEditStartDate(result.start_date ? result.start_date.substring(0, 10) : '');
 setEditEndDate(result.end_date ? result.end_date.substring(0, 10) : '');
 setEditRecurrence(result.recurrence || null);
 } catch (e: any) {
 toast.error('Error al cargar la estrategia');
 } finally {
 setLoading(false);
 }
 }, [id, token]);

 const fetchCustomRoles = useCallback(async () => {
 setLoadingRoles(true);
 try {
 const result = await apiFetch<CustomRole[]>(`/evangelism/strategies/${id}/roles`, { token });
 setCustomRoles(result || []);
 } catch {
 // Roles endpoint may not exist for old strategies without codigo
 setCustomRoles([]);
 } finally {
 setLoadingRoles(false);
 }
 }, [id, token]);

 const fetchFollowUps = useCallback(async () => {
 setLoadingFollowUps(true);
 try {
 const result = await apiFetch<FollowUpRecord[]>('/evangelism/follow-up/pending', { token });
 setFollowUps(result || []);
 } catch {
 setFollowUps([]);
 } finally {
 setLoadingFollowUps(false);
 }
 }, [token]);

 useEffect(() => {
 fetchStrategy();
 fetchCustomRoles();
 fetchFollowUps();
 }, [fetchStrategy, fetchCustomRoles, fetchFollowUps]);

 const fetchGroups = useCallback(async () => {
 setGroupsLoading(true);
 try {
 const all = await apiFetch<StrategyGroup[]>('/evangelism/grupos', { token, query: { evangelism_strategy_id: id } });
 setGroups(all || []);
 } catch { toast.error('Error al cargar grupos'); } finally {
 setGroupsLoading(false);
 }
 }, [id, token]);

 // Cargar grupos al montar para que aparezcan en el sidebar
 useEffect(() => {
 if (token) fetchGroups();
 }, [fetchGroups, token]);

 const fetchMetrics = useCallback(async () => {
 try {
 const m = await apiFetch<StrategyMetrics>(`/evangelism/strategies/${id}/metrics`, { token });
 setMetrics(m);
 } catch { toast.error('Error al cargar métricas'); }
 }, [id, token]);

 const fetchSessions = useCallback(async () => {
 setSessionsLoading(true);
 try {
 const data = await apiFetch<SessionRow[]>(`/evangelism/sessions?strategy_id=${id}`, { token });
 setSessions(data || []);
 } catch { toast.error('Error al cargar sesiones'); } finally {
 setSessionsLoading(false);
 }
 }, [id, token]);

 useEffect(() => {
 if (activeTab === 'groups') fetchGroups();
 if (activeTab === 'metrics') fetchMetrics();
 if (activeTab === 'sessions') { fetchGroups(); fetchSessions(); }
 if (activeTab === 'attendance') { fetchGroups(); fetchSessions(); }
 }, [activeTab, fetchGroups, fetchMetrics, fetchSessions]);

 useEffect(() => {
 if (!roleDropdown) return;
 const field = roleDropdown;
 const query = (roleSearch[field] || '').trim();
 setRoleLoading(l => ({ ...l, [field]: true }));
 const timer = setTimeout(async () => {
 try {
 const params: Record<string, any> = query.length >= 1
 ? { limit: 200, search: query }
 : { limit: 1000, sort_by: 'first_name', sort_dir: 'asc' };
 const res = await apiFetch<any[]>('/crm/personas', { token, query: params });
 setRoleResults(r => ({ ...r, [field]: res || [] }));
 } catch {
 setRoleResults(r => ({ ...r, [field]: [] }));
 } finally {
 setRoleLoading(l => ({ ...l, [field]: false }));
 }
 }, query.length >= 1 ? 300 : 0);
 return () => clearTimeout(timer);
 }, [roleSearch, roleDropdown, token]);

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
 } catch (e: any) {
 toast.error('Error al crear: ' + (e.message || 'Intente de nuevo'));
 } finally { setGroupSaving(false); }
 };

 const handleDeleteGroup = async (groupId: string) => {
 try {
 await apiFetch(`/evangelism/grupos/${groupId}`, { method: 'DELETE', token });
 toast.success('Grupo eliminado');
 fetchGroups(); fetchStrategy();
 } catch { toast.error('Error al eliminar'); }
 };

 const requestDeleteGroup = (groupId: string, groupName: string) => {
 setConfirmAction({
 title: 'Eliminar grupo',
 description: `Se eliminara "${groupName}" y todo su historial de asistencia.`,
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
 setAllPersonas([]);
 setPersonaSplitHeight(200);
 try {
 const house = await apiFetch<GroupDetailResponse>(`/evangelism/grupos/${group.id}`, { token });
 setGroupPersonas(house?.base_attendees?.map((a: any) => ({
 id: a.persona_id,
 name: a.name || a.persona?.nombre_completo || '',
 email: a.persona?.email || '',
 role: a.role || 'persona',
 role_label: a.role_label,
 })) || []);
 } catch { setGroupPersonas([]); }
 };

 // Carga todas las personas al abrir el drawer — el filtro es client-side por nombre
 useEffect(() => {
 if (!isPersonaDrawerOpen) return;
 setPersonaSearchLoading(true);
 apiFetch<any[]>('/crm/personas', { token, query: { limit: 1000, sort_by: 'first_name', sort_dir: 'asc' } })
 .then(res => setAllPersonas(res || []))
 .catch(() => {})
 .finally(() => setPersonaSearchLoading(false));
 }, [isPersonaDrawerOpen, token]); // eslint-disable-line react-hooks/exhaustive-deps

 const handleSavePersonas = async () => {
 if (!selectedGroup) return;
 setPersonaSaving(true);
 try {
 await apiFetch(`/evangelism/grupos/${selectedGroup.id}`, {
 method: 'PUT', token,
 body: {
 base_attendees_with_roles: groupPersonas.map(m => ({
 persona_id: m.id,
 role: m.role,
 rol_personalizado_id: m.role.startsWith('custom:') ? Number(m.role.split(':')[1]) : null,
 })),
 },
 });
 toast.success('Personas actualizados');
 setIsPersonaDrawerOpen(false);
 fetchGroups();
 } catch (e: any) {
 toast.error('Error al guardar: ' + (e.message || 'Intente de nuevo'));
 } finally { setPersonaSaving(false); }
 };

 const addPersonaToGroup = (persona: any) => {
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
 method: 'POST', token,
 body: {
 grupo_id: sessionForm.grupo_id,
 session_date: sessionForm.session_date + 'T12:00:00',
 topic: sessionForm.topic || null,
 offering_amount: sessionForm.offering_amount ? parseFloat(sessionForm.offering_amount) : null,
 report_notes: sessionForm.report_notes || null,
 status: 'Realizada',
 },
 });
 toast.success('Sesión registrada');
 setIsNewSessionDrawerOpen(false);
 setSessionForm({ grupo_id: '', session_date: new Date().toISOString().split('T')[0], topic: '', offering_amount: '', report_notes: '' });
 fetchSessions();
 } catch (e: any) {
 toast.error('Error al guardar: ' + (e.message || 'Intente de nuevo'));
 } finally { setSessionSaving(false); }
 };

 const openGroupAttendance = async (g: StrategyGroup) => {
  let sessionList = sessions;
  if (sessionList.length === 0) {
   try {
    sessionList = (await apiFetch<SessionRow[]>(`/evangelism/sessions?strategy_id=${id}`, { token })) || [];
    setSessions(sessionList);
   } catch { toast.error('Error al cargar sesiones'); return; }
  }
  const grpSessions = sessionList
   .filter(s => s.grupo_id === g.id)
   .sort((a, b) => b.session_date.localeCompare(a.session_date));
  const target = grpSessions.find(s => s.estado_habilitacion === 'HABILITADO') ?? grpSessions[0];
  if (!target) { toast.error('Este grupo no tiene sesiones registradas'); return; }
  openAttendanceDrawer(target);
 };

 const openAttendanceDrawer = async (session: SessionRow) => {
 setAttendanceSession(session);
 setIsAttendanceDrawerOpen(true);
 setShowVisitorSearch(false);
 setVisitorSearch('');
 setShowNewVisitorForm(false);
 setNewVisitorForm({ first_name: '', last_name: '', phone: '', whatsapp: '', email: '', address: '' });
 // Pre-load all personas for visitor search if not already loaded
 if (allPersonas.length === 0) {
 apiFetch<any[]>('/crm/personas', { token, query: { limit: 1000, sort_by: 'first_name', sort_dir: 'asc' } }).then(res => {
 if (Array.isArray(res)) setAllPersonas(res);
 }).catch(() => { toast.error('Error al cargar personas'); });
 }
 try {
 // Get house personas to build attendance list
 const house = await apiFetch<GroupDetailResponse>(`/evangelism/grupos/${session.grupo_id}`, { token });
 const existing = await apiFetch<SessionDetailResponse>(`/evangelism/sessions/${session.id}`, { token }).catch(() => null);
 const existingMap: Record<string, { status: string; notes: string }> = {};
 if (existing?.attendance) {
 for (const a of existing.attendance) {
 existingMap[a.persona_id] = { status: a.status, notes: a.notes || '' };
 }
 }
 const personaList = house?.base_attendees?.map((a: any) => ({
 persona_id: a.persona_id,
 name: a.name || a.persona?.nombre_completo || '',
 role: a.role || 'persona',
 role_label: a.role_label,
 status: (existingMap[a.persona_id]?.status as any) || 'present',
 notes: existingMap[a.persona_id]?.notes || '',
 })) || [];
 setAttendancePersonas(personaList);
 } catch { setAttendancePersonas([]); }
 };

 const handleSaveAttendance = async () => {
 if (!attendanceSession) return;
 setAttendanceSaving(true);
 try {
 await apiFetch(`/evangelism/sessions/${attendanceSession.id}/attendance`, {
 method: 'POST', token,
 body: attendancePersonas.map(m => ({
 session_id: attendanceSession.id,
 persona_id: m.persona_id,
 status: m.status,
 notes: m.notes || null,
 })),
 });
 toast.success('Asistencia guardada');
 setIsAttendanceDrawerOpen(false);
 fetchSessions();
 } catch (e: any) {
 toast.error('Error: ' + (e.message || 'Intente de nuevo'));
 } finally { setAttendanceSaving(false); }
 };

 const handleCreateNewVisitor = async () => {
 if (!attendanceSession) return;
 setSavingNewVisitor(true);
 try {
 const res = await apiFetch<{ status: string; persona_id: string; first_name?: string | null; last_name?: string | null }>('/evangelism/faro/visitors', {
 method: 'POST', token,
 body: {
 first_name: newVisitorForm.first_name || null,
 last_name: newVisitorForm.last_name || null,
 phone: newVisitorForm.phone || null,
 whatsapp: newVisitorForm.whatsapp || null,
 email: newVisitorForm.email || null,
 address: newVisitorForm.address || null,
 grupo_id: attendanceSession.grupo_id,
 session_id: attendanceSession.id,
 },
 });
 const realName = [res.first_name, res.last_name].filter(Boolean).join(' ') || 'Visitante';
 if (res.status === 'duplicate') {
 toast.info(`Ya existe una persona con ese teléfono: ${realName}`);
 } else {
 toast.success(`Visitante "${realName}" registrado`);
 }
 setAttendancePersonas(prev => {
 const nextPersona = {
 persona_id: res.persona_id,
 name: realName,
 role: 'visitante',
 role_label: 'Visitante',
 status: 'first_time' as const,
 notes: '',
 };
 if (prev.some(persona => persona.persona_id === res.persona_id)) {
 return prev.map(persona => persona.persona_id === res.persona_id ? { ...persona, ...nextPersona } : persona);
 }
 return [...prev, nextPersona];
 });
 setAllPersonas(prev => {
 if (prev.some(persona => persona.id === res.persona_id)) return prev;
 return [
 ...prev,
 {
 id: res.persona_id,
 first_name: res.first_name || '',
 last_name: res.last_name || '',
 nombre_completo: realName,
 church_role: 'Visitante',
 },
 ];
 });
 setNewVisitorForm({ first_name: '', last_name: '', phone: '', whatsapp: '', email: '', address: '' });
 setShowNewVisitorForm(false);
 fetchGroups();
 fetchStrategy();
 } catch (e: any) {
 toast.error('Error al registrar visitante: ' + (e.message || 'Intente de nuevo'));
 } finally { setSavingNewVisitor(false); }
 };

 const handleDeleteSession = async (sessionId: number) => {
 try {
 await apiFetch(`/evangelism/sessions/${sessionId}`, { method: 'DELETE', token });
 toast.success('Sesión eliminada');
 fetchSessions();
 } catch (e: any) {
 toast.error('Error: ' + (e.message || 'Intente de nuevo'));
 }
 setSessionMenuId(null);
 };

 const requestDeleteSession = (sessionId: number) => {
 setConfirmAction({
 title: 'Eliminar sesion',
 description: 'Se eliminara esta sesion y su asistencia registrada.',
 confirmLabel: 'Eliminar',
 destructive: true,
 onConfirm: () => handleDeleteSession(sessionId),
 });
 };

 const handleSave = async () => {
 if (!strategy) return;
 setSaving(true);
 try {
 await apiFetch(`/evangelism/strategies/${id}`, {
 method: 'PUT', token,
 body: {
 name: editName, description: editDesc, strategy_type: editType,
 status: editStatus,
 activa: editActiva,
 clase_raiz: editClaseRaiz || null,
 default_role_id: editDefaultRoleId ?? null,
 recurrence: editRecurrence,
 start_date: editStartDate ? new Date(editStartDate).toISOString() : null,
 end_date: editEndDate ? new Date(editEndDate).toISOString() : null,
 },
 });
 toast.success('Estrategia actualizada');
 window.dispatchEvent(new CustomEvent('evangelism-strategy-created'));
 fetchStrategy();
 fetchCustomRoles();
 } catch (e: any) {
 toast.error('Error al guardar: ' + (e?.message || 'Error desconocido'));
 }
 finally { setSaving(false); }
 };

 const handleDelete = async () => {
 if (!strategy) return;
 try {
 await apiFetch(`/evangelism/strategies/${id}`, { method: 'DELETE', token });
 toast.success('Estrategia eliminada');
 window.dispatchEvent(new CustomEvent('evangelism-strategy-created'));
 router.push('/plataforma/evangelism');
 } catch (e: any) {
 toast.error('Error al eliminar: ' + (e?.message || 'Intente de nuevo'));
 }
 };

 const requestDeleteStrategy = () => {
 if (!strategy) return;
 setConfirmAction({
 title: 'Eliminar estrategia',
 description: `Se eliminara "${strategy.name}" con sus grupos, sesiones y registros de asistencia.`,
 confirmLabel: 'Eliminar',
 destructive: true,
 onConfirm: handleDelete,
 });
 };

 const requestBlockAllSessions = () => {
 setConfirmAction({
 title: 'Bloquear sesiones',
 description: 'Se bloquearan todas las sesiones para reporte.',
 confirmLabel: 'Bloquear',
 destructive: true,
 onConfirm: async () => {
 try {
 const res = await apiFetch<BulkHabilitacionResponse>(`/evangelism/strategies/${id}/deshabilitar-todas`, { method: 'POST', token });
 toast.success(`${res.sesiones_deshabilitadas} sesiones bloqueadas`);
 fetchSessions();
 } catch (e: any) { toast.error('Error al deshabilitar sesiones'); }
 },
 });
 };

 const requestDeleteRole = (role: CustomRole) => {
 setConfirmAction({
 title: 'Eliminar rol',
 description: `Se eliminara el rol "${role.nombre_rol}".`,
 confirmLabel: 'Eliminar',
 destructive: true,
 onConfirm: async () => {
 try {
 await apiFetch(`/evangelism/strategies/${id}/roles/${role.id}`, { method: 'DELETE', token });
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
 const url = `${window.location.origin}/plataforma/evangelism/faro/${groupId}`;
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

 if (loading) {
 return (
 <EvangelismShell breadcrumbs={[
 { label: 'Evangelismo', icon: Flame, href: '/plataforma/evangelism' },
 { label: 'Estrategias', href: '/plataforma/evangelism' },
 { label: 'Cargando...' }
 ]}>
 <div className="space-y-3 p-3">
 {[1, 2, 3].map(i => <div key={i} className="h-12 bg-[hsl(var(--bg-muted))] rounded-lg animate-pulse" />)}
 </div>
 </EvangelismShell>
 );
 }

 if (!strategy) {
 return (
 <EvangelismShell breadcrumbs={[
 { label: 'Evangelismo', icon: Flame, href: '/plataforma/evangelism' },
 { label: 'Estrategias', href: '/plataforma/evangelism' },
 { label: 'No encontrada' }
 ]}>
 <div className="flex flex-col items-center justify-center py-16 text-center">
 <AlertCircle size={48} className="text-[hsl(var(--text-secondary))] mb-4" />
 <h2 className="text-lg font-bold text-[hsl(var(--text-primary))]">Estrategia no encontrada</h2>
 <button onClick={() => router.push('/plataforma/evangelism')}
 className="mt-4 px-4 h-9 rounded-lg bg-[hsl(var(--primary))] text-white text-xs font-semibold hover:bg-[hsl(var(--primary))] transition-colors">
 Volver a Estrategias
 </button>
 </div>
 </EvangelismShell>
 );
 }

 return (
 <EvangelismShell
 breadcrumbs={[
 { label: 'Evangelismo', icon: Flame, href: '/plataforma/evangelism' },
 { label: 'Estrategias', href: '/plataforma/evangelism' },
 { label: strategy.name }
 ]}
 sidebarGroups={groups.map(g => ({ id: g.id, name: g.name, estrategiaId: id as string }))}
 >
 <div className="flex-1 space-y-3 animate-fade-in px-3 md:px-6 lg:px-8 xl:px-12 py-1">
 {/* Header */}
 <div className="flex items-start justify-between gap-4">
 <div className="flex items-start gap-3">
 <button onClick={() => router.push('/plataforma/evangelism')}
 className="p-1.5 rounded-lg hover:bg-[hsl(var(--bg-muted))] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-secondary))] dark:hover:text-white transition-all mt-1">
 <ArrowLeft size={16} />
 </button>
 <div>
 <h1 className="text-xl font-bold text-[hsl(var(--text-primary))]">{strategy.name}</h1>
 <div className="flex items-center gap-3 mt-1 text-xs text-[hsl(var(--text-secondary))] font-medium flex-wrap">
 {strategy.typology && (
 <span className="px-2 py-0.5 rounded-full text-[10px] font-bold"
 style={{ backgroundColor: `${TYPOLOGY_COLORS[strategy.typology]}18`, color: TYPOLOGY_COLORS[strategy.typology] }}>
 {TYPOLOGY_LABELS[strategy.typology]}
 </span>
 )}
 {strategy.recurrence && <span className="inline-flex items-center gap-1.5"><Clock size={12} />{strategy.recurrence}</span>}
 <span className="px-2 py-0.5 rounded-full text-[10px] font-bold"
 style={{ backgroundColor: `${STATUS_COLORS[strategy.status]}18`, color: STATUS_COLORS[strategy.status] }}>
 {STATUS_LABELS[strategy.status]}
 </span>
 {strategy.group_count !== undefined && (
 <span className="inline-flex items-center gap-1.5"><Users size={12} />{strategy.group_count} grupo{strategy.group_count !== 1 ? 's' : ''}</span>
 )}
 </div>
 </div>
 </div>
 <button onClick={requestDeleteStrategy}
 className="p-2 rounded-lg text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--destructive))] hover:bg-red-50 dark:hover:bg-red-500/10 transition-all" title="Eliminar estrategia">
 <Trash2 size={16} />
 </button>
 </div>

 {/* Tabs */}
 <div className="flex items-center gap-1 border-b border-[hsl(var(--border-primary))]">
 {TABS.map(tab => (
 <button key={tab.id}
 onClick={() => tab.id === 'metrics' ? router.push(`/plataforma/evangelism/strategies/${id}/analytics`) : setActiveTab(tab.id)}
 className={`flex items-center gap-1.5 px-3 py-2 text-xs font-semibold border-b-2 transition-colors ${
 activeTab === tab.id
 ? 'border-blue-600 text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))] dark:border-blue-400'
 : 'border-transparent text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] dark:hover:text-[hsl(var(--text-secondary))]'
 }`}>
 <tab.icon size={14} />{tab.label}
 </button>
 ))}
 <div className="flex-1" />
 <ViewSwitcher viewType={viewType} setViewType={setViewType} availableViews={FULL_VIEWS} />
 </div>

 {/* ── View: Calendar ── */}
 {viewType === 'calendar' && (
 <UniversalCalendarView
 title={`Sesiones — ${strategy.name}`}
 events={sessions.map(s => ({
 id: String(s.id), title: s.topic || `Sesión #${s.id}`,
 date: s.session_date,
 color: s.status === 'Realizada' ? 'emerald' : 'blue' as const,
 location: groupName(s.grupo_id),
 }))}
 />
 )}

 {/* ── View: Gantt ── */}
 {viewType === 'gantt' && (
 <UniversalGanttView moduleName="Evangelismo"
 items={[
 ...groups.map(g => ({
 id: String(g.id), name: g.name, title: g.name,
 start_date: new Date().toISOString(), end_date: new Date(Date.now() + 30 * 86400000).toISOString(),
 progress: Math.min(g.personas_count * 20, 100),
 color: 'blue' as const, subtitle: `${g.personas_count} personas`,
 })),
 ...sessions.map(s => ({
 id: `s-${s.id}`, title: s.topic || `Sesión #${s.id}`,
 start_date: s.session_date, end_date: s.session_date,
 progress: s.status === 'Realizada' ? 100 : 0,
 color: s.status === 'Realizada' ? 'emerald' as const : 'blue' as const,
 subtitle: groupName(s.grupo_id),
 })),
 ]}
 />
 )}

 {/* ── View: Wiki ── */}
 {viewType === 'wiki' && (
 <UniversalWikiView moduleName="evangelism" storageKey={`strategy_${id}`} />
 )}

 {/* ── View: Kanban ── */}
 {viewType === 'kanban' && (activeTab === 'sessions' || activeTab === 'overview') && (
 <div className="flex gap-3 overflow-x-auto pb-4">
 {['Pendiente', 'Programada', 'Realizada'].map(label => {
 const colors: Record<string, string> = { 'Pendiente': '#F59E0B', 'Programada': '#3B82F6', 'Realizada': '#10B981' };
 const filtered = sessions.filter(s => s.status === label);
 return (
 <div key={label} className="min-w-[280px] w-[280px] shrink-0">
 <div className="rounded-lg p-3 mb-2 text-xs font-bold uppercase" style={{ background: `${colors[label]}15`, color: colors[label] }}>
 {label} ({filtered.length})
 </div>
 <div className="space-y-2">
 {filtered.map(s => (
 <div key={s.id} className="rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] dark:bg-[#1a1b1e] p-3">
 <p className="text-sm font-semibold text-[hsl(var(--text-primary))]">{s.topic || `Sesión #${s.id}`}</p>
 <p className="text-xs text-[hsl(var(--text-secondary))] mt-1">{groupName(s.grupo_id)}</p>
 <p className="text-xs text-[hsl(var(--text-secondary))] mt-1">{formatDate(s.session_date)}</p>
 </div>
 ))}
 {filtered.length === 0 && <p className="text-xs text-[hsl(var(--text-secondary))] p-3">Sin sesiones</p>}
 </div>
 </div>
 );
 })}
 </div>
 )}

 {/* ── View: Table (ag-grid, editable como Airtable) ── */}
 {viewType === 'table' && (
 <div className="flex flex-col gap-3">
 {/* Sub-tab switcher */}
 <div className="flex items-center gap-1 shrink-0">
 <button
 onClick={() => setTableSubTab('groups')}
 className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors ${
 tableSubTab === 'groups'
 ? 'bg-[hsl(var(--primary))] text-white'
 : 'bg-[hsl(var(--bg-muted))] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]'
 }`}
 >
 Grupos ({groups.length})
 </button>
 <button
 onClick={() => { setTableSubTab('sessions'); if (sessions.length === 0) fetchSessions(); }}
 className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors ${
 tableSubTab === 'sessions'
 ? 'bg-[hsl(var(--primary))] text-white'
 : 'bg-[hsl(var(--bg-muted))] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]'
 }`}
 >
 Sesiones ({sessions.length})
 </button>
 </div>

 {/* Groups table */}
 {tableSubTab === 'groups' && (
 <div className="h-[calc(100vh-280px)]">
 <UniversalTableView
 key="groups-table"
 viewName={`strategy_groups_${id}`}
 data={groups}
 isLoading={groupsLoading}
 emptyMessage="Sin grupos en esta estrategia"
 onAddItem={() => setIsGroupDrawerOpen(true)}
 onUpdateItem={async (rowId, field, value) => {
 const group = groups.find(g => g.id === rowId);
 if (!group) return false;
 try {
 await apiFetch(`/evangelism/grupos/${rowId}`, {
 method: 'PUT', token,
 body: JSON.stringify({ [field]: value }),
 });
 fetchGroups();
 toast.success('Grupo actualizado');
 return true;
 } catch {
 toast.error('Error al actualizar');
 return false;
 }
 }}
 columns={[
 {
 key: 'name',
 label: 'Nombre',
 type: 'text',
 editable: true,
 },
 {
 key: 'personas_count',
 label: 'Personas',
 type: 'number',
 width: '95',
 editable: false,
 filterable: true,
 render: (v: any) => (
 <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-[hsl(var(--bg-muted))] text-[hsl(var(--text-secondary))] text-[11px] font-semibold">
 <Users size={10} />{v}
 </span>
 ),
 },
 {
 key: 'leader_name',
 label: 'Líder',
 type: 'user',
 editable: false,
 },
 {
 key: 'zone',
 label: 'Zona',
 type: 'text',
 editable: true,
 },
 {
 key: 'capacity',
 label: 'Capacidad',
 type: 'number',
 width: '100',
 editable: false,
 },
 {
 key: 'status',
 label: 'Estado',
 type: 'status',
 width: '110',
 editable: false,
 },
 {
 key: '_acciones',
 label: '',
 type: 'text',
 width: '150',
 editable: false,
 filterable: false,
 hidden: false,
 render: (_: any, item: any) => (
 <div className="flex items-center gap-1">
 <button
 onClick={(e) => { e.stopPropagation(); openPersonaDrawer(item); }}
 className="inline-flex items-center gap-1 px-2 h-6 rounded bg-[hsl(var(--bg-muted))] text-[hsl(var(--text-secondary))] text-[10px] font-semibold hover:bg-blue-50 hover:text-[hsl(var(--primary))] dark:hover:bg-blue-900/20 dark:hover:text-[hsl(var(--primary))] transition-colors"
 >
 <Users size={10} /> Personas
 </button>
 <button
 onClick={(e) => { e.stopPropagation(); router.push(`/plataforma/evangelism/faro/${item.id}`); }}
 className="inline-flex items-center gap-1 px-2 h-6 rounded bg-[hsl(var(--bg-muted))] text-[hsl(var(--text-secondary))] text-[10px] font-semibold hover:bg-blue-50 hover:text-[hsl(var(--primary))] dark:hover:bg-blue-900/20 dark:hover:text-[hsl(var(--primary))] transition-colors"
 >
 <Calendar size={10} /> Detalle
 </button>
 <button
 onClick={(e) => { e.stopPropagation(); shareGroupLink(item.id, item.name, 'whatsapp'); }}
 title="Compartir por WhatsApp"
 className="w-6 h-6 inline-flex items-center justify-center rounded bg-emerald-50 text-emerald-600 hover:bg-emerald-100 dark:bg-emerald-900/20 dark:text-emerald-400 transition-colors"
 >
 <Share2 size={10} />
 </button>
 </div>
 ),
 },
 ]}
 />
 </div>
 )}

 {/* Sessions table */}
 {tableSubTab === 'sessions' && (
 <div className="h-[calc(100vh-280px)]">
 <UniversalTableView
 key="sessions-table"
 viewName={`strategy_sessions_${id}`}
 data={sessions.map(s => ({
 ...s,
 __displayName: s.topic || `Sesión #${s.id}`,
 grupo_nombre: groupName(s.grupo_id),
 }))}
 isLoading={sessionsLoading}
 emptyMessage="Sin sesiones registradas"
 onUpdateItem={async (rowId, field, value) => {
 const actualField = field === '__displayName' ? 'topic' : field;
 try {
 await apiFetch(`/evangelism/sessions/${rowId}`, {
 method: 'PUT', token,
 body: JSON.stringify({ [actualField]: value }),
 });
 fetchSessions();
 toast.success('Sesión actualizada');
 return true;
 } catch {
 toast.error('Error al actualizar');
 return false;
 }
 }}
 columns={[
 {
 key: '__displayName',
 label: 'Tema / Sesión',
 type: 'text',
 editable: true,
 },
 {
 key: 'grupo_nombre',
 label: 'Grupo',
 type: 'text',
 width: '130',
 editable: false,
 },
 {
 key: 'session_date',
 label: 'Fecha',
 type: 'date',
 width: '110',
 editable: false,
 },
 {
 key: 'status',
 label: 'Estado',
 type: 'status',
 width: '120',
 editable: false,
 },
 {
 key: 'estado_habilitacion',
 label: 'Habilitación',
 type: 'status',
 width: '120',
 editable: false,
 },
 {
 key: '_acciones',
 label: '',
 type: 'text',
 width: '160',
 editable: false,
 filterable: false,
 render: (_: any, item: any) => (
 <div className="flex items-center gap-1">
 <button
 onClick={(e) => { e.stopPropagation(); openAttendanceDrawer(item); }}
 className="inline-flex items-center gap-1 px-2 h-6 rounded bg-[hsl(var(--bg-muted))] text-[hsl(var(--text-secondary))] text-[10px] font-semibold hover:bg-blue-50 hover:text-[hsl(var(--primary))] dark:hover:bg-blue-900/20 dark:hover:text-[hsl(var(--primary))] transition-colors whitespace-nowrap"
 >
 <Users size={10} /> Asistencia
 </button>
 {item.estado_habilitacion !== 'CERRADO' && item.estado_habilitacion !== 'CANCELADA' && (
 <button
 onClick={async (e) => {
 e.stopPropagation();
 const accion = item.estado_habilitacion === 'HABILITADO' ? 'DESHABILITAR' : 'HABILITAR';
 try {
 await apiFetch(`/evangelism/sessions/${item.id}/habilitacion`, { method: 'PATCH', token, body: JSON.stringify({ accion }) });
 fetchSessions();
 } catch { toast.error('Error al cambiar estado'); }
 }}
 title={item.estado_habilitacion === 'HABILITADO' ? 'Cerrar sesión' : 'Abrir sesión'}
 className={`w-6 h-6 inline-flex items-center justify-center rounded font-bold text-[11px] transition-colors ${
 item.estado_habilitacion === 'HABILITADO'
 ? 'bg-emerald-100 text-emerald-700 hover:bg-rose-100 hover:text-rose-600 dark:bg-emerald-900/30 dark:text-emerald-400'
 : 'bg-amber-50 text-amber-600 hover:bg-emerald-100 hover:text-emerald-700 dark:bg-amber-900/20 dark:text-amber-400'
 }`}
 >
 {item.estado_habilitacion === 'HABILITADO' ? '✓' : '○'}
 </button>
 )}
 <button
 onClick={(e) => { e.stopPropagation(); requestDeleteSession(item.id); }}
 className="w-6 h-6 inline-flex items-center justify-center rounded text-[hsl(var(--text-secondary))] hover:bg-red-50 hover:text-rose-500 dark:hover:bg-red-900/20 transition-colors"
 title="Eliminar"
 >
 <Trash2 size={11} />
 </button>
 </div>
 ),
 },
 ]}
 />
 </div>
 )}
 </div>
 )}

 {/* ── View: List (tab-aware) ── */}
 {viewType === 'list' && (
 <div className="space-y-1">
 {(activeTab === 'groups' || activeTab === 'overview') && groups.map(g => (
 <div key={`g-${g.id}`} className="flex items-center gap-3 p-3 rounded-lg hover:bg-[hsl(var(--bg-muted))] dark:hover:bg-white/5 transition-all">
 <div className="w-8 h-8 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center shrink-0"><Users size={14} className="text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))]" /></div>
 <div className="flex-1 min-w-0">
 <p className="text-sm font-semibold text-[hsl(var(--text-primary))] truncate">{g.name}</p>
 <p className="text-xs text-[hsl(var(--text-secondary))]">{g.personas_count} personas{g.zone ? ` · ${g.zone}` : ''}</p>
 </div>
 <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-green-100 text-[hsl(var(--secondary))] dark:bg-green-900/30 dark:text-green-300">Grupo</span>
 </div>
 ))}
 {(activeTab === 'sessions' || activeTab === 'overview') && sessions.map(s => (
 <div key={`s-${s.id}`} className="flex items-center gap-3 p-3 rounded-lg hover:bg-[hsl(var(--bg-muted))] dark:hover:bg-white/5 transition-all">
 <div className="w-8 h-8 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center shrink-0"><Calendar size={14} className="text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))]" /></div>
 <div className="flex-1 min-w-0">
 <p className="text-sm font-semibold text-[hsl(var(--text-primary))] truncate">{s.topic || `Sesión #${s.id}`}</p>
 <p className="text-xs text-[hsl(var(--text-secondary))]">{groupName(s.grupo_id)} · {formatDate(s.session_date)}</p>
 </div>
 <span className="px-2 py-0.5 rounded text-[10px] font-bold" style={{ backgroundColor: s.status === 'Realizada' ? '#10B98120' : '#3B82F620', color: s.status === 'Realizada' ? '#10B981' : '#3B82F6' }}>{s.status}</span>
 </div>
 ))}
 </div>
 )}

 {/* ── View: Grid (tab-aware) ── */}
 {viewType === 'grid' && (
 <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
 {(activeTab === 'groups' || activeTab === 'overview') && groups.map(g => (
 <div key={`g-${g.id}`} className="rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] dark:bg-[#1a1b1e] p-4 hover:shadow-md transition-shadow">
 <div className="flex items-center gap-2 mb-2">
 <div className="w-6 h-6 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center"><Users size={12} className="text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))]" /></div>
 <span className="text-xs font-bold text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))]">GRUPO</span>
 </div>
 <h3 className="text-sm font-bold text-[hsl(var(--text-primary))]">{g.name}</h3>
 <p className="text-xs text-[hsl(var(--text-secondary))] mt-1">{g.zone || 'Sin zona'}</p>
 <span className="text-xs font-medium text-[hsl(var(--text-secondary))] mt-3 block">{g.personas_count} personas</span>
 </div>
 ))}
 {(activeTab === 'sessions' || activeTab === 'overview') && sessions.map(s => (
 <div key={`s-${s.id}`} className="rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] dark:bg-[#1a1b1e] p-4 hover:shadow-md transition-shadow">
 <div className="flex items-center gap-2 mb-2">
 <div className="w-6 h-6 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center"><Calendar size={12} className="text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))]" /></div>
 <span className="text-xs font-bold text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))]">SESIÓN</span>
 </div>
 <h3 className="text-sm font-bold text-[hsl(var(--text-primary))]">{s.topic || `Sesión #${s.id}`}</h3>
 <p className="text-xs text-[hsl(var(--text-secondary))] mt-1">{groupName(s.grupo_id)}</p>
 <div className="flex items-center justify-between mt-3">
 <span className="text-xs text-[hsl(var(--text-secondary))]">{formatDate(s.session_date)}</span>
 <span className="px-1.5 py-0.5 rounded text-[10px] font-bold" style={{ backgroundColor: s.status === 'Realizada' ? '#10B98120' : '#3B82F620', color: s.status === 'Realizada' ? '#10B981' : '#3B82F6' }}>{s.status}</span>
 </div>
 </div>
 ))}
 </div>
 )}

 {/* ── Overview ── */}
 {viewType === 'dashboard' && activeTab === 'overview' && (
 <div className="bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] border border-[hsl(var(--border-primary))] rounded-lg p-4 space-y-4">
 <div>
 <label className="block text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1">Nombre</label>
 <input type="text" value={editName} onChange={e => setEditName(e.target.value)}
 className="w-full px-3 py-2 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-muted))] text-sm text-[hsl(var(--text-primary))] focus:border-[hsl(var(--primary))] focus:outline-none transition-colors" />
 </div>
 <div>
 <label className="block text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1">Descripción</label>
 <textarea value={editDesc} onChange={e => setEditDesc(e.target.value)} rows={3}
 className="w-full px-3 py-2 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-muted))] text-sm text-[hsl(var(--text-primary))] focus:border-[hsl(var(--primary))] focus:outline-none transition-colors resize-none"
 placeholder="Detalles sobre la estrategia..." />
 </div>
 <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
 <div>
 <label className="block text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1">Tipo</label>
 <select value={editType} onChange={e => setEditType(e.target.value)}
 className="w-full px-3 py-2 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-muted))] text-sm text-[hsl(var(--text-primary))] focus:border-[hsl(var(--primary))] focus:outline-none transition-colors">
 <option value="">General</option>
 <option value="Geográfica">Geográfica</option>
 <option value="Temática">Temática</option>
 <option value="Sectorial">Sectorial</option>
 <option value="Poblacional">Poblacional</option>
 <option value="Servicios (Cultos)">Servicios (Cultos)</option>
 </select>
 </div>
 <div>
 <label className="block text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1">Estado</label>
 <select value={editStatus} onChange={e => setEditStatus(e.target.value as any)}
 className="w-full px-3 py-2 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-muted))] text-sm text-[hsl(var(--text-primary))] focus:border-[hsl(var(--primary))] focus:outline-none transition-colors">
 <option value="pending">No iniciada</option>
 <option value="active">Iniciada</option>
 <option value="done">Terminada</option>
 </select>
 </div>
 </div>
 <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
 <div>
 <label className="block text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1">Clase Raíz</label>
 <div className="flex gap-2">
 {['relacional', 'evento_masivo', 'sectorial'].map(c => (
 <button key={c} onClick={() => setEditClaseRaiz(c)}
 className={`flex-1 px-2 py-1.5 text-[10px] font-bold rounded-lg transition-all capitalize ${
 editClaseRaiz === c
 ? 'bg-[hsl(var(--primary))] text-white shadow-sm'
 : 'bg-[hsl(var(--bg-muted))] text-[hsl(var(--text-secondary))] border border-[hsl(var(--border-primary))]'
 }`}>
 {c === 'evento_masivo' ? 'Evento Masivo' : c}
 </button>
 ))}
 </div>
 </div>
 <div>
 <label className="block text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1">Activa</label>
 <button onClick={() => setEditActiva(!editActiva)}
 className={`w-full px-3 py-2 rounded-lg text-[12px] font-bold transition-all text-left ${
 editActiva
 ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800'
 : 'bg-[hsl(var(--bg-muted))] text-[hsl(var(--text-secondary))] border border-[hsl(var(--border-primary))]'
 }`}>
 {editActiva ? 'Activa' : 'Inactiva'}
 </button>
 </div>
 </div>
 <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
 <div>
 <label className="block text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1">Recurrencia</label>
 <select value={editRecurrence || ''} onChange={e => setEditRecurrence(e.target.value || null)}
 className="w-full px-3 py-2 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-muted))] text-sm text-[hsl(var(--text-primary))] focus:border-[hsl(var(--primary))] focus:outline-none transition-colors">
 <option value="">Sin recurrencia</option>
 <option value="SEMANAL">Semanal</option>
 <option value="QUINCENAL">Quincenal</option>
 <option value="MENSUAL">Mensual</option>
 <option value="BIMENSUAL">Bimensual</option>
 <option value="TRIMESTRAL">Trimestral</option>
 <option value="SEMESTRAL">Semestral</option>
 <option value="ANUAL">Anual</option>
 <option value="EVENTO_UNICO">Evento único</option>
 </select>
 </div>
 <div>
 <input type="date" value={editStartDate} onChange={e => setEditStartDate(e.target.value)}
 className="w-full px-3 py-2 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-muted))] text-sm text-[hsl(var(--text-primary))] focus:border-[hsl(var(--primary))] focus:outline-none transition-colors" />
 </div>
 <div>
 <label className="block text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1">Fecha de fin</label>
 <input type="date" value={editEndDate} onChange={e => setEditEndDate(e.target.value)}
 className="w-full px-3 py-2 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-muted))] text-sm text-[hsl(var(--text-primary))] focus:border-[hsl(var(--primary))] focus:outline-none transition-colors" />
 </div>
 </div>
 <div className="flex items-center justify-end gap-2 pt-2 border-t border-[hsl(var(--border-primary))]">
 <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
 onClick={handleSave} disabled={saving}
 className="inline-flex items-center gap-2 px-4 h-9 rounded-lg bg-[hsl(var(--primary))] text-white text-xs font-semibold hover:bg-[hsl(var(--primary))] disabled:opacity-60 transition-colors">
 <Save size={14} />{saving ? 'Guardando...' : 'Guardar cambios'}
 </motion.button>
 </div>
 </div>
 )}

 {/* ── Grupos ── */}
 {viewType === 'dashboard' && activeTab === 'groups' && (
 <div className="space-y-3">
 <div className="flex items-center justify-between">
 <div>
 <h2 className="text-sm font-bold text-[hsl(var(--text-primary))]">Grupos de esta estrategia</h2>
 {strategy.typology === 'relacional' && (
 <p className="text-[11px] text-[hsl(var(--text-secondary))] mt-0.5">
 Config: {strategy.recurrence} · {strategy.day_of_week ? `Día: ${strategy.day_of_week}` : ''} {strategy.start_time ? `Hora: ${strategy.start_time}` : ''}
 </p>
 )}
 </div>
 <button onClick={openGroupDrawer}
 className="inline-flex items-center gap-1.5 px-3 h-8 rounded-lg bg-[hsl(var(--primary))] text-white text-xs font-semibold hover:bg-[hsl(var(--primary))] transition-colors">
 <Plus size={14} />Nuevo grupo
 </button>
 </div>
 {groups.length === 0 ? (
 <div className="flex flex-col items-center justify-center py-12 text-center bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] border border-[hsl(var(--border-primary))] rounded-lg">
 <Home size={32} className="text-[hsl(var(--text-secondary))] mb-2" />
 <p className="text-sm font-medium text-[hsl(var(--text-secondary))]">Sin grupos aún</p>
 <p className="text-xs text-[hsl(var(--text-secondary))]">Crea el primer grupo para esta estrategia</p>
 </div>
 ) : (
 <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
 {groups.map(g => (
 <div key={g.id}
 className="group bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] border border-[hsl(var(--border-primary))] rounded-lg p-4 hover:border-blue-300 dark:hover:border-blue-800 transition-all cursor-pointer relative"
 onClick={() => openPersonaDrawer(g)}>
 <button onClick={e => { e.stopPropagation(); requestDeleteGroup(g.id, g.name); }}
 className="absolute top-2 right-2 p-1 rounded text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--destructive))] hover:bg-red-50 dark:hover:bg-red-900/20 opacity-0 group-hover:opacity-100 transition-all z-10" title="Eliminar">
 <Trash2 size={14} />
 </button>
 <button onClick={e => { e.stopPropagation(); router.push(`/plataforma/evangelism/faro/${g.id}`); }}
 className="absolute top-2 right-8 p-1 rounded text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] hover:bg-blue-50 dark:hover:bg-blue-900/20 opacity-0 group-hover:opacity-100 transition-all z-10" title="Ver detalle">
 <Calendar size={14} />
 </button>
 <button onClick={e => { e.stopPropagation(); openGroupAttendance(g); }}
 className="absolute top-2 right-[3.25rem] p-1 rounded text-[hsl(var(--text-secondary))] hover:text-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-900/20 opacity-0 group-hover:opacity-100 transition-all z-10" title="Registrar asistencia">
 <ClipboardList size={14} />
 </button>
 {/* Share button + dropdown */}
 <div className="absolute top-2 right-[4.75rem] z-20">
 <button
 onClick={e => { e.stopPropagation(); setShareMenuId(shareMenuId === g.id ? null : g.id); }}
 className="p-1 rounded text-[hsl(var(--text-secondary))] hover:text-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-900/20 opacity-0 group-hover:opacity-100 transition-all"
 title="Compartir enlace del grupo"
 >
 <Share2 size={14} />
 </button>
 {shareMenuId === g.id && (
 <div
 onClick={e => e.stopPropagation()}
 className="absolute top-7 right-0 w-52 bg-[hsl(var(--bg-primary))] dark:bg-[#2a2b2d] border border-[hsl(var(--border-primary))] rounded-lg shadow-xl py-1"
 >
 <p className="text-[9px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] px-3 py-1.5">Compartir enlace del grupo</p>
 <button onClick={() => shareGroupLink(g.id, g.name, 'copy')}
 className="w-full text-left px-3 py-2 text-xs font-medium text-[hsl(var(--text-primary))] hover:bg-[hsl(var(--bg-muted))] flex items-center gap-2">
 <Copy size={12} className="shrink-0" /> Copiar enlace
 </button>
 <button onClick={() => shareGroupLink(g.id, g.name, 'whatsapp')}
 className="w-full text-left px-3 py-2 text-xs font-medium text-[hsl(var(--text-primary))] hover:bg-[hsl(var(--bg-muted))] flex items-center gap-2">
 <span className="shrink-0 w-3 h-3 rounded-full bg-emerald-500 inline-block" />WhatsApp
 </button>
 <button onClick={() => shareGroupLink(g.id, g.name, 'telegram')}
 className="w-full text-left px-3 py-2 text-xs font-medium text-[hsl(var(--text-primary))] hover:bg-[hsl(var(--bg-muted))] flex items-center gap-2">
 <span className="shrink-0 w-3 h-3 rounded-full bg-sky-500 inline-block" />Telegram
 </button>
 </div>
 )}
 </div>
 <h3 className="text-sm font-bold text-[hsl(var(--text-primary))] pr-28">{g.name}</h3>
 <p className="text-xs text-[hsl(var(--text-secondary))] mt-1">{g.zone || 'Sin zona'}</p>
 <div className="flex items-center gap-3 mt-3 text-xs text-[hsl(var(--text-secondary))]">
 <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-[hsl(var(--bg-muted))]">
 <Users size={12} />{g.personas_count} personas
 </span>
 {g.leader_name && <span>Líder: {g.leader_name}</span>}
 </div>
 </div>
 ))}
 </div>
 )}
 </div>
 )}

 {/* ── Sesiones ── */}
 {viewType === 'dashboard' && activeTab === 'sessions' && (
 <div className="space-y-3">
 <div className="flex items-center justify-between flex-wrap gap-2">
 <h2 className="text-sm font-bold text-[hsl(var(--text-primary))]">Registro de sesiones</h2>
 <div className="flex items-center gap-2 flex-wrap">
 {strategy.recurrence && strategy.start_date && strategy.end_date && (
 <button onClick={async () => {
 const btn = toast.loading('Generando sesiones...');
 try {
 const res = await apiFetch<GenerateSessionsResponse>(`/evangelism/strategies/${id}/generate-sessions`, { method: 'POST', token });
 toast.dismiss(btn);
 if (res.message) {
 toast.info(res.message);
 } else {
 toast.success(`Sesiones generadas: ${res.sessions_per_group || ''} por grupo (${res.total_sessions_created} totales)`);
 }
 fetchSessions();
 } catch (e: any) {
 toast.dismiss(btn);
 toast.error('Error: ' + (e.message || 'Verifica fechas y frecuencia'));
 }
 }}
 className="inline-flex items-center gap-1.5 px-3 h-8 rounded-lg border border-[hsl(var(--border-primary))] dark:border-white/20 text-[hsl(var(--text-secondary))] text-xs font-semibold hover:bg-[hsl(var(--bg-muted))] transition-colors">
 <Sparkles size={14} />Generar sesiones
 </button>
 )}
 <button onClick={async () => {
 try {
 const res = await apiFetch<BulkHabilitacionResponse>(`/evangelism/strategies/${id}/habilitar-todas`, { method: 'POST', token });
 toast.success(`${res.sesiones_habilitadas} sesiones habilitadas`);
 fetchSessions();
 } catch (e: any) { toast.error('Error al habilitar sesiones'); }
 }}
 className="inline-flex items-center gap-1.5 px-3 h-8 rounded-lg border border-emerald-300 dark:border-emerald-700 text-emerald-700 dark:text-emerald-400 text-xs font-semibold hover:bg-emerald-50 dark:hover:bg-emerald-900/20 transition-colors">
 <CheckCircle2 size={14} />Habilitar todas
 </button>
 <button onClick={requestBlockAllSessions}
 className="inline-flex items-center gap-1.5 px-3 h-8 rounded-lg border border-rose-300 dark:border-rose-700 text-rose-600 dark:text-rose-400 text-xs font-semibold hover:bg-rose-50 dark:hover:bg-rose-900/20 transition-colors">
 <AlertCircle size={14} />Bloquear todas
 </button>
 <button onClick={() => {
 setSessionForm({ grupo_id: groups[0]?.id || '', session_date: new Date().toISOString().split('T')[0], topic: '', offering_amount: '', report_notes: '' });
 setIsNewSessionDrawerOpen(true);
 }}
 className="inline-flex items-center gap-1.5 px-3 h-8 rounded-lg bg-[hsl(var(--primary))] text-white text-xs font-semibold hover:opacity-90 transition-colors">
 <Plus size={14} />Nueva sesión
 </button>
 </div>
 </div>

 {/* Buscador + filtros */}
 <div className="flex flex-col gap-2">
 {/* Buscador */}
 <div className="relative">
 <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))] pointer-events-none" />
 <input
 value={sessionSearch}
 onChange={e => setSessionSearch(e.target.value)}
 placeholder="Buscar por tema, grupo o mes (ej. 2025-03)…"
 className="w-full pl-8 pr-8 h-8 text-xs rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] text-[hsl(var(--text-primary))] placeholder:text-[hsl(var(--text-secondary))] focus:outline-none focus:ring-1 focus:ring-blue-400"
 />
 {sessionSearch && (
 <button onClick={() => setSessionSearch('')} className="absolute right-2 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-secondary))]">
 <X size={12} />
 </button>
 )}
 </div>
 {/* Filtros en fila */}
 <div className="flex items-center gap-2 flex-wrap">
 {groups.length > 1 && (
 <select
 value={sessionGroupFilter}
 onChange={e => setSessionGroupFilter(e.target.value)}
 className="h-7 px-2 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] text-xs text-[hsl(var(--text-primary))] focus:outline-none focus:ring-1 focus:ring-blue-400">
 <option value="all">Todos los grupos</option>
 {groups.map(g => <option key={g.id} value={g.id}>{g.name}</option>)}
 </select>
 )}
 <select
 value={sessionHabFilter}
 onChange={e => setSessionHabFilter(e.target.value as typeof sessionHabFilter)}
 className="h-7 px-2 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] text-xs text-[hsl(var(--text-primary))] focus:outline-none focus:ring-1 focus:ring-blue-400">
 <option value="all">Todas las habilitaciones</option>
 <option value="HABILITADO">Abiertas</option>
 <option value="DESHABILITADO">Bloqueadas</option>
 <option value="CERRADO">Cerradas</option>
 </select>
 {sessionMonths.length > 1 && (
 <select
 value={sessionMonthFilter}
 onChange={e => setSessionMonthFilter(e.target.value)}
 className="h-7 px-2 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] text-xs text-[hsl(var(--text-primary))] focus:outline-none focus:ring-1 focus:ring-blue-400">
 <option value="all">Todos los meses</option>
 {sessionMonths.map(m => {
 const [y, mo] = m.split('-');
 const label = new Date(Number(y), Number(mo) - 1, 1).toLocaleDateString('es-CO', { month: 'long', year: 'numeric' });
 return <option key={m} value={m}>{label}</option>;
 })}
 </select>
 )}
 {/* Contador */}
 <span className="ml-auto text-[11px] text-[hsl(var(--text-secondary))]">
 {filteredSessions.length !== sessions.length
 ? `${filteredSessions.length} de ${sessions.length} sesiones`
 : `${sessions.length} sesion${sessions.length !== 1 ? 'es' : ''}`}
 </span>
 </div>
 </div>

 {sessionsLoading ? (
 <div className="space-y-2">
 {[1, 2, 3].map(i => <div key={i} className="h-14 bg-[hsl(var(--bg-muted))] rounded-lg animate-pulse" />)}
 </div>
 ) : filteredSessions.length === 0 ? (
 <div className="flex flex-col items-center justify-center py-12 text-center bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] border border-[hsl(var(--border-primary))] rounded-lg">
 <ClipboardList size={32} className="text-[hsl(var(--text-secondary))] mb-2" />
 <p className="text-sm font-medium text-[hsl(var(--text-secondary))]">
 {sessions.length === 0 ? 'Sin sesiones registradas' : 'Sin sesiones con esos filtros'}
 </p>
 <p className="text-xs text-[hsl(var(--text-secondary))]">
 {sessions.length === 0 ? 'Registra la primera sesión semanal' : 'Prueba ajustando la búsqueda o los filtros'}
 </p>
 </div>
 ) : (
 <div className="space-y-2">
 {filteredSessions.map(s => (
 <div key={s.id} className={`flex items-center gap-3 bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] border rounded-lg px-4 py-3 transition-all ${
 s.estado_habilitacion === 'HABILITADO'
 ? 'border-emerald-300 dark:border-emerald-700'
 : s.estado_habilitacion === 'CERRADO'
 ? 'border-[hsl(var(--border-primary))] opacity-60'
 : 'border-[hsl(var(--border-primary))]'
 }`}>
 <div className="flex-1 min-w-0">
 <div className="flex items-center gap-2 flex-wrap">
 <span className="text-xs font-bold text-[hsl(var(--text-primary))]">
 {new Date(s.session_date.split('T')[0] + 'T12:00:00').toLocaleDateString('es-CO', { weekday: 'long', day: 'numeric', month: 'short', year: 'numeric' })}
 </span>
 <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-green-100 text-[hsl(var(--secondary))] dark:bg-green-900/30 dark:text-[hsl(var(--secondary))]">
 {s.status}
 </span>
 {/* Badge de habilitación */}
 {s.estado_habilitacion === 'HABILITADO' && (
 <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400">Abierta</span>
 )}
 {s.estado_habilitacion === 'CERRADO' && (
 <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-[hsl(var(--bg-muted))] text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]">Cerrada</span>
 )}
 {(!s.estado_habilitacion || s.estado_habilitacion === 'DESHABILITADO') && (
 <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-50 text-amber-600 dark:bg-amber-900/20 dark:text-amber-400">Bloqueada</span>
 )}
 </div>
 <div className="flex items-center gap-3 mt-0.5 text-[11px] text-[hsl(var(--text-secondary))]">
 <span>{groupName(s.grupo_id)}</span>
 {s.topic && <span>· {s.topic}</span>}
 {s.offering_amount != null && <span>· Ofrenda: ${s.offering_amount.toLocaleString()}</span>}
 </div>
 </div>
 <div className="flex items-center gap-2">
 {/* Toggle habilitación individual */}
 <button
 onClick={async () => {
 const accion = s.estado_habilitacion === 'HABILITADO' ? 'DESHABILITAR' : 'HABILITAR';
 try {
 await apiFetch(`/evangelism/sessions/${s.id}/habilitacion`, {
 method: 'PATCH', token,
 body: JSON.stringify({ accion }),
 });
 fetchSessions();
 } catch { toast.error('Error al cambiar estado'); }
 }}
 title={s.estado_habilitacion === 'HABILITADO' ? 'Bloquear sesión' : 'Habilitar sesión'}
 className={`w-7 h-7 flex items-center justify-center rounded-lg transition-colors text-[11px] font-bold ${
 s.estado_habilitacion === 'HABILITADO'
 ? 'bg-emerald-100 text-emerald-700 hover:bg-rose-100 hover:text-rose-600 dark:bg-emerald-900/30 dark:text-emerald-400'
 : 'bg-amber-50 text-amber-600 hover:bg-emerald-100 hover:text-emerald-700 dark:bg-amber-900/20 dark:text-amber-400'
 }`}
 >
 {s.estado_habilitacion === 'HABILITADO' ? '✓' : '○'}
 </button>
 <button onClick={() => openAttendanceDrawer(s)}
 className="inline-flex items-center gap-1.5 px-3 h-7 rounded-lg bg-[hsl(var(--bg-muted))] text-[hsl(var(--text-secondary))] text-[11px] font-semibold hover:bg-blue-50 hover:text-[hsl(var(--primary))] dark:hover:bg-blue-900/20 dark:hover:text-[hsl(var(--primary))] transition-colors whitespace-nowrap">
 <Users size={12} />Asistencia
 </button>
 <div className="relative">
 <button onClick={() => setSessionMenuId(sessionMenuId === s.id ? null : s.id)}
 className="w-7 h-7 flex items-center justify-center rounded-lg text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--bg-muted))] dark:hover:bg-white/10 hover:text-[hsl(var(--text-secondary))] dark:hover:text-white transition-colors">
 <span className="text-base leading-none">⋯</span>
 </button>
 {sessionMenuId === s.id && (
 <div className="absolute right-0 top-8 z-20 bg-[hsl(var(--bg-primary))] dark:bg-[#2a2b2d] border border-[hsl(var(--border-primary))] rounded-lg shadow-lg py-1 min-w-[130px]">
 <button
 onClick={() => requestDeleteSession(s.id)}
 className="w-full text-left px-3 py-2 text-xs text-[hsl(var(--destructive))] dark:text-[hsl(var(--destructive))] hover:bg-red-50 dark:hover:bg-red-900/20 flex items-center gap-2">
 <Trash2 size={12} />Eliminar sesión
 </button>
 </div>
 )}
 </div>
 </div>
 </div>
 ))}
 </div>
 )}
 </div>
 )}

 {/* ── Asistencia ── */}
 {viewType === 'dashboard' && activeTab === 'attendance' && (
  <div className="space-y-4">
   <div className="flex items-center justify-between">
    <p className="text-[11px] font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
     Grupos — sesiones recientes
    </p>
    {sessionsLoading && <Loader2 size={14} className="animate-spin text-[hsl(var(--text-secondary))]" />}
   </div>

   {sessionsLoading && attendanceByGroup.length === 0 ? (
    <div className="space-y-3">
     {[1, 2, 3].map(i => <div key={i} className="h-28 rounded-xl bg-[hsl(var(--bg-muted))] animate-pulse" />)}
    </div>
   ) : attendanceByGroup.length === 0 ? (
    <div className="flex flex-col items-center gap-2 py-10 border-2 border-dashed border-[hsl(var(--border-primary))] rounded-xl text-center">
     <ClipboardList size={28} className="text-[hsl(var(--text-secondary))] opacity-40" />
     <p className="text-sm font-semibold text-[hsl(var(--text-secondary))]">Sin sesiones registradas</p>
     <p className="text-xs text-[hsl(var(--text-secondary))] opacity-70">Crea sesiones en el tab Sesiones para poder reportar asistencia</p>
    </div>
   ) : (
    <div className="space-y-3">
     {attendanceByGroup.map(({ group: grp, sessions: grpSessions, latest }) => {
      const isHabilitado = latest?.estado_habilitacion === 'HABILITADO';
      return (
       <div key={grp.id} className={`bg-[hsl(var(--bg-primary))] rounded-xl border overflow-hidden ${isHabilitado ? 'border-emerald-200 dark:border-emerald-800/40' : 'border-[hsl(var(--border-primary))]'}`}>
        {/* Cabecera del grupo */}
        <div className={`flex items-center justify-between px-4 py-3 ${isHabilitado ? 'bg-emerald-50 dark:bg-emerald-900/10' : 'bg-[hsl(var(--bg-secondary))]'}`}>
         <div className="min-w-0">
          <div className="flex items-center gap-2">
           {isHabilitado && <span className="size-1.5 rounded-full bg-emerald-500 animate-pulse shrink-0" />}
           <p className="text-sm font-bold text-[hsl(var(--text-primary))] truncate">{grp.name}</p>
          </div>
          <div className="flex items-center gap-3 mt-0.5 text-[11px] text-[hsl(var(--text-secondary))]">
           {grp.leader_name && <span>{grp.leader_name}</span>}
           <span>{grp.personas_count} personas</span>
          </div>
         </div>
         {latest && (
          <button
           onClick={() => openAttendanceDrawer(latest)}
           className={`shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-bold uppercase tracking-wide transition-all active:scale-95 ${
            isHabilitado
             ? 'bg-[hsl(var(--primary))] text-white hover:opacity-90 shadow-sm'
             : 'bg-[hsl(var(--bg-muted))] text-[hsl(var(--text-secondary))] hover:bg-blue-50 hover:text-[hsl(var(--primary))] dark:hover:bg-blue-900/20'
           }`}
          >
           <ClipboardList size={12} />
           {isHabilitado ? 'Registrar' : 'Ver sesión'}
          </button>
         )}
        </div>

        {/* Lista de sesiones recientes del grupo */}
        <div className="divide-y divide-[hsl(var(--border-primary))]">
         {grpSessions.map(s => {
          const dateStr = new Date(s.session_date.split('T')[0] + 'T12:00:00').toLocaleDateString('es-CO', {
           weekday: 'short', day: 'numeric', month: 'short',
          });
          const isClosed = s.estado_habilitacion === 'CERRADO' || s.estado_habilitacion === 'CANCELADA';
          const habColor = s.estado_habilitacion === 'HABILITADO'
           ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400'
           : s.estado_habilitacion === 'CANCELADA'
           ? 'bg-red-50 text-[hsl(var(--destructive))] dark:bg-red-900/20'
           : s.estado_habilitacion === 'CERRADO'
           ? 'bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))] dark:bg-white/10 dark:text-[hsl(var(--text-secondary))]'
           : 'bg-amber-50 text-amber-600 dark:bg-amber-900/20 dark:text-amber-400';
          return (
           <div key={s.id} className="flex items-center gap-3 px-4 py-2.5 hover:bg-[hsl(var(--bg-muted))] transition-colors">
            <div className="flex-1 min-w-0 flex items-center gap-2">
             <span className={`shrink-0 px-1.5 py-0.5 rounded text-[9px] font-bold uppercase tracking-wide ${habColor}`}>
              {s.estado_habilitacion ?? 'DESHABILITADO'}
             </span>
             <p className="text-[12px] text-[hsl(var(--text-secondary))] capitalize truncate">
              {dateStr}{s.topic ? ` · ${s.topic}` : ''}
             </p>
            </div>
            {!isClosed && (
             <button
              onClick={() => openAttendanceDrawer(s)}
              className="shrink-0 text-[11px] font-semibold text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] transition-colors whitespace-nowrap"
             >
              Reportar
             </button>
            )}
           </div>
          );
         })}
        </div>
       </div>
      );
     })}
    </div>
   )}
  </div>
 )}

 {/* ── Métricas ── */}
 {viewType === 'dashboard' && activeTab === 'metrics' && (
 <div className="space-y-4">
 <div className="bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border-primary))] rounded-xl p-8 flex flex-col items-center text-center gap-4">
 <div className="p-4 rounded-2xl bg-sky-50 dark:bg-sky-950/40">
 <BarChart3 size={36} className="text-[hsl(var(--primary))]" />
 </div>
 <div>
 <h3 className="text-base font-bold text-[hsl(var(--text-primary))] mb-1">Dashboard de métricas</h3>
 <p className="text-sm text-[hsl(var(--text-secondary))] max-w-sm">
 Tendencias de asistencia, embudo de roles, mapa de calor, alertas tempranas y velocidad ministerial en tiempo real.
 </p>
 </div>
 <button
 onClick={() => router.push(`/plataforma/evangelism/strategies/${id}/analytics`)}
 className="flex items-center gap-2 px-5 py-2.5 bg-[hsl(var(--primary))] hover:opacity-90 text-white rounded-lg text-sm font-semibold transition-all shadow-sm"
 >
 <BarChart3 size={15} />
 Abrir dashboard analítico
 </button>
 </div>
 {metrics && (
 <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
 {[
 { label: 'Grupos', value: metrics.summary.total_groups },
 { label: 'Sesiones', value: metrics.summary.total_sessions },
 { label: 'Primera vez', value: metrics.summary.total_first_timers, cls: 'text-emerald-600' },
 { label: 'Inasistencias', value: metrics.summary.total_absences, cls: 'text-[hsl(var(--destructive))]' },
 ].map(stat => (
 <div key={stat.label} className="bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border-primary))] rounded-lg p-4">
 <p className="text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]">{stat.label}</p>
 <p className={`text-2xl font-black mt-1 ${stat.cls || 'text-[hsl(var(--text-primary))]'}`}>{stat.value}</p>
 </div>
 ))}
 </div>
 )}
 </div>
 )}

 {/* Metadata */}
 {viewType === 'dashboard' && activeTab === 'overview' && (
 <>
 <div className="bg-[hsl(var(--bg-secondary))] border border-[hsl(var(--border-primary))] rounded-lg p-4">
 <h3 className="text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-3">Información</h3>
 <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
 <div><p className="text-[hsl(var(--text-secondary))] font-medium">ID</p><p className="text-[hsl(var(--text-primary))] font-bold">{strategy.codigo ? strategy.codigo : `#${strategy.id}`}</p></div>
 <div><p className="text-[hsl(var(--text-secondary))] font-medium">Inicio</p><p className="text-[hsl(var(--text-primary))] font-bold">{formatDate(strategy.start_date)}</p></div>
 <div><p className="text-[hsl(var(--text-secondary))] font-medium">Fin</p><p className="text-[hsl(var(--text-primary))] font-bold">{formatDate(strategy.end_date)}</p></div>
 <div><p className="text-[hsl(var(--text-secondary))] font-medium">Actualización</p><p className="text-[hsl(var(--text-primary))] font-bold">{formatDate(strategy.updated_at)}</p></div>
 <div><p className="text-[hsl(var(--text-secondary))] font-medium">Clase</p><p className="text-[hsl(var(--text-primary))] font-bold capitalize">{strategy.clase_raiz || strategy.typology || '—'}</p></div>
 <div><p className="text-[hsl(var(--text-secondary))] font-medium">Activa</p><p className={`font-bold ${strategy.activa ? 'text-emerald-600' : 'text-[hsl(var(--text-secondary))]'}`}>{strategy.activa ? 'Sí' : 'No'}</p></div>
 </div>
 </div>

 {/* ── Roles Personalizados ── */}
 <div className="bg-[hsl(var(--bg-secondary))] border border-[hsl(var(--border-primary))] rounded-lg p-4">
 <div className="flex items-center justify-between mb-3">
 <h3 className="text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]">Roles Personalizados</h3>
 <button onClick={() => setShowRoleForm(!showRoleForm)}
 className="text-[11px] font-bold text-[hsl(var(--primary))] hover:text-[hsl(var(--primary))] flex items-center gap-1">
 <Plus size={12} />{showRoleForm ? 'Cancelar' : 'Agregar'}
 </button>
 </div>

 <div className="mb-3">
 <label className="block text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1">Rol por defecto</label>
 <select
 value={editDefaultRoleId ?? ''}
 onChange={e => setEditDefaultRoleId(e.target.value ? Number(e.target.value) : null)}
 disabled={customRoles.length === 0}
 className="w-full px-3 py-2 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] text-sm text-[hsl(var(--text-primary))] focus:border-[hsl(var(--primary))] focus:outline-none transition-colors disabled:opacity-60"
 >
 <option value="">Sin rol por defecto</option>
 {customRoles.map(role => (
 <option key={role.id} value={role.id}>
 {role.nombre_rol}
 </option>
 ))}
 </select>
 <p className="mt-1 text-[10px] text-[hsl(var(--text-secondary))]">
 Este rol se usa como base al agregar personas al grupo.
 </p>
 </div>

 {showRoleForm && (
 <div className="mb-3 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg space-y-2">
 <input value={newRoleName} onChange={e => setNewRoleName(e.target.value)}
 placeholder="Nombre del rol (ej: Coordinador de zona)"
 className="w-full px-2.5 py-1.5 text-[12px] bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border-primary))] rounded-lg text-[hsl(var(--text-primary))] outline-none" />
 <input value={newRoleDesc} onChange={e => setNewRoleDesc(e.target.value)}
 placeholder="Descripción (opcional)"
 className="w-full px-2.5 py-1.5 text-[12px] bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border-primary))] rounded-lg text-[hsl(var(--text-primary))] outline-none" />
 <button onClick={async () => {
 if (!newRoleName.trim()) return;
 try {
 await apiFetch(`/evangelism/strategies/${id}/roles`, {
 method: 'POST', token,
 body: { estrategia_id: id, nombre_rol: newRoleName.trim(), descripcion: newRoleDesc || null },
 });
 toast.success('Rol creado');
 setNewRoleName(''); setNewRoleDesc(''); setShowRoleForm(false);
 fetchCustomRoles();
 } catch { toast.error('Error al crear rol'); }
 }} disabled={!newRoleName.trim()}
 className="px-3 py-1.5 text-[11px] font-bold text-white bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))] disabled:opacity-50 rounded-lg transition-colors">
 Crear Rol
 </button>
 </div>
 )}

 {loadingRoles ? (
 <p className="text-[11px] text-[hsl(var(--text-secondary))] italic">Cargando...</p>
 ) : customRoles.length === 0 ? (
 <p className="text-[11px] text-[hsl(var(--text-secondary))] italic">Sin roles personalizados</p>
 ) : (
 <div className="space-y-1.5">
 {customRoles.map(r => (
 <div key={r.id} className="flex items-center justify-between px-2.5 py-1.5 bg-[hsl(var(--bg-primary))] rounded-lg border border-[hsl(var(--border-primary))]">
 <div>
 <div className="flex items-center gap-2">
 <span className="text-[12px] font-semibold text-[hsl(var(--text-primary))] ">{r.nombre_rol}</span>
 {editDefaultRoleId === r.id && (
 <span className="px-1.5 py-0.5 rounded bg-blue-100 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--primary))] dark:bg-blue-900/30 dark:text-blue-300">
 Defecto
 </span>
 )}
 </div>
 {r.descripcion && <p className="text-[10px] text-[hsl(var(--text-secondary))]">{r.descripcion}</p>}
 </div>
 <button onClick={() => requestDeleteRole(r)} className="p-1 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--destructive))] rounded hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors">
 <X size={12} />
 </button>
 </div>
 ))}
 </div>
 )}
 </div>

 {/* ── Seguimiento Pendiente ── */}
 <div className="bg-[hsl(var(--bg-secondary))] border border-[hsl(var(--border-primary))] rounded-lg p-4">
 <div className="flex items-center justify-between mb-3">
 <h3 className="text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]">Seguimiento Pendiente</h3>
 <span className="text-[10px] font-bold px-2 py-0.5 bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 rounded-full">
 {followUps.filter(f => !f.estado_completado).length}
 </span>
 </div>
 {loadingFollowUps ? (
 <p className="text-[11px] text-[hsl(var(--text-secondary))] italic">Cargando...</p>
 ) : followUps.filter(f => !f.estado_completado).length === 0 ? (
 <p className="text-[11px] text-[hsl(var(--text-secondary))] italic">Sin seguimientos pendientes</p>
 ) : (
 <div className="space-y-1.5 max-h-48 overflow-y-auto">
 {followUps.filter(f => !f.estado_completado).slice(0, 10).map(f => (
 <div key={f.id} className="flex items-center justify-between px-2.5 py-1.5 bg-[hsl(var(--bg-primary))] rounded-lg border border-[hsl(var(--border-primary))]">
 <div className="flex items-center gap-2">
 <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full ${f.tipo === 'llamada' ? 'bg-blue-100 text-[hsl(var(--primary))]' : f.tipo === 'visita' ? 'bg-blue-100 text-[hsl(var(--primary))]' : f.tipo === 'oracion' ? 'bg-green-100 text-[hsl(var(--secondary))]' : 'bg-[hsl(var(--bg-muted))] text-[hsl(var(--text-secondary))]'}`}>
 {f.tipo}
 </span>
 <span className="text-[11px] text-[hsl(var(--text-secondary))]">{f.observaciones || '—'}</span>
 </div>
 <button onClick={async () => {
 try {
 await apiFetch(`/evangelism/follow-up/${f.id}`, {
 method: 'PATCH', token,
 body: { estado_completado: true, fecha_seguimiento: new Date().toISOString() },
 });
 toast.success('Seguimiento completado');
 fetchFollowUps();
 } catch { toast.error('Error al actualizar'); }
 }} className="px-2 py-0.5 text-[10px] font-bold text-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-900/20 rounded transition-colors">
 Completar
 </button>
 </div>
 ))}
 </div>
 )}
 </div>
 </>
 )}
 </div>

 {/* ── Group Creation Drawer ── */}
 <WorkspaceDrawer isOpen={isGroupDrawerOpen} onClose={() => setIsGroupDrawerOpen(false)}
 title="Nuevo Grupo" subtitle={`Estrategia: ${strategy?.name}`}
 actions={<>
 <button onClick={() => setIsGroupDrawerOpen(false)}
 className="px-4 py-1.5 text-[12px] font-semibold text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--bg-muted))] rounded-md transition-colors">Cancelar</button>
 <button onClick={handleCreateGroup} disabled={groupSaving || !groupForm.name.trim()}
 className="px-4 py-1.5 text-[12px] font-semibold text-white bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))] disabled:opacity-50 rounded-md transition-colors flex items-center gap-2">
 {groupSaving ? <><Loader2 size={14} className="animate-spin" />Creando...</> : <><Plus size={14} />Crear Grupo</>}
 </button>
 </>}>
 <div className="space-y-4">
 {strategy?.typology === 'relacional' && (
 <div className="px-3 py-2 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg text-[11px] text-[hsl(var(--primary))] dark:text-blue-300">
 <p className="font-semibold">Config. heredada:</p>
 <p>Recurrencia: {strategy.recurrence} · Día: {strategy.day_of_week} · Hora: {strategy.start_time}</p>
 </div>
 )}
 {[
 { label: 'Nombre del grupo *', field: 'name', placeholder: 'Ej: Grupo Norte' },
 { label: 'Zona / Sector', field: 'zone', placeholder: 'Ej: Zona Norte' },
 { label: 'Dirección', field: 'address', placeholder: 'Dirección completa' },
 ].map(({ label, field, placeholder }) => (
 <div key={field}>
 <label className="text-[11px] font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wider mb-2 block">{label}</label>
 <input value={(groupForm as any)[field]} onChange={e => setGroupForm(f => ({ ...f, [field]: e.target.value }))}
 placeholder={placeholder}
 className="w-full px-3 py-2 text-[13px] bg-[hsl(var(--bg-muted))] border border-[hsl(var(--border-primary))] rounded-lg text-[hsl(var(--text-primary))] outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-[hsl(var(--primary))]" />
 </div>
 ))}
 <div>
 <label className="text-[11px] font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wider mb-2 block">Capacidad</label>
 <input type="number" value={groupForm.capacity} onChange={e => setGroupForm(f => ({ ...f, capacity: parseInt(e.target.value) || 15 }))}
 className="w-full px-3 py-2 text-[13px] bg-[hsl(var(--bg-muted))] border border-[hsl(var(--border-primary))] rounded-lg text-[hsl(var(--text-primary))] outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-[hsl(var(--primary))]" />
 </div>
 <div className="grid grid-cols-3 gap-2">
 <div>
 <label className="text-[11px] font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wider mb-2 block">Día</label>
 <select value={groupForm.day_of_week} onChange={e => setGroupForm(f => ({ ...f, day_of_week: e.target.value }))}
 className="w-full px-2 py-2 text-[12px] bg-[hsl(var(--bg-muted))] border border-[hsl(var(--border-primary))] rounded-lg text-[hsl(var(--text-primary))] outline-none">
 <option value="">—</option>
 {['Domingo','Lunes','Martes','Miércoles','Jueves','Viernes','Sábado'].map(d => <option key={d} value={d}>{d}</option>)}
 </select>
 </div>
 <div>
 <label className="text-[11px] font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wider mb-2 block">Inicio</label>
 <input type="time" value={groupForm.start_time} onChange={e => setGroupForm(f => ({ ...f, start_time: e.target.value }))}
 className="w-full px-2 py-2 text-[12px] bg-[hsl(var(--bg-muted))] border border-[hsl(var(--border-primary))] rounded-lg text-[hsl(var(--text-primary))] outline-none" />
 </div>
 <div>
 <label className="text-[11px] font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wider mb-2 block">Fin</label>
 <input type="time" value={groupForm.end_time} onChange={e => setGroupForm(f => ({ ...f, end_time: e.target.value }))}
 className="w-full px-2 py-2 text-[12px] bg-[hsl(var(--bg-muted))] border border-[hsl(var(--border-primary))] rounded-lg text-[hsl(var(--text-primary))] outline-none" />
 </div>
 </div>
 {customRoles.length === 0 ? (
 <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-[12px] font-medium text-amber-700 dark:border-amber-500/20 dark:bg-amber-500/10 dark:text-amber-300">
 Esta estrategia no tiene roles definidos. El grupo se creará sin cargos de servicio por defecto.
 </div>
 ) : customRoles.map((role) => {
 const field = customRoleValue(role);
 const label = role.nombre_rol;
 const selectedId = groupRoleAssignments[field] || null;
 const selectedPersona = selectedId ? personaCache[selectedId] : null;
 const selectedName = selectedPersona
 ? (selectedPersona.nombre_completo || `${selectedPersona.first_name ?? ''} ${selectedPersona.last_name ?? ''}`.trim())
 : '';
 const query = roleSearch[field] || '';
 const results = roleResults[field] || [];
 const isLoading = Boolean(roleLoading[field]);
 return (
 <div key={field} className="relative">
 <label className="text-[11px] font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wider mb-2 block">{label}</label>
 <div className="relative">
 <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))] pointer-events-none" />
 <input
 type="text"
 placeholder={selectedName || `Buscar ${label.toLowerCase()}...`}
 value={roleDropdown === field ? query : selectedName}
 onFocus={() => {
 setRoleDropdown(field);
 setRoleSearch(s => ({ ...s, [field]: '' }));
 }}
 onBlur={() => setTimeout(() => setRoleDropdown(null), 150)}
 onChange={e => setRoleSearch(s => ({ ...s, [field]: e.target.value }))}
 className="w-full pl-8 pr-3 py-2 text-[13px] bg-[hsl(var(--bg-muted))] border border-[hsl(var(--border-primary))] rounded-lg text-[hsl(var(--text-primary))] outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-[hsl(var(--primary))]"
 />
 {selectedId && (
 <button
 type="button"
 onClick={() => { setGroupRoleAssignments(f => ({ ...f, [field]: null })); setRoleDropdown(null); }}
 className="absolute right-2 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-secondary))] dark:hover:text-[hsl(var(--text-primary))]"
 >
 <X size={13} />
 </button>
 )}
 </div>
 {roleDropdown === field && (
 <div className="absolute z-50 mt-1 w-full bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] border border-[hsl(var(--border-primary))] rounded-lg shadow-xl max-h-48 overflow-y-auto">
 <button
 type="button"
 onMouseDown={() => { setGroupRoleAssignments(f => ({ ...f, [field]: null })); setRoleDropdown(null); }}
 className="w-full text-left px-3 py-2 text-[12px] text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--bg-muted))] dark:hover:bg-white/5 border-b border-[hsl(var(--border-primary))]"
 >
 Sin asignar
 </button>
 {isLoading ? (
 <div className="px-3 py-3 text-[12px] text-[hsl(var(--text-secondary))] text-center">Buscando...</div>
 ) : results.length === 0 ? (
 <div className="px-3 py-3 text-[12px] text-[hsl(var(--text-secondary))] text-center">Sin resultados</div>
 ) : results.map(m => {
 const name = m.nombre_completo || `${m.first_name ?? ''} ${m.last_name ?? ''}`.trim();
 return (
 <button
 key={m.id}
 type="button"
 onMouseDown={() => {
 setPersonaCache(c => ({ ...c, [m.id]: m }));
 setGroupRoleAssignments(f => ({ ...f, [field]: m.id }));
 setRoleDropdown(null);
 setRoleSearch(s => ({ ...s, [field]: '' }));
 }}
 className="w-full text-left px-3 py-2 text-[12px] text-[hsl(var(--text-primary))] hover:bg-[hsl(var(--bg-muted))] dark:hover:bg-white/5 flex items-center justify-between gap-2"
 >
 <span className="font-medium">{name}</span>
 {m.church_role && <span className="text-[10px] text-[hsl(var(--text-secondary))] shrink-0">{m.church_role}</span>}
 </button>
 );
 })}
 </div>
 )}
 </div>
 );
 })}
 </div>
 </WorkspaceDrawer>

 {/* ── Persona Management Drawer ── */}
 <WorkspaceDrawer isOpen={isPersonaDrawerOpen} onClose={() => setIsPersonaDrawerOpen(false)}
 title="Gestionar Personas" subtitle={selectedGroup?.name || ''}
 actions={<>
 <button onClick={() => setIsPersonaDrawerOpen(false)}
 className="px-4 py-1.5 text-[12px] font-semibold text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--bg-muted))] rounded-md transition-colors">Cancelar</button>
 <button onClick={handleSavePersonas} disabled={personaSaving}
 className="px-4 py-1.5 text-[12px] font-semibold text-white bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))] disabled:opacity-50 rounded-md transition-colors flex items-center gap-2">
 {personaSaving ? <><Loader2 size={14} className="animate-spin" />Guardando...</> : <><UserCheck size={14} />Guardar ({groupPersonas.length})</>}
 </button>
 </>}>
 <div ref={personaSplitRef} className="flex flex-col" style={{ height: 'calc(100vh - 16rem)' }}>
 {/* Panel superior: personas asignadas */}
 <div className="overflow-y-auto shrink-0 pb-2" style={{ height: personaSplitHeight }}>
 <label className="text-[11px] font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wider block mb-2">
 Personas ({groupPersonas.length})
 </label>
 {groupPersonas.length === 0 ? (
 <p className="text-xs text-[hsl(var(--text-secondary))] italic py-2">Sin personas asignados</p>
 ) : (
 <div className="space-y-1.5">
 {groupPersonas.map(m => (
 <div key={m.id} className="flex items-center gap-2 px-2 py-1.5 bg-[hsl(var(--bg-muted))] rounded-md">
 <div className="flex-1 min-w-0">
 <span className="text-xs font-medium text-[hsl(var(--text-primary))] truncate block">{m.name}</span>
 </div>
 <RoleSelect
 value={m.role}
 options={personaRoleOptions}
 colorClass={getRoleColor(m.role)}
 onChange={v => updateGroupPersonaRole(m.id, v)}
 />
 <button onClick={() => removePersonaFromGroup(m.id)}
 className="p-1 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--destructive))] hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-colors">
 <UserMinus size={13} />
 </button>
 </div>
 ))}
 </div>
 )}
 </div>

 {/* Divisor arrastrable */}
 <div
 onMouseDown={handlePersonaSplitDrag}
 className="shrink-0 h-4 flex items-center justify-center cursor-row-resize group select-none border-y border-[hsl(var(--border-primary))] hover:border-blue-300 dark:hover:border-blue-500/40 transition-colors"
 title="Arrastra para ajustar el espacio"
 >
 <div className="w-12 h-1 rounded-full bg-[hsl(var(--bg-muted))] group-hover:bg-[hsl(var(--primary))] dark:group-hover:bg-[hsl(var(--primary))] transition-colors" />
 </div>

 {/* Panel inferior: agregar personas */}
 <div className="flex-1 min-h-0 flex flex-col pt-3">
 <label className="text-[11px] font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wider mb-2 block shrink-0">Agregar personas</label>
 <div className="relative mb-2 shrink-0">
 {personaSearchLoading
 ? <Loader2 size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[hsl(var(--primary))] animate-spin" />
 : <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]" />}
 <input value={personaSearch}
 onChange={e => setPersonaSearch(e.target.value)}
 placeholder="Filtrar por nombre..."
 className="w-full pl-9 pr-3 py-2 text-[12px] bg-[hsl(var(--bg-muted))] border border-[hsl(var(--border-primary))] rounded-lg text-[hsl(var(--text-primary))] outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-[hsl(var(--primary))]" />
 </div>
 <div className="flex-1 min-h-0 overflow-y-auto space-y-1">
 {(() => {
 if (personaSearchLoading) return (
 <p className="text-[11px] text-[hsl(var(--text-secondary))] text-center py-3">Cargando personas...</p>
 );
 const norm = (s: string) => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
 const q = norm(personaSearch.trim());
 const notInGroup = allPersonas.filter(m => !groupPersonas.find(gm => String(gm.id) === String(m.id)));
 const available = q
 ? notInGroup
 .filter(m => {
 const name = norm(m.nombre_completo || `${m.first_name ?? ''} ${m.last_name ?? ''}`);
 return name.split(/\s+/).some(word => word.startsWith(q));
 })
 .sort((a, b) => {
 const aFirst = norm(a.first_name || '').startsWith(q);
 const bFirst = norm(b.first_name || '').startsWith(q);
 if (aFirst !== bFirst) return aFirst ? -1 : 1;
 const aName = norm(a.nombre_completo || `${a.first_name ?? ''} ${a.last_name ?? ''}`);
 const bName = norm(b.nombre_completo || `${b.first_name ?? ''} ${b.last_name ?? ''}`);
 return aName.localeCompare(bName, 'es');
 })
 : notInGroup;
 if (allPersonas.length === 0) return (
 <p className="text-[11px] text-[hsl(var(--text-secondary))] text-center py-3">Sin personas en el sistema</p>
 );
 if (available.length === 0) return (
 <p className="text-[11px] text-[hsl(var(--text-secondary))] text-center py-3">
 {q ? 'Sin coincidencias' : 'Todas las personas ya están en el grupo'}
 </p>
 );
 return available.map(m => (
 <button key={m.id} onClick={() => addPersonaToGroup(m)}
 className="w-full flex items-center justify-between px-2 py-1.5 hover:bg-[hsl(var(--bg-muted))] dark:hover:bg-white/5 rounded-md text-xs text-left transition-colors group/add">
 <span className="font-medium text-[hsl(var(--text-primary))]">{m.nombre_completo || `${m.first_name ?? ''} ${m.last_name ?? ''}`.trim()}
 {m.email && <span className="text-[hsl(var(--text-secondary))] ml-2">{m.email}</span>}
 </span>
 <Plus size={14} className="text-[hsl(var(--text-secondary))] group-hover/add:text-[hsl(var(--primary))] transition-colors" />
 </button>
 ));
 })()}
 </div>
 </div>
 </div>
 </WorkspaceDrawer>

 {/* ── New Session Drawer ── */}
 <WorkspaceDrawer isOpen={isNewSessionDrawerOpen} onClose={() => setIsNewSessionDrawerOpen(false)}
 title="Registrar Sesión" subtitle={`Estrategia: ${strategy?.name}`}
 actions={<>
 <button onClick={() => setIsNewSessionDrawerOpen(false)}
 className="px-4 py-1.5 text-[12px] font-semibold text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--bg-muted))] rounded-md transition-colors">Cancelar</button>
 <button onClick={handleCreateSession} disabled={sessionSaving}
 className="px-4 py-1.5 text-[12px] font-semibold text-white bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))] disabled:opacity-50 rounded-md transition-colors flex items-center gap-2">
 {sessionSaving ? <><Loader2 size={14} className="animate-spin" />Guardando...</> : <><Save size={14} />Guardar</>}
 </button>
 </>}>
 <div className="space-y-4">
 <div>
 <label className="text-[11px] font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wider mb-2 block">Grupo *</label>
 <select value={sessionForm.grupo_id} onChange={e => setSessionForm(f => ({ ...f, grupo_id: e.target.value }))}
 className="w-full px-3 py-2 text-[13px] bg-[hsl(var(--bg-muted))] border border-[hsl(var(--border-primary))] rounded-lg text-[hsl(var(--text-primary))] outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-[hsl(var(--primary))]">
 <option value="">Seleccionar grupo...</option>
 {groups.map(g => <option key={g.id} value={g.id}>{g.name}</option>)}
 </select>
 </div>
 <div>
 <label className="text-[11px] font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wider mb-2 block">Fecha de la sesión *</label>
 <input type="date" value={sessionForm.session_date} onChange={e => setSessionForm(f => ({ ...f, session_date: e.target.value }))}
 className="w-full px-3 py-2 text-[13px] bg-[hsl(var(--bg-muted))] border border-[hsl(var(--border-primary))] rounded-lg text-[hsl(var(--text-primary))] outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-[hsl(var(--primary))]" />
 </div>
 <div>
 <label className="text-[11px] font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wider mb-2 block">Tema de la sesión</label>
 <input value={sessionForm.topic} onChange={e => setSessionForm(f => ({ ...f, topic: e.target.value }))}
 placeholder="Ej: La fe que mueve montañas"
 className="w-full px-3 py-2 text-[13px] bg-[hsl(var(--bg-muted))] border border-[hsl(var(--border-primary))] rounded-lg text-[hsl(var(--text-primary))] outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-[hsl(var(--primary))]" />
 </div>
 <div>
 <label className="text-[11px] font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wider mb-2 block">Ofrenda recogida</label>
 <input type="number" value={sessionForm.offering_amount} onChange={e => setSessionForm(f => ({ ...f, offering_amount: e.target.value }))}
 placeholder="0.00"
 className="w-full px-3 py-2 text-[13px] bg-[hsl(var(--bg-muted))] border border-[hsl(var(--border-primary))] rounded-lg text-[hsl(var(--text-primary))] outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-[hsl(var(--primary))]" />
 </div>
 <div>
 <label className="text-[11px] font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wider mb-2 block">Notas de la sesión</label>
 <textarea value={sessionForm.report_notes} onChange={e => setSessionForm(f => ({ ...f, report_notes: e.target.value }))} rows={3}
 placeholder="Observaciones, peticiones de oración, novedades..."
 className="w-full px-3 py-2 text-[13px] bg-[hsl(var(--bg-muted))] border border-[hsl(var(--border-primary))] rounded-lg text-[hsl(var(--text-primary))] outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-[hsl(var(--primary))] resize-none" />
 </div>
 </div>
 </WorkspaceDrawer>

 {/* ── Attendance Drawer ── */}
 <WorkspaceDrawer isOpen={isAttendanceDrawerOpen} onClose={() => setIsAttendanceDrawerOpen(false)}
 title="Registrar Asistencia"
 subtitle={attendanceSession ? new Date(attendanceSession.session_date.split('T')[0] + 'T12:00:00').toLocaleDateString('es-CO', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }) : ''}
 actions={<>
 <button onClick={() => setIsAttendanceDrawerOpen(false)}
 className="px-4 py-1.5 text-[12px] font-semibold text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--bg-muted))] rounded-md transition-colors">Cancelar</button>
 <button onClick={handleSaveAttendance} disabled={attendanceSaving}
 className="px-4 py-1.5 text-[12px] font-semibold text-white bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))] disabled:opacity-50 rounded-md transition-colors flex items-center gap-2">
 {attendanceSaving ? <><Loader2 size={14} className="animate-spin" />Guardando...</> : <><UserCheck size={14} />Guardar asistencia</>}
 </button>
 </>}>
 <div className="space-y-3">
 {attendancePersonas.length === 0 && !showVisitorSearch ? (
 <div className="text-center py-8">
 <Users size={32} className="text-[hsl(var(--text-secondary))] mx-auto mb-2" />
 <p className="text-xs text-[hsl(var(--text-secondary))]">Este grupo no tiene personas asignados</p>
 <p className="text-[11px] text-[hsl(var(--text-secondary))] mt-1">Agrega personas desde la pestaña Grupos</p>
 </div>
 ) : (
 <>
 {attendancePersonas.length > 0 && (
 <div className="flex items-center gap-2 text-[11px] text-[hsl(var(--text-secondary))] mb-1">
 <span>{attendancePersonas.filter(m => m.status === 'present').length} presentes</span>
 <span>·</span>
 <span>{attendancePersonas.filter(m => m.status === 'absent').length} ausentes</span>
 <span>·</span>
 <span className="text-[hsl(var(--primary))]">{attendancePersonas.filter(m => m.status === 'first_time').length} primera vez</span>
 </div>
 )}
 <div className="space-y-2">
 {attendancePersonas.map((m, i) => (
 <div key={m.persona_id} className={`flex items-center gap-3 px-3 py-2.5 rounded-lg ${m.status === 'first_time' ? 'bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800' : 'bg-[hsl(var(--bg-muted))]'}`}>
 <div className="flex-1 min-w-0">
 <div className="flex items-center gap-1.5">
 <p className="text-xs font-semibold text-[hsl(var(--text-primary))] ">{m.name}</p>
 {m.status === 'first_time' && <span className="text-[9px] font-bold px-1 py-0.5 rounded bg-[hsl(var(--primary))] text-white">1ª vez</span>}
 </div>
 <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${getRoleColor(m.role)}`}>
 {getRoleLabel(m.role, m.role_label)}
 </span>
 </div>
 <div className="flex items-center gap-1">
 {[
 { status: 'present', label: 'P', cls: 'bg-green-100 text-[hsl(var(--secondary))] dark:bg-green-900/30 dark:text-[hsl(var(--secondary))]', activeCls: 'ring-2 ring-green-500' },
 { status: 'absent', label: 'A', cls: 'bg-red-100 text-[hsl(var(--destructive))] dark:bg-red-900/30 dark:text-[hsl(var(--destructive))]', activeCls: 'ring-2 ring-red-500' },
 { status: 'first_time', label: '1°', cls: 'bg-blue-100 text-[hsl(var(--primary))] dark:bg-blue-900/30 dark:text-[hsl(var(--primary))]', activeCls: 'ring-2 ring-blue-500' },
 ].map(opt => (
 <button key={opt.status}
 onClick={() => setAttendancePersonas(prev => prev.map((x, j) => j === i ? { ...x, status: opt.status as any } : x))}
 className={`w-8 h-8 rounded-lg text-[11px] font-bold transition-all ${opt.cls} ${m.status === opt.status ? opt.activeCls : 'opacity-50 hover:opacity-100'}`}>
 {opt.label}
 </button>
 ))}
 {m.role === 'visitante' && (
 <button onClick={() => setAttendancePersonas(prev => prev.filter((_, j) => j !== i))}
 className="w-7 h-7 ml-1 flex items-center justify-center rounded-lg text-[hsl(var(--text-secondary))] hover:bg-red-50 hover:text-[hsl(var(--destructive))] dark:hover:bg-red-900/20 transition-colors">
 <X size={12} />
 </button>
 )}
 </div>
 </div>
 ))}
 </div>
 </>
 )}

 {/* Agregar visitante */}
 <div className="pt-2 border-t border-[hsl(var(--border-primary))]">
 {!showVisitorSearch && !showNewVisitorForm ? (
 <div className="flex gap-2">
 <button onClick={() => setShowVisitorSearch(true)}
 className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg border border-dashed border-[hsl(var(--border-primary))] dark:border-white/20 text-xs text-[hsl(var(--text-secondary))] hover:border-blue-400 hover:text-[hsl(var(--primary))] dark:hover:border-blue-700 dark:hover:text-[hsl(var(--primary))] transition-colors">
 <Search size={13} />Buscar existente
 </button>
 <button onClick={() => setShowNewVisitorForm(true)}
 className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg border border-dashed border-[hsl(var(--border-primary))] dark:border-white/20 text-xs text-[hsl(var(--text-secondary))] hover:border-green-400 hover:text-[hsl(var(--secondary))] dark:hover:border-green-700 dark:hover:text-[hsl(var(--secondary))] transition-colors">
 <UserPlus size={13} />Crear persona nueva
 </button>
 </div>
 ) : showVisitorSearch ? (
 <div className="space-y-2">
 <div className="flex items-center gap-2">
 <div className="relative flex-1">
 <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]" />
 <input
 autoFocus
 value={visitorSearch}
 onChange={e => setVisitorSearch(e.target.value)}
 placeholder="Buscar persona por nombre..."
 className="w-full pl-8 pr-3 py-2 text-[12px] bg-[hsl(var(--bg-muted))] border border-[hsl(var(--border-primary))] rounded-lg text-[hsl(var(--text-primary))] outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-[hsl(var(--primary))]"
 />
 </div>
 <button onClick={() => { setShowVisitorSearch(false); setVisitorSearch(''); }}
 className="w-8 h-8 flex items-center justify-center rounded-lg text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--bg-muted))] dark:hover:bg-white/10">
 <X size={14} />
 </button>
 </div>
 {visitorSearch.trim().length >= 2 && (
 <div className="max-h-40 overflow-y-auto space-y-1 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] p-1">
 {allPersonas
 .filter(m => {
 const name = (m.nombre_completo || `${m.first_name ?? ''} ${m.last_name ?? ''}`).toLowerCase();
 return name.includes(visitorSearch.toLowerCase()) &&
 !attendancePersonas.find(a => a.persona_id === m.id);
 })
 .slice(0, 8)
 .map(m => (
 <button key={m.id}
 onClick={() => {
 setAttendancePersonas(prev => [...prev, {
 persona_id: m.id,
 name: m.nombre_completo || `${m.first_name ?? ''} ${m.last_name ?? ''}`.trim(),
 role: 'visitante',
 role_label: 'Visitante',
 status: 'first_time',
 notes: '',
 }]);
 setVisitorSearch('');
 setShowVisitorSearch(false);
 }}
 className="w-full text-left px-3 py-2 rounded-md text-xs text-[hsl(var(--text-primary))] hover:bg-[hsl(var(--bg-muted))] flex items-center gap-2 transition-colors">
 <UserPlus size={12} className="text-[hsl(var(--primary))] shrink-0" />
 <span className="font-medium">{m.nombre_completo || `${m.first_name ?? ''} ${m.last_name ?? ''}`.trim()}</span>
 {m.church_role && <span className="text-[hsl(var(--text-secondary))] text-[10px]">({m.church_role})</span>}
 </button>
 ))}
 {allPersonas.filter(m => {
 const name = (m.nombre_completo || `${m.first_name ?? ''} ${m.last_name ?? ''}`).toLowerCase();
 return name.includes(visitorSearch.toLowerCase()) && !attendancePersonas.find(a => a.persona_id === m.id);
 }).length === 0 && (
 <p className="text-center py-3 text-xs text-[hsl(var(--text-secondary))]">No se encontraron personas</p>
 )}
 </div>
 )}
 </div>
 ) : (
 /* Formulario crear persona nueva */
 <div className="space-y-3 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-muted))] dark:bg-black/20 p-3">
 <div className="flex items-center justify-between mb-1">
 <span className="text-[11px] font-semibold text-[hsl(var(--text-primary))] uppercase tracking-wide">Nueva persona visitante</span>
 <button onClick={() => { setShowNewVisitorForm(false); setNewVisitorForm({ first_name: '', last_name: '', phone: '', whatsapp: '', email: '', address: '' }); }}
 className="w-6 h-6 flex items-center justify-center rounded text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--bg-primary))] dark:hover:bg-white/10">
 <X size={13} />
 </button>
 </div>
 <div className="grid grid-cols-2 gap-2">
 <div>
 <label className="block text-[10px] text-[hsl(var(--text-secondary))] mb-0.5">Nombres</label>
 <input value={newVisitorForm.first_name} onChange={e => setNewVisitorForm(p => ({ ...p, first_name: e.target.value }))}
 placeholder="Opcional"
 className="w-full py-1.5 px-2 text-[12px] bg-[hsl(var(--bg-primary))] dark:bg-black/30 border border-[hsl(var(--border-primary))] rounded-md text-[hsl(var(--text-primary))] outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]" />
 </div>
 <div>
 <label className="block text-[10px] text-[hsl(var(--text-secondary))] mb-0.5">Apellidos</label>
 <input value={newVisitorForm.last_name} onChange={e => setNewVisitorForm(p => ({ ...p, last_name: e.target.value }))}
 placeholder="Opcional"
 className="w-full py-1.5 px-2 text-[12px] bg-[hsl(var(--bg-primary))] dark:bg-black/30 border border-[hsl(var(--border-primary))] rounded-md text-[hsl(var(--text-primary))] outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]" />
 </div>
 <div>
 <label className="block text-[10px] text-[hsl(var(--text-secondary))] mb-0.5">Teléfono</label>
 <input value={newVisitorForm.phone} onChange={e => setNewVisitorForm(p => ({ ...p, phone: e.target.value }))}
 placeholder="Opcional" type="tel"
 className="w-full py-1.5 px-2 text-[12px] bg-[hsl(var(--bg-primary))] dark:bg-black/30 border border-[hsl(var(--border-primary))] rounded-md text-[hsl(var(--text-primary))] outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]" />
 </div>
 <div>
 <label className="block text-[10px] text-[hsl(var(--text-secondary))] mb-0.5">WhatsApp</label>
 <input value={newVisitorForm.whatsapp} onChange={e => setNewVisitorForm(p => ({ ...p, whatsapp: e.target.value }))}
 placeholder="Opcional" type="tel"
 className="w-full py-1.5 px-2 text-[12px] bg-[hsl(var(--bg-primary))] dark:bg-black/30 border border-[hsl(var(--border-primary))] rounded-md text-[hsl(var(--text-primary))] outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]" />
 </div>
 <div className="col-span-2">
 <label className="block text-[10px] text-[hsl(var(--text-secondary))] mb-0.5">Email</label>
 <input value={newVisitorForm.email} onChange={e => setNewVisitorForm(p => ({ ...p, email: e.target.value }))}
 placeholder="Opcional" type="email"
 className="w-full py-1.5 px-2 text-[12px] bg-[hsl(var(--bg-primary))] dark:bg-black/30 border border-[hsl(var(--border-primary))] rounded-md text-[hsl(var(--text-primary))] outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]" />
 </div>
 <div className="col-span-2">
 <label className="block text-[10px] text-[hsl(var(--text-secondary))] mb-0.5">Dirección</label>
 <input value={newVisitorForm.address} onChange={e => setNewVisitorForm(p => ({ ...p, address: e.target.value }))}
 placeholder="Opcional"
 className="w-full py-1.5 px-2 text-[12px] bg-[hsl(var(--bg-primary))] dark:bg-black/30 border border-[hsl(var(--border-primary))] rounded-md text-[hsl(var(--text-primary))] outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]" />
 </div>
 </div>
 <button onClick={handleCreateNewVisitor} disabled={savingNewVisitor}
 className="w-full py-2 rounded-lg text-[12px] font-semibold text-white bg-[hsl(var(--secondary))] hover:bg-[hsl(var(--secondary))] disabled:opacity-50 transition-colors flex items-center justify-center gap-2">
 {savingNewVisitor ? <><Loader2 size={13} className="animate-spin" />Guardando...</> : <><UserPlus size={13} />Registrar visitante</>}
 </button>
 </div>
 )}
 </div>
 </div>
 </WorkspaceDrawer>
 <ConfirmActionDrawer action={confirmAction} onClose={() => setConfirmAction(null)} />
 </EvangelismShell>
 );
}
