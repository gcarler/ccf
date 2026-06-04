"use client";

import { useEffect, useMemo, useState } from "react";
import { ArrowRight, School, Clock } from "lucide-react";
import { useToast } from "@/context/ToastContext";
import { useRouter } from 'next/navigation';
import { apiFetch } from "@/lib/http";
import ViewSwitcher, { ViewType, getStoredView } from "@/components/ViewSwitcher";
import { useWikiDocument } from "@/hooks/useWikiDocument";

type Modality = "formal" | "no_formal";

type AccessLevel = "open" | "member" | "advanced";

const ACCESS_LABEL: Record<AccessLevel, string> = {
  open: "Abierto",
  member: "Miembros",
  advanced: "Formadores",
};
const ACCESS_COLOR: Record<AccessLevel, string> = {
  open: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  member: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  advanced: "bg-amber-500/10 text-amber-400 border-amber-500/20",
};

interface Course {
  id: number;
  code: string;
  title: string;
  description: string;
  modality: Modality;
  duration_hours: number;
  is_self_paced: boolean;
  cohort_name?: string | null;
  certificate_type?: string | null;
  lesson_count: number;
  total_minutes: number;
  access_level?: AccessLevel;
}

interface CourseCatalogProps {
  token: string;
  enrolledCourseIds?: number[];
  initialCourses?: Course[];
  viewType?: ViewType;
  onViewTypeChange?: (view: ViewType) => void;
  showViewSwitcher?: boolean;
}


export default function CourseCatalog({
  token,
  enrolledCourseIds = [],
  initialCourses,
  viewType,
  onViewTypeChange,
  showViewSwitcher = true,
}: CourseCatalogProps) {
  const { addToast } = useToast();
  const router = useRouter();

  const [courses, setCourses] = useState<Course[]>(initialCourses ?? []);
  const [loading, setLoading] = useState(!initialCourses);
  const [filterModality, setFilterModality] = useState<Modality | "all">("all");
  const [internalViewType, setInternalViewType] = useState<ViewType>(() => getStoredView('academy_catalog_view', 'grid'));
  const { content: wikiNotes, setContent: setWikiNotes } = useWikiDocument("academy_catalog_wiki_notes", {
    title: "Wiki del catalogo academico",
  });
  const resolvedViewType = viewType ?? internalViewType;

  const handleViewTypeChange = (nextView: ViewType) => {
    if (onViewTypeChange) {
      onViewTypeChange(nextView);
      return;
    }
    setInternalViewType(nextView);
  };

  useEffect(() => {
    if (initialCourses && filterModality === 'all') {
      setCourses(initialCourses);
      setLoading(false);
      return;
    }

    const loadCourses = async () => {
      setLoading(true);
      try {
        const data = await apiFetch<Course[]>("/academy/courses/", {
          token,
          cache: "no-store",
          query: filterModality === "all" ? undefined : { modality: filterModality },
        });
        setCourses(Array.isArray(data) ? data : []);
      } catch (error) {
        console.error("Error loading courses", error);
        addToast("No pudimos cargar los cursos", "error");
        setCourses([]);
      } finally {
        setLoading(false);
      }
    };

    loadCourses();
  }, [filterModality, token, addToast, initialCourses]);

  const boardColumns = useMemo(() => {
    const formal = courses.filter((c) => c.modality === "formal");
    const nonFormal = courses.filter((c) => c.modality !== "formal");
    const enrolled = courses.filter((c) => enrolledCourseIds.includes(c.id));
    return [
      { key: "formal", label: "Teología", items: formal },
      { key: "non-formal", label: "Liderazgo", items: nonFormal },
      { key: "enrolled", label: "Inscritos", items: enrolled },
    ];
  }, [courses, enrolledCourseIds]);

  const calendarBuckets = useMemo(() => {
    const map: Record<string, Course[]> = {};
    for (const course of courses) {
      const key = course.cohort_name || "Sin cohorte";
      if (!map[key]) map[key] = [];
      map[key].push(course);
    }
    return Object.entries(map);
  }, [courses]);


  const handleEnrollClick = (courseId: number) => {
    if (enrolledCourseIds.includes(courseId)) {
      router.push(`/plataforma/academy/course/${courseId}`);
    } else {
      router.push(`/plataforma/academy/enroll/${courseId}`);
    }
  };


  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3 overflow-x-auto hide-scrollbar pb-2 px-4">
        <div className="flex gap-3 flex-1">
        <button
          onClick={() => setFilterModality("all")}
          className={`px-3 py-2.5 rounded-full text-sm font-bold whitespace-nowrap transition-all ${filterModality === "all" ? "bg-primary text-white shadow-lg shadow-primary/20" : "glass text-slate-500"}`}
        >
          Todos
        </button>
        <button
          onClick={() => setFilterModality("formal")}
          className={`px-3 py-2.5 rounded-full text-sm font-bold whitespace-nowrap transition-all ${filterModality === "formal" ? "bg-primary text-white shadow-lg shadow-primary/20" : "glass text-slate-500"}`}
        >
          Teología
        </button>
        <button
          onClick={() => setFilterModality("no_formal")}
          className={`px-3 py-2.5 rounded-full text-sm font-bold whitespace-nowrap transition-all ${filterModality === "no_formal" ? "bg-primary text-white shadow-lg shadow-primary/20" : "glass text-slate-500"}`}
        >
          Liderazgo
        </button>
        </div>
        {showViewSwitcher && (
          <ViewSwitcher
            viewType={resolvedViewType}
            setViewType={handleViewTypeChange}
            availableViews={['grid', 'list', 'table', 'board', 'kanban', 'calendar', 'gantt', 'wiki']}
            storageKey="academy_catalog_view"
          />
        )}
      </div>

      {loading ? (
        <div className="flex justify-center py-1.5">
          <div className="w-8 h-8 animate-spin border-4 border-primary border-t-transparent rounded-full" />
        </div>
      ) : (
        <>
        {/* GRID VIEW */}
        {resolvedViewType === 'grid' && (
        <div className="flex flex-col gap-4 px-4">
          {courses.map((course) => (
            <div key={course.id} className="glass p-3 rounded-lg flex flex-col gap-4 transition-transform active:scale-[0.98]">
              <div className="flex gap-4">
                  <div className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                    <span className="material-symbols-outlined text-lg">
                        {course.modality === 'formal' ? 'school' : 'menu_book'}
                    </span>
                  </div>
                  <div className="flex flex-1 flex-col justify-center min-w-0">
                    <div className="flex justify-between items-start mb-1">
                      <h3 className="font-bold text-base text-white truncate pr-2">{course.title}</h3>
                      <div className="flex items-center gap-1 shrink-0">
                        {course.access_level && course.access_level !== 'member' && (
                          <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full border uppercase tracking-wider ${ACCESS_COLOR[course.access_level] ?? ACCESS_COLOR.member}`}>
                            {ACCESS_LABEL[course.access_level] ?? course.access_level}
                          </span>
                        )}
                        <span className="text-[9px] font-bold text-primary px-2 py-0.5 rounded bg-primary/10 uppercase tracking-wider">{course.code}</span>
                      </div>
                    </div>
                    <p className="text-slate-400 text-xs line-clamp-2 pr-2 leading-relaxed">{course.description}</p>
                  </div>
              </div>
              <div className="flex items-center gap-4 py-3 border-t border-b border-white/5">
                <div className="flex flex-col">
                  <span className="text-[10px] font-semibold uppercase tracking-wide text-slate-500 mb-1 flex items-center gap-1"><Clock size={10} /> Tiempo</span>
                  <span className="text-xs font-bold text-white">{course.total_minutes > 0 ? `${course.total_minutes}m` : `${course.duration_hours}h`}</span>
                </div>
                <div className="w-px h-6 bg-white/10"></div>
                <div className="flex flex-col">
                  <span className="text-[10px] font-semibold uppercase tracking-wide text-slate-500 mb-1 flex items-center gap-1"><School size={10} /> Lecciones</span>
                  <span className="text-xs font-bold text-white">{course.lesson_count} módulos</span>
                </div>
              </div>
              <button
                onClick={() => handleEnrollClick(course.id)}
                className={`w-full py-1.5 rounded-md text-xs font-bold uppercase tracking-wide transition-all flex items-center justify-center gap-2 ${enrolledCourseIds.includes(course.id) ? 'bg-white/10 text-white hover:bg-white/20' : 'bg-primary text-white shadow-lg shadow-primary/20 hover:bg-primary/90'}`}
              >
                {enrolledCourseIds.includes(course.id) ? (<>Continuar Curso <ArrowRight size={16} /></>) : (<>Inscribirme Ahora <ArrowRight size={16} /></>)}
              </button>
            </div>
          ))}
          {courses.length === 0 && (
            <div className="rounded-lg border border-dashed border-white/10 bg-slate-900/30 p-4 text-center">
              <p className="text-xs font-bold text-slate-500 uppercase tracking-wide">No hay cursos publicados.</p>
            </div>
          )}
        </div>
        )}

        {/* LIST VIEW */}
        {resolvedViewType === 'list' && (
        <div className="flex flex-col gap-2 px-4">
          {courses.map((course) => (
            <div key={course.id} className="glass flex items-center gap-4 px-4 py-1.5 rounded-md hover:bg-white/10 transition-colors group">
              <div className="flex size-9 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary">
                <School size={14} />
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-bold text-white text-sm truncate">{course.title}</p>
                <p className="text-xs text-slate-400 truncate">{course.code} · {course.duration_hours}h · {course.is_self_paced ? 'Autoguiado' : 'Cohorte'}</p>
              </div>
              <button
                onClick={() => handleEnrollClick(course.id)}
                className={`px-3 py-1.5 rounded-md text-[10px] font-semibold uppercase tracking-wide transition-all flex items-center gap-1.5 ${enrolledCourseIds.includes(course.id) ? 'bg-white/10 text-white' : 'bg-primary text-white'}`}
              >
                {enrolledCourseIds.includes(course.id) ? 'Continuar' : 'Inscribirse'} <ArrowRight size={12} />
              </button>
            </div>
          ))}
        </div>
        )}

        {/* TABLE VIEW */}
        {resolvedViewType === 'table' && (
        <div className="px-4 overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-white/10">
                <th className="pb-3 text-[10px] font-semibold uppercase tracking-wide text-slate-500">Curso</th>
                <th className="pb-3 text-[10px] font-semibold uppercase tracking-wide text-slate-500">Código</th>
                <th className="pb-3 text-[10px] font-semibold uppercase tracking-wide text-slate-500">Duración</th>
                <th className="pb-3 text-[10px] font-semibold uppercase tracking-wide text-slate-500">Tipo</th>
                <th className="pb-3 text-[10px] font-semibold uppercase tracking-wide text-slate-500 text-right">Acción</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {courses.map((course) => (
                <tr key={course.id} className="hover:bg-white/5 transition-colors">
                  <td className="py-1.5 pr-4">
                    <p className="font-bold text-white text-sm">{course.title}</p>
                    <p className="text-xs text-slate-500 line-clamp-1 mt-0.5">{course.description}</p>
                  </td>
                  <td className="py-1.5 pr-4">
                    <span className="text-[10px] font-bold text-primary px-2 py-0.5 rounded bg-primary/10 uppercase">{course.code}</span>
                  </td>
                  <td className="py-1.5 pr-4 text-sm text-slate-300 font-bold">{course.duration_hours}h</td>
                  <td className="py-1.5 pr-4 text-xs text-slate-400">{course.is_self_paced ? 'Autoguiado' : 'Cohorte'}</td>
                  <td className="py-1.5 text-right">
                    <button
                      onClick={() => handleEnrollClick(course.id)}
                      className={`px-3 py-1.5 rounded-md text-[10px] font-semibold uppercase tracking-wide transition-all inline-flex items-center gap-1 ${enrolledCourseIds.includes(course.id) ? 'bg-white/10 text-white' : 'bg-primary text-white'}`}
                    >
                      {enrolledCourseIds.includes(course.id) ? 'Continuar' : 'Inscribirse'} <ArrowRight size={10} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {courses.length === 0 && (
            <div className="rounded-lg border border-dashed border-white/10 bg-slate-900/30 p-4 text-center mt-4">
              <p className="text-xs font-bold text-slate-500 uppercase tracking-wide">No hay cursos publicados.</p>
            </div>
          )}
        </div>
        )}

        {(resolvedViewType === 'board' || resolvedViewType === 'kanban') && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 px-4">
          {boardColumns.map((column) => (
            <div key={column.key} className="rounded-lg border border-white/10 bg-slate-900/30 p-3">
              <div className="mb-3 flex items-center justify-between">
                <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">{column.label}</p>
                <span className="font-semibold text-slate-500">{column.items.length}</span>
              </div>
              <div className="space-y-2">
                {column.items.map((course) => (
                  <button
                    key={course.id}
                    onClick={() => handleEnrollClick(course.id)}
                    className="w-full text-left rounded-md border border-white/10 bg-white/5 p-3 hover:border-primary/40 transition-all"
                  >
                    <p className="text-xs font-semibold text-white">{course.title}</p>
                    <p className="text-[10px] text-slate-400">{course.code} · {course.duration_hours}h</p>
                  </button>
                ))}
                {column.items.length === 0 && <div className="py-2 text-center text-[10px] font-semibold uppercase tracking-wide text-slate-500">Vacío</div>}
              </div>
            </div>
          ))}
        </div>
        )}

        {resolvedViewType === 'calendar' && (
        <div className="space-y-4 px-4">
          {calendarBuckets.map(([bucket, items]) => (
            <div key={bucket} className="rounded-lg border border-white/10 bg-slate-900/30 p-4">
              <p className="mb-3 text-[10px] font-semibold uppercase tracking-wide text-slate-400">{bucket}</p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {items.map((course) => (
                  <button key={course.id} onClick={() => handleEnrollClick(course.id)} className="rounded-md border border-white/10 bg-white/5 p-3 text-left hover:border-primary/40 transition-all">
                    <p className="text-sm font-semibold text-white">{course.title}</p>
                    <p className="text-[10px] text-slate-400">{course.code} · {course.is_self_paced ? 'Autoguiado' : 'Cohorte'}</p>
                  </button>
                ))}
              </div>
            </div>
          ))}
          {calendarBuckets.length === 0 && <div className="py-8 text-center text-slate-500 text-sm">Sin cursos en calendario</div>}
        </div>
        )}

        {resolvedViewType === 'gantt' && (
        <div className="px-4">
          <div className="rounded-lg border border-white/10 bg-slate-900/30 p-4 space-y-3">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Progreso sugerido por curso</p>
            {courses.map((course) => {
              const progress = Math.min(100, Math.max(15, Math.round((course.lesson_count / 12) * 100)));
              return (
                <div key={course.id} className="space-y-1">
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="font-bold text-slate-200">{course.title}</span>
                    <span className="font-semibold text-slate-400">{progress}%</span>
                  </div>
                  <div className="h-2 rounded-full bg-white/10 overflow-hidden">
                    <div className="h-full bg-primary" style={{ width: `${progress}%` }} />
                  </div>
                </div>
              );
            })}
            {courses.length === 0 && <div className="py-8 text-center text-slate-500 text-sm">Sin datos para timeline</div>}
          </div>
        </div>
        )}

        {resolvedViewType === 'wiki' && (
        <div className="px-4">
          <div className="rounded-lg border border-white/10 bg-slate-900/30 p-4 space-y-3">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Wiki del catálogo</p>
            <textarea
              value={wikiNotes}
              onChange={(e) => setWikiNotes(e.target.value)}
              placeholder="Documenta rutas de cursos, prerequisitos, recomendaciones y lineamientos para estudiantes..."
              className="w-full min-h-[320px] rounded-lg border border-white/10 bg-black/20 p-4 text-sm font-medium text-slate-200 outline-none focus:ring-2 focus:ring-primary/20"
            />
          </div>
        </div>
        )}
        </>
      )}
    </div>
  );
}
