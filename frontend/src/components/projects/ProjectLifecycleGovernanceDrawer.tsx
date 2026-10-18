"use client";

import { useCallback, useEffect, useState } from "react";
import clsx from "clsx";
import { apiFetch } from "@/lib/http";
import RightPanel from "@/components/ui/RightPanel";
import { toast } from "sonner";
import { Check, ClipboardCheck, Plus, Save, Trash2, Users } from "lucide-react";
import type { ProjectDevelopmentApproach, ProjectPMOType } from "@/types/projects";

type CharterStatus = "draft" | "authorized";
type Quadrant = "manage_closely" | "keep_satisfied" | "keep_informed" | "monitor";
type Engagement = "unaware" | "resistant" | "neutral" | "supportive" | "leading";
type Tab = "charter" | "stakeholders" | "closure";

interface Charter {
  sponsor_id: string | null;
  business_case: string;
  strategic_justification: string;
  measurable_objectives: string[];
  key_assumptions: string[];
  key_constraints: string[];
  high_level_risks: string[];
  preliminary_budget: number | null;
  development_approach: ProjectDevelopmentApproach;
  pmo_type: ProjectPMOType;
  charter_status: CharterStatus;
  authorized_by: string | null;
  authorized_at: string | null;
}

interface Stakeholder {
  id: string;
  project_id: string;
  persona_id: string | null;
  display_name: string | null;
  role_title: string | null;
  organization_or_ministry: string | null;
  power_level: number;
  interest_level: number;
  quadrant: Quadrant;
  engagement_level: Engagement;
  management_strategy: string | null;
}

interface Lesson {
  category: string;
  what_worked: string;
  what_failed: string;
  recommendation: string;
}

interface Closure {
  closure_status: "open" | "closed";
  deliverables_accepted_verified: boolean;
  financial_reconciliation_completed: boolean;
  final_bac: number | null;
  final_ac: number | null;
  final_variance: number | null;
  operational_handover_to: string | null;
  lessons_learned: Lesson[];
  closed_by: string | null;
  closed_at: string | null;
  wiki_synced: boolean;
}

interface ProjectLifecycleGovernanceDrawerProps {
  projectId: string;
  isOpen: boolean;
  onClose: () => void;
}

const emptyCharter: Charter = {
  sponsor_id: null,
  business_case: "",
  strategic_justification: "",
  measurable_objectives: [],
  key_assumptions: [],
  key_constraints: [],
  high_level_risks: [],
  preliminary_budget: null,
  development_approach: "hybrid",
  pmo_type: "controlling",
  charter_status: "draft",
  authorized_by: null,
  authorized_at: null,
};

const emptyClosure: Closure = {
  closure_status: "open",
  deliverables_accepted_verified: false,
  financial_reconciliation_completed: false,
  final_bac: null,
  final_ac: null,
  final_variance: null,
  operational_handover_to: "",
  lessons_learned: [],
  closed_by: null,
  closed_at: null,
  wiki_synced: false,
};

const fieldClass = "w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-3 py-2 text-sm text-[hsl(var(--text-primary))] placeholder:text-[hsl(var(--text-secondary))] focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]/40";
const labelClass = "mb-1 block text-xs font-semibold text-[hsl(var(--text-secondary))]";

function arrayField(value: string[]) {
  return value.join("\n");
}

function parseArray(value: string) {
  return value.split("\n").map(item => item.trim()).filter(Boolean);
}

export function ProjectLifecycleGovernanceDrawer({
  projectId,
  isOpen,
  onClose,
}: ProjectLifecycleGovernanceDrawerProps) {
  const [tab, setTab] = useState<Tab>("charter");
  const [charter, setCharter] = useState<Charter>(emptyCharter);
  const [stakeholders, setStakeholders] = useState<Stakeholder[]>([]);
  const [closure, setClosure] = useState<Closure>(emptyClosure);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [newStakeholder, setNewStakeholder] = useState({ display_name: "", role_title: "", organization_or_ministry: "", power_level: 3, interest_level: 3, engagement_level: "neutral" as Engagement, management_strategy: "" });
  const [confirmRemoval, setConfirmRemoval] = useState<string | null>(null);

  const loadGovernance = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [charterResult, stakeholderResult, closureResult] = await Promise.all([
        apiFetch<Charter>(`/projects/${projectId}/charter`),
        apiFetch<Stakeholder[]>(`/projects/${projectId}/stakeholders`),
        apiFetch<Closure>(`/projects/${projectId}/closure`),
      ]);
      setCharter({ ...emptyCharter, ...charterResult });
      setStakeholders(stakeholderResult);
      setClosure({ ...emptyClosure, ...closureResult });
    } catch (cause: unknown) {
      const message = cause instanceof Error ? cause.message : "No se pudo cargar la gobernanza del proyecto.";
      setError(message);
      toast.error(message);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    if (isOpen) void loadGovernance();
  }, [isOpen, loadGovernance]);

  const saveCharter = async (authorize = false) => {
    setSaving(true);
    try {
      const result = await apiFetch<Charter>(`/projects/${projectId}/charter`, {
        method: "PUT",
        body: JSON.stringify({ ...charter, charter_status: authorize ? "authorized" : charter.charter_status }),
      });
      setCharter({ ...emptyCharter, ...result });
      toast.success(authorize ? "Acta autorizada formalmente." : "Acta guardada.");
    } catch (cause: unknown) {
      toast.error(cause instanceof Error ? cause.message : "No se pudo guardar el acta.");
    } finally {
      setSaving(false);
    }
  };

  const addStakeholder = async () => {
    if (!newStakeholder.display_name.trim() && !newStakeholder.role_title.trim()) {
      toast.error("Indica un nombre o cargo para registrar al interesado.");
      return;
    }
    setSaving(true);
    try {
      const created = await apiFetch<Stakeholder>(`/projects/${projectId}/stakeholders`, {
        method: "POST",
        body: JSON.stringify(newStakeholder),
      });
      setStakeholders(current => [...current, created]);
      setNewStakeholder({ display_name: "", role_title: "", organization_or_ministry: "", power_level: 3, interest_level: 3, engagement_level: "neutral", management_strategy: "" });
      toast.success("Interesado agregado a la matriz.");
    } catch (cause: unknown) {
      toast.error(cause instanceof Error ? cause.message : "No se pudo agregar el interesado.");
    } finally {
      setSaving(false);
    }
  };

  const updateStakeholder = async (id: string, patch: Partial<Stakeholder>) => {
    try {
      const updated = await apiFetch<Stakeholder>(`/projects/${projectId}/stakeholders/${id}`, {
        method: "PATCH",
        body: JSON.stringify(patch),
      });
      setStakeholders(current => current.map(item => item.id === id ? updated : item));
    } catch (cause: unknown) {
      toast.error(cause instanceof Error ? cause.message : "No se pudo actualizar el interesado.");
    }
  };

  const removeStakeholder = async (id: string) => {
    try {
      await apiFetch<void>(`/projects/${projectId}/stakeholders/${id}`, { method: "DELETE" });
      setStakeholders(current => current.filter(item => item.id !== id));
      setConfirmRemoval(null);
      toast.success("Interesado retirado de la matriz.");
    } catch (cause: unknown) {
      toast.error(cause instanceof Error ? cause.message : "No se pudo retirar el interesado.");
    }
  };

  const finalizeClosure = async () => {
    setSaving(true);
    try {
      const result = await apiFetch<Closure>(`/projects/${projectId}/closure/finalize`, {
        method: "POST",
        body: JSON.stringify(closure),
      });
      setClosure({ ...emptyClosure, ...result });
      toast.success("Cierre formal registrado con sus lecciones aprendidas.");
    } catch (cause: unknown) {
      toast.error(cause instanceof Error ? cause.message : "No se pudo finalizar el cierre.");
    } finally {
      setSaving(false);
    }
  };

  const setLesson = (index: number, field: keyof Lesson, value: string) => {
    setClosure(current => ({
      ...current,
      lessons_learned: current.lessons_learned.map((lesson, lessonIndex) => lessonIndex === index ? { ...lesson, [field]: value } : lesson),
    }));
  };

  const variance = (Number(closure.final_bac) || 0) - (Number(closure.final_ac) || 0);

  return (
    <RightPanel
      open={isOpen}
      onClose={onClose}
      title="Gobernanza PMI del proyecto"
      subtitle="Acta de Constitución · Interesados · Cierre formal"
      width="w-full sm:max-w-3xl"
      contentClassName="bg-[hsl(var(--surface-1))]"
    >
      <div className="flex h-full min-h-0 flex-col">
        <div role="tablist" aria-label="Gobernanza PMI" className="flex shrink-0 gap-1 overflow-x-auto border-b border-[hsl(var(--border))] p-3">
          {([
            ["charter", "Acta de Constitución"],
            ["stakeholders", "Matriz de Interesados"],
            ["closure", "Cierre y Lecciones"],
          ] as const).map(([key, label]) => (
            <button key={key} type="button" role="tab" aria-selected={tab === key} onClick={() => setTab(key)} className={clsx("shrink-0 rounded-lg px-3 py-2 text-xs font-semibold", tab === key ? "bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))]" : "text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))]")}>{label}</button>
          ))}
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto p-4 sm:p-6">
          {loading ? <div role="status" aria-label="Cargando gobernanza" className="space-y-3"><div className="h-6 animate-pulse rounded bg-[hsl(var(--surface-2))]" /><div className="h-24 animate-pulse rounded bg-[hsl(var(--surface-2))]" /><div className="h-24 animate-pulse rounded bg-[hsl(var(--surface-2))]" /></div> : error ? <div role="alert" className="rounded-lg border border-[hsl(var(--border))] p-4 text-sm text-[hsl(var(--text-secondary))]"><p>{error}</p><button type="button" onClick={() => void loadGovernance()} className="mt-3 rounded-md border border-[hsl(var(--border))] px-3 py-2">Reintentar</button></div> : <>
            {tab === "charter" && <section aria-label="Acta de Constitución" className="space-y-4">
              <p className="text-sm text-[hsl(var(--text-secondary))]">Define el propósito, autorización y límites de alto nivel del proyecto.</p>
              <label className={labelClass}>Sponsor (UUID de Persona)<input className={fieldClass} value={charter.sponsor_id ?? ""} onChange={event => setCharter(current => ({ ...current, sponsor_id: event.target.value || null }))} placeholder="UUID de persona" /></label>
              <label className={labelClass}>Caso de negocio<textarea className={fieldClass} rows={3} value={charter.business_case} onChange={event => setCharter(current => ({ ...current, business_case: event.target.value }))} /></label>
              <label className={labelClass}>Justificación estratégica<textarea className={fieldClass} rows={3} value={charter.strategic_justification} onChange={event => setCharter(current => ({ ...current, strategic_justification: event.target.value }))} /></label>
              <div className="grid gap-3 sm:grid-cols-2">
                <label className={labelClass}>Enfoque de desarrollo<select className={fieldClass} value={charter.development_approach} onChange={event => setCharter(current => ({ ...current, development_approach: event.target.value as ProjectDevelopmentApproach }))}><option value="predictive">Predictivo</option><option value="agile">Ágil</option><option value="hybrid">Híbrido</option></select></label>
                <label className={labelClass}>Tipología PMO<select className={fieldClass} value={charter.pmo_type} onChange={event => setCharter(current => ({ ...current, pmo_type: event.target.value as ProjectPMOType }))}><option value="supportive">De apoyo</option><option value="controlling">De control</option><option value="directive">Directiva</option></select></label>
              </div>
              {([
                ["measurable_objectives", "Objetivos medibles"],
                ["key_assumptions", "Supuestos clave"],
                ["key_constraints", "Restricciones clave"],
                ["high_level_risks", "Riesgos de alto nivel"],
              ] as const).map(([key, label]) => <label key={key} className={labelClass}>{label}<textarea className={fieldClass} rows={3} value={arrayField(charter[key])} onChange={event => setCharter(current => ({ ...current, [key]: parseArray(event.target.value) }))} placeholder="Un elemento por línea" /></label>)}
              <label className={labelClass}>Presupuesto preliminar<input className={fieldClass} type="number" min="0" step="0.01" value={charter.preliminary_budget ?? ""} onChange={event => setCharter(current => ({ ...current, preliminary_budget: event.target.value ? Number(event.target.value) : null }))} /></label>
              {charter.charter_status === "authorized" && <p className="rounded-lg border border-[hsl(var(--success)/0.35)] bg-[hsl(var(--success)/0.1)] p-3 text-sm text-[hsl(var(--success-text))]">Autorizada {charter.authorized_at ? `el ${new Date(charter.authorized_at).toLocaleString()}` : "formalmente"}.</p>}
              <div className="flex flex-wrap gap-2"><button type="button" disabled={saving || charter.charter_status === "authorized"} onClick={() => void saveCharter(false)} className="inline-flex items-center gap-2 rounded-lg border border-[hsl(var(--border))] px-4 py-2 text-sm font-semibold disabled:opacity-50"><Save size={16} />Guardar borrador</button><button type="button" disabled={saving || charter.charter_status === "authorized"} onClick={() => void saveCharter(true)} className="inline-flex items-center gap-2 rounded-lg bg-[hsl(var(--primary))] px-4 py-2 text-sm font-semibold text-[hsl(var(--primary-foreground))] disabled:opacity-50"><Check size={16} />Autorizar formalmente</button></div>
            </section>}

            {tab === "stakeholders" && <section aria-label="Matriz de Interesados" className="space-y-4">
              <p className="text-sm text-[hsl(var(--text-secondary))]">El cuadrante se calcula automáticamente con poder e interés (escala 1–5).</p>
              <div className="grid grid-cols-2 gap-2 text-center text-xs"><span className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] p-3">Mantener satisfechos<br /><b>Poder alto · Interés bajo</b></span><span className="rounded-lg border border-[hsl(var(--primary)/0.35)] bg-[hsl(var(--primary)/0.08)] p-3">Gestionar de cerca<br /><b>Poder alto · Interés alto</b></span><span className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] p-3">Monitorear<br /><b>Poder bajo · Interés bajo</b></span><span className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] p-3">Mantener informados<br /><b>Poder bajo · Interés alto</b></span></div>
              <div className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-4"><h3 className="mb-3 flex items-center gap-2 text-sm font-bold"><Users size={16} />Agregar interesado</h3><div className="grid gap-3 sm:grid-cols-2"><label className={labelClass}>Nombre<input className={fieldClass} value={newStakeholder.display_name} onChange={event => setNewStakeholder(current => ({ ...current, display_name: event.target.value }))} /></label><label className={labelClass}>Cargo / rol<input className={fieldClass} value={newStakeholder.role_title} onChange={event => setNewStakeholder(current => ({ ...current, role_title: event.target.value }))} /></label><label className={labelClass}>Organización / ministerio<input className={fieldClass} value={newStakeholder.organization_or_ministry} onChange={event => setNewStakeholder(current => ({ ...current, organization_or_ministry: event.target.value }))} /></label><label className={labelClass}>Estrategia de gestión<input className={fieldClass} value={newStakeholder.management_strategy} onChange={event => setNewStakeholder(current => ({ ...current, management_strategy: event.target.value }))} /></label><label className={labelClass}>Poder (1–5)<select className={fieldClass} value={newStakeholder.power_level} onChange={event => setNewStakeholder(current => ({ ...current, power_level: Number(event.target.value) }))}>{[1,2,3,4,5].map(value => <option key={value}>{value}</option>)}</select></label><label className={labelClass}>Interés (1–5)<select className={fieldClass} value={newStakeholder.interest_level} onChange={event => setNewStakeholder(current => ({ ...current, interest_level: Number(event.target.value) }))}>{[1,2,3,4,5].map(value => <option key={value}>{value}</option>)}</select></label><label className={labelClass}>Compromiso<select className={fieldClass} value={newStakeholder.engagement_level} onChange={event => setNewStakeholder(current => ({ ...current, engagement_level: event.target.value as Engagement }))}>{["unaware", "resistant", "neutral", "supportive", "leading"].map(value => <option key={value} value={value}>{value}</option>)}</select></label></div><button type="button" disabled={saving} onClick={() => void addStakeholder()} className="mt-3 inline-flex items-center gap-2 rounded-lg bg-[hsl(var(--primary))] px-4 py-2 text-sm font-semibold text-[hsl(var(--primary-foreground))] disabled:opacity-50"><Plus size={16} />Agregar</button></div>
              {stakeholders.length === 0 ? <p className="rounded-lg border border-dashed border-[hsl(var(--border))] p-6 text-center text-sm text-[hsl(var(--text-secondary))]">Aún no hay interesados registrados.</p> : <ul className="space-y-3">{stakeholders.map(person => <li key={person.id} className="rounded-xl border border-[hsl(var(--border))] p-4"><div className="flex items-start justify-between gap-3"><div><h3 className="text-sm font-bold">{person.display_name || person.role_title || "Interesado"}</h3><p className="text-xs text-[hsl(var(--text-secondary))]">{person.role_title}{person.organization_or_ministry ? ` · ${person.organization_or_ministry}` : ""}</p></div><span className="rounded-full bg-[hsl(var(--surface-2))] px-2 py-1 text-xs">{person.quadrant.replaceAll("_", " ")}</span></div><div className="mt-3 grid gap-3 sm:grid-cols-3"><label className={labelClass}>Poder<select className={fieldClass} value={person.power_level} onChange={event => void updateStakeholder(person.id, { power_level: Number(event.target.value) })}>{[1,2,3,4,5].map(value => <option key={value}>{value}</option>)}</select></label><label className={labelClass}>Interés<select className={fieldClass} value={person.interest_level} onChange={event => void updateStakeholder(person.id, { interest_level: Number(event.target.value) })}>{[1,2,3,4,5].map(value => <option key={value}>{value}</option>)}</select></label><label className={labelClass}>Compromiso<select className={fieldClass} value={person.engagement_level} onChange={event => void updateStakeholder(person.id, { engagement_level: event.target.value as Engagement })}>{["unaware", "resistant", "neutral", "supportive", "leading"].map(value => <option key={value} value={value}>{value}</option>)}</select></label></div>{confirmRemoval === person.id ? <div className="mt-3 flex items-center gap-2 text-xs"><span>¿Retirar a {person.display_name || "este interesado"}?</span><button type="button" onClick={() => void removeStakeholder(person.id)} className="rounded border border-[hsl(var(--destructive))] px-2 py-1 text-[hsl(var(--destructive))]">Confirmar</button><button type="button" onClick={() => setConfirmRemoval(null)} className="rounded border border-[hsl(var(--border))] px-2 py-1">Cancelar</button></div> : <button type="button" onClick={() => setConfirmRemoval(person.id)} className="mt-3 inline-flex items-center gap-1 text-xs text-[hsl(var(--destructive))]"><Trash2 size={14} />Retirar</button>}</li>)}</ul>}
            </section>}

            {tab === "closure" && <section aria-label="Cierre formal" className="space-y-4">
              {closure.closure_status === "closed" ? <div role="status" className="rounded-lg border border-[hsl(var(--success)/0.35)] bg-[hsl(var(--success)/0.1)] p-4 text-sm text-[hsl(var(--success-text))]">Proyecto cerrado {closure.closed_at ? `el ${new Date(closure.closed_at).toLocaleString()}` : "formalmente"}.</div> : <p className="text-sm text-[hsl(var(--text-secondary))]">Completa la aceptación, conciliación financiera y entrega antes de formalizar el cierre.</p>}
              <label className="flex items-center gap-3 rounded-lg border border-[hsl(var(--border))] p-3 text-sm"><input type="checkbox" checked={closure.deliverables_accepted_verified} disabled={closure.closure_status === "closed"} onChange={event => setClosure(current => ({ ...current, deliverables_accepted_verified: event.target.checked }))} />Entregables aceptados y verificados</label>
              <label className="flex items-center gap-3 rounded-lg border border-[hsl(var(--border))] p-3 text-sm"><input type="checkbox" checked={closure.financial_reconciliation_completed} disabled={closure.closure_status === "closed"} onChange={event => setClosure(current => ({ ...current, financial_reconciliation_completed: event.target.checked }))} />Conciliación financiera completada</label>
              <div className="grid gap-3 sm:grid-cols-3">{([["final_bac", "BAC final"], ["final_ac", "AC final"]] as const).map(([key, label]) => <label key={key} className={labelClass}>{label}<input className={fieldClass} type="number" min="0" step="0.01" disabled={closure.closure_status === "closed"} value={closure[key] ?? ""} onChange={event => setClosure(current => ({ ...current, [key]: event.target.value ? Number(event.target.value) : null, final_variance: key === "final_bac" ? (event.target.value ? Number(event.target.value) : 0) - (Number(current.final_ac) || 0) : (Number(current.final_bac) || 0) - (event.target.value ? Number(event.target.value) : 0) }))} /></label>)}<div className="rounded-lg border border-[hsl(var(--border))] p-3"><span className={labelClass}>Variación BAC − AC</span><p aria-label="Variación final" className="text-lg font-bold">{closure.final_variance ?? variance}</p></div></div>
              <label className={labelClass}>Entrega operativa a (sede / ministerio)<input className={fieldClass} disabled={closure.closure_status === "closed"} value={closure.operational_handover_to ?? ""} onChange={event => setClosure(current => ({ ...current, operational_handover_to: event.target.value }))} /></label>
              <div className="flex items-center justify-between gap-3"><h3 className="text-sm font-bold">Lecciones aprendidas</h3><button type="button" disabled={closure.closure_status === "closed"} onClick={() => setClosure(current => ({ ...current, lessons_learned: [...current.lessons_learned, { category: "", what_worked: "", what_failed: "", recommendation: "" }] }))} className="inline-flex items-center gap-1 rounded-lg border border-[hsl(var(--border))] px-3 py-2 text-xs"><Plus size={14} />Agregar lección</button></div>
              {closure.lessons_learned.length === 0 && <p className="rounded-lg border border-dashed border-[hsl(var(--border))] p-5 text-center text-sm text-[hsl(var(--text-secondary))]">Registra aprendizajes que ayuden a futuros proyectos.</p>}
              {closure.lessons_learned.map((lesson, index) => <fieldset key={index} className="space-y-3 rounded-xl border border-[hsl(var(--border))] p-4"><legend className="px-1 text-xs font-semibold">Lección {index + 1}</legend>{([["category", "Categoría"], ["what_worked", "Qué funcionó"], ["what_failed", "Qué falló"], ["recommendation", "Recomendación"]] as const).map(([field, label]) => <label key={field} className={labelClass}>{label}<textarea className={fieldClass} rows={field === "category" ? 1 : 2} disabled={closure.closure_status === "closed"} value={lesson[field]} onChange={event => setLesson(index, field, event.target.value)} /></label>)}</fieldset>)}
              <button type="button" disabled={saving || closure.closure_status === "closed" || !closure.deliverables_accepted_verified || !closure.financial_reconciliation_completed} onClick={() => void finalizeClosure()} className="inline-flex items-center gap-2 rounded-lg bg-[hsl(var(--primary))] px-4 py-2 text-sm font-semibold text-[hsl(var(--primary-foreground))] disabled:cursor-not-allowed disabled:opacity-50"><ClipboardCheck size={16} />{saving ? "Finalizando…" : "Finalizar cierre formal"}</button>
            </section>}
          </>}
        </div>
      </div>
    </RightPanel>
  );
}
