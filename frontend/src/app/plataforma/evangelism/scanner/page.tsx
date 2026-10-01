'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  QrCode,
  RefreshCcw,
  UserCheck,
  Users,
  Camera,
  Barcode,
  Volume2,
  VolumeX,
  AlertTriangle,
  AlertCircle,
  Calendar,
  CheckCircle2,
  Lock,
  ChevronDown,
  Eye,
  CloudOff,
  CloudUpload,
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch, ApiError } from '@/lib/http';
import { toast } from 'sonner';
import EvangelismShell from '@/components/evangelism/EvangelismShell';
import AdminHero from '@/components/admin/AdminHero';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';
import type { MinistryEvent } from '@/app/plataforma/evangelism/types';
import { participantRoleLabel } from '@/app/plataforma/evangelism/types';
import {
  enqueueOfflineCheckin,
  getPendingCheckins,
  syncOfflineQueue,
  type StoredCheckin,
} from './offlineQueue';

// =============================================================================
// WEB AUDIO API FEEDBACK SYNTHESIZER
// =============================================================================

let audioContextInstance: AudioContext | null = null;

function getAudioContext(): AudioContext | null {
  if (typeof window === 'undefined') return null;
  const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
  if (!AudioCtx) return null;
  if (!audioContextInstance) {
    audioContextInstance = new AudioCtx();
  }
  if (audioContextInstance.state === 'suspended') {
    audioContextInstance.resume();
  }
  return audioContextInstance;
}

function playAuthorizedSound(): void {
  const ctx = getAudioContext();
  if (!ctx) return;
  const now = ctx.currentTime;

  // Tono 1: Re5 (587.33 Hz)
  const osc1 = ctx.createOscillator();
  const gain1 = ctx.createGain();
  osc1.type = 'sine';
  osc1.frequency.setValueAtTime(587.33, now);
  gain1.gain.setValueAtTime(0.2, now);
  gain1.gain.exponentialRampToValueAtTime(0.001, now + 0.15);
  osc1.connect(gain1);
  gain1.connect(ctx.destination);
  osc1.start(now);
  osc1.stop(now + 0.15);

  // Tono 2: La5 (880.00 Hz) con armónico brillante
  const osc2 = ctx.createOscillator();
  const gain2 = ctx.createGain();
  osc2.type = 'sine';
  osc2.frequency.setValueAtTime(880.0, now + 0.1);
  gain2.gain.setValueAtTime(0.25, now + 0.1);
  gain2.gain.exponentialRampToValueAtTime(0.001, now + 0.35);
  osc2.connect(gain2);
  gain2.connect(ctx.destination);
  osc2.start(now + 0.1);
  osc2.stop(now + 0.35);
}

function playDuplicateAlarmSound(): void {
  const ctx = getAudioContext();
  if (!ctx) return;
  const now = ctx.currentTime;

  // Alarma de sirena / buzzer urgente: 3 pulsos disonantes en diente de sierra
  for (let i = 0; i < 3; i++) {
    const pulseStart = now + i * 0.16;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = 'sawtooth';
    osc.frequency.setValueAtTime(190, pulseStart);
    osc.frequency.linearRampToValueAtTime(130, pulseStart + 0.12);
    gain.gain.setValueAtTime(0.4, pulseStart);
    gain.gain.exponentialRampToValueAtTime(0.01, pulseStart + 0.12);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start(pulseStart);
    osc.stop(pulseStart + 0.13);
  }
}

function playInvalidSound(): void {
  const ctx = getAudioContext();
  if (!ctx) return;
  const now = ctx.currentTime;

  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  osc.type = 'triangle';
  osc.frequency.setValueAtTime(320, now);
  osc.frequency.linearRampToValueAtTime(220, now + 0.25);
  gain.gain.setValueAtTime(0.25, now);
  gain.gain.exponentialRampToValueAtTime(0.001, now + 0.25);
  osc.connect(gain);
  gain.connect(ctx.destination);
  osc.start(now);
  osc.stop(now + 0.25);
}

// =============================================================================
// TIPOS Y MODELOS DEL GATEKEEPER
// =============================================================================

interface OccupancyData {
  event_id?: string;
  event_name?: string;
  session_date?: string;
  checked_in_count: number;
  capacity_max: number;
  percentage: number;
  is_full?: boolean;
}

interface ScanFeedbackState {
  type: 'authorized' | 'duplicate' | 'invalid' | 'offline';
  title: string;
  personaName?: string;
  registrationCode?: string;
  participantRoleCode?: string | null;
  roleAtEvent?: string | null;
  checkInAt?: string | null;
  firstCheckinAt?: string | null;
  checkedByName?: string | null;
  message?: string;
}

interface CheckinSuccessResponse {
  status: string;
  message: string;
  persona_id: string;
  persona_name: string;
  first_name?: string;
  last_name?: string;
  email?: string;
  phone?: string;
  registration_code?: string;
  registration_id?: string;
  participant_role_code?: string | null;
  role_at_event?: string | null;
  check_in_at?: string;
  checked_in_at?: string;
  checked_by_name?: string;
  occupancy?: {
    count: number;
    capacity_max: number;
    percentage: number;
  };
}

interface AttendeeListItem {
  persona_id: string;
  persona_name: string;
  role?: string;
  status?: string;
  check_in_at?: string | null;
}

import { sanitizeAndExtractQrToken } from './utils';

export default function GatekeeperScannerPage() {
  const { token: authToken } = useAuth();

  // Estados de eventos y aforo
  const [events, setEvents] = useState<MinistryEvent[]>([]);
  const [selectedEventId, setSelectedEventId] = useState<string>('');
  const [loadingEvents, setLoadingEvents] = useState<boolean>(true);

  // Cola offline (TKT-EVANGELISM-OFFLINE-SYNC-01)
  const [isOffline, setIsOffline] = useState<boolean>(false);
  const [pendingQueue, setPendingQueue] = useState<StoredCheckin[]>([]);
  const [isSyncing, setIsSyncing] = useState<boolean>(false);
  const [occupancy, setOccupancy] = useState<OccupancyData>({
    checked_in_count: 0,
    capacity_max: 0,
    percentage: 0,
  });

  // Modo dual: 'physical' (lector/input con auto-enfoque) | 'camera'
  const [scannerMode, setScannerMode] = useState<'physical' | 'camera'>('physical');
  const [soundEnabled, setSoundEnabled] = useState<boolean>(true);

  // Input y procesamiento
  const [barcodeInput, setBarcodeInput] = useState<string>('');
  const [processing, setProcessing] = useState<boolean>(false);
  const [scanFeedback, setScanFeedback] = useState<ScanFeedbackState | null>(null);

  // Cámara
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [, setCameraActive] = useState<boolean>(false);

  // Drawer de asistentes
  const [drawerOpen, setDrawerOpen] = useState<boolean>(false);
  const [attendeesList, setAttendeesList] = useState<AttendeeListItem[]>([]);
  const [loadingAttendees, setLoadingAttendees] = useState<boolean>(false);

  const inputRef = useRef<HTMLInputElement | null>(null);
  const feedbackTimerRef = useRef<NodeJS.Timeout | null>(null);

  // ── Auto-enfoque permanente para pistola lectora física ──────────────────
  const refocusInput = useCallback(() => {
    if (scannerMode === 'physical' && !drawerOpen && !scanFeedback) {
      inputRef.current?.focus();
    }
  }, [scannerMode, drawerOpen, scanFeedback]);

  useEffect(() => {
    refocusInput();
  }, [refocusInput, scanFeedback]);

  // Refocus en clic global o teclas
  useEffect(() => {
    const handleGlobalClick = () => {
      refocusInput();
    };
    window.addEventListener('click', handleGlobalClick);
    return () => window.removeEventListener('click', handleGlobalClick);
  }, [refocusInput]);

  // ── Cargar eventos activos al montar ─────────────────────────────────────
  useEffect(() => {
    async function loadEvents() {
      try {
        setLoadingEvents(true);
        const data = await apiFetch<MinistryEvent[]>('/evangelism/events/', {
          token: authToken,
          silent: true,
        });
        const activeList = Array.isArray(data) ? data : [];
        setEvents(activeList);
        if (activeList.length > 0) {
          setSelectedEventId(activeList[0].id);
        }
      } catch (err) {
        toast.error('Error al cargar la lista de eventos');
      } finally {
        setLoadingEvents(false);
      }
    }
    loadEvents();
  }, [authToken]);

  // ── Cargar y monitorear aforo en tiempo real ─────────────────────────────
  const fetchOccupancy = useCallback(
    async (eventId: string) => {
      if (!eventId) return;
      try {
        const todayUtc = new Date().toISOString().slice(0, 10);
        const data = await apiFetch<OccupancyData>(
          `/evangelism/events/${eventId}/sessions/${todayUtc}/occupancy`,
          { token: authToken, silent: true }
        );
        if (data) {
          setOccupancy(data);
        }
      } catch {
        // Fallback si la sesión de hoy aún no tiene registros
        const currentEvt = events.find((e) => e.id === eventId);
        if (currentEvt) {
          setOccupancy((prev) => ({
            ...prev,
            capacity_max: currentEvt.capacity_max || 0,
          }));
        }
      }
    },
    [authToken, events]
  );

  useEffect(() => {
    if (selectedEventId) {
      fetchOccupancy(selectedEventId);
      const interval = setInterval(() => {
        fetchOccupancy(selectedEventId);
      }, 10000);
      return () => clearInterval(interval);
    }
  }, [selectedEventId, fetchOccupancy]);

  // ── Offline: detectar conectividad y reflejar la cola persistida ───────────
  useEffect(() => {
    const updateOnlineStatus = () => {
      setIsOffline(!navigator.onLine);
    };
    updateOnlineStatus();
    window.addEventListener('online', updateOnlineStatus);
    window.addEventListener('offline', updateOnlineStatus);
    return () => {
      window.removeEventListener('online', updateOnlineStatus);
      window.removeEventListener('offline', updateOnlineStatus);
    };
  }, []);

  useEffect(() => {
    setPendingQueue(getPendingCheckins());
  }, []);

  const runOfflineSync = useCallback(async () => {
    if (isSyncing) return;
    if (getPendingCheckins().length === 0) {
      setPendingQueue([]);
      return;
    }
    setIsSyncing(true);
    try {
      const result = await syncOfflineQueue({ authToken });
      setPendingQueue(getPendingCheckins());
      if (result.attempted > 0) {
        if (result.networkError) {
          toast.error(
            `Sincronización interrumpida: ${result.remaining} check-ins siguen en cola`,
          );
        } else {
          toast.success(
            `Sincronización offline: ${result.synced} nuevos, ${result.duplicates} duplicados, ${result.errors} errores`,
          );
          fetchOccupancy(selectedEventId);
        }
      }
    } finally {
      setIsSyncing(false);
    }
  }, [authToken, fetchOccupancy, isSyncing, selectedEventId]);

  const runOfflineSyncRef = useRef(runOfflineSync);
  useEffect(() => {
    runOfflineSyncRef.current = runOfflineSync;
  });

  // Al recuperar conectividad, sincronizar en lote la cola pendiente.
  useEffect(() => {
    if (!isOffline) {
      void runOfflineSyncRef.current();
    }
  }, [isOffline]);

  // ── Manejo de cámara en modo 'camera' ─────────────────────────────────────
  useEffect(() => {
    let stream: MediaStream | null = null;
    let isCancelled = false;

    if (scannerMode === 'camera') {
      navigator.mediaDevices
        ?.getUserMedia({ video: { facingMode: 'environment' } })
        .then((s) => {
          if (isCancelled) {
            s.getTracks().forEach((track) => track.stop());
            return;
          }
          stream = s;
          if (videoRef.current) {
            videoRef.current.srcObject = s;
            videoRef.current.play().catch(() => {});
          }
          setCameraActive(true);
        })
        .catch(() => {
          setCameraActive(false);
          toast.info('No se detectó cámara física. Usando modo de entrada rápida.');
        });
    } else {
      setCameraActive(false);
    }

    return () => {
      isCancelled = true;
      if (stream) {
        stream.getTracks().forEach((track) => track.stop());
      }
    };
  }, [scannerMode]);

  // ── Procesar escaneo de credencial QR ─────────────────────────────────────
  const processScan = async (rawToken: string) => {
    const token = sanitizeAndExtractQrToken(rawToken);
    if (!token) return;

    if (feedbackTimerRef.current) {
      clearTimeout(feedbackTimerRef.current);
    }

    setProcessing(true);
    setBarcodeInput('');

    let targetEventId = selectedEventId;
    const todayUtc = new Date().toISOString().slice(0, 10);

    try {

      // Si el QR es de tipo CCF-EVT-, podemos extraer el eventId embebido
      if (token.startsWith('CCF-EVT-')) {
        const payloadStr = token.slice('CCF-EVT-'.length);
        if (payloadStr.length >= 36) {
          const parsedEventId = payloadStr.slice(0, 36);
          // Si el evento embebido está en la lista activa, lo priorizamos
          if (events.some((e) => e.id === parsedEventId)) {
            targetEventId = parsedEventId;
            if (targetEventId !== selectedEventId) {
              setSelectedEventId(targetEventId);
            }
          }
        }
      }

      if (!targetEventId) {
        throw new Error('Selecciona un evento activo antes de escanear.');
      }

      // Endpoint canonical de check-in con rol contextual y bloqueo anti-fraude
      const endpoint = token.startsWith('CCF-EVT-')
        ? `/evangelism/events/${targetEventId}/sessions/${todayUtc}/ccf-evt-checkin`
        : `/evangelism/events/${targetEventId}/sessions/${todayUtc}/checkin`;

      const response = await apiFetch<CheckinSuccessResponse>(endpoint, {
        method: 'POST',
        body: { qr_token: token },
        token: authToken,
        silent: true,
      });

      // ── AUTORIZADO (Verde) ────────────────────────────────────────────────
      if (soundEnabled) playAuthorizedSound();

      setScanFeedback({
        type: 'authorized',
        title: 'ACCESO AUTORIZADO',
        personaName: response.persona_name || 'Asistente',
        registrationCode: response.registration_code || undefined,
        participantRoleCode: response.participant_role_code,
        roleAtEvent: response.role_at_event,
        checkInAt: response.check_in_at || new Date().toISOString(),
        checkedByName: response.checked_by_name || 'Operador',
      });

      if (response.occupancy) {
        setOccupancy({
          checked_in_count: response.occupancy.count,
          capacity_max: response.occupancy.capacity_max,
          percentage: response.occupancy.percentage,
        });
      } else {
        fetchOccupancy(targetEventId);
      }

      // Auto-descarte suave para flujo rápido de puerta (2.8 segundos)
      feedbackTimerRef.current = setTimeout(() => {
        setScanFeedback(null);
        refocusInput();
      }, 2800);
    } catch (err: unknown) {
      const apiErr = err instanceof ApiError ? err : null;
      const detailObj = apiErr && typeof apiErr.detail === 'object' && apiErr.detail !== null ? (apiErr.detail as Record<string, unknown>) : null;

      // ── OFFLINE (Cola diferida, TKT-EVANGELISM-OFFLINE-SYNC-01) ───────────
      // Fallo de red real (status 0): encolar para sincronización diferida.
      // Los 4xx estructurales (QR inválido, duplicado, permisos) NO se encolan.
      if (apiErr && apiErr.status === 0 && targetEventId) {
        const enqueued = await enqueueOfflineCheckin({
          eventId: targetEventId,
          sessionDate: todayUtc,
          qrToken: token,
        });
        if (soundEnabled) playInvalidSound();
        setPendingQueue(getPendingCheckins());
        setScanFeedback({
          type: 'offline',
          title: enqueued.accepted ? 'SIN CONEXIÓN - CHECK-IN EN COLA' : 'SIN CONEXIÓN - YA ESTÁ EN COLA',
          message: enqueued.accepted
            ? 'El registro quedó guardado en este dispositivo y se sincronizará automáticamente al recuperar la conexión. La puerta no se detiene.'
            : 'Esta credencial ya estaba pendiente en la cola offline de este dispositivo.',
        });
        feedbackTimerRef.current = setTimeout(() => {
          setScanFeedback(null);
          refocusInput();
        }, 3500);
        return;
      }

      // ── DUPLICADO / DENEGADO (Rojo + Alarma Sonora) ──────────────────────
      const isDuplicate =
        (apiErr && apiErr.status === 409) &&
        (detailObj?.status === 'duplicate_access' ||
          String(detailObj?.message || '').toLowerCase().includes('duplicado') ||
          String(detailObj?.detail || '').toLowerCase().includes('duplicado'));

      if (isDuplicate) {
        if (soundEnabled) playDuplicateAlarmSound();

        const personaName = (detailObj?.persona_name as string) || 'Identidad Registrada';
        const regCode = (detailObj?.registration_code as string) || undefined;
        const firstCheckin = (detailObj?.first_checkin_at as string) || undefined;
        const checkedBy = (detailObj?.checked_by_name as string) || 'Operador previo';

        setScanFeedback({
          type: 'duplicate',
          title: 'ACCESO DUPLICADO - REINGRESO BLOQUEADO',
          personaName,
          registrationCode: regCode,
          firstCheckinAt: firstCheckin,
          checkedByName: checkedBy,
          message: 'Esta credencial ya fue escaneada previamente. Prevención de fraude activada.',
        });

        // La alarma roja permanece hasta que el operador haga clic o presione Enter (máx 8 seg)
        feedbackTimerRef.current = setTimeout(() => {
          setScanFeedback(null);
          refocusInput();
        }, 8000);
      } else {
        // ── INVÁLIDO (Amarillo) ──────────────────────────────────────────────
        if (soundEnabled) playInvalidSound();

        const errorMsg =
          (detailObj?.detail as string) ||
          (detailObj?.message as string) ||
          (err instanceof Error ? err.message : 'Código no reconocido o vencido.');

        setScanFeedback({
          type: 'invalid',
          title: 'CÓDIGO NO VÁLIDO',
          message: String(errorMsg),
        });

        feedbackTimerRef.current = setTimeout(() => {
          setScanFeedback(null);
          refocusInput();
        }, 3500);
      }
    } finally {
      setProcessing(false);
    }
  };

  const dismissFeedback = useCallback(() => {
    if (feedbackTimerRef.current) {
      clearTimeout(feedbackTimerRef.current);
    }
    setScanFeedback(null);
    refocusInput();
  }, [refocusInput]);

  // ── Teclas rápidas globales (Enter / Escape / Barra espaciadora) ───────────
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (scanFeedback) {
        if (e.key === 'Enter' || e.key === ' ' || e.key === 'Escape') {
          e.preventDefault();
          dismissFeedback();
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [scanFeedback, dismissFeedback]);

  // ── Cargar lista de asistentes para el Drawer ─────────────────────────────
  const openAttendeesDrawer = async () => {
    setDrawerOpen(true);
    if (!selectedEventId) return;
    try {
      setLoadingAttendees(true);
      const data = await apiFetch<{
        counts?: Record<string, number>;
        total?: number;
        present?: AttendeeListItem[];
      }>(`/evangelism/events/${selectedEventId}/attendance`, {
        token: authToken,
        silent: true,
      });
      setAttendeesList(data.present || []);
    } catch {
      toast.error('No se pudo cargar la lista de asistentes');
    } finally {
      setLoadingAttendees(false);
    }
  };

  const selectedEvent = events.find((e) => e.id === selectedEventId);

  // Determinación de color de aforo
  const capacityPct = occupancy.capacity_max > 0 ? occupancy.percentage : 0;
  const aforoBarColor =
    capacityPct >= 95
      ? 'bg-[hsl(var(--destructive))]'
      : capacityPct >= 80
      ? 'bg-[hsl(var(--warning))]'
      : 'bg-[hsl(var(--success))]';

  return (
    <EvangelismShell
      breadcrumbs={[
        { label: 'CCF', icon: Users },
        { label: 'Evangelismo', icon: Users },
        { label: 'Control de Acceso Gatekeeper', icon: QrCode },
      ]}
      rightActions={
        <div className="flex items-center gap-2">
          <button
            onClick={() => setSoundEnabled((prev) => !prev)}
            title={soundEnabled ? 'Sonido Activado' : 'Sonido Silenciado'}
            className="p-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] text-[hsl(var(--foreground))] hover:bg-[hsl(var(--surface-3))] transition-colors"
          >
            {soundEnabled ? <Volume2 size={16} className="text-[hsl(var(--success))]" /> : <VolumeX size={16} className="text-[hsl(var(--muted-foreground))]" />}
          </button>
          <button
            onClick={openAttendeesDrawer}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] text-[hsl(var(--foreground))] hover:bg-[hsl(var(--surface-3))] text-xs font-semibold transition-colors"
          >
            <Eye size={14} />
            <span>Ver Asistentes ({occupancy.checked_in_count})</span>
          </button>
        </div>
      }
    >
      <AdminHero
        eyebrow="Puerta & Seguridad Ministerial"
        title="Gatekeeper: Scanner y Control de Aforo"
        description="Fase 2 Super-PRO: Validación con blindaje anti-fraude duplicate_access, monitor de aforo en vivo y lector físico de alta velocidad."
        tags={['Anti-Fraude', 'Aforo en Vivo', 'Alta Velocidad', 'Web Audio']}
        watchers={['Optimus Brain', 'Seguridad Faro']}
      />

      <div className="w-full max-w-5xl mx-auto px-4 py-6 space-y-6">
        {/* BANNER: Check-ins pendientes en cola (offline → sync batch) */}
        {pendingQueue.length > 0 && (
          <div className="flex items-center justify-between gap-3 rounded-xl border border-[hsl(var(--warning))]/40 bg-[hsl(var(--warning))]/10 px-4 py-3">
            <div className="flex items-center gap-2">
              <CloudOff size={16} className="text-[hsl(var(--warning))]" />
              <div>
                <p className="text-xs font-bold uppercase tracking-wider text-[hsl(var(--warning))]">
                  Check-ins pendientes en cola ({pendingQueue.length})
                </p>
                <p className="text-2xs text-[hsl(var(--muted-foreground))]">
                  {isOffline
                    ? 'Se sincronizarán automáticamente al recuperar la conexión.'
                    : 'Listos para sincronizar con el servidor.'}
                </p>
              </div>
            </div>
            <button
              onClick={() => void runOfflineSync()}
              disabled={isSyncing || isOffline}
              className="inline-flex items-center gap-1.5 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] px-3 py-1.5 text-xs font-semibold text-[hsl(var(--foreground))] transition-colors hover:bg-[hsl(var(--surface-3))] disabled:opacity-50"
            >
              {isSyncing ? <RefreshCcw size={14} className="animate-spin" /> : <CloudUpload size={14} />}
              <span>{isSyncing ? 'Sincronizando...' : 'Sincronizar ahora'}</span>
            </button>
          </div>
        )}
        {/* ========================================================================= */}
        {/* PANEL SUPERIOR: SELECTOR DE EVENTO ACTIVO + MONITOR DE AFORO EN VIVO      */}
        {/* ========================================================================= */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Selector de Evento Activo */}
          <div className="md:col-span-2 bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] rounded-xl p-4 shadow-sm flex flex-col justify-between">
            <div className="space-y-1 mb-3">
              <div className="flex items-center justify-between">
                <span className="text-2xs font-semibold uppercase tracking-wider text-[hsl(var(--primary))] flex items-center gap-1.5">
                  <Calendar size={13} />
                  Evento Activo en Puerta
                </span>
                {selectedEvent?.requires_registration && (
                  <span className="px-2 py-0.5 rounded text-2xs font-bold uppercase tracking-wider bg-[hsl(var(--primary))]/10 text-[hsl(var(--primary))] border border-[hsl(var(--primary))]/20">
                    Pre-Registro Obligatorio
                  </span>
                )}
              </div>
              <h2 className="text-base font-bold text-[hsl(var(--foreground))]">
                {selectedEvent?.name || 'Selecciona un evento'}
              </h2>
              {selectedEvent?.location && (
                <p className="text-xs text-[hsl(var(--muted-foreground))]">
                  Ubicación: {selectedEvent.location}
                </p>
              )}
            </div>

            <div className="relative">
              <select
                aria-label="Seleccionar evento activo"
                value={selectedEventId}
                onChange={(e) => setSelectedEventId(e.target.value)}
                disabled={loadingEvents}
                className="w-full appearance-none bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded-lg px-3 py-2 text-sm text-[hsl(var(--foreground))] font-medium focus:outline-none focus:border-[hsl(var(--primary))] transition-all pr-8"
              >
                {loadingEvents ? (
                  <option value="">Cargando eventos...</option>
                ) : events.length === 0 ? (
                  <option value="">No hay eventos activos disponibles</option>
                ) : (
                  events.map((evt) => (
                    <option key={evt.id} value={evt.id}>
                      {evt.name} — {evt.event_date ? new Date(evt.event_date).toLocaleDateString() : 'Sin fecha'} (Aforo: {evt.capacity_max || 'Ilimitado'})
                    </option>
                  ))
                )}
              </select>
              <ChevronDown
                size={16}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-[hsl(var(--muted-foreground))] pointer-events-none"
              />
            </div>
          </div>

          {/* Monitor de Aforo en Vivo */}
          <div className="bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] rounded-xl p-4 shadow-sm flex flex-col justify-between">
            <div className="flex items-center justify-between">
              <span className="text-2xs font-semibold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
                Monitor de Aforo
              </span>
              <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-[hsl(var(--success))]/10 border border-[hsl(var(--success))]/20">
                <span className="size-2 rounded-full bg-[hsl(var(--success))] animate-pulse"></span>
                <span className="text-2xs font-bold text-[hsl(var(--success))] uppercase tracking-wider">
                  En Vivo
                </span>
              </div>
            </div>

            <div className="my-2">
              <div className="flex items-baseline justify-between">
                <div className="text-2xl font-black tracking-tight text-[hsl(var(--foreground))]">
                  {occupancy.checked_in_count}
                  {occupancy.capacity_max > 0 && (
                    <span className="text-sm font-normal text-[hsl(var(--muted-foreground))] ml-1">
                      / {occupancy.capacity_max}
                    </span>
                  )}
                </div>
                <div className="text-sm font-bold text-[hsl(var(--foreground))]">
                  {occupancy.capacity_max > 0 ? `${occupancy.percentage}%` : 'Sin Límite'}
                </div>
              </div>

              {/* Barra de progreso de capacidad */}
              {occupancy.capacity_max > 0 && (
                <div className="w-full h-2 rounded-full bg-[hsl(var(--surface-2))] overflow-hidden mt-2">
                  <div
                    className={`h-full transition-all duration-500 rounded-full ${aforoBarColor}`}
                    style={{ width: `${Math.min(100, occupancy.percentage)}%` }}
                  ></div>
                </div>
              )}
            </div>

            <p className="text-2xs text-[hsl(var(--muted-foreground))]">
              {capacityPct >= 95
                ? '⚠️ Aforo máximo casi alcanzado o completo.'
                : 'Acceso fluido y controlado por Gatekeeper.'}
            </p>
          </div>
        </div>

        {/* ========================================================================= */}
        {/* SELECTOR DE MODO DUAL: LECTOR FÍSICO VS CÁMARA                            */}
        {/* ========================================================================= */}
        <div className="flex items-center justify-center gap-2">
          <button
            onClick={() => setScannerMode('physical')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
              scannerMode === 'physical'
                ? 'bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] shadow-md'
                : 'bg-[hsl(var(--surface-2))] text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))] border border-[hsl(var(--border))]'
            }`}
          >
            <Barcode size={16} />
            <span>Lector Físico / Pistola USB (Auto-enfoque)</span>
          </button>
          <button
            onClick={() => setScannerMode('camera')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
              scannerMode === 'camera'
                ? 'bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] shadow-md'
                : 'bg-[hsl(var(--surface-2))] text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))] border border-[hsl(var(--border))]'
            }`}
          >
            <Camera size={16} />
            <span>Cámara en Vivo</span>
          </button>
        </div>

        {/* ========================================================================= */}
        {/* ÁREA PRINCIPAL DE ESCANEO                                                 */}
        {/* ========================================================================= */}
        <div className="relative bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] rounded-2xl p-6 shadow-xl flex flex-col items-center justify-center overflow-hidden">
          {/* Estado de Cámara */}
          {scannerMode === 'camera' ? (
            <div className="relative w-full max-w-md aspect-square rounded-xl overflow-hidden border-2 border-dashed border-[hsl(var(--primary))]/40 bg-[hsl(var(--surface-3))] flex items-center justify-center">
              <video
                ref={videoRef}
                className="w-full h-full object-cover"
                playsInline
                autoPlay
                muted
              />
              <div className="absolute inset-0 pointer-events-none flex flex-col items-center justify-center">
                {/* Mirilla de escáner */}
                <div className="w-56 h-56 border-2 border-[hsl(var(--primary))] rounded-2xl relative shadow-[0_0_20px_hsl(var(--primary)/0.4)]">
                  <div className="absolute top-0 inset-x-0 h-0.5 bg-[hsl(var(--primary))] shadow-[0_0_10px_hsl(var(--primary))] animate-scan"></div>
                </div>
                <span className="text-2xs font-semibold uppercase tracking-wider text-[hsl(var(--foreground))] bg-[hsl(var(--surface-1))]/90 border border-[hsl(var(--border))] px-3 py-1 rounded-full mt-4 shadow">
                  Apunta al código QR del pase
                </span>
              </div>
            </div>
          ) : (
            /* Modo Lector Físico / Pistola */
            <div className="w-full max-w-md space-y-4 text-center py-4">
              <div className="size-20 mx-auto rounded-full bg-[hsl(var(--primary))]/10 text-[hsl(var(--primary))] flex items-center justify-center border border-[hsl(var(--primary))]/20 shadow-inner">
                <Barcode size={40} className="animate-pulse" />
              </div>

              <div>
                <h3 className="text-base font-bold text-[hsl(var(--foreground))]">
                  Lector Físico Activo
                </h3>
                <p className="text-xs text-[hsl(var(--muted-foreground))] mt-1">
                  Apunta la pistola escáner al código QR o carnet digital. El sistema procesa y bloquea duplicados en milisegundos.
                </p>
              </div>

              <div className="relative pt-2">
                <input
                  ref={inputRef}
                  type="text"
                  aria-label="Código QR escaneado"
                  placeholder="Escaneando... (esperando lectura de código)"
                  value={barcodeInput}
                  disabled={processing}
                  onChange={(e) => setBarcodeInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      processScan(barcodeInput);
                    }
                  }}
                  className="w-full bg-[hsl(var(--surface-2))] border-2 border-[hsl(var(--primary))] rounded-xl px-4 py-3 text-center text-sm font-mono text-[hsl(var(--foreground))] placeholder:text-[hsl(var(--muted-foreground))] focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]/40 shadow-inner transition-all"
                />
              </div>

              <button
                onClick={() => processScan(barcodeInput)}
                disabled={!barcodeInput || processing}
                className="w-full py-2.5 rounded-lg bg-[hsl(var(--primary))] hover:opacity-90 disabled:opacity-50 text-[hsl(var(--primary-foreground))] font-semibold text-xs uppercase tracking-wider flex items-center justify-center gap-2 transition-all shadow-md"
              >
                {processing ? <RefreshCcw size={15} className="animate-spin" /> : <UserCheck size={15} />}
                <span>Validar Ingreso</span>
              </button>
            </div>
          )}

          {/* Footer de estado del sistema */}
          <div className="mt-4 flex items-center gap-4 text-2xs text-[hsl(var(--muted-foreground))] border-t border-[hsl(var(--border))] pt-3 w-full justify-between">
            <span className="flex items-center gap-1.5">
              {isOffline ? (
                <>
                  <CloudOff size={12} className="text-[hsl(var(--warning))]" />
                  <span className="font-semibold uppercase text-[hsl(var(--warning))]">Sin conexión — encolando</span>
                </>
              ) : (
                <>
                  <span className="size-2 rounded-full bg-[hsl(var(--success))]"></span>
                  Gatekeeper 2.0 Operativo
                </>
              )}
            </span>
            <span className="font-mono">Invariante: Previene Fraude y Reingreso</span>
          </div>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* FEEDBACK VISUAL A PANTALLA COMPLETA                                       */}
      {/* (Verde: Autorizado | Rojo: Duplicado con Alarma | Amarillo: Inválido)     */}
      {/* ========================================================================= */}
      {scanFeedback && (
        <aside
          aria-label="Notificación de escaneo a pantalla completa"
          onClick={dismissFeedback}
          className={`fixed inset-0 z-50 flex flex-col justify-between p-6 md:p-12 backdrop-blur-xl animate-in fade-in duration-200 cursor-pointer ${
            scanFeedback.type === 'authorized'
              ? 'bg-[hsl(var(--surface-1))]/95 border-8 border-[hsl(var(--success))] shadow-[inset_0_0_100px_hsl(var(--success)/0.2)]'
              : scanFeedback.type === 'duplicate'
              ? 'bg-[hsl(var(--surface-1))]/95 border-8 border-[hsl(var(--destructive))] shadow-[inset_0_0_120px_hsl(var(--destructive)/0.3)]'
              : 'bg-[hsl(var(--surface-1))]/95 border-8 border-[hsl(var(--warning))] shadow-[inset_0_0_100px_hsl(var(--warning)/0.2)]'
          }`}
        >
          {/* Header Superior del Feedback a Pantalla Completa */}
          <div className="flex items-center justify-between border-b border-[hsl(var(--border))] pb-4">
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono font-bold uppercase tracking-wider text-[hsl(var(--primary))]">
                {selectedEvent?.name || 'Gatekeeper Scanner'}
              </span>
            </div>
            <div className="text-2xs font-mono uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
              Presiona [Enter] o clic en cualquier parte para continuar
            </div>
          </div>

          {/* Cuerpo Central del Feedback */}
          <div
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-2xl mx-auto text-center space-y-6 my-auto"
          >
            {/* Ícono de Estado */}
            <div className="flex justify-center">
              {scanFeedback.type === 'authorized' && (
                <div className="p-6 rounded-full bg-[hsl(var(--success))]/15 text-[hsl(var(--success))] shadow-lg">
                  <CheckCircle2 size={96} />
                </div>
              )}
              {scanFeedback.type === 'duplicate' && (
                <div className="p-6 rounded-full bg-[hsl(var(--destructive))]/20 text-[hsl(var(--destructive))] animate-bounce shadow-lg">
                  <AlertTriangle size={96} />
                </div>
              )}
              {scanFeedback.type === 'invalid' && (
                <div className="p-6 rounded-full bg-[hsl(var(--warning))]/15 text-[hsl(var(--warning))] shadow-lg">
                  <AlertCircle size={96} />
                </div>
              )}
              {scanFeedback.type === 'offline' && (
                <div className="p-6 rounded-full bg-[hsl(var(--warning))]/15 text-[hsl(var(--warning))] shadow-lg">
                  <CloudOff size={96} />
                </div>
              )}
            </div>

            {/* Título de Estado */}
            <div className="space-y-1">
              <h2
                className={`text-3xl md:text-4xl font-black uppercase tracking-tight ${
                  scanFeedback.type === 'authorized'
                    ? 'text-[hsl(var(--success))]'
                    : scanFeedback.type === 'duplicate'
                    ? 'text-[hsl(var(--destructive))]'
                    : 'text-[hsl(var(--warning))]'
                }`}
              >
                {scanFeedback.title}
              </h2>

              {scanFeedback.type === 'duplicate' && (
                <p className="text-sm font-bold text-[hsl(var(--destructive))] uppercase tracking-widest">
                  ⚠️ ALERTA DE SEGURIDAD: PREVENCIÓN DE FRAUDE
                </p>
              )}
            </div>

            {/* Datos de la Persona / Credencial */}
            {scanFeedback.personaName && (
              <div className="space-y-2 py-4 border-y border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]/50 rounded-2xl p-4">
                <p className="text-xs text-[hsl(var(--muted-foreground))] uppercase font-semibold">
                  Titular de la Credencial
                </p>
                <p className="text-2xl md:text-3xl font-bold text-[hsl(var(--foreground))]">
                  {scanFeedback.personaName}
                </p>

                <div className="flex items-center justify-center gap-3 pt-2 flex-wrap">
                  {scanFeedback.registrationCode && (
                    <span className="px-3 py-1 rounded-lg bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] font-mono text-sm font-bold text-[hsl(var(--foreground))] shadow-sm">
                      {scanFeedback.registrationCode}
                    </span>
                  )}
                  {scanFeedback.participantRoleCode && (
                    <span className="px-3 py-1 rounded-lg bg-[hsl(var(--primary))]/10 border border-[hsl(var(--primary))]/20 text-xs font-bold uppercase tracking-wider text-[hsl(var(--primary))]">
                      {participantRoleLabel(scanFeedback.participantRoleCode)}
                    </span>
                  )}
                </div>
              </div>
            )}

            {/* Detalle especial de bloqueo por duplicado */}
            {scanFeedback.type === 'duplicate' && (
              <div className="bg-[hsl(var(--destructive))]/10 border border-[hsl(var(--destructive))]/30 rounded-2xl p-5 text-left space-y-2 text-sm max-w-lg mx-auto">
                <div className="font-bold text-[hsl(var(--destructive))] flex items-center gap-2">
                  <Lock size={16} />
                  <span>Historial de Primer Ingreso Registrado:</span>
                </div>
                {scanFeedback.firstCheckinAt && (
                  <p className="text-[hsl(var(--foreground))]">
                    <span className="font-semibold">Hora de Entrada:</span>{' '}
                    {new Date(scanFeedback.firstCheckinAt).toLocaleTimeString()} ({new Date(scanFeedback.firstCheckinAt).toLocaleDateString()})
                  </p>
                )}
                {scanFeedback.checkedByName && (
                  <p className="text-[hsl(var(--foreground))]">
                    <span className="font-semibold">Registrado por:</span> {scanFeedback.checkedByName}
                  </p>
                )}
                <p className="text-xs text-[hsl(var(--muted-foreground))] pt-1 border-t border-[hsl(var(--destructive))]/20">
                  El reingreso con este mismo pase queda denegado para evitar el uso duplicado de entradas.
                </p>
              </div>
            )}

            {/* Mensaje de error general si aplica */}
            {scanFeedback.message && scanFeedback.type !== 'duplicate' && (
              <p className="text-base text-[hsl(var(--muted-foreground))] max-w-md mx-auto">
                {scanFeedback.message}
              </p>
            )}
          </div>

          {/* Footer Inferior del Feedback */}
          <div className="w-full max-w-lg mx-auto pt-4">
            <button
              onClick={dismissFeedback}
              className={`w-full py-3.5 rounded-xl font-bold uppercase tracking-wider text-xs transition-all flex items-center justify-center gap-2 shadow-lg ${
                scanFeedback.type === 'authorized'
                  ? 'bg-[hsl(var(--success))] text-[hsl(var(--success-foreground))] hover:opacity-90'
                  : scanFeedback.type === 'duplicate'
                  ? 'bg-[hsl(var(--destructive))] text-[hsl(var(--destructive-foreground))] hover:opacity-90'
                  : 'bg-[hsl(var(--warning))] text-[hsl(var(--warning-foreground))] hover:opacity-90'
              }`}
            >
              <span>Continuar / Siguiente (Enter)</span>
            </button>
          </div>
        </aside>
      )}

      {/* ========================================================================= */}
      {/* DRAWER LATERAL: LISTA DE ASISTENTES (0 MODALES CENTRADOS)                 */}
      {/* ========================================================================= */}
      <WorkspaceDrawer
        isOpen={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        title="Control de Ingresos"
        subtitle={`Asistentes registrados en ${selectedEvent?.name || 'el evento'}`}
      >
        <div className="p-4 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-[hsl(var(--border))]">
            <span className="text-xs font-semibold text-[hsl(var(--muted-foreground))]">
              Total presentes hoy: {occupancy.checked_in_count}
            </span>
            <button
              onClick={openAttendeesDrawer}
              className="text-xs text-[hsl(var(--primary))] hover:underline flex items-center gap-1"
            >
              <RefreshCcw size={12} /> Actualizar
            </button>
          </div>

          {loadingAttendees ? (
            <div className="py-12 text-center text-xs text-[hsl(var(--muted-foreground))]">
              Cargando lista de asistentes...
            </div>
          ) : attendeesList.length === 0 ? (
            <div className="py-12 text-center text-xs text-[hsl(var(--muted-foreground))]">
              Aún no hay ingresos registrados para este evento en el día de hoy.
            </div>
          ) : (
            <div className="divide-y divide-[hsl(var(--border))]">
              {attendeesList.map((att, idx) => (
                <div key={att.persona_id || idx} className="py-2.5 flex items-center justify-between">
                  <div>
                    <p className="text-sm font-semibold text-[hsl(var(--foreground))]">
                      {att.persona_name}
                    </p>
                    <p className="text-2xs text-[hsl(var(--muted-foreground))]">
                      {att.role || 'Participante'} • {att.check_in_at ? new Date(att.check_in_at).toLocaleTimeString() : 'Hora no disponible'}
                    </p>
                  </div>
                  <span className="px-2 py-0.5 rounded text-2xs font-bold uppercase bg-[hsl(var(--success))]/10 text-[hsl(var(--success))] border border-[hsl(var(--success))]/20">
                    Presente
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </WorkspaceDrawer>
    </EvangelismShell>
  );
}
