"use client";

import type {
  BulkAttendanceSyncResult,
  EventDashboardStat,
  EventSessionAttendanceData,
  Persona,
  MinistryEvent,
  RoleDefinition,
  ScanValidationResult,
} from '@/app/plataforma/evangelism/types';
import { ViewType, getStoredView } from '@/components/ViewSwitcher';
import { type ConfirmActionState } from '@/components/evangelism/ConfirmActionDrawer';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { useWikiDocument } from '@/hooks/useWikiDocument';
import { apiFetch } from '@/lib/http';
import { parseAndValidateTime } from '@/lib/time';
import { useSearchParams } from 'next/navigation';
import React, { useEffect, useRef, useState } from 'react';
import { toast } from 'sonner';
import { formatLocalDate, getErrorMessage } from '../utils';

const normalizeMinistryEvent = (raw: MinistryEvent): MinistryEvent => ({
  ...raw,
  target_role_ids: Array.isArray(raw.target_role_ids)
    ? raw.target_role_ids.map(String)
    : raw.target_role_id
      ? [String(raw.target_role_id)]
      : [],
  target_persona_ids: Array.isArray(raw.target_persona_ids)
    ? raw.target_persona_ids.map(String)
    : [],
});

interface AudiencePreset {
  id: string;
  name: string;
  target_audience: 'ALL' | 'ROLE' | 'MANUAL';
  target_role_ids: string[];
  target_persona_ids: string[];
}

export function useEventsPage() {
 const { token, hasModuleAccess } = useAuth();
 const searchParams = useSearchParams();
 const requestedEventId = searchParams?.get('event_id');
 const autoOpenedEventRef = useRef<string | null>(null);
 const canManageEvents = hasModuleAccess('evangelism', 'manage');
 const canEditEvents = hasModuleAccess('evangelism', 'edit');
 const { addToast } = useToast();
 const [viewType, setViewType] = useState<ViewType>(() => getStoredView('evangelism_events_view', 'grid'));
 const [events, setEvents] = useState<MinistryEvent[]>([]);
 const [personas, setPersonas] = useState<Persona[]>([]);
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
 const [deletingEventId, setDeletingEventId] = useState<string | null>(null);
 const [menuOpenId, setMenuOpenId] = useState<string | null>(null);
 useEffect(() => {
 if (menuOpenId === null) return;
 const close = () => setMenuOpenId(null);
 document.addEventListener('click', close);
 return () => document.removeEventListener('click', close);
 }, [menuOpenId]);
 const [savingCreateEvent, setSavingCreateEvent] = useState(false);
 const [savingAttendance, setSavingAttendance] = useState(false);
 const [updatingEventId, setUpdatingEventId] = useState<string | null>(null);
 const [deletingEventLoadingId, setDeletingEventLoadingId] = useState<string | null>(null);

 useEffect(() => {
 const abort = new AbortController();
 if (token) {
 apiFetch<RoleDefinition[]>('/evangelism/roles', { token, silent: true, signal: abort.signal }).then(setRoles).catch(() => {});
 }
 return () => abort.abort();
 }, [token]);

 // Attendance State
 const [attendanceDate, setAttendanceDate] = useState(() => formatLocalDate(new Date()));
 const [attendedPersonaIds, setAttendedPersonaIds] = useState<string[]>([]);
 const [attendanceSearch, setAttendanceSearch] = useState('');
 const [attendanceLoading, setAttendanceLoading] = useState(false);
 const [attendanceRoleFilter, setAttendanceRoleFilter] = useState('ALL');
 const [attendanceStatusFilter, setAttendanceStatusFilter] = useState<'ALL' | 'PENDING' | 'PRESENT'>('ALL');
 const [createManualSearch, setCreateManualSearch] = useState('');
 const [editManualSearch, setEditManualSearch] = useState('');
 const [audiencePresets, setAudiencePresets] = useState<AudiencePreset[]>([]);
 const [audiencePresetNameOpen, setAudiencePresetNameOpen] = useState(false);
 const [audiencePresetNameDraft, setAudiencePresetNameDraft] = useState('');
 const [pendingAudiencePreset, setPendingAudiencePreset] = useState<{
 target_audience: AudiencePreset['target_audience'];
 target_role_ids: string[];
 target_persona_ids: string[];
 } | null>(null);

 const handleScanToken = async () => {
 if (!scannerToken || !selectedEvent) return;
 setIsScanning(true);
 try {
 const result = await apiFetch<ScanValidationResult>(`/evangelism/scanner/validate/${scannerToken}`, {
  method: 'POST',
  token,
  silent: true
 });
 if (result.valid) {
 const pid = result.persona_id;
 if (!attendedPersonaIds.includes(pid)) {
 setAttendedPersonaIds(prev => [...prev, pid]);
 addToast(`¡Bienvenido ${result.persona_name}!`, "success");
 } else {
 addToast(`${result.persona_name} ya está marcado`, "info");
 }
 setScannerToken('');
 }
 } catch {
 addToast("Token de escaneo inválido", "error");
 } finally {
 setIsScanning(false);
 }
 };

 const fetchData = async (signal?: AbortSignal) => {
 if (!token) return;
 setLoading(true);
 try {
 const eventsRes = await apiFetch<MinistryEvent[]>('/evangelism/events/', { token, silent: true, cache: 'no-store', signal });
 const [personasRes, statsRes] = await Promise.all([
 canManageEvents || canEditEvents
 ? apiFetch<Persona[]>('/crm/personas', { token, silent: true, query: { limit: 200 }, cache: 'no-store', signal })
 : Promise.resolve([] as Persona[]),
 canManageEvents
 ? apiFetch<EventDashboardStat[]>('/evangelism/events/dashboard-stats', { token, silent: true, cache: 'no-store', signal })
 : Promise.resolve([] as EventDashboardStat[]),
 ]);
 setEvents(Array.isArray(eventsRes) ? eventsRes.map(normalizeMinistryEvent) : []);
 setPersonas(Array.isArray(personasRes) ? personasRes : []);
 setStats(Array.isArray(statsRes) ? statsRes : []);
 } catch {
 if (signal?.aborted) return;
 setEvents([]);
 setPersonas([]);
 setStats([]);
 } finally {
 setLoading(false);
 }
 };

 useEffect(() => {
 const abort = new AbortController();
 fetchData(abort.signal);
 return () => abort.abort();
 // eslint-disable-next-line react-hooks/exhaustive-deps
 }, [token, canEditEvents, canManageEvents]);

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

 const sortedPersonas = [...personas].sort((a, b) =>
 (a.nombre_completo || '').localeCompare(b.nombre_completo || '')
 );

 const filterPersonasByQuery = (query: string) => {
 const normalized = query.trim().toLowerCase();
 if (!normalized) return sortedPersonas;
 return sortedPersonas.filter((persona) =>
 (persona.nombre_completo || '').toLowerCase().includes(normalized) ||
 persona.email.toLowerCase().includes(normalized) ||
 (persona.church_role || '').toLowerCase().includes(normalized)
 );
 };

 const createManualPersonas = filterPersonasByQuery(createManualSearch);
 const editManualPersonas = filterPersonasByQuery(editManualSearch);

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
 const targetRoleIds = (source.target_role_ids || []).map(String).filter(Boolean);
 const targetPersonaIds = (source.target_persona_ids || []).map(String);

 if (targetAudience === 'ROLE' && targetRoleIds.length === 0) {
 addToast("No puedes guardar una plantilla de roles sin roles seleccionados", "error");
 return;
 }
 if (targetAudience === 'MANUAL' && targetPersonaIds.length === 0) {
 addToast("No puedes guardar una plantilla manual sin personas seleccionadas", "error");
 return;
 }

 setPendingAudiencePreset({ target_audience: targetAudience, target_role_ids: targetRoleIds, target_persona_ids: targetPersonaIds });
 setAudiencePresetNameDraft('');
 setAudiencePresetNameOpen(true);
 };

 const submitAudiencePreset = () => {
 const name = audiencePresetNameDraft.trim();
 if (!name || !pendingAudiencePreset) return;
 setAudiencePresets((prev) => [
 {
 id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
 name,
 target_audience: pendingAudiencePreset.target_audience,
 target_role_ids: pendingAudiencePreset.target_audience === 'ROLE' ? pendingAudiencePreset.target_role_ids : [],
 target_persona_ids: pendingAudiencePreset.target_audience === 'MANUAL' ? pendingAudiencePreset.target_persona_ids : [],
 },
 ...prev,
 ]);
 addToast(`Plantilla guardada: ${name}`, "success");
 setAudiencePresetNameOpen(false);
 setPendingAudiencePreset(null);
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
 const roleNameToId = new Map<string, string>(
 roles
 .filter((role) => role && typeof role.id === 'string' && typeof role.name === 'string')
 .map((role) => [normalized(role.name), role.id])
 );

 const findRoleIdsByKeywords = (keywords: string[]) => {
 const wanted = keywords.map(normalized);
 const ids = new Set<string>();
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
 if (!canManageEvents) return;
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
 target_role_id: string | null;
 target_role_ids: string[];
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
 target_role_id: newEvent.target_audience === 'ROLE' && newEvent.target_role_ids[0] ? newEvent.target_role_ids[0] : null,
 target_role_ids: newEvent.target_audience === 'ROLE' ? newEvent.target_role_ids : [],
 target_persona_ids: newEvent.target_audience === 'MANUAL' ? newEvent.target_persona_ids : [],
 start_time: startParsed.normalized,
 end_time: endParsed.normalized,
 };

 if (['PERMANENT', 'GROUPS', 'ONLINE'].includes(newEvent.event_type)) payload.day_of_week = parseInt(newEvent.day_of_week);
 if (['ANNUAL', 'MONTHLY'].includes(newEvent.event_type)) payload.month_day = newEvent.month_day;
 if (['ONCE', 'SPECIAL'].includes(newEvent.event_type)) payload.fixed_date = newEvent.fixed_date;

 try {
 setSavingCreateEvent(true);
 await apiFetch('/evangelism/events/', { method: 'POST', token, silent: true, body: payload });
 addToast("Evento creado con éxito", "success");
 setIsCreateDrawerOpen(false);
 setNewEvent({ name: '', description: '', event_type: 'PERMANENT', target_audience: 'ALL', target_role_id: '', target_role_ids: [], target_persona_ids: [], day_of_week: '0', month_day: '', fixed_date: '', start_time: '', end_time: '' });
 fetchData();
 } catch (error: unknown) {
 const msg = getErrorMessage(error, "Error de conexión");
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
 return personas.filter((persona) => roleNames.includes((persona.church_role || '').trim())).length;
 }
 if (event.target_audience === 'MANUAL') {
 return Array.isArray(event.target_persona_ids) ? event.target_persona_ids.length : 0;
 }
 return personas.length;
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
 setSelectedEvent(normalizeMinistryEvent(ev));
 setIsQrDrawerOpen(true);
 };

const openAttendance = (ev: MinistryEvent) => {
 if (!canEditEvents) return;
 setSelectedEvent(normalizeMinistryEvent(ev));
 setIsAttendanceDrawerOpen(true);
 setAttendanceDate(formatLocalDate(new Date()));
 setAttendedPersonaIds([]);
 setShowScanner(false);
 setAttendanceSearch('');
 setAttendanceRoleFilter('ALL');
 setAttendanceStatusFilter('ALL');
 };

 useEffect(() => {
  if (!requestedEventId || !canEditEvents || autoOpenedEventRef.current === requestedEventId) return;
  const event = events.find((item) => String(item.id) === requestedEventId);
  if (!event) return;
  autoOpenedEventRef.current = requestedEventId;
  openAttendance(event);
 }, [canEditEvents, events, requestedEventId]);

 useEffect(() => {
 if (!token || !selectedEvent || !isAttendanceDrawerOpen || !attendanceDate) return;
 const abort = new AbortController();

 const loadAttendanceSession = async () => {
 setAttendanceLoading(true);
 try {
 const data = await apiFetch<EventSessionAttendanceData>(`/evangelism/events/${selectedEvent.id}/sessions/${attendanceDate}`, { token, silent: true, signal: abort.signal });
 setAttendedPersonaIds(Array.isArray(data?.attendees) ? data.attendees.map((item) => item.persona_id) : []);
 } catch {
 if (!abort.signal.aborted) setAttendedPersonaIds([]);
 } finally {
 if (!abort.signal.aborted) setAttendanceLoading(false);
 }
 };

 loadAttendanceSession();
 return () => abort.abort();
 }, [attendanceDate, isAttendanceDrawerOpen, selectedEvent, token]);

const saveAttendance = async (forceEmpty = false) => {
 if (!selectedEvent || !canEditEvents) return;
 const normalizedStatus = String(selectedEvent.status || '').toUpperCase();
 if (normalizedStatus === 'CANCELLED' || normalizedStatus === 'CANCELED') {
 addToast("No se puede registrar asistencia en eventos cancelados", "error");
 return;
 }
 if (!forceEmpty && expectedUniversePersonas.length > 0 && attendedPersonaIds.length === 0) {
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
  silent: true,
  body: {
 event_id: selectedEvent.id,
 persona_ids: attendedPersonaIds,
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
 setAttendedPersonaIds(prev =>
 prev.includes(id) ? prev.filter(mId => mId !== id) : [...prev, id]
 );
 };

 const expectedUniversePersonas = personas.filter((persona) => {
 if (!selectedEvent) {
 return true;
 }
 if (selectedEvent.target_audience === 'MANUAL') {
 return Array.isArray(selectedEvent.target_persona_ids) && selectedEvent.target_persona_ids.includes(persona.id);
 }
 if (selectedEvent.target_audience !== 'ROLE') {
 return true;
 }
 const roleNames = getTargetRoleIds(selectedEvent)
 .map((roleId) => roles.find((role) => role.id === roleId)?.name)
 .filter(Boolean) as string[];
 return roleNames.length > 0 && roleNames.includes((persona.church_role || '').trim());
 });

 const attendanceRoleOptions = Array.from(
 new Set(
 expectedUniversePersonas
 .map((persona) => persona.church_role?.trim())
 .filter((role): role is string => Boolean(role))
 )
 ).sort((a, b) => a.localeCompare(b));

 const filteredPersonas = expectedUniversePersonas.filter((persona) => {
 const query = attendanceSearch.trim().toLowerCase();
 const matchesSearch = !query || (persona.nombre_completo || '').toLowerCase().includes(query) || persona.email.toLowerCase().includes(query);
 const matchesRole = attendanceRoleFilter === 'ALL' || (persona.church_role || 'Sin rol') === attendanceRoleFilter;
 const isPresent = attendedPersonaIds.includes(persona.id);
 const matchesStatus =
 attendanceStatusFilter === 'ALL' ||
 (attendanceStatusFilter === 'PRESENT' && isPresent) ||
 (attendanceStatusFilter === 'PENDING' && !isPresent);

 return matchesSearch && matchesRole && matchesStatus;
 });

 const markFilteredPersonas = () => {
 setAttendedPersonaIds((prev) => {
 const next = new Set(prev);
 filteredPersonas.forEach((persona) => next.add(persona.id));
 return Array.from(next);
 });
 };

 const clearFilteredPersonas = () => {
 const filteredIds = new Set(filteredPersonas.map((persona) => persona.id));
 setAttendedPersonaIds((prev) => prev.filter((personaId) => !filteredIds.has(personaId)));
 };

 const getVisualDate = (event: MinistryEvent) => {
 if (event.fixed_date) return event.fixed_date;
 const current = new Date();
 const targetDay = Number(event.day_of_week ?? current.getDay());
 const next = new Date(current);
 const offset = (targetDay - current.getDay() + 7) % 7;
 next.setDate(current.getDate() + offset);
 return formatLocalDate(next);
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

const handleDeleteEvent = async (evId: string) => {
 if (!token || !canManageEvents) return;
 setDeletingEventLoadingId(evId);
 try {
 await apiFetch(`/evangelism/events/${evId}`, { method: 'DELETE', token, silent: true });
 setEvents(prev => prev.filter(e => e.id !== evId));
 toast.success('Evento eliminado con éxito');
 } catch {
 toast.error('Error al eliminar el evento');
 } finally {
 setDeletingEventLoadingId(null);
 setDeletingEventId(null);
 }
 };

const handleUpdateEvent = async (evId: string, payload: Partial<MinistryEvent> & {
 target_audience?: string;
 target_role_ids?: string[];
 target_persona_ids?: string[];
 }) => {
 if (!token || !canManageEvents) return;
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
 await apiFetch(`/evangelism/events/${evId}`, { method: 'PUT', body: payload, token, silent: true });
 setEvents(prev => prev.map((event) => (
  event.id === evId ? normalizeMinistryEvent({ ...event, ...payload }) : event
 )));
 toast.success('Evento actualizado con éxito');
 setEditingEvent(null);
 } catch (error: unknown) {
 const msg = getErrorMessage(error, 'Error al actualizar el evento');
 toast.error(msg);
 } finally {
 setUpdatingEventId(null);
 }
 };

  return {
    canManageEvents,
    viewType, setViewType,
    events,
    loading,
    wikiNotes, setWikiNotes,
    isCreateDrawerOpen, setIsCreateDrawerOpen,
    isAttendanceDrawerOpen, setIsAttendanceDrawerOpen,
    isQrDrawerOpen, setIsQrDrawerOpen,
    confirmAction, setConfirmAction,
    selectedEvent,
    showScanner, setShowScanner,
    scannerToken, setScannerToken,
    isScanning,
    newEvent, setNewEvent,
    roles,
    editingEvent, setEditingEvent,
    deletingEventId, setDeletingEventId,
    menuOpenId, setMenuOpenId,
    savingCreateEvent,
    savingAttendance,
    updatingEventId,
    deletingEventLoadingId,
    attendanceDate, setAttendanceDate,
    attendedPersonaIds,
    attendanceSearch, setAttendanceSearch,
    attendanceLoading,
    attendanceRoleFilter, setAttendanceRoleFilter,
    attendanceStatusFilter, setAttendanceStatusFilter,
    createManualSearch, setCreateManualSearch,
    editManualSearch, setEditManualSearch,
    audiencePresets,
    audiencePresetNameOpen, setAudiencePresetNameOpen,
    audiencePresetNameDraft, setAudiencePresetNameDraft,
    handleScanToken,
    getTargetRoleIds,
    getTargetRoleLabel,
    createManualPersonas,
    editManualPersonas,
    applyPresetToCreateEvent,
    applyPresetToEditingEvent,
    saveAudiencePreset,
    submitAudiencePreset,
    deleteAudiencePreset,
    addSuggestedAudiencePresets,
    handleCreateEvent,
    getEventAttendanceStat,
    openQr,
    openAttendance,
    saveAttendance,
    toggleAttendance,
    expectedUniversePersonas,
    attendanceRoleOptions,
    filteredPersonas,
    markFilteredPersonas,
    clearFilteredPersonas,
    getVisualDate,
    calendarEvents,
    ganttItems,
    boardColumns,
    handleDeleteEvent,
    handleUpdateEvent,
  };
}
