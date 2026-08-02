export interface CourseSummary {
  id: string;
  code: string;
  title: string;
  description?: string | null;
  modality: string;
  duration_hours: number;
  is_self_paced: boolean;
  cohort_name?: string | null;
  certificate_type?: string | null;
}

export interface EnrollmentRecord {
  id: string;
  status: string;
  progress_percent: number;
  final_grade?: number | null;
  attendance_percent: number;
  approved: boolean;
  certificate_issued: boolean;
  acta_closed: boolean;
  course: CourseSummary;
}

export interface LessonRecord {
  id: string;
  course_id: string;
  title: string;
  content: string;
  order_index: number;
  duration_minutes: number;
}

export interface CertificateRecord {
  id: string;
  enrollment_id: string;
  certificate_code: string;
  certificate_type?: string | null;
  course_title?: string | null;
  issued_at: string;
}

export interface AssignmentSubmissionReview {
  id: string;
  enrollment_id: string;
  lesson_id: string;
  student_name: string;
  lesson_title: string;
  file_url: string;
  comment?: string | null;
  grade?: number | null;
  teacher_feedback?: string | null;
  submitted_at: string;
}

export interface MetricCard {
  title: string;
  value: string;
  trend: string;
  tone: string;
}

export interface DashboardMetrics {
  active_students?: number;
  completion_rate?: number;
  certificates_issued?: number;
  total_courses: number;
  formal_courses: number;
  non_formal_courses: number;
  total_enrollments: number;
  completed_enrollments: number;
  approved_formal_enrollments: number;
  approved_non_formal_enrollments: number;
  cards?: MetricCard[];
  enrollment_trends?: { label: string; value: number }[];
  top_courses?: { title: string; count: number }[];
}

export interface PilotChecklistItem {
  key: string;
  label: string;
  completed: boolean;
}

export interface PilotReadiness {
  environment_ready: boolean;
  kpi_dashboard_ready: boolean;
  support_ready: boolean;
  security_ready: boolean;
  readiness_score: number;
  checklist: PilotChecklistItem[];
}

export interface AcademyStudentProfile {
  persona_id: string;
  username: string;
  total_progress: number;
  enrollments_count: number;
  certificates_count: number;
  active_courses: EnrollmentRecord[];
  recent_certificates: CertificateRecord[];
}

// H-11 (cierre 2026-07-24): tipos mirror de las schemas Pydantic en
// ``backend/schemas/academy.py`` — sustituyen los ``any`` en hooks y
// submódulos del front (forum thread/comments, course detail).
// Mantener sincronizado con el contract del backend.

export interface ForumThreadRecord {
  id: string;
  title: string;
  category: string;
  author_persona_id: string;
  is_resolved: boolean;
  created_at: string;
  // Backend ``ForumThread`` no expone ``content`` en la lista, pero el
  // detalle del thread lo incluye vía el row ORM completo — opcional aquí
  // para que page.tsx del detalle pueda leerlo sin romper TS.
  content?: string;
  course_id?: string | null;
  // Campos opcionales derivados/presentes en el detalle del thread.
  author?: string | null;
  author_role?: string | null;
  upvotes?: number;
}

export interface ForumCommentRecord {
  id: string;
  thread_id: string;
  parent_id?: string | null;
  author_persona_id: string;
  content: string;
  created_at: string;
}

export interface CourseDetail {
  id: string;
  code: string;
  slug?: string | null;
  title: string;
  description?: string | null;
  excerpt?: string | null;
  tag?: string | null;
  cta_text?: string | null;
  syllabus?: Record<string, unknown> | unknown[] | null;
  modality: string;
  sede_id?: string | null;
  is_published: boolean;
  is_self_paced: boolean;
  duration_hours: number;
  xp_per_lesson?: number;
  cohort_name?: string | null;
  certificate_type?: string | null;
  access_level: string;
  image_url?: string | null;
  instructor_name?: string | null;
  created_at?: string | null;
  lesson_count?: number;
  total_minutes?: number;
  lessons?: LessonRecord[];
  // H-11 (cierre 2026-07-24) + F-02bis (cierre 2026-08-02):
  // ``students_count`` SÍ es emitido por ``_serialize_course`` en list/detail
  // (count bulk Axioma-3, sin N+1; 0 para cursos globales en un Manager con
  // sede — scope admin estricto F-02). ``lesson_count`` (singular) es el
  // campo real de lecciones. ``lessons_count`` es legacy muerto (el backend
  // nunca lo emite) y se conserva por tolerancia, sin renderizarse.
  students_count?: number;
  lessons_count?: number;
}

export interface CertificateDetail {
  id: string;
  enrollment_id: string;
  certificate_code: string;
  issued_at: string;
  certificate_type?: string | null;
  course_title?: string | null;
}
