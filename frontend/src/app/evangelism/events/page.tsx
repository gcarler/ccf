'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { apiFetch } from '@/lib/http';
import { toast } from 'react-toastify';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { Plus, Calendar, Check, Users, Link2, QrCode, Download, Pencil, Trash2, MoreVertical } from 'lucide-react';
import { QRCodeSVG } from 'qrcode.react';
import ViewSwitcher, { ViewType, getStoredView } from '@/components/ViewSwitcher';
import EvangelismShell from '@/components/evangelism/EvangelismShell';
import AdminHero from '@/components/admin/AdminHero';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';
import SplitDropdownButton from '@/components/ui/SplitDropdownButton';
import UniversalCalendarView from '@/components/ui/UniversalCalendarView';
import UniversalGanttView from '@/components/ui/UniversalGanttView';
import type {
    BulkAttendanceSyncResult,
    EventAudience,
    EventDashboardStat,
    EventSessionAttendanceData,
    Member,
    MinistryEvent,
    RoleDefinition,
    ScanValidationResult,
} from '@/app/evangelism/types';
import { useWikiDocument } from '@/hooks/useWikiDocument';

const EVENT_TYPE_LABEL: Record<string, string> = {
    PERMANENT: 'Semanal',
    MONTHLY:   'Mensual',
    ANNUAL:    'Anual',
    ONCE:      'Única Vez',
    SPECIAL:   'Especial',
    FARO:      'Temporada - fuera del templo',
    ONLINE:    'En Línea',
};

const EVENT_TYPE_COLOR: Record<string, string> = {
    PERMANENT: 'bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-400',
    MONTHLY:   'bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-400',
    ANNUAL:    'bg-amber-100 dark:bg-amber-900/20 text-amber-700 dark:text-amber-400',
    ONCE:      'bg-rose-100 dark:bg-rose-900/20 text-rose-700 dark:text-rose-400',
    SPECIAL:   'bg-orange-100 dark:bg-orange-900/20 text-orange-700 dark:text-orange-400',
    FARO:      'bg-emerald-100 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-400',
    ONLINE:    'bg-cyan-100 dark:bg-cyan-900/20 text-cyan-700 dark:text-cyan-400',
};

const DAY_LABELS = ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado'];

interface AudiencePreset {
    id: string;
    name: string;
    target_audience: 'ALL' | 'ROLE' | 'MANUAL';
    target_role_ids: number[];
    target_member_ids: number[];
}

function parseAndValidateTime(timeStr: string): { valid: boolean; minutes: number; normalized: string } {
    if (!timeStr) return { valid: false, minutes: 0, normalized: '' };
    
    const clean = timeStr.trim().toLowerCase().replace(/\s+/g, ' ');
    
    // Handle standard 24h format HH:MM
    const match24 = clean.match(/^(\d{1,2}):(\d{2})$/);
    if (match24) {
        const h = parseInt(match24[1], 10);
        const m = parseInt(match24[2], 10);
        if (h >= 0 && h < 24 && m >= 0 && m < 60) {
            const padH = String(h).padStart(2, '0');
            const padM = String(m).padStart(2, '0');
            return { valid: true, minutes: h * 60 + m, normalized: `${padH}:${padM}` };
        }
    }
    
    // Handle formats with AM/PM (could be a. m., p. m., a.m., p.m., am, pm, etc.)
    const matchAmpm = clean.match(/^(\d{1,2}):(\d{2})\s*([ap](?:\.?,?\s*m?\.?)?)/i);
    if (matchAmpm) {
        let h = parseInt(matchAmpm[1], 10);
        const m = parseInt(matchAmpm[2], 10);
        const periodStr = matchAmpm[3];
        
        const isPm = periodStr.includes('p');
        const isAm = periodStr.includes('a');
        
        if (h >= 1 && h <= 12 && m >= 0 && m < 60 && (isAm || isPm)) {
            if (isPm && h < 12) {
                h += 12;
            } else if (isAm && h === 12) {
                h = 0;
            }
            const padH = String(h).padStart(2, '0');
            const padM = String(m).padStart(2, '0');
            return { valid: true, minutes: h * 60 + m, normalized: `${padH}:${padM}` };
        }
    }
    
    return { valid: false, minutes: 0, normalized: '' };
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
        target_member_ids: [] as string[],
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
    const [attendedMemberIds, setAttendedMemberIds] = useState<number[]>([]);
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
                const mid = result.member_id;
                if (!attendedMemberIds.includes(mid)) {
                    setAttendedMemberIds(prev => [...prev, mid]);
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
                apiFetch<Member[]>('/crm/members/', { token, cache: 'no-store' }),
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
            const count = Array.isArray(event.target_member_ids) ? event.target_member_ids.length : 0;
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
        `${a.first_name} ${a.last_name}`.localeCompare(`${b.first_name} ${b.last_name}`)
    );

    const filterMembersByQuery = (query: string) => {
        const normalized = query.trim().toLowerCase();
        if (!normalized) return sortedMembers;
        return sortedMembers.filter((member) =>
            `${member.first_name} ${member.last_name}`.toLowerCase().includes(normalized) ||
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
            target_member_ids: preset.target_audience === 'MANUAL' ? preset.target_member_ids.map(String) : [],
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
            target_member_ids: preset.target_audience === 'MANUAL' ? preset.target_member_ids : [],
        });
        setEditManualSearch('');
        addToast(`Plantilla aplicada: ${preset.name}`, "success");
    };

    const saveAudiencePreset = (source: { target_audience: string; target_role_ids?: Array<string | number>; target_member_ids?: Array<string | number> }) => {
        const targetAudience = source.target_audience as AudiencePreset['target_audience'];
        const targetRoleIds = (source.target_role_ids || []).map((value) => Number(value)).filter((value) => Number.isFinite(value));
        const targetMemberIds = (source.target_member_ids || []).map((value) => Number(value)).filter((value) => Number.isFinite(value));

        if (targetAudience === 'ROLE' && targetRoleIds.length === 0) {
            addToast("No puedes guardar una plantilla de roles sin roles seleccionados", "error");
            return;
        }
        if (targetAudience === 'MANUAL' && targetMemberIds.length === 0) {
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
                target_member_ids: targetAudience === 'MANUAL' ? targetMemberIds : [],
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
                target_member_ids: [],
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
        if (newEvent.target_audience === 'MANUAL' && newEvent.target_member_ids.length === 0) {
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
            target_member_ids: number[];
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
            target_member_ids: newEvent.target_audience === 'MANUAL' ? newEvent.target_member_ids.map((value) => Number(value)) : [],
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
            setNewEvent({ name: '', description: '', event_type: 'PERMANENT', target_audience: 'ALL', target_role_id: '', target_role_ids: [], target_member_ids: [], day_of_week: '0', month_day: '', fixed_date: '', start_time: '', end_time: '' });
            fetchData();
        } catch (error: any) {
            console.error("Error creating event:", error);
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
            return Array.isArray(event.target_member_ids) ? event.target_member_ids.length : 0;
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
                setAttendedMemberIds(Array.isArray(data?.attendees) ? data.attendees.map((item) => item.member_id) : []);
            } catch {
                setAttendedMemberIds([]);
                addToast("No se pudo cargar la asistencia guardada para esa fecha", "error");
            } finally {
                setAttendanceLoading(false);
            }
        };

        loadAttendanceSession();
    }, [addToast, attendanceDate, isAttendanceDrawerOpen, selectedEvent, token]);

    const saveAttendance = async () => {
        if (!selectedEvent) return;
        const normalizedStatus = String(selectedEvent.status || '').toUpperCase();
        if (normalizedStatus === 'CANCELLED' || normalizedStatus === 'CANCELED') {
            addToast("No se puede registrar asistencia en eventos cancelados", "error");
            return;
        }
        if (expectedUniverseMembers.length > 0 && attendedMemberIds.length === 0) {
            const confirmed = window.confirm(
                "Vas a guardar 0 presentes y marcar pendientes como ausentes para esta fecha. ¿Deseas continuar?"
            );
            if (!confirmed) return;
        }
        setSavingAttendance(true);
        try {
            const result = await apiFetch<BulkAttendanceSyncResult>('/evangelism/attendance/bulk', {
                method: 'POST',
                token,
                body: {
                    event_id: selectedEvent.id,
                    member_ids: attendedMemberIds,
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

    const toggleAttendance = (id: number) => {
        setAttendedMemberIds(prev =>
            prev.includes(id) ? prev.filter(mId => mId !== id) : [...prev, id]
        );
    };

    const expectedUniverseMembers = members.filter((member) => {
        if (!selectedEvent) {
            return true;
        }
        if (selectedEvent.target_audience === 'MANUAL') {
            return Array.isArray(selectedEvent.target_member_ids) && selectedEvent.target_member_ids.includes(member.id);
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
        const matchesSearch = !query || `${member.first_name} ${member.last_name}`.toLowerCase().includes(query) || member.email.toLowerCase().includes(query);
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

    const heroWatchers = ['Eventos', 'Optimus Brain'];

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
        target_member_ids?: number[];
    }) => {
        if (!token) return;
        if (payload.target_audience === 'ROLE' && (!Array.isArray(payload.target_role_ids) || payload.target_role_ids.length === 0)) {
            toast.error('Selecciona al menos un rol esperado antes de guardar');
            return;
        }
        if (payload.target_audience === 'MANUAL' && (!Array.isArray(payload.target_member_ids) || payload.target_member_ids.length === 0)) {
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
            console.error("Error updating event:", error);
            const msg = error?.message || 'Error al actualizar el evento';
            toast.error(msg);
        } finally {
            setUpdatingEventId(null);
        }
    };

    return (
        <EvangelismShell
            breadcrumbs={[{ label: 'CCF', icon: Calendar }, { label: 'Evangelismo', icon: Users }, { label: 'Eventos', icon: Calendar }]}
            viewOptions={ALL_VIEWS}
            viewType={viewType}
            onViewChange={(view) => setViewType(view as ViewType)}
            rightActions={
                <SplitDropdownButton
                    mainLabel="Nuevo"
                    icon={Plus}
                    onMainClick={() => setIsCreateDrawerOpen(true)}
                    options={[
                        { id: 'event', label: 'Evento', icon: Calendar, onClick: () => setIsCreateDrawerOpen(true) },
                        { id: 'attendance', label: 'Pasar Asistencia', icon: Check, onClick: () => setViewType('table') }
                    ]}
                />
            }
        >
        <AdminHero
            eyebrow="Eventos"
            title="Eventos y asistencia"
            description="Programa encuentros recurrentes y registra la participación en tiempo real con paneles estilo ClickUp."
            tags={['Agenda', 'Asistencia', 'IA']}
            watchers={heroWatchers}
            primaryAction={{ label: 'Crear evento', icon: Plus, onClick: () => setIsCreateDrawerOpen(true) }}
            secondaryAction={{ label: 'Ver calendario', icon: Link2, onClick: () => setViewType('calendar') }}
        />
        <div className="space-y-3">
            {/* View switcher */}
            <div className="flex items-center justify-end">
                <ViewSwitcher
                    viewType={viewType}
                    setViewType={setViewType}
                    availableViews={ALL_VIEWS}
                    storageKey="evangelism_events_view"
                />
            </div>

            {loading ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {Array.from({ length: 6 }).map((_, i) => (
                        <div key={i} className="animate-pulse h-48 rounded-xl bg-slate-100 dark:bg-white/5" />
                    ))}
                </div>
            ) : (
            <>
            {/* GRID VIEW */}
            {viewType === 'grid' && (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {events.length === 0 ? (
                        <div className="col-span-3 py-24 text-center text-slate-400 text-sm">
                            No hay eventos registrados
                        </div>
                    ) : events.map(ev => (
                        (() => {
                            const attendanceStat = getEventAttendanceStat(ev);
                            return (
                        <div 
                            key={ev.id} 
                            onClick={() => router.push(`/evangelism/events/${ev.id}`)}
                            className="p-4 rounded-xl border border-slate-100 dark:border-white/5 bg-white dark:bg-[#1e1f21] hover:border-blue-500/30 hover:shadow-2xl hover:shadow-blue-500/10 transition-all group flex flex-col justify-between cursor-pointer"
                        >
                            <div>
                                <div className="flex justify-between items-start mb-4">
                                    <div className="flex gap-2 items-center">
                                        <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-blue-50 to-indigo-50 text-blue-600 flex items-center justify-center">
                                            <Calendar size={20} />
                                        </div>
                                        {ev.status === 'CANCELLED' && (
                                            <span className="px-3 py-1 text-[10px] font-black uppercase tracking-widest rounded-full bg-red-100 dark:bg-red-900/20 text-red-600 dark:text-red-400" title={ev.cancellation_reason}>
                                                Cancelado
                                            </span>
                                        )}
                                    </div>
                                    <span className={`px-3 py-1 text-[10px] font-black uppercase tracking-widest rounded-full ${EVENT_TYPE_COLOR[ev.event_type] ?? 'bg-slate-100 text-slate-500'}`}>
                                        {EVENT_TYPE_LABEL[ev.event_type] ?? ev.event_type}
                                    </span>
                                </div>
                                <h3 className="text-sm font-black text-slate-900 dark:text-white mb-2 truncate group-hover:text-blue-600 transition-colors uppercase italic pr-4">
                                    {ev.name}
                                </h3>
                                <p className="text-sm font-medium text-slate-500 line-clamp-2">{ev.description || 'Evento comunitario de CCF.'}</p>
                                <div className="mt-3 flex flex-wrap gap-2">
                                    <span className="px-2.5 py-1 rounded-full text-[10px] font-black uppercase tracking-widest bg-slate-100 dark:bg-white/10 text-slate-500">
                                        {getTargetRoleLabel(ev)}
                                    </span>
                                    <span className="px-2.5 py-1 rounded-full text-[10px] font-black uppercase tracking-widest bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-300">
                                        Universo: {attendanceStat.expected}
                                    </span>
                                    <span className="px-2.5 py-1 rounded-full text-[10px] font-black uppercase tracking-widest bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-300">
                                        {attendanceStat.attended} / {attendanceStat.expected || 0} ({attendanceStat.rate}%)
                                    </span>
                                </div>
                            </div>
                            <div className="mt-6 flex items-center justify-between gap-2">
                                <button onClick={(e) => { e.stopPropagation(); openQr(ev); }} className="size-8 flex items-center justify-center bg-slate-50 dark:bg-white/5 hover:bg-blue-600 text-slate-400 hover:text-white rounded-xl transition-all shrink-0" title="Generar QR">
                                    <QrCode size={16} />
                                </button>
                                <button onClick={(e) => { e.stopPropagation(); openAttendance(ev); }} className="flex-1 py-1.5 bg-slate-50 dark:bg-white/5 group-hover:bg-blue-600 text-slate-500 group-hover:text-white rounded-xl text-[10px] font-black uppercase tracking-widest transition-all">
                                    Panel de Asistencia
                                </button>
                                <div className="relative shrink-0" onClick={e => e.stopPropagation()}>
                                    <button
                                        onClick={() => setMenuOpenId(menuOpenId === ev.id ? null : ev.id)}
                                        className="size-8 flex items-center justify-center bg-slate-50 dark:bg-white/5 hover:bg-slate-200 dark:hover:bg-white/10 text-slate-400 rounded-xl transition-all"
                                    >
                                        <MoreVertical size={16} />
                                    </button>
                                    {menuOpenId === ev.id && (
                                        <div className="absolute right-0 bottom-12 z-50 bg-white dark:bg-[#18181b] border border-slate-200 dark:border-white/10 rounded-2xl shadow-2xl overflow-hidden w-40 animate-in fade-in slide-in-from-bottom-2">
                                            <button
                                                onClick={() => { setEditingEvent({ ...ev, target_role_ids: getTargetRoleIds(ev) }); setMenuOpenId(null); }}
                                                className="w-full flex items-center gap-3 px-4 py-1.5 text-sm font-bold text-slate-700 dark:text-white hover:bg-blue-50 dark:hover:bg-white/5 transition-all"
                                            >
                                                <Pencil size={14} className="text-blue-500" /> Editar
                                            </button>
                                            <button
                                                onClick={() => { setDeletingEventId(ev.id); setMenuOpenId(null); }}
                                                className="w-full flex items-center gap-3 px-4 py-1.5 text-sm font-bold text-red-600 hover:bg-red-50 dark:hover:bg-red-900/10 transition-all"
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
                <div className="bg-white dark:bg-[#1e1f21] rounded-xl border border-slate-100 dark:border-white/5 overflow-hidden shadow-sm divide-y divide-slate-100 dark:divide-white/5">
                    {events.map(ev => {
                        const attendanceStat = getEventAttendanceStat(ev);
                        return (
                        <div key={ev.id} className="flex items-center gap-4 px-4 py-2 hover:bg-slate-50 dark:hover:bg-white/5 transition-colors group">
                            <div className="w-9 h-9 rounded-xl bg-blue-50 dark:bg-blue-900/20 text-blue-600 flex items-center justify-center shrink-0">
                                <Calendar size={16} />
                            </div>
                            <div className="flex-1 min-w-0">
                                <p 
                                    onClick={() => router.push(`/evangelism/events/${ev.id}`)}
                                    className="font-bold text-slate-800 dark:text-slate-100 text-sm truncate cursor-pointer hover:text-blue-600 transition-colors"
                                >
                                    {ev.name}
                                </p>
                                <p className="text-xs text-slate-400 truncate">{ev.description || 'Sin descripción'}</p>
                            </div>
                            <div className="flex gap-2 items-center">
                                {ev.status === 'CANCELLED' && (
                                    <span className="px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase bg-red-100 dark:bg-red-900/20 text-red-600 dark:text-red-400" title={ev.cancellation_reason}>
                                        Cancelado
                                    </span>
                                )}
                                <span className="px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase bg-slate-100 dark:bg-white/10 text-slate-500">
                                    {getTargetRoleLabel(ev)}
                                </span>
                                <span className="px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-300">
                                    Universo: {attendanceStat.expected}
                                </span>
                                <span className="px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-300">
                                    {attendanceStat.attended} / {attendanceStat.expected || 0} ({attendanceStat.rate}%)
                                </span>
                                <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase ${EVENT_TYPE_COLOR[ev.event_type] ?? 'bg-slate-100 dark:bg-white/10 text-slate-500'}`}>
                                    {EVENT_TYPE_LABEL[ev.event_type] ?? ev.event_type}
                                </span>
                            </div>
                            <button onClick={(e) => { e.stopPropagation(); openQr(ev); }} className="px-3 py-1.5 rounded-xl bg-blue-50 dark:bg-blue-900/20 text-blue-600 text-[10px] font-black uppercase opacity-0 group-hover:opacity-100 transition-opacity mr-2">
                                QR
                            </button>
                            <button onClick={(e) => { e.stopPropagation(); openAttendance(ev); }} className="px-3 py-1.5 rounded-xl bg-blue-50 dark:bg-blue-900/20 text-blue-600 text-[10px] font-black uppercase opacity-0 group-hover:opacity-100 transition-opacity">
                                Asistencia
                            </button>
                        </div>
                        );
                    })}
                </div>
            )}

            {viewType === 'table' && (
                <div className="overflow-hidden rounded-xl border border-slate-100 dark:border-white/5 bg-white dark:bg-[#1e1f21] shadow-sm">
                    <table className="w-full text-left">
                        <thead className="bg-slate-50 dark:bg-white/5">
                            <tr>
                                {['Evento', 'Tipo', 'Audiencia', 'Universo', 'Asistencia', 'Fecha visual'].map((label) => (
                                    <th key={label} className="px-5 py-2 text-[10px] font-black uppercase tracking-widest text-slate-400">
                                        {label}
                                    </th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {events.map((event) => {
                                const attendanceStat = getEventAttendanceStat(event);
                                return (
                                    <tr key={event.id} className="border-t border-slate-100 dark:border-white/5 hover:bg-slate-50 dark:hover:bg-white/[0.02]">
                                        <td className="px-5 py-2">
                                            <button onClick={() => router.push(`/evangelism/events/${event.id}`)} className="font-bold text-slate-800 dark:text-slate-100 hover:text-blue-600">
                                                {event.name}
                                            </button>
                                        </td>
                                        <td className="px-5 py-2 text-xs font-bold text-slate-500">{EVENT_TYPE_LABEL[event.event_type] ?? event.event_type}</td>
                                        <td className="px-5 py-2 text-xs text-slate-500">{getTargetRoleLabel(event)}</td>
                                        <td className="px-5 py-2 text-xs text-slate-500">{attendanceStat.expected}</td>
                                        <td className="px-5 py-2 text-xs font-bold text-emerald-600">{attendanceStat.rate}%</td>
                                        <td className="px-5 py-2 text-xs text-slate-500">{getVisualDate(event)}</td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                    {events.length === 0 && <div className="py-6 text-center text-sm text-slate-400">No hay eventos registrados</div>}
                </div>
            )}

            {(viewType === 'board' || viewType === 'kanban') && (
                <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
                    {boardColumns.map((column) => (
                        <section key={column.key} className="rounded-xl border border-slate-100 bg-white p-4 shadow-sm dark:border-white/5 dark:bg-[#1e1f21]">
                            <header className="mb-4 flex items-center justify-between">
                                <h3 className="text-[11px] font-black uppercase tracking-widest text-slate-500">{column.label}</h3>
                                <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-black text-slate-500 dark:bg-white/10">
                                    {column.items.length}
                                </span>
                            </header>
                            <div className="space-y-3">
                                {column.items.map((event) => {
                                    const attendanceStat = getEventAttendanceStat(event);
                                    return (
                                        <button
                                            key={event.id}
                                            onClick={() => router.push(`/evangelism/events/${event.id}`)}
                                            className="w-full rounded-2xl border border-slate-100 p-4 text-left transition-all hover:border-blue-500/30 hover:shadow-lg dark:border-white/5"
                                        >
                                            <p className="text-sm font-black text-slate-900 dark:text-white">{event.name}</p>
                                            <p className="mt-1 text-[11px] text-slate-500">{getTargetRoleLabel(event)}</p>
                                            <div className="mt-3 flex items-center justify-between text-[10px] font-black uppercase tracking-widest text-slate-400">
                                                <span>{EVENT_TYPE_LABEL[event.event_type] ?? event.event_type}</span>
                                                <span>{attendanceStat.rate}%</span>
                                            </div>
                                        </button>
                                    );
                                })}
                                {column.items.length === 0 && <div className="py-6 text-center text-xs text-slate-400">Sin eventos</div>}
                            </div>
                        </section>
                    ))}
                </div>
            )}

            {viewType === 'calendar' && (
                <div className="rounded-xl border border-slate-100 bg-white p-4 shadow-sm dark:border-white/5 dark:bg-[#1e1f21]">
                    <UniversalCalendarView events={calendarEvents} title="Calendario de eventos" />
                </div>
            )}

            {viewType === 'gantt' && (
                <div className="rounded-xl border border-slate-100 bg-white p-4 shadow-sm dark:border-white/5 dark:bg-[#1e1f21]">
                    <UniversalGanttView items={ganttItems} moduleName="Eventos" />
                </div>
            )}

            {viewType === 'wiki' && (
                <section className="rounded-xl border border-slate-100 bg-white p-5 shadow-sm dark:border-white/5 dark:bg-[#1e1f21]">
                    <p className="mb-3 text-[10px] font-black uppercase tracking-widest text-slate-500">Wiki de eventos</p>
                    <textarea
                        value={wikiNotes}
                        onChange={(event) => setWikiNotes(event.target.value)}
                        placeholder="Documenta protocolos, checklist de registro, roles y aprendizajes de cada evento..."
                        className="min-h-[360px] w-full rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm font-medium text-slate-700 outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-white/10 dark:bg-black/20 dark:text-slate-200"
                    />
                </section>
            )}
            </>
            )}
        </div>

        {/* â”€â”€â”€ Drawer: Crear Evento â”€â”€â”€ */}
        <WorkspaceDrawer
            isOpen={isCreateDrawerOpen}
            onClose={() => setIsCreateDrawerOpen(false)}
            title="Nuevo Evento"
            subtitle="Configura un evento de la iglesia"
            actions={
                <>
                    <button type="button" disabled={savingCreateEvent} onClick={() => setIsCreateDrawerOpen(false)} className="px-4 py-2 text-[11px] font-bold text-slate-500 hover:text-slate-700 transition-colors disabled:opacity-60">
                        Cancelar
                    </button>
                    <button
                        form="create-event-form"
                        type="submit"
                        disabled={savingCreateEvent}
                        className="px-5 py-2 bg-blue-600 text-white rounded-lg text-[11px] font-black uppercase tracking-widest shadow-lg shadow-blue-500/20 hover:bg-blue-700 active:scale-95 transition-all flex items-center gap-2 disabled:opacity-60 disabled:active:scale-100"
                    >
                        {savingCreateEvent ? 'Guardando...' : 'Guardar'} <Check size={14} />
                    </button>
                </>
            }
        >
            <form id="create-event-form" onSubmit={handleCreateEvent} className="space-y-3">
                <div className="space-y-1.5">
                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Nombre del Evento *</label>
                    <input
                        required
                        value={newEvent.name}
                        onChange={e => setNewEvent({ ...newEvent, name: e.target.value })}
                        className="w-full px-4 py-1.5 rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-black/20 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm text-slate-800 dark:text-white"
                        placeholder="Ej: Servicio Dominical"
                    />
                </div>

                <div className="space-y-1.5">
                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Tipo de Evento *</label>
                    <select
                        required
                        value={newEvent.event_type}
                        onChange={e => setNewEvent({ ...newEvent, event_type: e.target.value })}
                        className="w-full px-4 py-1.5 rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-black/20 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm text-slate-800 dark:text-white appearance-none"
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
                        <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Universo Esperado</label>
                        <select
                            value={newEvent.target_audience}
                            onChange={e => setNewEvent({
                                ...newEvent,
                                target_audience: e.target.value,
                                target_role_id: e.target.value === 'ROLE' ? newEvent.target_role_id : '',
                                target_role_ids: e.target.value === 'ROLE' ? newEvent.target_role_ids : [],
                                target_member_ids: e.target.value === 'MANUAL' ? newEvent.target_member_ids : [],
                            })}
                            className="w-full px-4 py-1.5 rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-black/20 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm text-slate-800 dark:text-white appearance-none"
                        >
                            <option value="ALL">Toda la iglesia</option>
                            <option value="ROLE">Uno o varios roles</option>
                            <option value="MANUAL">Selección manual</option>
                        </select>
                    </div>
                    <div className="space-y-1.5">
                        <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Roles esperados</label>
                        <select
                            multiple
                            disabled={newEvent.target_audience !== 'ROLE'}
                            value={newEvent.target_role_ids}
                            onChange={e => {
                                const selectedValues = Array.from(e.target.selectedOptions).map((option) => option.value);
                                setNewEvent({ ...newEvent, target_role_ids: selectedValues, target_role_id: selectedValues[0] || '' });
                            }}
                            className="min-h-[140px] w-full px-4 py-1.5 rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-black/20 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm text-slate-800 dark:text-white disabled:opacity-50"
                        >
                            {roles.map((role) => (
                                <option key={role.id} value={role.id}>{role.name}</option>
                            ))}
                        </select>
                    </div>
                </div>

                <div className="space-y-3 rounded-xl border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-black/20 p-4">
                    <div className="flex items-center justify-between gap-3">
                        <div>
                            <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">Plantillas de audiencia</p>
                            <p className="text-sm font-bold text-slate-700 dark:text-slate-200">Guarda y reaplica universos esperados frecuentes</p>
                        </div>
                        <div className="flex items-center gap-2">
                            <button
                                type="button"
                                onClick={addSuggestedAudiencePresets}
                                className="rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 px-4 py-2 text-[10px] font-black uppercase tracking-widest text-slate-600 dark:text-slate-200 transition-all hover:bg-slate-100 dark:hover:bg-white/10"
                            >
                                Sugerencias
                            </button>
                            <button
                                type="button"
                                onClick={() => saveAudiencePreset(newEvent)}
                                className="rounded-2xl bg-blue-600 px-4 py-2 text-[10px] font-black uppercase tracking-widest text-white transition-all hover:bg-blue-700"
                            >
                                Guardar actual
                            </button>
                        </div>
                    </div>
                    <div className="space-y-2">
                        {audiencePresets.length === 0 ? (
                            <div className="rounded-2xl border border-dashed border-slate-200 dark:border-white/10 px-4 py-5 text-center text-sm text-slate-400">
                                Aun no hay plantillas guardadas
                            </div>
                        ) : audiencePresets.map((preset) => (
                            <div key={preset.id} className="flex items-center justify-between gap-3 rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 px-4 py-1.5">
                                <div className="min-w-0">
                                    <p className="truncate text-sm font-bold text-slate-800 dark:text-white">{preset.name}</p>
                                    <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">
                                        {preset.target_audience === 'ALL'
                                            ? 'Toda la iglesia'
                                            : preset.target_audience === 'ROLE'
                                                ? `${preset.target_role_ids.length} roles`
                                                : `${preset.target_member_ids.length} personas`}
                                    </p>
                                </div>
                                <div className="flex items-center gap-2">
                                    <button
                                        type="button"
                                        onClick={() => applyPresetToCreateEvent(preset.id)}
                                        className="rounded-2xl bg-slate-900 px-3 py-2 text-[10px] font-black uppercase tracking-widest text-white transition-all hover:opacity-85 dark:bg-white/10"
                                    >
                                        Aplicar
                                    </button>
                                    <button
                                        type="button"
                                        onClick={() => deleteAudiencePreset(preset.id)}
                                        className="rounded-2xl border border-slate-200 dark:border-white/10 px-3 py-2 text-[10px] font-black uppercase tracking-widest text-slate-500 transition-all hover:bg-slate-100 dark:hover:bg-white/5"
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
                            <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Personas esperadas</label>
                            <span className="rounded-full bg-blue-50 dark:bg-blue-900/20 px-3 py-1 text-[10px] font-black uppercase tracking-widest text-blue-600 dark:text-blue-300">
                                {newEvent.target_member_ids.length} seleccionadas
                            </span>
                        </div>
                        <input
                            value={createManualSearch}
                            onChange={e => setCreateManualSearch(e.target.value)}
                            placeholder="Buscar por nombre, correo o rol..."
                            className="w-full rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-black/20 px-4 py-1.5 text-sm font-bold text-slate-800 dark:text-white outline-none focus:ring-2 focus:ring-blue-500/20"
                        />
                        <div className="max-h-64 space-y-2 overflow-y-auto rounded-2xl border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-black/20 p-3">
                            {createManualMembers.map((member) => {
                                const isSelected = newEvent.target_member_ids.includes(String(member.id));
                                return (
                                    <button
                                        key={member.id}
                                        type="button"
                                        onClick={() => setNewEvent({
                                            ...newEvent,
                                            target_member_ids: isSelected
                                                ? newEvent.target_member_ids.filter((value) => value !== String(member.id))
                                                : [...newEvent.target_member_ids, String(member.id)],
                                        })}
                                        className={`flex w-full items-center justify-between rounded-2xl border px-4 py-1.5 text-left transition-all ${
                                            isSelected
                                                ? 'border-blue-200 bg-blue-50 dark:border-blue-800 dark:bg-blue-900/20'
                                                : 'border-slate-200 bg-white dark:border-white/10 dark:bg-white/5'
                                        }`}
                                    >
                                        <div>
                                            <p className="text-sm font-bold text-slate-800 dark:text-white">{member.first_name} {member.last_name}</p>
                                            <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">{member.church_role || 'Sin rol'}</p>
                                        </div>
                                        <span className={`text-[10px] font-black uppercase tracking-widest ${isSelected ? 'text-blue-600 dark:text-blue-300' : 'text-slate-400'}`}>
                                            {isSelected ? 'Incluida' : 'Agregar'}
                                        </span>
                                    </button>
                                );
                            })}
                            {createManualMembers.length === 0 && (
                                <div className="py-6 text-center text-sm text-slate-400">No hay personas para este filtro</div>
                            )}
                        </div>
                    </div>
                )}

                <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-1.5">
                        <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Hora de Inicio *</label>
                        <input
                            type="time"
                            required
                            value={newEvent.start_time}
                            onChange={e => setNewEvent({ ...newEvent, start_time: e.target.value })}
                            className="w-full px-4 py-1.5 rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-black/20 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm text-slate-800 dark:text-white"
                        />
                    </div>
                    <div className="space-y-1.5">
                        <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Hora de Finalización *</label>
                        <input
                            type="time"
                            required
                            value={newEvent.end_time}
                            onChange={e => setNewEvent({ ...newEvent, end_time: e.target.value })}
                            className="w-full px-4 py-1.5 rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-black/20 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm text-slate-800 dark:text-white"
                        />
                    </div>
                </div>

                {['PERMANENT', 'FARO', 'ONLINE'].includes(newEvent.event_type) && (
                    <div className="space-y-1.5">
                        <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Día de la Semana</label>
                        <select
                            value={newEvent.day_of_week}
                            onChange={e => setNewEvent({ ...newEvent, day_of_week: e.target.value })}
                            className="w-full px-4 py-1.5 rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-black/20 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm dark:text-white"
                        >
                            {DAY_LABELS.map((d, i) => <option key={i} value={i}>{d}</option>)}
                        </select>
                    </div>
                )}

                {['ONCE', 'SPECIAL'].includes(newEvent.event_type) && (
                    <div className="space-y-1.5">
                        <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Fecha Exacta</label>
                        <input
                            type="date"
                            value={newEvent.fixed_date}
                            onChange={e => setNewEvent({ ...newEvent, fixed_date: e.target.value })}
                            className="w-full px-4 py-1.5 rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-black/20 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm dark:text-white"
                        />
                    </div>
                )}

                {['ANNUAL', 'MONTHLY'].includes(newEvent.event_type) && (
                    <div className="space-y-1.5">
                        <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Día(s) del Mes / Año</label>
                        <input
                            value={newEvent.month_day}
                            onChange={e => setNewEvent({ ...newEvent, month_day: e.target.value })}
                            className="w-full px-4 py-1.5 rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-black/20 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm dark:text-white"
                            placeholder="Ej: 15 de cada mes, o 24 Dic"
                        />
                    </div>
                )}

                <div className="space-y-1.5">
                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest">descripción</label>
                    <textarea
                        value={newEvent.description}
                        onChange={e => setNewEvent({ ...newEvent, description: e.target.value })}
                        rows={3}
                        className="w-full px-4 py-1.5 rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-black/20 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm dark:text-white resize-none"
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
                        <Calendar size={14} className="text-slate-400" />
                        <input
                            type="date"
                            value={attendanceDate}
                            onChange={e => setAttendanceDate(e.target.value)}
                            className="text-sm font-bold text-slate-700 dark:text-slate-300 outline-none bg-transparent"
                        />
                    </div>
                    <button disabled={savingAttendance} onClick={() => setIsAttendanceDrawerOpen(false)} className="px-4 py-2 text-[11px] font-bold text-slate-500 disabled:opacity-60">
                        Cancelar
                    </button>
                    <button
                        onClick={saveAttendance}
                        disabled={savingAttendance || attendanceLoading || String(selectedEvent?.status || '').toUpperCase() === 'CANCELLED' || String(selectedEvent?.status || '').toUpperCase() === 'CANCELED'}
                        className="px-5 py-2 bg-emerald-600 text-white rounded-lg text-[11px] font-black uppercase tracking-widest shadow-lg shadow-emerald-500/20 hover:bg-emerald-700 active:scale-95 transition-all disabled:opacity-60 disabled:active:scale-100"
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
                        className={`px-4 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all ${showScanner ? 'bg-rose-500 text-white' : 'bg-slate-900 dark:bg-white/10 text-white hover:opacity-80'}`}
                    >
                        {showScanner ? 'Cerrar Escáner' : 'Modo Escáner'}
                    </button>
                </div>

                {showScanner && (
                    <div className="p-4 bg-slate-900 dark:bg-black/40 rounded-2xl space-y-4">
                        <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest text-center">Ingresa el token del carnet (CCF-MBR-ID-TOKEN)</p>
                        <div className="flex gap-2">
                            <input
                                type="text"
                                value={scannerToken}
                                onChange={e => setScannerToken(e.target.value)}
                                placeholder="CCF-MBR-1-XXXXXX"
                                className="flex-1 bg-slate-950 border border-white/10 rounded-xl px-4 py-1.5 text-sm text-white focus:outline-none focus:border-blue-500"
                                onKeyDown={e => e.key === 'Enter' && handleScanToken()}
                            />
                            <button
                                onClick={handleScanToken}
                                disabled={isScanning || !scannerToken}
                                className="px-4 py-1.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-xl text-[10px] font-black uppercase tracking-widest transition-all"
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
                        className="w-full rounded-2xl border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-black/20 px-4 py-1.5 text-sm font-bold text-slate-800 dark:text-white outline-none focus:ring-2 focus:ring-blue-500/20"
                    />
                    <select
                        value={attendanceRoleFilter}
                        onChange={e => setAttendanceRoleFilter(e.target.value)}
                        className="w-full rounded-2xl border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-black/20 px-4 py-1.5 text-sm font-bold text-slate-800 dark:text-white outline-none focus:ring-2 focus:ring-blue-500/20"
                    >
                        <option value="ALL">Todos los roles</option>
                        {attendanceRoleOptions.map((role) => (
                            <option key={role} value={role}>{role}</option>
                        ))}
                    </select>
                    <select
                        value={attendanceStatusFilter}
                        onChange={e => setAttendanceStatusFilter(e.target.value as 'ALL' | 'PENDING' | 'PRESENT')}
                        className="w-full rounded-2xl border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-black/20 px-4 py-1.5 text-sm font-bold text-slate-800 dark:text-white outline-none focus:ring-2 focus:ring-blue-500/20"
                    >
                        <option value="ALL">Todos</option>
                        <option value="PENDING">Pendientes</option>
                        <option value="PRESENT">Presentes</option>
                    </select>
                    <button
                        onClick={markFilteredMembers}
                        disabled={filteredMembers.length === 0}
                        className="px-4 py-1.5 rounded-2xl border border-emerald-200 dark:border-emerald-900/30 bg-emerald-50 dark:bg-emerald-900/10 text-[10px] font-black uppercase tracking-widest text-emerald-700 dark:text-emerald-300 transition-all hover:bg-emerald-100 disabled:opacity-50"
                    >
                        Marcar filtrados
                    </button>
                    <button
                        onClick={clearFilteredMembers}
                        disabled={filteredMembers.length === 0}
                        className="px-4 py-1.5 rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 text-[10px] font-black uppercase tracking-widest text-slate-500 dark:text-slate-300 transition-all hover:bg-slate-50 disabled:opacity-50"
                    >
                        Limpiar filtrados
                    </button>
                </div>

                {/* Summary badge */}
                <div className="flex items-center justify-between px-4 py-1.5 bg-emerald-50 dark:bg-emerald-900/20 rounded-2xl border border-emerald-100 dark:border-emerald-900/30">
                    <div>
                        <p className="text-sm font-bold text-slate-600 dark:text-slate-300">Presentes</p>
                        <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">
                            {attendanceLoading ? 'Cargando sesión...' : `${filteredMembers.length} visibles en esta búsqueda`}
                        </p>
                    </div>
                    <p className="text-base font-black text-emerald-600">{attendedMemberIds.length} <span className="text-sm font-bold text-slate-400">/ {expectedUniverseMembers.length}</span></p>
                </div>

                {!attendanceLoading && (
                    <div className="flex flex-wrap gap-2">
                        <span className="rounded-full border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 px-3 py-1 text-[10px] font-black uppercase tracking-widest text-slate-500 dark:text-slate-300">
                            {selectedEvent?.target_audience === 'ROLE'
                                ? `Universo: ${getTargetRoleLabel(selectedEvent)}`
                                : 'Universo: toda la iglesia'}
                        </span>
                        <span className="rounded-full border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 px-3 py-1 text-[10px] font-black uppercase tracking-widest text-slate-500 dark:text-slate-300">
                            {attendanceRoleFilter === 'ALL' ? 'Todos los roles visibles' : attendanceRoleFilter}
                        </span>
                        <span className="rounded-full border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 px-3 py-1 text-[10px] font-black uppercase tracking-widest text-slate-500 dark:text-slate-300">
                            {attendanceStatusFilter === 'ALL' ? 'Vista completa' : attendanceStatusFilter === 'PENDING' ? 'Solo pendientes' : 'Solo presentes'}
                        </span>
                    </div>
                )}

                {/* Member list */}
                <div className="grid grid-cols-1 gap-3">
                    {attendanceLoading ? (
                        <div className="py-12 text-center text-slate-400 text-sm">Cargando asistencia registrada...</div>
                    ) : filteredMembers.map(member => (
                        <div
                            key={member.id}
                            onClick={() => toggleAttendance(member.id)}
                            className={`flex items-center p-4 rounded-2xl cursor-pointer transition-all border ${attendedMemberIds.includes(member.id)
                                ? 'bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200 dark:border-emerald-700/30 shadow-sm'
                                : 'bg-slate-50 dark:bg-white/5 border-slate-100 dark:border-white/5 hover:border-slate-300 dark:hover:border-white/10'
                            }`}
                        >
                            <div className={`w-6 h-6 rounded-full border-2 flex items-center justify-center mr-4 transition-colors shrink-0 ${attendedMemberIds.includes(member.id)
                                ? 'bg-emerald-500 border-emerald-500 text-white'
                                : 'border-slate-300 dark:border-white/20 bg-white dark:bg-black/20'
                            }`}>
                                {attendedMemberIds.includes(member.id) && <Check size={12} strokeWidth={4} />}
                            </div>
                            <div>
                                <p className={`font-bold text-sm ${attendedMemberIds.includes(member.id) ? 'text-emerald-900 dark:text-emerald-200' : 'text-slate-700 dark:text-slate-300'}`}>
                                    {member.first_name} {member.last_name}
                                </p>
                                <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">
                                    {member.church_role || 'Sin rol'}
                                </p>
                            </div>
                        </div>
                    ))}
                    {!attendanceLoading && filteredMembers.length === 0 && (
                        <div className="py-12 text-center text-slate-400 text-sm">
                            {expectedUniverseMembers.length === 0 ? 'Este evento no tiene universo esperado configurado con miembros disponibles' : 'No hay miembros para este filtro'}
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
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg text-[11px] font-black uppercase tracking-widest shadow-lg shadow-blue-500/20 hover:bg-blue-700 active:scale-95 transition-all flex items-center gap-2"
                >
                    <Download size={14} /> Descargar
                </button>
            }
        >
            <div className="flex flex-col items-center justify-center space-y-3 py-4">
                <div className="p-4 bg-white rounded-xl shadow-xl border border-slate-100 dark:border-white/5 flex items-center justify-center">
                    <QRCodeSVG 
                        id="event-qr-code"
                        value={typeof window !== 'undefined' ? `${window.location.origin}/public/register?event_id=${selectedEvent?.id}` : ''}
                        size={256}
                        level="H"
                        includeMargin={true}
                    />
                </div>
                <div className="text-center space-y-2">
                    <p className="text-sm font-bold text-slate-700 dark:text-slate-300">Escanea para registrarte</p>
                    <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">Enlace de Registro</p>
                    <a href={typeof window !== 'undefined' ? `${window.location.origin}/public/register?event_id=${selectedEvent?.id}` : '#'} target="_blank" rel="noreferrer" className="text-xs font-medium text-blue-500 hover:text-blue-600 transition-colors break-all bg-blue-50 dark:bg-blue-500/10 px-4 py-2 rounded-xl inline-block mt-2">
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
                        <button disabled={deletingEventLoadingId === deletingEventId} onClick={() => setDeletingEventId(null)} className="px-4 py-2 text-[11px] font-bold text-slate-500 hover:text-slate-700 transition-colors disabled:opacity-60">
                            Cancelar
                        </button>
                        <button onClick={() => deletingEventId && handleDeleteEvent(deletingEventId)} disabled={deletingEventLoadingId === deletingEventId} className="px-5 py-2 bg-red-600 text-white rounded-lg text-[11px] font-black uppercase tracking-widest shadow-lg shadow-red-500/20 hover:bg-red-700 active:scale-95 transition-all flex items-center gap-2 disabled:opacity-60">
                            <Trash2 size={14} /> Eliminar
                        </button>
                    </>
                }
            >
                <div className="flex flex-col items-center text-center p-4 bg-red-50 dark:bg-red-900/10 rounded-xl border border-red-100 dark:border-red-900/30">
                    <div className="size-16 bg-red-100 dark:bg-red-900/40 text-red-600 dark:text-red-400 rounded-full flex items-center justify-center mb-4">
                        <Trash2 size={24} />
                    </div>
                    <p className="text-sm text-red-900 dark:text-red-200 font-bold mb-2">Se eliminará todo el historial</p>
                    <p className="text-xs text-red-700 dark:text-red-300">Esta acción también borrará los registros de asistencia asociados. No podrás recuperar esta información.</p>
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
                        <button disabled={!!editingEvent && updatingEventId === editingEvent.id} onClick={() => setEditingEvent(null)} className="px-4 py-2 text-[11px] font-bold text-slate-500 hover:text-slate-700 transition-colors disabled:opacity-60">
                            Cancelar
                        </button>
                        <button disabled={!editingEvent || updatingEventId === editingEvent.id} onClick={() => editingEvent && handleUpdateEvent(editingEvent.id, { name: editingEvent.name, description: editingEvent.description, location: editingEvent.location, status: editingEvent.status, cancellation_reason: editingEvent.cancellation_reason, start_time: editingEvent.start_time, end_time: editingEvent.end_time, target_audience: editingEvent.target_audience || 'ALL', target_role_id: (editingEvent.target_audience || 'ALL') === 'ROLE' ? (editingEvent.target_role_ids?.[0] || editingEvent.target_role_id) : null, target_role_ids: (editingEvent.target_audience || 'ALL') === 'ROLE' ? (editingEvent.target_role_ids || getTargetRoleIds(editingEvent)) : [], target_member_ids: (editingEvent.target_audience || 'ALL') === 'MANUAL' ? (editingEvent.target_member_ids || []) : [] })} className="px-5 py-2 bg-blue-600 text-white rounded-lg text-[11px] font-black uppercase tracking-widest shadow-lg shadow-blue-500/20 hover:bg-blue-700 active:scale-95 transition-all flex items-center gap-2 disabled:opacity-60">
                            {editingEvent && updatingEventId === editingEvent.id ? 'Guardando...' : 'Guardar'} <Pencil size={14} />
                        </button>
                    </>
                }
            >
                {editingEvent && (
                    <div className="space-y-3">
                        <div className="space-y-1.5">
                            <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Nombre</label>
                            <input type="text" value={editingEvent.name} onChange={e => setEditingEvent({...editingEvent, name: e.target.value})} className="w-full px-4 py-1.5 rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-black/20 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm text-slate-800 dark:text-white" />
                        </div>
                        <div className="space-y-1.5">
                            <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Estado</label>
                            <select 
                                value={editingEvent.status || 'SCHEDULED'} 
                                onChange={e => setEditingEvent({...editingEvent, status: e.target.value})} 
                                className="w-full px-4 py-1.5 rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-black/20 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm text-slate-800 dark:text-white appearance-none"
                            >
                                <option value="SCHEDULED">Programado</option>
                                <option value="COMPLETED">Realizado</option>
                                <option value="CANCELLED">Cancelado</option>
                            </select>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="space-y-1.5">
                                <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Universo Esperado</label>
                                <select
                                    value={editingEvent.target_audience || 'ALL'}
                                    onChange={e => setEditingEvent({
                                        ...editingEvent,
                                        target_audience: e.target.value as EventAudience,
                                        target_role_id: e.target.value === 'ROLE' ? editingEvent.target_role_id : null,
                                        target_role_ids: e.target.value === 'ROLE' ? (editingEvent.target_role_ids || getTargetRoleIds(editingEvent)) : [],
                                        target_member_ids: e.target.value === 'MANUAL' ? (editingEvent.target_member_ids || []) : [],
                                    })}
                                    className="w-full px-4 py-1.5 rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-black/20 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm text-slate-800 dark:text-white appearance-none"
                                >
                                    <option value="ALL">Toda la iglesia</option>
                                    <option value="ROLE">Uno o varios roles</option>
                                    <option value="MANUAL">Selección manual</option>
                                </select>
                            </div>
                            <div className="space-y-1.5">
                                <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Roles esperados</label>
                                <select
                                    multiple
                                    disabled={(editingEvent.target_audience || 'ALL') !== 'ROLE'}
                                    value={(editingEvent.target_role_ids || getTargetRoleIds(editingEvent)).map((value: number) => String(value))}
                                    onChange={e => {
                                        const selectedValues = Array.from(e.target.selectedOptions).map((option) => Number(option.value));
                                        setEditingEvent({ ...editingEvent, target_role_ids: selectedValues, target_role_id: selectedValues[0] || null });
                                    }}
                                    className="min-h-[140px] w-full px-4 py-1.5 rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-black/20 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm text-slate-800 dark:text-white disabled:opacity-50"
                                >
                                    {roles.map((role) => (
                                        <option key={role.id} value={role.id}>{role.name}</option>
                                    ))}
                                </select>
                            </div>
                        </div>
                        <div className="space-y-3 rounded-xl border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-black/20 p-4">
                            <div className="flex items-center justify-between gap-3">
                                <div>
                                    <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">Plantillas de audiencia</p>
                                    <p className="text-sm font-bold text-slate-700 dark:text-slate-200">Aplica o guarda universos reutilizables</p>
                                </div>
                                <div className="flex items-center gap-2">
                                    <button type="button" onClick={addSuggestedAudiencePresets} className="rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 px-4 py-2 text-[10px] font-black uppercase tracking-widest text-slate-600 dark:text-slate-200 transition-all hover:bg-slate-100 dark:hover:bg-white/10">Sugerencias</button>
                                    <button type="button" onClick={() => saveAudiencePreset({ target_audience: editingEvent.target_audience || 'ALL', target_role_ids: editingEvent.target_role_ids || [], target_member_ids: editingEvent.target_member_ids || [] })} className="rounded-2xl bg-blue-600 px-4 py-2 text-[10px] font-black uppercase tracking-widest text-white transition-all hover:bg-blue-700">Guardar actual</button>
                                </div>
                            </div>
                            <div className="space-y-2">
                                {audiencePresets.length === 0 ? (
                                    <div className="rounded-2xl border border-dashed border-slate-200 dark:border-white/10 px-4 py-5 text-center text-sm text-slate-400">Aun no hay plantillas guardadas</div>
                                ) : audiencePresets.map((preset) => (
                                    <div key={preset.id} className="flex items-center justify-between gap-3 rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 px-4 py-1.5">
                                        <div className="min-w-0">
                                            <p className="truncate text-sm font-bold text-slate-800 dark:text-white">{preset.name}</p>
                                            <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">{preset.target_audience === 'ALL' ? 'Toda la iglesia' : preset.target_audience === 'ROLE' ? `${preset.target_role_ids.length} roles` : `${preset.target_member_ids.length} personas`}</p>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <button type="button" onClick={() => applyPresetToEditingEvent(preset.id)} className="rounded-2xl bg-slate-900 px-3 py-2 text-[10px] font-black uppercase tracking-widest text-white transition-all hover:opacity-85 dark:bg-white/10">Aplicar</button>
                                            <button type="button" onClick={() => deleteAudiencePreset(preset.id)} className="rounded-2xl border border-slate-200 dark:border-white/10 px-3 py-2 text-[10px] font-black uppercase tracking-widest text-slate-500 transition-all hover:bg-slate-100 dark:hover:bg-white/5">Borrar</button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                        {editingEvent.target_audience === 'MANUAL' && (
                            <div className="space-y-3">
                                <div className="flex items-center justify-between gap-3">
                                    <label className="text-[10px] font-black uppercase tracking-widest text-slate-400">Personas esperadas</label>
                                    <span className="rounded-full bg-blue-50 dark:bg-blue-900/20 px-3 py-1 text-[10px] font-black uppercase tracking-widest text-blue-600 dark:text-blue-300">{(editingEvent.target_member_ids || []).length} seleccionadas</span>
                                </div>
                                <input value={editManualSearch} onChange={e => setEditManualSearch(e.target.value)} placeholder="Buscar por nombre, correo o rol..." className="w-full px-4 py-1.5 rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-black/20 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm text-slate-800 dark:text-white" />
                                <div className="max-h-64 space-y-2 overflow-y-auto rounded-2xl border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-black/20 p-3">
                                    {editManualMembers.map((member) => {
                                        const isSelected = (editingEvent.target_member_ids || []).includes(member.id);
                                        return (
                                            <button key={member.id} type="button" onClick={() => setEditingEvent({ ...editingEvent, target_member_ids: isSelected ? (editingEvent.target_member_ids || []).filter((value) => value !== member.id) : [...(editingEvent.target_member_ids || []), member.id], })} className={`flex w-full items-center justify-between rounded-2xl border px-4 py-1.5 text-left transition-all ${isSelected ? 'border-blue-200 bg-blue-50 dark:border-blue-800 dark:bg-blue-900/20' : 'border-slate-200 bg-white dark:border-white/10 dark:bg-white/5'}`}>
                                                <div>
                                                    <p className="text-sm font-bold text-slate-800 dark:text-white">{member.first_name} {member.last_name}</p>
                                                    <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">{member.church_role || 'Sin rol'}</p>
                                                </div>
                                                <span className={`text-[10px] font-black uppercase tracking-widest ${isSelected ? 'text-blue-600 dark:text-blue-300' : 'text-slate-400'}`}>{isSelected ? 'Incluida' : 'Agregar'}</span>
                                            </button>
                                        );
                                    })}
                                    {editManualMembers.length === 0 && <div className="py-6 text-center text-sm text-slate-400">No hay personas para este filtro</div>}
                                </div>
                            </div>
                        )}
                        {editingEvent.status === 'CANCELLED' && (
                            <div className="animate-in fade-in slide-in-from-top-2 space-y-1.5">
                                <label className="text-[10px] font-black uppercase tracking-widest text-red-400">Razón de Cancelación *</label>
                                <textarea value={editingEvent.cancellation_reason || ''} onChange={e => setEditingEvent({...editingEvent, cancellation_reason: e.target.value})} rows={3} placeholder="¿Por qué no se realizó este evento?" className="w-full px-4 py-1.5 rounded-2xl border border-red-200 dark:border-white/10 bg-red-50 dark:bg-black/20 focus:ring-2 focus:ring-red-500/20 outline-none font-bold text-sm text-red-900 dark:text-red-200 resize-none placeholder:text-red-300 dark:placeholder:text-red-700" />
                            </div>
                        )}
                        <div className="space-y-1.5">
                            <label className="text-[10px] font-black uppercase tracking-widest text-slate-400">Descripción</label>
                            <textarea value={editingEvent.description || ''} onChange={e => setEditingEvent({...editingEvent, description: e.target.value})} rows={3} className="w-full px-4 py-1.5 rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-black/20 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm text-slate-800 dark:text-white resize-none" />
                        </div>
                        <div className="space-y-1.5">
                            <label className="text-[10px] font-black uppercase tracking-widest text-slate-400">Ubicación</label>
                            <input type="text" value={editingEvent.location || ''} onChange={e => setEditingEvent({...editingEvent, location: e.target.value})} className="w-full px-4 py-1.5 rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-black/20 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm text-slate-800 dark:text-white" />
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-1.5">
                                <label className="text-[10px] font-black uppercase tracking-widest text-slate-400">Hora de Inicio</label>
                                <input type="time" value={editingEvent.start_time || ''} onChange={e => setEditingEvent({...editingEvent, start_time: e.target.value})} className="w-full px-4 py-1.5 rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-black/20 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm text-slate-800 dark:text-white" />
                            </div>
                            <div className="space-y-1.5">
                                <label className="text-[10px] font-black uppercase tracking-widest text-slate-400">Hora de Finalización</label>
                                <input type="time" value={editingEvent.end_time || ''} onChange={e => setEditingEvent({...editingEvent, end_time: e.target.value})} className="w-full px-4 py-1.5 rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-black/20 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm text-slate-800 dark:text-white" />
                            </div>
                        </div>
                    </div>
                )}
            </WorkspaceDrawer>
        </EvangelismShell>
    );
}
