"use client";

import { useEffect, useState, useCallback } from "react";
import { apiUrl } from "../lib/api";
import { apiFetch } from "@/lib/http";

interface Enrollment {
  id: number;
  status: string;
  progress_percent: number;
  approved: boolean;
  course: {
    id: number;
    title: string;
    modality: string;
    certificate_type?: string | null;
  };
}

interface Assessment {
  id: number;
  title: string;
  passing_score: number;
  max_score: number;
}

interface Certificate {
  id: number;
  enrollment_id: number;
  certificate_code: string;
  certificate_type?: string | null;
  issued_at: string;
}

interface MyEnrollmentsProps {
  userId: number;
  token: string;
  initialEnrollments?: Enrollment[];
}

import { Award, FileText, ArrowRight, Play, BookOpen, ChevronRight, X as CloseIcon, Loader2, School, Paperclip, Upload, File, Clock } from "lucide-react";
import { useToast } from "@/context/ToastContext";
import { useMeshSocket } from "@/hooks/useMeshSocket";
import CertificateDrawer from "./CertificateDrawer";
import AssessmentDrawer from "./academy/AssessmentDrawer";
import EmptyState from "@/components/ui/EmptyState";

interface Lesson {
  id: number;
  title: string;
  content: string;
  order_index: number;
  duration_minutes: number;
  resources?: any[];
}

export default function MyEnrollments({ userId, token, initialEnrollments }: MyEnrollmentsProps) {
  const { addToast } = useToast();
  const [enrollments, setEnrollments] = useState<Enrollment[]>(initialEnrollments ?? []);
  const [assessmentsByCourse, setAssessmentsByCourse] = useState<Record<number, Assessment[]>>({});
  const [certificatesByEnrollment, setCertificatesByEnrollment] = useState<Record<number, Certificate>>({});
  const [loading, setLoading] = useState(!initialEnrollments);
  const [activeAssessment, setActiveAssessment] = useState<{ id: number, enrollmentId: number } | null>(null);

  // Mesh WebSocket Integration
  const { lastEvent } = useMeshSocket(userId ? String(userId) : "");

  const [selectedCertificate, setSelectedCertificate] = useState<{ cert: Certificate, enrollment: Enrollment } | null>(null);

  // Lesson Viewer State
  const [viewingLessonsCourse, setViewingLessonsCourse] = useState<Enrollment | null>(null);
  const [lessons, setLessons] = useState<Lesson[]>([]);
  const [selectedLesson, setSelectedLesson] = useState<Lesson | null>(null);
  const [loadingLessons, setLoadingLessons] = useState(false);

  const loadEnrollments = useCallback(async () => {
    if (!token) {
      setEnrollments([]);
      setLoading(false);
      return;
    }

    setLoading(true);
    try {
      const data = await apiFetch<Enrollment[]>(`/academy/users/${userId}/enrollments`, {
        token,
        cache: "no-store",
      });
      const normalized = Array.isArray(data) ? data : [];
      setEnrollments(normalized);

      normalized.forEach((item) => {
        if (item.status === "active" || item.status === "enrolled") {
          apiFetch(`/academy/enrollments/${item.id}/check-in`, {
            method: "POST",
            token,
          }).catch((err) => { console.error('[MyEnrollments] Failed to check-in:', err); });
        }
      });

      const assessmentsEntries = await Promise.all(
        normalized.map(async (item) => {
          try {
            const assessments = await apiFetch<Assessment[]>(`/academy/courses/${item.course.id}/assessments`, {
              token,
              cache: "no-store",
            });
            return [item.course.id, Array.isArray(assessments) ? assessments : []] as const;
          } catch {
            return [item.course.id, []] as const;
          }
        })
      );
      setAssessmentsByCourse(Object.fromEntries(assessmentsEntries));

      try {
        const certificates = await apiFetch<Certificate[]>(`/academy/me/certificates`, {
          token,
          cache: "no-store",
        });
        const mapped: Record<number, Certificate> = {};
        (Array.isArray(certificates) ? certificates : []).forEach((cert) => {
          mapped[cert.enrollment_id] = cert;
        });
        setCertificatesByEnrollment(mapped);
      } catch {
        setCertificatesByEnrollment({});
      }
    } catch (error) {
      console.error("Error loading enrollments", error);
      setEnrollments([]);
    } finally {
      setLoading(false);
    }
  }, [token, userId]);

  useEffect(() => {
    if (initialEnrollments) return;
    if (!token || !userId) return;
    loadEnrollments();
  }, [loadEnrollments, token, userId, initialEnrollments]);

  // Handle Mesh Events
  useEffect(() => {
    if (lastEvent) {
      if (lastEvent.event === "MESH_EVENT_ASSESSMENT_SCORED" && lastEvent.user_id === userId) {
        addToast(`Examen calificado: ${lastEvent.score}% - ${lastEvent.passed ? 'Aprobado' : 'Reprobado'}`, lastEvent.passed ? 'success' : 'error');
        loadEnrollments();
      }
    }
  }, [lastEvent, addToast, userId, loadEnrollments]);

  const handleAssessmentSuccess = (score: number) => {
    addToast(`Examen completado con ${score}%`, "success");
    setActiveAssessment(null);
    loadEnrollments();
  };

  const openLessons = async (enrollment: Enrollment) => {
    setViewingLessonsCourse(enrollment);
    setLoadingLessons(true);
    try {
      const data = await apiFetch<Lesson[]>(`/academy/courses/${enrollment.course.id}/lessons`, {
        token,
        cache: "no-store",
      });
      const normalized = Array.isArray(data) ? data : [];
      setLessons(normalized);
      if (normalized.length > 0) {
        setSelectedLesson(normalized[0]);
      }
    } catch (err) {
      addToast("Error al cargar lecciones", "error");
    } finally {
      setLoadingLessons(false);
    }
  };

  if (loading) {
    return <div className="flex justify-center p-4"><Loader2 className="animate-spin text-primary w-8 h-8" /></div>;
  }

  return (
    <section className="animate-in fade-in duration-500">
      {viewingLessonsCourse && (
        <div className="fixed inset-0 z-[100] bg-slate-950 flex flex-col md:flex-row animate-in slide-in-from-bottom-full duration-300">
          {/* Mobile Header */}
          <div className="md:hidden flex items-center justify-between p-4 border-b border-white/5 bg-slate-900">
            <h3 className="font-bold text-white truncate pr-4">{viewingLessonsCourse.course.title}</h3>
            <button onClick={() => setViewingLessonsCourse(null)} className="p-2 bg-white/5 rounded-full text-white">
              <CloseIcon size={20} />
            </button>
          </div>

          <div className="flex flex-col md:flex-row w-full h-full">
            {/* Sidebar Lessons List */}
            <div className="w-full md:w-80 bg-slate-900 border-r border-white/5 flex flex-col h-1/3 md:h-full">
              <div className="p-3 border-b border-white/5 hidden md:block">
                <div className="flex items-center gap-3 mb-2">
                  <span className="p-1.5 bg-primary/20 text-primary rounded-lg"><BookOpen size={16} /></span>
                  <span className="text-[10px] font-bold text-primary uppercase tracking-wide">Curso Activo</span>
                </div>
                <h3 className="font-bold text-white leading-tight">{viewingLessonsCourse.course.title}</h3>
              </div>
              <div className="flex-1 overflow-y-auto p-4 space-y-2 hide-scrollbar">
                {loadingLessons ? (
                  Array.from({ length: 4 }).map((_, i) => <div key={i} className="h-8 w-full bg-slate-800 animate-pulse rounded-lg" />)
                ) : lessons.length > 0 ? (
                  lessons.map((lesson) => (
                    <button
                      key={lesson.id}
                      onClick={() => setSelectedLesson(lesson)}
                      className={`w-full text-left p-3.5 rounded-lg transition-all flex items-center gap-4 group ${selectedLesson?.id === lesson.id ? 'bg-primary/20 border border-primary/30 shadow-lg shadow-primary/10' : 'hover:bg-slate-800/60 border border-transparent'}`}
                    >
                      <div className={`p-2 rounded-md transition-colors ${selectedLesson?.id === lesson.id ? 'bg-primary text-white shadow-md shadow-primary/30' : 'bg-slate-800 text-slate-400 group-hover:text-primary group-hover:bg-primary/10'}`}>
                        <Play size={14} className={selectedLesson?.id === lesson.id ? 'fill-current' : 'group-hover:fill-current'} />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className={`text-xs font-bold truncate ${selectedLesson?.id === lesson.id ? 'text-white' : 'text-slate-300 group-hover:text-white'}`}>{lesson.title}</p>
                        <p className={`text-[10px] ${selectedLesson?.id === lesson.id ? 'text-primary-200' : 'text-slate-500'}`}>{lesson.duration_minutes} min</p>
                      </div>
                    </button>
                  ))
                ) : (
                  <p className="text-center py-1.5 text-[10px] font-bold text-slate-500 uppercase tracking-wide">No hay lecciones.</p>
                )}
              </div>
            </div>

            {/* Content Area */}
            <div className="flex-1 bg-slate-950 relative flex flex-col h-2/3 md:h-full">
              <div className="absolute top-3 right-6 hidden md:block z-10">
                <button onClick={() => setViewingLessonsCourse(null)} className="p-3 bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700 rounded-full transition-all shadow-sm">
                  <CloseIcon size={20} />
                </button>
              </div>

              {selectedLesson ? (
                <div className="flex-1 overflow-y-auto p-3 md:p-4 relative hide-scrollbar">
                  <div className="absolute inset-x-0 top-0 h-40 bg-gradient-to-b from-primary/10 to-transparent pointer-events-none"></div>
                  <div className="max-w-3xl mx-auto space-y-3 relative">
                    <div>
                      <div className="flex items-center gap-2 mb-4">
                        <span className="p-2 bg-primary/20 text-primary rounded-md"><BookOpen size={16} /></span>
                        <span className="text-[10px] font-bold text-primary uppercase tracking-wide">Lección Actual</span>
                      </div>
                      <h2 className="text-xl md:text-lg font-bold text-white tracking-tight leading-tight mb-3">{selectedLesson.title}</h2>
                    </div>

                    <div className="prose prose-invert prose-lg max-w-none">
                      <div dangerouslySetInnerHTML={{ __html: selectedLesson.content.replace(/\n/g, '<br/>') }} className="text-slate-300 font-normal leading-relaxed text-lg" />
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-3 pt-12 border-t border-white/10">
                      <div className="space-y-4">
                        <h4 className="text-sm font-bold text-white flex items-center gap-2"><Paperclip size={18} className="text-primary" /> Material de Estudio</h4>
                        <div className="space-y-2">
                            {selectedLesson.resources && selectedLesson.resources.length > 0 ? (
                              selectedLesson.resources.map((res: any) => (
                                <a key={res.id} href={res.file_url?.startsWith('http') ? res.file_url : apiUrl(res.file_url || '')} target="_blank" rel="noopener noreferrer" className="flex items-center justify-between p-4 bg-slate-900 border border-white/5 rounded-lg hover:border-primary/50 transition-all group">
                                <div className="flex items-center gap-3">
                                  <div className="p-2 bg-primary/10 rounded-lg text-primary"><File size={16} /></div>
                                  <span className="text-xs font-medium text-slate-300 group-hover:text-white">{res.title}</span>
                                </div>
                                <ChevronRight size={14} className="text-slate-600 group-hover:text-primary" />
                              </a>
                            ))
                          ) : (
                            <div className="p-4 bg-slate-900/50 rounded-lg border border-dashed border-white/5 text-center">
                              <p className="text-[10px] text-slate-500 italic font-medium uppercase tracking-wide">No hay material.</p>
                            </div>
                          )}
                        </div>
                      </div>

                      <div className="space-y-4">
                        <h4 className="text-sm font-bold text-white flex items-center gap-2"><Upload size={18} className="text-emerald-500" /> Entregar Tarea</h4>
                        <div className="p-3 bg-slate-900 border border-white/5 rounded-lg flex flex-col items-center justify-center text-center gap-4">
                          <div className="p-4 bg-emerald-500/10 rounded-full text-emerald-500"><FileText size={24} /></div>
                          <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wide leading-relaxed">Sube tu trabajo en PDF o Word para ser calificado.</p>
                          <label className="w-full py-3 bg-[hsl(var(--bg-primary))] text-slate-900 rounded-md text-[10px] font-semibold uppercase tracking-wide hover:bg-slate-100 transition-all cursor-pointer text-center">
                            <input
                              type="file"
                              className="hidden"
                              onChange={(e) => {
                                const file = e.target.files?.[0];
                                  if (file && viewingLessonsCourse) {
                                    const formData = new FormData();
                                    formData.append('file', file);
                                    formData.append('enrollment_id', viewingLessonsCourse.id.toString());
                                    apiFetch(`/academy/lessons/${selectedLesson.id}/submit-assignment`, {
                                      method: 'POST',
                                      token,
                                      body: formData
                                    })
                                      .then(() => addToast("Tarea entregada", "success"))
                                      .catch(() => addToast("Error al subir archivo", "error"));
                                  }
                                }}
                              />
                              Subir Archivo
                          </label>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="flex-1 flex flex-col items-center justify-center p-4 text-center relative">
                  <div className="relative p-3 bg-slate-800/50 rounded-full text-slate-400 mb-3"><BookOpen size={48} /></div>
                  <h3 className="text-xl font-bold text-white mb-2">Comienza a Aprender</h3>
                  <p className="text-sm text-slate-400 max-w-xs">Selecciona una lección para ver su contenido.</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {enrollments.length === 0 ? (
        <EmptyState 
            icon={BookOpen}
            title="No tienes cursos activos."
            description="Explora el Catálogo Formativo y encuentra tu próxima lección para continuar tu crecimiento."
        />
      ) : (
        <div className="flex flex-col gap-2">
          {enrollments.map((item) => {
            const progressCircumference = 263.89;
            const progressOffset = progressCircumference - (progressCircumference * item.progress_percent) / 100;

            return (
              <article key={item.id} className="bg-[hsl(var(--bg-primary))] dark:bg-black/20 border border-[#e8eaed] dark:border-white/5 p-4 rounded-lg flex flex-col gap-3 group hover:border-indigo-500/30 transition-all hover:shadow-xl hover:shadow-indigo-500/5 cursor-pointer" onClick={() => openLessons(item)}>
                <div className="flex gap-4 items-center relative">
                  <div className="relative flex size-7 shrink-0 items-center justify-center">
                    <svg className="absolute inset-0 size-7 -rotate-90" viewBox="0 0 100 100">
                      <circle className="text-slate-100 dark:text-white/5 stroke-current" cx="50" cy="50" fill="transparent" r="42" strokeWidth="10"></circle>
                      <circle className="text-indigo-600 stroke-current transition-all duration-1000 ease-out" cx="50" cy="50" fill="transparent" r="42" strokeLinecap="round" strokeWidth="10" style={{ strokeDasharray: progressCircumference, strokeDashoffset: progressOffset }}></circle>
                    </svg>
                    <div className="z-10 text-indigo-600 dark:text-indigo-400">
                      {item.course.modality === 'formal' ? <School size={16} /> : <BookOpen size={16} />}
                    </div>
                  </div>

                  <div className="flex flex-1 flex-col justify-center min-w-0">
                    <div className="flex justify-between items-start">
                      <h3 className="font-bold text-sm truncate pr-2 text-slate-800 dark:text-white tracking-tight">{item.course.title}</h3>
                      <div className="flex items-center gap-1.5 shrink-0">
                         <span className="font-semibold text-indigo-600 dark:text-indigo-400 px-2 py-0.5 rounded-lg bg-indigo-50 dark:bg-indigo-900/30 uppercase tracking-wide">{Math.round(item.progress_percent)}%</span>
                         <ChevronRight size={14} className="text-slate-300 group-hover:text-indigo-500 transition-colors" />
                      </div>
                    </div>
                    <div className="flex items-center gap-3 mt-0.5">
                        <p className="text-slate-400 text-[10px] font-semibold uppercase tracking-wide flex items-center gap-1">
                            <Clock size={10} />
                            {item.course.modality.replace('_', ' ')}
                        </p>
                        <div className="w-1 h-1 rounded-full bg-slate-200 dark:bg-white/10" />
                        <p className="text-slate-400 text-[10px] font-medium truncate">En progreso</p>
                    </div>
                  </div>
                </div>

                <div className="flex gap-2 empty:hidden pt-2 border-t border-slate-50 dark:border-white/5">
                  {item.approved && certificatesByEnrollment[item.id] ? (
                    <button 
                        onClick={(e) => { e.stopPropagation(); setSelectedCertificate({ cert: certificatesByEnrollment[item.id], enrollment: item }); }} 
                        className="flex-1 py-1.5 bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400 rounded-md text-[10px] font-semibold uppercase tracking-wide transition-all flex items-center justify-center gap-2 hover:bg-emerald-100 dark:hover:bg-emerald-900/40"
                    >
                      <Award size={12} /> Certificado Disponible
                    </button>
                  ) : !item.approved && item.progress_percent >= 90 && assessmentsByCourse[item.course.id]?.length > 0 && (
                    <button 
                        onClick={(e) => { 
                          e.stopPropagation(); 
                          setActiveAssessment({ id: assessmentsByCourse[item.course.id][0].id, enrollmentId: item.id }); 
                        }} 
                        className="flex-1 py-1.5 bg-indigo-600 text-white rounded-md text-[10px] font-semibold uppercase tracking-wide hover:bg-indigo-700 transition-all flex items-center justify-center gap-2 shadow-lg shadow-indigo-500/20"
                    >
                      Tomar Examen <ArrowRight size={12} />
                    </button>
                  )}
                </div>
              </article>
            );
          })}
        </div>
      )}

      {activeAssessment && (
        <AssessmentDrawer
          assessmentId={activeAssessment.id}
          enrollmentId={activeAssessment.enrollmentId}
          token={token}
          onClose={() => setActiveAssessment(null)}
          onSuccess={handleAssessmentSuccess}
        />
      )}

      {selectedCertificate && (
        <CertificateDrawer
          certificate={selectedCertificate.cert}
          enrollment={selectedCertificate.enrollment}
          userName={userId ? "Estudiante" : "Estudiante"}
          onClose={() => setSelectedCertificate(null)}
        />
      )}
    </section>
  );
}
