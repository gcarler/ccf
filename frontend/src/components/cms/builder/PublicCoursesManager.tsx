"use client";

import React, { useCallback, useEffect, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import {
  GraduationCap,
  Plus,
  Pencil,
  ImageIcon,
  Trash2,
  ExternalLink,
  Sparkles,
  Check,
  X,
  BookOpen,
  Loader2,
  ChevronUp,
  ChevronDown,
  Clock,
  User,
  AlertTriangle,
  Tag,
  Eye,
} from "lucide-react";
import { toast } from "sonner";
import {
  CmsCourse,
  getCmsCourses,
  createCmsCourse,
  updateCmsCourse,
  deleteCmsCourse,
} from "@/lib/cms/v2";
import MediaPicker from "@/components/cms/builder/MediaPicker";

interface PublicCoursesManagerProps {
  token: string;
}

interface CourseFormData {
  title: string;
  code: string;
  slug: string;
  description: string;
  excerpt: string;
  instructor_name: string;
  modality: string;
  image_url: string;
  cta_text: string;
  is_published: boolean;
  access_level: string;
  duration_hours: number;
  sort_order: number;
}

const emptyFormData: CourseFormData = {
  title: "",
  code: "",
  slug: "",
  description: "",
  excerpt: "",
  instructor_name: "",
  modality: "online",
  image_url: "",
  cta_text: "Inscribirme",
  is_published: true,
  access_level: "persona",
  duration_hours: 0,
  sort_order: 0,
};

export default function PublicCoursesManager({
  token,
}: PublicCoursesManagerProps): React.ReactElement | null {
  const [courses, setCourses] = useState<CmsCourse[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // Drawers state (STRICT: Drawers/SidePanels only, no modals)
  const [createDrawerOpen, setCreateDrawerOpen] = useState(false);
  const [editDrawerOpen, setEditDrawerOpen] = useState(false);
  const [deleteDrawerOpen, setDeleteDrawerOpen] = useState(false);
  const [selectedCourse, setSelectedCourse] = useState<CmsCourse | null>(null);

  // Form states
  const [formData, setFormData] = useState<CourseFormData>(emptyFormData);

  // MediaPicker state
  const [mediaPickerOpen, setMediaPickerOpen] = useState(false);
  const [mediaPickerTarget, setMediaPickerTarget] = useState<"form" | "direct">("form");
  const [directPhotoCourseId, setDirectPhotoCourseId] = useState<string | null>(null);

  const fetchCourses = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getCmsCourses(token);
      setCourses(Array.isArray(data) ? data : []);
    } catch {
      toast.error("Error al cargar los cursos de la academia");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    if (token) {
      fetchCourses();
    }
  }, [token, fetchCourses]);

  // Open Create Drawer
  const handleOpenCreate = () => {
    setFormData({
      ...emptyFormData,
      sort_order: courses.length > 0 ? (courses[courses.length - 1].sort_order ?? 0) + 10 : 10,
    });
    setCreateDrawerOpen(true);
  };

  // Open Edit Drawer
  const handleOpenEdit = (course: CmsCourse) => {
    setSelectedCourse(course);
    setFormData({
      title: course.title || "",
      code: course.code || "",
      slug: course.slug || "",
      description: course.description || "",
      excerpt: course.excerpt || "",
      instructor_name: course.instructor_name || "",
      modality: course.modality || "online",
      image_url: course.image_url || "",
      cta_text: course.cta_text || "Inscribirme",
      is_published: course.is_published ?? true,
      access_level: course.access_level || "persona",
      duration_hours: course.duration_hours || 0,
      sort_order: course.sort_order ?? 0,
    });
    setEditDrawerOpen(true);
  };

  // Open Delete Drawer
  const handleOpenDelete = (course: CmsCourse) => {
    setSelectedCourse(course);
    setDeleteDrawerOpen(true);
  };

  // Submit Create
  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.title.trim()) {
      toast.error("El título del curso es obligatorio");
      return;
    }

    try {
      setSaving(true);
      const res = await createCmsCourse(formData, token);
      toast.success(`Curso "${res.title}" creado exitosamente`);
      setCreateDrawerOpen(false);
      await fetchCourses();
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Error al crear el curso");
    } finally {
      setSaving(false);
    }
  };

  // Submit Edit
  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCourse) return;
    if (!formData.title.trim()) {
      toast.error("El título del curso es obligatorio");
      return;
    }

    try {
      setSaving(true);
      const res = await updateCmsCourse(selectedCourse.id, formData, token);
      toast.success(`Curso "${res.title}" actualizado exitosamente`);
      setEditDrawerOpen(false);
      setSelectedCourse(null);
      await fetchCourses();
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Error al actualizar el curso");
    } finally {
      setSaving(false);
    }
  };

  // Submit Delete
  const handleDeleteConfirm = async () => {
    if (!selectedCourse) return;

    try {
      setSaving(true);
      await deleteCmsCourse(selectedCourse.id, token);
      toast.success("Curso archivado exitosamente");
      setDeleteDrawerOpen(false);
      setSelectedCourse(null);
      await fetchCourses();
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Error al archivar el curso");
    } finally {
      setSaving(false);
    }
  };

  // Quick Reordering (Swap sort_order with adjacent item)
  const handleQuickReorder = async (index: number, direction: "up" | "down") => {
    const targetIndex = direction === "up" ? index - 1 : index + 1;
    if (targetIndex < 0 || targetIndex >= courses.length) return;

    const current = courses[index];
    const target = courses[targetIndex];

    const currentSort = current.sort_order ?? index * 10;
    const targetSort = target.sort_order ?? targetIndex * 10;

    let newCurrentSort = targetSort;
    let newTargetSort = currentSort;
    if (newCurrentSort === newTargetSort) {
      newCurrentSort = direction === "up" ? targetSort - 1 : targetSort + 1;
    }

    // Optimistically update local state
    const updated = [...courses];
    updated[index] = { ...current, sort_order: newCurrentSort };
    updated[targetIndex] = { ...target, sort_order: newTargetSort };
    updated.sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0));
    setCourses(updated);

    try {
      await Promise.all([
        updateCmsCourse(current.id, { sort_order: newCurrentSort }, token),
        updateCmsCourse(target.id, { sort_order: newTargetSort }, token),
      ]);
      toast.success(
        `Orden actualizado: "${current.title}" ${direction === "up" ? "subió al puesto #" + (targetIndex + 1) : "bajó al puesto #" + (targetIndex + 1)}`
      );
      await fetchCourses();
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Error al guardar el nuevo orden");
      await fetchCourses();
    }
  };

  // Direct photo change from card button
  const handleDirectPhotoClick = (courseId: string) => {
    setDirectPhotoCourseId(courseId);
    setMediaPickerTarget("direct");
    setMediaPickerOpen(true);
  };

  // Form photo button
  const handleFormPhotoClick = () => {
    setMediaPickerTarget("form");
    setMediaPickerOpen(true);
  };

  // Media select callback
  const handleMediaSelect = async (item: { url?: string } | string) => {
    const url = typeof item === "string" ? item : item?.url || "";
    if (!url) return;

    if (mediaPickerTarget === "form") {
      setFormData((prev) => ({ ...prev, image_url: url }));
      setMediaPickerOpen(false);
    } else if (mediaPickerTarget === "direct" && directPhotoCourseId) {
      try {
        await updateCmsCourse(directPhotoCourseId, { image_url: url }, token);
        toast.success("Portada del curso actualizada exitosamente");
        await fetchCourses();
      } catch (err: unknown) {
        toast.error(err instanceof Error ? err.message : "No se pudo actualizar la portada");
      } finally {
        setMediaPickerOpen(false);
        setDirectPhotoCourseId(null);
      }
    }
  };

  return (
    <div className="bg-[hsl(var(--surface-1))] dark:bg-white/[0.02] border-t border-[hsl(var(--border))] dark:border-white/10 p-4 md:p-6">
      {/* ── Header ── */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-[hsl(var(--primary))/0.1] text-[hsl(var(--primary))] flex items-center justify-center">
              <GraduationCap size={18} />
            </div>
            <h2 className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white">
              Gestión de Cursos Públicos (/cursos)
            </h2>
            <span className="text-2xs font-semibold px-2 py-0.5 rounded-full bg-[hsl(var(--primary))/0.1] text-[hsl(var(--primary))] uppercase tracking-wider">
              {courses.length} Cursos
            </span>
          </div>
          <p className="text-xs text-[hsl(var(--text-secondary))] mt-1">
            Personaliza las portadas, textos, instructores, modalidad y orden del catálogo público. El curso en la posición #1 es el destacado principal en la web.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link
            href="/cursos"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-xl border border-[hsl(var(--border))] dark:border-white/10 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] hover:bg-[hsl(var(--surface-2))] transition-colors"
          >
            <ExternalLink size={13} />
            Ver Catálogo Público
          </Link>
          <button
            type="button"
            onClick={handleOpenCreate}
            className="flex items-center gap-1.5 px-4 py-2 text-xs font-bold rounded-xl bg-[hsl(var(--primary))] text-white hover:bg-[hsl(var(--primary))/0.9] shadow-sm transition-all uppercase tracking-wider"
          >
            <Plus size={14} />
            Nuevo Curso
          </button>
        </div>
      </div>

      {/* ── Banner Informativo de Orden y Destacado ── */}
      <div className="mb-6 p-4 rounded-xl border border-amber-500/20 bg-amber-500/5 flex items-start gap-3">
        <Sparkles className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />
        <div className="text-xs text-[hsl(var(--text-secondary))] leading-relaxed">
          <span className="font-bold text-[hsl(var(--text-primary))]">Prioridad y Curso Destacado: </span>
          El curso en la posición <strong className="text-amber-600 dark:text-amber-400">#1</strong> es presentado automáticamente en la tarjeta principal grande del catálogo en{" "}
          <code className="text-2xs px-1.5 py-0.5 rounded bg-[hsl(var(--surface-3))] font-mono">/cursos</code>. Los siguientes 3 aparecen en la columna lateral de recomendaciones y los demás en la cuadrícula general. Usa los botones <strong>Subir (▲)</strong> y <strong>Bajar (▼)</strong> para definir la secuencia exacta.
        </div>
      </div>

      {/* ── Loading Skeleton ── */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map((idx) => (
            <div
              key={idx}
              className="h-56 rounded-2xl bg-[hsl(var(--surface-2))] animate-pulse border border-[hsl(var(--border))] dark:border-white/5"
            />
          ))}
        </div>
      ) : courses.length === 0 ? (
        /* ── Empty State ── */
        <div className="text-center py-12 px-4 rounded-2xl border border-dashed border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-2))]">
          <div className="w-12 h-12 rounded-xl bg-[hsl(var(--primary))/0.1] text-[hsl(var(--primary))] mx-auto flex items-center justify-center mb-3">
            <BookOpen size={24} />
          </div>
          <h3 className="text-sm font-bold text-[hsl(var(--text-primary))] mb-1">
            No hay cursos registrados
          </h3>
          <p className="text-xs text-[hsl(var(--text-secondary))] max-w-sm mx-auto mb-4">
            Crea tu primer curso para que aparezca en el catálogo público de la academia.
          </p>
          <button
            type="button"
            onClick={handleOpenCreate}
            className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-bold rounded-xl bg-[hsl(var(--primary))] text-white hover:bg-[hsl(var(--primary))/0.9] transition-all uppercase tracking-wider"
          >
            <Plus size={14} /> Crear Curso
          </button>
        </div>
      ) : (
        /* ── Courses Cards Grid ── */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {courses.map((course, index) => (
            <div
              key={course.id}
              className={`group relative rounded-2xl border transition-all duration-200 overflow-hidden flex flex-col justify-between ${
                index === 0
                  ? "border-amber-500/40 bg-[hsl(var(--surface-2))] shadow-md ring-1 ring-amber-500/20"
                  : "border-[hsl(var(--border))] dark:border-white/[0.06] bg-[hsl(var(--surface-2))] hover:border-[hsl(var(--primary))/0.4]"
              }`}
            >
              {/* Card Header with Badges and Reordering Controls */}
              <div className="p-3 border-b border-[hsl(var(--border))] dark:border-white/[0.06] flex items-center justify-between bg-[hsl(var(--surface-3))/0.5]">
                <div className="flex items-center gap-1.5 flex-wrap">
                  {index === 0 ? (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-3xs font-black uppercase tracking-wider bg-amber-500/20 text-amber-700 dark:text-amber-300 border border-amber-500/30">
                      <Sparkles size={10} /> #1 Destacado Principal
                    </span>
                  ) : (
                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-3xs font-bold uppercase tracking-wider bg-[hsl(var(--surface-3))] text-[hsl(var(--text-secondary))] border border-[hsl(var(--border))]">
                      Posición #{index + 1}
                    </span>
                  )}

                  {course.is_published ? (
                    <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-3xs font-semibold bg-emerald-500/15 text-emerald-600 dark:text-emerald-400">
                      <Check size={9} /> Publicado
                    </span>
                  ) : (
                    <span className="inline-flex items-center px-1.5 py-0.5 rounded text-3xs font-semibold bg-zinc-500/15 text-zinc-500">
                      Oculto
                    </span>
                  )}
                </div>

                {/* Quick Reordering Arrows */}
                <div className="flex items-center gap-0.5 bg-[hsl(var(--surface-1))] rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-0.5 shadow-2xs">
                  <button
                    type="button"
                    disabled={index === 0}
                    onClick={() => handleQuickReorder(index, "up")}
                    title="Mover arriba en el catálogo (mayor prioridad)"
                    className="p-1 rounded hover:bg-[hsl(var(--surface-3))] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] disabled:opacity-30 disabled:hover:bg-transparent transition-colors"
                  >
                    <ChevronUp size={14} />
                  </button>
                  <button
                    type="button"
                    disabled={index === courses.length - 1}
                    onClick={() => handleQuickReorder(index, "down")}
                    title="Mover abajo en el catálogo"
                    className="p-1 rounded hover:bg-[hsl(var(--surface-3))] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] disabled:opacity-30 disabled:hover:bg-transparent transition-colors"
                  >
                    <ChevronDown size={14} />
                  </button>
                </div>
              </div>

              {/* Card Body */}
              <div className="p-4 flex gap-4 items-start">
                {/* Image Thumbnail with Direct Change Button */}
                <div className="relative w-24 h-24 rounded-xl overflow-hidden bg-[hsl(var(--surface-3))] border border-[hsl(var(--border))] dark:border-white/10 shrink-0 group/img">
                  {course.image_url ? (
                    <Image
                      src={course.image_url}
                      alt={course.title}
                      fill
                      className="object-cover transition-transform duration-300 group-hover/img:scale-105"
                      sizes="96px"
                    />
                  ) : (
                    <div className="w-full h-full flex flex-col items-center justify-center text-[hsl(var(--text-secondary))] opacity-60">
                      <GraduationCap size={28} />
                      <span className="text-3xs mt-1 font-semibold uppercase">Sin Foto</span>
                    </div>
                  )}

                  {/* Direct Change Button Overlay */}
                  <button
                    type="button"
                    onClick={() => handleDirectPhotoClick(course.id)}
                    title="Cambiar fotografía de portada"
                    className="absolute inset-0 bg-black/60 opacity-0 group-hover/img:opacity-100 flex flex-col items-center justify-center text-white text-3xs font-bold uppercase tracking-wider transition-opacity duration-200 gap-1 p-1 text-center"
                  >
                    <ImageIcon size={16} />
                    <span>Cambiar Foto</span>
                  </button>
                </div>

                {/* Course Metadata */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5 mb-1 text-3xs text-[hsl(var(--text-secondary))] uppercase tracking-wider font-semibold">
                    <Tag size={10} />
                    <span className="truncate">{course.code}</span>
                    <span>•</span>
                    <span className="capitalize">{course.modality || "online"}</span>
                  </div>

                  <h3 className="font-bold text-sm text-[hsl(var(--text-primary))] dark:text-white leading-snug line-clamp-2 mb-1">
                    {course.title}
                  </h3>

                  {course.instructor_name && (
                    <div className="flex items-center gap-1 text-xs text-[hsl(var(--primary))] font-medium mb-1.5">
                      <User size={12} />
                      <span className="truncate">{course.instructor_name}</span>
                    </div>
                  )}

                  <p className="text-xs text-[hsl(var(--text-secondary))] line-clamp-2 leading-relaxed">
                    {course.excerpt || course.description || "Sin descripción corta registrada."}
                  </p>
                </div>
              </div>

              {/* Card Footer with Meta & Actions */}
              <div className="px-4 py-3 border-t border-[hsl(var(--border))] dark:border-white/[0.06] bg-[hsl(var(--surface-3))/0.3] flex items-center justify-between gap-2">
                <div className="flex items-center gap-3 text-3xs text-[hsl(var(--text-secondary))]">
                  <span className="flex items-center gap-1 font-medium">
                    <BookOpen size={11} /> {course.lessons_count || 0} lecciones
                  </span>
                  {course.duration_hours ? (
                    <span className="flex items-center gap-1">
                      <Clock size={11} /> {course.duration_hours}h
                    </span>
                  ) : null}
                </div>

                <div className="flex items-center gap-1">
                  <Link
                    href={`/cursos/${course.slug || course.id}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    title="Ver página pública del curso"
                    className="p-1.5 rounded-lg hover:bg-[hsl(var(--surface-3))] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] transition-colors"
                  >
                    <Eye size={14} />
                  </Link>
                  <button
                    type="button"
                    onClick={() => handleOpenEdit(course)}
                    title="Editar detalles y textos del curso"
                    className="p-1.5 rounded-lg hover:bg-[hsl(var(--surface-3))] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] transition-colors"
                  >
                    <Pencil size={14} />
                  </button>
                  <button
                    type="button"
                    onClick={() => handleOpenDelete(course)}
                    title="Archivar / Ocultar curso"
                    className="p-1.5 rounded-lg hover:bg-[hsl(var(--destructive))/0.1] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--destructive))] transition-colors"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── CREATE / EDIT DRAWER (SidePanel Sliding from Right) ── */}
      {(createDrawerOpen || editDrawerOpen) && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div
            className="absolute inset-0 bg-black/50 backdrop-blur-sm animate-fadeIn"
            onClick={() => {
              setCreateDrawerOpen(false);
              setEditDrawerOpen(false);
            }}
          />
          <div className="relative w-full max-w-2xl h-full bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-2))] border-l border-[hsl(var(--border))] dark:border-white/[0.06] shadow-2xl flex flex-col z-10 animate-in slide-in-from-right duration-300">
            {/* Drawer Header */}
            <div className="px-6 py-4 border-b border-[hsl(var(--border))] dark:border-white/[0.06] flex items-center justify-between shrink-0 bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-2))]">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-[hsl(var(--primary))/0.1] text-[hsl(var(--primary))] flex items-center justify-center">
                  {createDrawerOpen ? <Plus size={16} /> : <Pencil size={16} />}
                </div>
                <h3 className="font-bold text-sm text-[hsl(var(--text-primary))] dark:text-white uppercase tracking-wider">
                  {createDrawerOpen ? "Crear Nuevo Curso Público" : "Editar Curso y Portada"}
                </h3>
              </div>
              <button
                type="button"
                onClick={() => {
                  setCreateDrawerOpen(false);
                  setEditDrawerOpen(false);
                }}
                className="w-8 h-8 rounded-lg hover:bg-[hsl(var(--surface-3))] flex items-center justify-center text-[hsl(var(--text-secondary))]"
              >
                <X size={16} />
              </button>
            </div>

            {/* Scrollable Form */}
            <form
              onSubmit={createDrawerOpen ? handleCreateSubmit : handleEditSubmit}
              className="flex-1 overflow-y-auto p-6 space-y-5"
            >
              {/* Title and Code */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="md:col-span-2">
                  <label className="block text-2xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1.5">
                    Título del Curso *
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.title}
                    onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                    placeholder="Ej: Discipulado Básico CCF"
                    className="w-full px-3.5 py-2.5 rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-transparent text-sm focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3]"
                  />
                </div>

                <div>
                  <label className="block text-2xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1.5">
                    Código de Curso
                  </label>
                  <input
                    type="text"
                    value={formData.code}
                    onChange={(e) => setFormData({ ...formData, code: e.target.value })}
                    placeholder="Auto o CCF-DISC-01"
                    className="w-full px-3.5 py-2.5 rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-transparent text-sm focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3]"
                  />
                </div>
              </div>

              {/* Photo / Cover Selector with MediaPicker */}
              <div>
                <label className="block text-2xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1.5">
                  Fotografía de Portada (Catálogo Público)
                </label>
                <div className="flex gap-3 items-center">
                  <div className="relative w-20 h-20 rounded-xl overflow-hidden bg-[hsl(var(--surface-3))] border border-[hsl(var(--border))] shrink-0">
                    {formData.image_url ? (
                      <Image
                        src={formData.image_url}
                        alt="Preview"
                        fill
                        className="object-cover"
                        sizes="80px"
                      />
                    ) : (
                      <div className="w-full h-full flex flex-col items-center justify-center text-[hsl(var(--text-secondary))] opacity-40">
                        <GraduationCap size={24} />
                      </div>
                    )}
                  </div>
                  <div className="flex-1 space-y-1.5">
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={formData.image_url}
                        onChange={(e) => setFormData({ ...formData, image_url: e.target.value })}
                        placeholder="URL de la imagen o selecciona de la biblioteca..."
                        className="flex-1 px-3 py-2 rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-transparent text-xs focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3]"
                      />
                      <button
                        type="button"
                        onClick={handleFormPhotoClick}
                        className="px-3 py-2 rounded-xl bg-[hsl(var(--primary))/0.1] text-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))/0.2] text-xs font-bold uppercase tracking-wider transition-colors shrink-0 flex items-center gap-1.5"
                      >
                        <ImageIcon size={14} /> Seleccionar
                      </button>
                    </div>
                    <p className="text-3xs text-[hsl(var(--text-secondary))]">
                      Recomendado: 1200x800 px o proporción 16:9 en alta definición.
                    </p>
                  </div>
                </div>
              </div>

              {/* Instructor and Modality */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-2xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1.5">
                    Docente / Facilitador
                  </label>
                  <input
                    type="text"
                    value={formData.instructor_name}
                    onChange={(e) => setFormData({ ...formData, instructor_name: e.target.value })}
                    placeholder="Ej: Pastor Luis Ricardo Meza"
                    className="w-full px-3.5 py-2.5 rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-transparent text-sm focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3]"
                  />
                </div>

                <div>
                  <label className="block text-2xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1.5">
                    Modalidad
                  </label>
                  <select
                    value={formData.modality}
                    onChange={(e) => setFormData({ ...formData, modality: e.target.value })}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] text-sm focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3]"
                  >
                    <option value="online">Virtual / Online</option>
                    <option value="presencial">Presencial en Sede</option>
                    <option value="hibrido">Híbrido (Online + Presencial)</option>
                  </select>
                </div>
              </div>

              {/* Excerpt (Short description for card) */}
              <div>
                <label className="block text-2xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1.5 flex items-center gap-1.5">
                  <Tag size={12} /> Resumen Corto (Tarjeta del catálogo)
                </label>
                <textarea
                  rows={2}
                  value={formData.excerpt}
                  onChange={(e) => setFormData({ ...formData, excerpt: e.target.value })}
                  placeholder="Ej: Fundamentos esenciales de la fe cristiana y crecimiento espiritual para nuevos creyentes."
                  className="w-full px-3.5 py-2 rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-transparent text-sm focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3] resize-none"
                />
              </div>

              {/* Full Description */}
              <div>
                <label className="block text-2xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1.5 flex items-center gap-1.5">
                  <BookOpen size={12} /> Descripción Completa del Curso
                </label>
                <textarea
                  rows={4}
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Detalla los objetivos de aprendizaje, a quién está dirigido y el contenido ministerial..."
                  className="w-full px-3.5 py-2.5 rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-transparent text-sm focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3]"
                />
              </div>

              {/* CTA, Hours, and Order */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="block text-3xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1">
                    Texto del Botón CTA
                  </label>
                  <input
                    type="text"
                    value={formData.cta_text}
                    onChange={(e) => setFormData({ ...formData, cta_text: e.target.value })}
                    placeholder="Inscribirme"
                    className="w-full px-3 py-2 rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-transparent text-xs focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3]"
                  />
                </div>

                <div>
                  <label className="block text-3xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1">
                    Duración Estimada (Horas)
                  </label>
                  <input
                    type="number"
                    min="0"
                    value={formData.duration_hours}
                    onChange={(e) => setFormData({ ...formData, duration_hours: parseInt(e.target.value, 10) || 0 })}
                    placeholder="24"
                    className="w-full px-3 py-2 rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-transparent text-xs focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3]"
                  />
                </div>

                <div>
                  <label className="block text-3xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1">
                    Orden de Visualización
                  </label>
                  <input
                    type="number"
                    value={formData.sort_order}
                    onChange={(e) => setFormData({ ...formData, sort_order: parseInt(e.target.value, 10) || 0 })}
                    placeholder="0"
                    className="w-full px-3 py-2 rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-transparent text-xs focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3]"
                  />
                </div>
              </div>

              {/* Status and Access Toggles */}
              <div className="p-4 rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-3))/0.3] space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-xs font-bold text-[hsl(var(--text-primary))]">Publicar en la Web</span>
                    <p className="text-3xs text-[hsl(var(--text-secondary))]">
                      Si está activo, los visitantes podrán ver e inscribirse en el curso desde /cursos.
                    </p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={formData.is_published}
                      onChange={(e) => setFormData({ ...formData, is_published: e.target.checked })}
                      className="sr-only peer"
                    />
                    <div className="w-10 h-6 bg-zinc-300 peer-focus:outline-none rounded-full peer dark:bg-zinc-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-zinc-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-[hsl(var(--primary))]"></div>
                  </label>
                </div>

                <div className="flex items-center justify-between pt-2 border-t border-[hsl(var(--border))] dark:border-white/5">
                  <div>
                    <span className="text-xs font-bold text-[hsl(var(--text-primary))]">Nivel de Acceso</span>
                    <p className="text-3xs text-[hsl(var(--text-secondary))]">
                      Controla quién puede acceder al contenido en el aula virtual.
                    </p>
                  </div>
                  <select
                    value={formData.access_level}
                    onChange={(e) => setFormData({ ...formData, access_level: e.target.value })}
                    className="px-2.5 py-1.5 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] text-xs"
                  >
                    <option value="open">Abierto (Cualquier visitante)</option>
                    <option value="persona">Comunidad CCF (Requiere cuenta)</option>
                    <option value="advanced">Avanzado (Liderazgo)</option>
                  </select>
                </div>
              </div>

              {/* Submit Buttons */}
              <div className="pt-4 border-t border-[hsl(var(--border))] dark:border-white/[0.06] flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => {
                    setCreateDrawerOpen(false);
                    setEditDrawerOpen(false);
                  }}
                  className="px-4 py-2 text-xs font-semibold rounded-xl border border-[hsl(var(--border))] dark:border-white/10 text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-3))] transition-colors"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="px-5 py-2 text-xs font-bold rounded-xl bg-[hsl(var(--primary))] text-white hover:bg-[hsl(var(--primary))/0.9] disabled:opacity-50 transition-all uppercase tracking-wider flex items-center gap-1.5 shadow-sm"
                >
                  {saving && <Loader2 size={13} className="animate-spin" />}
                  {createDrawerOpen ? "Crear Curso" : "Guardar Cambios"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── DELETE CONFIRMATION DRAWER (SidePanel Sliding from Right) ── */}
      {deleteDrawerOpen && selectedCourse && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div
            className="absolute inset-0 bg-black/50 backdrop-blur-sm animate-fadeIn"
            onClick={() => {
              setDeleteDrawerOpen(false);
              setSelectedCourse(null);
            }}
          />
          <div className="relative w-full max-w-md h-full bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-2))] border-l border-[hsl(var(--border))] dark:border-white/[0.06] shadow-2xl flex flex-col z-10 animate-in slide-in-from-right duration-300">
            {/* Header */}
            <div className="px-6 py-4 border-b border-[hsl(var(--border))] dark:border-white/[0.06] flex items-center justify-between shrink-0">
              <div className="flex items-center gap-2 text-[hsl(var(--destructive))]">
                <AlertTriangle size={18} />
                <h3 className="font-bold text-sm uppercase tracking-wider">
                  Archivar Curso
                </h3>
              </div>
              <button
                type="button"
                onClick={() => {
                  setDeleteDrawerOpen(false);
                  setSelectedCourse(null);
                }}
                className="w-8 h-8 rounded-lg hover:bg-[hsl(var(--surface-3))] flex items-center justify-center text-[hsl(var(--text-secondary))]"
              >
                <X size={16} />
              </button>
            </div>

            {/* Body */}
            <div className="p-6 flex-1 space-y-4">
              <p className="text-xs text-[hsl(var(--text-secondary))] leading-relaxed">
                ¿Estás seguro de que deseas archivar el curso{" "}
                <strong className="text-[hsl(var(--text-primary))] font-bold">
                  &quot;{selectedCourse.title}&quot;
                </strong>
                ?
              </p>
              <div className="p-3 rounded-xl bg-[hsl(var(--destructive))/0.1] border border-[hsl(var(--destructive))/0.2] text-xs text-[hsl(var(--destructive))] leading-relaxed">
                El curso dejará de mostrarse en el catálogo público de la academia (<code className="font-mono text-2xs">/cursos</code>). No se borrarán los progresos históricos de los estudiantes inscritos.
              </div>
            </div>

            {/* Footer */}
            <div className="px-6 py-4 border-t border-[hsl(var(--border))] dark:border-white/[0.06] flex items-center justify-end gap-2 bg-[hsl(var(--surface-3))/0.3]">
              <button
                type="button"
                onClick={() => {
                  setDeleteDrawerOpen(false);
                  setSelectedCourse(null);
                }}
                className="px-4 py-2 text-xs font-semibold rounded-xl border border-[hsl(var(--border))] dark:border-white/10 text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-3))] transition-colors"
              >
                Cancelar
              </button>
              <button
                type="button"
                disabled={saving}
                onClick={handleDeleteConfirm}
                className="px-5 py-2 text-xs font-bold rounded-xl bg-[hsl(var(--destructive))] text-white hover:bg-[hsl(var(--destructive))/0.9] disabled:opacity-50 transition-all uppercase tracking-wider flex items-center gap-1.5"
              >
                {saving && <Loader2 size={13} className="animate-spin" />}
                Confirmar y Archivar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── MediaPicker Drawer ── */}
      <MediaPicker
        open={mediaPickerOpen}
        token={token}
        selectedUrl={mediaPickerTarget === "form" ? formData.image_url : undefined}
        onClose={() => {
          setMediaPickerOpen(false);
          setDirectPhotoCourseId(null);
        }}
        onSelect={handleMediaSelect}
      />
    </div>
  );
}
