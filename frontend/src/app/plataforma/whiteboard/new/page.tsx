"use client";

import React, { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import CrmShell from "@/components/crm/CrmShell";
import { apiFetch } from "@/lib/http";
import { useAuth } from "@/context/AuthContext";
import {
  LayoutDashboard,
  PenTool,
  Sparkles,
  Loader2,
  Check,
} from "lucide-react";

interface ProjectOption {
  id: string;
  title: string;
  description?: string | null;
}

export default function NewWhiteboardPage() {
  const router = useRouter();
  const { token } = useAuth();
  const [title, setTitle] = useState("");
  const [projects, setProjects] = useState<ProjectOption[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>("");
  const [loadingProjects, setLoadingProjects] = useState(true);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    fetchProjects();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const fetchProjects = async () => {
    if (!token) return;
    setLoadingProjects(true);
    try {
      const data = await apiFetch<ProjectOption[]>("/projects", { token });
      setProjects(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error("Error loading projects:", err);
    } finally {
      setLoadingProjects(false);
    }
  };

  const previewTitle = useMemo(
    () => title.trim() || "Nueva pizarra CCF",
    [title]
  );

  const handleCreate = async () => {
    if (!token || !selectedProjectId) return;
    setCreating(true);
    try {
      await apiFetch(`/projects/${selectedProjectId}/whiteboard`, {
        method: "POST",
        token,
        body: { title: previewTitle, elements_json: "[]" },
      });
      router.push(`/plataforma/whiteboard/${selectedProjectId}`);
    } catch (err) {
      console.error("Error creating whiteboard:", err);
      setCreating(false);
    }
  };

  const canCreate = selectedProjectId && !creating;

  return (
    <CrmShell
      breadcrumbs={[
        {
          label: "CCF Tools",
          icon: LayoutDashboard,
          href: "/plataforma/whiteboard",
        },
        { label: "Nueva Pizarra", icon: PenTool },
      ]}
    >
      <div className="mx-auto flex h-full max-w-5xl items-center px-4 py-1.5">
        <section className="grid w-full grid-cols-1 overflow-hidden rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] shadow-2xl dark:border-white/10 dark:bg-white/5 lg:grid-cols-[1fr_0.9fr]">
          <div className="space-y-3 p-4 lg:p-4">
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--primary))]">
                Lienzo colaborativo
              </p>
              <h1 className="mt-2 text-lg font-bold tracking-tight text-[hsl(var(--text-primary))] dark:text-white">
                Crear pizarra
              </h1>
              <p className="mt-3 max-w-xl text-sm font-medium leading-6 text-[hsl(var(--text-secondary))]">
                Activa un espacio de trabajo para mapas, diagramas, lluvia de
                ideas y planeacion asistida vinculado a un proyecto.
              </p>
            </div>

            <label className="block space-y-2">
              <span className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                Nombre
              </span>
              <input
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                placeholder="Ej: Planeacion CCF Q2"
                className="w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-4 py-3 text-sm font-bold outline-none focus:border-blue-400 dark:border-white/10 dark:bg-black/20"
              />
            </label>

            <label className="block space-y-2">
              <span className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                Proyecto vinculado
              </span>
              {loadingProjects ? (
                <div className="flex items-center gap-2 py-3 text-[hsl(var(--text-secondary))]">
                  <Loader2 size={16} className="animate-spin" />
                  Cargando proyectos...
                </div>
              ) : projects.length === 0 ? (
                <p className="text-sm text-[hsl(var(--text-secondary))]">
                  No tienes proyectos disponibles. Crea un proyecto primero.
                </p>
              ) : (
                <div className="max-h-60 overflow-y-auto space-y-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-2 dark:border-white/10 dark:bg-black/20">
                  {projects.map((project) => {
                    const selected = selectedProjectId === project.id;
                    return (
                      <button
                        key={project.id}
                        type="button"
                        onClick={() => setSelectedProjectId(project.id)}
                        className={`w-full flex items-center justify-between rounded-md px-3 py-2 text-left transition-colors ${
                          selected
                            ? "bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-500/30"
                            : "hover:bg-white/5"
                        }`}
                      >
                        <div>
                          <p className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-white">
                            {project.title}
                          </p>
                          {project.description && (
                            <p className="text-[11px] text-[hsl(var(--text-secondary))] line-clamp-1">
                              {project.description}
                            </p>
                          )}
                        </div>
                        {selected && (
                          <Check
                            size={16}
                            className="text-[hsl(var(--primary))]"
                          />
                        )}
                      </button>
                    );
                  })}
                </div>
              )}
            </label>

            <div className="flex items-center gap-3">
              <button
                onClick={handleCreate}
                disabled={!canCreate}
                className="rounded-lg bg-[hsl(var(--primary))] px-3 py-3 text-[11px] font-semibold uppercase tracking-wide text-white shadow-xl shadow-blue-500/20 disabled:opacity-50"
              >
                {creating ? (
                  <span className="flex items-center gap-2">
                    <Loader2 size={14} className="animate-spin" /> Creando...
                  </span>
                ) : (
                  "Crear pizarra"
                )}
              </button>
              <button
                onClick={() => router.push("/plataforma/whiteboard")}
                className="rounded-lg border border-[hsl(var(--border))] px-3 py-3 text-[11px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] dark:border-white/10"
              >
                Cancelar
              </button>
            </div>
          </div>

          <div className="relative min-h-[420px] overflow-hidden bg-[hsl(var(--bg-muted))] p-4 text-white">
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(59,130,246,0.35),transparent_35%),radial-gradient(circle_at_80%_70%,rgba(14,165,233,0.2),transparent_30%)]" />
            <div className="relative flex h-full flex-col justify-between rounded-lg border border-white/10 bg-white/10 p-3 backdrop-blur">
              <Sparkles className="text-blue-300" size={36} />
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-wide text-blue-200">
                  Preview
                </p>
                <h2 className="mt-2 text-xl font-bold">{previewTitle}</h2>
                <p className="mt-3 text-sm font-medium text-[hsl(var(--text-secondary))]">
                  {selectedProjectId
                    ? `Vinculada al proyecto seleccionado.`
                    : "Selecciona un proyecto para continuar."}
                </p>
              </div>
            </div>
          </div>
        </section>
      </div>
    </CrmShell>
  );
}
