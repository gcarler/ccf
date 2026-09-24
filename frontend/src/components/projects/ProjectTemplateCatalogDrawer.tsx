"use client";

import React, { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { RightPanel } from "@/components/ui/RightPanel";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { apiFetch } from "@/lib/http";
import type {
  ProjectTemplate,
  ProjectTemplateCreate,
  InstantiateProjectFromTemplate,
  SaveProjectAsTemplate,
  ProjectRecord,
} from "@/types/projects";
import {
  BookTemplate,
  FolderPlus,
  Copy,
  Layers,
  Calendar,
  DollarSign,
  Search,
  CheckCircle2,
  ChevronRight,
  ChevronDown,
  Sparkles,
  BookmarkPlus,
  ArrowRight,
  Clock,
  Tag,
  Trash2,
  Globe,
  Lock,
} from "lucide-react";
import clsx from "clsx";

interface ProjectTemplateCatalogDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  activeProjectId?: string;
  activeProjectTitle?: string;
  onProjectCreated?: (newProject: ProjectRecord) => void;
}

const TEMPLATE_CATEGORIES = [
  { id: "all", label: "Todas las categorías" },
  { id: "ministerial", label: "Ministerial & Pastoral" },
  { id: "evangelism", label: "Evangelismo & Campañas" },
  { id: "events", label: "Eventos & Congresos" },
  { id: "construction", label: "Infraestructura & Sedes" },
  { id: "general", label: "General & Operativo" },
];

export function ProjectTemplateCatalogDrawer({
  isOpen,
  onClose,
  activeProjectId,
  activeProjectTitle,
  onProjectCreated,
}: ProjectTemplateCatalogDrawerProps) {
  const router = useRouter();
  const { token, user } = useAuth();
  const { addToast } = useToast();

  const [activeTab, setActiveTab] = useState<"catalog" | "instantiate" | "save_current">("catalog");
  const [templates, setTemplates] = useState<ProjectTemplate[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<ProjectTemplate | null>(null);
  const [expandedPreviewId, setExpandedPreviewId] = useState<string | null>(null);

  // Filtros
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");

  // Formulario Instanciación
  const [instantiateTitle, setInstantiateTitle] = useState<string>("");
  const [instantiateDescription, setInstantiateDescription] = useState<string>("");
  const [instantiateStartDate, setInstantiateStartDate] = useState<string>(() => {
    return new Date().toISOString().split("T")[0];
  });
  const [instantiateBudget, setInstantiateBudget] = useState<string>("0");
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  // Formulario Guardar Proyecto Actual
  const [saveName, setSaveName] = useState<string>("");
  const [saveDescription, setSaveDescription] = useState<string>("");
  const [saveCategory, setSaveCategory] = useState<string>("general");
  const [saveIsPublic, setSaveIsPublic] = useState<boolean>(true);

  // Cargar plantillas
  const fetchTemplates = useCallback(async () => {
    if (!token || !isOpen) return;
    setLoading(true);
    try {
      const queryParams: Record<string, string> = {};
      if (selectedCategory !== "all") queryParams.category = selectedCategory;
      if (searchQuery.trim()) queryParams.search = searchQuery.trim();

      const queryString = new URLSearchParams(queryParams).toString();
      const url = `/projects/templates${queryString ? `?${queryString}` : ""}`;
      const data = await apiFetch<ProjectTemplate[]>(url, { token });
      setTemplates(Array.isArray(data) ? data : []);
    } catch {
      addToast("Error al cargar el catálogo de plantillas", "error");
    } finally {
      setLoading(false);
    }
  }, [token, isOpen, selectedCategory, searchQuery, addToast]);

  useEffect(() => {
    if (isOpen) {
      fetchTemplates();
      if (activeProjectId && activeProjectTitle) {
        setSaveName(`Plantilla: ${activeProjectTitle}`);
      }
    }
  }, [isOpen, fetchTemplates, activeProjectId, activeProjectTitle]);

  const handleSelectTemplateForInstantiation = (template: ProjectTemplate) => {
    setSelectedTemplate(template);
    setInstantiateTitle(`${template.name} - ${new Date().getFullYear()}`);
    setInstantiateDescription(template.description || "");
    setInstantiateBudget(template.default_budget ? String(template.default_budget) : "0");
    setActiveTab("instantiate");
  };

  const handleInstantiate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTemplate || !token) return;

    if (!instantiateTitle.trim()) {
      addToast("El título del proyecto es obligatorio", "warning");
      return;
    }

    setIsSubmitting(true);
    try {
      const payload: InstantiateProjectFromTemplate = {
        title: instantiateTitle.trim(),
        description: instantiateDescription.trim() || null,
        start_date: instantiateStartDate ? new Date(`${instantiateStartDate}T09:00:00Z`).toISOString() : null,
        budget_allocated: parseFloat(instantiateBudget) || null,
      };

      const newProject = await apiFetch<ProjectRecord>(
        `/projects/from-template/${selectedTemplate.id}`,
        {
          method: "POST",
          token,
          body: JSON.stringify(payload),
        }
      );

      addToast(`¡Proyecto '${newProject.title}' instanciado exitosamente!`, "success");
      onProjectCreated?.(newProject);
      onClose();
      router.push(`/plataforma/projects/${newProject.id}`);
    } catch {
      addToast("Error al instanciar el proyecto desde la plantilla", "error");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSaveCurrentAsTemplate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeProjectId || !token) return;

    if (!saveName.trim()) {
      addToast("El nombre de la plantilla es obligatorio", "warning");
      return;
    }

    setIsSubmitting(true);
    try {
      const payload: SaveProjectAsTemplate = {
        name: saveName.trim(),
        description: saveDescription.trim() || null,
        category: saveCategory,
        is_public: saveIsPublic,
      };

      await apiFetch<ProjectTemplate>(
        `/projects/${activeProjectId}/save-as-template`,
        {
          method: "POST",
          token,
          body: JSON.stringify(payload),
        }
      );

      addToast("Plantilla guardada y disponible en el catálogo", "success");
      setActiveTab("catalog");
      fetchTemplates();
    } catch {
      addToast("Error al guardar el proyecto como plantilla", "error");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteTemplate = async (templateId: string) => {
    if (!token) return;
    try {
      await apiFetch(`/projects/templates/${templateId}`, {
        method: "DELETE",
        token,
      });
      addToast("Plantilla eliminada del catálogo", "info");
      fetchTemplates();
      if (selectedTemplate?.id === templateId) {
        setSelectedTemplate(null);
        setActiveTab("catalog");
      }
    } catch {
      addToast("Error al eliminar la plantilla", "error");
    }
  };

  return (
    <RightPanel
      isOpen={isOpen}
      onClose={onClose}
      title="Catálogo de Plantillas Reutilizables de Proyectos"
      className="w-full max-w-2xl"
    >
      <div className="flex flex-col gap-5 p-6 text-sm" style={{ color: "hsl(var(--text-1))" }}>
        {/* NAVEGACIÓN ENTRE PESTAÑAS */}
        <div
          className="flex items-center gap-1 p-1 rounded-xl border"
          style={{
            backgroundColor: "hsl(var(--surface-2))",
            borderColor: "hsl(var(--border))",
          }}
        >
          <button
            type="button"
            onClick={() => setActiveTab("catalog")}
            className={clsx(
              "flex-1 py-2 px-3 rounded-lg text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-2 transition-all",
              activeTab === "catalog" ? "shadow-sm" : "opacity-75 hover:opacity-100"
            )}
            style={{
              backgroundColor: activeTab === "catalog" ? "hsl(var(--surface-1))" : "transparent",
              color: activeTab === "catalog" ? "hsl(var(--primary))" : "hsl(var(--text-muted))",
            }}
          >
            <BookTemplate className="w-4 h-4" />
            Explorar ({templates.length})
          </button>

          {selectedTemplate && (
            <button
              type="button"
              onClick={() => setActiveTab("instantiate")}
              className={clsx(
                "flex-1 py-2 px-3 rounded-lg text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-2 transition-all",
                activeTab === "instantiate" ? "shadow-sm" : "opacity-75 hover:opacity-100"
              )}
              style={{
                backgroundColor: activeTab === "instantiate" ? "hsl(var(--surface-1))" : "transparent",
                color: activeTab === "instantiate" ? "hsl(var(--primary))" : "hsl(var(--text-muted))",
              }}
            >
              <FolderPlus className="w-4 h-4" />
              Instanciar
            </button>
          )}

          {activeProjectId && (
            <button
              type="button"
              onClick={() => setActiveTab("save_current")}
              className={clsx(
                "flex-1 py-2 px-3 rounded-lg text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-2 transition-all",
                activeTab === "save_current" ? "shadow-sm" : "opacity-75 hover:opacity-100"
              )}
              style={{
                backgroundColor: activeTab === "save_current" ? "hsl(var(--surface-1))" : "transparent",
                color: activeTab === "save_current" ? "hsl(var(--primary))" : "hsl(var(--text-muted))",
              }}
            >
              <BookmarkPlus className="w-4 h-4" />
              Guardar Proyecto
            </button>
          )}
        </div>

        {/* TAB 1: EXPLORAR CATÁLOGO */}
        {activeTab === "catalog" && (
          <div className="flex flex-col gap-4">
            {/* Buscador y Filtro por Categorías */}
            <div className="space-y-3">
              <div
                className="flex items-center gap-2 px-3 py-2 rounded-xl border"
                style={{
                  backgroundColor: "hsl(var(--surface-1))",
                  borderColor: "hsl(var(--border))",
                }}
              >
                <Search className="w-4 h-4 opacity-50" />
                <input
                  type="text"
                  placeholder="Buscar plantilla por nombre o descripción..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="bg-transparent text-xs w-full outline-none"
                  style={{ color: "hsl(var(--foreground))" }}
                />
              </div>

              <div className="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-none">
                {TEMPLATE_CATEGORIES.map((cat) => (
                  <button
                    key={cat.id}
                    type="button"
                    onClick={() => setSelectedCategory(cat.id)}
                    className={clsx(
                      "px-3 py-1 rounded-full text-xs font-medium whitespace-nowrap transition-all border",
                      selectedCategory === cat.id
                        ? "font-bold shadow-sm"
                        : "opacity-70 hover:opacity-100"
                    )}
                    style={{
                      backgroundColor:
                        selectedCategory === cat.id
                          ? "hsl(var(--primary) / 0.15)"
                          : "hsl(var(--surface-2))",
                      borderColor:
                        selectedCategory === cat.id
                          ? "hsl(var(--primary))"
                          : "hsl(var(--border))",
                      color:
                        selectedCategory === cat.id
                          ? "hsl(var(--primary))"
                          : "hsl(var(--text-muted))",
                    }}
                  >
                    {cat.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Listado de Plantillas */}
            {loading ? (
              <div className="py-12 text-center text-xs" style={{ color: "hsl(var(--text-muted))" }}>
                Cargando plantillas ministeriales...
              </div>
            ) : templates.length === 0 ? (
              <div
                className="py-12 text-center rounded-xl border text-xs space-y-2 p-6"
                style={{
                  backgroundColor: "hsl(var(--surface-1))",
                  borderColor: "hsl(var(--border))",
                  color: "hsl(var(--text-muted))",
                }}
              >
                <BookTemplate className="w-10 h-10 mx-auto opacity-30" />
                <p className="font-semibold text-sm">No se encontraron plantillas</p>
                <p className="text-3xs max-w-sm mx-auto">
                  Guarda proyectos activos como plantillas reutilizables para estandarizar tus
                  flujos de trabajo pastorales y ministeriales.
                </p>
              </div>
            ) : (
              <div className="flex flex-col gap-3">
                {templates.map((tpl) => {
                  const phases = tpl.structure?.phases || [];
                  const tasks = tpl.structure?.tasks || [];
                  const isExpanded = expandedPreviewId === tpl.id;

                  return (
                    <div
                      key={tpl.id}
                      className="rounded-xl border p-4 transition-all hover:shadow-sm space-y-3"
                      style={{
                        backgroundColor: "hsl(var(--surface-1))",
                        borderColor: "hsl(var(--border))",
                      }}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="space-y-1 min-w-0 flex-1">
                          <div className="flex items-center gap-2 flex-wrap">
                            <h3 className="font-bold text-sm" style={{ color: "hsl(var(--foreground))" }}>
                              {tpl.name}
                            </h3>
                            <span
                              className="px-2 py-0.5 rounded text-3xs font-semibold uppercase tracking-wider"
                              style={{
                                backgroundColor: "hsl(var(--surface-2))",
                                color: "hsl(var(--primary))",
                              }}
                            >
                              {tpl.category}
                            </span>
                            {tpl.is_public ? (
                              <span className="flex items-center gap-1 text-3xs" style={{ color: "hsl(var(--success))" }}>
                                <Globe className="w-3 h-3" /> Pública
                              </span>
                            ) : (
                              <span className="flex items-center gap-1 text-3xs" style={{ color: "hsl(var(--warning))" }}>
                                <Lock className="w-3 h-3" /> Sede
                              </span>
                            )}
                          </div>
                          {tpl.description && (
                            <p className="text-xs line-clamp-2" style={{ color: "hsl(var(--text-muted))" }}>
                              {tpl.description}
                            </p>
                          )}
                        </div>

                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            onClick={() => handleDeleteTemplate(tpl.id)}
                            className="p-1.5 rounded-lg border opacity-40 hover:opacity-100 transition-opacity"
                            style={{
                              borderColor: "hsl(var(--border))",
                              color: "hsl(var(--destructive))",
                            }}
                            title="Eliminar plantilla"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>

                      {/* Métricas y Datos Rápidos */}
                      <div
                        className="grid grid-cols-3 gap-2 p-2.5 rounded-lg border text-center text-xs"
                        style={{
                          backgroundColor: "hsl(var(--surface-2))",
                          borderColor: "hsl(var(--border))",
                        }}
                      >
                        <div>
                          <span className="text-3xs block" style={{ color: "hsl(var(--text-muted))" }}>Fases</span>
                          <span className="font-bold">{phases.length}</span>
                        </div>
                        <div>
                          <span className="text-3xs block" style={{ color: "hsl(var(--text-muted))" }}>Tareas</span>
                          <span className="font-bold">{tasks.length}</span>
                        </div>
                        <div>
                          <span className="text-3xs block" style={{ color: "hsl(var(--text-muted))" }}>Presupuesto</span>
                          <span className="font-bold font-mono" style={{ color: "hsl(var(--primary))" }}>
                            ${(tpl.default_budget || 0).toLocaleString("es-CO")}
                          </span>
                        </div>
                      </div>

                      {/* Botones de Acción */}
                      <div className="flex items-center justify-between pt-1">
                        <button
                          type="button"
                          onClick={() => setExpandedPreviewId(isExpanded ? null : tpl.id)}
                          className="text-xs font-semibold flex items-center gap-1 opacity-70 hover:opacity-100 transition-opacity"
                          style={{ color: "hsl(var(--text-1))" }}
                        >
                          {isExpanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                          {isExpanded ? "Ocultar estructura" : "Ver estructura"}
                        </button>

                        <button
                          type="button"
                          onClick={() => handleSelectTemplateForInstantiation(tpl)}
                          className="px-3.5 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 transition-all shadow-sm active:scale-95"
                          style={{
                            backgroundColor: "hsl(var(--primary))",
                            color: "hsl(var(--primary-foreground))",
                          }}
                        >
                          <Copy className="w-3.5 h-3.5" />
                          Usar Plantilla
                        </button>
                      </div>

                      {/* Vista previa de estructura de fases y tareas */}
                      {isExpanded && (
                        <div
                          className="mt-3 p-3 rounded-lg border space-y-2.5 text-xs animate-in fade-in"
                          style={{
                            backgroundColor: "hsl(var(--surface-2))",
                            borderColor: "hsl(var(--border))",
                          }}
                        >
                          <span className="font-bold text-3xs uppercase tracking-wider block" style={{ color: "hsl(var(--text-muted))" }}>
                            Estructura de la Plantilla ({phases.length} fases, {tasks.length} tareas)
                          </span>

                          {phases.length > 0 ? (
                            <div className="space-y-2">
                              {phases.map((ph, idx) => {
                                const phaseTasks = tasks.filter(
                                  (t) =>
                                    t.phase_index === idx ||
                                    (t.phase_name && t.phase_name.toLowerCase() === ph.title.toLowerCase())
                                );
                                return (
                                  <div
                                    key={idx}
                                    className="p-2 rounded border"
                                    style={{
                                      backgroundColor: "hsl(var(--surface-1))",
                                      borderColor: "hsl(var(--border))",
                                    }}
                                  >
                                    <div className="font-semibold flex items-center gap-1.5 text-2xs">
                                      <Layers className="w-3 h-3" style={{ color: "hsl(var(--primary))" }} />
                                      <span>Fase {idx + 1}: {ph.title}</span>
                                    </div>
                                    {phaseTasks.length > 0 ? (
                                      <div className="pl-4 pt-1.5 space-y-1">
                                        {phaseTasks.map((t, tIdx) => (
                                          <div key={tIdx} className="flex items-center justify-between text-3xs">
                                            <span className="truncate max-w-[220px]">
                                              • {t.title}
                                            </span>
                                            <span style={{ color: "hsl(var(--text-muted))" }}>
                                              {t.duration_days}d (+{t.day_offset}d)
                                            </span>
                                          </div>
                                        ))}
                                      </div>
                                    ) : (
                                      <p className="pl-4 text-3xs italic" style={{ color: "hsl(var(--text-muted))" }}>
                                        Sin tareas específicas
                                      </p>
                                    )}
                                  </div>
                                );
                              })}
                            </div>
                          ) : tasks.length > 0 ? (
                            <div className="space-y-1">
                              {tasks.map((t, tIdx) => (
                                <div
                                  key={tIdx}
                                  className="flex items-center justify-between p-1.5 rounded border text-3xs"
                                  style={{
                                    backgroundColor: "hsl(var(--surface-1))",
                                    borderColor: "hsl(var(--border))",
                                  }}
                                >
                                  <span>• {t.title}</span>
                                  <span style={{ color: "hsl(var(--text-muted))" }}>
                                    {t.duration_days}d
                                  </span>
                                </div>
                              ))}
                            </div>
                          ) : (
                            <p className="text-3xs italic" style={{ color: "hsl(var(--text-muted))" }}>
                              Plantilla sin fases ni tareas predefinidas.
                            </p>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* TAB 2: INSTANCIAR PROYECTO */}
        {activeTab === "instantiate" && selectedTemplate && (
          <form
            onSubmit={handleInstantiate}
            className="flex flex-col gap-4 p-5 rounded-xl border"
            style={{
              backgroundColor: "hsl(var(--surface-1))",
              borderColor: "hsl(var(--border))",
            }}
          >
            <div className="flex items-center justify-between pb-3 border-b" style={{ borderColor: "hsl(var(--border))" }}>
              <div className="flex items-center gap-2">
                <FolderPlus className="w-5 h-5" style={{ color: "hsl(var(--primary))" }} />
                <div>
                  <h3 className="font-bold text-sm">Instanciar Nuevo Proyecto</h3>
                  <span className="text-3xs" style={{ color: "hsl(var(--text-muted))" }}>
                    Basado en: {selectedTemplate.name}
                  </span>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setActiveTab("catalog")}
                className="text-xs font-semibold hover:underline"
                style={{ color: "hsl(var(--text-muted))" }}
              >
                Volver
              </button>
            </div>

            <div>
              <label className="block text-xs font-semibold mb-1" style={{ color: "hsl(var(--text-muted))" }}>
                Título del Nuevo Proyecto *
              </label>
              <input
                type="text"
                required
                value={instantiateTitle}
                onChange={(e) => setInstantiateTitle(e.target.value)}
                className="w-full py-2 px-3 rounded-lg border text-sm"
                style={{
                  backgroundColor: "hsl(var(--surface-2))",
                  borderColor: "hsl(var(--border))",
                  color: "hsl(var(--foreground))",
                }}
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold mb-1" style={{ color: "hsl(var(--text-muted))" }}>
                  Fecha de Inicio *
                </label>
                <input
                  type="date"
                  required
                  value={instantiateStartDate}
                  onChange={(e) => setInstantiateStartDate(e.target.value)}
                  className="w-full py-2 px-3 rounded-lg border text-sm"
                  style={{
                    backgroundColor: "hsl(var(--surface-2))",
                    borderColor: "hsl(var(--border))",
                    color: "hsl(var(--foreground))",
                  }}
                />
              </div>

              <div>
                <label className="block text-xs font-semibold mb-1" style={{ color: "hsl(var(--text-muted))" }}>
                  Presupuesto Asignado ($ COP)
                </label>
                <input
                  type="number"
                  step="100"
                  min="0"
                  value={instantiateBudget}
                  onChange={(e) => setInstantiateBudget(e.target.value)}
                  className="w-full py-2 px-3 rounded-lg border text-sm"
                  style={{
                    backgroundColor: "hsl(var(--surface-2))",
                    borderColor: "hsl(var(--border))",
                    color: "hsl(var(--foreground))",
                  }}
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold mb-1" style={{ color: "hsl(var(--text-muted))" }}>
                Descripción o Justificación del Proyecto
              </label>
              <textarea
                rows={3}
                value={instantiateDescription}
                onChange={(e) => setInstantiateDescription(e.target.value)}
                className="w-full py-2 px-3 rounded-lg border text-sm"
                style={{
                  backgroundColor: "hsl(var(--surface-2))",
                  borderColor: "hsl(var(--border))",
                  color: "hsl(var(--foreground))",
                }}
              />
            </div>

            <div
              className="p-3 rounded-lg border text-xs space-y-1"
              style={{
                backgroundColor: "hsl(var(--surface-2))",
                borderColor: "hsl(var(--border))",
              }}
            >
              <span className="font-bold block" style={{ color: "hsl(var(--primary))" }}>
                ¿Qué se creará automáticamente?
              </span>
              <p className="text-3xs" style={{ color: "hsl(var(--text-muted))" }}>
                • {selectedTemplate.structure?.phases?.length || 0} fase(s) organizadas.
              </p>
              <p className="text-3xs" style={{ color: "hsl(var(--text-muted))" }}>
                • {selectedTemplate.structure?.tasks?.length || 0} tarea(s) con cronograma relativo calculado desde la fecha de inicio.
              </p>
              <p className="text-3xs" style={{ color: "hsl(var(--text-muted))" }}>
                • Control presupuestario y asignación de sede multi-tenant segura.
              </p>
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="mt-2 py-2.5 px-4 rounded-xl font-bold flex items-center justify-center gap-2 transition-all shadow-md active:scale-95 disabled:opacity-50"
              style={{
                backgroundColor: "hsl(var(--primary))",
                color: "hsl(var(--primary-foreground))",
              }}
            >
              <Sparkles className="w-4 h-4" />
              {isSubmitting ? "Creando proyecto..." : "Crear Proyecto desde Plantilla"}
            </button>
          </form>
        )}

        {/* TAB 3: GUARDAR PROYECTO ACTUAL COMO PLANTILLA */}
        {activeTab === "save_current" && activeProjectId && (
          <form
            onSubmit={handleSaveCurrentAsTemplate}
            className="flex flex-col gap-4 p-5 rounded-xl border"
            style={{
              backgroundColor: "hsl(var(--surface-1))",
              borderColor: "hsl(var(--border))",
            }}
          >
            <div className="flex items-center gap-2 pb-3 border-b" style={{ borderColor: "hsl(var(--border))" }}>
              <BookmarkPlus className="w-5 h-5" style={{ color: "hsl(var(--primary))" }} />
              <div>
                <h3 className="font-bold text-sm">Guardar Proyecto Activo como Plantilla</h3>
                <span className="text-3xs" style={{ color: "hsl(var(--text-muted))" }}>
                  Captura las fases y tareas actuales para estandarizarlas
                </span>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold mb-1" style={{ color: "hsl(var(--text-muted))" }}>
                Nombre de la Plantilla *
              </label>
              <input
                type="text"
                required
                value={saveName}
                onChange={(e) => setSaveName(e.target.value)}
                className="w-full py-2 px-3 rounded-lg border text-sm"
                style={{
                  backgroundColor: "hsl(var(--surface-2))",
                  borderColor: "hsl(var(--border))",
                  color: "hsl(var(--foreground))",
                }}
              />
            </div>

            <div>
              <label className="block text-xs font-semibold mb-1" style={{ color: "hsl(var(--text-muted))" }}>
                Categoría *
              </label>
              <select
                value={saveCategory}
                onChange={(e) => setSaveCategory(e.target.value)}
                className="w-full py-2 px-3 rounded-lg border text-sm"
                style={{
                  backgroundColor: "hsl(var(--surface-2))",
                  borderColor: "hsl(var(--border))",
                  color: "hsl(var(--foreground))",
                }}
              >
                {TEMPLATE_CATEGORIES.filter((c) => c.id !== "all").map((cat) => (
                  <option key={cat.id} value={cat.id}>
                    {cat.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold mb-1" style={{ color: "hsl(var(--text-muted))" }}>
                Descripción de la Plantilla
              </label>
              <textarea
                rows={3}
                placeholder="Explica para qué tipo de iniciativa o campaña se recomienda..."
                value={saveDescription}
                onChange={(e) => setSaveDescription(e.target.value)}
                className="w-full py-2 px-3 rounded-lg border text-sm"
                style={{
                  backgroundColor: "hsl(var(--surface-2))",
                  borderColor: "hsl(var(--border))",
                  color: "hsl(var(--foreground))",
                }}
              />
            </div>

            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="template-public"
                checked={saveIsPublic}
                onChange={(e) => setSaveIsPublic(e.target.checked)}
                className="rounded cursor-pointer"
                style={{ accentColor: "hsl(var(--primary))" }}
              />
              <label htmlFor="template-public" className="text-xs font-medium cursor-pointer">
                Disponible para todas las sedes de la plataforma (Pública)
              </label>
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="mt-2 py-2.5 px-4 rounded-xl font-bold flex items-center justify-center gap-2 transition-all shadow-md active:scale-95 disabled:opacity-50"
              style={{
                backgroundColor: "hsl(var(--primary))",
                color: "hsl(var(--primary-foreground))",
              }}
            >
              <CheckCircle2 className="w-4 h-4" />
              {isSubmitting ? "Guardando..." : "Guardar como Plantilla Reutilizable"}
            </button>
          </form>
        )}
      </div>
    </RightPanel>
  );
}
