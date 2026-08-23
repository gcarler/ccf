"use client";

import React, { useEffect, useState, useCallback } from "react";
import { apiFetch, ApiError } from "@/lib/http";
import { toast } from "sonner";
import {
  Check, Download, FolderOpen, Loader2, Mail, Plus,
  QrCode, RefreshCw, Send, Trash2, Users, X, Megaphone, Settings2,
} from "lucide-react";
import clsx from "clsx";

type RegistrationStatus =
  | "PENDING"
  | "CONFIRMED"
  | "CHECKED_IN"
  | "ABSENT"
  | "CANCELLED"
  | "WAITLIST";

type EventRegistrationRow = {
  id: string;
  event_id: string;
  persona_id: string;
  persona_name: string | null;
  persona_email: string | null;
  persona_phone: string | null;
  registration_status: RegistrationStatus;
  qr_token: string | null;
  qr_generated_at: string | null;
  registered_at: string;
  confirmed_at: string | null;
  cancelled_at: string | null;
  check_in_at: string | null;
  check_out_at: string | null;
  checked_in_by: string | null;
  source: string;
  extras: Record<string, unknown>;
  waiting_list_position: number | null;
  reminder_sent_count: number;
  last_reminder_sent_at: string | null;
  crm_case_id?: string | null;
};

type RegistrationStats = {
  total: number;
  pending: number;
  confirmed: number;
  checked_in: number;
  absent: number;
  waitlist: number;
  cancelled: number;
  capacity_max: number | null;
  capacity_remaining: number | null;
  attendance_rate: number | null;
};

type PreregConfig = {
  requires_registration: boolean;
  requires_email_verification: boolean;
  registration_opens_at: string | null;
  registration_closes_at: string | null;
  capacity_max: number | null;
  waiting_list_enabled: boolean;
  qr_mode: "PER_REGISTRANT" | "PER_EVENT";
  contact_person: string | null;
  settings_json: Record<string, unknown>;
};

type EventCampaign = {
  id: string;
  event_id: string;
  name: string;
  plantilla_id: string | null;
  canal: "WHATSAPP" | "EMAIL" | "SMS";
  trigger_type: "MANUAL" | "RELATIVE_TO_EVENT" | "RELATIVE_TO_REGISTRATION";
  trigger_offset_minutes: number | null;
  target_status: RegistrationStatus[];
  sent_count: number;
  last_sent_at: string | null;
  created_by_id: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

type Plantilla = {
  id: string;
  nombre: string;
  canal?: string;
  contenido?: string;
};

const STATUS_BADGE: Record<RegistrationStatus, string> = {
  PENDING: "bg-warning-soft text-warning-text",
  CONFIRMED: "bg-success-soft text-success-text",
  CHECKED_IN: "bg-info-soft text-info-text",
  ABSENT: "bg-danger-soft text-danger-text",
  CANCELLED: "bg-[hsl(var(--bg-muted))] text-[hsl(var(--text-secondary))]",
  WAITLIST: "bg-info-soft text-info-text",
};

const STATUS_LABEL: Record<RegistrationStatus, string> = {
  PENDING: "Pendiente",
  CONFIRMED: "Confirmado",
  CHECKED_IN: "Asistió",
  ABSENT: "Ausente",
  CANCELLED: "Cancelado",
  WAITLIST: "Lista de espera",
};

const CANAL_LABEL: Record<EventCampaign["canal"], string> = {
  WHATSAPP: "WhatsApp",
  EMAIL: "Email",
  SMS: "SMS",
};

const TRIGGER_LABEL: Record<EventCampaign["trigger_type"], string> = {
  MANUAL: "Manual",
  RELATIVE_TO_EVENT: "Antes del evento",
  RELATIVE_TO_REGISTRATION: "Tras inscribirse",
};

export default function PreregistrationTab({ eventId, token }: { eventId: string; token: string | null }) {
  const [config, setConfig] = useState<PreregConfig | null>(null);
  const [stats, setStats] = useState<RegistrationStats | null>(null);
  const [rows, setRows] = useState<EventRegistrationRow[]>([]);
  const [campaigns, setCampaigns] = useState<EventCampaign[]>([]);
  const [plantillas, setPlantillas] = useState<Plantilla[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<RegistrationStatus | "">("");
  const [search, setSearch] = useState("");
  const [showConfigForm, setShowConfigForm] = useState(false);
  const [showCampaignForm, setShowCampaignForm] = useState(false);
  const [sendingCampaignId, setSendingCampaignId] = useState<string | null>(null);
  const [exportingCsv, setExportingCsv] = useState(false);

  const handleExportCsv = async () => {
    if (!token) return;
    setExportingCsv(true);
    try {
      const res = await apiFetch<string>(`/evangelism/events/${eventId}/registrations/export.csv`, { token, silent: true });
      const blob = new Blob([res], { type: "text/csv;charset=utf-8;" });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `inscritos_${eventId}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
    } catch {
      toast.error("Error al exportar el CSV");
    } finally {
      setExportingCsv(false);
    }
  };

  const loadAll = useCallback(async () => {
    setLoading(true);
    try {
      const [statsRes, rowsRes, campaignsRes, configRes] = await Promise.all([
        apiFetch<RegistrationStats>(`/evangelism/events/${eventId}/registrations/stats`, { token, silent: true }),
        apiFetch<EventRegistrationRow[]>(`/evangelism/events/${eventId}/registrations?page=1&page_size=200`, { token, silent: true }),
        apiFetch<EventCampaign[]>(`/evangelism/events/${eventId}/campaigns`, { token, silent: true }),
        apiFetch<PreregConfig>(`/evangelism/events/${eventId}`, { token, silent: true }).catch(() => null),
      ]);
      setStats(statsRes);
      setRows(rowsRes);
      setCampaigns(campaignsRes);
      setConfig(configRes);
    } catch (err) {
      if (err instanceof ApiError && err.status !== 404) {
        toast.error("No se pudo cargar el pre-registro");
      }
    } finally {
      setLoading(false);
    }
  }, [eventId, token]);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  useEffect(() => {
    apiFetch<Plantilla[]>(`/crm/plantillas?limit=100`, { token, silent: true })
      .then(setPlantillas)
      .catch(() => undefined);
  }, [token]);

  if (loading) {
    return <div className="p-6 text-center animate-pulse font-bold text-[hsl(var(--text-secondary))]">Cargando pre-registro...</div>;
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Settings2 size={16} className="text-[hsl(var(--primary))]" />
          <h3 className="text-sm font-bold uppercase tracking-wide text-[hsl(var(--text-primary))]">Pre-registro del evento</h3>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setShowCampaignForm(true)}
            className="px-3 py-2 rounded-md bg-[hsl(var(--bg-muted))] hover:bg-[hsl(var(--primary))] text-[hsl(var(--text-secondary))] hover:text-white text-xs font-semibold uppercase tracking-wide transition-all flex items-center gap-2"
          >
            <Megaphone size={14} /> Nueva campaña
          </button>
          <button
            onClick={() => setShowConfigForm(true)}
            className="px-3 py-2 rounded-md bg-[hsl(var(--bg-muted))] hover:bg-[hsl(var(--primary))] text-[hsl(var(--text-secondary))] hover:text-white text-xs font-semibold uppercase tracking-wide transition-all flex items-center gap-2"
          >
            <Settings2 size={14} /> Configurar
          </button>
        </div>
      </div>

      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
          <StatCard label="Total" value={stats.total} />
          <StatCard label="Confirmados" value={stats.confirmed} accent="success" />
          <StatCard label="Asistieron" value={stats.checked_in} accent="info" />
          <StatCard label="Pendientes" value={stats.pending} accent="warning" />
          <StatCard label="Lista de espera" value={stats.waitlist} accent="warning" />
          <StatCard label="Cancelados" value={stats.cancelled} accent="danger" />
        </div>
      )}

      <div className="flex items-center justify-between gap-3 p-3 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--bg-muted))]">
        <div className="text-sm text-[hsl(var(--text-secondary))]">
          Al cerrar la asistencia, los confirmados sin check-in se marcan como ausentes y generan seguimiento CRM automaticamente.
        </div>
        <button
          onClick={async () => {
            if (!window.confirm("¿Cerrar la asistencia? Los confirmados sin check-in se marcaran como ausentes.")) return;
            try {
              await apiFetch(`/evangelism/events/${eventId}/attendance/close`, { method: "POST", token });
              toast.success("Asistencia cerrada");
              loadAll();
            } catch {
              toast.error("No se pudo cerrar la asistencia");
            }
          }}
          className="shrink-0 inline-flex items-center gap-1.5 rounded-md bg-danger-soft px-3 py-1.5 text-sm font-semibold text-danger-text hover:opacity-80 transition-all"
        >
          <Check size={14} /> Cerrar asistencia
        </button>
      </div>

      {config?.requires_registration === false && (
        <div className="p-4 bg-info-soft text-info-text rounded-lg text-sm font-semibold flex items-center gap-2">
          <InfoIcon /> Este evento no tiene pre-registro activo. Configúralo para habilitar el flujo de inscripción con QR.
        </div>
      )}

      {campaigns.length > 0 && (
        <div className="rounded-lg border border-[hsl(var(--border))] overflow-hidden">
          <div className="px-4 py-2.5 bg-[hsl(var(--bg-muted))] text-2xs font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] flex items-center gap-2">
            <Megaphone size={13} /> Campañas de mensajería
          </div>
          <div className="divide-y divide-[hsl(var(--border))]">
            {campaigns.map((c) => (
              <div key={c.id} className="px-4 py-3 flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm font-bold text-[hsl(var(--text-primary))]">{c.name}</span>
                    <span className="rounded-full bg-[hsl(var(--bg-muted))] px-2 py-0.5 text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                      {CANAL_LABEL[c.canal]}
                    </span>
                    <span className="rounded-full bg-[hsl(var(--bg-muted))] px-2 py-0.5 text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                      {TRIGGER_LABEL[c.trigger_type]}
                    </span>
                  </div>
                  <p className="text-xs font-medium text-[hsl(var(--text-secondary))] mt-1">
                    Enviados: {c.sent_count}{c.last_sent_at ? ` · Último envío: ${new Date(c.last_sent_at).toLocaleString("es-CO")}` : " · Sin envíos"}
                  </p>
                  <button
                    onClick={() => {
                      if (!c.sent_count || c.sent_count === 0) {
                        toast.info("Sin entregas registradas para esta campaña");
                      } else {
                        toast.info(`${c.sent_count} envíos realizados${c.last_sent_at ? ` · Último envío: ${new Date(c.last_sent_at).toLocaleString("es-CO")}` : ""}`);
                      }
                    }}
                    className="text-xs text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] transition-all"
                    title="Ver entregas"
                  >
                    Ver entregas
                  </button>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <button
                    onClick={async () => {
                      setSendingCampaignId(c.id);
                      try {
                        await apiFetch(`/evangelism/events/${eventId}/campaigns/${c.id}/send`, { method: "POST", token, body: {}, silent: true });
                        toast.success("Campaña enviada");
                        loadAll();
                      } catch (err) {
                        if (err instanceof ApiError) {
                          const detail = err.detail as { code?: string; detail?: string } | undefined;
                          toast.error(detail?.detail || "No se pudo enviar la campaña");
                        }
                      } finally {
                        setSendingCampaignId(null);
                      }
                    }}
                    disabled={sendingCampaignId !== null}
                    className="px-3 py-1.5 rounded-md bg-info-soft dark:bg-[hsl(var(--info)/0.2)] text-[hsl(var(--primary))] text-2xs font-semibold uppercase flex items-center gap-1.5 hover:opacity-80 transition-all disabled:opacity-50"
                  >
                    {sendingCampaignId === c.id ? <Loader2 size={13} className="animate-spin" /> : <Send size={13} />} Enviar
                  </button>
                  <button
                    onClick={async () => {
                      if (!window.confirm(`¿Eliminar la campaña "${c.name}"?`)) return;
                      try {
                        await apiFetch(`/evangelism/events/${eventId}/campaigns/${c.id}`, { method: "DELETE", token, silent: true });
                        toast.success("Campaña eliminada");
                        loadAll();
                      } catch {
                        toast.error("No se pudo eliminar la campaña");
                      }
                    }}
                    className="p-1.5 rounded-md text-[hsl(var(--text-secondary))] hover:text-danger-text hover:bg-danger-soft transition-all"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="rounded-lg border border-[hsl(var(--border))] overflow-hidden">
        <div className="px-4 py-2.5 bg-[hsl(var(--bg-muted))] flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2 text-2xs font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
            <Users size={13} /> Inscritos ({rows.length})
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as RegistrationStatus | "")}
              className="px-2 py-1.5 rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] text-xs font-semibold text-[hsl(var(--text-primary))] outline-none"
            >
              <option value="">Todos los estados</option>
              {Object.entries(STATUS_LABEL).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Buscar por nombre/email/teléfono"
              className="px-2 py-1.5 rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] text-xs font-semibold text-[hsl(var(--text-primary))] outline-none placeholder:text-[hsl(var(--text-secondary))] w-44"
            />
            <button
              onClick={handleExportCsv}
              disabled={exportingCsv}
              className="px-2.5 py-1.5 rounded-md bg-[hsl(var(--bg-muted))] hover:bg-[hsl(var(--primary))] text-[hsl(var(--text-secondary))] hover:text-white text-2xs font-semibold uppercase flex items-center gap-1.5 transition-all disabled:opacity-50"
            >
              {exportingCsv ? <Loader2 size={13} className="animate-spin" /> : <Download size={13} />} CSV
            </button>
            <button
              onClick={loadAll}
              className="p-1.5 rounded-md text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--bg-muted))] transition-all"
              title="Refrescar"
            >
              <RefreshCw size={14} />
            </button>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-[hsl(var(--bg-muted))]/50 text-2xs font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                <th className="px-4 py-2 text-left">Persona</th>
                <th className="px-4 py-2 text-left">Estado</th>
                <th className="px-4 py-2 text-left">Registro</th>
                <th className="px-4 py-2 text-left">QR</th>
                <th className="px-4 py-2 text-left">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[hsl(var(--border))]">
              {rows
                .filter((r) => !statusFilter || r.registration_status === statusFilter)
                .filter((r) => {
                  if (!search) return true;
                  const q = search.toLowerCase();
                  return (r.persona_name || "").toLowerCase().includes(q)
                    || (r.persona_email || "").toLowerCase().includes(q)
                    || (r.persona_phone || "").toLowerCase().includes(q);
                })
                .map((r) => (
                  <tr key={r.id}>
                    <td className="px-4 py-2.5">
                      <div className="font-bold text-[hsl(var(--text-primary))]">{r.persona_name || "—"}</div>
                      <div className="text-xs font-medium text-[hsl(var(--text-secondary))]">
                        {r.persona_email || ""}{r.persona_email && r.persona_phone ? " · " : ""}{r.persona_phone || ""}
                      </div>
                    </td>
                    <td className="px-4 py-2.5">
                      <span className={clsx("inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-2xs font-semibold uppercase tracking-wide", STATUS_BADGE[r.registration_status])}>
                        {STATUS_LABEL[r.registration_status]}
                        {r.waiting_list_position != null && <span>#{r.waiting_list_position}</span>}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-xs font-semibold text-[hsl(var(--text-secondary))]">
                      {new Date(r.registered_at).toLocaleString("es-CO")}
                    </td>
                    <td className="px-4 py-2.5">
                      {r.qr_token ? (
                        <a
                          href={`/public/events/${eventId}/qr?token=${r.qr_token}`}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-1 text-xs font-semibold text-[hsl(var(--primary))] hover:underline"
                        >
                          <QrCode size={14} /> Ver
                        </a>
                      ) : (
                        <span className="text-xs font-medium text-[hsl(var(--text-secondary))]">—</span>
                      )}
                    </td>
                    <td className="px-4 py-2.5">
                      <div className="flex items-center gap-1.5">
                        {r.registration_status === "CONFIRMED" && (
                          <button
                            onClick={async () => {
                              if (!window.confirm("¿Reenviar el correo de confirmación/QR a esta persona?")) return;
                              try {
                                await apiFetch(`/evangelism/events/${eventId}/registrations/${r.id}/resend-confirmation`, { method: "POST", token, silent: true });
                                toast.success("Confirmación reenviada");
                              } catch {
                                toast.error("No se pudo reenviar la confirmación");
                              }
                            }}
                            className="p-1.5 rounded-md text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] hover:bg-info-soft transition-all"
                            title="Reenviar confirmación"
                          >
                            <Mail size={14} />
                          </button>
                        )}
                        {r.crm_case_id && (
                          <a
                            href={`/plataforma/crm/cases/${r.crm_case_id}`}
                            className="p-1.5 rounded-md text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] hover:bg-info-soft transition-all"
                            title="Ver caso CRM"
                          >
                            <FolderOpen size={14} />
                          </a>
                        )}
                        {r.registration_status !== "CANCELLED" && (
                          <button
                            onClick={async () => {
                              if (!window.confirm(`¿Marcar a ${r.persona_name || "esta persona"} como CANCELADO?`)) return;
                              try {
                                await apiFetch(`/evangelism/events/${eventId}/registrations/${r.id}`, {
                                  method: "PATCH",
                                  token,
                                  body: { registration_status: "CANCELLED" },
                                  silent: true,
                                });
                                toast.success("Inscripción cancelada");
                                loadAll();
                              } catch {
                                toast.error("No se pudo cancelar la inscripción");
                              }
                            }}
                            className="p-1.5 rounded-md text-[hsl(var(--text-secondary))] hover:text-danger-text hover:bg-danger-soft transition-all"
                            title="Cancelar inscripción"
                          >
                            <X size={14} />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
          {rows.length === 0 && (
            <div className="p-6 text-center text-sm font-semibold text-[hsl(var(--text-secondary))]">
              No hay inscritos todavía. Comparte el enlace de pre-registro.
            </div>
          )}
        </div>
      </div>

      {showConfigForm && (
        <ConfigForm
          eventId={eventId}
          token={token}
          config={config}
          onClose={() => setShowConfigForm(false)}
          onSaved={() => { setShowConfigForm(false); loadAll(); }}
        />
      )}

      {showCampaignForm && (
        <CampaignForm
          eventId={eventId}
          token={token}
          plantillas={plantillas}
          onClose={() => setShowCampaignForm(false)}
          onSaved={() => { setShowCampaignForm(false); loadAll(); }}
        />
      )}
    </div>
  );
}

function InfoIcon() {
  return <span className="inline-block w-4 h-4 rounded-full bg-info-soft text-info-text text-2xs font-bold text-center leading-4">i</span>;
}

function StatCard({ label, value, accent }: { label: string; value: number; accent?: "success" | "info" | "warning" | "danger" }) {
  const color = accent === "success"
    ? "text-success-text"
    : accent === "info"
      ? "text-info-text"
      : accent === "warning"
        ? "text-warning-text"
        : accent === "danger"
          ? "text-danger-text"
          : "text-[hsl(var(--text-primary))]";
  return (
    <div className="rounded-lg border border-[hsl(var(--border))] p-3">
      <div className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{label}</div>
      <div className={clsx("text-xl font-bold mt-0.5", color)}>{value}</div>
    </div>
  );
}

function ConfigForm({ eventId, token, config, onClose, onSaved }: {
  eventId: string;
  token: string | null;
  config: PreregConfig | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [form, setForm] = useState<PreregConfig>(() => config ?? {
    requires_registration: true,
    requires_email_verification: false,
    registration_opens_at: null,
    registration_closes_at: null,
    capacity_max: null,
    waiting_list_enabled: false,
    qr_mode: "PER_REGISTRANT",
    contact_person: null,
    settings_json: {},
  });
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      await apiFetch(`/evangelism/events/${eventId}/preregistration-config`, {
        method: "PATCH",
        token,
        body: {
          ...form,
          registration_opens_at: form.registration_opens_at || null,
          registration_closes_at: form.registration_closes_at || null,
          capacity_max: form.capacity_max ? Number(form.capacity_max) : null,
        },
        silent: true,
      });
      toast.success("Configuración guardada");
      onSaved();
    } catch {
      toast.error("No se pudo guardar la configuración");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-end sm:items-center justify-center p-0 sm:p-4" onClick={onClose}>
      <div className="w-full sm:max-w-lg bg-[hsl(var(--bg-primary))] rounded-t-xl sm:rounded-xl shadow-2xl p-4 sm:p-6 max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-bold uppercase tracking-wide text-[hsl(var(--text-primary))] flex items-center gap-2">
            <Settings2 size={15} /> Configuración de pre-registro
          </h3>
          <button onClick={onClose} className="p-1.5 rounded-md hover:bg-[hsl(var(--bg-muted))] text-[hsl(var(--text-secondary))]">
            <X size={16} />
          </button>
        </div>

        <div className="space-y-4">
          <ToggleRow
            label="Habilitar pre-registro"
            checked={form.requires_registration}
            onChange={(v) => setForm({ ...form, requires_registration: v })}
          />
          <ToggleRow
            label="Verificación de email"
            hint="El inscrito debe confirmar su correo antes de recibir el QR"
            checked={form.requires_email_verification}
            onChange={(v) => setForm({ ...form, requires_email_verification: v })}
          />
          <ToggleRow
            label="Lista de espera"
            hint="Cuando el aforo esté lleno, los nuevos quedan en espera"
            checked={form.waiting_list_enabled}
            onChange={(v) => setForm({ ...form, waiting_list_enabled: v })}
          />

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="space-y-2">
              <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] block">Aforo máximo</label>
              <input
                type="number"
                min={1}
                value={form.capacity_max ?? ""}
                onChange={(e) => setForm({ ...form, capacity_max: e.target.value ? Number(e.target.value) : null })}
                className="w-full px-3 py-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] outline-none text-sm font-semibold text-[hsl(var(--text-primary))]"
                placeholder="Sin límite"
              />
            </div>
            <div className="space-y-2">
              <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] block">Modo QR</label>
              <select
                value={form.qr_mode}
                onChange={(e) => setForm({ ...form, qr_mode: e.target.value as "PER_REGISTRANT" | "PER_EVENT" })}
                className="w-full px-3 py-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] outline-none text-sm font-semibold text-[hsl(var(--text-primary))]"
              >
                <option value="PER_REGISTRANT">QR por inscrito</option>
                <option value="PER_EVENT">QR por evento</option>
              </select>
            </div>
            <div className="space-y-2">
              <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] block">Apertura de registro</label>
              <input
                type="datetime-local"
                value={toLocalInput(form.registration_opens_at)}
                onChange={(e) => setForm({ ...form, registration_opens_at: e.target.value ? new Date(e.target.value).toISOString() : null })}
                className="w-full px-3 py-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] outline-none text-sm font-semibold text-[hsl(var(--text-primary))]"
              />
            </div>
            <div className="space-y-2">
              <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] block">Cierre de registro</label>
              <input
                type="datetime-local"
                value={toLocalInput(form.registration_closes_at)}
                onChange={(e) => setForm({ ...form, registration_closes_at: e.target.value ? new Date(e.target.value).toISOString() : null })}
                className="w-full px-3 py-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] outline-none text-sm font-semibold text-[hsl(var(--text-primary))]"
              />
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] block">Persona de contacto</label>
            <input
              type="text"
              value={form.contact_person ?? ""}
              onChange={(e) => setForm({ ...form, contact_person: e.target.value || null })}
              className="w-full px-3 py-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] outline-none text-sm font-semibold text-[hsl(var(--text-primary))]"
              placeholder="Nombre de quien recibe consultas"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button onClick={onClose} className="px-4 py-2 text-xs font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] transition-colors">
              Cancelar
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-4 py-2 rounded-md bg-[hsl(var(--primary))] text-white text-xs font-bold uppercase tracking-wide flex items-center gap-2 disabled:opacity-50"
            >
              {saving ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />} Guardar
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function ToggleRow({ label, hint, checked, onChange }: {
  label: string;
  hint?: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <button type="button" onClick={() => onChange(!checked)} className="w-full flex items-center justify-between gap-3 text-left">
      <div>
        <div className="text-sm font-semibold text-[hsl(var(--text-primary))]">{label}</div>
        {hint && <div className="text-xs font-medium text-[hsl(var(--text-secondary))]">{hint}</div>}
      </div>
      <div className={clsx("relative w-10 h-6 rounded-full transition-all shrink-0", checked ? "bg-[hsl(var(--primary))]" : "bg-[hsl(var(--bg-muted))]")}>
        <div className={clsx("absolute top-0.5 w-5 h-5 rounded-full bg-white shadow transition-all", checked ? "left-4.5" : "left-0.5")} style={checked ? { left: "18px" } : { left: "2px" }} />
      </div>
    </button>
  );
}

function CampaignForm({ eventId, token, plantillas, onClose, onSaved }: {
  eventId: string;
  token: string | null;
  plantillas: Plantilla[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const [form, setForm] = useState({
    name: "",
    plantilla_id: plantillas[0]?.id ?? "",
    canal: "EMAIL" as "WHATSAPP" | "EMAIL" | "SMS",
    trigger_type: "MANUAL" as "MANUAL" | "RELATIVE_TO_EVENT" | "RELATIVE_TO_REGISTRATION",
    trigger_offset_minutes: "",
    target_status: ["CONFIRMED"] as string[],
    is_active: true,
  });
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    if (!form.name.trim() || !form.plantilla_id) {
      toast.error("Nombre y plantilla son obligatorios");
      return;
    }
    setSaving(true);
    try {
      await apiFetch(`/evangelism/events/${eventId}/campaigns`, {
        method: "POST",
        token,
        body: {
          ...form,
          trigger_offset_minutes: form.trigger_offset_minutes ? Number(form.trigger_offset_minutes) : null,
        },
        silent: true,
      });
      toast.success("Campaña creada");
      onSaved();
    } catch (err) {
      if (err instanceof ApiError) {
        const detail = err.detail as { code?: string; detail?: string } | undefined;
        toast.error(detail?.detail || "No se pudo crear la campaña");
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-end sm:items-center justify-center p-0 sm:p-4" onClick={onClose}>
      <div className="w-full sm:max-w-lg bg-[hsl(var(--bg-primary))] rounded-t-xl sm:rounded-xl shadow-2xl p-4 sm:p-6 max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-bold uppercase tracking-wide text-[hsl(var(--text-primary))] flex items-center gap-2">
            <Megaphone size={15} /> Nueva campaña
          </h3>
          <button onClick={onClose} className="p-1.5 rounded-md hover:bg-[hsl(var(--bg-muted))] text-[hsl(var(--text-secondary))]">
            <X size={16} />
          </button>
        </div>

        <div className="space-y-4">
          <div className="space-y-2">
            <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] block">Nombre *</label>
            <input
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="Ej: Recordatorio día del evento"
              className="w-full px-3 py-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] outline-none text-sm font-semibold text-[hsl(var(--text-primary))] placeholder:text-[hsl(var(--text-secondary))]"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="space-y-2">
              <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] block">Canal</label>
              <select
                value={form.canal}
                onChange={(e) => setForm({ ...form, canal: e.target.value as "WHATSAPP" | "EMAIL" | "SMS" })}
                className="w-full px-3 py-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] outline-none text-sm font-semibold text-[hsl(var(--text-primary))]"
              >
                <option value="EMAIL">Email</option>
                <option value="WHATSAPP">WhatsApp</option>
                <option value="SMS">SMS</option>
              </select>
            </div>
            <div className="space-y-2">
              <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] block">Disparo</label>
              <select
                value={form.trigger_type}
                onChange={(e) => setForm({ ...form, trigger_type: e.target.value as "MANUAL" | "RELATIVE_TO_EVENT" | "RELATIVE_TO_REGISTRATION" })}
                className="w-full px-3 py-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] outline-none text-sm font-semibold text-[hsl(var(--text-primary))]"
              >
                <option value="MANUAL">Manual</option>
                <option value="RELATIVE_TO_EVENT">Antes del evento</option>
                <option value="RELATIVE_TO_REGISTRATION">Tras inscribirse</option>
              </select>
            </div>
          </div>

          {form.trigger_type !== "MANUAL" && (
            <div className="space-y-2">
              <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] block">Offset (minutos)</label>
              <input
                type="number"
                value={form.trigger_offset_minutes}
                onChange={(e) => setForm({ ...form, trigger_offset_minutes: e.target.value })}
                placeholder="Ej: -1440 = 1 día antes"
                className="w-full px-3 py-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] outline-none text-sm font-semibold text-[hsl(var(--text-primary))] placeholder:text-[hsl(var(--text-secondary))]"
              />
            </div>
          )}

          <div className="space-y-2">
            <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] block">Plantilla de mensaje *</label>
            <select
              value={form.plantilla_id}
              onChange={(e) => setForm({ ...form, plantilla_id: e.target.value })}
              className="w-full px-3 py-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] outline-none text-sm font-semibold text-[hsl(var(--text-primary))]"
            >
              {plantillas.map((p) => (
                <option key={p.id} value={p.id}>{p.nombre}</option>
              ))}
            </select>
          </div>

          <div className="space-y-2">
            <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] block">Audiencia (estados)</label>
            <div className="flex flex-wrap gap-2">
              {(["CONFIRMED", "PENDING", "CHECKED_IN", "WAITLIST"] as const).map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => {
                    const next = form.target_status.includes(s)
                      ? form.target_status.filter((x) => x !== s)
                      : [...form.target_status, s];
                    setForm({ ...form, target_status: next });
                  }}
                  className={clsx(
                    "px-2.5 py-1.5 rounded-md text-2xs font-semibold uppercase tracking-wide border transition-all",
                    form.target_status.includes(s)
                      ? "bg-info-soft text-[hsl(var(--primary))] border-[hsl(var(--info)/40%)]"
                      : "border-[hsl(var(--border))] text-[hsl(var(--text-secondary))]"
                  )}
                >
                  {STATUS_LABEL[s]}
                </button>
              ))}
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button onClick={onClose} className="px-4 py-2 text-xs font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] transition-colors">
              Cancelar
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-4 py-2 rounded-md bg-[hsl(var(--primary))] text-white text-xs font-bold uppercase tracking-wide flex items-center gap-2 disabled:opacity-50"
            >
              {saving ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />} Crear
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function toLocalInput(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}
