"use client";

import React, { useEffect, useState } from "react";
import {
  Bot,
  Bell,
  Clock,
  ShieldAlert,
  ToggleLeft,
  ToggleRight,
  ArrowRight,
  Sparkles,
  Plus,
  Loader2,
  LucideIcon,
} from "lucide-react";
import { motion } from "framer-motion";
import clsx from "clsx";
import ProjectsShell from "@/components/projects/ProjectsShell";
import { apiFetch } from "@/lib/http";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";

interface AutomationRule {
  id: string;
  name: string;
  trigger_type: string;
  action_type?: string | null;
  is_active: boolean;
  last_run?: string | null;
}

const TRIGGER_META: Record<
  string,
  { icon: LucideIcon; label: string; color: string; bg: string }
> = {
  overload: {
    icon: ShieldAlert,
    label: "Carga alta de tareas",
    color: "text-rose-500",
    bg: "bg-rose-50 dark:bg-rose-900/20",
  },
  deadline: {
    icon: Bell,
    label: "Tarea cerca de su deadline",
    color: "text-[hsl(var(--primary))]",
    bg: "bg-blue-50 dark:bg-blue-900/20",
  },
  stale: {
    icon: Clock,
    label: "Sin cambios por varios días",
    color: "text-amber-500",
    bg: "bg-amber-50 dark:bg-amber-900/20",
  },
  weekly_summary: {
    icon: Bot,
    label: "Resumen periódico",
    color: "text-[hsl(var(--primary))]",
    bg: "bg-blue-50 dark:bg-blue-900/20",
  },
  manual: {
    icon: Sparkles,
    label: "Disparador manual",
    color: "text-[hsl(var(--primary))]",
    bg: "bg-blue-50 dark:bg-blue-900/20",
  },
};

function getTriggerMeta(triggerType: string) {
  return (
    TRIGGER_META[triggerType] ?? {
      icon: Sparkles,
      label: triggerType,
      color: "text-[hsl(var(--primary))]",
      bg: "bg-blue-50 dark:bg-blue-900/20",
    }
  );
}

export default function AutomationsPage() {
  const { token, loading: authLoading } = useAuth();
  const [rules, setRules] = useState<AutomationRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!authLoading) fetchRules();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authLoading, token]);

  const fetchRules = async () => {
    if (!token) {
      setLoading(false);
      setRules([]);
      setError('Debes iniciar sesión para ver las automatizaciones.');
      return;
    }
    setLoading(true);
    try {
      setError(null);
      const data = await apiFetch<{ items: AutomationRule[]; total: number }>("/admin/automations", {
        token,
      });
      setRules(data?.items ?? []);
    } catch (err) {
      setRules([]);
      setError('No se pudieron cargar las automatizaciones.');
      toast.error("Error loading automations:");
    } finally {
      setLoading(false);
    }
  };

  const toggleRule = async (id: string, active: boolean) => {
    if (!token) {
      setError('Debes iniciar sesión para modificar automatizaciones.');
      return;
    }
    try {
      await apiFetch(`/admin/automations/${id}`, {
        method: "PATCH",
        token,
        body: { is_active: !active },
      });
      setRules((prev) =>
        prev.map((r) => (r.id === id ? { ...r, is_active: !active } : r))
      );
    } catch (err) {
      toast.error("Error toggling automation:");
    }
  };

  const handleCreate = async () => {
    if (!token) {
      setError('Debes iniciar sesión para crear automatizaciones.');
      return;
    }
    setCreating(true);
    try {
      const newRule = await apiFetch<AutomationRule>("/admin/automations", {
        method: "POST",
        token,
        body: {
          name: "Nueva Regla",
          trigger_type: "manual",
          action_type: "notification",
          is_active: true,
        },
      });
      setRules((prev) => [newRule, ...prev]);
    } catch (err) {
      toast.error("Error creating automation:");
    } finally {
      setCreating(false);
    }
  };

  return (
    <ProjectsShell
      breadcrumbs={[
        { label: "Proyectos", icon: Sparkles },
        { label: "Automation", icon: Sparkles },
      ]}
    >
      <div className="flex flex-col h-full font-display">
        <div className="w-full mx-auto p-3 space-y-3 pb-4">
          {error && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-amber-900 dark:border-amber-500/20 dark:bg-amber-500/10 dark:text-amber-200">
              <p className="text-[11px] font-bold uppercase tracking-wide">{error}</p>
            </div>
          )}
          {/* Sub-header */}
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <div className="size-7 rounded-lg bg-blue-50 dark:bg-blue-900/30 flex items-center justify-center">
                  <Sparkles size={14} className="text-[hsl(var(--primary))]" />
                </div>
                <span className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--primary))]">
                  Motor Optimus 3.0
                </span>
              </div>
              <h1 className="text-xl font-bold tracking-tight text-[hsl(var(--text-primary))] dark:text-white leading-none">
                Automatizaciones
              </h1>
              <p className="text-[12px] text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] mt-0.5 font-medium">
                Configura cómo el sistema reacciona a los desafíos de tu ministerio.
              </p>
            </div>
            <button
              onClick={handleCreate}
              disabled={creating}
              className="flex items-center gap-2 px-4 py-1.5 bg-[hsl(var(--primary))] text-white rounded-lg text-[11px] font-semibold uppercase tracking-wide shadow-xl shadow-blue-500/20 hover:bg-[hsl(var(--primary))] active:scale-95 transition-all disabled:opacity-60"
            >
              {creating ? (
                <Loader2 size={13} className="animate-spin" />
              ) : (
                <Plus size={13} />
              )}{" "}
              Nueva Regla
            </button>
          </div>

          {/* Active count */}
          <div className="flex items-center gap-3">
            <span className="px-2.5 py-1 bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400 rounded-full text-[10px] font-semibold uppercase tracking-wide border border-emerald-200 dark:border-emerald-500/20">
              {rules.filter((r) => r.is_active).length} activas
            </span>
            <span className="px-2.5 py-1 bg-[hsl(var(--surface-2))] dark:bg-white/5 text-[hsl(var(--text-secondary))] rounded-full text-[10px] font-semibold uppercase tracking-wide border border-[hsl(var(--border))] dark:border-white/10">
              {rules.filter((r) => !r.is_active).length} inactivas
            </span>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-12 text-[hsl(var(--text-secondary))]">
              <Loader2 size={24} className="animate-spin mr-2" />
              Cargando automatizaciones...
            </div>
          ) : !error ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {rules.map((rule, idx) => {
                const meta = getTriggerMeta(rule.trigger_type);
                const Icon = meta.icon;
                return (
                  <motion.div
                    key={rule.id}
                    initial={{ opacity: 0, y: 16 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: idx * 0.07 }}
                    className={clsx(
                      "group p-3 rounded-lg border transition-all",
                      rule.is_active
                        ? "bg-[hsl(var(--bg-primary))] dark:bg-[#1a1b1e] border-[hsl(var(--border))] dark:border-white/[0.06] shadow-sm hover:shadow-lg hover:border-blue-200 dark:hover:border-blue-500/20"
                        : "bg-[hsl(var(--surface-1))] dark:bg-white/[0.02] border-[hsl(var(--border))] dark:border-white/[0.04] opacity-60"
                    )}
                  >
                    <div className="flex items-start justify-between mb-4">
                      <div
                        className={clsx(
                          "size-10 rounded-md flex items-center justify-center border shrink-0",
                          meta.bg,
                          meta.color
                            .replace("text-", "border-")
                            .replace("500", "200") + " dark:border-opacity-20"
                        )}
                      >
                        <Icon size={18} className={meta.color} />
                      </div>
                      <button
                        onClick={() => toggleRule(rule.id, rule.is_active)}
                        className="transition-transform active:scale-90 shrink-0"
                        aria-label={
                          rule.is_active ? "Desactivar regla" : "Activar regla"
                        }
                      >
                        {rule.is_active ? (
                          <ToggleRight
                            size={32}
                            className="text-[hsl(var(--primary))]"
                          />
                        ) : (
                          <ToggleLeft
                            size={32}
                            className="text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]"
                          />
                        )}
                      </button>
                    </div>

                    <div className="space-y-1 mb-4">
                      <h3 className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-white leading-tight">
                        {rule.name}
                      </h3>
                      <p className="text-[11px] font-medium text-[hsl(var(--text-secondary))] uppercase tracking-wider">
                        {meta.label}
                      </p>
                    </div>

                    <div className="pt-3 border-t border-[hsl(var(--border))] dark:border-white/5 flex items-center justify-between">
                      <button className="text-[10px] font-semibold uppercase text-[hsl(var(--primary))] tracking-wide flex items-center gap-1.5 hover:underline">
                        Configurar lógica <ArrowRight size={11} />
                      </button>
                      {!rule.is_active && (
                        <span className="px-2 py-0.5 bg-[hsl(var(--surface-2))] dark:bg-white/5 text-[hsl(var(--text-secondary))] rounded-md text-[9px] font-semibold uppercase tracking-wide">
                          Inactivo
                        </span>
                      )}
                    </div>
                  </motion.div>
                );
              })}

              {/* Add new rule card */}
              <motion.div
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: rules.length * 0.07 }}
                onClick={handleCreate}
                className="flex flex-col items-center justify-center p-3 rounded-lg border-2 border-dashed border-[hsl(var(--border))] dark:border-white/10 text-center gap-2 group cursor-pointer hover:border-blue-400 dark:hover:border-blue-500/40 hover:bg-blue-50/50 dark:hover:bg-blue-900/10 transition-all min-h-[100px]"
              >
                <div className="size-10 rounded-md bg-[hsl(var(--bg-primary))] dark:bg-white/5 shadow-sm border border-[hsl(var(--border))] dark:border-white/10 flex items-center justify-center text-[hsl(var(--text-secondary))] group-hover:text-[hsl(var(--primary))] group-hover:border-blue-200 dark:group-hover:border-blue-500/30 transition-all">
                  <Plus size={18} />
                </div>
                <div>
                  <h4 className="text-[13px] font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] group-hover:text-[hsl(var(--primary))] transition-colors">
                    Crear Regla
                  </h4>
                  <p className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide mt-0.5">
                    Expandir Inteligencia
                  </p>
                </div>
              </motion.div>
            </div>
          ) : null}
        </div>
      </div>
    </ProjectsShell>
  );
}
