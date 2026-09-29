"use client";

import React, { useState, useEffect, useCallback } from "react";
import { RightPanel } from "@/components/ui/RightPanel";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { apiFetch } from "@/lib/http";
import type { ProjectWorkloadSummary } from "@/types/projects";
import { Users, AlertOctagon, Scale, CheckCircle2, Clock, ChevronDown, ChevronUp, UserX, ExternalLink } from "lucide-react";

interface ProjectWorkloadDrawerProps {
  projectId: string;
  isOpen: boolean;
  onClose: () => void;
  onWorkloadUpdated?: () => void;
  onOpenTask?: (taskId: string) => void;
}

const CAPACITY_CONFIG = {
  overloaded: {
    label: "Sobrecargado",
    color: "hsl(var(--destructive))",
    bg: "hsl(var(--destructive) / 0.12)",
    border: "hsl(var(--destructive) / 0.35)",
    barColor: "hsl(var(--destructive))",
    icon: AlertOctagon,
  },
  balanced: {
    label: "Balanceado",
    color: "hsl(var(--primary))",
    bg: "hsl(var(--primary) / 0.12)",
    border: "hsl(var(--primary) / 0.35)",
    barColor: "hsl(var(--primary))",
    icon: Scale,
  },
  available: {
    label: "Disponible",
    color: "hsl(var(--success))",
    bg: "hsl(var(--success) / 0.12)",
    border: "hsl(var(--success) / 0.35)",
    barColor: "hsl(var(--success))",
    icon: CheckCircle2,
  },
};

export function ProjectWorkloadDrawer({
  projectId,
  isOpen,
  onClose,
  onWorkloadUpdated,
  onOpenTask,
}: ProjectWorkloadDrawerProps) {
  const { token } = useAuth();
  const { addToast } = useToast();

  const [summary, setSummary] = useState<ProjectWorkloadSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [reassigningTaskId, setReassigningTaskId] = useState<string | null>(null);
  const [expandedMembers, setExpandedMembers] = useState<Record<string, boolean>>({});

  const fetchWorkload = useCallback(async () => {
    if (!projectId || !token) return;
    setLoading(true);
    try {
      const data = await apiFetch<ProjectWorkloadSummary>(`/projects/${projectId}/workload`, { token });
      setSummary(data);
      // Expandir por defecto el primer colaborador y sin asignar
      if (data?.members?.length) {
        setExpandedMembers((prev) => ({
          ...prev,
          [data.members[0].persona_id || "unassigned"]: true,
          unassigned: true,
        }));
      }
    } catch {
      addToast("Error al cargar la carga de trabajo del equipo", "error");
    } finally {
      setLoading(false);
    }
  }, [projectId, token, addToast]);

  useEffect(() => {
    if (isOpen) {
      fetchWorkload();
    }
  }, [isOpen, fetchWorkload]);

  const toggleExpand = (key: string) => {
    setExpandedMembers((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const handleReassign = async (taskId: string, targetPersonaId: string | null) => {
    if (!taskId || !token) return;
    setReassigningTaskId(taskId);
    try {
      await apiFetch(`/projects/${projectId}/tasks/${taskId}/reassign`, {
        method: "PATCH",
        token,
        body: JSON.stringify({
          new_assignee_id: targetPersonaId || null,
        }),
      });

      const targetMember = summary?.members.find((m) => m.persona_id === targetPersonaId);
      const targetName = targetMember ? targetMember.name : "Sin Asignar";
      addToast(`Tarea reasignada a ${targetName}`, "success");
      fetchWorkload();
      onWorkloadUpdated?.();
    } catch {
      addToast("Error al reasignar la tarea", "error");
    } finally {
      setReassigningTaskId(null);
    }
  };

  const assignableMembers = summary?.members.filter((m) => m.persona_id !== null) || [];

  return (
    <RightPanel
      isOpen={isOpen}
      onClose={onClose}
      title="Capacidad de Equipo y Carga de Trabajo"
      description="Monitoreo de saturación operativa, balanceo de tareas y prevención de sobrecarga en el equipo ministerial."
      width="max-w-3xl"
    >
      <div className="space-y-6 pb-12">
        {/* RESUMEN DE CAPACIDAD */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div
            className="p-3.5 rounded-xl border flex flex-col justify-between"
            style={{
              backgroundColor: "hsl(var(--surface-2))",
              borderColor: "hsl(var(--border))",
            }}
          >
            <div className="flex items-center justify-between text-xs text-muted font-medium">
              <span>Equipo Ministerial</span>
              <Users className="w-4 h-4 opacity-70" />
            </div>
            <div className="text-2xl font-bold mt-2" style={{ color: "hsl(var(--text-main))" }}>
              {summary?.total_members ?? 0}
            </div>
            <div className="text-[11px] text-muted mt-1">
              {summary?.total_active_tasks ?? 0} tareas en curso
            </div>
          </div>

          <div
            className="p-3.5 rounded-xl border flex flex-col justify-between"
            style={{
              backgroundColor: "hsl(var(--destructive) / 0.08)",
              borderColor: "hsl(var(--destructive) / 0.25)",
            }}
          >
            <div className="flex items-center justify-between text-xs font-semibold" style={{ color: "hsl(var(--destructive))" }}>
              <span>Sobrecargados</span>
              <AlertOctagon className="w-4 h-4" />
            </div>
            <div className="text-2xl font-bold mt-2" style={{ color: "hsl(var(--destructive))" }}>
              {summary?.overloaded_members_count ?? 0}
            </div>
            <div className="text-[11px] font-medium mt-1" style={{ color: "hsl(var(--destructive) / 0.8)" }}>
              Requieren balanceo
            </div>
          </div>

          <div
            className="p-3.5 rounded-xl border flex flex-col justify-between"
            style={{
              backgroundColor: "hsl(var(--primary) / 0.08)",
              borderColor: "hsl(var(--primary) / 0.25)",
            }}
          >
            <div className="flex items-center justify-between text-xs font-semibold" style={{ color: "hsl(var(--primary))" }}>
              <span>Balanceados</span>
              <Scale className="w-4 h-4" />
            </div>
            <div className="text-2xl font-bold mt-2" style={{ color: "hsl(var(--primary))" }}>
              {summary?.balanced_members_count ?? 0}
            </div>
            <div className="text-[11px] font-medium mt-1" style={{ color: "hsl(var(--primary) / 0.8)" }}>
              Régimen óptimo
            </div>
          </div>

          <div
            className="p-3.5 rounded-xl border flex flex-col justify-between"
            style={{
              backgroundColor: "hsl(var(--success) / 0.08)",
              borderColor: "hsl(var(--success) / 0.25)",
            }}
          >
            <div className="flex items-center justify-between text-xs font-semibold" style={{ color: "hsl(var(--success))" }}>
              <span>Disponibles</span>
              <CheckCircle2 className="w-4 h-4" />
            </div>
            <div className="text-2xl font-bold mt-2" style={{ color: "hsl(var(--success))" }}>
              {summary?.available_members_count ?? 0}
            </div>
            <div className="text-[11px] font-medium mt-1" style={{ color: "hsl(var(--success) / 0.8)" }}>
              Capacidad libre
            </div>
          </div>
        </div>

        {/* ALERTA DE TAREAS SIN ASIGNAR */}
        {(summary?.unassigned_tasks_count ?? 0) > 0 && (
          <div
            className="p-3.5 rounded-xl border flex items-center justify-between gap-3"
            style={{
              backgroundColor: "hsl(var(--warning) / 0.08)",
              borderColor: "hsl(var(--warning) / 0.3)",
            }}
          >
            <div className="flex items-center gap-2.5">
              <UserX className="w-5 h-5 shrink-0" style={{ color: "hsl(var(--warning))" }} />
              <div>
                <span className="text-xs font-bold block" style={{ color: "hsl(var(--warning))" }}>
                  {summary?.unassigned_tasks_count} tarea(s) sin responsable asignado
                </span>
                <span className="text-[11px] text-muted">
                  Asigna estas tareas a miembros con disponibilidad para mantener el ritmo del proyecto.
                </span>
              </div>
            </div>
          </div>
        )}

        {/* LISTADO DE MIEMBROS Y MATRIZ DE SATURACIÓN */}
        <div className="space-y-4">
          <div className="flex items-center justify-between text-xs font-medium" style={{ color: "hsl(var(--text-muted))" }}>
            <span>Distribución de Carga por Responsable ({summary?.members?.length ?? 0})</span>
            <span>Escala estándar: 5 tareas activas = 100% de carga</span>
          </div>

          {loading ? (
            <div className="space-y-3 py-4">
              {[1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="h-28 rounded-xl animate-pulse"
                  style={{ backgroundColor: "hsl(var(--surface-2))" }}
                />
              ))}
            </div>
          ) : summary?.members?.length === 0 ? (
            <div
              className="p-8 text-center rounded-xl border"
              style={{
                backgroundColor: "hsl(var(--surface-1))",
                borderColor: "hsl(var(--border))",
              }}
            >
              <Users className="w-8 h-8 mx-auto mb-2 opacity-40" style={{ color: "hsl(var(--text-muted))" }} />
              <p className="text-sm font-medium" style={{ color: "hsl(var(--text-main))" }}>
                No hay miembros ni tareas en este proyecto
              </p>
            </div>
          ) : (
            summary?.members?.map((member) => {
              const memberKey = member.persona_id || "unassigned";
              const isExpanded = !!expandedMembers[memberKey];
              const capCfg = CAPACITY_CONFIG[member.capacity_status] || CAPACITY_CONFIG.available;
              const CapIcon = capCfg.icon;

              const isUnassigned = member.persona_id === null;

              return (
                <div
                  key={memberKey}
                  className="rounded-xl border transition-all"
                  style={{
                    backgroundColor: "hsl(var(--surface-1))",
                    borderColor: "hsl(var(--border))",
                  }}
                >
                  {/* CABECERA DEL MIEMBRO */}
                  <div className="p-4 space-y-3">
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-center gap-3">
                        {/* Avatar o Inicial */}
                        <div
                          className="w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm shrink-0"
                          style={{
                            backgroundColor: isUnassigned
                              ? "hsl(var(--surface-3))"
                              : "hsl(var(--primary) / 0.15)",
                            color: isUnassigned
                              ? "hsl(var(--text-muted))"
                              : "hsl(var(--primary))",
                          }}
                        >
                          {isUnassigned ? (
                            <UserX className="w-5 h-5" />
                          ) : member.avatar_url ? (
                            <img
                              src={member.avatar_url}
                              alt={member.name}
                              className="w-full h-full rounded-full object-cover"
                            />
                          ) : (
                            member.name.charAt(0).toUpperCase()
                          )}
                        </div>

                        <div>
                          <div className="flex items-center gap-2">
                            <h4
                              className="text-sm font-bold"
                              style={{ color: "hsl(var(--text-main))" }}
                            >
                              {member.name}
                            </h4>

                            {!isUnassigned && (
                              <span
                                className="text-[11px] font-bold px-2 py-0.5 rounded-full border inline-flex items-center gap-1"
                                style={{
                                  backgroundColor: capCfg.bg,
                                  color: capCfg.color,
                                  borderColor: capCfg.border,
                                }}
                              >
                                <CapIcon className="w-3 h-3" />
                                <span>{capCfg.label}</span>
                              </span>
                            )}
                          </div>

                          <div className="text-[11px] text-muted flex items-center gap-3 mt-0.5 flex-wrap">
                            <span>
                              <strong>{member.active_tasks}</strong> activas
                            </span>
                            <span>•</span>
                            <span>{member.completed_tasks} completadas</span>
                            {member.overdue_tasks > 0 && (
                              <>
                                <span>•</span>
                                <span
                                  className="font-bold inline-flex items-center gap-0.5"
                                  style={{ color: "hsl(var(--destructive))" }}
                                >
                                  <Clock className="w-3 h-3" />
                                  {member.overdue_tasks} vencida(s)
                                </span>
                              </>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Botón Plegar / Desplegar */}
                      <button
                        onClick={() => toggleExpand(memberKey)}
                        className="p-1.5 rounded-lg border text-muted hover:opacity-100 transition-colors flex items-center gap-1 text-xs"
                        style={{
                          backgroundColor: "hsl(var(--surface-2))",
                          borderColor: "hsl(var(--border))",
                        }}
                      >
                        <span className="text-[11px]">{member.tasks.length} tareas</span>
                        {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                      </button>
                    </div>

                    {/* BARRA DE SATURACIÓN / CAPACIDAD */}
                    {!isUnassigned && (
                      <div className="space-y-1">
                        <div className="flex items-center justify-between text-[11px]">
                          <span className="text-muted font-medium">Nivel de Carga</span>
                          <span className="font-bold" style={{ color: capCfg.color }}>
                            {member.workload_percent}%
                          </span>
                        </div>
                        <div
                          className="h-2 w-full rounded-full overflow-hidden"
                          style={{ backgroundColor: "hsl(var(--surface-2))" }}
                        >
                          <div
                            className="h-full rounded-full transition-all duration-300"
                            style={{
                              width: `${member.workload_percent}%`,
                              backgroundColor: capCfg.barColor,
                            }}
                          />
                        </div>
                      </div>
                    )}

                    {/* DISTRIBUCIÓN DE PRIORIDADES */}
                    <div className="flex items-center gap-2 pt-1 flex-wrap text-[11px]">
                      {member.urgent_tasks > 0 && (
                        <span
                          className="px-2 py-0.5 rounded-md font-semibold"
                          style={{
                            backgroundColor: "hsl(var(--destructive) / 0.12)",
                            color: "hsl(var(--destructive))",
                          }}
                        >
                          {member.urgent_tasks} urgentes
                        </span>
                      )}
                      {member.high_tasks > 0 && (
                        <span
                          className="px-2 py-0.5 rounded-md font-semibold"
                          style={{
                            backgroundColor: "hsl(28 90% 55% / 0.12)",
                            color: "hsl(28 90% 55%)",
                          }}
                        >
                          {member.high_tasks} altas
                        </span>
                      )}
                      {member.medium_tasks > 0 && (
                        <span
                          className="px-2 py-0.5 rounded-md"
                          style={{
                            backgroundColor: "hsl(var(--surface-2))",
                            color: "hsl(var(--text-muted))",
                          }}
                        >
                          {member.medium_tasks} medias
                        </span>
                      )}
                      {member.low_tasks > 0 && (
                        <span
                          className="px-2 py-0.5 rounded-md"
                          style={{
                            backgroundColor: "hsl(var(--surface-2))",
                            color: "hsl(var(--text-muted))",
                          }}
                        >
                          {member.low_tasks} bajas
                        </span>
                      )}
                    </div>
                  </div>

                  {/* LISTADO DE TAREAS EXPANDIBLE CON REASIGNACIÓN RÁPIDA */}
                  {isExpanded && (
                    <div
                      className="border-t p-3 space-y-2"
                      style={{
                        backgroundColor: "hsl(var(--surface-2) / 0.4)",
                        borderColor: "hsl(var(--border))",
                      }}
                    >
                      {member.tasks.length === 0 ? (
                        <p className="text-xs text-muted italic text-center py-2">
                          Sin tareas asignadas actualmente.
                        </p>
                      ) : (
                        member.tasks.map((task) => (
                          <div
                            key={task.id}
                            className="p-2.5 rounded-lg border flex items-center justify-between gap-3 text-xs"
                            style={{
                              backgroundColor: "hsl(var(--surface-1))",
                              borderColor: "hsl(var(--border))",
                            }}
                          >
                            <div className="space-y-0.5 min-w-0 flex-1">
                              <div className="flex items-center gap-1.5 flex-wrap">
                                <span
                                  className="w-2 h-2 rounded-full shrink-0"
                                  style={{
                                    backgroundColor:
                                      task.status === "completed"
                                        ? "hsl(var(--success))"
                                        : task.priority === "urgent"
                                        ? "hsl(var(--destructive))"
                                        : "hsl(var(--primary))",
                                  }}
                                />
                                <span
                                  className="font-medium truncate"
                                  style={{ color: "hsl(var(--text-main))" }}
                                >
                                  {task.title}
                                </span>
                                {task.is_overdue && (
                                  <span
                                    className="text-[10px] font-bold px-1.5 py-0.2 rounded"
                                    style={{
                                      backgroundColor: "hsl(var(--destructive) / 0.15)",
                                      color: "hsl(var(--destructive))",
                                    }}
                                  >
                                    Vencida
                                  </span>
                                )}
                              </div>
                              <div className="text-[10px] text-muted flex items-center gap-2">
                                <span>Estado: {task.status}</span>
                                <span>•</span>
                                <span>Prioridad: {task.priority}</span>
                              </div>
                            </div>

                            {/* REASIGNACIÓN RÁPIDA */}
                            <div className="flex items-center gap-1.5 shrink-0">
                              <select
                                disabled={reassigningTaskId === task.id}
                                value={member.persona_id || ""}
                                onChange={(e) =>
                                  handleReassign(task.id, e.target.value || null)
                                }
                                className="text-[11px] px-2 py-1 rounded border focus:outline-none cursor-pointer"
                                style={{
                                  backgroundColor: "hsl(var(--surface-2))",
                                  borderColor: "hsl(var(--border))",
                                  color: "hsl(var(--text-main))",
                                }}
                                title="Reasignar tarea a otro colaborador"
                              >
                                <option value="" disabled>
                                  Reasignar a...
                                </option>
                                <option value="">Sin Asignar</option>
                                {assignableMembers.map((m) => (
                                  <option key={m.persona_id} value={m.persona_id || ""}>
                                    {m.name} ({m.active_tasks} act.)
                                  </option>
                                ))}
                              </select>

                              {onOpenTask && (
                                <button
                                  onClick={() => onOpenTask(task.id)}
                                  className="p-1 rounded text-muted hover:opacity-100 transition-colors"
                                  title="Ver detalle de la tarea"
                                >
                                  <ExternalLink className="w-3.5 h-3.5" />
                                </button>
                              )}
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>
    </RightPanel>
  );
}
