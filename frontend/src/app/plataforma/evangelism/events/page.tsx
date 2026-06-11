'use client';

import type {
BulkAttendanceSyncResult,
EventAudience,
EventDashboardStat,
EventSessionAttendanceData,
Member,
MinistryEvent,
RoleDefinition,
ScanValidationResult,
} from '@/app/plataforma/evangelism/types';
import { ViewType,getStoredView } from '@/components/ViewSwitcher';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';
import ConfirmActionDrawer, { type ConfirmActionState } from '@/components/evangelism/ConfirmActionDrawer';
import EvangelismShell from '@/components/evangelism/EvangelismShell';
import Skeleton from '@/components/ui/Skeleton';
import UniversalCalendarView from '@/components/ui/UniversalCalendarView';
import UniversalGanttView from '@/components/ui/UniversalGanttView';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { useWikiDocument } from '@/hooks/useWikiDocument';
import { apiFetch } from '@/lib/http';
import { parseAndValidateTime } from '@/lib/time';
import { Calendar,Check,Download,MoreVertical,Pencil,QrCode,Trash2 } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { QRCodeSVG } from 'qrcode.react';
import React,{ useEffect,useState } from 'react';
import { toast } from 'sonner';

const EVENT_TYPE_LABEL: Record<string, string> = {
 PERMANENT: 'Semanal',
 MONTHLY: 'Mensual',
 ANNUAL: 'Anual',
 ONCE: 'Única Vez',
 SPECIAL: 'Especial',
 FARO: 'Temporada - fuera del templo',
 ONLINE: 'En Línea',
};

const EVENT_TYPE_COLOR: Record<string, string> = {
 PERMANENT: 'bg-blue-100 dark:bg-blue-900/20 text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))]',
 MONTHLY: 'bg-blue-100 dark:bg-blue-900/20 text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))]',
 ANNUAL: 'bg-amber-100 dark:bg-amber-900/20 text-amber-700 dark:text-amber-400',
 ONCE: 'bg-rose-100 dark:bg-rose-900/20 text-rose-700 dark:text-rose-400',
 SPECIAL: 'bg-orange-100 dark:bg-orange-900/20 text-orange-700 dark:text-orange-400',
 FARO: 'bg-emerald-100 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-400',
 ONLINE: 'bg-cyan-100 dark:bg-cyan-900/20 text-cyan-700 dark:text-cyan-400',
};

const DAY_LABELS = ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado'];

interface AudiencePreset {
 id: string;
 name: string;
 target_audience: 'ALL' | 'ROLE' | 'MANUAL';
 target_role_ids: number[];
 target_persona_ids: string[];
}



export default function EventsPage() {
 const { token } = useAuth();
 const router = useRouter();
 const { addToast } = useToast();
 const [viewType, setViewType] = useState<ViewType>(() => getStoredView('evangelism_events_view', 'grid'));
 const ALL_VIEWS: ViewType[] = ['table', 'list', 'grid', 'board', 'kanban', 'gantt', 'calendar', 'wiki'];
 const [events, setEvents] = useState<MinistryEvent[]>([]);
 const [members, setMembers] = useState<Member[]>([]);
 const [stats, setStats] = useState<EventDashboardStat[]>([]);
 const [loading, setLoading] = useState(true);
 const { content: wikiNotes, setContent: setWikiNotes } = useWikiDocument('evangelism_events_wiki_notes', {
 title: 'Wiki de eventos de evangelismo',
 });

 // Drawer states (NO modals)
 const [isCreateDrawerOpen, setIsCreateDrawerOpen] = useState(false);
 const [isAttendanceDrawerOpen, setIsAttendanceDrawerOpen] = useState(false);
 const [isQrDrawerOpen, setIsQrDrawerOpen] = useState(false);
 const [confirmAction, setConfirmAction] = useState<ConfirmActionState>(null);
 const [selectedEvent, setSelectedEvent] = useState<MinistryEvent | null>(null);

 // Scanner
 const [showScanner, setShowScanner] = useState(false);
 const [scannerToken, setScannerToken] = useState('');
 const [isScanning, setIsScanning] = useState(false);

 // Form states
 const [newEvent, setNewEvent] = useState({
 name: '',
 description: '',
 event_type: 'PERMANENT',
 target_audience: 'ALL',
 target_role_id: '',
 target_role_ids: [] as string[],
 target_persona_ids: [] as string[],
 day_of_week: '0',
 month_day: '',
 fixed_date: '',
 start_time: '',
 end_time: ''
 });

 const [roles, setRoles] = useState<RoleDefinition[]>([]);
 const [editingEvent, setEditingEvent] = useState<MinistryEvent | null>(null);
 const [deletingEventId, setDeletingEventId] = useState<number | null>(null);
 const [menuOpenId, setMenuOpenId] = useState<number | null>(null);
 const [savingCreateEvent, setSavingCreateEvent] = useState(false);
 const [savingAttendance, setSavingAttendance] = useState(false);
 const [updatingEventId, setUpdatingEventId] = useState<number | null>(null);
 const [deletingEventLoadingId, setDeletingEventLoadingId] = useState<number | null>(null);

 useEffect(() => {
 if (token) {
 apiFetch<RoleDefinition[]>('/evangelism/roles', { token }).then(setRoles).catch(() => {});
 }
 }, [token]);

 // Attendance State
 const [attendanceDate, setAttendanceDate] = useState(new Date().toISOString().split('T')[0]);
 const [attendedMemberIds, setAttendedMemberIds] = useState<string[]>([]);
 const [attendanceSearch, setAttendanceSearch] = useState('');
 const [attendanceLoading, setAttendanceLoading] = useState(false);
 const [attendanceRoleFilter, setAttendanceRoleFilter] = useState('ALL');
 const [attendanceStatusFilter, setAttendanceStatusFilter] = useState<'ALL' | 'PENDING' | 'PRESENT'>('ALL');
 const [createManualSearch, setCreateManualSearch] = useState('');
 const [editManualSearch, setEditManualSearch] = useState('');
 const [audiencePresets, setAudiencePresets] = useState<AudiencePreset[]>([]);

 const handleScanToken = async () => {
 if (!scannerToken || !selectedEvent) return;
 setIsScanning(true);
 try {
 const result = await apiFetch<ScanValidationResult>(`/evangelism/scanner/validate/${scannerToken}`, {
 method: 'POST',
 token
 });
 if (result.valid) {
 const pid = result.persona_id;
 if (!attendedMemberIds.includes(pid)) {
 setAttendedMemberIds(prev => [...prev, pid]);
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
 if (!token) return;
 setLoading(true);
 try {
 const [eventsRes, membersRes, statsRes] = await Promise.all([
 apiFetch<MinistryEvent[]>('/evangelism/events/', { token, cache: 'no-store' }),
 apiFetch<Member[]>('/crm/personas', { token, query: { limit: 200 }, cache: 'no-store' }),
 apiFetch<EventDashboardStat[]>('/evangelism/events/dashboard-stats', { token, cache: 'no-store' })
 ]);
 setEvents(Array.isArray(eventsRes) ? eventsRes : []);
 setMembers(Array.isArray(membersRes) ? membersRes : []);
 setStats(Array.isArray(statsRes) ? statsRes : []);
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
 try {
 const raw = localStorage.getItem('evangelism_event_audience_presets');
 if (!raw) return;
 const parsed = JSON.parse(raw);
 if (!Array.isArray(parsed)) return;
 setAudiencePresets(parsed.filter((item) =>
 item &&
 typeof item.id === 'string' &&
 typeof item.name === 'string' &&
 ['ALL', 'ROLE', 'MANUAL'].includes(item.target_audience)
 ));
 } catch {
 localStorage.removeItem('evangelism_event_audience_presets');
 }
 }, []);

 useEffect(() => {
 localStorage.setItem('evangelism_event_audience_presets', JSON.stringify(audiencePresets));
 }, [audiencePresets]);

 const getTargetRoleIds = (event: MinistryEvent | null | undefined) => {
 if (!event) return [];
 if (Array.isArray(event.target_role_ids) && event.target_role_ids.length > 0) {
 return event.target_role_ids;
 }
 return event.target_role_id ? [event.target_role_id] : [];
 };

 const getTargetRoleLabel = (event: MinistryEvent | null | undefined) => {
 if (!event) return 'Toda la iglesia';
 if (event.target_audience === 'MANUAL') {
 const count = Array.isArray(event.target_persona_ids) ? event.target_persona_ids.length : 0;
 return count > 0 ? `${count} personas` : 'Selección manual';
 }
 if (event.target_audience !== 'ROLE') return 'Toda la iglesia';
 const roleNames = getTargetRoleIds(event)
 .map((roleId) => roles.find((role) => role.id === roleId)?.name)
 .filter(Boolean) as string[];
 if (roleNames.length === 0) return 'Roles específicos';
 if (roleNames.length === 1) return `Rol: ${roleNames[0]}`;
 return `${roleNames.length} roles`;
 };

 const sortedMembers = [...members].sort((a, b) =>
 (a.nombre_completo || '').localeCompare(b.nombre_completo || '')
 );

 const filterMembersByQuery = (query: string) => {
 const normalized = query.trim().toLowerCase();
 if (!normalized) return sortedMembers;
 return sortedMembers.filter((member) =>
 (member.nombre_completo || '').toLowerCase().includes(normalized) ||
 member.email.toLowerCase().includes(normalized) ||
 (member.church_role || '').toLowerCase().includes(normalized)
 );
 };

 const createManualMembers = filterMembersByQuery(createManualSearch);
 const editManualMembers = filterMembersByQuery(editManualSearch);

 const applyPresetToCreateEvent = (presetId: string) => {
 const preset = audiencePresets.find((item) => item.id === presetId);
 if (!preset) return;
 setNewEvent((prev) => ({
 ...prev,
 target_audience: preset.target_audience,
 target_role_id: preset.target_audience === 'ROLE' && preset.target_role_ids[0] ? String(preset.target_role_ids[0]) : '',
 target_role_ids: preset.target_audience === 'ROLE' ? preset.target_role_ids.map(String) : [],
 target_persona_ids: preset.target_audience === 'MANUAL' ? preset.target_persona_ids : [],
 }));
 setCreateManualSearch('');
 addToast(`Plantilla aplicada: ${preset.name}`, "success");
 };

 const applyPresetToEditingEvent = (presetId: string) => {
 const preset = audiencePresets.find((item) => item.id === presetId);
 if (!preset || !editingEvent) return;
 setEditingEvent({
 ...editingEvent,
 target_audience: preset.target_audience,
 target_role_id: preset.target_audience === 'ROLE' ? (preset.target_role_ids[0] || null) : null,
 target_role_ids: preset.target_audience === 'ROLE' ? preset.target_role_ids : [],
 target_persona_ids: preset.target_audience === 'MANUAL' ? preset.target_persona_ids : [],
 });
 setEditManualSearch('');
 addToast(`Plantilla aplicada: ${preset.name}`, "success");
 };

 const saveAudiencePreset = (source: { target_audience: string; target_role_ids?: Array<string | number>; target_persona_ids?: Array<string | number> }) => {
 const targetAudience = source.target_audience as AudiencePreset['target_audience'];
 const targetRoleIds = (source.target_role_ids || []).map((value) => Number(value)).filter((value) => Number.isFinite(value));
 const targetPersonaIds = (source.target_persona_ids || []).map(String);

 if (targetAudience === 'ROLE' && targetRoleIds.length === 0) {
 addToast("No puedes guardar una plantilla de roles sin roles seleccionados", "error");
 return;
 }
 if (targetAudience === 'MANUAL' && targetPersonaIds.length === 0) {
 addToast("No puedes guardar una plantilla manual sin personas seleccionadas", "error");
 return;
 }

 const name = window.prompt('Nombre de la plantilla de audiencia');
 if (!name || !name.trim()) return;

 setAudiencePresets((prev) => [
 {
 id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
 name: name.trim(),
 target_audience: targetAudience,
 target_role_ids: targetAudience === 'ROLE' ? targetRoleIds : [],
 target_persona_ids: targetAudience === 'MANUAL' ? targetPersonaIds : [],
 },
 ...prev,
 ]);
 addToast(`Plantilla guardada: ${name.trim()}`, "success");
 };

 const deleteAudiencePreset = (presetId: string) => {
 setAudiencePresets((prev) => prev.filter((preset) => preset.id !== presetId));
 addToast("Plantilla eliminada", "info");
 };

 const addSuggestedAudiencePresets = () => {
 const normalized = (value: string) =>
 value
 .toLowerCase()
 .normalize('NFD')
 .replace(/[\u0300-\u036f]/g, '');

 const existingNames = new Set(audiencePresets.map((preset) => normalized(preset.name)));
 const roleNameToId = new Map<string, number>(
 roles
 .filter((role) => role && typeof role.id === 'number' && typeof role.name === 'string')
 .map((role) => [normalized(role.name), role.id])
 );

 const findRoleIdsByKeywords = (keywords: string[]) => {
 const wanted = keywords.map(normalized);
 const ids = new Set<number>();
 for (const [roleName, roleId] of roleNameToId.entries()) {
 if (wanted.some((kw) => roleName.includes(kw))) ids.add(roleId);
 }
 return Array.from(ids);
 };

 const suggestions: Array<{ name: string; roleKeywords: string[] }> = [
 { name: 'Lideres', roleKeywords: ['lider'] },
 { name: 'Ujieres', roleKeywords: ['ujier'] },
 { name: 'Alabanza', roleKeywords: ['alabanza', 'worship'] },
 { name: 'Maestros', roleKeywords: ['maestro', 'docente'] },
 { name: 'Intercesion', roleKeywords: ['interces'] },
 ];

 const toAdd: AudiencePreset[] = [];
 for (const suggestion of suggestions) {
 const suggestionName = normalized(suggestion.name);
 if (existingNames.has(suggestionName)) continue;
 const roleIds = findRoleIdsByKeywords(suggestion.roleKeywords);
 if (roleIds.length === 0) continue;
 toAdd.push({
 id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
 name: suggestion.name,
 target_audience: 'ROLE',
 target_role_ids: roleIds,
 target_persona_ids: [],
 });
 }

 if (toAdd.length === 0) {
 addToast("No hay sugerencias disponibles para tus roles actuales", "info");
 return;
 }

 setAudiencePresets((prev) => [...toAdd, ...prev]);
 addToast(`Sugerencias agregadas: ${toAdd.length}`, "success");
 };

 const handleCreateEvent = async (e: React.FormEvent) => {
 e.preventDefault();
 if (!newEvent.name) return;
 if (newEvent.target_audience === 'ROLE' && newEvent.target_role_ids.length === 0) {
 addToast("Selecciona al menos un rol esperado para este evento", "error");
 return;
 }
 if (newEvent.target_audience === 'MANUAL' && newEvent.target_persona_ids.length === 0) {
 addToast("Selecciona al menos una persona esperada para este evento", "error");
 return;
 }

 if (!newEvent.start_time) {
 addToast("La hora de inicio es requerida", "error");
 return;
 }
 if (!newEvent.end_time) {
 addToast("La hora de finalización es requerida", "error");
 return;
 }

 const startParsed = parseAndValidateTime(newEvent.start_time);
 if (!startParsed.valid) {
 addToast("Formato de hora de inicio inválido (use HH:MM)", "error");
 return;
 }

 const endParsed = parseAndValidateTime(newEvent.end_time);
 if (!endParsed.valid) {
 addToast("Formato de hora de finalización inválido (use HH:MM)", "error");
 return;
 }

 if (endParsed.minutes <= startParsed.minutes) {
 addToast("La hora de finalización debe ser posterior a la hora de inicio", "error");
 return;
 }

 const payload: {
 name: string;
 description: string;
 event_type: string;
 target_audience: string;
 target_role_id: number | null;
 target_role_ids: number[];
 target_persona_ids: string[];
 start_time: string;
 end_time: string;
 day_of_week?: number;
 month_day?: string;
 fixed_date?: string;
 } = {
 name: newEvent.name,
 description: newEvent.description,
 event_type: newEvent.event_type,
 target_audience: newEvent.target_audience,
 target_role_id: newEvent.target_audience === 'ROLE' && newEvent.target_role_ids[0] ? Number(newEvent.target_role_ids[0]) : null,
 target_role_ids: newEvent.target_audience === 'ROLE' ? newEvent.target_role_ids.map((value) => Number(value)) : [],
 target_persona_ids: newEvent.target_audience === 'MANUAL' ? newEvent.target_persona_ids : [],
 start_time: startParsed.normalized,
 end_time: endParsed.normalized,
 };

 if (['PERMANENT', 'FARO', 'ONLINE'].includes(newEvent.event_type)) payload.day_of_week = parseInt(newEvent.day_of_week);
 if (['ANNUAL', 'MONTHLY'].includes(newEvent.event_type)) payload.month_day = newEvent.month_day;
 if (['ONCE', 'SPECIAL'].includes(newEvent.event_type)) payload.fixed_date = new Date(newEvent.fixed_date).toISOString();

 try {
 setSavingCreateEvent(true);
 await apiFetch('/evangelism/events/', { method: 'POST', token, body: payload });
 addToast("Evento creado exitosamente", "success");
 setIsCreateDrawerOpen(false);
 setNewEvent({ name: '', description: '', event_type: 'PERMANENT', target_audience: 'ALL', target_role_id: '', target_role_ids: [], target_persona_ids: [], day_of_week: '0', month_day: '', fixed_date: '', start_time: '', end_time: '' });
 fetchData();
 } catch (error: any) {
 const msg = error?.message || "Error de conexión";
 addToast(msg, "error");
 } finally {
 setSavingCreateEvent(false);
 }
 };

 const getExpectedUniverseCount = (event: MinistryEvent) => {
 if (event.target_audience === 'ROLE') {
 const roleNames = getTargetRoleIds(event)
 .map((roleId) => roles.find((role) => role.id === roleId)?.name)
 .filter(Boolean) as string[];
 if (roleNames.length === 0) return 0;
 return members.filter((member) => roleNames.includes((member.church_role || '').trim())).length;
 }
 if (event.target_audience === 'MANUAL') {
 return Array.isArray(event.target_persona_ids) ? event.target_persona_ids.length : 0;
 }
 return members.length;
 };

 const getEventAttendanceStat = (event: MinistryEvent) => {
 const stat = stats.find((item) => item.event_id === event.id);
 if (stat) return stat;

 const expected = getExpectedUniverseCount(event);
 return {
 event_id: event.id,
 latest_session: null,
 attended: 0,
 expected,
 rate: 0,
 };
 };


 const openQr = (ev: MinistryEvent) => {
 setSelectedEvent(ev);
 setIsQrDrawerOpen(true);
 };

 const downloadQr = () => {
 const svg = document.getElementById('event-qr-code');
 if (!svg) return;
 const svgData = new XMLSerializer().serializeToString(svg);
 const canvas = document.createElement('canvas');
 const ctx = canvas.getContext('2d');
 const img = new Image();
 img.onload = () => {
 canvas.width = img.width;
 canvas.height = img.height;
 if(ctx) {
 ctx.fillStyle = 'white';
 ctx.fillRect(0, 0, canvas.width, canvas.height);
 ctx.drawImage(img, 0, 0);
 }
 const pngFile = canvas.toDataURL('image/png');
 const downloadLink = document.createElement('a');
 downloadLink.download = `QR_${selectedEvent?.name}.png`;
 downloadLink.href = pngFile;
 downloadLink.click();
 };
 img.src = 'data:image/svg+xml;base64,' + btoa(unescape(encodeURIComponent(svgData)));
 };

 const openAttendance = (ev: MinistryEvent) => {
 setSelectedEvent(ev);
 setIsAttendanceDrawerOpen(true);
 setAttendanceDate(new Date().toISOString().split('T')[0]);
 setAttendedMemberIds([]);
 setShowScanner(false);
 setAttendanceSearch('');
 setAttendanceRoleFilter('ALL');
 setAttendanceStatusFilter('ALL');
 };

 useEffect(() => {
 if (!token || !selectedEvent || !isAttendanceDrawerOpen || !attendanceDate) return;

 const loadAttendanceSession = async () => {
 setAttendanceLoading(true);
 try {
 const data = await apiFetch<EventSessionAttendanceData>(`/evangelism/events/${selectedEvent.id}/sessions/${attendanceDate}`, { token });
 setAttendedMemberIds(Array.isArray(data?.attendees) ? data.attendees.map((item) => item.persona_id) : []);
 } catch {
 setAttendedMemberIds([]);
 addToast("No se pudo cargar la asistencia guardada para esa fecha", "error");
 } finally {
 setAttendanceLoading(false);
 }
 };

 loadAttendanceSession();
 }, [addToast, attendanceDate, isAttendanceDrawerOpen, selectedEvent, token]);

 const saveAttendance = async (forceEmpty = false) => {
 if (!selectedEvent) return;
 const normalizedStatus = String(selectedEvent.status || '').toUpperCase();
 if (normalizedStatus === 'CANCELLED' || normalizedStatus === 'CANCELED') {
 addToast("No se puede registrar asistencia en eventos cancelados", "error");
 return;
 }
 if (!forceEmpty && expectedUniverseMembers.length > 0 && attendedMemberIds.length === 0) {
 setConfirmAction({
 title: 'Guardar asistencia en cero',
 description: 'Vas a guardar 0 presentes y marcar pendientes como ausentes para esta fecha.',
 confirmLabel: 'Guardar',
 destructive: true,
 onConfirm: () => saveAttendance(true),
 });
 return;
 }
 setSavingAttendance(true);
 try {
 const result = await apiFetch<BulkAttendanceSyncResult>('/evangelism/attendance/bulk', {
 method: 'POST',
 token,
 body: {
 event_id: selectedEvent.id,
 persona_ids: attendedMemberIds,
 attendance_date: attendanceDate
 }
 });
 addToast(
 `Asistencia sincronizada (${result.recorded} presentes, ${result.marked_absent ?? 0} ausentes)`,
 "success"
 );
 setIsAttendanceDrawerOpen(false);
 fetchData();
 } catch {
 addToast("Error al guardar asistencia", "error");
 } finally {
 setSavingAttendance(false);
 }
 };

 const toggleAttendance = (id: string) => {
 setAttendedMemberIds(prev =>
 prev.includes(id) ? prev.filter(mId => mId !== id) : [...prev, id]
 );
 };

 const expectedUniverseMembers = members.filter((member) => {
 if (!selectedEvent) {
 return true;
 }
 if (selectedEvent.target_audience === 'MANUAL') {
 return Array.isArray(selectedEvent.target_persona_ids) && selectedEvent.target_persona_ids.includes(member.id);
 }
 if (selectedEvent.target_audience !== 'ROLE') {
 return true;
 }
 const roleNames = getTargetRoleIds(selectedEvent)
 .map((roleId) => roles.find((role) => role.id === roleId)?.name)
 .filter(Boolean) as string[];
 return roleNames.length > 0 && roleNames.includes((member.church_role || '').trim());
 });

 const attendanceRoleOptions = Array.from(
 new Set(
 expectedUniverseMembers
 .map((member) => member.church_role?.trim())
 .filter((role): role is string => Boolean(role))
 )
 ).sort((a, b) => a.localeCompare(b));

 const filteredMembers = expectedUniverseMembers.filter((member) => {
 const query = attendanceSearch.trim().toLowerCase();
 const matchesSearch = !query || (member.nombre_completo || '').toLowerCase().includes(query) || member.email.toLowerCase().includes(query);
 const matchesRole = attendanceRoleFilter === 'ALL' || (member.church_role || 'Sin rol') === attendanceRoleFilter;
 const isPresent = attendedMemberIds.includes(member.id);
 const matchesStatus =
 attendanceStatusFilter === 'ALL' ||
 (attendanceStatusFilter === 'PRESENT' && isPresent) ||
 (attendanceStatusFilter === 'PENDING' && !isPresent);

 return matchesSearch && matchesRole && matchesStatus;
 });

 const markFilteredMembers = () => {
 setAttendedMemberIds((prev) => {
 const next = new Set(prev);
 filteredMembers.forEach((member) => next.add(member.id));
 return Array.from(next);
 });
 };

 const clearFilteredMembers = () => {
 const filteredIds = new Set(filteredMembers.map((member) => member.id));
 setAttendedMemberIds((prev) => prev.filter((memberId) => !filteredIds.has(memberId)));
 };

 const getVisualDate = (event: MinistryEvent) => {
 if (event.fixed_date) return event.fixed_date;
 const current = new Date();
 const targetDay = Number(event.day_of_week ?? current.getDay());
 const next = new Date(current);
 const offset = (targetDay - current.getDay() + 7) % 7;
 next.setDate(current.getDate() + offset);
 return next.toISOString().split('T')[0];
 };

 const calendarEvents = events.map((event) => ({
 id: event.id,
 title: event.name,
 date: getVisualDate(event),
 color: event.status === 'CANCELLED' ? 'rose' as const : 'blue' as const,
 location: getTargetRoleLabel(event),
 }));

 const ganttItems = events.map((event) => ({
 id: event.id,
 title: event.name,
 subtitle: getTargetRoleLabel(event),
 start_date: getVisualDate(event),
 end_date: getVisualDate(event),
 color: event.status === 'CANCELLED' ? 'rose' as const : 'emerald' as const,
 progress: getEventAttendanceStat(event).rate,
 }));

 const boardColumns = [
 {
 key: 'active',
 label: 'Programados',
 items: events.filter((event) => event.status !== 'CANCELLED' && event.event_type !== 'PERMANENT'),
 },
 {
 key: 'permanent',
 label: 'Recurrentes',
 items: events.filter((event) => event.status !== 'CANCELLED' && event.event_type === 'PERMANENT'),
 },
 {
 key: 'cancelled',
 label: 'Cancelados',
 items: events.filter((event) => event.status === 'CANCELLED'),
 },
 ];

 const handleDeleteEvent = async (evId: number) => {
 if (!token) return;
 setDeletingEventLoadingId(evId);
 try {
 await apiFetch(`/evangelism/events/${evId}`, { method: 'DELETE', token });
 setEvents(prev => prev.filter(e => e.id !== evId));
 toast.success('Evento eliminado correctamente');
 } catch {
 toast.error('Error al eliminar el evento');
 } finally {
 setDeletingEventLoadingId(null);
 setDeletingEventId(null);
 }
 };

 const handleUpdateEvent = async (evId: number, payload: Partial<MinistryEvent> & {
 target_audience?: string;
 target_role_ids?: number[];
 target_persona_ids?: string[];
 }) => {
 if (!token) return;
 if (payload.target_audience === 'ROLE' && (!Array.isArray(payload.target_role_ids) || payload.target_role_ids.length === 0)) {
 toast.error('Selecciona al menos un rol esperado antes de guardar');
 return;
 }
 if (payload.target_audience === 'MANUAL' && (!Array.isArray(payload.target_persona_ids) || payload.target_persona_ids.length === 0)) {
 toast.error('Selecciona al menos una persona esperada antes de guardar');
 return;
 }

 // Validate and normalize times if they are modified or provided
 if (payload.start_time || payload.end_time) {
 if (payload.start_time) {
 const startParsed = parseAndValidateTime(payload.start_time);
 if (!startParsed.valid) {
 toast.error("Formato de hora de inicio inválido (use HH:MM)");
 return;
 }
 payload.start_time = startParsed.normalized;
 }
 if (payload.end_time) {
 const endParsed = parseAndValidateTime(payload.end_time);
 if (!endParsed.valid) {
 toast.error("Formato de hora de finalización inválido (use HH:MM)");
 return;
 }
 payload.end_time = endParsed.normalized;
 }

 const currentStartTime = payload.start_time || editingEvent?.start_time || '';
 const currentEndTime = payload.end_time || editingEvent?.end_time || '';
 if (currentStartTime && currentEndTime) {
 const startParsed = parseAndValidateTime(currentStartTime);
 const endParsed = parseAndValidateTime(currentEndTime);
 if (startParsed.valid && endParsed.valid && endParsed.minutes <= startParsed.minutes) {
 toast.error("La hora de finalización debe ser posterior a la hora de inicio");
 return;
 }
 }
 }

 setUpdatingEventId(evId);
 try {
 await apiFetch(`/evangelism/events/${evId}`, { method: 'PUT', body: payload, token });
 setEvents(prev => prev.map(e => e.id === evId ? { ...e, ...payload } : e));
 toast.success('Evento actualizado');
 setEditingEvent(null);
 } catch (error: any) {
 const msg = error?.message || 'Error al actualizar el evento';
 toast.error(msg);
 } finally {
 setUpdatingEventId(null);
 }
 };

 if (loading) {
 return (
 <EvangelismShell breadcrumbs={[{ label: 'Evangelismo' }, { label: 'Eventos' }]}>
 <div className="p-4 space-y-3">
 <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
 {[1, 2, 3, 4, 5, 6].map(i => <Skeleton key={i} className="h-48 rounded-lg" />)}
 </div>
 </div>
 </EvangelismShell>
 );
 }

 return (
 <EvangelismShell
 breadcrumbs={[{ label: 'Evangelismo' }, { label: 'Eventos' }]}
 viewOptions={ALL_VIEWS}
 viewType={viewType}
 onViewChange={(view) => setViewType(view as ViewType)}
 onAdd={() => setIsCreateDrawerOpen(true)}
 >
 <div className="p-4 space-y-3">
 {/* GRID VIEW */}
 {viewType === 'grid' && (
 <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
 {events.length === 0 ? (
 <div className="col-span-3 py-1.5 text-center text-[hsl(var(--text-secondary))] text-sm">
 No hay eventos registrados
 </div>
 ) : events.map(ev => (
 (() => {
 const attendanceStat = getEventAttendanceStat(ev);
 return (
 <div 
 key={ev.id} 
 onClick={() => router.push(`/plataforma/evangelism/events/${ev.id}`)}
 className="p-4 rounded-md border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] hover:border-blue-500/30 hover:shadow-2xl hover:shadow-blue-500/10 transition-all group flex flex-col justify-between cursor-pointer"
 >
 <div>
 <div className="flex justify-between items-start mb-4">
 <div className="flex gap-2 items-center">
 <div className="w-12 h-8 rounded-lg bg-gradient-to-tr from-blue-50 to-sky-50 text-[hsl(var(--primary))] flex items-center justify-center">
 <Calendar size={20} />
 </div>
 {ev.status === 'CANCELLED' && (
 <span className="px-3 py-1 text-[10px] font-semibold uppercase tracking-wide rounded-full bg-red-100 dark:bg-red-900/20 text-[hsl(var(--destructive))] dark:text-[hsl(var(--destructive))]" title={ev.cancellation_reason}>
 Cancelado
 </span>
 )}
 </div>
 <span className={`px-3 py-1 text-[10px] font-semibold uppercase tracking-wide rounded-full ${EVENT_TYPE_COLOR[ev.event_type] ?? 'bg-[hsl(var(--bg-muted))] text-[hsl(var(--text-secondary))]'}`}>
 {EVENT_TYPE_LABEL[ev.event_type] ?? ev.event_type}
 </span>
 </div>
 <h3 className="text-sm font-semibold text-[hsl(var(--text-primary))] mb-2 truncate group-hover:text-[hsl(var(--primary))] transition-colors uppercase italic pr-4">
 {ev.name}
 </h3>
 <p className="text-sm font-medium text-[hsl(var(--text-secondary))] line-clamp-2">{ev.description || 'Evento comunitario de CCF.'}</p>
 <div className="mt-3 flex flex-wrap gap-2">
 <span className="px-2.5 py-1 rounded-full text-[10px] font-semibold uppercase tracking-wide bg-[hsl(var(--bg-muted))] text-[hsl(var(--text-secondary))]">
 {getTargetRoleLabel(ev)}
 </span>
 <span className="px-2.5 py-1 rounded-full text-[10px] font-semibold uppercase tracking-wide bg-blue-50 dark:bg-blue-900/20 text-[hsl(var(--primary))] dark:text-blue-300">
 Universo: {attendanceStat.expected}
 </span>
 <span className="px-2.5 py-1 rounded-full text-[10px] font-semibold uppercase tracking-wide bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-300">
 {attendanceStat.attended} / {attendanceStat.expected || 0} ({attendanceStat.rate}%)
 </span>
 </div>
 </div>
 <div className="mt-3 flex items-center justify-between gap-2">
 <button onClick={(e) => { e.stopPropagation(); openQr(ev); }} className="size-8 flex items-center justify-center bg-[hsl(var(--bg-muted))] hover:bg-[hsl(var(--primary))] text-[hsl(var(--text-secondary))] hover:text-white rounded-md transition-all shrink-0" title="Generar QR">
 <QrCode size={16} />
 </button>
 <button onClick={(e) => { e.stopPropagation(); openAttendance(ev); }} className="flex-1 py-1.5 bg-[hsl(var(--bg-muted))] group-hover:bg-[hsl(var(--primary))] text-[hsl(var(--text-secondary))] group-hover:text-white rounded-md text-[10px] font-semibold uppercase tracking-wide transition-all">
 Panel de Asistencia
 </button>
 <div className="relative shrink-0" onClick={e => e.stopPropagation()}>
 <button
 onClick={() => setMenuOpenId(menuOpenId === ev.id ? null : ev.id)}
 className="size-8 flex items-center justify-center bg-[hsl(var(--bg-muted))] hover:bg-[hsl(var(--bg-muted))] text-[hsl(var(--text-secondary))] rounded-md transition-all"
 >
 <MoreVertical size={16} />
 </button>
 {menuOpenId === ev.id && (
 <div className="absolute right-0 bottom-12 z-50 bg-[hsl(var(--bg-primary))] dark:bg-[#18181b] border border-[hsl(var(--border-primary))] rounded-lg shadow-2xl overflow-hidden w-40 animate-in fade-in slide-in-from-bottom-2">
 <button
 onClick={() => { setEditingEvent({ ...ev, target_role_ids: getTargetRoleIds(ev) }); setMenuOpenId(null); }}
 className="w-full flex items-center gap-3 px-4 py-1.5 text-sm font-bold text-[hsl(var(--text-primary))] hover:bg-blue-50 dark:hover:bg-white/5 transition-all"
 >
 <Pencil size={14} className="text-[hsl(var(--primary))]" /> Editar
 </button>
 <button
 onClick={() => { setDeletingEventId(ev.id); setMenuOpenId(null); }}
 className="w-full flex items-center gap-3 px-4 py-1.5 text-sm font-bold text-[hsl(var(--destructive))] hover:bg-red-50 dark:hover:bg-red-900/10 transition-all"
 >
 <Trash2 size={14} /> Eliminar
 </button>
 </div>
 )}
 </div>
 </div>
 </div>
 );
 })()
 ))}
 </div>
 )}

 {/* LIST VIEW */}
 {viewType === 'list' && (
 <div className="bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] rounded-md border border-[hsl(var(--border-primary))] overflow-hidden shadow-sm divide-y divide-[hsl(var(--border-primary))]">
 {events.map(ev => {
 const attendanceStat = getEventAttendanceStat(ev);
 return (
 <div key={ev.id} className="flex items-center gap-4 px-4 py-2 hover:bg-[hsl(var(--bg-muted))] dark:hover:bg-white/5 transition-colors group">
 <div className="w-9 h-9 rounded-md bg-blue-50 dark:bg-blue-900/20 text-[hsl(var(--primary))] flex items-center justify-center shrink-0">
 <Calendar size={16} />
 </div>
 <div className="flex-1 min-w-0">
 <p 
 onClick={() => router.push(`/plataforma/evangelism/events/${ev.id}`)}
 className="font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-primary))] text-sm truncate cursor-pointer hover:text-[hsl(var(--primary))] transition-colors"
 >
 {ev.name}
 </p>
 <p className="text-xs text-[hsl(var(--text-secondary))] truncate">{ev.description || 'Sin descripción'}</p>
 </div>
 <div className="flex gap-2 items-center">
 {ev.status === 'CANCELLED' && (
 <span className="px-2.5 py-0.5 rounded-full text-[10px] font-semibold uppercase bg-red-100 dark:bg-red-900/20 text-[hsl(var(--destructive))] dark:text-[hsl(var(--destructive))]" title={ev.cancellation_reason}>
 Cancelado
 </span>
 )}
 <span className="px-2.5 py-0.5 rounded-full text-[10px] font-semibold uppercase bg-[hsl(var(--bg-muted))] text-[hsl(var(--text-secondary))]">
 {getTargetRoleLabel(ev)}
 </span>
 <span className="px-2.5 py-0.5 rounded-full text-[10px] font-semibold uppercase bg-blue-50 dark:bg-blue-900/20 text-[hsl(var(--primary))] dark:text-blue-300">
 Universo: {attendanceStat.expected}
 </span>
 <span className="px-2.5 py-0.5 rounded-full text-[10px] font-semibold uppercase bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-300">
 {attendanceStat.attended} / {attendanceStat.expected || 0} ({attendanceStat.rate}%)
 </span>
 <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-semibold uppercase ${EVENT_TYPE_COLOR[ev.event_type] ?? 'bg-[hsl(var(--bg-muted))] text-[hsl(var(--text-secondary))]'}`}>
 {EVENT_TYPE_LABEL[ev.event_type] ?? ev.event_type}
 </span>
 </div>
 <button onClick={(e) => { e.stopPropagation(); openQr(ev); }} className="px-3 py-1.5 rounded-md bg-blue-50 dark:bg-blue-900/20 text-[hsl(var(--primary))] text-[10px] font-semibold uppercase opacity-0 group-hover:opacity-100 transition-opacity mr-2">
 QR
 </button>
 <button onClick={(e) => { e.stopPropagation(); openAttendance(ev); }} className="px-3 py-1.5 rounded-md bg-blue-50 dark:bg-blue-900/20 text-[hsl(var(--primary))] text-[10px] font-semibold uppercase opacity-0 group-hover:opacity-100 transition-opacity">
 Asistencia
 </button>
 </div>
 );
 })}
 </div>
 )}

 {viewType === 'table' && (
 <div className="overflow-hidden rounded-md border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] shadow-sm">
 <table className="w-full text-left">
 <thead className="bg-[hsl(var(--bg-muted))]">
 <tr>
 {['Evento', 'Tipo', 'Audiencia', 'Universo', 'Asistencia', 'Fecha visual'].map((label) => (
 <th key={label} className="px-3 py-2 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
 {label}
 </th>
 ))}
 </tr>
 </thead>
 <tbody>
 {events.map((event) => {
 const attendanceStat = getEventAttendanceStat(event);
 return (
 <tr key={event.id} className="border-t border-[hsl(var(--border-primary))] hover:bg-[hsl(var(--bg-muted))]">
 <td className="px-3 py-2">
 <button onClick={() => router.push(`/plataforma/evangelism/events/${event.id}`)} className="font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-primary))] hover:text-[hsl(var(--primary))]">
 {event.name}
 </button>
 </td>
 <td className="px-3 py-2 text-xs font-bold text-[hsl(var(--text-secondary))]">{EVENT_TYPE_LABEL[event.event_type] ?? event.event_type}</td>
 <td className="px-3 py-2 text-xs text-[hsl(var(--text-secondary))]">{getTargetRoleLabel(event)}</td>
 <td className="px-3 py-2 text-xs text-[hsl(var(--text-secondary))]">{attendanceStat.expected}</td>
 <td className="px-3 py-2 text-xs font-bold text-emerald-600">{attendanceStat.rate}%</td>
 <td className="px-3 py-2 text-xs text-[hsl(var(--text-secondary))]">{getVisualDate(event)}</td>
 </tr>
 );
 })}
 </tbody>
 </table>
 {events.length === 0 && <div className="py-2 text-center text-sm text-[hsl(var(--text-secondary))]">No hay eventos registrados</div>}
 </div>
 )}

 {(viewType === 'board' || viewType === 'kanban') && (
 <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
 {boardColumns.map((column) => (
 <section key={column.key} className="rounded-md border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] p-4 shadow-sm dark:bg-[#1e1f21]">
 <header className="mb-4 flex items-center justify-between">
 <h3 className="text-[11px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{column.label}</h3>
 <span className="rounded-full bg-[hsl(var(--bg-muted))] px-2 py-0.5 font-semibold text-[hsl(var(--text-secondary))] ">
 {column.items.length}
 </span>
 </header>
 <div className="space-y-3">
 {column.items.map((event) => {
 const attendanceStat = getEventAttendanceStat(event);
 return (
 <button
 key={event.id}
 onClick={() => router.push(`/plataforma/evangelism/events/${event.id}`)}
 className="w-full rounded-lg border border-[hsl(var(--border-primary))] p-4 text-left transition-all hover:border-blue-500/30 hover:shadow-lg "
 >
 <p className="text-sm font-semibold text-[hsl(var(--text-primary))]">{event.name}</p>
 <p className="mt-1 text-[11px] text-[hsl(var(--text-secondary))]">{getTargetRoleLabel(event)}</p>
 <div className="mt-3 flex items-center justify-between text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
 <span>{EVENT_TYPE_LABEL[event.event_type] ?? event.event_type}</span>
 <span>{attendanceStat.rate}%</span>
 </div>
 </button>
 );
 })}
 {column.items.length === 0 && <div className="py-2 text-center text-xs text-[hsl(var(--text-secondary))]">Sin eventos</div>}
 </div>
 </section>
 ))}
 </div>
 )}

 {viewType === 'calendar' && (
 <div className="rounded-md border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] p-4 shadow-sm dark:bg-[#1e1f21]">
 <UniversalCalendarView events={calendarEvents} title="Calendario de eventos" />
 </div>
 )}

 {viewType === 'gantt' && (
 <div className="rounded-md border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] p-4 shadow-sm dark:bg-[#1e1f21]">
 <UniversalGanttView items={ganttItems} moduleName="Eventos" />
 </div>
 )}

 {viewType === 'wiki' && (
 <section className="rounded-md border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] p-3 shadow-sm dark:bg-[#1e1f21]">
 <p className="mb-3 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Wiki de eventos</p>
 <textarea
 value={wikiNotes}
 onChange={(event) => setWikiNotes(event.target.value)}
 placeholder="Documenta protocolos, checklist de registro, roles y aprendizajes de cada evento..."
 className="min-h-[360px] w-full rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-muted))] p-4 text-sm font-medium text-[hsl(var(--text-primary))] outline-none focus:ring-2 focus:ring-blue-500/20 dark:bg-black/20 "
 />
 </section>
 )}
 </div>

 {/* â"€â"€â"€ Drawer: Crear Evento â"€â"€â"€ */}
 <WorkspaceDrawer
 isOpen={isCreateDrawerOpen}
 onClose={() => setIsCreateDrawerOpen(false)}
 title="Nuevo Evento"
 subtitle="Configura un evento de la iglesia"
 actions={
 <>
 <button type="button" disabled={savingCreateEvent} onClick={() => setIsCreateDrawerOpen(false)} className="px-4 py-2 text-[11px] font-bold text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] transition-colors disabled:opacity-60">
 Cancelar
 </button>
 <button
 form="create-event-form"
 type="submit"
 disabled={savingCreateEvent}
 className="px-3 py-2 bg-[hsl(var(--primary))] text-white rounded-lg text-[11px] font-semibold uppercase tracking-wide shadow-lg shadow-blue-500/20 hover:bg-[hsl(var(--primary))] active:scale-95 transition-all flex items-center gap-2 disabled:opacity-60 disabled:active:scale-100"
 >
 {savingCreateEvent ? 'Guardando...' : 'Guardar'} <Check size={14} />
 </button>
 </>
 }
 >
 <form id="create-event-form" onSubmit={handleCreateEvent} className="space-y-3">
 <div className="space-y-1.5">
 <label className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Nombre del Evento *</label>
 <input
 required
 value={newEvent.name}
 onChange={e => setNewEvent({ ...newEvent, name: e.target.value })}
 className="w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] dark:bg-black/20 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm text-[hsl(var(--text-primary))]"
 placeholder="Ej: Servicio Dominical"
 />
 </div>

 <div className="space-y-1.5">
 <label className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Tipo de Evento *</label>
 <select
 required
 value={newEvent.event_type}
 onChange={e => setNewEvent({ ...newEvent, event_type: e.target.value })}
 className="w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] dark:bg-black/20 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm text-[hsl(var(--text-primary))] appearance-none"
 >
 <option value="PERMANENT">Semanal / Rutinario</option>
 <option value="MONTHLY">Mensual</option>
 <option value="ANNUAL">Anual</option>
 <option value="ONCE">Única Vez / Fecha Fija</option>
 <option value="SPECIAL">Especial / Campaña</option>
 <option value="FARO">Temporada - fuera del templo</option>
 <option value="ONLINE">En Línea / Transmisión</option>
 </select>
 </div>

 <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
 <div className="space-y-1.5">
 <label className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Universo Esperado</label>
 <select
 value={newEvent.target_audience}
 onChange={e => setNewEvent({
 ...newEvent,
 target_audience: e.target.value,
 target_role_id: e.target.value === 'ROLE' ? newEvent.target_role_id : '',
 target_role_ids: e.target.value === 'ROLE' ? newEvent.target_role_ids : [],
 target_persona_ids: e.target.value === 'MANUAL' ? newEvent.target_persona_ids : [],
 })}
 className="w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] dark:bg-black/20 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm text-[hsl(var(--text-primary))] appearance-none"
 >
 <option value="ALL">Toda la iglesia</option>
 <option value="ROLE">Uno o varios roles</option>
 <option value="MANUAL">Selección manual</option>
 </select>
 </div>
 <div className="space-y-1.5">
 <label className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Roles esperados</label>
 <select
 multiple
 disabled={newEvent.target_audience !== 'ROLE'}
 value={newEvent.target_role_ids}
 onChange={e => {
 const selectedValues = Array.from(e.target.selectedOptions).map((option) => option.value);
 setNewEvent({ ...newEvent, target_role_ids: selectedValues, target_role_id: selectedValues[0] || '' });
 }}
 className="min-h-[140px] w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] dark:bg-black/20 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm text-[hsl(var(--text-primary))] disabled:opacity-50"
 >
 {roles.map((role) => (
 <option key={role.id} value={role.id}>{role.name}</option>
 ))}
 </select>
 </div>
 </div>

 <div className="space-y-3 rounded-md border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-muted))] dark:bg-black/20 p-4">
 <div className="flex items-center justify-between gap-3">
 <div>
 <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Plantillas de audiencia</p>
 <p className="text-sm font-bold text-[hsl(var(--text-primary))] ">Guarda y reaplica universos esperados frecuentes</p>
 </div>
 <div className="flex items-center gap-2">
 <button
 type="button"
 onClick={addSuggestedAudiencePresets}
 className="rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] px-4 py-2 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] transition-all hover:bg-[hsl(var(--bg-muted))] dark:hover:bg-white/10"
 >
 Sugerencias
 </button>
 <button
 type="button"
 onClick={() => saveAudiencePreset(newEvent)}
 className="rounded-lg bg-[hsl(var(--primary))] px-4 py-2 text-[10px] font-semibold uppercase tracking-wide text-white transition-all hover:bg-[hsl(var(--primary))]"
 >
 Guardar actual
 </button>
 </div>
 </div>
 <div className="space-y-2">
 {audiencePresets.length === 0 ? (
 <div className="rounded-lg border border-dashed border-[hsl(var(--border-primary))] px-4 py-2 text-center text-sm text-[hsl(var(--text-secondary))]">
 Aun no hay plantillas guardadas
 </div>
 ) : audiencePresets.map((preset) => (
 <div key={preset.id} className="flex items-center justify-between gap-3 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] px-4 py-1.5">
 <div className="min-w-0">
 <p className="truncate text-sm font-bold text-[hsl(var(--text-primary))]">{preset.name}</p>
 <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
 {preset.target_audience === 'ALL'
 ? 'Toda la iglesia'
 : preset.target_audience === 'ROLE'
 ? `${preset.target_role_ids.length} roles`
 : `${preset.target_persona_ids.length} personas`}
 </p>
 </div>
 <div className="flex items-center gap-2">
 <button
 type="button"
 onClick={() => applyPresetToCreateEvent(preset.id)}
 className="rounded-lg bg-[hsl(var(--bg-primary))] px-3 py-2 text-[10px] font-semibold uppercase tracking-wide text-white transition-all hover:opacity-85 "
 >
 Aplicar
 </button>
 <button
 type="button"
 onClick={() => deleteAudiencePreset(preset.id)}
 className="rounded-lg border border-[hsl(var(--border-primary))] px-3 py-2 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] transition-all hover:bg-[hsl(var(--bg-muted))]"
 >
 Borrar
 </button>
 </div>
 </div>
 ))}
 </div>
 </div>

 {newEvent.target_audience === 'MANUAL' && (
 <div className="space-y-3">
 <div className="flex items-center justify-between gap-3">
 <label className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Personas esperadas</label>
 <span className="rounded-full bg-blue-50 dark:bg-blue-900/20 px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--primary))] dark:text-blue-300">
 {newEvent.target_persona_ids.length} seleccionadas
 </span>
 </div>
 <input
 value={createManualSearch}
 onChange={e => setCreateManualSearch(e.target.value)}
 placeholder="Buscar por nombre, correo o rol..."
 className="w-full rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] dark:bg-black/20 px-4 py-1.5 text-sm font-bold text-[hsl(var(--text-primary))] outline-none focus:ring-2 focus:ring-blue-500/20"
 />
 <div className="max-h-48 space-y-2 overflow-y-auto rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-muted))] dark:bg-black/20 p-3">
 {createManualMembers.map((member) => {
 const isSelected = newEvent.target_persona_ids.includes(member.id);
 return (
 <button
 key={member.id}
 type="button"
 onClick={() => setNewEvent({
 ...newEvent,
 target_persona_ids: isSelected
 ? newEvent.target_persona_ids.filter((value) => value !== member.id)
 : [...newEvent.target_persona_ids, member.id],
 })}
 className={`flex w-full items-center justify-between rounded-lg border px-4 py-1.5 text-left transition-all ${
 isSelected
 ? 'border-blue-200 bg-blue-50 dark:border-blue-800 dark:bg-blue-900/20'
 : 'border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] '
 }`}
 >
 <div>
 <p className="text-sm font-bold text-[hsl(var(--text-primary))]">{member.nombre_completo}</p>
 <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{member.church_role || 'Sin rol'}</p>
 </div>
 <span className={`text-[10px] font-semibold uppercase tracking-wide ${isSelected ? 'text-[hsl(var(--primary))] dark:text-blue-300' : 'text-[hsl(var(--text-secondary))]'}`}>
 {isSelected ? 'Incluida' : 'Agregar'}
 </span>
 </button>
 );
 })}
 {createManualMembers.length === 0 && (
 <div className="py-2 text-center text-sm text-[hsl(var(--text-secondary))]">No hay personas para este filtro</div>
 )}
 </div>
 </div>
 )}

 <div className="grid grid-cols-2 gap-4">
 <div className="space-y-1.5">
 <label className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Hora de Inicio *</label>
 <input
 type="time"
 required
 value={newEvent.start_time}
 onChange={e => setNewEvent({ ...newEvent, start_time: e.target.value })}
 className="w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] dark:bg-black/20 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm text-[hsl(var(--text-primary))]"
 />
 </div>
 <div className="space-y-1.5">
 <label className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Hora de Finalización *</label>
 <input
 type="time"
 required
 value={newEvent.end_time}
 onChange={e => setNewEvent({ ...newEvent, end_time: e.target.value })}
 className="w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] dark:bg-black/20 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm text-[hsl(var(--text-primary))]"
 />
 </div>
 </div>

 {['PERMANENT', 'FARO', 'ONLINE'].includes(newEvent.event_type) && (
 <div className="space-y-1.5">
 <label className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Día de la Semana</label>
 <select
 value={newEvent.day_of_week}
 onChange={e => setNewEvent({ ...newEvent, day_of_week: e.target.value })}
 className="w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] dark:bg-black/20 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm "
 >
 {DAY_LABELS.map((d, i) => <option key={i} value={i}>{d}</option>)}
 </select>
 </div>
 )}

 {['ONCE', 'SPECIAL'].includes(newEvent.event_type) && (
 <div className="space-y-1.5">
 <label className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Fecha Exacta</label>
 <input
 type="date"
 value={newEvent.fixed_date}
 onChange={e => setNewEvent({ ...newEvent, fixed_date: e.target.value })}
 className="w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] dark:bg-black/20 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm "
 />
 </div>
 )}

 {['ANNUAL', 'MONTHLY'].includes(newEvent.event_type) && (
 <div className="space-y-1.5">
 <label className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Día(s) del Mes / Año</label>
 <input
 value={newEvent.month_day}
 onChange={e => setNewEvent({ ...newEvent, month_day: e.target.value })}
 className="w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] dark:bg-black/20 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm "
 placeholder="Ej: 15 de cada mes, o 24 Dic"
 />
 </div>
 )}

 <div className="space-y-1.5">
 <label className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">descripción</label>
 <textarea
 value={newEvent.description}
 onChange={e => setNewEvent({ ...newEvent, description: e.target.value })}
 rows={3}
 className="w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] dark:bg-black/20 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm resize-none"
 placeholder="Breve descripción del evento..."
 />
 </div>
 </form>
 </WorkspaceDrawer>

 {/* â”€â”€â”€ Drawer: Registrar Asistencia â”€â”€â”€ */}
 <WorkspaceDrawer
 isOpen={isAttendanceDrawerOpen}
 onClose={() => setIsAttendanceDrawerOpen(false)}
 title="Registro de Asistencia"
 subtitle={selectedEvent?.name ?? 'Evento'}
 actions={
 <>
 <div className="flex items-center gap-2 mr-auto">
 <Calendar size={14} className="text-[hsl(var(--text-secondary))]" />
 <input
 type="date"
 value={attendanceDate}
 onChange={e => setAttendanceDate(e.target.value)}
 className="text-sm font-bold text-[hsl(var(--text-primary))] outline-none bg-transparent"
 />
 </div>
 <button disabled={savingAttendance} onClick={() => setIsAttendanceDrawerOpen(false)} className="px-4 py-2 text-[11px] font-bold text-[hsl(var(--text-secondary))] disabled:opacity-60">
 Cancelar
 </button>
 <button
 onClick={() => saveAttendance()}
 disabled={savingAttendance || attendanceLoading || String(selectedEvent?.status || '').toUpperCase() === 'CANCELLED' || String(selectedEvent?.status || '').toUpperCase() === 'CANCELED'}
 className="px-3 py-2 bg-emerald-600 text-white rounded-lg text-[11px] font-semibold uppercase tracking-wide shadow-lg shadow-emerald-500/20 hover:bg-emerald-700 active:scale-95 transition-all disabled:opacity-60 disabled:active:scale-100"
 >
 {savingAttendance ? 'Guardando...' : 'Guardar Registro'}
 </button>
 </>
 }
 >
 <div className="space-y-3">
 {/* Scanner section */}
 <div>
 <button
 onClick={() => setShowScanner(s => !s)}
 className={`px-4 py-2 rounded-md text-[10px] font-semibold uppercase tracking-wide transition-all ${showScanner ? 'bg-rose-500 text-white' : 'bg-[hsl(var(--bg-primary))] text-white hover:opacity-80'}`}
 >
 {showScanner ? 'Cerrar Escáner' : 'Modo Escáner'}
 </button>
 </div>

 {showScanner && (
 <div className="p-4 bg-[hsl(var(--bg-primary))] dark:bg-black/40 rounded-lg space-y-4">
 <p className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide text-center">Ingresa el token del carnet (CCF-MBR-ID-TOKEN)</p>
 <div className="flex gap-2">
 <input
 type="text"
 value={scannerToken}
 onChange={e => setScannerToken(e.target.value)}
 placeholder="CCF-MBR-1-XXXXXX"
 className="flex-1 bg-[hsl(var(--bg-primary))] border border-white/10 rounded-md px-4 py-1.5 text-sm text-white focus:outline-none focus:border-[hsl(var(--primary))]"
 onKeyDown={e => e.key === 'Enter' && handleScanToken()}
 />
 <button
 onClick={handleScanToken}
 disabled={isScanning || !scannerToken}
 className="px-4 py-1.5 bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))] disabled:opacity-50 text-white rounded-md text-[10px] font-semibold uppercase tracking-wide transition-all"
 >
 {isScanning ? 'Validando...' : 'Validar'}
 </button>
 </div>
 </div>
 )}

 <div className="grid gap-3 md:grid-cols-[1.2fr,0.9fr,0.8fr,auto,auto] md:items-center">
 <input
 type="text"
 value={attendanceSearch}
 onChange={e => setAttendanceSearch(e.target.value)}
 placeholder="Buscar por nombre o correo..."
 className="w-full rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-muted))] dark:bg-black/20 px-4 py-1.5 text-sm font-bold text-[hsl(var(--text-primary))] outline-none focus:ring-2 focus:ring-blue-500/20"
 />
 <select
 value={attendanceRoleFilter}
 onChange={e => setAttendanceRoleFilter(e.target.value)}
 className="w-full rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-muted))] dark:bg-black/20 px-4 py-1.5 text-sm font-bold text-[hsl(var(--text-primary))] outline-none focus:ring-2 focus:ring-blue-500/20"
 >
 <option value="ALL">Todos los roles</option>
 {attendanceRoleOptions.map((role) => (
 <option key={role} value={role}>{role}</option>
 ))}
 </select>
 <select
 value={attendanceStatusFilter}
 onChange={e => setAttendanceStatusFilter(e.target.value as 'ALL' | 'PENDING' | 'PRESENT')}
 className="w-full rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-muted))] dark:bg-black/20 px-4 py-1.5 text-sm font-bold text-[hsl(var(--text-primary))] outline-none focus:ring-2 focus:ring-blue-500/20"
 >
 <option value="ALL">Todos</option>
 <option value="PENDING">Pendientes</option>
 <option value="PRESENT">Presentes</option>
 </select>
 <button
 onClick={markFilteredMembers}
 disabled={filteredMembers.length === 0}
 className="px-4 py-1.5 rounded-lg border border-emerald-200 dark:border-emerald-900/30 bg-emerald-50 dark:bg-emerald-900/10 text-[10px] font-semibold uppercase tracking-wide text-emerald-700 dark:text-emerald-300 transition-all hover:bg-emerald-100 disabled:opacity-50"
 >
 Marcar filtrados
 </button>
 <button
 onClick={clearFilteredMembers}
 disabled={filteredMembers.length === 0}
 className="px-4 py-1.5 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] transition-all hover:bg-[hsl(var(--bg-muted))] disabled:opacity-50"
 >
 Limpiar filtrados
 </button>
 </div>

 {/* Summary badge */}
 <div className="flex items-center justify-between px-4 py-1.5 bg-emerald-50 dark:bg-emerald-900/20 rounded-lg border border-emerald-100 dark:border-emerald-900/30">
 <div>
 <p className="text-sm font-bold text-[hsl(var(--text-secondary))]">Presentes</p>
 <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
 {attendanceLoading ? 'Cargando sesión...' : `${filteredMembers.length} visibles en esta búsqueda`}
 </p>
 </div>
 <p className="text-base font-bold text-emerald-600">{attendedMemberIds.length} <span className="text-sm font-bold text-[hsl(var(--text-secondary))]">/ {expectedUniverseMembers.length}</span></p>
 </div>

 {!attendanceLoading && (
 <div className="flex flex-wrap gap-2">
 <span className="rounded-full border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
 {selectedEvent?.target_audience === 'ROLE'
 ? `Universo: ${getTargetRoleLabel(selectedEvent)}`
 : 'Universo: toda la iglesia'}
 </span>
 <span className="rounded-full border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
 {attendanceRoleFilter === 'ALL' ? 'Todos los roles visibles' : attendanceRoleFilter}
 </span>
 <span className="rounded-full border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
 {attendanceStatusFilter === 'ALL' ? 'Vista completa' : attendanceStatusFilter === 'PENDING' ? 'Solo pendientes' : 'Solo presentes'}
 </span>
 </div>
 )}

 {/* Member list */}
 <div className="grid grid-cols-1 gap-3">
 {attendanceLoading ? (
 <div className="py-1.5 text-center text-[hsl(var(--text-secondary))] text-sm">Cargando asistencia registrada...</div>
 ) : filteredMembers.map(member => (
 <div
 key={member.id}
 onClick={() => toggleAttendance(member.id)}
 className={`flex items-center p-4 rounded-lg cursor-pointer transition-all border ${attendedMemberIds.includes(member.id)
 ? 'bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200 dark:border-emerald-700/30 shadow-sm'
 : 'bg-[hsl(var(--bg-muted))] border-[hsl(var(--border-primary))] hover:border-[hsl(var(--border-primary))] dark:hover:border-white/10'
 }`}
 >
 <div className={`w-6 h-6 rounded-full border-2 flex items-center justify-center mr-4 transition-colors shrink-0 ${attendedMemberIds.includes(member.id)
 ? 'bg-emerald-500 border-emerald-500 text-white'
 : 'border-[hsl(var(--border-primary))] dark:border-white/20 bg-[hsl(var(--bg-primary))] dark:bg-black/20'
 }`}>
 {attendedMemberIds.includes(member.id) && <Check size={12} strokeWidth={4} />}
 </div>
 <div>
 <p className={`font-bold text-sm ${attendedMemberIds.includes(member.id) ? 'text-emerald-900 dark:text-emerald-200' : 'text-[hsl(var(--text-primary))]'}`}>
 {member.nombre_completo}
 </p>
 <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
 {member.church_role || 'Sin rol'}
 </p>
 </div>
 </div>
 ))}
 {!attendanceLoading && filteredMembers.length === 0 && (
 <div className="py-1.5 text-center text-[hsl(var(--text-secondary))] text-sm">
 {expectedUniverseMembers.length === 0 ? 'Este evento no tiene universo esperado configurado con personas disponibles' : 'No hay personas para este filtro'}
 </div>
 )}
 </div>
 </div>
 </WorkspaceDrawer>

 {/* ─── Drawer: Generar QR ─── */}
 <WorkspaceDrawer
 isOpen={isQrDrawerOpen}
 onClose={() => setIsQrDrawerOpen(false)}
 title="código QR de Registro"
 subtitle={selectedEvent?.name ?? 'Evento'}
 actions={
 <button
 onClick={downloadQr}
 className="px-4 py-2 bg-[hsl(var(--primary))] text-white rounded-lg text-[11px] font-semibold uppercase tracking-wide shadow-lg shadow-blue-500/20 hover:bg-[hsl(var(--primary))] active:scale-95 transition-all flex items-center gap-2"
 >
 <Download size={14} /> Descargar
 </button>
 }
 >
 <div className="flex flex-col items-center justify-center space-y-3 py-1.5">
 <div className="p-4 bg-[hsl(var(--bg-primary))] rounded-md shadow-xl border border-[hsl(var(--border-primary))] flex items-center justify-center">
 <QRCodeSVG 
 id="event-qr-code"
 value={typeof window !== 'undefined' ? `${window.location.origin}/public/register?event_id=${selectedEvent?.id}` : ''}
 size={256}
 level="H"
 includeMargin={true}
 />
 </div>
 <div className="text-center space-y-2">
 <p className="text-sm font-bold text-[hsl(var(--text-primary))]">Escanea para registrarte</p>
 <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Enlace de Registro</p>
 <a href={typeof window !== 'undefined' ? `${window.location.origin}/public/register?event_id=${selectedEvent?.id}` : '#'} target="_blank" rel="noreferrer" className="text-xs font-medium text-[hsl(var(--primary))] hover:text-[hsl(var(--primary))] transition-colors break-all bg-blue-50 dark:bg-blue-500/10 px-4 py-2 rounded-md inline-block mt-2">
 {typeof window !== 'undefined' ? `${window.location.origin}/public/register?event_id=${selectedEvent?.id}` : ''}
 </a>
 </div>
 </div>
 </WorkspaceDrawer>

 {/* DELETE CONFIRM DRAWER */}
 <WorkspaceDrawer
 isOpen={!!deletingEventId}
 onClose={() => setDeletingEventId(null)}
 title="¿Eliminar Evento?"
 subtitle="Atención: Acción destructiva irreversible"
 actions={
 <>
 <button disabled={deletingEventLoadingId === deletingEventId} onClick={() => setDeletingEventId(null)} className="px-4 py-2 text-[11px] font-bold text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] transition-colors disabled:opacity-60">
 Cancelar
 </button>
 <button onClick={() => deletingEventId && handleDeleteEvent(deletingEventId)} disabled={deletingEventLoadingId === deletingEventId} className="px-3 py-2 bg-[hsl(var(--destructive))] text-white rounded-lg text-[11px] font-semibold uppercase tracking-wide shadow-lg shadow-red-500/20 hover:bg-[hsl(var(--destructive))] active:scale-95 transition-all flex items-center gap-2 disabled:opacity-60">
 <Trash2 size={14} /> Eliminar
 </button>
 </>
 }
 >
 <div className="flex flex-col items-center text-center p-4 bg-red-50 dark:bg-red-900/10 rounded-md border border-red-100 dark:border-red-900/30">
 <div className="size-8 bg-red-100 dark:bg-red-900/40 text-[hsl(var(--destructive))] dark:text-[hsl(var(--destructive))] rounded-full flex items-center justify-center mb-4">
 <Trash2 size={24} />
 </div>
 <p className="text-sm text-red-900 dark:text-red-200 font-bold mb-2">Se eliminará todo el historial</p>
 <p className="text-xs text-[hsl(var(--destructive))] dark:text-red-300">Esta acción también borrará los registros de asistencia asociados. No podrás recuperar esta información.</p>
 </div>
 </WorkspaceDrawer>

 {/* EDIT DRAWER */}
 <WorkspaceDrawer
 isOpen={!!editingEvent}
 onClose={() => setEditingEvent(null)}
 title="Editar Evento"
 subtitle="Modifica los detalles o configuración"
 actions={
 <>
 <button disabled={!!editingEvent && updatingEventId === editingEvent.id} onClick={() => setEditingEvent(null)} className="px-4 py-2 text-[11px] font-bold text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] transition-colors disabled:opacity-60">
 Cancelar
 </button>
 <button disabled={!editingEvent || updatingEventId === editingEvent.id} onClick={() => editingEvent && handleUpdateEvent(editingEvent.id, { name: editingEvent.name, description: editingEvent.description, location: editingEvent.location, status: editingEvent.status, cancellation_reason: editingEvent.cancellation_reason, start_time: editingEvent.start_time, end_time: editingEvent.end_time, target_audience: editingEvent.target_audience || 'ALL', target_role_id: (editingEvent.target_audience || 'ALL') === 'ROLE' ? (editingEvent.target_role_ids?.[0] || editingEvent.target_role_id) : null, target_role_ids: (editingEvent.target_audience || 'ALL') === 'ROLE' ? (editingEvent.target_role_ids || getTargetRoleIds(editingEvent)) : [], target_persona_ids: (editingEvent.target_audience || 'ALL') === 'MANUAL' ? (editingEvent.target_persona_ids || []) : [] })} className="px-3 py-2 bg-[hsl(var(--primary))] text-white rounded-lg text-[11px] font-semibold uppercase tracking-wide shadow-lg shadow-blue-500/20 hover:bg-[hsl(var(--primary))] active:scale-95 transition-all flex items-center gap-2 disabled:opacity-60">
 {editingEvent && updatingEventId === editingEvent.id ? 'Guardando...' : 'Guardar'} <Pencil size={14} />
 </button>
 </>
 }
 >
 {editingEvent && (
 <div className="space-y-3">
 <div className="space-y-1.5">
 <label className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Nombre</label>
 <input type="text" value={editingEvent.name} onChange={e => setEditingEvent({...editingEvent, name: e.target.value})} className="w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] dark:bg-black/20 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm text-[hsl(var(--text-primary))]" />
 </div>
 <div className="space-y-1.5">
 <label className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Estado</label>
 <select 
 value={editingEvent.status || 'SCHEDULED'} 
 onChange={e => setEditingEvent({...editingEvent, status: e.target.value})} 
 className="w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] dark:bg-black/20 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm text-[hsl(var(--text-primary))] appearance-none"
 >
 <option value="SCHEDULED">Programado</option>
 <option value="COMPLETED">Realizado</option>
 <option value="CANCELLED">Cancelado</option>
 </select>
 </div>
 <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
 <div className="space-y-1.5">
 <label className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Universo Esperado</label>
 <select
 value={editingEvent.target_audience || 'ALL'}
 onChange={e => setEditingEvent({
 ...editingEvent,
 target_audience: e.target.value as EventAudience,
 target_role_id: e.target.value === 'ROLE' ? editingEvent.target_role_id : null,
 target_role_ids: e.target.value === 'ROLE' ? (editingEvent.target_role_ids || getTargetRoleIds(editingEvent)) : [],
 target_persona_ids: e.target.value === 'MANUAL' ? (editingEvent.target_persona_ids || []) : [],
 })}
 className="w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] dark:bg-black/20 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm text-[hsl(var(--text-primary))] appearance-none"
 >
 <option value="ALL">Toda la iglesia</option>
 <option value="ROLE">Uno o varios roles</option>
 <option value="MANUAL">Selección manual</option>
 </select>
 </div>
 <div className="space-y-1.5">
 <label className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Roles esperados</label>
 <select
 multiple
 disabled={(editingEvent.target_audience || 'ALL') !== 'ROLE'}
 value={(editingEvent.target_role_ids || getTargetRoleIds(editingEvent)).map((value: number) => String(value))}
 onChange={e => {
 const selectedValues = Array.from(e.target.selectedOptions).map((option) => Number(option.value));
 setEditingEvent({ ...editingEvent, target_role_ids: selectedValues, target_role_id: selectedValues[0] || null });
 }}
 className="min-h-[140px] w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] dark:bg-black/20 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm text-[hsl(var(--text-primary))] disabled:opacity-50"
 >
 {roles.map((role) => (
 <option key={role.id} value={role.id}>{role.name}</option>
 ))}
 </select>
 </div>
 </div>
 <div className="space-y-3 rounded-md border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-muted))] dark:bg-black/20 p-4">
 <div className="flex items-center justify-between gap-3">
 <div>
 <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Plantillas de audiencia</p>
 <p className="text-sm font-bold text-[hsl(var(--text-primary))] ">Aplica o guarda universos reutilizables</p>
 </div>
 <div className="flex items-center gap-2">
 <button type="button" onClick={addSuggestedAudiencePresets} className="rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] px-4 py-2 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] transition-all hover:bg-[hsl(var(--bg-muted))] dark:hover:bg-white/10">Sugerencias</button>
 <button type="button" onClick={() => saveAudiencePreset({ target_audience: editingEvent.target_audience || 'ALL', target_role_ids: editingEvent.target_role_ids || [], target_persona_ids: editingEvent.target_persona_ids || [] })} className="rounded-lg bg-[hsl(var(--primary))] px-4 py-2 text-[10px] font-semibold uppercase tracking-wide text-white transition-all hover:bg-[hsl(var(--primary))]">Guardar actual</button>
 </div>
 </div>
 <div className="space-y-2">
 {audiencePresets.length === 0 ? (
 <div className="rounded-lg border border-dashed border-[hsl(var(--border-primary))] px-4 py-2 text-center text-sm text-[hsl(var(--text-secondary))]">Aun no hay plantillas guardadas</div>
 ) : audiencePresets.map((preset) => (
 <div key={preset.id} className="flex items-center justify-between gap-3 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] px-4 py-1.5">
 <div className="min-w-0">
 <p className="truncate text-sm font-bold text-[hsl(var(--text-primary))]">{preset.name}</p>
 <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{preset.target_audience === 'ALL' ? 'Toda la iglesia' : preset.target_audience === 'ROLE' ? `${preset.target_role_ids.length} roles` : `${preset.target_persona_ids.length} personas`}</p>
 </div>
 <div className="flex items-center gap-2">
 <button type="button" onClick={() => applyPresetToEditingEvent(preset.id)} className="rounded-lg bg-[hsl(var(--bg-primary))] px-3 py-2 text-[10px] font-semibold uppercase tracking-wide text-white transition-all hover:opacity-85 ">Aplicar</button>
 <button type="button" onClick={() => deleteAudiencePreset(preset.id)} className="rounded-lg border border-[hsl(var(--border-primary))] px-3 py-2 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] transition-all hover:bg-[hsl(var(--bg-muted))]">Borrar</button>
 </div>
 </div>
 ))}
 </div>
 </div>
 {editingEvent.target_audience === 'MANUAL' && (
 <div className="space-y-3">
 <div className="flex items-center justify-between gap-3">
 <label className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Personas esperadas</label>
 <span className="rounded-full bg-blue-50 dark:bg-blue-900/20 px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--primary))] dark:text-blue-300">{(editingEvent.target_persona_ids || []).length} seleccionadas</span>
 </div>
 <input value={editManualSearch} onChange={e => setEditManualSearch(e.target.value)} placeholder="Buscar por nombre, correo o rol..." className="w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] dark:bg-black/20 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm text-[hsl(var(--text-primary))]" />
 <div className="max-h-48 space-y-2 overflow-y-auto rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-muted))] dark:bg-black/20 p-3">
 {editManualMembers.map((member) => {
 const isSelected = (editingEvent.target_persona_ids || []).includes(member.id);
 return (
 <button key={member.id} type="button" onClick={() => setEditingEvent({ ...editingEvent, target_persona_ids: isSelected ? (editingEvent.target_persona_ids || []).filter((value) => value !== member.id) : [...(editingEvent.target_persona_ids || []), member.id], })} className={`flex w-full items-center justify-between rounded-lg border px-4 py-1.5 text-left transition-all ${isSelected ? 'border-blue-200 bg-blue-50 dark:border-blue-800 dark:bg-blue-900/20' : 'border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] '}`}>
 <div>
 <p className="text-sm font-bold text-[hsl(var(--text-primary))]">{member.nombre_completo}</p>
 <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{member.church_role || 'Sin rol'}</p>
 </div>
 <span className={`text-[10px] font-semibold uppercase tracking-wide ${isSelected ? 'text-[hsl(var(--primary))] dark:text-blue-300' : 'text-[hsl(var(--text-secondary))]'}`}>{isSelected ? 'Incluida' : 'Agregar'}</span>
 </button>
 );
 })}
 {editManualMembers.length === 0 && <div className="py-2 text-center text-sm text-[hsl(var(--text-secondary))]">No hay personas para este filtro</div>}
 </div>
 </div>
 )}
 {editingEvent.status === 'CANCELLED' && (
 <div className="animate-in fade-in slide-in-from-top-2 space-y-1.5">
 <label className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--destructive))]">Razón de Cancelación *</label>
 <textarea value={editingEvent.cancellation_reason || ''} onChange={e => setEditingEvent({...editingEvent, cancellation_reason: e.target.value})} rows={3} placeholder="¿Por qué no se realizó este evento?" className="w-full px-4 py-1.5 rounded-lg border border-red-200 bg-red-50 dark:bg-black/20 focus:ring-2 focus:ring-red-500/20 outline-none font-bold text-sm text-red-900 dark:text-red-200 resize-none placeholder:text-red-300 dark:placeholder:text-[hsl(var(--destructive))]" />
 </div>
 )}
 <div className="space-y-1.5">
 <label className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Descripción</label>
 <textarea value={editingEvent.description || ''} onChange={e => setEditingEvent({...editingEvent, description: e.target.value})} rows={3} className="w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] dark:bg-black/20 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm text-[hsl(var(--text-primary))] resize-none" />
 </div>
 <div className="space-y-1.5">
 <label className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Ubicación</label>
 <input type="text" value={editingEvent.location || ''} onChange={e => setEditingEvent({...editingEvent, location: e.target.value})} className="w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] dark:bg-black/20 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm text-[hsl(var(--text-primary))]" />
 </div>
 <div className="grid grid-cols-2 gap-4">
 <div className="space-y-1.5">
 <label className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Hora de Inicio</label>
 <input type="time" value={editingEvent.start_time || ''} onChange={e => setEditingEvent({...editingEvent, start_time: e.target.value})} className="w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] dark:bg-black/20 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm text-[hsl(var(--text-primary))]" />
 </div>
 <div className="space-y-1.5">
 <label className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Hora de Finalización</label>
 <input type="time" value={editingEvent.end_time || ''} onChange={e => setEditingEvent({...editingEvent, end_time: e.target.value})} className="w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] dark:bg-black/20 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm text-[hsl(var(--text-primary))]" />
 </div>
 </div>
 </div>
 )}
 </WorkspaceDrawer>
 <ConfirmActionDrawer action={confirmAction} onClose={() => setConfirmAction(null)} />
 </EvangelismShell>
 );
}
