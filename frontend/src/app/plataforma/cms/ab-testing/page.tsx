"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { SITE_KEY } from "@/lib/site-config";
import { toast } from "sonner";
import { motion, AnimatePresence } from "framer-motion";
import {
  FlaskConical,
  Plus,
  Search,
  Pause,
  Play,
  Trash2,
  BarChart2,
  Trophy,
  Loader2,
  AlertCircle,
  FileText,
  Layers,
  Sparkles,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import SidePanel from "@/components/ui/SidePanel";
import clsx from "clsx";
import {
  applyCmsAbTestWinner,
  createCmsAbTest,
  deleteCmsAbTest,
  getCmsAbTestResults,
  listCmsAbTests,
  listCmsSites,
  patchCmsAbTest,
} from "@/lib/cms/v2";
import { CmsAbTest, CmsAbTestResults, CmsAbTestStatus, CmsPage, CmsSection, CmsSite } from "@/types/cms-v2";
import { canEditCms } from "@/lib/cms/permissions";
import { apiFetch } from "@/lib/http";
import { CmsModuleNav } from "@/components/cms/CmsModuleNav";

export default function CmsAbTestingManagement() {
  const { token, user } = useAuth();
  const [siteKey, setSiteKey] = useState(SITE_KEY);
  const [sites, setSites] = useState<CmsSite[]>([]);
  const [tests, setTests] = useState<CmsAbTest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");

  // Create drawer state
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [saving, setSaving] = useState(false);

  // Pages & Sections for create drawer
  const [pages, setPages] = useState<CmsPage[]>([]);
  const [loadingPages, setLoadingPages] = useState(false);
  const [selectedPageId, setSelectedPageId] = useState<string>("");
  const [pageSections, setPageSections] = useState<CmsSection[]>([]);
  const [loadingSections, setLoadingSections] = useState(false);

  // Form State
  const [formName, setFormName] = useState("");
  const [formSectionAId, setFormSectionAId] = useState("");
  const [formSectionBId, setFormSectionBId] = useState("");
  const [formTrafficSplit, setFormTrafficSplit] = useState(0.5);

  // Results drawer state
  const [selectedTestResults, setSelectedTestResults] = useState<{
    test: CmsAbTest;
    results: CmsAbTestResults;
  } | null>(null);
  const [_loadingResults, setLoadingResults] = useState(false);

  // Delete / Apply modal state
  const [pendingDelete, setPendingDelete] = useState<CmsAbTest | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [applyingWinner, setApplyingWinner] = useState(false);

  const canEdit = canEditCms(user?.role);

  const fetchData = useCallback(async (targetSite: string) => {
    if (!token) {
      setLoading(false);
      setTests([]);
      setError("Debes iniciar sesión para gestionar A/B testing.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const [nextSites, nextTests] = await Promise.all([
        listCmsSites(token),
        listCmsAbTests(targetSite, undefined, token),
      ]);
      setSites(nextSites || []);
      setTests(nextTests || []);
    } catch (err) {
      toast.error("Error al cargar experimentos A/B");
      setTests([]);
      setError("No se pudieron cargar los experimentos A/B.");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    fetchData(siteKey);
  }, [fetchData, siteKey]);

  // Load pages when opening create drawer
  const fetchPages = useCallback(async () => {
    if (!token) return;
    setLoadingPages(true);
    try {
      const res = await apiFetch<{ items: CmsPage[] }>(`/cms/v2/sites/${siteKey}/pages`, { token });
      setPages(res.items || []);
    } catch (err) {
      toast.error("Error al cargar páginas");
    } finally {
      setLoadingPages(false);
    }
  }, [siteKey, token]);

  // Load sections when selectedPageId changes
  useEffect(() => {
    if (!selectedPageId || !token) {
      setPageSections([]);
      return;
    }
    const page = pages.find((p) => p.id === selectedPageId);
    if (!page) return;

    const fetchSections = async () => {
      setLoadingSections(true);
      try {
        const res = await apiFetch<{ items: CmsSection[] }>(
          `/cms/v2/sites/${siteKey}/pages/${page.slug}/sections`,
          { token }
        );
        setPageSections(res.items || []);
      } catch (err) {
        toast.error("Error al cargar secciones de la página");
        setPageSections([]);
      } finally {
        setLoadingSections(false);
      }
    };
    fetchSections();
  }, [selectedPageId, pages, siteKey, token]);

  const filteredTests = useMemo(() => {
    return tests.filter((t) => {
      const matchesSearch =
        t.name.toLowerCase().includes(search.trim().toLowerCase()) ||
        t.id.toLowerCase().includes(search.trim().toLowerCase());
      const matchesStatus =
        statusFilter === "all" || t.status === statusFilter;
      return matchesSearch && matchesStatus;
    });
  }, [tests, search, statusFilter]);

  const handleOpenCreate = () => {
    setFormName("");
    setSelectedPageId("");
    setFormSectionAId("");
    setFormSectionBId("");
    setFormTrafficSplit(0.5);
    setIsDrawerOpen(true);
    fetchPages();
  };

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formName.trim() || !selectedPageId || !formSectionAId || !formSectionBId) {
      toast.error("Por favor completa todos los campos requeridos");
      return;
    }
    if (formSectionAId === formSectionBId) {
      toast.error("La Sección A y la Sección B deben ser diferentes");
      return;
    }

    setSaving(true);
    try {
      const created = await createCmsAbTest(
        siteKey,
        {
          name: formName.trim(),
          page_id: selectedPageId,
          section_a_id: formSectionAId,
          section_b_id: formSectionBId,
          traffic_split: formTrafficSplit,
        },
        token
      );
      toast.success("Experimento A/B creado exitosamente");
      setTests((prev) => [created, ...prev]);
      setIsDrawerOpen(false);
    } catch (err: any) {
      toast.error(err.message || "Error al crear experimento");
    } finally {
      setSaving(false);
    }
  };

  const handleToggleStatus = async (test: CmsAbTest) => {
    const nextStatus: CmsAbTestStatus = test.status === "active" ? "paused" : "active";
    try {
      const updated = await patchCmsAbTest(siteKey, test.id, { status: nextStatus }, token);
      toast.success(
        nextStatus === "active" ? "Experimento reanudado" : "Experimento pausado"
      );
      setTests((prev) => prev.map((t) => (t.id === test.id ? updated : t)));
    } catch (err: any) {
      toast.error(err.message || "Error al cambiar estado");
    }
  };

  const handleDelete = async () => {
    if (!pendingDelete) return;
    setDeleting(true);
    try {
      await deleteCmsAbTest(siteKey, pendingDelete.id, token);
      toast.success("Experimento A/B eliminado");
      setTests((prev) => prev.filter((t) => t.id !== pendingDelete.id));
      if (selectedTestResults?.test.id === pendingDelete.id) {
        setSelectedTestResults(null);
      }
      setPendingDelete(null);
    } catch (err: any) {
      toast.error(err.message || "Error al eliminar experimento");
    } finally {
      setDeleting(false);
    }
  };

  const handleOpenResults = async (test: CmsAbTest) => {
    setLoadingResults(true);
    try {
      const results = await getCmsAbTestResults(siteKey, test.id, token);
      setSelectedTestResults({ test, results });
    } catch (err: any) {
      toast.error("Error al cargar resultados del experimento");
    } finally {
      setLoadingResults(false);
    }
  };

  const handleApplyWinner = async (testId: string, winnerVariant?: "a" | "b") => {
    setApplyingWinner(true);
    try {
      const updated = await applyCmsAbTestWinner(
        siteKey,
        testId,
        winnerVariant ? { winner_variant: winnerVariant } : undefined,
        token
      );
      toast.success("Ganador aplicado con éxito a la página");
      setTests((prev) => prev.map((t) => (t.id === testId ? updated : t)));
      if (selectedTestResults?.test.id === testId) {
        setSelectedTestResults((prev) =>
          prev ? { ...prev, test: updated } : null
        );
      }
    } catch (err: any) {
      toast.error(err.message || "Error al aplicar ganador");
    } finally {
      setApplyingWinner(false);
    }
  };

  return (
    <div className="min-h-screen bg-[hsl(var(--bg-primary))] text-[hsl(var(--text-primary))]">
      <CmsModuleNav />

      <main className="p-6 max-w-7xl mx-auto space-y-6">
        {/* Top Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[hsl(var(--border))] pb-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-cyan-500/10 text-cyan-600 dark:text-cyan-400">
              <FlaskConical size={24} />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight">Experimentos A/B de Secciones</h1>
              <p className="text-xs text-[hsl(var(--text-secondary))]">
                Optimiza conversiones probando diferentes variantes de secciones en tus páginas.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {sites.length > 1 && (
              <select
                value={siteKey}
                onChange={(e) => setSiteKey(e.target.value)}
                className="px-3 py-1.5 text-xs rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] text-[hsl(var(--text-primary))]"
              >
                {sites.map((s) => (
                  <option key={s.id} value={s.site_key}>
                    {s.name} ({s.site_key})
                  </option>
                ))}
              </select>
            )}

            {canEdit && (
              <button
                onClick={handleOpenCreate}
                className="flex items-center gap-2 px-4 py-2 text-xs font-medium rounded-lg bg-[hsl(var(--primary))] text-white hover:opacity-90 transition-opacity shadow-sm"
              >
                <Plus size={16} />
                Nuevo Experimento
              </button>
            )}
          </div>
        </div>

        {/* Filters and Search */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-1.5 border border-[hsl(var(--border))] p-1 rounded-xl bg-[hsl(var(--surface-1))]">
            {[
              { id: "all", label: "Todos" },
              { id: "active", label: "Activos" },
              { id: "paused", label: "Pausados" },
              { id: "completed", label: "Completados" },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setStatusFilter(tab.id)}
                className={clsx(
                  "px-3 py-1.5 text-xs font-medium rounded-lg transition-all",
                  statusFilter === tab.id
                    ? "bg-[hsl(var(--bg-primary))] shadow-xs text-[hsl(var(--primary))]"
                    : "text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]"
                )}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div className="relative w-full sm:w-64">
            <Search
              size={14}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]"
            />
            <input
              type="text"
              placeholder="Buscar experimentos..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-xs rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] text-[hsl(var(--text-primary))] focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]"
            />
          </div>
        </div>

        {/* Loading Skeletons */}
        {loading && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="p-5 rounded-2xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] animate-pulse space-y-4"
              >
                <div className="h-4 bg-[hsl(var(--border))] rounded w-3/4" />
                <div className="h-3 bg-[hsl(var(--border))] rounded w-1/2" />
                <div className="h-10 bg-[hsl(var(--border))] rounded" />
              </div>
            ))}
          </div>
        )}

        {/* Error state */}
        {!loading && error && (
          <div className="p-4 rounded-xl bg-red-500/10 text-red-600 dark:text-red-400 text-xs flex items-center gap-2">
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        {/* Empty state */}
        {!loading && !error && filteredTests.length === 0 && (
          <div className="text-center py-16 border border-dashed border-[hsl(var(--border))] rounded-2xl bg-[hsl(var(--surface-1))]">
            <FlaskConical size={40} className="mx-auto text-[hsl(var(--text-secondary))] mb-3 opacity-60" />
            <h3 className="text-sm font-semibold mb-1">No se encontraron experimentos A/B</h3>
            <p className="text-xs text-[hsl(var(--text-secondary))] mb-4">
              Crea tu primer experimento para comparar dos versiones de seccion.
            </p>
            {canEdit && (
              <button
                onClick={handleOpenCreate}
                className="px-4 py-2 text-xs font-medium rounded-lg bg-[hsl(var(--primary))] text-white hover:opacity-90 inline-flex items-center gap-2"
              >
                <Plus size={14} />
                Crear Experimento
              </button>
            )}
          </div>
        )}

        {/* Tests List Grid */}
        {!loading && !error && filteredTests.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredTests.map((test) => {
              const isActive = test.status === "active";
              const isCompleted = test.status === "completed";
              const isPaused = test.status === "paused";

              return (
                <motion.div
                  key={test.id}
                  layout
                  initial={{ opacity: 0, scale: 0.98 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="p-5 rounded-2xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] flex flex-col justify-between space-y-4 hover:border-cyan-500/30 transition-all shadow-xs"
                >
                  <div className="space-y-2">
                    <div className="flex items-start justify-between gap-2">
                      <h3 className="font-semibold text-sm leading-snug">{test.name}</h3>
                      <span
                        className={clsx(
                          "px-2.5 py-0.5 text-[10px] font-semibold rounded-full capitalize shrink-0",
                          isActive && "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20",
                          isPaused && "bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20",
                          isCompleted && "bg-slate-500/10 text-slate-600 dark:text-slate-400 border border-slate-500/20"
                        )}
                      >
                        {test.status === "active" ? "Activo" : test.status === "paused" ? "Pausado" : "Completado"}
                      </span>
                    </div>

                    <div className="text-xs text-[hsl(var(--text-secondary))] space-y-1">
                      <div className="flex items-center gap-1.5">
                        <FileText size={12} />
                        <span>Página ID: <code className="text-[10px] bg-[hsl(var(--bg-primary))] px-1 py-0.5 rounded">{test.page_id.substring(0, 8)}...</code></span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <Layers size={12} />
                        <span>Split: {Math.round(test.traffic_split * 100)}% A / {Math.round((1 - test.traffic_split) * 100)}% B</span>
                      </div>
                    </div>
                  </div>

                  <div className="pt-3 border-t border-[hsl(var(--border))] flex items-center justify-between gap-2">
                    <button
                      onClick={() => handleOpenResults(test)}
                      className="px-3 py-1.5 text-xs font-medium rounded-lg bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 hover:bg-cyan-500/20 transition-colors flex items-center gap-1.5"
                    >
                      <BarChart2 size={14} />
                      Resultados
                    </button>

                    <div className="flex items-center gap-1">
                      {canEdit && !isCompleted && (
                        <button
                          onClick={() => handleToggleStatus(test)}
                          title={isActive ? "Pausar" : "Reanudar"}
                          className="p-1.5 rounded-lg text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--border))] transition-colors"
                        >
                          {isActive ? <Pause size={14} /> : <Play size={14} />}
                        </button>
                      )}

                      {canEdit && (
                        <button
                          onClick={() => setPendingDelete(test)}
                          title="Eliminar"
                          className="p-1.5 rounded-lg text-red-500 hover:bg-red-500/10 transition-colors"
                        >
                          <Trash2 size={14} />
                        </button>
                      )}
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </div>
        )}
      </main>

      {/* Create Experiment SidePanel Drawer */}
      <SidePanel
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        title="Crear Experimento A/B"
      >
        <form onSubmit={handleCreateSubmit} className="space-y-5 p-4">
          <div>
            <label className="block text-xs font-medium mb-1.5">Nombre del experimento *</label>
            <input
              type="text"
              required
              placeholder="Ej: Prueba Hero Call To Action"
              value={formName}
              onChange={(e) => setFormName(e.target.value)}
              className="w-full px-3 py-2 text-xs rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))]"
            />
          </div>

          <div>
            <label className="block text-xs font-medium mb-1.5">Página *</label>
            {loadingPages ? (
              <div className="text-xs text-[hsl(var(--text-secondary))] flex items-center gap-1.5">
                <Loader2 size={12} className="animate-spin" /> Cargando páginas...
              </div>
            ) : (
              <select
                required
                value={selectedPageId}
                onChange={(e) => setSelectedPageId(e.target.value)}
                className="w-full px-3 py-2 text-xs rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))]"
              >
                <option value="">-- Selecciona una página --</option>
                {pages.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.title} (/{p.slug})
                  </option>
                ))}
              </select>
            )}
          </div>

          {selectedPageId && (
            <>
              <div>
                <label className="block text-xs font-medium mb-1.5">Sección A (Variante Control) *</label>
                {loadingSections ? (
                  <div className="text-xs text-[hsl(var(--text-secondary))] flex items-center gap-1.5">
                    <Loader2 size={12} className="animate-spin" /> Cargando secciones...
                  </div>
                ) : (
                  <select
                    required
                    value={formSectionAId}
                    onChange={(e) => setFormSectionAId(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))]"
                  >
                    <option value="">-- Selecciona la Sección A --</option>
                    {pageSections.map((sec) => (
                      <option key={sec.id} value={sec.id}>
                        {sec.section_key} (Tipo: {sec.type})
                      </option>
                    ))}
                  </select>
                )}
              </div>

              <div>
                <label className="block text-xs font-medium mb-1.5">Sección B (Variante Prueba) *</label>
                {loadingSections ? (
                  <div className="text-xs text-[hsl(var(--text-secondary))] flex items-center gap-1.5">
                    <Loader2 size={12} className="animate-spin" /> Cargando secciones...
                  </div>
                ) : (
                  <select
                    required
                    value={formSectionBId}
                    onChange={(e) => setFormSectionBId(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))]"
                  >
                    <option value="">-- Selecciona la Sección B --</option>
                    {pageSections.map((sec) => (
                      <option key={sec.id} value={sec.id}>
                        {sec.section_key} (Tipo: {sec.type})
                      </option>
                    ))}
                  </select>
                )}
              </div>
            </>
          )}

          <div>
            <div className="flex justify-between items-center mb-1.5">
              <label className="text-xs font-medium">Distribución de Tráfico</label>
              <span className="text-xs font-bold text-cyan-600 dark:text-cyan-400">
                {Math.round(formTrafficSplit * 100)}% A / {Math.round((1 - formTrafficSplit) * 100)}% B
              </span>
            </div>
            <input
              type="range"
              min="0.1"
              max="0.9"
              step="0.05"
              value={formTrafficSplit}
              onChange={(e) => setFormTrafficSplit(parseFloat(e.target.value))}
              className="w-full accent-cyan-600"
            />
          </div>

          <div className="pt-4 flex justify-end gap-2 border-t border-[hsl(var(--border))]">
            <button
              type="button"
              onClick={() => setIsDrawerOpen(false)}
              className="px-4 py-2 text-xs font-medium rounded-xl border border-[hsl(var(--border))]"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-4 py-2 text-xs font-medium rounded-xl bg-[hsl(var(--primary))] text-white hover:opacity-90 disabled:opacity-50 flex items-center gap-1.5"
            >
              {saving && <Loader2 size={14} className="animate-spin" />}
              Crear Experimento
            </button>
          </div>
        </form>
      </SidePanel>

      {/* Results View Modal / SidePanel */}
      <SidePanel
        isOpen={!!selectedTestResults}
        onClose={() => setSelectedTestResults(null)}
        title="Resultados del Experimento A/B"
      >
        {selectedTestResults && (
          <div className="p-4 space-y-6">
            <div className="space-y-1">
              <h3 className="font-bold text-base">{selectedTestResults.test.name}</h3>
              <p className="text-xs text-[hsl(var(--text-secondary))]">
                Métricas de interacción y significancia estadística calculada.
              </p>
            </div>

            {/* Winner Badge */}
            {selectedTestResults.results.is_significant ? (
              <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-700 dark:text-emerald-300 flex items-start gap-3">
                <Trophy size={20} className="shrink-0 mt-0.5 text-amber-500" />
                <div className="space-y-1 text-xs">
                  <h4 className="font-bold text-sm">
                    🏆 Ganador Recomendado: Variante {selectedTestResults.results.recommended_winner?.toUpperCase()}
                  </h4>
                  <p>
                    Se alcanzó una confianza estadística del{" "}
                    <strong>
                      {(selectedTestResults.results.statistical_significance * 100).toFixed(1)}%
                    </strong>{" "}
                    (&gt;95%).
                  </p>
                  {canEdit && selectedTestResults.test.status !== "completed" && (
                    <button
                      onClick={() =>
                        handleApplyWinner(
                          selectedTestResults.test.id,
                          selectedTestResults.results.recommended_winner as "a" | "b"
                        )
                      }
                      disabled={applyingWinner}
                      className="mt-2 px-3 py-1.5 rounded-lg bg-emerald-600 text-white font-medium hover:bg-emerald-700 transition-colors flex items-center gap-1.5"
                    >
                      {applyingWinner && <Loader2 size={12} className="animate-spin" />}
                      Aplicar Ganador
                    </button>
                  )}
                </div>
              </div>
            ) : (
              <div className="p-4 rounded-xl bg-slate-500/10 border border-slate-500/20 text-slate-600 dark:text-slate-400 text-xs flex items-center gap-2">
                <Sparkles size={16} />
                <span>
                  Acumulando datos. Confianza actual:{" "}
                  <strong>
                    {(selectedTestResults.results.statistical_significance * 100).toFixed(1)}%
                  </strong>{" "}
                  (requiere &gt;95%).
                </span>
              </div>
            )}

            {/* Progress Bars for A vs B */}
            <div className="space-y-4 border-t border-b border-[hsl(var(--border))] py-4">
              <h4 className="font-semibold text-xs text-[hsl(var(--text-secondary))] uppercase tracking-wider">
                Comparativa de Variantes
              </h4>

              {/* Views */}
              <div className="space-y-1.5 text-xs">
                <div className="flex justify-between font-medium">
                  <span>Visualizaciones</span>
                  <span>A: {selectedTestResults.results.views_a} | B: {selectedTestResults.results.views_b}</span>
                </div>
                <div className="h-3 rounded-full bg-[hsl(var(--border))] overflow-hidden flex">
                  <div
                    style={{
                      width: `${
                        selectedTestResults.results.views_a + selectedTestResults.results.views_b > 0
                          ? (selectedTestResults.results.views_a /
                              (selectedTestResults.results.views_a + selectedTestResults.results.views_b)) *
                            100
                          : 50
                      }%`,
                    }}
                    className="bg-blue-500 h-full"
                    title="Variante A"
                  />
                  <div
                    style={{
                      width: `${
                        selectedTestResults.results.views_a + selectedTestResults.results.views_b > 0
                          ? (selectedTestResults.results.views_b /
                              (selectedTestResults.results.views_a + selectedTestResults.results.views_b)) *
                            100
                          : 50
                      }%`,
                    }}
                    className="bg-cyan-500 h-full"
                    title="Variante B"
                  />
                </div>
              </div>

              {/* Clicks */}
              <div className="space-y-1.5 text-xs">
                <div className="flex justify-between font-medium">
                  <span>Clics</span>
                  <span>A: {selectedTestResults.results.clicks_a} | B: {selectedTestResults.results.clicks_b}</span>
                </div>
                <div className="h-3 rounded-full bg-[hsl(var(--border))] overflow-hidden flex">
                  <div
                    style={{
                      width: `${
                        selectedTestResults.results.clicks_a + selectedTestResults.results.clicks_b > 0
                          ? (selectedTestResults.results.clicks_a /
                              (selectedTestResults.results.clicks_a + selectedTestResults.results.clicks_b)) *
                            100
                          : 50
                      }%`,
                    }}
                    className="bg-blue-500 h-full"
                  />
                  <div
                    style={{
                      width: `${
                        selectedTestResults.results.clicks_a + selectedTestResults.results.clicks_b > 0
                          ? (selectedTestResults.results.clicks_b /
                              (selectedTestResults.results.clicks_a + selectedTestResults.results.clicks_b)) *
                            100
                          : 50
                      }%`,
                    }}
                    className="bg-cyan-500 h-full"
                  />
                </div>
              </div>

              {/* Conversion Rates */}
              <div className="grid grid-cols-2 gap-3 pt-2 text-center text-xs">
                <div className="p-3 rounded-xl border border-blue-500/20 bg-blue-500/5">
                  <div className="text-[10px] text-blue-600 dark:text-blue-400 font-semibold uppercase">Variante A</div>
                  <div className="text-lg font-bold">
                    {(selectedTestResults.results.conversion_rate_a * 100).toFixed(2)}%
                  </div>
                  <div className="text-[10px] text-[hsl(var(--text-secondary))]">Tasa de Conversión</div>
                </div>

                <div className="p-3 rounded-xl border border-cyan-500/20 bg-cyan-500/5">
                  <div className="text-[10px] text-cyan-600 dark:text-cyan-400 font-semibold uppercase">Variante B</div>
                  <div className="text-lg font-bold">
                    {(selectedTestResults.results.conversion_rate_b * 100).toFixed(2)}%
                  </div>
                  <div className="text-[10px] text-[hsl(var(--text-secondary))]">Tasa de Conversión</div>
                </div>
              </div>
            </div>

            {/* Manual Winner Application Actions */}
            {canEdit && selectedTestResults.test.status !== "completed" && (
              <div className="space-y-2 pt-2">
                <label className="text-xs font-semibold">Aplicar Ganador Manualmente:</label>
                <div className="flex gap-2">
                  <button
                    onClick={() => handleApplyWinner(selectedTestResults.test.id, "a")}
                    disabled={applyingWinner}
                    className="flex-1 py-2 text-xs font-medium rounded-xl border border-blue-500/30 text-blue-600 dark:text-blue-400 hover:bg-blue-500/10"
                  >
                    Aplicar Variante A
                  </button>
                  <button
                    onClick={() => handleApplyWinner(selectedTestResults.test.id, "b")}
                    disabled={applyingWinner}
                    className="flex-1 py-2 text-xs font-medium rounded-xl border border-cyan-500/30 text-cyan-600 dark:text-cyan-400 hover:bg-cyan-500/10"
                  >
                    Aplicar Variante B
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </SidePanel>

      {/* Delete Confirmation Modal */}
      <AnimatePresence>
        {pendingDelete && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="w-full max-w-md p-6 rounded-2xl bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border))] space-y-4 shadow-xl"
            >
              <h3 className="text-base font-bold">¿Eliminar Experimento?</h3>
              <p className="text-xs text-[hsl(var(--text-secondary))]">
                Esta acción eliminará el experimento <strong>{pendingDelete.name}</strong> y sus eventos registrados de forma permanente.
              </p>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  onClick={() => setPendingDelete(null)}
                  className="px-4 py-2 text-xs font-medium rounded-xl border border-[hsl(var(--border))]"
                >
                  Cancelar
                </button>
                <button
                  onClick={handleDelete}
                  disabled={deleting}
                  className="px-4 py-2 text-xs font-medium rounded-xl bg-red-600 text-white hover:bg-red-700 disabled:opacity-50 flex items-center gap-1.5"
                >
                  {deleting && <Loader2 size={14} className="animate-spin" />}
                  Eliminar
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
