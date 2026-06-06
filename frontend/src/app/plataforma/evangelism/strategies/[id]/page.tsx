"use client";

import EvangelismShell from '@/components/evangelism/EvangelismShell';
import ConfirmActionDrawer, { type ConfirmActionState } from '@/components/evangelism/ConfirmActionDrawer';
import UniversalCalendarView from '@/components/ui/UniversalCalendarView';
import UniversalGanttView from '@/components/ui/UniversalGanttView';
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
Flame,
FolderOpen,
Home,
Plus,
Save,
Search,
Sparkles,
Trash2,
UserCheck,
UserMinus,
UserPlus,
Users,
X
} from 'lucide-react';
import { useParams,useRouter } from 'next/navigation';
import { useCallback,useEffect,useState } from 'react';
import { toast } from 'sonner';

interface Strategy {
    id: string;
    name: string;
    description: string;
    codigo?: string;
    clase_raiz?: string;
    activa: boolean;
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
    id: number;
    asistencia_id: number;
    tipo: string;
    fecha_programada?: string;
    fecha_realizada?: string;
    notas?: string;
    completado: boolean;
    resultado?: string;
}

interface StrategyGroup {
    id: number;
    name: string;
    zone: string | null;
    leader_name: string | null;
    members_count: number;
}

type HabilitacionEstado = 'DESHABILITADO' | 'HABILITADO' | 'CERRADO' | 'CANCELADA';

interface SessionRow {
    id: number;
    grupo_id: number;
    session_date: string;
    status: string;
    estado_habilitacion?: HabilitacionEstado;
    topic?: string | null;
    offering_amount?: number | null;
    report_notes?: string | null;
}

interface AttendanceMember {
    persona_id: string;
    name: string;
    role: string;
    status: 'present' | 'absent' | 'first_time';
    notes?: string;
}

type TabId = 'overview' | 'groups' | 'sessions' | 'metrics';

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

const MEMBER_ROLES = [
    { value: 'lider', label: 'Líder' },
    { value: 'colider', label: 'Colíder' },
    { value: 'persona', label: 'Persona' },
    { value: 'visitante', label: 'Visitante' },
];

const ROLE_COLORS: Record<string, string> = {
    lider: 'bg-blue-100 text-[hsl(var(--primary))] dark:bg-blue-900/30 dark:text-blue-300',
    colider: 'bg-blue-100 text-[hsl(var(--primary))] dark:bg-blue-900/30 dark:text-blue-300',
    persona: 'bg-slate-100 text-slate-600 dark:bg-white/10 dark:text-slate-300',
    visitante: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
    asistente: 'bg-slate-100 text-slate-600 dark:bg-white/10 dark:text-slate-300',
};

const TABS: { id: TabId; label: string; icon: typeof Users }[] = [
    { id: 'overview', label: 'General', icon: Sparkles },
    { id: 'groups', label: 'Grupos', icon: FolderOpen },
    { id: 'sessions', label: 'Sesiones', icon: Calendar },
    { id: 'metrics', label: 'Métricas', icon: BarChart3 },
];

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
    const [memberCache, setMemberCache] = useState<Record<string, any>>({});
    const [roleResults, setRoleResults] = useState<Record<'leader_id'|'assistant_id'|'host_id', any[]>>({ leader_id: [], assistant_id: [], host_id: [] });
    const [roleLoading, setRoleLoading] = useState<Record<'leader_id'|'assistant_id'|'host_id', boolean>>({ leader_id: false, assistant_id: false, host_id: false });

    // Group creation drawer
    const [isGroupDrawerOpen, setIsGroupDrawerOpen] = useState(false);
    const [groupForm, setGroupForm] = useState({
        name: '', zone: '', address: '', capacity: 15,
        day_of_week: '', start_time: '', end_time: '',
        leader_id: null as string | null,
        assistant_id: null as string | null,
        host_id: null as string | null,
    });
    const [groupSaving, setGroupSaving] = useState(false);
    const [roleSearch, setRoleSearch] = useState({ leader_id: '', assistant_id: '', host_id: '' });
    const [roleDropdown, setRoleDropdown] = useState<'leader_id' | 'assistant_id' | 'host_id' | null>(null);

    // Member management drawer
    const [isMemberDrawerOpen, setIsMemberDrawerOpen] = useState(false);
    const [selectedGroup, setSelectedGroup] = useState<StrategyGroup | null>(null);
    const [groupMembers, setGroupMembers] = useState<{ id: string; name: string; email: string; role: string }[]>([]);
    const [allMembers, setAllMembers] = useState<any[]>([]);
    const [memberSearch, setMemberSearch] = useState('');
    const [memberSaving, setMemberSaving] = useState(false);

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
    const [attendanceMembers, setAttendanceMembers] = useState<AttendanceMember[]>([]);
    const [attendanceSaving, setAttendanceSaving] = useState(false);
    const [isAttendanceDrawerOpen, setIsAttendanceDrawerOpen] = useState(false);

    // Session menu
    const [sessionMenuId, setSessionMenuId] = useState<number | null>(null);
    const [sessionGroupFilter, setSessionGroupFilter] = useState<number | 'all'>('all');

    // Visitor search (in attendance drawer)
    const [showVisitorSearch, setShowVisitorSearch] = useState(false);
    const [visitorSearch, setVisitorSearch] = useState('');
    useEffect(() => {
        if (sessionMenuId === null) return;
        const close = () => setSessionMenuId(null);
        document.addEventListener('click', close);
        return () => document.removeEventListener('click', close);
    }, [sessionMenuId]);

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
        try {
            const all = await apiFetch<StrategyGroup[]>('/evangelism/grupos', { token, query: { estrategia_id: id } });
            setGroups(all || []);
        } catch { toast.error('Error al cargar grupos'); }
    }, [id, token]);

    // Cargar grupos al montar para que aparezcan en el sidebar
    useEffect(() => {
        if (token) fetchGroups();
    }, [fetchGroups, token]);

    const fetchMetrics = useCallback(async () => {
        try {
            const m = await apiFetch<any>(`/evangelism/strategies/${id}/metrics`, { token });
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
    }, [activeTab, fetchGroups, fetchMetrics, fetchSessions]);

    useEffect(() => {
        if (!roleDropdown) return;
        const field = roleDropdown;
        const query = roleSearch[field].trim();
        setRoleLoading(l => ({ ...l, [field]: true }));
        const timer = setTimeout(async () => {
            try {
                const params: Record<string, any> = query.length >= 1
                    ? { limit: 50, search: query }
                    : { limit: 100, sort_by: 'first_name', sort_dir: 'asc' };
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
            leader_id: null, assistant_id: null, host_id: null,
        });
        setRoleSearch({ leader_id: '', assistant_id: '', host_id: '' });
        setRoleResults({ leader_id: [], assistant_id: [], host_id: [] });
        setRoleLoading({ leader_id: false, assistant_id: false, host_id: false });
        setRoleDropdown(null);
        setIsGroupDrawerOpen(true);
    };

    const handleCreateGroup = async () => {
        if (!groupForm.name.trim()) { toast.error('El nombre del grupo es obligatorio'); return; }
        setGroupSaving(true);
        try {
            await apiFetch('/evangelism/grupos', {
                method: 'POST', token,
                body: {
                    name: groupForm.name.trim(),
                    code: null,
                    zone: groupForm.zone || null,
                    address: groupForm.address || null,
                    latitude: null, longitude: null,
                    leader_name: null,
                    leader_id: groupForm.leader_id,
                    assistant_id: groupForm.assistant_id,
                    host_id: groupForm.host_id,
                    estrategia_id: id,
                    members_count: 0, capacity: groupForm.capacity,
                    status: 'Activo',
                    day_of_week: groupForm.day_of_week || null,
                    start_time: groupForm.start_time || null,
                    end_time: groupForm.end_time || null,
                },
            });
            toast.success('Grupo creado');
            setIsGroupDrawerOpen(false);
            fetchGroups(); fetchStrategy();
        } catch (e: any) {
            toast.error('Error al crear: ' + (e.message || 'Intente de nuevo'));
        } finally { setGroupSaving(false); }
    };

    const handleDeleteGroup = async (groupId: number, groupName: string) => {
        try {
            await apiFetch(`/evangelism/grupos/${groupId}`, { method: 'DELETE', token });
            toast.success('Grupo eliminado');
            fetchGroups(); fetchStrategy();
        } catch { toast.error('Error al eliminar'); }
    };

    const requestDeleteGroup = (groupId: number, groupName: string) => {
        setConfirmAction({
            title: 'Eliminar grupo',
            description: `Se eliminara "${groupName}" y todo su historial de asistencia.`,
            confirmLabel: 'Eliminar',
            destructive: true,
            onConfirm: () => handleDeleteGroup(groupId, groupName),
        });
    };

    // ── Member management ──
    const openMemberDrawer = async (group: StrategyGroup) => {
        setSelectedGroup(group);
        setIsMemberDrawerOpen(true);
        setMemberSearch('');
        setAllMembers([]);
        try {
            const house = await apiFetch<any>(`/evangelism/grupos/${group.id}`, { token });
            setGroupMembers(house?.base_attendees?.map((a: any) => ({
                id: a.persona_id,
                name: a.name || a.member?.nombre_completo || '',
                email: a.member?.email || '',
                role: a.role || 'persona',
            })) || []);
        } catch { setGroupMembers([]); }
    };

    // Búsqueda en tiempo real de personas para agregar al grupo
    useEffect(() => {
        if (!isMemberDrawerOpen) return;
        const query = memberSearch.trim();
        const timer = setTimeout(async () => {
            try {
                const params: Record<string, any> = query.length >= 1
                    ? { limit: 50, search: query }
                    : { limit: 2000, sort_by: 'first_name', sort_dir: 'asc' };
                const res = await apiFetch<any[]>('/crm/personas', { token, query: params });
                setAllMembers(res || []);
            } catch { /* silently keep previous results */ }
        }, query.length >= 1 ? 300 : 0);
        return () => clearTimeout(timer);
    }, [memberSearch, isMemberDrawerOpen, token]);

    const handleSaveMembers = async () => {
        if (!selectedGroup) return;
        setMemberSaving(true);
        try {
            await apiFetch(`/evangelism/grupos/${selectedGroup.id}`, {
                method: 'PUT', token,
                body: {
                    base_attendees_with_roles: groupMembers.map(m => ({
                        persona_id: m.id,
                        role: m.role,
                    })),
                },
            });
            toast.success('Personas actualizados');
            setIsMemberDrawerOpen(false);
            fetchGroups();
        } catch (e: any) {
            toast.error('Error al guardar: ' + (e.message || 'Intente de nuevo'));
        } finally { setMemberSaving(false); }
    };

    const addMemberToGroup = (member: any) => {
        if (groupMembers.find(m => m.id === member.id)) return;
        setGroupMembers(prev => [...prev, {
            id: member.id,
            name: member.nombre_completo || `${member.first_name ?? ''} ${member.last_name ?? ''}`.trim(),
            email: member.email || '',
            role: 'persona',
        }]);
    };

    const updateMemberRole = (memberId: string, role: string) => {
        setGroupMembers(prev => prev.map(m => m.id === memberId ? { ...m, role } : m));
    };

    const removeMemberFromGroup = (memberId: string) => {
        setGroupMembers(prev => prev.filter(m => m.id !== memberId));
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
                    grupo_id: parseInt(String(sessionForm.grupo_id)),
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

    const openAttendanceDrawer = async (session: SessionRow) => {
        setAttendanceSession(session);
        setIsAttendanceDrawerOpen(true);
        setShowVisitorSearch(false);
        setVisitorSearch('');
        // Pre-load all members for visitor search if not already loaded
        if (allMembers.length === 0) {
            apiFetch<any[]>('/crm/personas', { token, query: { limit: 200, sort_by: 'first_name', sort_dir: 'asc' } }).then(res => {
                if (Array.isArray(res)) setAllMembers(res);
            }).catch(() => { toast.error('Error al cargar personas'); });
        }
        try {
            // Get house members to build attendance list
            const house = await apiFetch<any>(`/evangelism/grupos/${session.grupo_id}`, { token });
            const existing = await apiFetch<any>(`/evangelism/sessions/${session.id}`, { token }).catch(() => null);
            const existingMap: Record<string, { status: string; notes: string }> = {};
            if (existing?.attendance) {
                for (const a of existing.attendance) {
                    existingMap[a.persona_id] = { status: a.status, notes: a.notes || '' };
                }
            }
            const memberList = house?.base_attendees?.map((a: any) => ({
                persona_id: a.persona_id,
                name: a.name || a.member?.nombre_completo || '',
                role: a.role || 'persona',
                status: (existingMap[a.persona_id]?.status as any) || 'present',
                notes: existingMap[a.persona_id]?.notes || '',
            })) || [];
            setAttendanceMembers(memberList);
        } catch { setAttendanceMembers([]); }
    };

    const handleSaveAttendance = async () => {
        if (!attendanceSession) return;
        setAttendanceSaving(true);
        try {
            await apiFetch(`/evangelism/sessions/${attendanceSession.id}/attendance`, {
                method: 'POST', token,
                body: attendanceMembers.map(m => ({
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
                    const res = await apiFetch<any>(`/evangelism/strategies/${id}/deshabilitar-todas`, { method: 'POST', token });
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
                } catch { toast.error('Error al eliminar rol'); }
            },
        });
    };

    const formatDate = (dateStr: string | null | undefined) => {
        if (!dateStr) return 'Sin fecha';
        try { return new Date(dateStr).toLocaleDateString('es-ES', { day: 'numeric', month: 'short', year: 'numeric' }); }
        catch { return dateStr; }
    };

    const groupName = (houseId: number) => groups.find(g => g.id === houseId)?.name || `Grupo #${houseId}`;

    if (loading) {
        return (
            <EvangelismShell breadcrumbs={[
                { label: 'Evangelismo', icon: Flame, href: '/plataforma/evangelism' },
                { label: 'Estrategias', href: '/plataforma/evangelism' },
                { label: 'Cargando...' }
            ]}>
                <div className="space-y-3 p-3">
                    {[1, 2, 3].map(i => <div key={i} className="h-12 bg-slate-100 dark:bg-white/5 rounded-lg animate-pulse" />)}
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
                    <AlertCircle size={48} className="text-slate-300 dark:text-slate-600 mb-4" />
                    <h2 className="text-lg font-bold text-slate-700 dark:text-slate-300">Estrategia no encontrada</h2>
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
                            className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-white/5 text-slate-400 hover:text-slate-600 dark:hover:text-white transition-all mt-1">
                            <ArrowLeft size={16} />
                        </button>
                        <div>
                            <h1 className="text-xl font-bold text-slate-900 dark:text-white">{strategy.name}</h1>
                            <div className="flex items-center gap-3 mt-1 text-xs text-slate-400 font-medium flex-wrap">
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
                        className="p-2 rounded-lg text-slate-400 hover:text-[hsl(var(--destructive))] hover:bg-red-50 dark:hover:bg-red-500/10 transition-all" title="Eliminar estrategia">
                        <Trash2 size={16} />
                    </button>
                </div>

                {/* Tabs */}
                <div className="flex items-center gap-1 border-b border-slate-200 dark:border-white/10">
                    {TABS.map(tab => (
                        <button key={tab.id} onClick={() => setActiveTab(tab.id)}
                            className={`flex items-center gap-1.5 px-3 py-2 text-xs font-semibold border-b-2 transition-colors ${
                                activeTab === tab.id
                                    ? 'border-blue-600 text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))] dark:border-blue-400'
                                    : 'border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
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
                                progress: Math.min(g.members_count * 20, 100),
                                color: 'blue' as const, subtitle: `${g.members_count} personas`,
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
                                            <div key={s.id} className="rounded-lg border border-slate-200 dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-[#1a1b1e] p-3">
                                                <p className="text-sm font-semibold text-slate-900 dark:text-white">{s.topic || `Sesión #${s.id}`}</p>
                                                <p className="text-xs text-slate-400 mt-1">{groupName(s.grupo_id)}</p>
                                                <p className="text-xs text-slate-500 mt-1">{formatDate(s.session_date)}</p>
                                            </div>
                                        ))}
                                        {filtered.length === 0 && <p className="text-xs text-slate-400 p-3">Sin sesiones</p>}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}

                {/* ── View: Table (tab-aware) ── */}
                {viewType === 'table' && (
                    <div className="overflow-x-auto">
                        <table className="w-full text-xs">
                            <thead><tr className="border-b border-slate-200 dark:border-white/10 text-slate-500">
                                <th className="text-left py-2 px-3 font-semibold">Tipo</th>
                                <th className="text-left py-2 px-3 font-semibold">Nombre</th>
                                <th className="text-left py-2 px-3 font-semibold">Fecha</th>
                                <th className="text-left py-2 px-3 font-semibold">Estado</th>
                                <th className="text-left py-2 px-3 font-semibold">Personas</th>
                            </tr></thead>
                            <tbody>
                                {(activeTab === 'groups' || activeTab === 'overview') && groups.map(g => (
                                    <tr key={`g-${g.id}`} className="border-b border-slate-100 dark:border-white/5 hover:bg-slate-50 dark:hover:bg-white/5">
                                        <td className="py-2 px-3"><span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-[hsl(var(--primary))] dark:bg-blue-900/30 dark:text-blue-300">Grupo</span></td>
                                        <td className="py-2 px-3 font-medium text-slate-900 dark:text-white">{g.name}</td>
                                        <td className="py-2 px-3 text-slate-400">—</td>
                                        <td className="py-2 px-3 text-slate-400">Activo</td>
                                        <td className="py-2 px-3 text-slate-400">{g.members_count}</td>
                                    </tr>
                                ))}
                                {(activeTab === 'sessions' || activeTab === 'overview') && sessions.map(s => (
                                    <tr key={`s-${s.id}`} className="border-b border-slate-100 dark:border-white/5 hover:bg-slate-50 dark:hover:bg-white/5">
                                        <td className="py-2 px-3"><span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-[hsl(var(--primary))] dark:bg-blue-900/30 dark:text-blue-300">Sesión</span></td>
                                        <td className="py-2 px-3 font-medium text-slate-900 dark:text-white">{s.topic || `Sesión #${s.id}`}</td>
                                        <td className="py-2 px-3 text-slate-400">{formatDate(s.session_date)}</td>
                                        <td className="py-2 px-3"><span className="px-1.5 py-0.5 rounded text-[10px] font-bold" style={{ backgroundColor: s.status === 'Realizada' ? '#10B98120' : '#3B82F620', color: s.status === 'Realizada' ? '#10B981' : '#3B82F6' }}>{s.status}</span></td>
                                        <td className="py-2 px-3 text-slate-400">—</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}

                {/* ── View: List (tab-aware) ── */}
                {viewType === 'list' && (
                    <div className="space-y-1">
                        {(activeTab === 'groups' || activeTab === 'overview') && groups.map(g => (
                            <div key={`g-${g.id}`} className="flex items-center gap-3 p-3 rounded-lg hover:bg-slate-50 dark:hover:bg-white/5 transition-all">
                                <div className="w-8 h-8 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center shrink-0"><Users size={14} className="text-[hsl(var(--primary))] dark:text-blue-400" /></div>
                                <div className="flex-1 min-w-0">
                                    <p className="text-sm font-semibold text-slate-900 dark:text-white truncate">{g.name}</p>
                                    <p className="text-xs text-slate-400">{g.members_count} personas{g.zone ? ` · ${g.zone}` : ''}</p>
                                </div>
                                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-green-100 text-[hsl(var(--secondary))] dark:bg-green-900/30 dark:text-green-300">Grupo</span>
                            </div>
                        ))}
                        {(activeTab === 'sessions' || activeTab === 'overview') && sessions.map(s => (
                            <div key={`s-${s.id}`} className="flex items-center gap-3 p-3 rounded-lg hover:bg-slate-50 dark:hover:bg-white/5 transition-all">
                                <div className="w-8 h-8 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center shrink-0"><Calendar size={14} className="text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))]" /></div>
                                <div className="flex-1 min-w-0">
                                    <p className="text-sm font-semibold text-slate-900 dark:text-white truncate">{s.topic || `Sesión #${s.id}`}</p>
                                    <p className="text-xs text-slate-400">{groupName(s.grupo_id)} · {formatDate(s.session_date)}</p>
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
                            <div key={`g-${g.id}`} className="rounded-lg border border-slate-200 dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-[#1a1b1e] p-4 hover:shadow-md transition-shadow">
                                <div className="flex items-center gap-2 mb-2">
                                    <div className="w-6 h-6 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center"><Users size={12} className="text-[hsl(var(--primary))] dark:text-blue-400" /></div>
                                    <span className="text-xs font-bold text-[hsl(var(--primary))] dark:text-blue-400">GRUPO</span>
                                </div>
                                <h3 className="text-sm font-bold text-slate-900 dark:text-white">{g.name}</h3>
                                <p className="text-xs text-slate-400 mt-1">{g.zone || 'Sin zona'}</p>
                                <span className="text-xs font-medium text-slate-500 mt-3 block">{g.members_count} personas</span>
                            </div>
                        ))}
                        {(activeTab === 'sessions' || activeTab === 'overview') && sessions.map(s => (
                            <div key={`s-${s.id}`} className="rounded-lg border border-slate-200 dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-[#1a1b1e] p-4 hover:shadow-md transition-shadow">
                                <div className="flex items-center gap-2 mb-2">
                                    <div className="w-6 h-6 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center"><Calendar size={12} className="text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))]" /></div>
                                    <span className="text-xs font-bold text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))]">SESIÓN</span>
                                </div>
                                <h3 className="text-sm font-bold text-slate-900 dark:text-white">{s.topic || `Sesión #${s.id}`}</h3>
                                <p className="text-xs text-slate-400 mt-1">{groupName(s.grupo_id)}</p>
                                <div className="flex items-center justify-between mt-3">
                                    <span className="text-xs text-slate-500">{formatDate(s.session_date)}</span>
                                    <span className="px-1.5 py-0.5 rounded text-[10px] font-bold" style={{ backgroundColor: s.status === 'Realizada' ? '#10B98120' : '#3B82F620', color: s.status === 'Realizada' ? '#10B981' : '#3B82F6' }}>{s.status}</span>
                                </div>
                            </div>
                        ))}
                    </div>
                )}

                {/* ── Overview ── */}
                {activeTab === 'overview' && (
                    <div className="bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] border border-slate-200 dark:border-white/10 rounded-lg p-4 space-y-4">
                        <div>
                            <label className="block text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-1">Nombre</label>
                            <input type="text" value={editName} onChange={e => setEditName(e.target.value)}
                                className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/5 text-sm text-slate-900 dark:text-white focus:border-blue-500 focus:outline-none transition-colors" />
                        </div>
                        <div>
                            <label className="block text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-1">Descripción</label>
                            <textarea value={editDesc} onChange={e => setEditDesc(e.target.value)} rows={3}
                                className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/5 text-sm text-slate-900 dark:text-white focus:border-blue-500 focus:outline-none transition-colors resize-none"
                                placeholder="Detalles sobre la estrategia..." />
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label className="block text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-1">Tipo</label>
                                <select value={editType} onChange={e => setEditType(e.target.value)}
                                    className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/5 text-sm text-slate-900 dark:text-white focus:border-blue-500 focus:outline-none transition-colors">
                                    <option value="">General</option>
                                    <option value="Geográfica">Geográfica</option>
                                    <option value="Temática">Temática</option>
                                    <option value="Sectorial">Sectorial</option>
                                    <option value="Poblacional">Poblacional</option>
                                    <option value="Servicios (Cultos)">Servicios (Cultos)</option>
                                </select>
                            </div>
                            <div>
                                <label className="block text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-1">Estado</label>
                                <select value={editStatus} onChange={e => setEditStatus(e.target.value as any)}
                                    className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/5 text-sm text-slate-900 dark:text-white focus:border-blue-500 focus:outline-none transition-colors">
                                    <option value="pending">No iniciada</option>
                                    <option value="active">Iniciada</option>
                                    <option value="done">Terminada</option>
                                </select>
                            </div>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label className="block text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-1">Clase Raíz</label>
                                <div className="flex gap-2">
                                    {['relacional', 'evento_masivo', 'sectorial'].map(c => (
                                        <button key={c} onClick={() => setEditClaseRaiz(c)}
                                            className={`flex-1 px-2 py-1.5 text-[10px] font-bold rounded-lg transition-all capitalize ${
                                                editClaseRaiz === c
                                                    ? 'bg-[hsl(var(--primary))] text-white shadow-sm'
                                                    : 'bg-slate-50 dark:bg-white/5 text-slate-500 border border-slate-200 dark:border-white/10'
                                            }`}>
                                            {c === 'evento_masivo' ? 'Evento Masivo' : c}
                                        </button>
                                    ))}
                                </div>
                            </div>
                            <div>
                                <label className="block text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-1">Activa</label>
                                <button onClick={() => setEditActiva(!editActiva)}
                                    className={`w-full px-3 py-2 rounded-lg text-[12px] font-bold transition-all text-left ${
                                        editActiva
                                            ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800'
                                            : 'bg-slate-50 dark:bg-white/5 text-slate-400 border border-slate-200 dark:border-white/10'
                                    }`}>
                                    {editActiva ? 'Activa' : 'Inactiva'}
                                </button>
                            </div>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label className="block text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-1">Recurrencia</label>
                                <select value={editRecurrence || ''} onChange={e => setEditRecurrence(e.target.value || null)}
                                    className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/5 text-sm text-slate-900 dark:text-white focus:border-blue-500 focus:outline-none transition-colors">
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
                                    className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/5 text-sm text-slate-900 dark:text-white focus:border-blue-500 focus:outline-none transition-colors" />
                            </div>
                            <div>
                                <label className="block text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-1">Fecha de fin</label>
                                <input type="date" value={editEndDate} onChange={e => setEditEndDate(e.target.value)}
                                    className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/5 text-sm text-slate-900 dark:text-white focus:border-blue-500 focus:outline-none transition-colors" />
                            </div>
                        </div>
                        <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100 dark:border-white/5">
                            <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
                                onClick={handleSave} disabled={saving}
                                className="inline-flex items-center gap-2 px-4 h-9 rounded-lg bg-[hsl(var(--primary))] text-white text-xs font-semibold hover:bg-[hsl(var(--primary))] disabled:opacity-60 transition-colors">
                                <Save size={14} />{saving ? 'Guardando...' : 'Guardar cambios'}
                            </motion.button>
                        </div>
                    </div>
                )}

                {/* ── Grupos ── */}
                {activeTab === 'groups' && (
                    <div className="space-y-3">
                        <div className="flex items-center justify-between">
                            <div>
                                <h2 className="text-sm font-bold text-slate-900 dark:text-white">Grupos de esta estrategia</h2>
                                {strategy.typology === 'relacional' && (
                                    <p className="text-[11px] text-slate-400 mt-0.5">
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
                            <div className="flex flex-col items-center justify-center py-12 text-center bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] border border-slate-200 dark:border-white/10 rounded-lg">
                                <Home size={32} className="text-slate-300 dark:text-slate-600 mb-2" />
                                <p className="text-sm font-medium text-slate-500">Sin grupos aún</p>
                                <p className="text-xs text-slate-400">Crea el primer grupo para esta estrategia</p>
                            </div>
                        ) : (
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                                {groups.map(g => (
                                    <div key={g.id}
                                        className="group bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] border border-slate-200 dark:border-white/10 rounded-lg p-4 hover:border-blue-300 dark:hover:border-blue-800 transition-all cursor-pointer relative"
                                        onClick={() => openMemberDrawer(g)}>
                                        <button onClick={e => { e.stopPropagation(); requestDeleteGroup(g.id, g.name); }}
                                            className="absolute top-2 right-2 p-1 rounded text-slate-300 hover:text-[hsl(var(--destructive))] hover:bg-red-50 dark:hover:bg-red-900/20 opacity-0 group-hover:opacity-100 transition-all z-10" title="Eliminar">
                                            <Trash2 size={14} />
                                        </button>
                                        <button onClick={e => { e.stopPropagation(); router.push(`/plataforma/evangelism/faro/${g.id}`); }}
                                            className="absolute top-2 right-8 p-1 rounded text-slate-300 hover:text-[hsl(var(--primary))] hover:bg-blue-50 dark:hover:bg-blue-900/20 opacity-0 group-hover:opacity-100 transition-all z-10" title="Ver detalle">
                                            <Calendar size={14} />
                                        </button>
                                        <h3 className="text-sm font-bold text-slate-900 dark:text-white pr-16">{g.name}</h3>
                                        <p className="text-xs text-slate-400 mt-1">{g.zone || 'Sin zona'}</p>
                                        <div className="flex items-center gap-3 mt-3 text-xs text-slate-500">
                                            <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-slate-100 dark:bg-white/5">
                                                <Users size={12} />{g.members_count} personas
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
                {activeTab === 'sessions' && (
                    <div className="space-y-3">
                        <div className="flex items-center justify-between flex-wrap gap-2">
                            <h2 className="text-sm font-bold text-slate-900 dark:text-white">Registro de sesiones</h2>
                            <div className="flex items-center gap-2 flex-wrap">
                                {strategy.recurrence && strategy.start_date && strategy.end_date && (
                                    <button onClick={async () => {
                                        const btn = toast.loading('Generando sesiones...');
                                        try {
                                            const res = await apiFetch<any>(`/evangelism/strategies/${id}/generate-sessions`, { method: 'POST', token });
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
                                        className="inline-flex items-center gap-1.5 px-3 h-8 rounded-lg border border-slate-300 dark:border-white/20 text-slate-600 dark:text-slate-300 text-xs font-semibold hover:bg-slate-100 dark:hover:bg-white/5 transition-colors">
                                        <Sparkles size={14} />Generar sesiones
                                    </button>
                                )}
                                <button onClick={async () => {
                                    try {
                                        const res = await apiFetch<any>(`/evangelism/strategies/${id}/habilitar-todas`, { method: 'POST', token });
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

                        {groups.length > 1 && (
                            <div className="flex items-center gap-2">
                                <select
                                    value={sessionGroupFilter}
                                    onChange={e => setSessionGroupFilter(e.target.value === 'all' ? 'all' : Number(e.target.value))}
                                    className="h-8 px-2 rounded-lg border border-slate-200 dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] text-xs text-slate-700 dark:text-slate-200 focus:outline-none focus:ring-1 focus:ring-blue-500">
                                    <option value="all">Todos los grupos</option>
                                    {groups.map(g => <option key={g.id} value={g.id}>{g.name}</option>)}
                                </select>
                            </div>
                        )}

                        {sessionsLoading ? (
                            <div className="space-y-2">
                                {[1, 2, 3].map(i => <div key={i} className="h-14 bg-slate-100 dark:bg-white/5 rounded-lg animate-pulse" />)}
                            </div>
                        ) : sessions.filter(s => sessionGroupFilter === 'all' || s.grupo_id === sessionGroupFilter).length === 0 ? (
                            <div className="flex flex-col items-center justify-center py-12 text-center bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] border border-slate-200 dark:border-white/10 rounded-lg">
                                <ClipboardList size={32} className="text-slate-300 dark:text-slate-600 mb-2" />
                                <p className="text-sm font-medium text-slate-500">Sin sesiones registradas</p>
                                <p className="text-xs text-slate-400">Registra la primera sesión semanal</p>
                            </div>
                        ) : (
                            <div className="space-y-2">
                                {sessions.filter(s => sessionGroupFilter === 'all' || s.grupo_id === sessionGroupFilter).map(s => (
                                    <div key={s.id} className={`flex items-center gap-3 bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] border rounded-lg px-4 py-3 transition-all ${
                                        s.estado_habilitacion === 'HABILITADO'
                                            ? 'border-emerald-300 dark:border-emerald-700'
                                            : s.estado_habilitacion === 'CERRADO'
                                            ? 'border-slate-300 dark:border-white/5 opacity-60'
                                            : 'border-slate-200 dark:border-white/10'
                                    }`}>
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2 flex-wrap">
                                                <span className="text-xs font-bold text-slate-700 dark:text-white">
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
                                                    <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-500 dark:bg-white/5 dark:text-slate-500">Cerrada</span>
                                                )}
                                                {(!s.estado_habilitacion || s.estado_habilitacion === 'DESHABILITADO') && (
                                                    <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-50 text-amber-600 dark:bg-amber-900/20 dark:text-amber-400">Bloqueada</span>
                                                )}
                                            </div>
                                            <div className="flex items-center gap-3 mt-0.5 text-[11px] text-slate-400">
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
                                                className="inline-flex items-center gap-1.5 px-3 h-7 rounded-lg bg-slate-100 dark:bg-white/5 text-slate-600 dark:text-slate-300 text-[11px] font-semibold hover:bg-blue-50 hover:text-[hsl(var(--primary))] dark:hover:bg-blue-900/20 dark:hover:text-[hsl(var(--primary))] transition-colors whitespace-nowrap">
                                                <Users size={12} />Asistencia
                                            </button>
                                            <div className="relative">
                                                <button onClick={() => setSessionMenuId(sessionMenuId === s.id ? null : s.id)}
                                                    className="w-7 h-7 flex items-center justify-center rounded-lg text-slate-400 hover:bg-slate-100 dark:hover:bg-white/10 hover:text-slate-600 dark:hover:text-white transition-colors">
                                                    <span className="text-base leading-none">⋯</span>
                                                </button>
                                                {sessionMenuId === s.id && (
                                                    <div className="absolute right-0 top-8 z-20 bg-[hsl(var(--bg-primary))] dark:bg-[#2a2b2d] border border-slate-200 dark:border-white/10 rounded-lg shadow-lg py-1 min-w-[130px]">
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

                {/* ── Métricas ── */}
                {activeTab === 'metrics' && (
                    <div className="space-y-3">
                        <h2 className="text-sm font-bold text-slate-900 dark:text-white">Métricas de la estrategia</h2>
                        {!metrics ? (
                            <div className="bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] border border-slate-200 dark:border-white/10 rounded-lg p-8 text-center">
                                <BarChart3 size={32} className="text-slate-300 dark:text-slate-600 mx-auto mb-2" />
                                <p className="text-sm font-medium text-slate-500">Cargando métricas...</p>
                            </div>
                        ) : (
                            <>
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                                    {[
                                        { label: 'Grupos', value: metrics.summary.total_groups },
                                        { label: 'Sesiones', value: metrics.summary.total_sessions },
                                        { label: 'Primeriza', value: metrics.summary.total_first_timers, cls: 'text-[hsl(var(--secondary))] dark:text-[hsl(var(--secondary))]' },
                                        { label: 'Inasistencias', value: metrics.summary.total_absences, cls: 'text-[hsl(var(--destructive))] dark:text-[hsl(var(--destructive))]' },
                                    ].map(stat => (
                                        <div key={stat.label} className="bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] border border-slate-200 dark:border-white/10 rounded-lg p-4">
                                            <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">{stat.label}</p>
                                            <p className={`text-lg font-bold mt-1 ${stat.cls || 'text-slate-900 dark:text-white'}`}>{stat.value}</p>
                                        </div>
                                    ))}
                                </div>
                                {metrics.weekly && metrics.weekly.length > 0 && (
                                    <div className="bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] border border-slate-200 dark:border-white/10 rounded-lg p-4">
                                        <h3 className="text-xs font-bold text-slate-700 dark:text-slate-300 mb-4">Asistencia semanal</h3>
                                        <div className="flex items-end gap-2 h-32">
                                            {metrics.weekly.map((w: any) => {
                                                const max = Math.max(...metrics.weekly.map((x: any) => x.present + x.absent), 1);
                                                return (
                                                    <div key={w.week} className="flex-1 flex flex-col items-center gap-1">
                                                        <div className="w-full flex flex-col" style={{ height: '100px' }}>
                                                            <div className="w-full rounded-t bg-[hsl(var(--primary))] dark:bg-[hsl(var(--primary))] transition-all"
                                                                style={{ height: `${(w.present / max) * 100}%`, minHeight: w.present > 0 ? '4px' : '0' }} />
                                                            {w.absent > 0 && (
                                                                <div className="w-full rounded-t bg-red-300 dark:bg-red-800 transition-all"
                                                                    style={{ height: `${(w.absent / max) * 100}%`, minHeight: '4px' }} />
                                                            )}
                                                        </div>
                                                        <span className="text-[9px] text-slate-400 truncate w-full text-center">{w.week.slice(5)}</span>
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    </div>
                                )}
                            </>
                        )}
                    </div>
                )}

                {/* Metadata */}
                {activeTab === 'overview' && (
                    <>
                    <div className="bg-slate-50 dark:bg-white/[0.02] border border-slate-200 dark:border-white/5 rounded-lg p-4">
                        <h3 className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-3">Información</h3>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
                            <div><p className="text-slate-400 font-medium">ID</p><p className="text-slate-700 dark:text-white font-bold">{strategy.codigo ? strategy.codigo : `#${strategy.id}`}</p></div>
                            <div><p className="text-slate-400 font-medium">Inicio</p><p className="text-slate-700 dark:text-white font-bold">{formatDate(strategy.start_date)}</p></div>
                            <div><p className="text-slate-400 font-medium">Fin</p><p className="text-slate-700 dark:text-white font-bold">{formatDate(strategy.end_date)}</p></div>
                            <div><p className="text-slate-400 font-medium">Actualización</p><p className="text-slate-700 dark:text-white font-bold">{formatDate(strategy.updated_at)}</p></div>
                            <div><p className="text-slate-400 font-medium">Clase</p><p className="text-slate-700 dark:text-white font-bold capitalize">{strategy.clase_raiz || strategy.typology || '—'}</p></div>
                            <div><p className="text-slate-400 font-medium">Activa</p><p className={`font-bold ${strategy.activa ? 'text-emerald-600' : 'text-slate-400'}`}>{strategy.activa ? 'Sí' : 'No'}</p></div>
                        </div>
                    </div>

                    {/* ── Roles Personalizados ── */}
                    <div className="bg-slate-50 dark:bg-white/[0.02] border border-slate-200 dark:border-white/5 rounded-lg p-4">
                        <div className="flex items-center justify-between mb-3">
                            <h3 className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Roles Personalizados</h3>
                            <button onClick={() => setShowRoleForm(!showRoleForm)}
                                className="text-[11px] font-bold text-[hsl(var(--primary))] hover:text-[hsl(var(--primary))] flex items-center gap-1">
                                <Plus size={12} />{showRoleForm ? 'Cancelar' : 'Agregar'}
                            </button>
                        </div>

                        {showRoleForm && (
                            <div className="mb-3 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg space-y-2">
                                <input value={newRoleName} onChange={e => setNewRoleName(e.target.value)}
                                    placeholder="Nombre del rol (ej: Coordinador de zona)"
                                    className="w-full px-2.5 py-1.5 text-[12px] bg-[hsl(var(--bg-primary))] dark:bg-white/10 border border-slate-200 dark:border-white/10 rounded-lg text-slate-700 dark:text-slate-200 outline-none" />
                                <input value={newRoleDesc} onChange={e => setNewRoleDesc(e.target.value)}
                                    placeholder="Descripción (opcional)"
                                    className="w-full px-2.5 py-1.5 text-[12px] bg-[hsl(var(--bg-primary))] dark:bg-white/10 border border-slate-200 dark:border-white/10 rounded-lg text-slate-700 dark:text-slate-200 outline-none" />
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
                            <p className="text-[11px] text-slate-400 italic">Cargando...</p>
                        ) : customRoles.length === 0 ? (
                            <p className="text-[11px] text-slate-400 italic">Sin roles personalizados</p>
                        ) : (
                            <div className="space-y-1.5">
                                {customRoles.map(r => (
                                    <div key={r.id} className="flex items-center justify-between px-2.5 py-1.5 bg-[hsl(var(--bg-primary))] dark:bg-white/5 rounded-lg border border-slate-100 dark:border-white/5">
                                        <div>
                                            <span className="text-[12px] font-semibold text-slate-700 dark:text-slate-200">{r.nombre_rol}</span>
                                            {r.descripcion && <p className="text-[10px] text-slate-400">{r.descripcion}</p>}
                                        </div>
                                        <button onClick={() => requestDeleteRole(r)} className="p-1 text-slate-400 hover:text-[hsl(var(--destructive))] rounded hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors">
                                            <X size={12} />
                                        </button>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* ── Seguimiento Pendiente ── */}
                    <div className="bg-slate-50 dark:bg-white/[0.02] border border-slate-200 dark:border-white/5 rounded-lg p-4">
                        <div className="flex items-center justify-between mb-3">
                            <h3 className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Seguimiento Pendiente</h3>
                            <span className="text-[10px] font-bold px-2 py-0.5 bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 rounded-full">
                                {followUps.filter(f => !f.completado).length}
                            </span>
                        </div>
                        {loadingFollowUps ? (
                            <p className="text-[11px] text-slate-400 italic">Cargando...</p>
                        ) : followUps.filter(f => !f.completado).length === 0 ? (
                            <p className="text-[11px] text-slate-400 italic">Sin seguimientos pendientes</p>
                        ) : (
                            <div className="space-y-1.5 max-h-48 overflow-y-auto">
                                {followUps.filter(f => !f.completado).slice(0, 10).map(f => (
                                    <div key={f.id} className="flex items-center justify-between px-2.5 py-1.5 bg-[hsl(var(--bg-primary))] dark:bg-white/5 rounded-lg border border-slate-100 dark:border-white/5">
                                        <div className="flex items-center gap-2">
                                            <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full ${f.tipo === 'llamada' ? 'bg-blue-100 text-[hsl(var(--primary))]' : f.tipo === 'visita' ? 'bg-blue-100 text-[hsl(var(--primary))]' : f.tipo === 'oracion' ? 'bg-green-100 text-[hsl(var(--secondary))]' : 'bg-slate-100 text-slate-600'}`}>
                                                {f.tipo}
                                            </span>
                                            <span className="text-[11px] text-slate-500">{f.notas || '—'}</span>
                                        </div>
                                        <button onClick={async () => {
                                            try {
                                                await apiFetch(`/evangelism/follow-up/${f.id}`, {
                                                    method: 'PATCH', token,
                                                    body: { completado: true, fecha_realizada: new Date().toISOString() },
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
                        className="px-4 py-1.5 text-[12px] font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-white/5 rounded-md transition-colors">Cancelar</button>
                    <button onClick={handleCreateGroup} disabled={groupSaving || !groupForm.name.trim()}
                        className="px-4 py-1.5 text-[12px] font-semibold text-white bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))] disabled:opacity-50 rounded-md transition-colors flex items-center gap-2">
                        {groupSaving ? <><Sparkles size={14} className="animate-spin" />Creando...</> : <><Plus size={14} />Crear Grupo</>}
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
                            <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2 block">{label}</label>
                            <input value={(groupForm as any)[field]} onChange={e => setGroupForm(f => ({ ...f, [field]: e.target.value }))}
                                placeholder={placeholder}
                                className="w-full px-3 py-2 text-[13px] bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg text-slate-700 dark:text-slate-200 outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500" />
                        </div>
                    ))}
                    <div>
                        <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2 block">Capacidad</label>
                        <input type="number" value={groupForm.capacity} onChange={e => setGroupForm(f => ({ ...f, capacity: parseInt(e.target.value) || 15 }))}
                            className="w-full px-3 py-2 text-[13px] bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg text-slate-700 dark:text-slate-200 outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500" />
                    </div>
                    <div className="grid grid-cols-3 gap-2">
                        <div>
                            <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2 block">Día</label>
                            <select value={groupForm.day_of_week} onChange={e => setGroupForm(f => ({ ...f, day_of_week: e.target.value }))}
                                className="w-full px-2 py-2 text-[12px] bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg text-slate-700 dark:text-slate-200 outline-none">
                                <option value="">—</option>
                                {['Domingo','Lunes','Martes','Miércoles','Jueves','Viernes','Sábado'].map(d => <option key={d} value={d}>{d}</option>)}
                            </select>
                        </div>
                        <div>
                            <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2 block">Inicio</label>
                            <input type="time" value={groupForm.start_time} onChange={e => setGroupForm(f => ({ ...f, start_time: e.target.value }))}
                                className="w-full px-2 py-2 text-[12px] bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg text-slate-700 dark:text-slate-200 outline-none" />
                        </div>
                        <div>
                            <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2 block">Fin</label>
                            <input type="time" value={groupForm.end_time} onChange={e => setGroupForm(f => ({ ...f, end_time: e.target.value }))}
                                className="w-full px-2 py-2 text-[12px] bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg text-slate-700 dark:text-slate-200 outline-none" />
                        </div>
                    </div>
                    {([
                        { label: 'Líder', field: 'leader_id' as const },
                        { label: 'Colíder', field: 'assistant_id' as const },
                        { label: 'Anfitrión', field: 'host_id' as const },
                    ]).map(({ label, field }) => {
                        const selectedId = (groupForm as any)[field] as string | null;
                        const selectedMember = selectedId ? memberCache[selectedId] : null;
                        const selectedName = selectedMember
                            ? (selectedMember.nombre_completo || `${selectedMember.first_name ?? ''} ${selectedMember.last_name ?? ''}`.trim())
                            : '';
                        const query = roleSearch[field];
                        const results = roleResults[field];
                        const isLoading = roleLoading[field];
                        return (
                            <div key={field} className="relative">
                                <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2 block">{label}</label>
                                <div className="relative">
                                    <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
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
                                        className="w-full pl-8 pr-3 py-2 text-[13px] bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg text-slate-700 dark:text-slate-200 outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                                    />
                                    {selectedId && (
                                        <button
                                            type="button"
                                            onClick={() => { setGroupForm(f => ({ ...f, [field]: null })); setRoleDropdown(null); }}
                                            className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                                        >
                                            <X size={13} />
                                        </button>
                                    )}
                                </div>
                                {roleDropdown === field && (
                                    <div className="absolute z-50 mt-1 w-full bg-white dark:bg-[#1e1f21] border border-slate-200 dark:border-white/10 rounded-lg shadow-xl max-h-48 overflow-y-auto">
                                        <button
                                            type="button"
                                            onMouseDown={() => { setGroupForm(f => ({ ...f, [field]: null })); setRoleDropdown(null); }}
                                            className="w-full text-left px-3 py-2 text-[12px] text-slate-400 hover:bg-slate-50 dark:hover:bg-white/5 border-b border-slate-100 dark:border-white/5"
                                        >
                                            Sin asignar
                                        </button>
                                        {isLoading ? (
                                            <div className="px-3 py-3 text-[12px] text-slate-400 text-center">Buscando...</div>
                                        ) : results.length === 0 ? (
                                            <div className="px-3 py-3 text-[12px] text-slate-400 text-center">Sin resultados</div>
                                        ) : results.map(m => {
                                            const name = m.nombre_completo || `${m.first_name ?? ''} ${m.last_name ?? ''}`.trim();
                                            return (
                                                <button
                                                    key={m.id}
                                                    type="button"
                                                    onMouseDown={() => {
                                                        setMemberCache(c => ({ ...c, [m.id]: m }));
                                                        setGroupForm(f => ({ ...f, [field]: m.id }));
                                                        setRoleDropdown(null);
                                                        setRoleSearch(s => ({ ...s, [field]: '' }));
                                                    }}
                                                    className="w-full text-left px-3 py-2 text-[12px] text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-white/5 flex items-center justify-between gap-2"
                                                >
                                                    <span className="font-medium">{name}</span>
                                                    {m.church_role && <span className="text-[10px] text-slate-400 shrink-0">{m.church_role}</span>}
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

            {/* ── Member Management Drawer ── */}
            <WorkspaceDrawer isOpen={isMemberDrawerOpen} onClose={() => setIsMemberDrawerOpen(false)}
                title="Gestionar Personas" subtitle={selectedGroup?.name || ''}
                actions={<>
                    <button onClick={() => setIsMemberDrawerOpen(false)}
                        className="px-4 py-1.5 text-[12px] font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-white/5 rounded-md transition-colors">Cancelar</button>
                    <button onClick={handleSaveMembers} disabled={memberSaving}
                        className="px-4 py-1.5 text-[12px] font-semibold text-white bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))] disabled:opacity-50 rounded-md transition-colors flex items-center gap-2">
                        {memberSaving ? <><Sparkles size={14} className="animate-spin" />Guardando...</> : <><UserCheck size={14} />Guardar ({groupMembers.length})</>}
                    </button>
                </>}>
                <div className="space-y-4">
                    <div>
                        <div className="flex items-center justify-between mb-2">
                            <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                                Personas ({groupMembers.length})
                            </label>
                        </div>
                        {groupMembers.length === 0 ? (
                            <p className="text-xs text-slate-400 italic py-2">Sin personas asignados</p>
                        ) : (
                            <div className="space-y-1.5 max-h-64 overflow-y-auto">
                                {groupMembers.map(m => (
                                    <div key={m.id} className="flex items-center gap-2 px-2 py-1.5 bg-slate-50 dark:bg-white/5 rounded-md">
                                        <div className="flex-1 min-w-0">
                                            <span className="text-xs font-medium text-slate-700 dark:text-slate-200 truncate block">{m.name}</span>
                                        </div>
                                        <select value={m.role} onChange={e => updateMemberRole(m.id, e.target.value)}
                                            className={`text-[11px] font-semibold px-2 py-1 rounded border-0 outline-none cursor-pointer ${ROLE_COLORS[m.role] || ROLE_COLORS.persona}`}>
                                            {MEMBER_ROLES.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
                                        </select>
                                        <button onClick={() => removeMemberFromGroup(m.id)}
                                            className="p-1 text-slate-400 hover:text-[hsl(var(--destructive))] hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-colors">
                                            <UserMinus size={13} />
                                        </button>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                    <div className="border-t border-slate-100 dark:border-white/5 pt-4">
                        <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2 block">Agregar personas</label>
                        <div className="relative mb-2">
                            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                            <input value={memberSearch} onChange={e => setMemberSearch(e.target.value)}
                                placeholder="Buscar por nombre o email..."
                                className="w-full pl-9 pr-3 py-2 text-[12px] bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg text-slate-700 dark:text-slate-200 outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500" />
                        </div>
                        <div className="space-y-1 max-h-48 overflow-y-auto">
                            {allMembers.length === 0 && (
                                <p className="text-[11px] text-slate-400 text-center py-3">
                                    {memberSearch ? 'Sin resultados para esta búsqueda' : 'Cargando personas...'}
                                </p>
                            )}
                            {allMembers
                                .filter(m => !groupMembers.find(gm => gm.id === m.id))
                                .map(m => (
                                    <button key={m.id} onClick={() => addMemberToGroup(m)}
                                        className="w-full flex items-center justify-between px-2 py-1.5 hover:bg-slate-50 dark:hover:bg-white/5 rounded-md text-xs text-left transition-colors group/add">
                                        <span className="font-medium text-slate-700 dark:text-slate-200">{m.nombre_completo || `${m.first_name ?? ''} ${m.last_name ?? ''}`.trim()}
                                            {m.email && <span className="text-slate-400 ml-2">{m.email}</span>}
                                        </span>
                                        <Plus size={14} className="text-slate-300 group-hover/add:text-[hsl(var(--primary))] transition-colors" />
                                    </button>
                                ))}
                        </div>
                    </div>
                </div>
            </WorkspaceDrawer>

            {/* ── New Session Drawer ── */}
            <WorkspaceDrawer isOpen={isNewSessionDrawerOpen} onClose={() => setIsNewSessionDrawerOpen(false)}
                title="Registrar Sesión" subtitle={`Estrategia: ${strategy?.name}`}
                actions={<>
                    <button onClick={() => setIsNewSessionDrawerOpen(false)}
                        className="px-4 py-1.5 text-[12px] font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-white/5 rounded-md transition-colors">Cancelar</button>
                    <button onClick={handleCreateSession} disabled={sessionSaving}
                        className="px-4 py-1.5 text-[12px] font-semibold text-white bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))] disabled:opacity-50 rounded-md transition-colors flex items-center gap-2">
                        {sessionSaving ? <><Sparkles size={14} className="animate-spin" />Guardando...</> : <><Save size={14} />Guardar</>}
                    </button>
                </>}>
                <div className="space-y-4">
                    <div>
                        <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2 block">Grupo *</label>
                        <select value={sessionForm.grupo_id} onChange={e => setSessionForm(f => ({ ...f, grupo_id: e.target.value }))}
                            className="w-full px-3 py-2 text-[13px] bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg text-slate-700 dark:text-slate-200 outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500">
                            <option value="">Seleccionar grupo...</option>
                            {groups.map(g => <option key={g.id} value={g.id}>{g.name}</option>)}
                        </select>
                    </div>
                    <div>
                        <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2 block">Fecha de la sesión *</label>
                        <input type="date" value={sessionForm.session_date} onChange={e => setSessionForm(f => ({ ...f, session_date: e.target.value }))}
                            className="w-full px-3 py-2 text-[13px] bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg text-slate-700 dark:text-slate-200 outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500" />
                    </div>
                    <div>
                        <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2 block">Tema de la sesión</label>
                        <input value={sessionForm.topic} onChange={e => setSessionForm(f => ({ ...f, topic: e.target.value }))}
                            placeholder="Ej: La fe que mueve montañas"
                            className="w-full px-3 py-2 text-[13px] bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg text-slate-700 dark:text-slate-200 outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500" />
                    </div>
                    <div>
                        <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2 block">Ofrenda recogida</label>
                        <input type="number" value={sessionForm.offering_amount} onChange={e => setSessionForm(f => ({ ...f, offering_amount: e.target.value }))}
                            placeholder="0.00"
                            className="w-full px-3 py-2 text-[13px] bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg text-slate-700 dark:text-slate-200 outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500" />
                    </div>
                    <div>
                        <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2 block">Notas de la sesión</label>
                        <textarea value={sessionForm.report_notes} onChange={e => setSessionForm(f => ({ ...f, report_notes: e.target.value }))} rows={3}
                            placeholder="Observaciones, peticiones de oración, novedades..."
                            className="w-full px-3 py-2 text-[13px] bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg text-slate-700 dark:text-slate-200 outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 resize-none" />
                    </div>
                </div>
            </WorkspaceDrawer>

            {/* ── Attendance Drawer ── */}
            <WorkspaceDrawer isOpen={isAttendanceDrawerOpen} onClose={() => setIsAttendanceDrawerOpen(false)}
                title="Registrar Asistencia"
                subtitle={attendanceSession ? new Date(attendanceSession.session_date.split('T')[0] + 'T12:00:00').toLocaleDateString('es-CO', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }) : ''}
                actions={<>
                    <button onClick={() => setIsAttendanceDrawerOpen(false)}
                        className="px-4 py-1.5 text-[12px] font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-white/5 rounded-md transition-colors">Cancelar</button>
                    <button onClick={handleSaveAttendance} disabled={attendanceSaving}
                        className="px-4 py-1.5 text-[12px] font-semibold text-white bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))] disabled:opacity-50 rounded-md transition-colors flex items-center gap-2">
                        {attendanceSaving ? <><Sparkles size={14} className="animate-spin" />Guardando...</> : <><UserCheck size={14} />Guardar asistencia</>}
                    </button>
                </>}>
                <div className="space-y-3">
                    {attendanceMembers.length === 0 && !showVisitorSearch ? (
                        <div className="text-center py-8">
                            <Users size={32} className="text-slate-300 mx-auto mb-2" />
                            <p className="text-xs text-slate-400">Este grupo no tiene personas asignados</p>
                            <p className="text-[11px] text-slate-400 mt-1">Agrega personas desde la pestaña Grupos</p>
                        </div>
                    ) : (
                        <>
                            {attendanceMembers.length > 0 && (
                                <div className="flex items-center gap-2 text-[11px] text-slate-400 mb-1">
                                    <span>{attendanceMembers.filter(m => m.status === 'present').length} presentes</span>
                                    <span>·</span>
                                    <span>{attendanceMembers.filter(m => m.status === 'absent').length} ausentes</span>
                                    <span>·</span>
                                    <span className="text-[hsl(var(--primary))]">{attendanceMembers.filter(m => m.status === 'first_time').length} primera vez</span>
                                </div>
                            )}
                            <div className="space-y-2">
                                {attendanceMembers.map((m, i) => (
                                    <div key={m.persona_id} className={`flex items-center gap-3 px-3 py-2.5 rounded-lg ${m.status === 'first_time' ? 'bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800' : 'bg-slate-50 dark:bg-white/5'}`}>
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-1.5">
                                                <p className="text-xs font-semibold text-slate-700 dark:text-slate-200">{m.name}</p>
                                                {m.status === 'first_time' && <span className="text-[9px] font-bold px-1 py-0.5 rounded bg-[hsl(var(--primary))] text-white">1ª vez</span>}
                                            </div>
                                            <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${ROLE_COLORS[m.role] || ROLE_COLORS.persona}`}>
                                                {MEMBER_ROLES.find(r => r.value === m.role)?.label || m.role}
                                            </span>
                                        </div>
                                        <div className="flex items-center gap-1">
                                            {[
                                                { status: 'present', label: 'P', cls: 'bg-green-100 text-[hsl(var(--secondary))] dark:bg-green-900/30 dark:text-[hsl(var(--secondary))]', activeCls: 'ring-2 ring-green-500' },
                                                { status: 'absent', label: 'A', cls: 'bg-red-100 text-[hsl(var(--destructive))] dark:bg-red-900/30 dark:text-[hsl(var(--destructive))]', activeCls: 'ring-2 ring-red-500' },
                                                { status: 'first_time', label: '1°', cls: 'bg-blue-100 text-[hsl(var(--primary))] dark:bg-blue-900/30 dark:text-[hsl(var(--primary))]', activeCls: 'ring-2 ring-blue-500' },
                                            ].map(opt => (
                                                <button key={opt.status}
                                                    onClick={() => setAttendanceMembers(prev => prev.map((x, j) => j === i ? { ...x, status: opt.status as any } : x))}
                                                    className={`w-8 h-8 rounded-lg text-[11px] font-bold transition-all ${opt.cls} ${m.status === opt.status ? opt.activeCls : 'opacity-50 hover:opacity-100'}`}>
                                                    {opt.label}
                                                </button>
                                            ))}
                                            {m.role === 'visitante' && (
                                                <button onClick={() => setAttendanceMembers(prev => prev.filter((_, j) => j !== i))}
                                                    className="w-7 h-7 ml-1 flex items-center justify-center rounded-lg text-slate-400 hover:bg-red-50 hover:text-[hsl(var(--destructive))] dark:hover:bg-red-900/20 transition-colors">
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
                    <div className="pt-2 border-t border-slate-200 dark:border-white/10">
                        {!showVisitorSearch ? (
                            <button onClick={() => setShowVisitorSearch(true)}
                                className="w-full flex items-center justify-center gap-2 py-2 rounded-lg border border-dashed border-slate-300 dark:border-white/20 text-xs text-slate-500 dark:text-slate-400 hover:border-blue-400 hover:text-[hsl(var(--primary))] dark:hover:border-blue-700 dark:hover:text-[hsl(var(--primary))] transition-colors">
                                <UserPlus size={14} />Agregar visitante (1ª vez)
                            </button>
                        ) : (
                            <div className="space-y-2">
                                <div className="flex items-center gap-2">
                                    <div className="relative flex-1">
                                        <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
                                        <input
                                            autoFocus
                                            value={visitorSearch}
                                            onChange={e => setVisitorSearch(e.target.value)}
                                            placeholder="Buscar persona por nombre..."
                                            className="w-full pl-8 pr-3 py-2 text-[12px] bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg text-slate-700 dark:text-slate-200 outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                                        />
                                    </div>
                                    <button onClick={() => { setShowVisitorSearch(false); setVisitorSearch(''); }}
                                        className="w-8 h-8 flex items-center justify-center rounded-lg text-slate-400 hover:bg-slate-100 dark:hover:bg-white/10">
                                        <X size={14} />
                                    </button>
                                </div>
                                {visitorSearch.trim().length >= 2 && (
                                    <div className="max-h-40 overflow-y-auto space-y-1 rounded-lg border border-slate-200 dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] p-1">
                                        {allMembers
                                            .filter(m => {
                                                const name = (m.nombre_completo || `${m.first_name ?? ''} ${m.last_name ?? ''}`).toLowerCase();
                                                return name.includes(visitorSearch.toLowerCase()) &&
                                                    !attendanceMembers.find(a => a.persona_id === m.id);
                                            })
                                            .slice(0, 8)
                                            .map(m => (
                                                <button key={m.id}
                                                    onClick={() => {
                                                        setAttendanceMembers(prev => [...prev, {
                                                            persona_id: m.id,
                                                            name: m.nombre_completo || `${m.first_name ?? ''} ${m.last_name ?? ''}`.trim(),
                                                            role: 'visitante',
                                                            status: 'first_time',
                                                            notes: '',
                                                        }]);
                                                        setVisitorSearch('');
                                                        setShowVisitorSearch(false);
                                                    }}
                                                    className="w-full text-left px-3 py-2 rounded-md text-xs text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-white/5 flex items-center gap-2 transition-colors">
                                                    <UserPlus size={12} className="text-[hsl(var(--primary))] shrink-0" />
                                                    <span className="font-medium">{m.nombre_completo || `${m.first_name ?? ''} ${m.last_name ?? ''}`.trim()}</span>
                                                    {m.church_role && <span className="text-slate-400 text-[10px]">({m.church_role})</span>}
                                                </button>
                                            ))}
                                        {allMembers.filter(m => {
                                            const name = (m.nombre_completo || `${m.first_name ?? ''} ${m.last_name ?? ''}`).toLowerCase();
                                            return name.includes(visitorSearch.toLowerCase()) && !attendanceMembers.find(a => a.persona_id === m.id);
                                        }).length === 0 && (
                                            <p className="text-center py-3 text-xs text-slate-400">No se encontraron personas</p>
                                        )}
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                </div>
            </WorkspaceDrawer>
            <ConfirmActionDrawer action={confirmAction} onClose={() => setConfirmAction(null)} />
        </EvangelismShell>
    );
}
