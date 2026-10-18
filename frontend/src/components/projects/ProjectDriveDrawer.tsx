"use client";

import React, { useState, useEffect, useCallback, useRef, useMemo } from "react";
import ConfirmActionDrawer, { type ConfirmActionState } from "@/components/ConfirmActionDrawer";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";
import type { ProjectFileRecord, ProjectFilesSummary } from "@/types/projects";
import { FolderArchive, Upload, Link2, Search, FileText, FileSpreadsheet, FileCode, Image as ImageIcon, Music, Video, HardDrive, Trash2, Eye, ExternalLink, Download, RefreshCw, Globe, CheckSquare, GitBranch, AlertTriangle, Settings2 } from "lucide-react";
import clsx from "clsx";
import { toast } from "sonner";
import { ProjectFileViewerDrawer } from "./ProjectFileViewerDrawer";
import { getSafeProjectLink } from "@/lib/projects/safeProjectLink";

interface ProjectDriveDrawerProps {
  projectId: string;
  isOpen: boolean;
  onClose: () => void;
  onFileUpdated?: () => void;
}

const CATEGORIES = [
  { id: "ALL", label: "Todas" },
  { id: "general", label: "General" },
  { id: "actas", label: "Actas y Minutas" },
  { id: "disenos", label: "Diseños & Planos" },
  { id: "finanzas", label: "Finanzas & Presupuesto" },
  { id: "contratos", label: "Contratos & Legal" },
  { id: "informes", label: "Informes & Entregables" },
  { id: "multimedia", label: "Multimedia & Fotos" },
];

const SOURCES: { id: string; label: string }[] = [
  { id: "ALL", label: "Todos los orígenes" },
  { id: "local", label: "Archivos Locales" },
  { id: "drive", label: "Google Drive & Docs" },
  { id: "dropbox", label: "Dropbox" },
  { id: "onedrive", label: "OneDrive" },
];

type WbsTraceabilityFilter = "ALL" | "LINKED" | "ORPHAN";

const WBS_TRACEABILITY_FILTERS: { key: WbsTraceabilityFilter; label: string }[] = [
  { key: "ALL", label: "Todos" },
  { key: "LINKED", label: "Vinculados a EDT" },
  { key: "ORPHAN", label: "Huérfanos sin EDT" },
];

/** Los 4 pilares documentales del PMBOK 7ma Ed. — Artifact & Configuration Management. */
const PMI_DOC_PILLARS: { key: string; label: string; matches: (category: string) => boolean }[] = [
  { key: "gobernanza", label: "Gobernanza / Actas", matches: (c) => c === "actas" },
  { key: "linea-base", label: "Línea Base Técnica", matches: (c) => c === "disenos" },
  { key: "finanzas", label: "Finanzas / Adquisiciones", matches: (c) => c === "finanzas" || c === "contratos" },
  { key: "informes", label: "Informes / Aceptación", matches: (c) => c === "informes" },
];

interface ProjectDriveDrawerProps {
  projectId: string;
  isOpen: boolean;
  onClose: () => void;
  onFileUpdated?: () => void;
}

export function ProjectDriveDrawer({
  projectId,
  isOpen,
  onClose: _onClose,
  onFileUpdated,
}: ProjectDriveDrawerProps) {
  const { token } = useAuth();

  const [activeTab, setActiveTab] = useState<"explorer" | "upload" | "link-drive">("explorer");
  const [loading, setLoading] = useState(false);
  const [summary, setSummary] = useState<ProjectFilesSummary | null>(null);
  const [files, setFiles] = useState<ProjectFileRecord[]>([]);

  // Filtros
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("ALL");
  const [selectedSource, setSelectedSource] = useState("ALL");
  const [selectedTaskId, setSelectedTaskId] = useState("ALL");
  const [traceabilityFilter, setTraceabilityFilter] = useState<WbsTraceabilityFilter>("ALL");
  const [projectTasks, setProjectTasks] = useState<Array<{ id: string; title: string }>>([]);

  // Estado de visor embebido
  const [viewingFile, setViewingFile] = useState<ProjectFileRecord | null>(null);
  const [confirmAction, setConfirmAction] = useState<ConfirmActionState>(null);

  // Formulario Local Upload
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadCategory, setUploadCategory] = useState("general");
  const [uploadTaskId, setUploadTaskId] = useState("none");
  const [uploadCustomName, setUploadCustomName] = useState("");
  const [uploadDescription, setUploadDescription] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragOver, setIsDragOver] = useState(false);

  // Formulario Link Drive
  const [driveUrl, setDriveUrl] = useState("");
  const [driveName, setDriveName] = useState("");
  const [driveCategory, setDriveCategory] = useState("general");
  const [driveTaskId, setDriveTaskId] = useState("none");
  const [driveDescription, setDriveDescription] = useState("");
  const [isLinking, setIsLinking] = useState(false);

  // Cargar actividades/tareas del proyecto para el filtro
  useEffect(() => {
    if (!isOpen || !projectId || !token) return;
    let active = true;
    apiFetch<Array<{ id?: string; title?: string; name?: string; file_source?: string }>>(`/projects/${projectId}/tasks`, { token })
      .then((data) => {
        if (!active || !Array.isArray(data)) return;
        setProjectTasks(
          data
            .filter((t) => t && t.id && (t.title || (!t.file_source && t.name)))
            .map((t) => ({
              id: String(t.id),
              title: t.title || t.name || `Actividad #${t.id}`,
            }))
        );
      })
      .catch(() => {
        // En caso de que no haya tareas o endpoint mockeado, continúa normalmente
      });
    return () => {
      active = false;
    };
  }, [isOpen, projectId, token]);

  const availableTasks = useMemo(() => {
    const map = new Map<string, string>();
    for (const t of projectTasks) {
      map.set(t.id, t.title);
    }
    for (const f of files) {
      if (f.task_id && f.task_title && !map.has(f.task_id)) {
        map.set(f.task_id, f.task_title);
      }
    }
    return Array.from(map.entries()).map(([id, title]) => ({ id, title }));
  }, [projectTasks, files]);

  // Carga de Archivos
  const loadFiles = useCallback(async () => {
    if (!token || !projectId) return;
    setLoading(true);
    try {
      const query: Record<string, string> = {};
      if (selectedCategory !== "ALL") query.category = selectedCategory;
      if (selectedSource !== "ALL") query.file_source = selectedSource;
      if (selectedTaskId !== "ALL") query.task_id = selectedTaskId;
      if (searchQuery.trim()) query.search = searchQuery.trim();

      const [filesData, summaryData] = await Promise.all([
        apiFetch<ProjectFileRecord[]>(`/projects/${projectId}/files`, {
          token,
          query,
        }),
        apiFetch<ProjectFilesSummary>(`/projects/${projectId}/files/summary`, {
          token,
        }),
      ]);

      if (Array.isArray(filesData)) {
        setFiles(filesData);
      }
      if (summaryData) {
        setSummary(summaryData);
      }
    } catch {
      toast.error("Error al cargar Drive");
    } finally {
      setLoading(false);
    }
  }, [token, projectId, selectedCategory, selectedSource, selectedTaskId, searchQuery]);

  const displayedFiles = useMemo(() => {
    return files.filter((file) => {
      if (selectedTaskId !== "ALL" && file.task_id !== selectedTaskId) {
        return false;
      }
      if (traceabilityFilter === "LINKED" && !file.task_id) {
        return false;
      }
      if (traceabilityFilter === "ORPHAN" && file.task_id) {
        return false;
      }
      return true;
    });
  }, [files, selectedTaskId, traceabilityFilter]);

  /** Gestión de la Configuración y Trazabilidad EDT de Artefactos PMI (PMBOK 7ma Ed.). */
  const pmiConfigAudit = useMemo(() => {
    const total = files.length;
    const linked = files.filter((f) => Boolean(f.task_id)).length;
    const orphans = total - linked;
    const traceabilityPct = total > 0 ? Math.round((linked / total) * 100) : 0;
    const unlinkedDeliverables = files.filter(
      (f) => !f.task_id && (f.category === "informes" || f.category === "disenos"),
    );
    const pillars = PMI_DOC_PILLARS.map((pillar) => ({
      ...pillar,
      covered: files.some((f) => pillar.matches(f.category ?? "")),
    }));
    return {
      total,
      linked,
      orphans,
      traceabilityPct,
      unlinkedDeliverables,
      pillars,
      pillarsCovered: pillars.filter((p) => p.covered).length,
    };
  }, [files]);

  useEffect(() => {
    if (isOpen) {
      void loadFiles();
    }
  }, [isOpen, loadFiles]);

  // Manejo de Subida Local
  const handleLocalUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !projectId || !uploadFile) {
      toast.error("Por favor selecciona un archivo");
      return;
    }

    const MAX_SIZE_MB = 50;
    if (uploadFile.size > MAX_SIZE_MB * 1024 * 1024) {
      toast.error(`El archivo supera el tamaño máximo permitido (${MAX_SIZE_MB}MB)`);
      return;
    }

    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", uploadFile);
      if (uploadCategory) formData.append("category", uploadCategory);
      if (uploadTaskId && uploadTaskId !== "none") formData.append("task_id", uploadTaskId);
      let finalName = uploadCustomName.trim();
      if (finalName && uploadFile.name && uploadFile.name.includes(".")) {
        const origExt = uploadFile.name.slice(uploadFile.name.lastIndexOf("."));
        if (!finalName.toLowerCase().endsWith(origExt.toLowerCase()) && !finalName.includes(".")) {
          finalName = `${finalName}${origExt}`;
        }
      }
      if (finalName) formData.append("name", finalName);
      if (uploadDescription.trim()) formData.append("description", uploadDescription.trim());

      await apiFetch<ProjectFileRecord>(`/projects/${projectId}/files/upload`, {
        method: "POST",
        body: formData,
        token,
      });

      toast.success("Archivo subido a Drive exitosamente");
      setUploadFile(null);
      setUploadTaskId("none");
      setUploadCustomName("");
      setUploadDescription("");
      if (fileInputRef.current) fileInputRef.current.value = "";
      setActiveTab("explorer");
      void loadFiles();
      onFileUpdated?.();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error al subir archivo";
      toast.error(msg);
    } finally {
      setIsUploading(false);
    }
  };

  // Manejo de Enlace Google Drive
  const handleLinkDrive = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !projectId || !driveUrl.trim()) {
      toast.error("Ingresa la URL del documento o carpeta de Google Drive");
      return;
    }

    setIsLinking(true);
    try {
      await apiFetch<ProjectFileRecord>(`/projects/${projectId}/files/link-drive`, {
        method: "POST",
        body: {
          drive_url: driveUrl.trim(),
          name: driveName.trim() || undefined,
          category: driveCategory,
          task_id: driveTaskId && driveTaskId !== "none" ? driveTaskId : undefined,
          description: driveDescription.trim() || undefined,
        },
        token,
      });

      toast.success("Documento de Google Drive vinculado exitosamente");
      setDriveUrl("");
      setDriveName("");
      setDriveTaskId("none");
      setDriveDescription("");
      setActiveTab("explorer");
      void loadFiles();
      onFileUpdated?.();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error al vincular Google Drive";
      toast.error(msg);
    } finally {
      setIsLinking(false);
    }
  };

  // Eliminación de archivo (soft-delete)
  const handleDeleteFile = async (fileId: string, fileName: string) => {
    if (!token || !projectId) return;
    try {
      await apiFetch(`/projects/${projectId}/files/${fileId}`, {
        method: "DELETE",
        token,
      });
      toast.success(`"${fileName}" eliminado de Drive`);
      void loadFiles();
      onFileUpdated?.();
    } catch (error) {
      toast.error("Error al eliminar archivo");
      throw error;
    }
  };

  const requestDeleteFile = (file: ProjectFileRecord) => {
    setConfirmAction({
      title: "Eliminar archivo de la bóveda",
      description: `¿Deseas quitar “${file.name}” de la bóveda del proyecto? Dejará de aparecer en este proyecto.`,
      confirmLabel: "Eliminar",
      destructive: true,
      onConfirm: () => handleDeleteFile(file.id, file.name),
    });
  };

  const formatBytes = (bytes?: number | null) => {
    if (!bytes || bytes <= 0) return "0 KB";
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const getFileIcon = (file: ProjectFileRecord) => {
    if (file.file_source === "drive") {
      return <Globe size={18} className="text-[hsl(var(--primary))]" />;
    }
    const t = (file.file_type || "").toLowerCase();
    const n = file.name.toLowerCase();
    if (t.includes("pdf") || n.endsWith(".pdf")) {
      return <FileText size={18} className="text-[hsl(var(--destructive))]" />;
    }
    if (t.includes("sheet") || t.includes("excel") || n.endsWith(".xlsx") || n.endsWith(".csv")) {
      return <FileSpreadsheet size={18} className="text-[hsl(var(--success))]" />;
    }
    if (t.startsWith("image/") || /\.(png|jpe?g|webp|gif)$/i.test(n)) {
      return <ImageIcon size={18} className="text-[hsl(var(--warning))]" />;
    }
    if (t.startsWith("audio/") || /\.(mp3|wav|ogg)$/i.test(n)) {
      return <Music size={18} className="text-[hsl(var(--primary))]" />;
    }
    if (t.startsWith("video/") || /\.(mp4|mov)$/i.test(n)) {
      return <Video size={18} className="text-[hsl(var(--destructive))]" />;
    }
    return <FileCode size={18} className="text-[hsl(var(--text-secondary))]" />;
  };

  return (
    <>
      <>
        <div className="flex flex-col h-full bg-[hsl(var(--surface-1))] text-[hsl(var(--text-primary))]">
          {/* Cabecera y Resumen Métrico */}
          <div className="px-5 pt-3.5 pb-3 border-b border-[hsl(var(--border))] space-y-3 bg-[hsl(var(--surface-2))]/50">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-bold flex items-center gap-2">
                  <FolderArchive size={18} className="text-[hsl(var(--primary))]" />
                  Drive
                </h2>
                <p className="text-2xs text-[hsl(var(--text-secondary))]">
                  Almacenamiento unificado de planos, actas, minutas y documentos sincronizados de Google Workspace
                </p>
              </div>

              <button
                type="button"
                onClick={() => void loadFiles()}
                disabled={loading}
                title="Actualizar lista"
                aria-label="Actualizar lista de archivos"
                className="p-1.5 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] hover:bg-[hsl(var(--surface-3))] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] transition-colors"
              >
                <RefreshCw size={13} className={clsx(loading && "animate-spin")} />
              </button>
            </div>

            {/* Tarjetas Métricas Rápidas */}
            <div className="grid grid-cols-3 gap-2 pt-0.5">
              <div className="p-2 rounded-lg bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] flex items-center gap-2">
                <div className="p-1.5 rounded-md bg-[hsl(var(--primary))]/10 text-[hsl(var(--primary))]">
                  <FolderArchive size={15} />
                </div>
                <div>
                  <p className="text-2xs uppercase font-semibold text-[hsl(var(--text-secondary))]">
                    Total Archivos
                  </p>
                  <p className="text-xs font-extrabold">{summary?.total_files ?? files.length}</p>
                </div>
              </div>

              <div className="p-2 rounded-lg bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] flex items-center gap-2">
                <div className="p-1.5 rounded-md bg-[hsl(var(--success))]/10 text-[hsl(var(--success))]">
                  <HardDrive size={15} />
                </div>
                <div>
                  <p className="text-2xs uppercase font-semibold text-[hsl(var(--text-secondary))]">
                    Peso Local
                  </p>
                  <p className="text-xs font-extrabold text-[hsl(var(--success))]">
                    {formatBytes(summary?.total_size_bytes)}
                  </p>
                </div>
              </div>

              <div className="p-2 rounded-lg bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] flex items-center gap-2">
                <div className="p-1.5 rounded-md bg-[hsl(var(--primary))]/10 text-[hsl(var(--primary))]">
                  <Globe size={15} />
                </div>
                <div>
                  <p className="text-2xs uppercase font-semibold text-[hsl(var(--text-secondary))]">
                    En Google Drive
                  </p>
                  <p className="text-xs font-extrabold text-[hsl(var(--primary))]">
                    {summary?.by_source?.drive ?? 0} Docs
                  </p>
                </div>
              </div>
            </div>

            {/* Pestañas de Acción */}
            <div className="flex items-center gap-1.5 border-b border-[hsl(var(--border))] pt-1">
              <button
                onClick={() => setActiveTab("explorer")}
                className={clsx(
                  "px-3 py-1.5 text-2xs font-bold uppercase tracking-wider rounded-t-lg transition-all flex items-center gap-1.5",
                  activeTab === "explorer"
                    ? "bg-[hsl(var(--surface-1))] text-[hsl(var(--primary))] border-t-2 border-t-[hsl(var(--primary))] border-x border-[hsl(var(--border))]"
                    : "text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] hover:bg-[hsl(var(--surface-2))]"
                )}
              >
                <FolderArchive size={13} /> Explorador ({files.length})
              </button>

              <button
                onClick={() => setActiveTab("upload")}
                className={clsx(
                  "px-3 py-1.5 text-2xs font-bold uppercase tracking-wider rounded-t-lg transition-all flex items-center gap-1.5",
                  activeTab === "upload"
                    ? "bg-[hsl(var(--surface-1))] text-[hsl(var(--primary))] border-t-2 border-t-[hsl(var(--primary))] border-x border-[hsl(var(--border))]"
                    : "text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] hover:bg-[hsl(var(--surface-2))]"
                )}
              >
                <Upload size={13} /> Subir Local
              </button>

              <button
                onClick={() => setActiveTab("link-drive")}
                className={clsx(
                  "px-3 py-1.5 text-2xs font-bold uppercase tracking-wider rounded-t-lg transition-all flex items-center gap-1.5",
                  activeTab === "link-drive"
                    ? "bg-[hsl(var(--surface-1))] text-[hsl(var(--primary))] border-t-2 border-t-[hsl(var(--primary))] border-x border-[hsl(var(--border))]"
                    : "text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] hover:bg-[hsl(var(--surface-2))]"
                )}
              >
                <Link2 size={13} /> Vincular Google Drive
              </button>
            </div>
          </div>

          {/* Cuerpo según Pestaña */}
          <div className="flex-1 overflow-y-auto p-5">
            {/* ── PESTAÑA 1: EXPLORADOR DE ARCHIVOS ── */}
            {activeTab === "explorer" && (
              <div className="space-y-4">
                {/* Controles de Búsqueda y Filtros */}
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5">
                  <div className="relative">
                    <Search
                      size={14}
                      className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]"
                    />
                    <input
                      type="text"
                      aria-label="Buscar archivos por nombre"
                      placeholder="Buscar por nombre..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="w-full pl-8 pr-3 py-1.5 text-xs rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-primary))] focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]"
                    />
                  </div>

                  <div>
                    <select
                      aria-label="Filtrar por categoría"
                      value={selectedCategory}
                      onChange={(e) => setSelectedCategory(e.target.value)}
                      className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-primary))] focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]"
                    >
                      {CATEGORIES.map((cat) => (
                        <option key={cat.id} value={cat.id}>
                          {cat.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <select
                      aria-label="Filtrar por origen"
                      value={selectedSource}
                      onChange={(e) => setSelectedSource(e.target.value)}
                      className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-primary))] focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]"
                    >
                      {SOURCES.map((src) => (
                        <option key={src.id} value={src.id}>
                          {src.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <select
                      aria-label="Filtrar por actividad"
                      value={selectedTaskId}
                      onChange={(e) => setSelectedTaskId(e.target.value)}
                      className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-primary))] focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]"
                    >
                      <option value="ALL">Todas las actividades</option>
                      {availableTasks.map((t) => (
                        <option key={t.id} value={t.id}>
                          {t.title}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                {/* Diagnóstico de Gestión de la Configuración y Trazabilidad EDT de Artefactos PMI */}
                <div
                  data-testid="drive-pmi-config-audit"
                  className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]/40 p-3.5 space-y-3"
                >
                  <div className="flex items-center gap-2">
                    <Settings2 size={14} className="text-[hsl(var(--primary))]" />
                    <p className="text-2xs font-bold uppercase tracking-wider text-[hsl(var(--text-primary))]">
                      Gestión de la Configuración y Trazabilidad EDT (PMBOK 7)
                    </p>
                  </div>

                  {/* (a) Trazabilidad EDT (WBS Traceability) */}
                  <div className="flex flex-wrap items-center gap-2 text-2xs">
                    <span className="font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
                      Trazabilidad EDT:
                    </span>
                    <span
                      className="px-2 py-0.5 rounded-full font-extrabold border"
                      style={{
                        color: pmiConfigAudit.traceabilityPct >= 80 ? "hsl(var(--success))" : "hsl(var(--warning-text))",
                        borderColor: pmiConfigAudit.traceabilityPct >= 80 ? "hsl(var(--success) / 0.35)" : "hsl(var(--warning) / 0.4)",
                      }}
                    >
                      {pmiConfigAudit.traceabilityPct}%
                    </span>
                    <span className="text-[hsl(var(--text-secondary))]">
                      <span className="font-bold text-[hsl(var(--text-primary))]">{pmiConfigAudit.linked}</span> vinculados
                      ·{" "}
                      <span className="font-bold text-[hsl(var(--text-primary))]">{pmiConfigAudit.orphans}</span> huérfanos
                      sin paquete de trabajo
                    </span>
                    <GitBranch size={12} className="text-[hsl(var(--text-secondary))]" aria-hidden />
                  </div>

                  {pmiConfigAudit.unlinkedDeliverables.length > 0 && (
                    <div
                      className="flex items-start gap-2 rounded-lg border p-2.5"
                      style={{
                        borderColor: "hsl(var(--destructive) / 0.35)",
                        backgroundColor: "hsl(var(--destructive) / 0.08)",
                      }}
                    >
                      <AlertTriangle size={13} className="text-[hsl(var(--destructive))] mt-0.5 shrink-0" />
                      <p className="text-2xs leading-relaxed text-[hsl(var(--text-primary))]">
                        <span className="font-bold text-[hsl(var(--destructive))]">Entregables sin vínculo EDT:</span>{" "}
                        {pmiConfigAudit.unlinkedDeliverables.length} archivo(s) de informes o diseños no están vinculados a
                        un paquete de trabajo. Vinculalos para mantener la trazabilidad binaria EDT-entregable.
                      </p>
                    </div>
                  )}

                  {/* (b) Cobertura de los 4 Pilares Documentales PMI */}
                  <div className="space-y-1.5">
                    <p className="text-2xs">
                      <span className="font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
                        Cobertura Documental PMI:{" "}
                      </span>
                      <span
                        className="font-extrabold"
                        style={{
                          color: pmiConfigAudit.pillarsCovered === 4 ? "hsl(var(--success))" : "hsl(var(--warning-text))",
                        }}
                      >
                        {pmiConfigAudit.pillarsCovered}/4 pilares
                      </span>
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {pmiConfigAudit.pillars.map((pillar) => (
                        <span
                          key={pillar.key}
                          title={
                            pillar.covered
                              ? `${pillar.label}: cubierta por documentos en Drive`
                              : `${pillar.label}: sin documentos aún`
                          }
                          className="px-2 py-0.5 rounded-full text-2xs font-semibold border"
                          style={{
                            color: pillar.covered ? "hsl(var(--success))" : "hsl(var(--text-secondary))",
                            borderColor: pillar.covered ? "hsl(var(--success) / 0.35)" : "hsl(var(--border))",
                            backgroundColor: pillar.covered ? "hsl(var(--success) / 0.08)" : "hsl(var(--surface-1))",
                          }}
                        >
                          {pillar.covered ? "✓ " : "· "}{pillar.label}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Filtro rápido de trazabilidad EDT */}
                <div
                  data-testid="drive-wbs-traceability-filter"
                  className="flex items-center gap-1.5 flex-wrap"
                >
                  {WBS_TRACEABILITY_FILTERS.map((f) => {
                    const isActive = traceabilityFilter === f.key;
                    return (
                      <button
                        key={f.key}
                        type="button"
                        aria-pressed={isActive}
                        onClick={() => setTraceabilityFilter(f.key)}
                        className={clsx(
                          "px-2.5 py-1 rounded-lg text-2xs font-semibold uppercase tracking-wider border transition-all",
                          isActive ? "font-bold" : "opacity-70 hover:opacity-100",
                        )}
                        style={{
                          backgroundColor: isActive ? "hsl(var(--primary) / 0.12)" : "hsl(var(--surface-1))",
                          borderColor: isActive ? "hsl(var(--primary) / 0.35)" : "hsl(var(--border))",
                          color: isActive ? "hsl(var(--primary))" : "hsl(var(--text-secondary))",
                        }}
                      >
                        {f.label}
                      </button>
                    );
                  })}
                </div>

                {/* Lista de Archivos */}
                {loading && displayedFiles.length === 0 ? (
                  <div className="py-12 flex flex-col items-center justify-center gap-2 text-[hsl(var(--text-secondary))]">
                    <div className="w-6 h-6 border-2 border-[hsl(var(--primary))] border-t-transparent rounded-full animate-spin" />
                    <p className="text-2xs">Cargando archivos...</p>
                  </div>
                ) : displayedFiles.length === 0 ? (
                  <div className="py-12 text-center border-2 border-dashed border-[hsl(var(--border))] rounded-xl bg-[hsl(var(--surface-2))]/30 flex flex-col items-center justify-center p-6 space-y-3">
                    <FolderArchive size={36} className="text-[hsl(var(--text-secondary))]" />
                    <div className="space-y-1">
                      <p className="text-xs font-bold text-[hsl(var(--text-primary))]">
                        {traceabilityFilter !== "ALL"
                          ? "No hay archivos con este nivel de trazabilidad EDT"
                          : selectedTaskId !== "ALL"
                            ? "No hay archivos vinculados a esta actividad"
                            : "No hay archivos en Drive"}
                      </p>
                      <p className="text-2xs text-[hsl(var(--text-secondary))] max-w-sm">
                        Sube planos, especificaciones o vincula carpetas y documentos de Google Drive para mantener todo centralizado en el proyecto.
                      </p>
                    </div>
                    <div className="flex gap-2 pt-2">
                      <button
                        onClick={() => setActiveTab("upload")}
                        className="px-3 py-1.5 bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] rounded-lg text-2xs font-bold uppercase tracking-wider flex items-center gap-1.5 shadow"
                      >
                        <Upload size={12} /> Subir archivo
                      </button>
                      <button
                        onClick={() => setActiveTab("link-drive")}
                        className="px-3 py-1.5 bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] text-[hsl(var(--text-primary))] rounded-lg text-2xs font-bold uppercase tracking-wider flex items-center gap-1.5 hover:bg-[hsl(var(--surface-2))]"
                      >
                        <Link2 size={12} /> Vincular Drive
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 xl:grid-cols-2 2xl:grid-cols-3 gap-3">
                    {displayedFiles.map((file) => {
                      const safeFileUrl = getSafeProjectLink(file.file_url);
                      return (
                        <div
                          key={file.id}
                          className="group p-3 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] hover:border-[hsl(var(--primary))]/50 hover:shadow-sm transition-all flex items-center justify-between gap-3"
                        >
                        {/* Icono e Info Principal */}
                        <div className="flex items-center gap-3 min-w-0 flex-1">
                          <div className="p-2 rounded-lg bg-[hsl(var(--surface-2))] shrink-0 group-hover:scale-105 transition-transform">
                            {getFileIcon(file)}
                          </div>
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center gap-2 mb-1 flex-wrap">
                              <p className="text-xs font-bold text-[hsl(var(--text-primary))] truncate group-hover:text-[hsl(var(--primary))] transition-colors">
                                {file.name}
                              </p>
                              <span className="text-2xs font-semibold px-2 py-0.5 rounded-full bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))]">
                                {file.category}
                              </span>
                              {file.file_source === "drive" && (
                                <span className="text-2xs font-extrabold px-1.5 py-0.5 rounded bg-[hsl(var(--primary))]/15 text-[hsl(var(--primary))] uppercase">
                                  Drive
                                </span>
                              )}
                              {file.task_title ? (
                                <span
                                  data-testid={`file-task-badge-${file.id}`}
                                  className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-2xs font-bold bg-[hsl(var(--primary)/0.12)] text-[hsl(var(--primary))] border border-[hsl(var(--primary)/0.25)] max-w-[220px]"
                                  title={`Actividad vinculada: ${file.task_title}`}
                                >
                                  <CheckSquare size={11} className="shrink-0" />
                                  <span className="truncate">Actividad: {file.task_title}</span>
                                </span>
                              ) : (
                                <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-2xs text-[hsl(var(--text-secondary))]/60 italic bg-[hsl(var(--surface-2))]">
                                  Sin actividad
                                </span>
                              )}
                            </div>
                            <div className="flex items-center gap-3 text-2xs text-[hsl(var(--text-secondary))] flex-wrap">
                              <span>{formatBytes(file.file_size)}</span>
                              {file.uploader_name && <span>Por {file.uploader_name}</span>}
                              <span>
                                {new Date(file.created_at).toLocaleDateString("es-CO", {
                                  day: "numeric",
                                  month: "short",
                                })}
                              </span>
                            </div>
                          </div>
                        </div>

                        {/* Botones de Acción */}
                        <div className="flex items-center gap-1 shrink-0">
                          <button
                            type="button"
                            onClick={() => setViewingFile(file)}
                            aria-label={`Previsualizar ${file.name}`}
                            className="p-1.5 rounded-lg border border-[hsl(var(--border))] hover:bg-[hsl(var(--surface-2))] text-[hsl(var(--primary))] transition-colors"
                          >
                            <Eye size={14} />
                          </button>

                          {safeFileUrl && (
                            <a
                              href={safeFileUrl}
                              target="_blank"
                              rel="noopener noreferrer"
                              aria-label={`Abrir ${file.name} en pestaña nueva`}
                              className="p-1.5 rounded-lg border border-[hsl(var(--border))] hover:bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] transition-colors"
                            >
                              <ExternalLink size={14} />
                            </a>
                          )}

                          {file.file_source === "local" && safeFileUrl && (
                            <a
                              href={safeFileUrl}
                              download={file.name}
                              aria-label={`Descargar ${file.name}`}
                              className="p-1.5 rounded-lg border border-[hsl(var(--border))] hover:bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] transition-colors"
                            >
                              <Download size={14} />
                            </a>
                          )}

                          <button
                            type="button"
                            onClick={() => requestDeleteFile(file)}
                            aria-label={`Eliminar ${file.name} de la bóveda`}
                            className="p-1.5 rounded-lg border border-[hsl(var(--border))] hover:bg-[hsl(var(--destructive))]/15 text-[hsl(var(--destructive))] transition-colors"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}

            {/* ── PESTAÑA 2: SUBIR ARCHIVO LOCAL ── */}
            {activeTab === "upload" && (
              <form onSubmit={handleLocalUpload} className="space-y-4">
                <div
                  onDragOver={(e) => {
                    e.preventDefault();
                    setIsDragOver(true);
                  }}
                  onDragLeave={() => setIsDragOver(false)}
                  onDrop={(e) => {
                    e.preventDefault();
                    setIsDragOver(false);
                    if (e.dataTransfer.files?.[0]) {
                      setUploadFile(e.dataTransfer.files[0]);
                      if (!uploadCustomName) {
                        setUploadCustomName(e.dataTransfer.files[0].name);
                      }
                    }
                  }}
                  onClick={() => fileInputRef.current?.click()}
                  className={clsx(
                    "border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all flex flex-col items-center justify-center gap-3",
                    isDragOver
                      ? "border-[hsl(var(--primary))] bg-[hsl(var(--primary))]/10"
                      : "border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]/40 hover:bg-[hsl(var(--surface-2))]"
                  )}
                >
                  <input
                    type="file"
                    ref={fileInputRef}
                    onChange={(e) => {
                      if (e.target.files?.[0]) {
                        setUploadFile(e.target.files[0]);
                        if (!uploadCustomName) {
                          setUploadCustomName(e.target.files[0].name);
                        }
                      }
                    }}
                    className="hidden"
                  />
                  <div className="w-12 h-12 rounded-full bg-[hsl(var(--primary))]/15 text-[hsl(var(--primary))] flex items-center justify-center">
                    <Upload size={24} />
                  </div>
                  <div className="space-y-1">
                    <p className="text-xs font-bold text-[hsl(var(--text-primary))]">
                      {uploadFile ? uploadFile.name : "Haz clic o arrastra un archivo aquí"}
                    </p>
                    <p className="text-2xs text-[hsl(var(--text-secondary))]">
                      {uploadFile
                        ? `Tamaño: ${formatBytes(uploadFile.size)}`
                        : "Soporta PDF, Planos, Excel, Imágenes, Documentos (Máx 50MB)"}
                    </p>
                  </div>
                </div>

                <div className="space-y-3 pt-2">
                  <div>
                    <label className="block text-2xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1">
                      Nombre para mostrar en el proyecto (Opcional)
                    </label>
                    <input
                      type="text"
                      placeholder="Ej: Plano Arquitectónico Nivel 1.pdf"
                      value={uploadCustomName}
                      onChange={(e) => setUploadCustomName(e.target.value)}
                      className="w-full px-3 py-2 text-xs rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-primary))] focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]"
                    />
                  </div>

                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-2xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1">
                        Categoría Documental
                      </label>
                      <select
                        value={uploadCategory}
                        onChange={(e) => setUploadCategory(e.target.value)}
                        className="w-full px-3 py-2 text-xs rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-primary))] focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]"
                      >
                        {CATEGORIES.filter((c) => c.id !== "ALL").map((c) => (
                          <option key={c.id} value={c.id}>
                            {c.label}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="block text-2xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1">
                        Descripción o Notas (Opcional)
                      </label>
                      <input
                        type="text"
                        placeholder="Ej: Versión aprobada por comité de obra"
                        value={uploadDescription}
                        onChange={(e) => setUploadDescription(e.target.value)}
                        className="w-full px-3 py-2 text-xs rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-primary))] focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]"
                      />
                    </div>
                    <div>
                      <label className="block text-2xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1">
                        Actividad Asociada (Opcional)
                      </label>
                      <select
                        aria-label="Vincular a actividad"
                        value={uploadTaskId}
                        onChange={(e) => setUploadTaskId(e.target.value)}
                        className="w-full px-3 py-2 text-xs rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-primary))] focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]"
                      >
                        <option value="none">Sin actividad vinculada</option>
                        {availableTasks.map((t) => (
                          <option key={t.id} value={t.id}>
                            {t.title}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div className="pt-3 flex justify-end gap-2">
                    <button
                      type="button"
                      onClick={() => setActiveTab("explorer")}
                      className="px-4 py-2 rounded-lg border border-[hsl(var(--border))] text-xs font-semibold hover:bg-[hsl(var(--surface-2))]"
                    >
                      Cancelar
                    </button>
                    <button
                      type="submit"
                      disabled={!uploadFile || isUploading}
                      className="px-5 py-2 bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] rounded-lg text-xs font-bold uppercase tracking-wider shadow flex items-center gap-2 hover:opacity-90 disabled:opacity-50 transition-all"
                    >
                      {isUploading && (
                        <div className="w-3.5 h-3.5 border-2 border-current border-t-transparent rounded-full animate-spin" />
                      )}
                      Subir a Drive
                    </button>
                  </div>
                </div>
              </form>
            )}

            {/* ── PESTAÑA 3: VINCULAR GOOGLE DRIVE ── */}
            {activeTab === "link-drive" && (
              <form onSubmit={handleLinkDrive} className="space-y-4">
                <div className="p-4 rounded-xl bg-[hsl(var(--primary))]/10 border border-[hsl(var(--primary))]/20 space-y-1">
                  <div className="flex items-center gap-2 text-xs font-bold text-[hsl(var(--primary))]">
                    <Globe size={16} /> Integración Inteligente de Google Drive
                  </div>
                  <p className="text-2xs text-[hsl(var(--text-secondary))] leading-relaxed">
                    Pega cualquier enlace compartido de Google Docs, Sheets, Slides, Forms o PDFs de Google Drive. El sistema normalizará automáticamente el enlace a modo previsualización embebible para visualizarlo directamente dentro de la plataforma sin salir del proyecto.
                  </p>
                </div>

                <div className="space-y-3">
                  <div>
                    <label className="block text-2xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1">
                      URL de Google Drive o Docs <span className="text-[hsl(var(--destructive))]">*</span>
                    </label>
                    <input
                      type="url"
                      required
                      placeholder="https://docs.google.com/document/d/... o https://drive.google.com/file/d/..."
                      value={driveUrl}
                      onChange={(e) => setDriveUrl(e.target.value)}
                      className="w-full px-3 py-2 text-xs rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-primary))] focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]"
                    />
                  </div>

                  <div>
                    <label className="block text-2xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1">
                      Nombre Descriptivo del Documento
                    </label>
                    <input
                      type="text"
                      placeholder="Ej: Cuadro de Mando Integral 2026 (Drive)"
                      value={driveName}
                      onChange={(e) => setDriveName(e.target.value)}
                      className="w-full px-3 py-2 text-xs rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-primary))] focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]"
                    />
                  </div>

                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-2xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1">
                        Categoría Documental
                      </label>
                      <select
                        value={driveCategory}
                        onChange={(e) => setDriveCategory(e.target.value)}
                        className="w-full px-3 py-2 text-xs rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-primary))] focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]"
                      >
                        {CATEGORIES.filter((c) => c.id !== "ALL").map((c) => (
                          <option key={c.id} value={c.id}>
                            {c.label}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="block text-2xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1">
                        Notas Adicionales
                      </label>
                      <input
                        type="text"
                        placeholder="Ej: Archivo colaborativo en tiempo real"
                        value={driveDescription}
                        onChange={(e) => setDriveDescription(e.target.value)}
                        className="w-full px-3 py-2 text-xs rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-primary))] focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]"
                      />
                    </div>
                    <div>
                      <label className="block text-2xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1">
                        Actividad Asociada (Opcional)
                      </label>
                      <select
                        aria-label="Vincular enlace a actividad"
                        value={driveTaskId}
                        onChange={(e) => setDriveTaskId(e.target.value)}
                        className="w-full px-3 py-2 text-xs rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-primary))] focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]"
                      >
                        <option value="none">Sin actividad vinculada</option>
                        {availableTasks.map((t) => (
                          <option key={t.id} value={t.id}>
                            {t.title}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div className="pt-3 flex justify-end gap-2">
                    <button
                      type="button"
                      onClick={() => setActiveTab("explorer")}
                      className="px-4 py-2 rounded-lg border border-[hsl(var(--border))] text-xs font-semibold hover:bg-[hsl(var(--surface-2))]"
                    >
                      Cancelar
                    </button>
                    <button
                      type="submit"
                      disabled={!driveUrl.trim() || isLinking}
                      className="px-5 py-2 bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] rounded-lg text-xs font-bold uppercase tracking-wider shadow flex items-center gap-2 hover:opacity-90 disabled:opacity-50 transition-all"
                    >
                      {isLinking && (
                        <div className="w-3.5 h-3.5 border-2 border-current border-t-transparent rounded-full animate-spin" />
                      )}
                      Vincular a Drive
                    </button>
                  </div>
                </div>
              </form>
            )}
          </div>
        </div>
      </>

      <ConfirmActionDrawer action={confirmAction} onClose={() => setConfirmAction(null)} />

      {/* Visor Universal Embebido Integrado */}
      <ProjectFileViewerDrawer
        file={viewingFile}
        isOpen={Boolean(viewingFile)}
        onClose={() => setViewingFile(null)}
      />
    </>
  );
}
