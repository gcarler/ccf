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


const TRIGGER_META: Record<
  string,
  { icon: LucideIcon; label: string; color: string; bg: string }
> = {
  overload: {
    icon: ShieldAlert,
    label: "Carga alta de tareas",
    color: "text-[hsl(var(--destructive))]",
    bg: "bg-[hsl(var(--destructive)/0.15)]",
  },
  deadline: {
    icon: Bell,
    label: "Tarea cerca de su deadline",
    color: "text-[hsl(var(--primary))]",
    bg: "bg-[hsl(var(--primary)/0.15)]",
  },
  stale: {
    icon: Clock,
    label: "Sin cambios por varios días",
    color: "text-[hsl(var(--warning))]",
    bg: "bg-[hsl(var(--warning)/0.15)]",
  },
  weekly_summary: {
    icon: Bot,
    label: "Resumen periódico",
    color: "text-[hsl(var(--primary))]",
    bg: "bg-[hsl(var(--primary)/0.15)]",
  },
  manual: {
    icon: Sparkles,
    label: "Disparador manual",
    color: "text-[hsl(var(--primary))]",
    bg: "bg-[hsl(var(--primary)/0.15)]",
  },
};

function getTriggerMeta(triggerType: string) {
  return (
    TRIGGER_META[triggerType] ?? {
      icon: Sparkles,
      label: triggerType,
      color: "text-[hsl(var(--primary))]",
      bg: "bg-[hsl(var(--primary)/0.15)]",
    }
  );
}

import { AutomationRuleDrawer, type AutomationRule } from "./AutomationRuleDrawer";

export default function AutomationsPage() {
  const { token, loading: authLoading } = useAuth();
  const [rules, setRules] = useState<AutomationRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [editingRule, setEditingRule] = useState<AutomationRule | null>(null);

  useEffect(() => {
    if (authLoading) return;
    const controller = new AbortController();
    fetchRules(controller.signal);
    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authLoading, token]);

  const fetchRules = async (signal?: AbortSignal) => {
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
        cache: "no-store",
        signal,
      });
      setRules(data?.items ?? []);
    } catch {
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
    } catch {
      toast.error("Error toggling automation:");
    }
  };

  const handleOpenCreate = () => {
    setEditingRule(null);
    setIsDrawerOpen(true);
  };

  const handleOpenEdit = (rule: AutomationRule) => {
    setEditingRule(rule);
    setIsDrawerOpen(true);
  };

  const handleRuleSaved = (saved: AutomationRule) => {
    setRules((prev) => {
      const idx = prev.findIndex((r) => r.id === saved.id);
      if (idx >= 0) {
        const copy = [...prev];
        copy[idx] = saved;
        return copy;
      }
      return [saved, ...prev];
    });
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
            <div className="rounded-lg border border-[hsl(var(--warning)/0.3)] bg-[hsl(var(--warning)/0.1)] p-3 text-[hsl(var(--warning))]">
              <p className="text-xs font-bold uppercase tracking-wide">{error}</p>
            </div>
          )}
          {/* Sub-header */}
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <div className="size-7 rounded-lg bg-[hsl(var(--primary)/0.1)] flex items-center justify-center">
                  <Sparkles size={14} className="text-[hsl(var(--primary))]" />
                </div>
                <span className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--primary))]">
                  Motor Optimus 3.0
                </span>
              </div>
              <h1 className="text-xl font-bold tracking-tight text-[hsl(var(--foreground))] leading-none">
                Automatizaciones
              </h1>
              <p className="text-sm text-[hsl(var(--muted-foreground))] mt-0.5 font-medium">
                Configura cómo el sistema reacciona a los desafíos de tu ministerio.
              </p>
            </div>
            <button
              onClick={handleOpenCreate}
              className="flex items-center gap-2 px-4 py-1.5 bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] rounded-lg text-xs font-semibold uppercase tracking-wide shadow-xl hover:bg-[hsl(var(--primary))]/90 active:scale-95 transition-all"
            >
              <Plus size={13} /> Nueva Regla
            </button>
          </div>

          {/* Active count */}
          <div className="flex items-center gap-3">
            <span className="px-2.5 py-1 bg-[hsl(var(--success)/0.15)] text-[hsl(var(--success,var(--primary)))] rounded-full text-2xs font-semibold uppercase tracking-wide border border-[hsl(var(--success)/0.3)]">
              {rules.filter((r) => r.is_active).length} activas
            </span>
            <span className="px-2.5 py-1 bg-[hsl(var(--surface-2))] text-[hsl(var(--muted-foreground))] rounded-full text-2xs font-semibold uppercase tracking-wide border border-[hsl(var(--border))]">
              {rules.filter((r) => !r.is_active).length} inactivas
            </span>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-12 text-[hsl(var(--muted-foreground))]">
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
                        ? "bg-[hsl(var(--surface-1))] border-[hsl(var(--border))] shadow-sm hover:shadow-lg hover:border-[hsl(var(--primary)/0.5)]"
                        : "bg-[hsl(var(--surface-1))] border-[hsl(var(--border))] opacity-60"
                    )}
                  >
                    <div className="flex items-start justify-between mb-4">
                      <div
                        className={clsx(
                          "size-10 rounded-md flex items-center justify-center border shrink-0 border-[hsl(var(--border))]",
                          meta.bg
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
                            className="text-[hsl(var(--muted-foreground))]"
                          />
                        )}
                      </button>
                    </div>

                    <div className="space-y-1 mb-4">
                      <h3 className="text-sm font-bold text-[hsl(var(--foreground))] leading-tight">
                        {rule.name}
                      </h3>
                      <p className="text-xs font-medium text-[hsl(var(--muted-foreground))] uppercase tracking-wider">
                        {meta.label}
                      </p>
                    </div>

                    <div className="pt-3 border-t border-[hsl(var(--border))] flex items-center justify-between">
                      <button
                        onClick={() => handleOpenEdit(rule)}
                        className="text-2xs font-semibold uppercase text-[hsl(var(--primary))] tracking-wide flex items-center gap-1.5 hover:underline"
                      >
                        Configurar lógica <ArrowRight size={11} />
                      </button>
                      {!rule.is_active && (
                        <span className="px-2 py-0.5 bg-[hsl(var(--surface-2))] text-[hsl(var(--muted-foreground))] rounded-md text-2xs font-semibold uppercase tracking-wide">
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
                onClick={handleOpenCreate}
                className="flex flex-col items-center justify-center p-3 rounded-lg border-2 border-dashed border-[hsl(var(--border))] text-center gap-2 group cursor-pointer hover:border-[hsl(var(--primary))] hover:bg-[hsl(var(--surface-2))] transition-all min-h-[100px]"
              >
                <div className="size-10 rounded-md bg-[hsl(var(--surface-1))] shadow-sm border border-[hsl(var(--border))] flex items-center justify-center text-[hsl(var(--muted-foreground))] group-hover:text-[hsl(var(--primary))] group-hover:border-[hsl(var(--primary))] transition-all">
                  <Plus size={18} />
                </div>
                <div>
                  <h4 className="text-base font-bold text-[hsl(var(--foreground))] group-hover:text-[hsl(var(--primary))] transition-colors">
                    Crear Regla
                  </h4>
                  <p className="text-2xs font-bold text-[hsl(var(--muted-foreground))] uppercase tracking-wide mt-0.5">
                    Constructor Trigger → Action
                  </p>
                </div>
              </motion.div>
            </div>
          ) : null}
        </div>

        {/* Drawer Lateral Deslizante */}
        <AutomationRuleDrawer
          isOpen={isDrawerOpen}
          onClose={() => setIsDrawerOpen(false)}
          rule={editingRule}
          onSaved={handleRuleSaved}
        />
      </div>
    </ProjectsShell>
  );
}
