"use client";

import { useEffect, useState } from "react";
import { ArrowRight, School, Clock } from "lucide-react";
import { useToast } from "@/context/ToastContext";
import { useRouter } from 'next/navigation';
import { apiFetch } from "@/lib/http";
import ViewSwitcher, { ViewType, getStoredView } from "@/components/ViewSwitcher";

type Modality = "formal" | "no_formal";

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
}

interface CourseCatalogProps {
  userId: number;
  token: string;
  enrolledCourseIds?: number[];
  initialCourses?: Course[];
}


export default function CourseCatalog({ userId, token, enrolledCourseIds = [], initialCourses }: CourseCatalogProps) {
  const { addToast } = useToast();
  const router = useRouter();

  const [courses, setCourses] = useState<Course[]>(initialCourses ?? []);
  const [loading, setLoading] = useState(!initialCourses);
  const [filterModality, setFilterModality] = useState<Modality | "all">("all");
  const [viewType, setViewType] = useState<ViewType>(() => getStoredView('academy_catalog_view', 'grid'));

  useEffect(() => {
    if (initialCourses && filterModality === 'all') {
      setCourses(initialCourses);
      setLoading(false);
      return;
    }

    const loadCourses = async () => {
      setLoading(true);
      try {
        const data = await apiFetch<Course[]>("/courses/", {
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


  const handleEnrollClick = (courseId: number) => {
    if (enrolledCourseIds.includes(courseId)) {
      router.push(`/academy/course/${courseId}`);
    } else {
      router.push(`/academy/enroll/${courseId}`);
    }
  };


  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3 overflow-x-auto hide-scrollbar pb-2 px-4">
        <div className="flex gap-3 flex-1">
        <button
          onClick={() => setFilterModality("all")}
          className={`px-5 py-2.5 rounded-full text-sm font-bold whitespace-nowrap transition-all ${filterModality === "all" ? "bg-primary text-white shadow-lg shadow-primary/20" : "glass text-slate-500"}`}
        >
          Todos
        </button>
        <button
          onClick={() => setFilterModality("formal")}
          className={`px-5 py-2.5 rounded-full text-sm font-bold whitespace-nowrap transition-all ${filterModality === "formal" ? "bg-primary text-white shadow-lg shadow-primary/20" : "glass text-slate-500"}`}
        >
          Teología
        </button>
        <button
          onClick={() => setFilterModality("no_formal")}
          className={`px-5 py-2.5 rounded-full text-sm font-bold whitespace-nowrap transition-all ${filterModality === "no_formal" ? "bg-primary text-white shadow-lg shadow-primary/20" : "glass text-slate-500"}`}
        >
          Liderazgo
        </button>
        </div>
        <ViewSwitcher
          viewType={viewType}
          setViewType={setViewType}
          availableViews={['grid', 'list', 'table']}
          storageKey="academy_catalog_view"
        />
      </div>

      {loading ? (
        <div className="flex justify-center py-10">
          <div className="w-8 h-8 animate-spin border-4 border-primary border-t-transparent rounded-full" />
        </div>
      ) : (
        <>
        {/* GRID VIEW */}
        {viewType === 'grid' && (
        <div className="flex flex-col gap-4 px-4">
          {courses.map((course) => (
            <div key={course.id} className="glass p-5 rounded-3xl flex flex-col gap-4 transition-transform active:scale-[0.98]">
              <div className="flex gap-4">
                  <div className="flex size-14 shrink-0 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                    <span className="material-symbols-outlined text-2xl">
                        {course.modality === 'formal' ? 'school' : 'menu_book'}
                    </span>
                  </div>
                  <div className="flex flex-1 flex-col justify-center min-w-0">
                    <div className="flex justify-between items-start mb-1">
                      <h3 className="font-bold text-base text-white truncate pr-2">{course.title}</h3>
                      <span className="text-[9px] font-bold text-primary px-2 py-0.5 rounded bg-primary/10 uppercase tracking-wider shrink-0">{course.code}</span>
                    </div>
                    <p className="text-slate-400 text-xs line-clamp-2 pr-2 leading-relaxed">{course.description}</p>
                  </div>
              </div>
              <div className="flex items-center gap-4 py-3 border-t border-b border-white/5">
                <div className="flex flex-col">
                  <span className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-1 flex items-center gap-1"><Clock size={10} /> Tiempo</span>
                  <span className="text-xs font-bold text-white">{course.total_minutes > 0 ? `${course.total_minutes}m` : `${course.duration_hours}h`}</span>
                </div>
                <div className="w-px h-6 bg-white/10"></div>
                <div className="flex flex-col">
                  <span className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-1 flex items-center gap-1"><School size={10} /> Lecciones</span>
                  <span className="text-xs font-bold text-white">{course.lesson_count} módulos</span>
                </div>
              </div>
              <button
                onClick={() => handleEnrollClick(course.id)}
                className={`w-full py-4 rounded-xl text-xs font-bold uppercase tracking-widest transition-all flex items-center justify-center gap-2 ${enrolledCourseIds.includes(course.id) ? 'bg-white/10 text-white hover:bg-white/20' : 'bg-primary text-white shadow-lg shadow-primary/20 hover:bg-primary/90'}`}
              >
                {enrolledCourseIds.includes(course.id) ? (<>Continuar Curso <ArrowRight size={16} /></>) : (<>Inscribirme Ahora <ArrowRight size={16} /></>)}
              </button>
            </div>
          ))}
          {courses.length === 0 && (
            <div className="rounded-3xl border border-dashed border-white/10 bg-slate-900/30 p-8 text-center">
              <p className="text-xs font-bold text-slate-500 uppercase tracking-widest">No hay cursos publicados.</p>
            </div>
          )}
        </div>
        )}

        {/* LIST VIEW */}
        {viewType === 'list' && (
        <div className="flex flex-col gap-2 px-4">
          {courses.map((course) => (
            <div key={course.id} className="glass flex items-center gap-4 px-4 py-3 rounded-2xl hover:bg-white/10 transition-colors group">
              <div className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
                <School size={14} />
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-bold text-white text-sm truncate">{course.title}</p>
                <p className="text-xs text-slate-400 truncate">{course.code} · {course.duration_hours}h · {course.is_self_paced ? 'Autoguiado' : 'Cohorte'}</p>
              </div>
              <button
                onClick={() => handleEnrollClick(course.id)}
                className={`px-3 py-1.5 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all flex items-center gap-1.5 ${enrolledCourseIds.includes(course.id) ? 'bg-white/10 text-white' : 'bg-primary text-white'}`}
              >
                {enrolledCourseIds.includes(course.id) ? 'Continuar' : 'Inscribirse'} <ArrowRight size={12} />
              </button>
            </div>
          ))}
        </div>
        )}

        {/* TABLE VIEW */}
        {viewType === 'table' && (
        <div className="px-4 overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-white/10">
                <th className="pb-3 text-[10px] font-black uppercase tracking-widest text-slate-500">Curso</th>
                <th className="pb-3 text-[10px] font-black uppercase tracking-widest text-slate-500">Código</th>
                <th className="pb-3 text-[10px] font-black uppercase tracking-widest text-slate-500">Duración</th>
                <th className="pb-3 text-[10px] font-black uppercase tracking-widest text-slate-500">Tipo</th>
                <th className="pb-3 text-[10px] font-black uppercase tracking-widest text-slate-500 text-right">Acción</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {courses.map((course) => (
                <tr key={course.id} className="hover:bg-white/5 transition-colors">
                  <td className="py-4 pr-4">
                    <p className="font-bold text-white text-sm">{course.title}</p>
                    <p className="text-xs text-slate-500 line-clamp-1 mt-0.5">{course.description}</p>
                  </td>
                  <td className="py-4 pr-4">
                    <span className="text-[10px] font-bold text-primary px-2 py-0.5 rounded bg-primary/10 uppercase">{course.code}</span>
                  </td>
                  <td className="py-4 pr-4 text-sm text-slate-300 font-bold">{course.duration_hours}h</td>
                  <td className="py-4 pr-4 text-xs text-slate-400">{course.is_self_paced ? 'Autoguiado' : 'Cohorte'}</td>
                  <td className="py-4 text-right">
                    <button
                      onClick={() => handleEnrollClick(course.id)}
                      className={`px-3 py-1.5 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all inline-flex items-center gap-1 ${enrolledCourseIds.includes(course.id) ? 'bg-white/10 text-white' : 'bg-primary text-white'}`}
                    >
                      {enrolledCourseIds.includes(course.id) ? 'Continuar' : 'Inscribirse'} <ArrowRight size={10} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {courses.length === 0 && (
            <div className="rounded-3xl border border-dashed border-white/10 bg-slate-900/30 p-8 text-center mt-4">
              <p className="text-xs font-bold text-slate-500 uppercase tracking-widest">No hay cursos publicados.</p>
            </div>
          )}
        </div>
        )}
        </>
      )}
    </div>
  );
}
