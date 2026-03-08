"use client";

import { useEffect, useState } from "react";
import { apiUrl } from "../lib/api";

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
  refreshToken: number;
}

import { CheckCircle, Award, FileText, Send, AlertCircle, Info, ArrowRight, Play, BookOpen, ChevronRight, X as CloseIcon, Loader2, BookMarked, School, Paperclip, Upload, File } from "lucide-react";
import { useToast } from "@/context/ToastContext";
import { useMeshSocket } from "@/hooks/useMeshSocket";
import CertificateModal from "./CertificateModal";

interface Lesson {
  id: number;
  title: string;
  content: string;
  order_index: number;
  duration_minutes: number;
  resources?: any[];
}

export default function MyEnrollments({ userId, token, refreshToken }: MyEnrollmentsProps) {
  const { addToast } = useToast();
  const [enrollments, setEnrollments] = useState<Enrollment[]>([]);
  const [assessmentsByCourse, setAssessmentsByCourse] = useState<Record<number, Assessment[]>>({});
  const [certificatesByEnrollment, setCertificatesByEnrollment] = useState<Record<number, Certificate>>({});
  const [scoreByAssessment, setScoreByAssessment] = useState<Record<number, string>>({});
  const [messageByEnrollment, setMessageByEnrollment] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState(true);
  const [activeExam, setActiveExam] = useState<number | null>(null);

  // Mesh WebSocket Integration
  const { lastEvent } = useMeshSocket(userId ? String(userId) : "");

  const [selectedCertificate, setSelectedCertificate] = useState<{ cert: Certificate, enrollment: Enrollment } | null>(null);

  // Lesson Viewer State
  const [viewingLessonsCourse, setViewingLessonsCourse] = useState<Enrollment | null>(null);
  const [lessons, setLessons] = useState<Lesson[]>([]);
  const [selectedLesson, setSelectedLesson] = useState<Lesson | null>(null);
  const [loadingLessons, setLoadingLessons] = useState(false);

  const loadEnrollments = async () => {
    if (!token) {
      setEnrollments([]);
      setLoading(false);
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(apiUrl(`/users/${userId}/enrollments`), {
        cache: "no-store",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (!response.ok) {
        setEnrollments([]);
        return;
      }
      const data: Enrollment[] = await response.json();
      setEnrollments(data);

      data.forEach(async (item) => {
        if (item.status === 'active' || item.status === 'enrolled') {
          try {
            fetch(apiUrl(`/enrollments/${item.id}/check-in`), {
              method: "POST",
              headers: { Authorization: `Bearer ${token}` }
            });
          } catch (e) { }
        }
      });

      const assessmentsEntries = await Promise.all(
        data.map(async (item) => {
          const assessmentsResponse = await fetch(apiUrl(`/courses/${item.course.id}/assessments`), {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          });
          if (!assessmentsResponse.ok) {
            return [item.course.id, []] as const;
          }
          const assessments = (await assessmentsResponse.json()) as Assessment[];
          return [item.course.id, assessments] as const;
        })
      );
      setAssessmentsByCourse(Object.fromEntries(assessmentsEntries));

      const certificateResponse = await fetch(apiUrl(`/users/${userId}/certificates`), {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (certificateResponse.ok) {
        const certificates = (await certificateResponse.json()) as Certificate[];
        const mapped: Record<number, Certificate> = {};
        certificates.forEach((cert) => {
          mapped[cert.enrollment_id] = cert;
        });
        setCertificatesByEnrollment(mapped);
      }
    } catch (error) {
      setEnrollments([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEnrollments();
  }, [userId, token, refreshToken]);

  // Handle Mesh Events
  useEffect(() => {
    if (lastEvent) {
      try {
        const payload = JSON.parse(lastEvent);
        if (payload.event === "MESH_EVENT_ASSESSMENT_SCORED" && payload.user_id === userId) {
          addToast(`Examen calificado: ${payload.score}% - ${payload.passed ? 'Aprobado' : 'Reprobado'}`, payload.passed ? 'success' : 'error');
          loadEnrollments();
        }
      } catch (e) {
        console.error("Error parsing mesh event", e);
      }
    }
  }, [lastEvent]);

  const submitAssessment = async (enrollmentId: number, assessmentId: number) => {
    const score = parseFloat(scoreByAssessment[assessmentId] || "0");
    try {
      const response = await fetch(apiUrl(`/enrollments/${enrollmentId}/assessments/${assessmentId}/submit`), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ submitted_score: score }),
      });

      if (!response.ok) {
        const err = await response.json();
        setMessageByEnrollment(prev => ({ ...prev, [enrollmentId]: err.detail || "Error al calificar" }));
        return;
      }

      const result = await response.json();
      setMessageByEnrollment(prev => ({
        ...prev,
        [enrollmentId]: result.passed ? "¡Felicidades! Has aprobado el curso." : "No alcanzaste la nota mínima."
      }));
      setActiveExam(null);
      loadEnrollments();

    } catch (error) {
      setMessageByEnrollment(prev => ({ ...prev, [enrollmentId]: "Error de conexión" }));
    }
  };

  const openLessons = async (enrollment: Enrollment) => {
    setViewingLessonsCourse(enrollment);
    setLoadingLessons(true);
    try {
      const res = await fetch(apiUrl(`/courses/${enrollment.course.id}/lessons`), {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setLessons(data);
        if (data.length > 0) {
          setSelectedLesson(data[0]);
        }
      }
    } catch (err) {
      addToast("Error al cargar lecciones", "error");
    } finally {
      setLoadingLessons(false);
    }
  };

  if (loading) {
    return <div className="flex justify-center p-8"><Loader2 className="animate-spin text-primary w-8 h-8" /></div>;
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
              <div className="p-6 border-b border-white/5 hidden md:block">
                <div className="flex items-center gap-3 mb-2">
                  <span className="p-1.5 bg-primary/20 text-primary rounded-lg"><BookOpen size={16} /></span>
                  <span className="text-[10px] font-bold text-primary uppercase tracking-widest">Curso Activo</span>
                </div>
                <h3 className="font-bold text-white leading-tight">{viewingLessonsCourse.course.title}</h3>
              </div>
              <div className="flex-1 overflow-y-auto p-4 space-y-2 hide-scrollbar">
                {loadingLessons ? (
                  Array.from({ length: 4 }).map((_, i) => <div key={i} className="h-14 w-full bg-slate-800 animate-pulse rounded-2xl" />)
                ) : lessons.length > 0 ? (
                  lessons.map((lesson) => (
                    <button
                      key={lesson.id}
                      onClick={() => setSelectedLesson(lesson)}
                      className={`w-full text-left p-3.5 rounded-2xl transition-all flex items-center gap-4 group ${selectedLesson?.id === lesson.id ? 'bg-primary/20 border border-primary/30 shadow-lg shadow-primary/10' : 'hover:bg-slate-800/60 border border-transparent'}`}
                    >
                      <div className={`p-2 rounded-xl transition-colors ${selectedLesson?.id === lesson.id ? 'bg-primary text-white shadow-md shadow-primary/30' : 'bg-slate-800 text-slate-400 group-hover:text-primary group-hover:bg-primary/10'}`}>
                        <Play size={14} className={selectedLesson?.id === lesson.id ? 'fill-current' : 'group-hover:fill-current'} />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className={`text-xs font-bold truncate ${selectedLesson?.id === lesson.id ? 'text-white' : 'text-slate-300 group-hover:text-white'}`}>{lesson.title}</p>
                        <p className={`text-[10px] ${selectedLesson?.id === lesson.id ? 'text-primary-200' : 'text-slate-500'}`}>{lesson.duration_minutes} min</p>
                      </div>
                    </button>
                  ))
                ) : (
                  <p className="text-center py-10 text-[10px] font-bold text-slate-500 uppercase tracking-widest">No hay lecciones.</p>
                )}
              </div>
            </div>

            {/* Content Area */}
            <div className="flex-1 bg-slate-950 relative flex flex-col h-2/3 md:h-full">
              <div className="absolute top-6 right-6 hidden md:block z-10">
                <button onClick={() => setViewingLessonsCourse(null)} className="p-3 bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700 rounded-full transition-all shadow-sm">
                  <CloseIcon size={20} />
                </button>
              </div>

              {selectedLesson ? (
                <div className="flex-1 overflow-y-auto p-6 md:p-12 relative hide-scrollbar">
                  <div className="absolute inset-x-0 top-0 h-40 bg-gradient-to-b from-primary/10 to-transparent pointer-events-none"></div>
                  <div className="max-w-3xl mx-auto space-y-8 relative">
                    <div>
                      <div className="flex items-center gap-2 mb-4">
                        <span className="p-2 bg-primary/20 text-primary rounded-xl"><BookOpen size={16} /></span>
                        <span className="text-[10px] font-bold text-primary uppercase tracking-widest">Lección Actual</span>
                      </div>
                      <h2 className="text-3xl md:text-4xl font-bold text-white tracking-tight leading-tight mb-6">{selectedLesson.title}</h2>
                    </div>

                    <div className="prose prose-invert prose-lg max-w-none">
                      <div dangerouslySetInnerHTML={{ __html: selectedLesson.content.replace(/\n/g, '<br/>') }} className="text-slate-300 font-normal leading-relaxed text-lg" />
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-12 pt-12 border-t border-white/10">
                      <div className="space-y-4">
                        <h4 className="text-sm font-bold text-white flex items-center gap-2"><Paperclip size={18} className="text-primary" /> Material de Estudio</h4>
                        <div className="space-y-2">
                          {selectedLesson.resources && selectedLesson.resources.length > 0 ? (
                            selectedLesson.resources.map((res: any) => (
                              <a key={res.id} href={res.file_url.startsWith('http') ? res.file_url : `${apiUrl('')}${res.file_url}`} target="_blank" rel="noopener noreferrer" className="flex items-center justify-between p-4 bg-slate-900 border border-white/5 rounded-2xl hover:border-primary/50 transition-all group">
                                <div className="flex items-center gap-3">
                                  <div className="p-2 bg-primary/10 rounded-lg text-primary"><File size={16} /></div>
                                  <span className="text-xs font-medium text-slate-300 group-hover:text-white">{res.title}</span>
                                </div>
                                <ChevronRight size={14} className="text-slate-600 group-hover:text-primary" />
                              </a>
                            ))
                          ) : (
                            <div className="p-4 bg-slate-900/50 rounded-2xl border border-dashed border-white/5 text-center">
                              <p className="text-[10px] text-slate-500 italic font-medium uppercase tracking-widest">No hay material.</p>
                            </div>
                          )}
                        </div>
                      </div>

                      <div className="space-y-4">
                        <h4 className="text-sm font-bold text-white flex items-center gap-2"><Upload size={18} className="text-emerald-500" /> Entregar Tarea</h4>
                        <div className="p-6 bg-slate-900 border border-white/5 rounded-3xl flex flex-col items-center justify-center text-center gap-4">
                          <div className="p-4 bg-emerald-500/10 rounded-full text-emerald-500"><FileText size={24} /></div>
                          <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest leading-relaxed">Sube tu trabajo en PDF o Word para ser calificado.</p>
                          <label className="w-full py-3 bg-white text-slate-900 rounded-xl text-[10px] font-black uppercase tracking-widest hover:bg-slate-100 transition-all cursor-pointer text-center">
                            <input
                              type="file"
                              className="hidden"
                              onChange={(e) => {
                                const file = e.target.files?.[0];
                                if (file && viewingLessonsCourse) {
                                  const formData = new FormData();
                                  formData.append('file', file);
                                  formData.append('enrollment_id', viewingLessonsCourse.id.toString());
                                  fetch(apiUrl(`/lessons/${selectedLesson.id}/submit-assignment`), {
                                    method: 'POST',
                                    headers: { Authorization: `Bearer ${token}` },
                                    body: formData
                                  })
                                    .then(res => res.ok ? addToast("Tarea entregada", "success") : addToast("Error", "error"))
                                    .catch(() => addToast("Error", "error"));
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
                <div className="flex-1 flex flex-col items-center justify-center p-12 text-center relative">
                  <div className="relative p-6 bg-slate-800/50 rounded-full text-slate-400 mb-6"><BookOpen size={48} /></div>
                  <h3 className="text-xl font-bold text-white mb-2">Comienza a Aprender</h3>
                  <p className="text-sm text-slate-400 max-w-xs">Selecciona una lección para ver su contenido.</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {enrollments.length === 0 ? (
        <div className="p-10 text-center rounded-2xl border border-dashed border-white/10 bg-slate-900/30 backdrop-blur-md mx-2">
          <Info className="mx-auto text-slate-500 mb-4" size={32} />
          <p className="text-xs font-bold text-slate-400 uppercase tracking-widest leading-loose">No tienes cursos activos.</p>
        </div>
      ) : (
        <div className="flex flex-col gap-3 px-4">
          {enrollments.map((item) => {
            const progressCircumference = 263.89;
            const progressOffset = progressCircumference - (progressCircumference * item.progress_percent) / 100;

            return (
              <article key={item.id} className="glass p-4 rounded-2xl flex flex-col gap-3">
                <div className="flex gap-4 items-center cursor-pointer group" onClick={() => openLessons(item)}>
                  <div className="relative flex size-14 shrink-0 items-center justify-center">
                    <svg className="absolute inset-0 size-14 -rotate-90" viewBox="0 0 100 100">
                      <circle className="text-white/5 stroke-current" cx="50" cy="50" fill="transparent" r="42" strokeWidth="8"></circle>
                      <circle className="text-primary stroke-current transition-all duration-1000 ease-out" cx="50" cy="50" fill="transparent" r="42" strokeLinecap="round" strokeWidth="8" style={{ strokeDasharray: progressCircumference, strokeDashoffset: progressOffset }}></circle>
                    </svg>
                    <span className="material-symbols-outlined text-2xl text-primary group-hover:scale-110 transition-transform">
                      {item.course.modality === 'formal' ? 'school' : 'menu_book'}
                    </span>
                  </div>

                  <div className="flex flex-1 flex-col justify-center min-w-0">
                    <div className="flex justify-between items-start">
                      <h3 className="font-bold text-base truncate pr-2 text-white">{item.course.title}</h3>
                      <span className="text-[9px] font-bold text-primary px-1.5 py-0.5 rounded bg-primary/10 shrink-0">{Math.round(item.progress_percent)}%</span>
                    </div>
                    <p className="text-slate-400 text-xs line-clamp-1 capitalize">{item.course.modality.replace('_', ' ')}</p>
                  </div>
                  <span className="material-symbols-outlined text-slate-600">chevron_right</span>
                </div>

                <div className="flex gap-2 border-white/5 empty:hidden pt-2 border-t">
                  {item.approved && certificatesByEnrollment[item.id] ? (
                    <button onClick={() => setSelectedCertificate({ cert: certificatesByEnrollment[item.id], enrollment: item })} className="flex-1 py-2 bg-emerald-500/10 text-emerald-400 rounded-xl text-xs font-bold transition-all flex justify-center gap-2">
                      Ver Certificado <Award size={14} />
                    </button>
                  ) : !item.approved && item.progress_percent >= 90 && (
                    <button onClick={() => setActiveExam(item.id)} className="flex-1 py-2 bg-primary text-white rounded-xl text-xs font-bold hover:bg-primary/90 transition-all flex justify-center gap-2">
                      Tomar Examen <ArrowRight size={14} />
                    </button>
                  )}
                </div>

                {!item.approved && activeExam === item.id && (
                  <div className="mt-2 space-y-4">
                    {(assessmentsByCourse[item.course.id] || []).map((assessment) => (
                      <div key={assessment.id} className="p-5 bg-slate-800/80 rounded-2xl border border-primary/20 shadow-inner">
                        <div className="flex justify-between items-center mb-4">
                          <p className="text-xs font-bold uppercase tracking-widest text-slate-200">Examen Final</p>
                          <button onClick={() => setActiveExam(null)} className="text-slate-500 hover:text-white bg-white/5 rounded-full p-1"><CloseIcon size={16} /></button>
                        </div>
                        <div className="flex gap-2">
                          <input type="number" min="0" max="100" value={scoreByAssessment[assessment.id] || ""} onChange={(e) => setScoreByAssessment(prev => ({ ...prev, [assessment.id]: e.target.value }))} className="flex-1 rounded-xl bg-slate-900 border border-white/10 px-4 py-3 text-sm text-white focus:border-primary outline-none" placeholder="Nota" />
                          <button onClick={() => submitAssessment(item.id, assessment.id)} className="px-6 py-3 bg-primary text-white rounded-xl text-xs font-bold uppercase hover:bg-primary/90 transition-all">Enviar</button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </article>
            );
          })}
        </div>
      )}

      {selectedCertificate && (
        <CertificateModal
          certificate={selectedCertificate.cert}
          enrollment={selectedCertificate.enrollment}
          userName={userId ? "Estudiante" : "Estudiante"}
          onClose={() => setSelectedCertificate(null)}
        />
      )}
    </section>
  );
}
