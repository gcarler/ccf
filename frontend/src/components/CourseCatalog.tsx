"use client";

import { useEffect, useState } from "react";
import { BookOpen, Search, ArrowRight, Layers, School, Bookmark, Tag, Star, Clock } from "lucide-react";
import { useToast } from "@/context/ToastContext";
import { useRouter } from 'next/navigation';
import { apiUrl } from "../lib/api";

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
}

interface CourseCatalogProps {
  userId: number;
  token: string;
  enrolledCourseIds?: number[];
}


export default function CourseCatalog({ userId, token, enrolledCourseIds = [] }: CourseCatalogProps) {
  const { addToast } = useToast();
  const router = useRouter();

  const [courses, setCourses] = useState<Course[]>([]);
  const [loading, setLoading] = useState(false);
  const [filterModality, setFilterModality] = useState<Modality | "all">("all");

  useEffect(() => {
    const loadCourses = async () => {
      setLoading(true);
      try {
        const response = await fetch(apiUrl(`/courses/?modality=${filterModality === 'all' ? '' : filterModality}`), { cache: "no-store" });
        if (!response.ok) {
          setCourses([]);
          return;
        }
        const data = await response.json();
        setCourses(data);
      } catch (error) {
        setCourses([]);
      } finally {
        setLoading(false);
      }
    };

    loadCourses();
  }, [filterModality]);


  const handleEnrollClick = (courseId: number) => {
    if (enrolledCourseIds.includes(courseId)) {
      router.push(`/academy/course/${courseId}`);
    } else {
      router.push(`/academy/enroll/${courseId}`);
    }
  };


  return (
    <div className="space-y-6">
      <div className="flex gap-3 overflow-x-auto hide-scrollbar pb-2 px-4">
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

      {loading ? (
        <div className="flex justify-center py-10">
          <div className="w-8 h-8 animate-spin border-4 border-primary border-t-transparent rounded-full" />
        </div>
      ) : (
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
                  <span className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-1 flex items-center gap-1"><Clock size={10} /> Duración</span>
                  <span className="text-xs font-bold text-white">{course.duration_hours}h</span>
                </div>
                <div className="w-px h-6 bg-white/10"></div>
                <div className="flex flex-col">
                  <span className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-1 flex items-center gap-1"><School size={10} /> Tipo</span>
                  <span className="text-xs font-bold text-white">{course.is_self_paced ? "Autoguiado" : "Cohorte"}</span>
                </div>
              </div>

              <button
                onClick={() => handleEnrollClick(course.id)}
                className={`w-full py-4 rounded-xl text-xs font-bold uppercase tracking-widest transition-all flex items-center justify-center gap-2 ${enrolledCourseIds.includes(course.id) ? 'bg-white/10 text-white hover:bg-white/20' : 'bg-primary text-white shadow-lg shadow-primary/20 hover:bg-primary/90'}`}
              >
                {enrolledCourseIds.includes(course.id) ? (
                  <>Continuar Curso <ArrowRight size={16} /></>
                ) : (
                  <>Inscribirme Ahora <ArrowRight size={16} /></>
                )}
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
    </div>
  );
}
