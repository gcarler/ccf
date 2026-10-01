"use client";

import React, { useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  Layers,
  Mail,
  MapPin,
  MessageSquare,
  Phone,
  RefreshCw,
  Send,
  Sparkles,
  UserCheck,
  UserPlus,
  Users,
  UserX,
} from "lucide-react";
import { apiFetch } from "@/lib/http";
import WorkspaceDrawer from "@/components/WorkspaceDrawer";
import type {
  AutoAssignMentorsResponse,
  AvailableMentorItem,
  FollowupAttendeeItem,
  FollowupOverviewData,
  ManualAssignMentorPayload,
  RecordResponsePayload,
  TriggerStepPayload,
} from "@/app/plataforma/evangelism/types";

interface FollowupTabProps {
  eventId: string;
  token: string | null;
  eventName: string;
}

export default function FollowupTab({ eventId, token, eventName: _eventName }: FollowupTabProps) {
  const [overview, setOverview] = useState<FollowupOverviewData | null>(null);
  const [attendees, setAttendees] = useState<FollowupAttendeeItem[]>([]);
  const [mentors, setMentors] = useState<AvailableMentorItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [feedbackMessage, setFeedbackMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Filtros
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [stepFilter, setStepFilter] = useState<string>("ALL");
  const [mentorFilter, setMentorFilter] = useState<string>("ALL");

  // Drawers (0 modales centrados)
  const [selectedAttendeeForMentor, setSelectedAttendeeForMentor] = useState<FollowupAttendeeItem | null>(null);
  const [selectedAttendeeForSequence, setSelectedAttendeeForSequence] = useState<FollowupAttendeeItem | null>(null);

  // Form states for Drawers
  const [selectedMentorId, setSelectedMentorId] = useState<string>("");
  const [mentorNotes, setMentorNotes] = useState<string>("");
  const [responseNotes, setResponseNotes] = useState<string>("");
  const [responseChannel, setResponseChannel] = useState<string>("WHATSAPP");

  const loadData = async () => {
    if (!token) return;
    setLoading(true);
    try {
      const [overviewData, attendeesData, mentorsData] = await Promise.all([
        apiFetch<FollowupOverviewData>(`/evangelism/events/${eventId}/followup/overview`, { token, silent: true }),
        apiFetch<FollowupAttendeeItem[]>(`/evangelism/events/${eventId}/followup/attendees`, { token, silent: true }),
        apiFetch<AvailableMentorItem[]>(`/evangelism/events/${eventId}/followup/available-mentors`, { token, silent: true }),
      ]);
      setOverview(overviewData);
      setAttendees(attendeesData);
      setMentors(mentorsData);
    } catch (err: any) {
      setFeedbackMessage({
        type: "error",
        text: err?.message || "Error al cargar la información de seguimiento post-evento.",
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    // Carga inicial por evento; loadData se define estable y se invoca al montar/cambiar evento.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [eventId, token]);

  // Ejecución masiva de asignación inteligente con balanceo de carga
  const handleAutoAssign = async () => {
    if (!token) return;
    setActionLoading(true);
    setFeedbackMessage(null);
    try {
      const res = await apiFetch<AutoAssignMentorsResponse>(
        `/evangelism/events/${eventId}/followup/auto-assign-mentors`,
        {
          method: "POST",
          token,
          silent: true,
        }
      );
      setFeedbackMessage({ type: "success", text: res.message });
      await loadData();
    } catch (err: any) {
      setFeedbackMessage({
        type: "error",
        text: err?.message || "No se pudo realizar la asignación automática de mentores.",
      });
    } finally {
      setActionLoading(false);
    }
  };

  // Disparo manual de paso (cadencia)
  const handleTriggerStep = async (stepNumber: number, personaId?: string, force = false) => {
    if (!token) return;
    setActionLoading(true);
    setFeedbackMessage(null);
    try {
      const payload: TriggerStepPayload = {
        step_number: stepNumber,
        persona_ids: personaId ? [personaId] : undefined,
        force,
      };
      const res = await apiFetch<{ success: boolean; dispatched_count: number; message: string }>(
        `/evangelism/events/${eventId}/followup/trigger-step`,
        {
          method: "POST",
          token,
          body: payload,
          silent: true,
        }
      );
      setFeedbackMessage({ type: "success", text: res.message });
      await loadData();
      if (selectedAttendeeForSequence && personaId) {
        // refrescar asistente en drawer
        const updated = await apiFetch<FollowupAttendeeItem[]>(
          `/evangelism/events/${eventId}/followup/attendees?search=${encodeURIComponent(selectedAttendeeForSequence.full_name)}`,
          { token, silent: true }
        );
        const match = updated.find((a) => a.persona_id === personaId);
        if (match) setSelectedAttendeeForSequence(match);
      }
    } catch (err: any) {
      setFeedbackMessage({
        type: "error",
        text: err?.message || "Error al disparar el despacho de seguimiento.",
      });
    } finally {
      setActionLoading(false);
    }
  };

  // Asignar mentor manualmente
  const handleSaveManualMentor = async () => {
    if (!token || !selectedAttendeeForMentor || !selectedMentorId) return;
    setActionLoading(true);
    try {
      const chosenMentor = mentors.find((m) => m.mentor_id === selectedMentorId);
      const payload: ManualAssignMentorPayload = {
        persona_id: selectedAttendeeForMentor.persona_id,
        mentor_persona_id: selectedMentorId,
        suggested_group_id: chosenMentor?.group_id,
        notes: mentorNotes.trim() || undefined,
      };
      const res = await apiFetch<{ success: boolean; message: string }>(
        `/evangelism/events/${eventId}/followup/assign-mentor`,
        {
          method: "PUT",
          token,
          body: payload,
          silent: true,
        }
      );
      setFeedbackMessage({ type: "success", text: res.message });
      setSelectedAttendeeForMentor(null);
      setSelectedMentorId("");
      setMentorNotes("");
      await loadData();
    } catch (err: any) {
      setFeedbackMessage({
        type: "error",
        text: err?.message || "Error al asignar mentor.",
      });
    } finally {
      setActionLoading(false);
    }
  };

  // Registrar respuesta del asistente
  const handleSaveResponse = async () => {
    if (!token || !selectedAttendeeForSequence || !responseNotes.trim()) return;
    setActionLoading(true);
    try {
      const payload: RecordResponsePayload = {
        persona_id: selectedAttendeeForSequence.persona_id,
        notes: responseNotes.trim(),
        channel: responseChannel,
      };
      const res = await apiFetch<{ success: boolean; message: string }>(
        `/evangelism/events/${eventId}/followup/record-response`,
        {
          method: "POST",
          token,
          body: payload,
          silent: true,
        }
      );
      setFeedbackMessage({ type: "success", text: res.message });
      setResponseNotes("");
      setSelectedAttendeeForSequence(null);
      await loadData();
    } catch (err: any) {
      setFeedbackMessage({
        type: "error",
        text: err?.message || "Error al registrar respuesta del asistente.",
      });
    } finally {
      setActionLoading(false);
    }
  };

  // Filtrado de asistentes en memoria
  const filteredAttendees = useMemo(() => {
    return attendees.filter((a) => {
      if (statusFilter !== "ALL" && a.status !== statusFilter) return false;
      if (stepFilter !== "ALL" && a.current_step !== Number(stepFilter)) return false;
      if (mentorFilter === "ASSIGNED" && !a.mentor_persona_id) return false;
      if (mentorFilter === "UNASSIGNED" && a.mentor_persona_id) return false;
      if (search) {
        const q = search.toLowerCase();
        const matchesName = a.full_name.toLowerCase().includes(q);
        const matchesEmail = (a.email || "").toLowerCase().includes(q);
        const matchesPhone = (a.phone || "").toLowerCase().includes(q);
        const matchesMentor = (a.mentor_name || "").toLowerCase().includes(q);
        const matchesGroup = (a.suggested_group_name || "").toLowerCase().includes(q);
        if (!matchesName && !matchesEmail && !matchesPhone && !matchesMentor && !matchesGroup) {
          return false;
        }
      }
      return true;
    });
  }, [attendees, statusFilter, stepFilter, mentorFilter, search]);

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="flex items-center gap-3 text-sm text-[hsl(var(--text-secondary))]">
          <RefreshCw className="h-5 w-5 animate-spin text-[hsl(var(--primary))]" />
          <span>Cargando campaña de seguimiento post-evento...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Notificación Feedback */}
      {feedbackMessage && (
        <div
          className={`flex items-center justify-between rounded-lg border p-4 text-xs font-semibold ${
            feedbackMessage.type === "success"
              ? "border-[hsl(var(--success-border))] bg-[hsl(var(--success-muted))] text-[hsl(var(--success))]"
              : "border-[hsl(var(--destructive-border))] bg-[hsl(var(--destructive-muted))] text-[hsl(var(--destructive))]"
          }`}
        >
          <div className="flex items-center gap-2">
            {feedbackMessage.type === "success" ? (
              <CheckCircle2 className="h-4 w-4 shrink-0" />
            ) : (
              <AlertCircle className="h-4 w-4 shrink-0" />
            )}
            <span>{feedbackMessage.text}</span>
          </div>
          <button
            onClick={() => setFeedbackMessage(null)}
            className="text-xs uppercase hover:underline opacity-80"
          >
            Cerrar
          </button>
        </div>
      )}

      {/* 1. Header & Acciones Maestras */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-bold uppercase tracking-wide text-[hsl(var(--text-primary))]">
            Automatización de Seguimiento Post-Evento
          </h2>
          <p className="text-xs text-[hsl(var(--text-secondary))]">
            Cadencia automatizada multicanal (24h Agradecimiento, 72h Grupo de Vida, 7d Llamada Pastoral) y asignación inteligente de mentores.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={loadData}
            disabled={actionLoading}
            className="inline-flex items-center gap-1.5 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-secondary))] px-3 py-1.5 text-xs font-medium text-[hsl(var(--text-primary))] shadow-sm transition hover:bg-[hsl(var(--bg-muted))]"
            title="Refrescar métricas"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            <span>Refrescar</span>
          </button>
          <button
            onClick={handleAutoAssign}
            disabled={actionLoading}
            className="inline-flex items-center gap-2 rounded-lg bg-[hsl(var(--primary))] px-4 py-2 text-xs font-semibold text-[hsl(var(--primary-foreground))] shadow transition hover:opacity-90 disabled:opacity-50"
          >
            <Sparkles className="h-4 w-4" />
            <span>Asignación Inteligente (Zona y Carga)</span>
          </button>
        </div>
      </div>

      {/* 2. Tarjetas KPI Ejecutivas */}
      {overview && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {/* KPI 1: En Seguimiento */}
          <div className="rounded-xl border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-secondary))] p-4 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-2xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
                En Seguimiento
              </span>
              <Users className="h-4 w-4 text-[hsl(var(--info))]" />
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-2xl font-black text-[hsl(var(--text-primary))]">
                {overview.total_enrolled}
              </span>
              <span className="text-xs text-[hsl(var(--text-secondary))]">
                / {overview.total_checked_in} asistentes
              </span>
            </div>
            <div className="mt-2 flex items-center gap-2 text-2xs text-[hsl(var(--text-muted))]">
              <span className="inline-block h-2 w-2 rounded-full bg-[hsl(var(--success))]" />
              <span>{overview.active_in_sequence} activos en cadencia</span>
            </div>
          </div>

          {/* KPI 2: Tasa de Respuesta */}
          <div className="rounded-xl border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-secondary))] p-4 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-2xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
                Tasa de Respuesta
              </span>
              <MessageSquare className="h-4 w-4 text-[hsl(var(--success))]" />
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-2xl font-black text-[hsl(var(--text-primary))]">
                {overview.response_rate_percentage}%
              </span>
              <span className="text-xs text-[hsl(var(--text-secondary))]">
                ({overview.responses_received} respuestas)
              </span>
            </div>
            <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-[hsl(var(--bg-muted))]">
              <div
                className="h-full bg-[hsl(var(--success))]"
                style={{ width: `${Math.min(100, overview.response_rate_percentage)}%` }}
              />
            </div>
          </div>

          {/* KPI 3: Mentores Asignados */}
          <div className="rounded-xl border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-secondary))] p-4 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-2xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
                Mentores Asignados
              </span>
              <UserCheck className="h-4 w-4 text-[hsl(var(--primary))]" />
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-2xl font-black text-[hsl(var(--text-primary))]">
                {overview.mentors_assigned}
              </span>
              <span className="text-xs text-[hsl(var(--text-secondary))]">
                ({overview.mentors_unassigned} sin mentor)
              </span>
            </div>
            <div className="mt-2 text-2xs text-[hsl(var(--text-muted))]">
              {overview.total_enrolled > 0
                ? `${Math.round((overview.mentors_assigned / overview.total_enrolled) * 100)}% de cobertura pastoral`
                : "Sin personas registradas"}
            </div>
          </div>

          {/* KPI 4: Despacho Multicanal */}
          <div className="rounded-xl border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-secondary))] p-4 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-2xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
                Despacho Multicanal
              </span>
              <Send className="h-4 w-4 text-[hsl(var(--warning))]" />
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-2xl font-black text-[hsl(var(--text-primary))]">
                {overview.delivery_rate_percentage}%
              </span>
              <span className="text-xs text-[hsl(var(--text-secondary))]">
                efectividad
              </span>
            </div>
            <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-[hsl(var(--bg-muted))]">
              <div
                className="h-full bg-[hsl(var(--warning))]"
                style={{ width: `${Math.min(100, overview.delivery_rate_percentage)}%` }}
              />
            </div>
          </div>
        </div>
      )}

      {/* 3. Pipeline Interactivo de la Cadencia (24h, 72h, 7d) */}
      {overview && (
        <div className="rounded-xl border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-secondary))] p-5 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-[hsl(var(--text-primary))] flex items-center gap-2">
              <Clock className="h-4 w-4 text-[hsl(var(--primary))]" />
              Secuencia Automatizada por Etapas
            </h3>
            <span className="text-2xs text-[hsl(var(--text-secondary))]">
              Triggers automáticos calculados desde el check-in de cada persona
            </span>
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            {/* Paso 1 */}
            <div className="relative rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] p-4">
              <div className="flex items-center justify-between">
                <span className="inline-flex items-center gap-1 rounded-md bg-[hsl(var(--info-muted))] px-2 py-0.5 text-2xs font-bold text-[hsl(var(--info))]">
                  Paso 1 • 24 Horas
                </span>
                <span className="text-xs font-black text-[hsl(var(--text-primary))]">
                  {overview.steps_summary.step_1.sent_count} / {overview.total_enrolled}
                </span>
              </div>
              <h4 className="mt-2 text-sm font-semibold text-[hsl(var(--text-primary))]">
                {overview.steps_summary.step_1.name}
              </h4>
              <p className="mt-1 text-2xs text-[hsl(var(--text-secondary))]">
                Mensaje de bienvenida y agradecimiento por acompañarnos en el evento.
              </p>
              <div className="mt-3 flex items-center justify-between">
                <div className="h-1.5 w-24 overflow-hidden rounded-full bg-[hsl(var(--bg-muted))]">
                  <div
                    className="h-full bg-[hsl(var(--info))]"
                    style={{ width: `${overview.steps_summary.step_1.completion_percentage}%` }}
                  />
                </div>
                <button
                  onClick={() => handleTriggerStep(1)}
                  disabled={actionLoading}
                  className="inline-flex items-center gap-1 rounded bg-[hsl(var(--info-muted))] px-2 py-1 text-2xs font-semibold text-[hsl(var(--info))] hover:bg-[hsl(var(--info-muted))]/80 transition disabled:opacity-50"
                  title="Despachar mensajes pendientes del Paso 1"
                >
                  <Send className="h-3 w-3" />
                  <span>Despachar pendientes</span>
                </button>
              </div>
            </div>

            {/* Paso 2 */}
            <div className="relative rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] p-4">
              <div className="flex items-center justify-between">
                <span className="inline-flex items-center gap-1 rounded-md bg-[hsl(var(--warning-muted))] px-2 py-0.5 text-2xs font-bold text-[hsl(var(--warning))]">
                  Paso 2 • 72 Horas
                </span>
                <span className="text-xs font-black text-[hsl(var(--text-primary))]">
                  {overview.steps_summary.step_2.sent_count} / {overview.total_enrolled}
                </span>
              </div>
              <h4 className="mt-2 text-sm font-semibold text-[hsl(var(--text-primary))]">
                {overview.steps_summary.step_2.name}
              </h4>
              <p className="mt-1 text-2xs text-[hsl(var(--text-secondary))]">
                Invitación al Grupo de Vida más cercano según la zona y mentor asignado.
              </p>
              <div className="mt-3 flex items-center justify-between">
                <div className="h-1.5 w-24 overflow-hidden rounded-full bg-[hsl(var(--bg-muted))]">
                  <div
                    className="h-full bg-[hsl(var(--warning))]"
                    style={{ width: `${overview.steps_summary.step_2.completion_percentage}%` }}
                  />
                </div>
                <button
                  onClick={() => handleTriggerStep(2)}
                  disabled={actionLoading}
                  className="inline-flex items-center gap-1 rounded bg-[hsl(var(--warning-muted))] px-2 py-1 text-2xs font-semibold text-[hsl(var(--warning))] hover:bg-[hsl(var(--warning-muted))]/80 transition disabled:opacity-50"
                  title="Despachar mensajes pendientes del Paso 2"
                >
                  <Send className="h-3 w-3" />
                  <span>Despachar pendientes</span>
                </button>
              </div>
            </div>

            {/* Paso 3 */}
            <div className="relative rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] p-4">
              <div className="flex items-center justify-between">
                <span className="inline-flex items-center gap-1 rounded-md bg-[hsl(var(--success-muted))] px-2 py-0.5 text-2xs font-bold text-[hsl(var(--success))]">
                  Paso 3 • 7 Días
                </span>
                <span className="text-xs font-black text-[hsl(var(--text-primary))]">
                  {overview.steps_summary.step_3.sent_count} / {overview.total_enrolled}
                </span>
              </div>
              <h4 className="mt-2 text-sm font-semibold text-[hsl(var(--text-primary))]">
                {overview.steps_summary.step_3.name}
              </h4>
              <p className="mt-1 text-2xs text-[hsl(var(--text-secondary))]">
                Llamada de bendición pastoral, petición de oración y confirmación de asistencia.
              </p>
              <div className="mt-3 flex items-center justify-between">
                <div className="h-1.5 w-24 overflow-hidden rounded-full bg-[hsl(var(--bg-muted))]">
                  <div
                    className="h-full bg-[hsl(var(--success))]"
                    style={{ width: `${overview.steps_summary.step_3.completion_percentage}%` }}
                  />
                </div>
                <button
                  onClick={() => handleTriggerStep(3)}
                  disabled={actionLoading}
                  className="inline-flex items-center gap-1 rounded bg-[hsl(var(--success-muted))] px-2 py-1 text-2xs font-semibold text-[hsl(var(--success))] hover:bg-[hsl(var(--success-muted))]/80 transition disabled:opacity-50"
                  title="Despachar mensajes pendientes del Paso 3"
                >
                  <Send className="h-3 w-3" />
                  <span>Despachar pendientes</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 4. Barra de Filtros y Búsqueda */}
      <div className="flex flex-col gap-3 rounded-xl border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-secondary))] p-4 shadow-sm md:flex-row md:items-center md:justify-between">
        <div className="flex flex-1 flex-col gap-2 sm:flex-row sm:items-center">
          <input
            type="text"
            placeholder="Buscar por nombre, email, teléfono, mentor o grupo..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full sm:max-w-xs rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] px-3 py-1.5 text-xs text-[hsl(var(--text-primary))] placeholder-[hsl(var(--text-muted))] focus:border-[hsl(var(--primary))] focus:outline-none"
          />

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            aria-label="Filtro por estado"
            className="rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] px-2.5 py-1.5 text-xs text-[hsl(var(--text-primary))] focus:border-[hsl(var(--primary))] focus:outline-none"
          >
            <option value="ALL">Todos los Estados</option>
            <option value="ACTIVE">Activo en Cadencia</option>
            <option value="COMPLETED">Cadencia Completada</option>
            <option value="PAUSED">Pausado</option>
          </select>

          <select
            value={stepFilter}
            onChange={(e) => setStepFilter(e.target.value)}
            aria-label="Filtro por etapa"
            className="rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] px-2.5 py-1.5 text-xs text-[hsl(var(--text-primary))] focus:border-[hsl(var(--primary))] focus:outline-none"
          >
            <option value="ALL">Todas las Etapas</option>
            <option value="1">Paso 1 (24h Agradecimiento)</option>
            <option value="2">Paso 2 (72h Grupo de Vida)</option>
            <option value="3">Paso 3 (7d Llamada Pastoral)</option>
          </select>

          <select
            value={mentorFilter}
            onChange={(e) => setMentorFilter(e.target.value)}
            aria-label="Filtro por mentor"
            className="rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] px-2.5 py-1.5 text-xs text-[hsl(var(--text-primary))] focus:border-[hsl(var(--primary))] focus:outline-none"
          >
            <option value="ALL">Todos (Con y Sin Mentor)</option>
            <option value="ASSIGNED">Con Mentor Asignado</option>
            <option value="UNASSIGNED">Sin Mentor Asignado</option>
          </select>
        </div>

        <div className="text-2xs font-semibold text-[hsl(var(--text-secondary))]">
          Mostrando {filteredAttendees.length} de {attendees.length} asistentes
        </div>
      </div>

      {/* 5. Tabla de Asistentes en Seguimiento */}
      <div className="overflow-hidden rounded-xl border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-secondary))] shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] text-2xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
              <tr>
                <th className="px-4 py-3">Asistente</th>
                <th className="px-4 py-3">Código & Check-In</th>
                <th className="px-4 py-3">Etapa de Cadencia</th>
                <th className="px-4 py-3">Mentor & Grupo Asignado</th>
                <th className="px-4 py-3">Respuesta</th>
                <th className="px-4 py-3 text-right">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[hsl(var(--border-primary))] font-medium text-[hsl(var(--text-primary))]">
              {filteredAttendees.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-xs text-[hsl(var(--text-secondary))]">
                    No se encontraron asistentes con los filtros seleccionados.
                  </td>
                </tr>
              ) : (
                filteredAttendees.map((a) => (
                  <tr key={a.registration_id} className="transition hover:bg-[hsl(var(--bg-muted))]/40">
                    {/* Asistente */}
                    <td className="px-4 py-3">
                      <div className="font-bold text-[hsl(var(--text-primary))]">{a.full_name}</div>
                      <div className="flex items-center gap-3 text-2xs text-[hsl(var(--text-secondary))] mt-0.5">
                        {a.phone && (
                          <span className="flex items-center gap-1">
                            <Phone className="h-3 w-3" /> {a.phone}
                          </span>
                        )}
                        {a.email && (
                          <span className="flex items-center gap-1">
                            <Mail className="h-3 w-3" /> {a.email}
                          </span>
                        )}
                      </div>
                    </td>

                    {/* Código & Check-In */}
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className="font-mono text-2xs font-semibold text-[hsl(var(--text-primary))]">
                        {a.registration_code}
                      </span>
                      {a.check_in_at && (
                        <div className="text-2xs text-[hsl(var(--text-secondary))] mt-0.5">
                          {new Date(a.check_in_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                        </div>
                      )}
                    </td>

                    {/* Etapa de Cadencia */}
                    <td className="px-4 py-3 whitespace-nowrap">
                      <div className="flex items-center gap-1.5">
                        <span
                          className={`inline-flex items-center rounded-md px-2 py-0.5 text-2xs font-bold ${
                            a.current_step === 1
                              ? "bg-[hsl(var(--info-muted))] text-[hsl(var(--info))]"
                              : a.current_step === 2
                              ? "bg-[hsl(var(--warning-muted))] text-[hsl(var(--warning))]"
                              : "bg-[hsl(var(--success-muted))] text-[hsl(var(--success))]"
                          }`}
                        >
                          Paso {a.current_step} de 3
                        </span>
                        <span className="text-2xs text-[hsl(var(--text-secondary))]">
                          ({a.status})
                        </span>
                      </div>
                    </td>

                    {/* Mentor & Grupo Asignado */}
                    <td className="px-4 py-3">
                      {a.mentor_name ? (
                        <div>
                          <div className="flex items-center gap-1.5 font-semibold text-[hsl(var(--text-primary))]">
                            <span>{a.mentor_name}</span>
                            {a.matched_by_zone && (
                              <span
                                className="inline-flex items-center gap-0.5 rounded bg-[hsl(var(--success-muted))] px-1 py-0.2 text-3xs font-bold text-[hsl(var(--success))]"
                                title="Mentor asignado por coincidencia geográfica de zona"
                              >
                                <MapPin className="h-2.5 w-2.5" /> Zona
                              </span>
                            )}
                          </div>
                          {a.suggested_group_name && (
                            <div className="text-2xs text-[hsl(var(--text-secondary))]">
                              Grupo: {a.suggested_group_name} {a.suggested_group_zone ? `(${a.suggested_group_zone})` : ""}
                            </div>
                          )}
                        </div>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-2xs text-[hsl(var(--destructive))] font-semibold">
                          <UserX className="h-3 w-3" /> Sin mentor
                        </span>
                      )}
                    </td>

                    {/* Respuesta */}
                    <td className="px-4 py-3 whitespace-nowrap">
                      {a.response_received ? (
                        <span className="inline-flex items-center gap-1 rounded bg-[hsl(var(--success-muted))] px-2 py-0.5 text-2xs font-bold text-[hsl(var(--success))]">
                          <CheckCircle2 className="h-3 w-3" /> Recibida
                        </span>
                      ) : (
                        <span className="text-2xs text-[hsl(var(--text-muted))]">Pendiente</span>
                      )}
                    </td>

                    {/* Acciones */}
                    <td className="px-4 py-3 text-right whitespace-nowrap">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => {
                            setSelectedAttendeeForMentor(a);
                            setSelectedMentorId(a.mentor_persona_id || "");
                          }}
                          className="inline-flex items-center gap-1 rounded border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] px-2 py-1 text-2xs font-semibold text-[hsl(var(--text-primary))] hover:bg-[hsl(var(--bg-muted))] transition"
                          title="Asignar o reasignar mentor"
                        >
                          <UserPlus className="h-3 w-3" />
                          <span>Mentor</span>
                        </button>
                        <button
                          onClick={() => {
                            setSelectedAttendeeForSequence(a);
                            setResponseNotes(a.response_notes || "");
                          }}
                          className="inline-flex items-center gap-1 rounded bg-[hsl(var(--primary))] px-2.5 py-1 text-2xs font-semibold text-[hsl(var(--primary-foreground))] hover:opacity-90 transition"
                          title="Ver secuencia, forzar envío y registrar respuesta"
                        >
                          <Layers className="h-3 w-3" />
                          <span>Detalle</span>
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── DRAWER 1: ASIGNACIÓN MANUAL / REASIGNACIÓN DE MENTOR ── */}
      <WorkspaceDrawer
        isOpen={Boolean(selectedAttendeeForMentor)}
        onClose={() => {
          setSelectedAttendeeForMentor(null);
          setSelectedMentorId("");
          setMentorNotes("");
        }}
        title="Asignar Mentor y Grupo de Vida"
        subtitle={selectedAttendeeForMentor ? `Para: ${selectedAttendeeForMentor.full_name}` : undefined}
      >
        {selectedAttendeeForMentor && (
          <div className="space-y-5 p-4 text-xs">
            <div className="rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] p-3">
              <div className="font-bold text-[hsl(var(--text-primary))]">
                {selectedAttendeeForMentor.full_name}
              </div>
              <div className="text-2xs text-[hsl(var(--text-secondary))] mt-1">
                Inscripción: {selectedAttendeeForMentor.registration_code} • Check-in registrado
              </div>
              {selectedAttendeeForMentor.mentor_name && (
                <div className="mt-2 text-2xs font-semibold text-[hsl(var(--info))]">
                  Mentor actual: {selectedAttendeeForMentor.mentor_name}
                </div>
              )}
            </div>

            {/* Lista de Mentores Disponibles */}
            <div>
              <label className="block text-2xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-2">
                Selecciona un Mentor o Líder de Grupo (ordenado por menor carga):
              </label>
              <div className="max-h-72 space-y-2 overflow-y-auto pr-1">
                {mentors.length === 0 ? (
                  <p className="text-2xs text-[hsl(var(--text-secondary))]">
                    No se encontraron líderes de grupo en esta sede.
                  </p>
                ) : (
                  mentors.map((m) => {
                    const isSelected = selectedMentorId === m.mentor_id;
                    return (
                      <div
                        key={m.mentor_id}
                        onClick={() => setSelectedMentorId(m.mentor_id)}
                        className={`cursor-pointer rounded-lg border p-3 transition ${
                          isSelected
                            ? "border-[hsl(var(--primary))] bg-[hsl(var(--primary-muted))]"
                            : "border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] hover:border-[hsl(var(--border-secondary))]"
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <div className="font-bold text-[hsl(var(--text-primary))]">{m.name}</div>
                          <span className="inline-flex items-center gap-1 rounded bg-[hsl(var(--bg-muted))] px-1.5 py-0.5 text-3xs font-semibold text-[hsl(var(--text-secondary))]">
                            {m.active_mentees_count} asignados actualmente
                          </span>
                        </div>
                        {m.group_name && (
                          <div className="mt-1 flex items-center gap-1 text-2xs text-[hsl(var(--text-secondary))]">
                            <Users className="h-3 w-3" />
                            <span>Grupo: {m.group_name}</span>
                            {m.group_zone && <span className="opacity-70">• {m.group_zone}</span>}
                          </div>
                        )}
                      </div>
                    );
                  })
                )}
              </div>
            </div>

            {/* Notas opcionales */}
            <div>
              <label className="block text-2xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1">
                Notas de Asignación / Instrucciones para el Mentor:
              </label>
              <textarea
                rows={2}
                value={mentorNotes}
                onChange={(e) => setMentorNotes(e.target.value)}
                placeholder="Ej: Asignado por petición especial o cercanía al trabajo..."
                className="w-full rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] p-2.5 text-xs text-[hsl(var(--text-primary))] focus:border-[hsl(var(--primary))] focus:outline-none"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-[hsl(var(--border-primary))]">
              <button
                type="button"
                onClick={() => {
                  setSelectedAttendeeForMentor(null);
                  setSelectedMentorId("");
                  setMentorNotes("");
                }}
                className="rounded-lg border border-[hsl(var(--border-primary))] px-3 py-1.5 text-xs font-medium text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--bg-muted))]"
              >
                Cancelar
              </button>
              <button
                type="button"
                onClick={handleSaveManualMentor}
                disabled={!selectedMentorId || actionLoading}
                className="rounded-lg bg-[hsl(var(--primary))] px-4 py-1.5 text-xs font-semibold text-[hsl(var(--primary-foreground))] hover:opacity-90 disabled:opacity-50"
              >
                {actionLoading ? "Guardando..." : "Confirmar Asignación"}
              </button>
            </div>
          </div>
        )}
      </WorkspaceDrawer>

      {/* ── DRAWER 2: DETALLE DE SECUENCIA Y REGISTRO DE RESPUESTA ── */}
      <WorkspaceDrawer
        isOpen={Boolean(selectedAttendeeForSequence)}
        onClose={() => {
          setSelectedAttendeeForSequence(null);
          setResponseNotes("");
        }}
        title="Secuencia Multicanal y Respuesta"
        subtitle={selectedAttendeeForSequence ? selectedAttendeeForSequence.full_name : undefined}
      >
        {selectedAttendeeForSequence && (
          <div className="space-y-6 p-4 text-xs">
            {/* Resumen Asistente */}
            <div className="rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] p-3">
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-bold text-sm text-[hsl(var(--text-primary))]">
                    {selectedAttendeeForSequence.full_name}
                  </div>
                  <div className="text-2xs text-[hsl(var(--text-secondary))] mt-0.5">
                    {selectedAttendeeForSequence.email || "Sin email"} • {selectedAttendeeForSequence.phone || "Sin teléfono"}
                  </div>
                </div>
                <span className="rounded bg-[hsl(var(--bg-muted))] px-2 py-0.5 font-mono text-2xs font-semibold text-[hsl(var(--text-secondary))]">
                  {selectedAttendeeForSequence.registration_code}
                </span>
              </div>
            </div>

            {/* Historial de Pasos de la Cadencia */}
            <div className="space-y-3">
              <h4 className="text-2xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
                Cadencia Automatizada (3 Pasos)
              </h4>

              {/* Paso 1 */}
              <div className="rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] p-3">
                <div className="flex items-center justify-between">
                  <div className="font-semibold text-[hsl(var(--text-primary))]">
                    Paso 1: Agradecimiento (24h)
                  </div>
                  <span
                    className={`rounded px-1.5 py-0.5 text-3xs font-bold uppercase ${
                      selectedAttendeeForSequence.step_1?.status === "SENT"
                        ? "bg-[hsl(var(--success-muted))] text-[hsl(var(--success))]"
                        : "bg-[hsl(var(--warning-muted))] text-[hsl(var(--warning))]"
                    }`}
                  >
                    {selectedAttendeeForSequence.step_1?.status || "PENDING"}
                  </span>
                </div>
                {selectedAttendeeForSequence.step_1?.sent_at && (
                  <div className="mt-1 text-2xs text-[hsl(var(--text-muted))]">
                    Enviado: {new Date(selectedAttendeeForSequence.step_1.sent_at).toLocaleString()}
                  </div>
                )}
                <div className="mt-2 flex justify-end">
                  <button
                    onClick={() =>
                      handleTriggerStep(1, selectedAttendeeForSequence.persona_id, true)
                    }
                    disabled={actionLoading}
                    className="inline-flex items-center gap-1 rounded border border-[hsl(var(--border-primary))] px-2 py-1 text-2xs font-semibold text-[hsl(var(--text-primary))] hover:bg-[hsl(var(--bg-muted))] transition"
                  >
                    <Send className="h-3 w-3" />
                    <span>Forzar Reenvío Paso 1</span>
                  </button>
                </div>
              </div>

              {/* Paso 2 */}
              <div className="rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] p-3">
                <div className="flex items-center justify-between">
                  <div className="font-semibold text-[hsl(var(--text-primary))]">
                    Paso 2: Invitación Grupo de Vida (72h)
                  </div>
                  <span
                    className={`rounded px-1.5 py-0.5 text-3xs font-bold uppercase ${
                      selectedAttendeeForSequence.step_2?.status === "SENT"
                        ? "bg-[hsl(var(--success-muted))] text-[hsl(var(--success))]"
                        : "bg-[hsl(var(--warning-muted))] text-[hsl(var(--warning))]"
                    }`}
                  >
                    {selectedAttendeeForSequence.step_2?.status || "PENDING"}
                  </span>
                </div>
                {selectedAttendeeForSequence.step_2?.sent_at && (
                  <div className="mt-1 text-2xs text-[hsl(var(--text-muted))]">
                    Enviado: {new Date(selectedAttendeeForSequence.step_2.sent_at).toLocaleString()}
                  </div>
                )}
                <div className="mt-2 flex justify-end">
                  <button
                    onClick={() =>
                      handleTriggerStep(2, selectedAttendeeForSequence.persona_id, true)
                    }
                    disabled={actionLoading}
                    className="inline-flex items-center gap-1 rounded border border-[hsl(var(--border-primary))] px-2 py-1 text-2xs font-semibold text-[hsl(var(--text-primary))] hover:bg-[hsl(var(--bg-muted))] transition"
                  >
                    <Send className="h-3 w-3" />
                    <span>Forzar Reenvío Paso 2</span>
                  </button>
                </div>
              </div>

              {/* Paso 3 */}
              <div className="rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] p-3">
                <div className="flex items-center justify-between">
                  <div className="font-semibold text-[hsl(var(--text-primary))]">
                    Paso 3: Llamada Pastoral (7d)
                  </div>
                  <span
                    className={`rounded px-1.5 py-0.5 text-3xs font-bold uppercase ${
                      selectedAttendeeForSequence.step_3?.status === "SENT"
                        ? "bg-[hsl(var(--success-muted))] text-[hsl(var(--success))]"
                        : "bg-[hsl(var(--warning-muted))] text-[hsl(var(--warning))]"
                    }`}
                  >
                    {selectedAttendeeForSequence.step_3?.status || "PENDING"}
                  </span>
                </div>
                {selectedAttendeeForSequence.step_3?.sent_at && (
                  <div className="mt-1 text-2xs text-[hsl(var(--text-muted))]">
                    Enviado: {new Date(selectedAttendeeForSequence.step_3.sent_at).toLocaleString()}
                  </div>
                )}
                <div className="mt-2 flex justify-end">
                  <button
                    onClick={() =>
                      handleTriggerStep(3, selectedAttendeeForSequence.persona_id, true)
                    }
                    disabled={actionLoading}
                    className="inline-flex items-center gap-1 rounded border border-[hsl(var(--border-primary))] px-2 py-1 text-2xs font-semibold text-[hsl(var(--text-primary))] hover:bg-[hsl(var(--bg-muted))] transition"
                  >
                    <Send className="h-3 w-3" />
                    <span>Forzar Reenvío Paso 3</span>
                  </button>
                </div>
              </div>
            </div>

            {/* Registro de Respuesta o Petición de Oración */}
            <div className="space-y-3 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] p-3">
              <h4 className="text-2xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] flex items-center gap-1.5">
                <MessageSquare className="h-3.5 w-3.5 text-[hsl(var(--primary))]" />
                Registrar Respuesta / Feedback Pastoral
              </h4>

              {selectedAttendeeForSequence.response_received && (
                <div className="rounded bg-[hsl(var(--success-muted))] p-2 text-2xs text-[hsl(var(--success))] font-medium">
                  Última respuesta registrada{" "}
                  {selectedAttendeeForSequence.response_at
                    ? `el ${new Date(selectedAttendeeForSequence.response_at).toLocaleDateString()}`
                    : ""}
                </div>
              )}

              <div>
                <label className="block text-2xs font-semibold text-[hsl(var(--text-secondary))] mb-1">
                  Canal de contacto:
                </label>
                <select
                  value={responseChannel}
                  onChange={(e) => setResponseChannel(e.target.value)}
                  className="w-full rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-secondary))] px-2.5 py-1.5 text-xs text-[hsl(var(--text-primary))] focus:border-[hsl(var(--primary))] focus:outline-none"
                >
                  <option value="WHATSAPP">WhatsApp</option>
                  <option value="PHONE">Llamada Telefónica</option>
                  <option value="IN_PERSON">Presencial / En Servicio</option>
                  <option value="EMAIL">Correo Electrónico</option>
                </select>
              </div>

              <div>
                <label className="block text-2xs font-semibold text-[hsl(var(--text-secondary))] mb-1">
                  Petición de oración, notas o respuesta recibida:
                </label>
                <textarea
                  rows={3}
                  value={responseNotes}
                  onChange={(e) => setResponseNotes(e.target.value)}
                  placeholder="Detalla lo conversado con la persona, peticiones de oración o interés en grupo..."
                  className="w-full rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-secondary))] p-2.5 text-xs text-[hsl(var(--text-primary))] focus:border-[hsl(var(--primary))] focus:outline-none"
                />
              </div>

              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={handleSaveResponse}
                  disabled={!responseNotes.trim() || actionLoading}
                  className="rounded-lg bg-[hsl(var(--primary))] px-4 py-1.5 text-xs font-semibold text-[hsl(var(--primary-foreground))] hover:opacity-90 disabled:opacity-50"
                >
                  {actionLoading ? "Guardando..." : "Guardar Respuesta"}
                </button>
              </div>
            </div>
          </div>
        )}
      </WorkspaceDrawer>
    </div>
  );
}
