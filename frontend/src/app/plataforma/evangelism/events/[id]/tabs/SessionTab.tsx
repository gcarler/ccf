"use client";

import React, { useEffect, useMemo, useState } from "react";
import { apiFetch } from "@/lib/http";
import { toast } from "sonner";
import WorkspaceDrawer from "@/components/WorkspaceDrawer";
import { Calendar, CheckCircle2, Download, Mic, Save, UserPlus, Users, X } from "lucide-react";
import type { Persona } from "@/app/plataforma/evangelism/types";

type Assignment = { persona_id: string; role: string; persona_name?: string };

type SessionData = {
  event_id: number;
  session_date: string;
  assignments: Assignment[];
  metrics: Record<string, number>;
  attendees: { persona_id: string; name: string; role: string; scanned_at: string | null }[];
  absentees: { persona_id: string; name: string; role: string; phone: string }[];
  total_absentees: number;
  absentees_truncated: boolean;
  total_attendance: number;
  total_expected: number;
  attendance_rate: number;
};

interface PersonaSelectProps {
  personas: Persona[];
  value: string | string[] | null;
  onChange: (next: string | string[] | null) => void;
  label: string;
  multi?: boolean;
}

function PersonaSelect({ personas, value, onChange, label, multi = false }: PersonaSelectProps) {
  const [search, setSearch] = useState('');
  const [open, setOpen] = useState(false);

  const filtered = useMemo(() => {
    if (!search) return personas.slice(0, 50);
    const q = search.toLowerCase();
    return personas.filter((m) =>
      m.nombre_completo.toLowerCase().includes(q)
    ).slice(0, 50);
  }, [personas, search]);

  const handleSelect = (m: Persona) => {
    if (multi) {
      const selected = Array.isArray(value) ? value : [];
      if (!selected.includes(m.id)) onChange([...selected, m.id]);
    } else {
      onChange(m.id);
      setOpen(false);
    }
  };

  const handleRemove = (id: string) => {
    if (multi) {
      const selected = Array.isArray(value) ? value : [];
      onChange(selected.filter((v) => v !== id));
    }
    else onChange(null);
  };

  return (
    <div className="relative">
      <label className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-2 block">{label}</label>

      {multi ? (
        <div className="flex flex-wrap gap-2 mb-2">
          {(Array.isArray(value) ? value : []).map((id) => {
            const m = personas.find((x) => x.id === id);
            if (!m) return null;
            return (
              <div key={id} className="flex items-center gap-2 px-3 py-1.5 badge-info rounded-lg text-sm font-bold">
                {m.nombre_completo}
                <button type="button" aria-label={`Quitar ${m.nombre_completo}`} onClick={() => handleRemove(id)} className="hover:text-[hsl(var(--destructive))]"><X size={14}/></button>
              </div>
            );
          })}
        </div>
      ) : value ? (
        <div className="flex items-center justify-between px-4 py-1.5 bg-info-soft border border-info-muted rounded-lg mb-2">
          <span className="text-sm font-bold text-info-text dark:text-info">
            {(() => {
              const m = personas.find((x) => x.id === value);
              return m ? m.nombre_completo : 'Cargando...';
            })()}
          </span>
          <button type="button" aria-label="Quitar selección" onClick={() => typeof value === 'string' && handleRemove(value)} className="text-[hsl(var(--primary))] hover:text-[hsl(var(--destructive))]"><X size={16}/></button>
        </div>
      ) : null}

      {(!value || multi) && (
        <div>
          <div className="relative">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="absolute left-3 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
            <input
              aria-label={label}
              value={search}
              onChange={(e) => { setSearch(e.target.value); setOpen(true); }}
              onFocus={() => setOpen(true)}
              placeholder="Buscar persona..."
              className="w-full pl-9 pr-4 py-1.5 bg-[hsl(var(--bg-muted))] dark:bg-black/20 border border-[hsl(var(--border-primary))] rounded-lg text-sm outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
          {open && search && (
            <div className="absolute z-20 top-full left-0 right-0 mt-2 bg-[hsl(var(--bg-primary))] dark:bg-surface-card border border-[hsl(var(--border-primary))] rounded-lg shadow-xl max-h-60 overflow-y-auto">
              {filtered.map((m: Persona) => (
                <button
                  key={m.id}
                  onClick={() => handleSelect(m)}
                  className="w-full text-left px-4 py-1.5 hover:bg-[hsl(var(--bg-muted))] dark:hover:bg-white/5 border-b border-[hsl(var(--border-primary))] flex flex-col"
                >
                  <span className="text-sm font-bold text-[hsl(var(--text-primary))]">{m.nombre_completo}</span>
                  <span className="text-[10px] uppercase font-bold tracking-wide text-[hsl(var(--text-secondary))]">{m.church_role || 'Persona'}</span>
                </button>
              ))}
              {filtered.length === 0 && <div className="p-4 text-center text-sm text-[hsl(var(--text-secondary))]">Sin resultados</div>}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

interface SessionTabProps {
  eventId: string;
  token: string | null;
  eventName: string;
}

export default function SessionTab({ eventId, token, eventName }: SessionTabProps) {
  const [sessionDate, setSessionDate] = useState(() => new Date().toISOString().split('T')[0]);
  const [sessionData, setSessionData] = useState<SessionData | null>(null);
  const [initialSessionFingerprint, setInitialSessionFingerprint] = useState<string | null>(null);
  const [sessionLoading, setSessionLoading] = useState(false);
  const [isVisitorDrawerOpen, setIsVisitorDrawerOpen] = useState(false);
  const [visitorForm, setVisitorForm] = useState({ first_name: '', last_name: '', phone: '', email: '' });
  const [refreshKey, setRefreshKey] = useState(0);
  const [savingSession, setSavingSession] = useState(false);
  const [exportingCsv, setExportingCsv] = useState(false);
  const [savingVisitor, setSavingVisitor] = useState(false);

  // Agenda Form State
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [mcId, setMcId] = useState<string | null>(null);
  const [preacherIds, setPreacherIds] = useState<string[]>([]);
  const [offeringId, setOfferingId] = useState<string | null>(null);

  const buildSessionFingerprint = useMemo(() => {
    return (mc: string | null, preachers: string[], offering: string | null) => JSON.stringify({
      mc,
      preachers: [...preachers].sort((a, b) => a.localeCompare(b)),
      offering,
    });
  }, []);

  const currentSessionFingerprint = buildSessionFingerprint(mcId, preacherIds, offeringId);
  const hasUnsavedSessionChanges = Boolean(
    initialSessionFingerprint !== null &&
    currentSessionFingerprint !== initialSessionFingerprint
  );

  useEffect(() => {
    if (token) {
      apiFetch<Persona[]>('/crm/personas', { token, query: { limit: 1000 } })
        .then(setPersonas)
        .catch(() => toast.error('Error al cargar personas'));
    }
  }, [token]);

  useEffect(() => {
    if (!sessionDate || !token) return;
    const loadSession = async () => {
      try {
        setSessionLoading(true);
        const data = await apiFetch<SessionData>(`/evangelism/events/${eventId}/sessions/${sessionDate}`, { token });
        setSessionData(data);

        // Pre-fill forms
        const mc = data.assignments.find(a => a.role === 'MC');
        const pre = data.assignments.filter(a => a.role === 'PREACHER');
        const off = data.assignments.find(a => a.role === 'OFFERING');

        setMcId(mc?.persona_id || null);
        setPreacherIds(pre.map(a => a.persona_id));
        setOfferingId(off?.persona_id || null);
        setInitialSessionFingerprint(JSON.stringify({
          mc: mc?.persona_id || null,
          preachers: pre.map((a) => a.persona_id).sort((a, b) => a.localeCompare(b)),
          offering: off?.persona_id || null,
        }));
      } catch (err) {
        toast.error("Error al cargar datos de la sesión");
      } finally {
        setSessionLoading(false);
      }
    };
    loadSession();
  }, [sessionDate, token, eventId, refreshKey]);

  const handleExportCsv = async () => {
    if (!token) return;
    setExportingCsv(true);
    try {
      const res = await apiFetch<string>(`/evangelism/events/${eventId}/sessions/${sessionDate}/export`, { token });
      const blob = new Blob([res], { type: 'text/csv;charset=utf-8;' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Reporte_${eventName}_${sessionDate}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
    } catch {
      toast.error("Error al exportar el reporte");
    } finally {
      setExportingCsv(false);
    }
  };

  const handleAddVisitor = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;
    setSavingVisitor(true);
    try {
      await apiFetch(`/evangelism/events/${eventId}/sessions/${sessionDate}/visitors`, {
        method: 'POST',
        token,
        body: visitorForm
      });
      toast.success("Visitante registrado con éxito");
      setIsVisitorDrawerOpen(false);
      setVisitorForm({ first_name: '', last_name: '', phone: '', email: '' });
      setRefreshKey(k => k + 1);
    } catch {
      toast.error("Error al registrar visitante");
    } finally {
      setSavingVisitor(false);
    }
  };

  const saveSession = async () => {
    if (!token || !sessionDate) return;
    setSavingSession(true);
    try {
      const assignments: Assignment[] = [];
      if (mcId) assignments.push({ persona_id: mcId, role: 'MC' });
      if (offeringId) assignments.push({ persona_id: offeringId, role: 'OFFERING' });
      preacherIds.forEach(pid => assignments.push({ persona_id: pid, role: 'PREACHER' }));

      await apiFetch(`/evangelism/events/${eventId}/assignments`, {
        method: 'POST',
        token,
        body: { session_date: sessionDate, assignments }
      });
      setInitialSessionFingerprint(currentSessionFingerprint);
      toast.success("Agenda configurada correctamente");
    } catch (err) {
      toast.error("Error al guardar la agenda");
    } finally {
      setSavingSession(false);
    }
  };

  return (
    <div className="space-y-3">
      {/* Toolbar de Sesion */}
      <div className="flex flex-col md:flex-row gap-4 items-end bg-[hsl(var(--bg-primary))] p-4 rounded-md border border-[hsl(var(--border-primary))] shadow-sm">
        <div className="flex-1 w-full">
          <label className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-2 block">Fecha de la Sesion</label>
          <div className="relative">
            <Calendar className="absolute left-4 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]" size={16} />
            <input
              type="date"
              value={sessionDate}
              onChange={(e) => setSessionDate(e.target.value)}
              className="w-full bg-[hsl(var(--bg-muted))] dark:bg-black/20 border border-[hsl(var(--border-primary))] rounded-lg py-1.5 pl-11 pr-4 text-sm font-bold outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
        </div>
        <div className="flex items-center gap-4">
          <button
            onClick={() => setIsVisitorDrawerOpen(true)}
            className="px-3 py-1.5 bg-success text-white rounded-lg text-[10px] font-semibold uppercase tracking-wide shadow-lg shadow-success hover:scale-105 transition-all flex items-center gap-2"
          >
            <UserPlus size={16}/> Registrar Visitante
          </button>
          <button
            onClick={saveSession}
            disabled={savingSession || !sessionDate}
            className="px-3 py-1.5 bg-[hsl(var(--primary))] text-white rounded-lg text-[10px] font-semibold uppercase tracking-wide shadow-lg shadow-primary hover:scale-105 transition-all flex items-center gap-2 disabled:opacity-60 disabled:hover:scale-100"
          >
            <Save size={16}/> {savingSession ? 'Guardando...' : 'Guardar Agenda'}
          </button>
        </div>
      </div>

      {hasUnsavedSessionChanges && (
        <div className="px-3 py-2 bg-warning-soft border border-warning-muted rounded-lg text-[11px] font-semibold text-warning-text dark:text-warning flex items-center gap-2">
          <span className="size-2 rounded-full bg-warning animate-pulse" />
          Tienes cambios sin guardar en la agenda
        </div>
      )}

      {sessionLoading ? (
        <div className="p-4 text-center animate-pulse font-bold text-[hsl(var(--text-secondary))]">Cargando datos de la sesion...</div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* AGENDA PANNEL */}
          <div className="bg-[hsl(var(--bg-primary))] rounded-md border border-[hsl(var(--border-primary))] p-4 shadow-sm">
            <h3 className="text-sm font-semibold uppercase tracking-wide text-[hsl(var(--text-primary))] mb-3 flex items-center gap-2">
              <Mic className="text-[hsl(var(--primary))]" size={18}/> Agenda de la Reunion
            </h3>
            <div className="space-y-3">
              <PersonaSelect
                label="Maestro de Ceremonia"
                personas={personas}
                value={mcId}
                onChange={(next) => setMcId(typeof next === 'string' ? next : null)}
              />
              <div className="h-px bg-[hsl(var(--bg-muted))] w-full my-4" />
              <PersonaSelect
                label="Predicador(es)"
                personas={personas}
                value={preacherIds}
                onChange={(next) => setPreacherIds(Array.isArray(next) ? next : [])}
                multi
              />
              <div className="h-px bg-[hsl(var(--bg-muted))] w-full my-4" />
              <PersonaSelect
                label="Palabra de Ofrenda"
                personas={personas}
                value={offeringId}
                onChange={(next) => setOfferingId(typeof next === 'string' ? next : null)}
              />
            </div>
          </div>

          {/* ATTENDANCE PANNEL */}
          <div className="space-y-3">
            <div className="bg-[hsl(var(--bg-primary))] rounded-md border border-[hsl(var(--border-primary))] p-4 shadow-sm">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-[hsl(var(--text-primary))] mb-3 flex items-center gap-2">
                <Users className="text-success" size={18}/> Reporte de Asistencia
              </h3>
              <div className="flex items-center gap-4 mb-3">
                <div className="size-8 rounded-md bg-success-soft text-success-text flex items-center justify-center text-lg font-bold">
                  {sessionData?.total_attendance || 0}
                </div>
                <div>
                  <p className="text-lg font-bold text-[hsl(var(--text-primary))]">Asistentes Totales</p>
                  <p className="text-xs font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Registrados en check-in</p>
                </div>
              </div>

              <div className="space-y-4">
                <h4 className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Desglose por Ministerio / Perfil</h4>
                {sessionData?.metrics && Object.entries(sessionData.metrics).map(([key, val]) => (
                  <div key={key} className="flex items-center justify-between p-3 rounded-md bg-[hsl(var(--bg-muted))]">
                    <span className="text-sm font-bold text-[hsl(var(--text-primary))]">{key}</span>
                    <span className="text-sm font-semibold text-[hsl(var(--primary))] bg-info-muted px-3 py-1 rounded-lg">{val}</span>
                  </div>
                ))}
              </div>

              {/* Absentees Banner */}
              {(sessionData?.total_absentees ?? 0) > 0 && (
                <div className="mt-3 p-4 rounded-lg bg-warning-soft border border-warning-muted flex items-center justify-between gap-4">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-warning-text dark:text-warning">Inasistentes</p>
                    <p className="text-lg font-bold text-warning-text dark:text-warning mt-0.5">{sessionData?.total_absentees}</p>
                    {sessionData?.absentees_truncated && (
                      <p className="text-[10px] text-warning-text/70 mt-1">Mostrando {sessionData?.absentees?.length} de {sessionData?.total_absentees}. Descarga el CSV para ver todos.</p>
                    )}
                  </div>
                  <button
                    onClick={handleExportCsv}
                    disabled={exportingCsv}
                    className="shrink-0 px-4 py-2 bg-warning hover:opacity-90 text-white rounded-md text-[10px] font-semibold uppercase tracking-wide transition-all flex items-center gap-2 disabled:opacity-60"
                  >
                    <Download size={12} /> {exportingCsv ? 'Exportando...' : 'Exportar Lista'}
                  </button>
                </div>
              )}

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-3">
                <div className="rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-muted))] p-4">
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Personas presentes</h4>
                    <span className="text-[10px] font-semibold uppercase tracking-wide text-success-text">{sessionData?.attendees?.length ?? 0}</span>
                  </div>
                  <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                    {(sessionData?.attendees || []).length === 0 ? (
                      <p className="text-sm text-[hsl(var(--text-secondary))]">Sin registros de asistentes.</p>
                    ) : (
                      sessionData!.attendees.map((att) => (
                        <div key={`${att.persona_id}-${att.role}`} className="flex items-center justify-between gap-3 rounded-md bg-[hsl(var(--bg-primary))] dark:bg-surface-card border border-[hsl(var(--border-primary))] px-3 py-2">
                          <div className="min-w-0">
                            <p className="text-sm font-bold text-[hsl(var(--text-primary))] truncate">{att.name}</p>
                            <p className="text-[10px] uppercase font-bold tracking-wide text-[hsl(var(--text-secondary))]">{att.role}</p>
                          </div>
                          <span className="text-[10px] font-semibold uppercase tracking-wide text-success-text">
                            {att.scanned_at ? new Date(att.scanned_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'OK'}
                          </span>
                        </div>
                      ))
                    )}
                  </div>
                </div>

                <div className="rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-muted))] p-4">
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Personas ausentes</h4>
                    <span className="text-[10px] font-semibold uppercase tracking-wide text-warning-text">{sessionData?.absentees?.length ?? 0}</span>
                  </div>
                  <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                    {(sessionData?.absentees || []).length === 0 ? (
                      <p className="text-sm text-[hsl(var(--text-secondary))]">No hay ausentes en esta sesión.</p>
                    ) : (
                      sessionData!.absentees.map((att) => (
                        <div key={`${att.persona_id}-${att.role}`} className="flex items-center justify-between gap-3 rounded-md bg-[hsl(var(--bg-primary))] dark:bg-surface-card border border-[hsl(var(--border-primary))] px-3 py-2">
                          <div className="min-w-0">
                            <p className="text-sm font-bold text-[hsl(var(--text-primary))] truncate">{att.name}</p>
                            <p className="text-[10px] uppercase font-bold tracking-wide text-[hsl(var(--text-secondary))]">{att.role}</p>
                          </div>
                          <span className="text-[10px] font-semibold uppercase tracking-wide text-danger-text">Ausente</span>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* DRAWER Visitante */}
      <WorkspaceDrawer
        isOpen={isVisitorDrawerOpen}
        onClose={() => setIsVisitorDrawerOpen(false)}
        title="Nuevo Visitante"
        subtitle="Registra a una persona no perteneciente a la base de datos"
        actions={
          <>
            <button type="button" disabled={savingVisitor} onClick={() => setIsVisitorDrawerOpen(false)} className="px-4 py-2 text-[11px] font-bold text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] transition-colors disabled:opacity-60">
              Cancelar
            </button>
            <button type="button" onClick={handleAddVisitor} disabled={savingVisitor || !visitorForm.first_name || !visitorForm.last_name} className="flex items-center gap-2 px-3 py-2 bg-[hsl(var(--primary))] text-white rounded-lg text-[11px] font-semibold uppercase tracking-wide shadow-lg shadow-primary hover:bg-[hsl(var(--primary))] transition-all disabled:opacity-60">
              <CheckCircle2 size={16} /> {savingVisitor ? 'Guardando...' : 'Guardar Asistencia'}
            </button>
          </>
        }
      >
        <div className="space-y-3 mt-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] block">Nombre</label>
              <input required disabled={savingVisitor} value={visitorForm.first_name} onChange={e => setVisitorForm({...visitorForm, first_name: e.target.value})} className="w-full px-4 py-1.5 bg-[hsl(var(--bg-muted))] dark:bg-black/20 border border-[hsl(var(--border-primary))] rounded-md text-sm font-bold outline-none focus:ring-2 focus:ring-primary disabled:opacity-60" placeholder="Juan" />
            </div>
            <div className="space-y-1.5">
              <label className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] block">Apellido</label>
              <input required value={visitorForm.last_name} onChange={e => setVisitorForm({...visitorForm, last_name: e.target.value})} className="w-full px-4 py-1.5 bg-[hsl(var(--bg-muted))] dark:bg-black/20 border border-[hsl(var(--border-primary))] rounded-md text-sm font-bold outline-none focus:ring-2 focus:ring-primary" placeholder="Pérez" />
            </div>
          </div>
          <div className="space-y-1.5">
            <label className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] block">Teléfono (WhatsApp)</label>
            <input disabled={savingVisitor} value={visitorForm.phone} onChange={e => setVisitorForm({...visitorForm, phone: e.target.value})} className="w-full px-4 py-1.5 bg-[hsl(var(--bg-muted))] dark:bg-black/20 border border-[hsl(var(--border-primary))] rounded-md text-sm font-bold outline-none focus:ring-2 focus:ring-primary disabled:opacity-60" placeholder="+57 300 000 0000" />
          </div>
          <div className="space-y-1.5">
            <label className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] block">Correo Electrónico (Opcional)</label>
            <input type="email" disabled={savingVisitor} value={visitorForm.email} onChange={e => setVisitorForm({...visitorForm, email: e.target.value})} className="w-full px-4 py-1.5 bg-[hsl(var(--bg-muted))] dark:bg-black/20 border border-[hsl(var(--border-primary))] rounded-md text-sm font-bold outline-none focus:ring-2 focus:ring-primary disabled:opacity-60" placeholder="correo@ejemplo.com" />
          </div>
        </div>
      </WorkspaceDrawer>
    </div>
  );
}
